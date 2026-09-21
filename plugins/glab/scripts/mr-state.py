#!/usr/bin/env python3
"""Read the state of one or more GitLab merge requests, remember it, and report what changed.

One file, standard library only. Three ways to run it:

  mr-state.py                       the MR of the current branch, as glab detects it; full read
  mr-state.py --mr-url U [--mr-url U2]   a set of MRs across repos; full read
  mr-state.py --mr-url U --wait-for-state-change-timeout-minutes 9
                                    probe every minute, exit on the first change or on timeout

Every run loads the last known state of each MR from its state file, compares, prints the diff,
flushes, and only then writes the new state. A run that is killed between the print and the
write reports the same change again next time; nothing is lost between runs.

The probe is two calls per MR: the merge-request object and the newest note by updated_at.
The heavy reads are gated on what moved: the pipeline dump (glab-pipeline) on a pipeline id or
status change, the discussion dump (glab-discussion) on a note change, approvals on updated_at.

Exit codes: 0 a change was detected (or a one-shot read succeeded), 3 the wait timed out with no
change, 4 the first run established a baseline, 5 nothing could be read at all — every MR failed
on every probe of the run, 1 a fatal error (bad arguments, no MR, no glab). A run in which some
MRs read and others did not keeps its normal exit code and prints a READ_FAILED line per MR.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import re
import shutil
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote

MAX_RETRIES = 5
INITIAL_RETRY_DELAY = 1.0

EXIT_CHANGE = 0
EXIT_FATAL = 1
EXIT_TIMEOUT = 3
EXIT_BASELINE = 4
EXIT_READ_FAILED = 5

# The HTTP codes that mean "asking again changes nothing": a bad token, a forbidden project, a
# deleted or renamed MR. Whole tokens only — "connection refused" and "502 Bad Gateway" are
# transient and must keep their retries, and a substring match on words like refused or blocked
# swallowed both.
NON_RETRYABLE_HTTP = re.compile(r"\b(401|403|404)\b")

# Approvals the host would not hand over. Kept in the snapshot so the next run can tell "nobody
# has approved" from "we never found out", and does not re-probe a refused endpoint every minute.
APPROVALS_UNAVAILABLE = {"unavailable": True}

HELPER_URLS = {
    "glab-discussion": "https://github.com/fprochazka/glab-discussion",
    "glab-pipeline": "https://github.com/fprochazka/glab-pipeline",
}
INSTALL_HINT = "uv tool install glab-discussion glab-pipeline"

# Transient values GitLab reports while it recomputes. They are not a change; the last settled
# value stays in the snapshot until a settled value replaces it.
TRANSIENT_MERGE_STATUS = {"checking", "unchecked"}
TRANSIENT_DETAILED_MERGE_STATUS = {"checking", "unchecked", "preparing"}


# ----------------------------------------------------------------------------------------------
# Small helpers
# ----------------------------------------------------------------------------------------------


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def die(message: str) -> None:
    print(f"Error: {message}", file=sys.stderr)
    sys.exit(EXIT_FATAL)


def which(name: str) -> bool:
    return shutil.which(name) is not None


def run(cmd: list[str], *, check: bool = True, capture: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, check=check, capture_output=capture, text=True)


def parse_mr_url(url: str) -> tuple[str, str, int]:
    """Return (host, project_path, iid) for a GitLab MR URL."""
    m = re.match(r"^https?://([^/]+)/(.+?)/-/merge_requests/(\d+)(?:[/?#].*)?$", url.strip())
    if not m:
        raise ValueError(f"not a merge request URL: {url}")
    return m.group(1), m.group(2), int(m.group(3))


def state_dir_for(host: str, project_path: str, iid: int, root: Path | None = None) -> Path:
    base = root or Path(tempfile.gettempdir()) / "glab-state"
    safe_project = project_path.replace("/", "__")
    return base / host / safe_project / f"mr-{iid}"


# ----------------------------------------------------------------------------------------------
# GitLab access through glab
# ----------------------------------------------------------------------------------------------


class GlabError(Exception):
    pass


class RefusedError(GlabError):
    """The host, or a policy in front of glab, refused the call. Retrying does not help."""


def glab_api(host: str, path: str, *, paginate: bool = False, attempts: int = MAX_RETRIES) -> Any:
    """Call `glab api` with retry and exponential backoff; return parsed JSON.

    `attempts` is for a call whose failure is cheap to live without: retrying an endpoint that
    a policy wrapper refuses without an HTTP code only spends the backoff and fails anyway.
    """
    cmd = ["glab", "api", "--hostname", host, path]
    if paginate:
        cmd.append("--paginate")
    delay = INITIAL_RETRY_DELAY
    last_error = ""
    for attempt in range(attempts):
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode == 0:
            # strict=False: a merge-request title or description can carry a raw control
            # character, and the strict decoder rejects the whole response over one of them.
            try:
                if paginate:
                    # --paginate prints one JSON array per page, concatenated; merge them.
                    decoder = json.JSONDecoder(strict=False)
                    pos, merged, text = 0, [], proc.stdout.strip()
                    while pos < len(text):
                        obj, end = decoder.raw_decode(text, pos)
                        merged.extend(obj if isinstance(obj, list) else [obj])
                        pos = end
                        while pos < len(text) and text[pos] in " \n\r\t":
                            pos += 1
                    return merged
                return json.loads(proc.stdout, strict=False)
            except json.JSONDecodeError as e:
                # A response that does not parse parses no better on the fifth try.
                raise GlabError(f"invalid JSON from glab api {path}: {e}") from e
        else:
            last_error = (proc.stderr or proc.stdout).strip()
            if NON_RETRYABLE_HTTP.search(last_error):
                raise RefusedError(last_error)
        if attempt < attempts - 1:
            time.sleep(delay + random.uniform(0, delay / 2))
            delay *= 2
    raise GlabError(last_error or f"glab api {path} failed")


def resolve_current_branch_mr() -> str:
    """Return the web URL of the open MR for the current branch, or die with guidance."""
    try:
        run(["git", "rev-parse", "--git-dir"])
    except subprocess.CalledProcessError:
        die("not in a git repository; pass --mr-url or run from a checkout")
    proc = subprocess.run(["glab", "mr", "view", "--output=json"], capture_output=True, text=True)
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout).strip()
        # glab writes "No open merge request available for "<branch>"." — match without case,
        # or the guidance below is replaced by glab's own wall of text.
        lowered = err.lower()
        if "no open merge request" in lowered or "could not find" in lowered:
            branch = subprocess.run(["git", "branch", "--show-current"], capture_output=True, text=True).stdout.strip()
            die(f"no open merge request for the current branch ({branch or 'unknown'}); push the branch and open one, or pass --mr-url")
        if "authentication" in lowered or "401" in lowered:
            die("GitLab authentication failed; run `glab auth login`")
        die(f"glab mr view failed: {err}")
    try:
        return json.loads(proc.stdout, strict=False)["web_url"]
    except (json.JSONDecodeError, KeyError) as e:
        die(f"could not read web_url from glab mr view: {e}")
    return ""  # unreachable


# ----------------------------------------------------------------------------------------------
# Snapshot: what one probe of one MR yields
# ----------------------------------------------------------------------------------------------


def usernames(items: Any) -> list[str]:
    return sorted(str(i.get("username", "")) for i in (items or []) if isinstance(i, dict))


def snapshot_from_mr(mr: dict[str, Any], host: str, project_path: str) -> dict[str, Any]:
    """Reduce a merge-request API object to the fields the diff reads."""
    hp = mr.get("head_pipeline") or {}
    return {
        "host": host,
        "project_path": project_path,
        "iid": mr.get("iid"),
        "web_url": mr.get("web_url"),
        "title": mr.get("title"),
        "author": (mr.get("author") or {}).get("username"),
        "state": mr.get("state"),
        "draft": bool(mr.get("draft", mr.get("work_in_progress", False))),
        "sha": mr.get("sha"),
        "source_branch": mr.get("source_branch"),
        "target_branch": mr.get("target_branch"),
        "diverged_commits_count": mr.get("diverged_commits_count"),
        "rebase_in_progress": bool(mr.get("rebase_in_progress", False)),
        "merge_status": mr.get("merge_status"),
        "detailed_merge_status": mr.get("detailed_merge_status"),
        "has_conflicts": bool(mr.get("has_conflicts", False)),
        "blocking_discussions_resolved": mr.get("blocking_discussions_resolved"),
        "assignees": usernames(mr.get("assignees")),
        "reviewers": usernames(mr.get("reviewers")),
        "labels": sorted(mr.get("labels") or []),
        "user_notes_count": mr.get("user_notes_count"),
        "updated_at": mr.get("updated_at"),
        "head_pipeline": {
            "id": hp.get("id"),
            "status": hp.get("status"),
            "sha": hp.get("sha"),
            "web_url": hp.get("web_url"),
            "created_at": hp.get("created_at"),
            "updated_at": hp.get("updated_at"),
        }
        if hp
        else None,
        "newest_note": None,  # filled by probe_notes
        "notes_probe": None,  # "exact" | "count-only"
        "approvals": None,  # filled when updated_at moved; APPROVALS_UNAVAILABLE when refused
    }


def probe_notes(host: str, enc: str, iid: int) -> tuple[dict[str, Any] | None, str]:
    """Newest note by updated_at. Returns (note, mode); mode is 'exact' or 'count-only'.

    One attempt, never five. A host that refuses this sub-resource refuses it consistently, and
    a wrapper that answers without an HTTP code cannot be told apart from a transient failure,
    so retrying it would stall every probe of a wait by the whole backoff. The caller degrades
    to the count-only path for the rest of the run instead.
    """
    try:
        notes = glab_api(host, f"projects/{enc}/merge_requests/{iid}/notes?per_page=1&order_by=updated_at&sort=desc", attempts=1)
    except GlabError:
        return None, "count-only"
    if not isinstance(notes, list) or not notes:
        return None, "exact"
    n = notes[0]
    return {
        "id": n.get("id"),
        "updated_at": n.get("updated_at"),
        "created_at": n.get("created_at"),
        "author": (n.get("author") or {}).get("username"),
        "system": bool(n.get("system", False)),
        "resolved": n.get("resolved"),
    }, "exact"


def probe_approvals(host: str, enc: str, iid: int) -> dict[str, Any]:
    try:
        a = glab_api(host, f"projects/{enc}/merge_requests/{iid}/approvals")
    except GlabError:
        # A sentinel, not None: the next run then knows the endpoint was tried and refused,
        # and stops re-probing a refused endpoint on every probe of a nine-minute wait.
        return dict(APPROVALS_UNAVAILABLE)
    return {
        "approved_by": sorted(((x.get("user") or {}).get("username") or "") for x in (a.get("approved_by") or [])),
        "approvals_left": a.get("approvals_left"),
        "approved": a.get("approved"),
    }


def probe_default_branch(host: str, enc: str) -> str | None:
    try:
        p = glab_api(host, f"projects/{enc}")
    except GlabError:
        return None
    return p.get("default_branch")


# ----------------------------------------------------------------------------------------------
# Diff: two snapshots in, a list of events out
# ----------------------------------------------------------------------------------------------


@dataclass
class Event:
    id: str
    detail: str
    before: Any = None
    after: Any = None

    def line(self) -> str:
        return f"{self.id}: {self.detail}"


def settle(old: dict[str, Any] | None, new: dict[str, Any]) -> dict[str, Any]:
    """Keep the last settled merge status when GitLab reports a transient one."""
    if old is None:
        return new
    settled = dict(new)
    if new.get("merge_status") in TRANSIENT_MERGE_STATUS:
        settled["merge_status"] = old.get("merge_status")
    if new.get("detailed_merge_status") in TRANSIENT_DETAILED_MERGE_STATUS:
        settled["detailed_merge_status"] = old.get("detailed_merge_status")
    if new.get("rebase_in_progress"):
        # A rebase in flight also reports divergence and conflicts mid-way; hold both.
        settled["diverged_commits_count"] = old.get("diverged_commits_count")
        settled["has_conflicts"] = old.get("has_conflicts")
    return settled


def diff_snapshots(old: dict[str, Any] | None, new: dict[str, Any]) -> list[Event]:
    """Every observation-level change between two snapshots of one MR."""
    if old is None:
        return []
    new = settle(old, new)
    events: list[Event] = []

    def changed(key: str) -> bool:
        return old.get(key) != new.get(key)

    if changed("state"):
        events.append(Event("STATE_CHANGED", f"{old.get('state')} -> {new.get('state')}", old.get("state"), new.get("state")))
    if changed("draft"):
        events.append(Event("DRAFT_CHANGED", "draft" if new["draft"] else "ready", old.get("draft"), new.get("draft")))
    if changed("sha"):
        divergence = new.get("diverged_commits_count")
        hint = "rebase likely: behind count dropped to 0" if divergence == 0 and (old.get("diverged_commits_count") or 0) > 0 else "new head"
        # Full SHAs, not the short form the scorecard uses: the caller pins a review to the SHA
        # this line names, and an eight-character prefix is not something it can pass on.
        events.append(Event("HEAD_CHANGED", f"{old.get('sha')} -> {new.get('sha')} ({hint})", old.get("sha"), new.get("sha")))
    if changed("target_branch"):
        events.append(Event("TARGET_CHANGED", f"{old.get('target_branch')} -> {new.get('target_branch')}", old.get("target_branch"), new.get("target_branch")))
    if changed("title"):
        events.append(Event("TITLE_CHANGED", f"{old.get('title')!r} -> {new.get('title')!r}", old.get("title"), new.get("title")))

    op, np_ = old.get("head_pipeline") or {}, new.get("head_pipeline") or {}
    if (op.get("id"), op.get("status")) != (np_.get("id"), np_.get("status")):
        if op.get("id") != np_.get("id"):
            detail = f"new pipeline {np_.get('id')} ({np_.get('status')}) on {short(np_.get('sha'))}, was {op.get('id')} ({op.get('status')})"
        else:
            detail = f"pipeline {np_.get('id')}: {op.get('status')} -> {np_.get('status')}"
        if new.get("diverged_commits_count"):
            detail += f"; branch is {new['diverged_commits_count']} behind {new.get('target_branch')}, so this ran on a superseded base"
        events.append(Event("PIPELINE_CHANGED", detail, op, np_))

    if changed("diverged_commits_count"):
        events.append(Event("BEHIND_CHANGED", f"behind {new.get('target_branch')} by {old.get('diverged_commits_count')} -> {new.get('diverged_commits_count')}", old.get("diverged_commits_count"), new.get("diverged_commits_count")))
    if changed("merge_status") or changed("detailed_merge_status") or changed("has_conflicts"):
        events.append(Event(
            "MERGE_STATUS_CHANGED",
            f"{old.get('merge_status')}/{old.get('detailed_merge_status')}/conflicts={old.get('has_conflicts')} -> "
            f"{new.get('merge_status')}/{new.get('detailed_merge_status')}/conflicts={new.get('has_conflicts')}",
        ))

    if changed("blocking_discussions_resolved"):
        events.append(Event("DISCUSSIONS_RESOLVED_CHANGED", f"all blocking discussions resolved: {old.get('blocking_discussions_resolved')} -> {new.get('blocking_discussions_resolved')}"))
    for key, eid in (("reviewers", "REVIEWERS_CHANGED"), ("assignees", "ASSIGNEES_CHANGED"), ("labels", "LABELS_CHANGED")):
        if changed(key):
            added = sorted(set(new.get(key) or []) - set(old.get(key) or []))
            removed = sorted(set(old.get(key) or []) - set(new.get(key) or []))
            events.append(Event(eid, f"added {added or '-'}, removed {removed or '-'}", old.get(key), new.get(key)))
    oa, na = old.get("approvals"), new.get("approvals")
    if approvals_known(oa) and approvals_known(na) and (oa.get("approved_by"), oa.get("approvals_left")) != (na.get("approved_by"), na.get("approvals_left")):
        added = sorted(set(na.get("approved_by") or []) - set(oa.get("approved_by") or []))
        removed = sorted(set(oa.get("approved_by") or []) - set(na.get("approved_by") or []))
        events.append(Event("APPROVALS_CHANGED", f"approved by +{added or '-'} -{removed or '-'}; approvals left {na.get('approvals_left')}", oa, na))

    # Notes come last on purpose. The count-only probe blames a moved updated_at on note
    # traffic only when nothing else in this run explains it, and "nothing else" has to mean
    # every field compared above — a reviewer assignment bumps updated_at too.
    events.extend(note_events(old, new, explained=bool(events)))
    return events


def note_events(old: dict[str, Any], new: dict[str, Any], *, explained: bool) -> list[Event]:
    """What the notes moved, as far as this run's probe mode can tell."""
    on, nn = old.get("newest_note") or {}, new.get("newest_note") or {}
    if new.get("notes_probe") == "exact":
        if (on.get("id"), on.get("updated_at")) != (nn.get("id"), nn.get("updated_at")):
            if on.get("id") != nn.get("id"):
                # The newest note by updated_at went backwards in time, so the one we saw last
                # run is gone and an older note took its place. Nothing was posted.
                kind = "newest note deleted, now the newest is a note" if is_older(nn.get("updated_at"), on.get("updated_at")) else "new note"
            else:
                kind = "note edited or resolved"
            sysflag = " (system note)" if nn.get("system") else ""
            return [Event("NOTES_CHANGED", f"{kind} by @{nn.get('author')}{sysflag} at {nn.get('updated_at')}", on, nn)]
        if old.get("user_notes_count") != new.get("user_notes_count"):
            # The newest note by updated_at did not move, yet the count did: a note further
            # down the list came or went. The exact probe alone cannot see that.
            return [Event(
                "NOTES_CHANGED",
                f"user note count {old.get('user_notes_count')} -> {new.get('user_notes_count')} while the newest note stayed the same (a note elsewhere in the list came or went)",
                old.get("user_notes_count"),
                new.get("user_notes_count"),
            )]
        return []
    if old.get("user_notes_count") != new.get("user_notes_count"):
        return [Event("NOTES_CHANGED", f"user note count {old.get('user_notes_count')} -> {new.get('user_notes_count')} (count-only probe)", old.get("user_notes_count"), new.get("user_notes_count"))]
    if old.get("updated_at") != new.get("updated_at") and not explained:
        return [Event("NOTES_CHANGED", f"updated_at moved to {new.get('updated_at')} with no other field explaining it (count-only probe; may be a note edit, a resolve, or bot traffic)", old.get("updated_at"), new.get("updated_at"))]
    return []


def approvals_known(a: Any) -> bool:
    """False for approvals never read and for approvals the host refused."""
    return isinstance(a, dict) and not a.get("unavailable")


def is_older(a: Any, b: Any) -> bool:
    """True when timestamp a is strictly earlier than b. Unparsable input is never older."""
    if not a or not b:
        return False
    try:
        return datetime.fromisoformat(str(a).replace("Z", "+00:00")) < datetime.fromisoformat(str(b).replace("Z", "+00:00"))
    except ValueError:
        return False


def short(sha: Any) -> str:
    return str(sha)[:8] if sha else "-"


# ----------------------------------------------------------------------------------------------
# Detail fetches: the discussion dump and the pipeline dump
# ----------------------------------------------------------------------------------------------


@dataclass
class Details:
    discussions_dir: str | None = None
    discussions_summary: str = ""
    pipeline_dir: str | None = None
    pipeline_summary_file: str | None = None
    failed_jobs: list[str] = field(default_factory=list)
    external_statuses: list[dict[str, Any]] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def missing_helper_message(tool: str) -> str:
    return (
        f"DEPENDENCY MISSING: {tool} is not installed, so details could not be fetched automatically. "
        f"Ask the user to install it: `{INSTALL_HINT}` ({HELPER_URLS[tool]}). The probe keeps working without it."
    )


def fetch_discussions(url: str, details: Details) -> None:
    if not which("glab-discussion"):
        details.errors.append(missing_helper_message("glab-discussion"))
        return
    proc = subprocess.run(["glab-discussion", "read", "--dump", "--mr-url", url], capture_output=True, text=True)
    out = (proc.stdout + proc.stderr).strip()
    if proc.returncode != 0:
        details.errors.append(f"glab-discussion read failed: {out}")
        return
    details.discussions_summary = out
    first = out.splitlines()[0] if out else ""
    if first.startswith("Discussions:"):
        details.discussions_dir = first[len("Discussions:"):].strip().rstrip("/")


def fetch_pipeline(url: str, snap: dict[str, Any], sdir: Path, details: Details) -> None:
    if not which("glab-pipeline"):
        details.errors.append(missing_helper_message("glab-pipeline"))
        return
    hp = snap.get("head_pipeline") or {}
    if not hp:
        details.notes.append("no pipeline has run for this head, so there is nothing to dump")
        return
    pdir = sdir / "pipeline"
    summary_file = sdir / "pipeline-summary.txt"
    with open(summary_file, "w") as fh:
        proc = subprocess.run(["glab-pipeline", "inspect", "--mr-url", url, "--output-dir", str(pdir)], stdout=fh, stderr=subprocess.STDOUT, text=True)
    details.pipeline_dir = str(pdir)
    details.pipeline_summary_file = str(summary_file)
    if proc.returncode != 0:
        details.errors.append(f"glab-pipeline inspect failed, see {summary_file}")
        return
    summary_json = pdir / "summary.json"
    if summary_json.exists():
        try:
            data = json.loads(summary_json.read_text())
            details.failed_jobs = [f"{j.get('name')} [{j.get('stage')}] {j.get('failure_reason') or 'unknown'}" for j in data.get("failed_jobs") or []]
        except json.JSONDecodeError:
            pass
    # External commit statuses (for example a code-quality gate) live on the commit, not in the
    # pipeline, so glab-pipeline does not report them. Everything the pipeline itself ran also
    # shows up as a commit status, so filter those out: first by pipeline id, which GitLab sets
    # on every status a pipeline produced, then by name for a status that carries no id.
    # Names come from jobs.json *and* bridges.json — a trigger job is only in the latter, and
    # missing it turns every downstream trigger into a bogus external status.
    sha = hp.get("sha")
    if sha:
        try:
            enc = quote(snap["project_path"], safe="")
            statuses = glab_api(snap["host"], f"projects/{enc}/repository/commits/{sha}/statuses?per_page=100", paginate=True)
        except GlabError as e:
            details.errors.append(f"commit statuses unavailable: {e}")
            statuses = []
        details.external_statuses = external_statuses(statuses, hp.get("id"), pipeline_job_names(pdir))
        (sdir / "external-statuses.json").write_text(json.dumps(details.external_statuses, indent=2) + "\n")


def pipeline_job_names(pdir: Path) -> set[str]:
    """Every job name the pipeline dump knows, regular jobs and trigger jobs alike."""
    names: set[str] = set()
    for fname in ("jobs.json", "bridges.json"):
        path = pdir / fname
        if not path.exists():
            continue
        try:
            entries = json.loads(path.read_text(), strict=False)
        except json.JSONDecodeError:
            continue
        if isinstance(entries, list):
            names.update(str(j.get("name")) for j in entries if isinstance(j, dict) and j.get("name"))
    return names


def external_statuses(statuses: list[dict[str, Any]], pipeline_id: Any, job_names: set[str]) -> list[dict[str, Any]]:
    """Commit statuses that the head pipeline did not produce."""
    return [
        s
        for s in statuses
        if not (pipeline_id is not None and s.get("pipeline_id") == pipeline_id) and str(s.get("name")) not in job_names
    ]


# ----------------------------------------------------------------------------------------------
# One MR under watch
# ----------------------------------------------------------------------------------------------


@dataclass
class Watched:
    url: str
    host: str
    project_path: str
    iid: int
    sdir: Path
    enc: str = ""
    last: dict[str, Any] | None = None
    default_branch: str | None = None
    read_failure_reported: bool = False  # one READ_FAILED line per MR per run, not per probe
    notes_refused: bool = False  # the notes endpoint said no once, so stop asking it this run

    def __post_init__(self) -> None:
        self.enc = quote(self.project_path, safe="")
        self.sdir.mkdir(parents=True, exist_ok=True)
        # The skill names events.log as one of the files of a watched MR; create it on the
        # baseline run so the path exists even before the first change.
        (self.sdir / "events.log").touch()
        state_file = self.sdir / "state.json"
        if state_file.exists():
            try:
                saved = json.loads(state_file.read_text(), strict=False)
                self.last = saved.get("snapshot")
                self.default_branch = saved.get("default_branch")
            except json.JSONDecodeError:
                self.last = None

    @property
    def label(self) -> str:
        return f"{self.host}/{self.project_path}!{self.iid}"

    def probe(self) -> dict[str, Any]:
        # The MR object, the newest note and the default branch do not depend on each other, so
        # they run side by side; each is a glab process that mostly waits on the network.
        with ThreadPoolExecutor(max_workers=3) as pool:
            f_mr = pool.submit(glab_api, self.host, f"projects/{self.enc}/merge_requests/{self.iid}?include_diverged_commits_count=true&include_rebase_in_progress=true")
            f_notes = None if self.notes_refused else pool.submit(probe_notes, self.host, self.enc, self.iid)
            f_default = None if self.default_branch is not None else pool.submit(probe_default_branch, self.host, self.enc)
            mr = f_mr.result()
            notes = f_notes.result() if f_notes else None
            default_branch = f_default.result() if f_default else self.default_branch
        (self.sdir / "mr.json").write_text(json.dumps(mr, indent=2) + "\n")
        snap = snapshot_from_mr(mr, self.host, self.project_path)
        if notes is None:
            # Asked once this run and refused. The first probe of the next run asks again, so a
            # policy that is lifted between runs is picked up without a --reset.
            snap["newest_note"], snap["notes_probe"] = None, "count-only"
        else:
            snap["newest_note"], snap["notes_probe"] = notes
            self.notes_refused = snap["notes_probe"] == "count-only"
        if self.last is None or self.last.get("updated_at") != snap.get("updated_at") or self.last.get("approvals") is None:
            # Nothing else in the MR object reflects an approval, so the only trigger is a
            # moved updated_at. A refused read leaves the sentinel behind and waits for one.
            snap["approvals"] = probe_approvals(self.host, self.enc, self.iid)
        else:
            snap["approvals"] = self.last.get("approvals")
        self.default_branch = default_branch
        snap["default_branch"] = self.default_branch
        return snap

    def commit(self, snap: dict[str, Any]) -> None:
        """Advance the baseline. Called only after the diff has been printed and flushed."""
        payload = {"snapshot": settle(self.last, snap), "default_branch": self.default_branch, "written_at": utc_now()}
        tmp = self.sdir / "state.json.tmp"
        tmp.write_text(json.dumps(payload, indent=2) + "\n")
        os.replace(tmp, self.sdir / "state.json")
        self.last = payload["snapshot"]

    def log_events(self, events: list[Event]) -> None:
        with open(self.sdir / "events.log", "a") as fh:
            for e in events:
                fh.write(f"{utc_now()}\t{self.label}\t{e.id}\t{e.detail}\n")


# ----------------------------------------------------------------------------------------------
# Output
# ----------------------------------------------------------------------------------------------


def scorecard(snap: dict[str, Any]) -> str:
    hp = snap.get("head_pipeline") or {}
    behind = snap.get("diverged_commits_count")
    stacked = ""
    if snap.get("default_branch") and snap.get("target_branch") and snap["target_branch"] != snap["default_branch"]:
        stacked = f" · stacked on {snap['target_branch']}"
    approvals = snap.get("approvals")
    approved_by = ", ".join(approvals.get("approved_by") or []) or "-" if approvals_known(approvals) else "?"
    return (
        f"{snap['host']}/{snap['project_path']}!{snap['iid']} · {snap.get('state')} · {'draft' if snap.get('draft') else 'ready'}"
        f" · head {short(snap.get('sha'))} · pipeline {hp.get('status') or 'none'}"
        f"{'' if hp.get('sha') in (None, snap.get('sha')) else ' (on an older head)'}"
        f" · behind {behind if behind is not None else '?'}{stacked}"
        f" · conflicts {'yes' if snap.get('has_conflicts') else 'no'}"
        f" · notes {snap.get('user_notes_count')}"
        f" · approved by {approved_by} · updated {snap.get('updated_at')}"
    )


def print_snapshot(snap: dict[str, Any]) -> None:
    print(f"  title: {snap.get('title')}")
    print(f"  author: @{snap.get('author')} · source {snap.get('source_branch')} -> {snap.get('target_branch')}")
    print(f"  url: {snap.get('web_url')}")
    hp = snap.get("head_pipeline") or {}
    if hp:
        print(f"  pipeline: {hp.get('id')} {hp.get('status')} on {short(hp.get('sha'))} · {hp.get('web_url')}")
    print(f"  merge status: {snap.get('merge_status')} / {snap.get('detailed_merge_status')} · conflicts {snap.get('has_conflicts')} · rebase in progress {snap.get('rebase_in_progress')}")
    print(f"  reviewers: {snap.get('reviewers') or '-'} · assignees: {snap.get('assignees') or '-'} · labels: {snap.get('labels') or '-'}")
    nn = snap.get("newest_note") or {}
    if nn:
        print(f"  newest note: @{nn.get('author')}{' (system)' if nn.get('system') else ''} at {nn.get('updated_at')} (note:{nn.get('id')})")
    elif snap.get("notes_probe") == "count-only":
        print("  newest note: unavailable (notes endpoint refused; probing on note count and updated_at only)")


def print_details(d: Details) -> None:
    if d.discussions_dir:
        print(f"  discussions: {d.discussions_dir}/ (one file per thread; .meta.json maps id -> last activity)")
        lines = d.discussions_summary.splitlines()
        changed = [l for l in lines if l.strip().startswith(("updated:", "new:", "deleted:"))]
        for l in changed:
            print(f"    {l.strip()}")
        if not changed and len(lines) > 1:
            print(f"    {lines[-1].strip()}")
    if d.pipeline_dir:
        print(f"  pipeline dump: {d.pipeline_dir}/ (summary.json, jobs.json, job-logs/) · summary text: {d.pipeline_summary_file}")
        for j in d.failed_jobs:
            print(f"    failed: {j}")
        failed_ext = [s for s in d.external_statuses if s.get("status") == "failed"]
        for s in failed_ext:
            print(f"    failed external status: {s.get('name')} {s.get('description') or ''} {s.get('target_url') or ''}".rstrip())
        if d.external_statuses and not failed_ext:
            print(f"    external statuses: {len(d.external_statuses)}, none failed")
    for n in d.notes:
        print(f"  note: {n}")
    for e in d.errors:
        print(f"  ERROR: {e}")


def _try_probe(w: "Watched") -> "dict[str, Any] | GlabError":
    """Probe one MR for a thread pool: return the snapshot, or the error instead of raising."""
    try:
        return w.probe()
    except GlabError as e:
        return e


def check_helpers() -> list[str]:
    return [missing_helper_message(t) for t in ("glab-discussion", "glab-pipeline") if not which(t)]


# ----------------------------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--mr-url", action="append", default=[], help="MR URL; repeat for a set. Default: the current branch's MR")
    p.add_argument("--all", action="store_true", help="one-shot: fetch discussions and pipeline (default when not waiting)")
    p.add_argument("--comments", action="store_true", help="one-shot: fetch the discussion dump")
    p.add_argument("--pipeline", action="store_true", help="one-shot: fetch the pipeline dump")
    p.add_argument("--wait-for-state-change-timeout-minutes", type=float, default=None, metavar="N", help="probe until a change or N minutes; keep it under the caller's tool timeout")
    p.add_argument("--poll-interval-seconds", type=float, default=60.0, metavar="S")
    p.add_argument("--state-dir", type=Path, default=None, help="override the state root (default: <tmp>/glab-state)")
    p.add_argument("--reset", action="store_true", help="forget the stored state first; the run then establishes a new baseline")
    return p


def main(argv: list[str] | None = None) -> int:
    # Line-buffer stdout even when it is a pipe, so a caller reading the output as it comes
    # (the Bash tool, a tee, a log) sees each line when it is printed, not at exit.
    if hasattr(sys.stdout, "reconfigure"):  # a test's StringIO has no buffering to change
        sys.stdout.reconfigure(line_buffering=True)
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.wait_for_state_change_timeout_minutes is not None and (args.all or args.comments or args.pipeline):
        # In wait mode the fetches are driven by what moved, so an explicit flag would be read
        # as a promise the run cannot keep. Say so rather than accept it and ignore it.
        parser.error("--all, --comments and --pipeline are one-shot flags and cannot be combined with --wait-for-state-change-timeout-minutes; the wait fetches the discussion dump when a note moves and the pipeline dump when the pipeline moves")
    if not which("glab"):
        die("glab CLI is not installed")

    urls = args.mr_url or [resolve_current_branch_mr()]
    watched: list[Watched] = []
    for u in urls:
        try:
            host, project, iid = parse_mr_url(u)
        except ValueError as e:
            die(str(e))
        sdir = state_dir_for(host, project, iid, args.state_dir)
        if args.reset and sdir.exists():
            shutil.rmtree(sdir)
        watched.append(Watched(u, host, project, iid, sdir))

    waiting = args.wait_for_state_change_timeout_minutes is not None
    want_comments = args.comments or args.all or (not waiting and not args.pipeline)
    want_pipeline = args.pipeline or args.all or (not waiting and not args.comments)

    helper_errors = check_helpers()
    for e in helper_errors:
        print(f"ERROR: {e}")

    deadline = time.monotonic() + (args.wait_for_state_change_timeout_minutes or 0) * 60
    started = utc_now()
    probes = 0
    read_ever_succeeded = False
    while True:
        probes += 1
        any_change = False
        any_baseline = False
        # Every MR is probed at the same time, a few at once; the results are then handled in
        # the set's order, so the printing and the state advance stay sequential per MR.
        with ThreadPoolExecutor(max_workers=min(4, len(watched))) as pool:
            probed = list(pool.map(lambda w: _try_probe(w), watched))
        # Decide what every MR needs before fetching anything, so the dumps of the whole set
        # run in one pool; the blocks are then printed in the set's order as each MR's dumps land.
        plan: list[tuple[Any, ...]] = []
        for w, outcome in zip(watched, probed):
            if isinstance(outcome, GlabError):
                # A read failure does not end a wait: the token may come back, the host may
                # recover, and the other MRs in the set are still worth watching. Report it
                # once per MR per run so a nine-minute wait does not print it nine times.
                if not w.read_failure_reported:
                    ev = Event("READ_FAILED", f"probe failed: {outcome}")
                    print(f"== {w.label}")
                    print(f"  {ev.line()}")
                    sys.stdout.flush()
                    w.log_events([ev])
                    w.read_failure_reported = True
                continue
            snap = outcome
            w.read_failure_reported = False
            read_ever_succeeded = True
            events = diff_snapshots(w.last, snap)
            first = w.last is None
            # A wait can run for minutes and probe every MR every minute. Repeating the whole
            # block per probe buries the one probe that found something, so in wait mode an MR
            # that did not move stays silent and its scorecard goes out once, at the end.
            if waiting and not first and not events:
                w.commit(snap)
                continue
            ids = {e.id for e in events}
            fetch_c = want_comments if not waiting else ("NOTES_CHANGED" in ids)
            fetch_p = want_pipeline if not waiting else ("PIPELINE_CHANGED" in ids)
            if first and waiting:
                fetch_c = fetch_p = False
            details = Details()
            # The pipeline dump fetches every job trace and costs seconds. On a one-shot read
            # of a pipeline that did not move since the last dump, the dump on disk is current,
            # so reuse it unless --pipeline asked for a fresh one.
            existing_summary = w.sdir / "pipeline-summary.txt"
            if fetch_p and not waiting and not first and "PIPELINE_CHANGED" not in ids and not args.pipeline and existing_summary.exists():
                fetch_p = False
                details.pipeline_dir = str(w.sdir / "pipeline")
                details.pipeline_summary_file = str(existing_summary)
                details.notes.append("pipeline unchanged since the last dump, so the dump was reused; pass --pipeline to fetch it again")
            plan.append((w, snap, events, first, fetch_c, fetch_p, details))

        with ThreadPoolExecutor(max_workers=4) as pool:
            futures = {}
            for w, snap, events, first, fetch_c, fetch_p, details in plan:
                jobs = []
                if fetch_c:
                    jobs.append(pool.submit(fetch_discussions, w.url, details))
                if fetch_p:
                    jobs.append(pool.submit(fetch_pipeline, w.url, snap, w.sdir, details))
                futures[w.label] = jobs
            for w, snap, events, first, fetch_c, fetch_p, details in plan:
                for j in futures[w.label]:
                    j.result()
                print(f"== {w.label}")
                if first:
                    print("  baseline established (no earlier state for this MR)")
                    print_snapshot(snap)
                    any_baseline = True
                for ev in events:
                    print(f"  {ev.line()}")
                if not first and not events and not waiting:
                    print("  no change since the last run")
                    print_snapshot(snap)
                print_details(details)
                print(f"  scorecard: {scorecard(snap)}")
                sys.stdout.flush()
                if events:
                    w.log_events(events)
                    any_change = True
                w.commit(snap)
        sys.stdout.flush()

        if not waiting:
            if not read_ever_succeeded:
                print("result: nothing could be read; every MR failed (see the READ_FAILED lines above)")
                return EXIT_READ_FAILED
            print(f"state: {watched[0].sdir.parent.parent.parent if len(watched) > 1 else watched[0].sdir}")
            return EXIT_BASELINE if any_baseline and not any_change else EXIT_CHANGE
        # A change outranks a baseline: a set can hold both on the same probe, and the caller
        # has to hear about the change rather than be told the run was only a baseline.
        if any_change:
            print(f"result: change detected after {probes} probe(s) since {started}")
            return EXIT_CHANGE
        if any_baseline and probes == 1 and read_ever_succeeded:
            print(f"result: baseline established at {started}; run again to wait for changes")
            return EXIT_BASELINE
        # Never start a probe that the window cannot hold. A probe can pull a pipeline dump,
        # and one that begins near the deadline runs past the caller's own tool timeout.
        remaining = deadline - time.monotonic()
        if remaining < args.poll_interval_seconds:
            for w in watched:
                if w.last:
                    print(f"== {w.label}")
                    print(f"  scorecard: {scorecard(w.last)}")
            if not read_ever_succeeded:
                print(f"result: nothing could be read in {args.wait_for_state_change_timeout_minutes:g} minutes since {started}; every probe failed for every MR ({probes} probes)")
                return EXIT_READ_FAILED
            print(f"result: no change in {args.wait_for_state_change_timeout_minutes:g} minutes since {started} ({probes} probes)")
            return EXIT_TIMEOUT
        time.sleep(args.poll_interval_seconds)


if __name__ == "__main__":
    sys.exit(main())
