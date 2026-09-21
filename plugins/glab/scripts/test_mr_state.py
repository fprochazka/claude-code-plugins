"""Unit tests for the diff logic in mr-state.py. No network: every input is a literal snapshot."""

import importlib.util
import io
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest import mock

HERE = pathlib.Path(__file__).parent
spec = importlib.util.spec_from_file_location("mr_state", HERE / "mr-state.py")
mr_state = importlib.util.module_from_spec(spec)
sys.modules["mr_state"] = mr_state  # dataclasses resolve annotations through sys.modules
spec.loader.exec_module(mr_state)


def mr_object(**overrides):
    base = {
        "iid": 42,
        "web_url": "https://git.example.com/group/service/-/merge_requests/42",
        "title": "Add thing",
        "author": {"username": "jane"},
        "state": "opened",
        "draft": True,
        "sha": "aaaaaaaa1111",
        "source_branch": "jd/T-1-thing",
        "target_branch": "master",
        "diverged_commits_count": 0,
        "rebase_in_progress": False,
        "merge_status": "can_be_merged",
        "detailed_merge_status": "mergeable",
        "has_conflicts": False,
        "blocking_discussions_resolved": True,
        "assignees": [{"username": "jane"}],
        "reviewers": [],
        "labels": [],
        "user_notes_count": 3,
        "updated_at": "2026-09-21T10:00:00.000Z",
        "head_pipeline": {"id": 100, "status": "success", "sha": "aaaaaaaa1111", "web_url": "u", "created_at": "c", "updated_at": "u"},
    }
    base.update(overrides)
    return base


def snap(**overrides):
    s = mr_state.snapshot_from_mr(mr_object(**overrides), "git.example.com", "group/service")
    s["newest_note"] = {"id": 7, "updated_at": "2026-09-21T09:00:00.000Z", "author": "bot", "system": False}
    s["notes_probe"] = "exact"
    s["approvals"] = {"approved_by": [], "approvals_left": 1, "approved": False}
    return s


def ids(events):
    return [e.id for e in events]


class ParseUrl(unittest.TestCase):
    def test_parses_nested_group_and_trailing_parts(self):
        self.assertEqual(mr_state.parse_mr_url("https://git.example.com/a/b/c/-/merge_requests/7/diffs?x=1"), ("git.example.com", "a/b/c", 7))

    def test_rejects_note_link_to_issue(self):
        with self.assertRaises(ValueError):
            mr_state.parse_mr_url("https://git.example.com/a/b/-/issues/7")

    def test_state_dir_is_keyed_by_project(self):
        a = mr_state.state_dir_for("h", "g/one", 5, pathlib.Path("/x"))
        b = mr_state.state_dir_for("h", "g/two", 5, pathlib.Path("/x"))
        self.assertNotEqual(a, b)
        self.assertEqual(a, pathlib.Path("/x/h/g__one/mr-5"))


class Diff(unittest.TestCase):
    def test_no_events_without_baseline(self):
        self.assertEqual(mr_state.diff_snapshots(None, snap()), [])

    def test_identical_snapshots_yield_nothing(self):
        self.assertEqual(mr_state.diff_snapshots(snap(), snap()), [])

    def test_draft_and_state(self):
        ev = mr_state.diff_snapshots(snap(), snap(draft=False, state="merged"))
        self.assertEqual(ids(ev), ["STATE_CHANGED", "DRAFT_CHANGED"])

    def test_pipeline_status_change_same_id(self):
        new = snap(head_pipeline={"id": 100, "status": "failed", "sha": "aaaaaaaa1111"})
        ev = mr_state.diff_snapshots(snap(), new)
        self.assertEqual(ids(ev), ["PIPELINE_CHANGED"])
        self.assertIn("success -> failed", ev[0].detail)

    def test_new_pipeline_on_new_head_names_both(self):
        new = snap(sha="bbbbbbbb2222", head_pipeline={"id": 101, "status": "running", "sha": "bbbbbbbb2222"})
        ev = mr_state.diff_snapshots(snap(), new)
        self.assertEqual(ids(ev), ["HEAD_CHANGED", "PIPELINE_CHANGED"])
        self.assertIn("new pipeline 101", ev[1].detail)

    def test_failed_while_behind_is_called_out(self):
        new = snap(diverged_commits_count=4, head_pipeline={"id": 100, "status": "failed", "sha": "aaaaaaaa1111"})
        ev = mr_state.diff_snapshots(snap(), new)
        pipe = next(e for e in ev if e.id == "PIPELINE_CHANGED")
        self.assertIn("superseded base", pipe.detail)
        self.assertIn("BEHIND_CHANGED", ids(ev))

    def test_head_change_with_divergence_drop_hints_rebase(self):
        old = snap(diverged_commits_count=3)
        new = snap(sha="bbbbbbbb2222", diverged_commits_count=0)
        ev = mr_state.diff_snapshots(old, new)
        head = next(e for e in ev if e.id == "HEAD_CHANGED")
        self.assertIn("rebase likely", head.detail)

    def test_transient_merge_status_is_not_a_change(self):
        new = snap(merge_status="checking", detailed_merge_status="checking")
        self.assertEqual(mr_state.diff_snapshots(snap(), new), [])

    def test_rebase_in_progress_holds_divergence_and_conflicts(self):
        new = snap(rebase_in_progress=True, diverged_commits_count=9, has_conflicts=True)
        self.assertEqual(mr_state.diff_snapshots(snap(), new), [])

    def test_note_edit_same_id_is_reported_as_edit(self):
        new = snap()
        new["newest_note"] = {"id": 7, "updated_at": "2026-09-21T09:30:00.000Z", "author": "bot", "system": False}
        ev = mr_state.diff_snapshots(snap(), new)
        self.assertEqual(ids(ev), ["NOTES_CHANGED"])
        self.assertIn("edited or resolved", ev[0].detail)

    def test_new_note_is_reported_with_author(self):
        new = snap()
        new["newest_note"] = {"id": 8, "updated_at": "2026-09-21T09:30:00.000Z", "author": "alice", "system": False}
        ev = mr_state.diff_snapshots(snap(), new)
        self.assertIn("new note by @alice", ev[0].detail)

    def test_exact_probe_still_notices_a_deleted_note(self):
        # A note further down the list is deleted: the count drops, the newest note by
        # updated_at is untouched, and the exact comparison alone would report nothing.
        ev = mr_state.diff_snapshots(snap(), snap(user_notes_count=2))
        self.assertEqual(ids(ev), ["NOTES_CHANGED"])
        self.assertIn("newest note stayed the same", ev[0].detail)

    def test_exact_probe_does_not_double_report_a_new_note(self):
        new = snap(user_notes_count=4)
        new["newest_note"] = {"id": 8, "updated_at": "2026-09-21T09:30:00.000Z", "author": "alice", "system": False}
        ev = mr_state.diff_snapshots(snap(), new)
        self.assertEqual(ids(ev), ["NOTES_CHANGED"])
        self.assertIn("new note by @alice", ev[0].detail)

    def test_count_only_probe_uses_count_then_updated_at(self):
        old, new = snap(), snap(user_notes_count=4)
        old["notes_probe"] = new["notes_probe"] = "count-only"
        old["newest_note"] = new["newest_note"] = None
        self.assertEqual(ids(mr_state.diff_snapshots(old, new)), ["NOTES_CHANGED"])
        new2 = snap(updated_at="2026-09-21T11:00:00.000Z")
        new2["notes_probe"], new2["newest_note"] = "count-only", None
        ev = mr_state.diff_snapshots(old, new2)
        self.assertEqual(ids(ev), ["NOTES_CHANGED"])
        self.assertIn("no other field explaining it", ev[0].detail)

    def test_count_only_probe_does_not_blame_notes_for_a_reviewer_assignment(self):
        # Assigning a reviewer bumps updated_at. "Explained" used to cover only state, draft,
        # head, target and title, so this arrived as a note that nobody had written.
        old = snap()
        old["notes_probe"], old["newest_note"] = "count-only", None
        new = snap(reviewers=[{"username": "bob"}], updated_at="2026-09-21T11:00:00.000Z")
        new["notes_probe"], new["newest_note"] = "count-only", None
        self.assertEqual(ids(mr_state.diff_snapshots(old, new)), ["REVIEWERS_CHANGED"])

    def test_count_only_probe_does_not_blame_notes_for_a_label_or_merge_status_move(self):
        old = snap()
        old["notes_probe"], old["newest_note"] = "count-only", None
        new = snap(labels=["blocked"], has_conflicts=True, updated_at="2026-09-21T11:00:00.000Z")
        new["notes_probe"], new["newest_note"] = "count-only", None
        self.assertNotIn("NOTES_CHANGED", ids(mr_state.diff_snapshots(old, new)))

    def test_count_only_probe_still_blames_notes_when_nothing_else_moved(self):
        old = snap()
        old["notes_probe"], old["newest_note"] = "count-only", None
        new = snap(updated_at="2026-09-21T11:00:00.000Z")
        new["notes_probe"], new["newest_note"] = "count-only", None
        self.assertEqual(ids(mr_state.diff_snapshots(old, new)), ["NOTES_CHANGED"])

    def test_a_deleted_newest_note_is_not_reported_as_a_new_one(self):
        # The newest note is deleted, so an older note becomes the newest: a different id with
        # an earlier timestamp. Calling that "new note by @x" sends the reader to a fresh
        # comment that was never written.
        new = snap()
        new["newest_note"] = {"id": 5, "updated_at": "2026-09-21T08:00:00.000Z", "author": "bot", "system": False}
        ev = mr_state.diff_snapshots(snap(), new)
        self.assertEqual(ids(ev), ["NOTES_CHANGED"])
        self.assertIn("newest note deleted", ev[0].detail)

    def test_head_changed_names_the_full_shas(self):
        old = snap(sha="1111111111111111111111111111111111111111")
        new = snap(sha="2222222222222222222222222222222222222222")
        head = next(e for e in mr_state.diff_snapshots(old, new) if e.id == "HEAD_CHANGED")
        self.assertIn("1111111111111111111111111111111111111111 -> 2222222222222222222222222222222222222222", head.detail)

    def test_unavailable_approvals_never_produce_an_approvals_event(self):
        old, new = snap(), snap()
        old["approvals"] = dict(mr_state.APPROVALS_UNAVAILABLE)
        new["approvals"] = {"approved_by": ["carol"], "approvals_left": 0, "approved": True}
        self.assertNotIn("APPROVALS_CHANGED", ids(mr_state.diff_snapshots(old, new)))

    def test_count_only_probe_does_not_blame_notes_for_a_push(self):
        old = snap()
        old["notes_probe"], old["newest_note"] = "count-only", None
        new = snap(sha="bbbbbbbb2222", updated_at="2026-09-21T11:00:00.000Z", head_pipeline=None)
        new["notes_probe"], new["newest_note"] = "count-only", None
        self.assertNotIn("NOTES_CHANGED", ids(mr_state.diff_snapshots(old, new)))

    def test_reviewers_labels_approvals(self):
        new = snap(reviewers=[{"username": "bob"}], labels=["blocked"])
        new["approvals"] = {"approved_by": ["carol"], "approvals_left": 0, "approved": True}
        ev = mr_state.diff_snapshots(snap(), new)
        self.assertEqual(ids(ev), ["REVIEWERS_CHANGED", "LABELS_CHANGED", "APPROVALS_CHANGED"])
        self.assertIn("added ['bob']", ev[0].detail)
        self.assertIn("+['carol']", ev[2].detail)

    def test_settle_keeps_last_settled_merge_status(self):
        settled = mr_state.settle(snap(), snap(merge_status="checking"))
        self.assertEqual(settled["merge_status"], "can_be_merged")

    def test_first_read_records_a_transient_merge_status_verbatim(self):
        # There is no settled value to fall back on, so the baseline stores what the host said.
        settled = mr_state.settle(None, snap(merge_status="checking", detailed_merge_status="checking"))
        self.assertEqual(settled["merge_status"], "checking")
        self.assertEqual(settled["detailed_merge_status"], "checking")

    def test_a_settled_value_after_checking_is_reported(self):
        old = snap(merge_status="checking", detailed_merge_status="checking")
        ev = mr_state.diff_snapshots(old, snap(merge_status="cannot_be_merged", detailed_merge_status="not_approved"))
        self.assertEqual(ids(ev), ["MERGE_STATUS_CHANGED"])


class Scorecard(unittest.TestCase):
    def test_stacked_when_target_is_not_default(self):
        s = snap(target_branch="feature/base")
        s["default_branch"] = "master"
        self.assertIn("stacked on feature/base", mr_state.scorecard(s))

    def test_older_head_flag(self):
        s = snap(sha="bbbbbbbb2222")
        self.assertIn("older head", mr_state.scorecard(s))

    def test_unavailable_approvals_are_not_rendered_as_nobody_approved(self):
        s = snap()
        s["approvals"] = None
        self.assertIn("approved by ?", mr_state.scorecard(s))
        s["approvals"] = dict(mr_state.APPROVALS_UNAVAILABLE)
        self.assertIn("approved by ?", mr_state.scorecard(s))
        s["approvals"] = {"approved_by": [], "approvals_left": 1, "approved": False}
        self.assertIn("approved by -", mr_state.scorecard(s))


def status(name, *, pipeline_id=None, state="success"):
    return {"name": name, "status": state, "pipeline_id": pipeline_id}


class ExternalStatuses(unittest.TestCase):
    """A commit status the head pipeline produced is not an external status."""

    def test_pipeline_id_excludes_the_pipelines_own_statuses(self):
        rows = [status("build", pipeline_id=7), status("gate", pipeline_id=None)]
        self.assertEqual(mr_state.external_statuses(rows, 7, set()), [rows[1]])

    def test_trigger_jobs_are_excluded_even_though_jobs_json_omits_them(self):
        # Trigger jobs live in bridges.json, never in jobs.json. Filtering on jobs.json alone
        # turned every one of them into an external status, and a failed one into a fake alert.
        rows = [status("release-to-test: [a]", pipeline_id=None, state="failed"), status("gate", pipeline_id=None)]
        kept = mr_state.external_statuses(rows, 7, {"build", "release-to-test: [a]"})
        self.assertEqual(kept, [rows[1]])

    def test_a_status_from_an_older_pipeline_on_the_same_commit_is_external(self):
        rows = [status("build", pipeline_id=6)]
        self.assertEqual(mr_state.external_statuses(rows, 7, set()), rows)

    def test_job_names_union_jobs_and_bridges(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = pathlib.Path(tmp)
            (p / "jobs.json").write_text(json.dumps([{"name": "build"}, {"name": "test"}]))
            (p / "bridges.json").write_text(json.dumps([{"name": "trigger"}]))
            self.assertEqual(mr_state.pipeline_job_names(p), {"build", "test", "trigger"})

    def test_job_names_tolerate_a_missing_or_broken_dump(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = pathlib.Path(tmp)
            (p / "jobs.json").write_text("{ not json")
            self.assertEqual(mr_state.pipeline_job_names(p), set())


def completed(returncode, stdout="", stderr=""):
    return subprocess.CompletedProcess(args=["glab"], returncode=returncode, stdout=stdout, stderr=stderr)


def no_backoff():
    """Let a retrying call run its full course without sleeping through the backoff."""
    return mock.patch.object(mr_state.time, "sleep", lambda *_: None)


class GlabApi(unittest.TestCase):
    def test_a_control_character_in_a_description_still_parses(self):
        body = '{"iid": 1, "description": "line\x07one"}'
        with mock.patch.object(mr_state.subprocess, "run", return_value=completed(0, body)):
            self.assertEqual(mr_state.glab_api("h", "p")["description"], "line\x07one")

    def test_paginate_merges_the_one_array_per_page_that_glab_prints(self):
        body = '[{"id": 1}, {"id": 2}]\n[{"id": 3}]\n'
        with mock.patch.object(mr_state.subprocess, "run", return_value=completed(0, body)):
            self.assertEqual([r["id"] for r in mr_state.glab_api("h", "p", paginate=True)], [1, 2, 3])

    def test_unparsable_output_fails_at_once_instead_of_retrying(self):
        with mock.patch.object(mr_state.subprocess, "run", return_value=completed(0, "<html>gateway</html>")) as run:
            with self.assertRaises(mr_state.GlabError):
                mr_state.glab_api("h", "p")
        self.assertEqual(run.call_count, 1)

    def test_a_404_is_refused_not_retried(self):
        with mock.patch.object(mr_state.subprocess, "run", return_value=completed(1, "", "glab: 404 Not found (HTTP 404)")) as run:
            with self.assertRaises(mr_state.RefusedError):
                mr_state.glab_api("h", "p")
        self.assertEqual(run.call_count, 1)

    def test_a_401_and_a_403_are_refused_not_retried(self):
        for err in ("glab: 401 Unauthorized (HTTP 401)", "glab: 403 Forbidden (HTTP 403)"):
            with mock.patch.object(mr_state.subprocess, "run", return_value=completed(1, "", err)) as run:
                with self.assertRaises(mr_state.RefusedError):
                    mr_state.glab_api("h", "p")
            self.assertEqual(run.call_count, 1, err)

    def test_a_connection_refused_is_retried_not_classified_as_a_refusal(self):
        # "refused" as a substring used to end the run; a dropped connection is transient.
        with no_backoff(), mock.patch.object(mr_state.subprocess, "run", return_value=completed(1, "", "dial tcp: connection refused")) as run:
            with self.assertRaises(mr_state.GlabError) as raised:
                mr_state.glab_api("h", "p")
        self.assertNotIsInstance(raised.exception, mr_state.RefusedError)
        self.assertEqual(run.call_count, mr_state.MAX_RETRIES)

    def test_a_gateway_error_is_retried(self):
        with no_backoff(), mock.patch.object(mr_state.subprocess, "run", return_value=completed(1, "", "502 Bad Gateway")) as run:
            with self.assertRaises(mr_state.GlabError):
                mr_state.glab_api("h", "p")
        self.assertEqual(run.call_count, mr_state.MAX_RETRIES)

    def test_a_code_embedded_in_a_longer_number_is_not_a_refusal(self):
        with no_backoff(), mock.patch.object(mr_state.subprocess, "run", return_value=completed(1, "", "request id 40401 failed")) as run:
            with self.assertRaises(mr_state.GlabError) as raised:
                mr_state.glab_api("h", "p")
        self.assertNotIsInstance(raised.exception, mr_state.RefusedError)
        self.assertEqual(run.call_count, mr_state.MAX_RETRIES)

    def test_a_refused_notes_probe_degrades_to_count_only(self):
        with mock.patch.object(mr_state.subprocess, "run", return_value=completed(1, "", "glab: 403 Forbidden (HTTP 403)")):
            note, mode = mr_state.probe_notes("h", "g%2Fs", 1)
        self.assertIsNone(note)
        self.assertEqual(mode, "count-only")

    def test_a_policy_wrapper_without_an_http_code_degrades_after_a_single_attempt(self):
        # No HTTP code means the classifier cannot call it a refusal, so without a one-attempt
        # cap this endpoint would burn the whole backoff on every probe of a wait.
        with mock.patch.object(mr_state.subprocess, "run", return_value=completed(1, "", "reading notes via glab is blocked")) as run:
            note, mode = mr_state.probe_notes("h", "g%2Fs", 1)
        self.assertIsNone(note)
        self.assertEqual(mode, "count-only")
        self.assertEqual(run.call_count, 1)

    def test_an_empty_notes_page_is_an_exact_probe_with_no_note(self):
        with mock.patch.object(mr_state.subprocess, "run", return_value=completed(0, "[]")):
            self.assertEqual(mr_state.probe_notes("h", "g%2Fs", 1), (None, "exact"))

    def test_approvals_shape_reads_the_nested_user(self):
        body = json.dumps({"approved_by": [{"user": {"username": "carol"}}], "approvals_left": 0, "approved": True})
        with mock.patch.object(mr_state.subprocess, "run", return_value=completed(0, body)):
            self.assertEqual(mr_state.probe_approvals("h", "g%2Fs", 1), {"approved_by": ["carol"], "approvals_left": 0, "approved": True})

    def test_refused_approvals_return_the_unavailable_sentinel(self):
        # None would mean "never probed" and make the next run probe again every minute.
        with mock.patch.object(mr_state.subprocess, "run", return_value=completed(1, "", "glab: 403 Forbidden (HTTP 403)")):
            self.assertEqual(mr_state.probe_approvals("h", "g%2Fs", 1), {"unavailable": True})


class CurrentBranch(unittest.TestCase):
    def resolve(self, proc):
        # git rev-parse succeeds, glab mr view returns proc.
        with mock.patch.object(mr_state.subprocess, "run", side_effect=[completed(0, ".git"), proc, completed(0, "master\n")]):
            with self.assertRaises(SystemExit) as raised:
                mr_state.resolve_current_branch_mr()
        return raised.exception.code

    def test_glabs_capitalised_no_open_mr_message_still_gets_the_guidance(self):
        # glab writes it with a capital N; a case-sensitive match printed its raw error instead.
        err = 'ERROR\n\n  No open merge request available for "master".'
        buf = io.StringIO()
        with redirect_stdout(buf):
            with mock.patch.object(mr_state.sys, "stderr", buf):
                code = self.resolve(completed(1, "", err))
        self.assertEqual(code, mr_state.EXIT_FATAL)
        self.assertIn("push the branch and open one", buf.getvalue())

    def test_a_readable_mr_yields_its_web_url(self):
        body = json.dumps({"web_url": "https://git.example.com/group/service/-/merge_requests/42"})
        with mock.patch.object(mr_state.subprocess, "run", side_effect=[completed(0, ".git"), completed(0, body)]):
            self.assertEqual(mr_state.resolve_current_branch_mr(), "https://git.example.com/group/service/-/merge_requests/42")


class DiscussionSummary(unittest.TestCase):
    def render(self, summary):
        d = mr_state.Details(discussions_dir="/d", discussions_summary=summary)
        buf = io.StringIO()
        with redirect_stdout(buf):
            mr_state.print_details(d)
        return buf.getvalue()

    def test_changed_files_are_listed(self):
        out = self.render("Discussions: /d/\n  updated: a.txt\n  new: b.txt\n  deleted: c.txt\n  (3 discussions up to date)")
        for line in ("updated: a.txt", "new: b.txt", "deleted: c.txt"):
            self.assertIn(line, out)

    def test_an_unchanged_dump_reports_its_last_line(self):
        self.assertIn("(5 discussions up to date)", self.render("Discussions: /d/\n  (5 discussions up to date)"))

    def test_a_header_only_summary_is_not_echoed_as_a_change(self):
        self.assertNotIn("    Discussions: /d/", self.render("Discussions: /d/"))


class StateFile(unittest.TestCase):
    def test_commit_writes_settled_snapshot_atomically(self):
        with tempfile.TemporaryDirectory() as tmp:
            w = mr_state.Watched("https://git.example.com/g/s/-/merge_requests/1", "git.example.com", "g/s", 1, pathlib.Path(tmp) / "mr-1")
            self.assertIsNone(w.last)
            w.commit(snap())
            w.commit(snap(merge_status="checking"))
            saved = json.loads((pathlib.Path(tmp) / "mr-1" / "state.json").read_text())
            self.assertEqual(saved["snapshot"]["merge_status"], "can_be_merged")
            self.assertFalse((pathlib.Path(tmp) / "mr-1" / "state.json.tmp").exists())
            reloaded = mr_state.Watched(w.url, w.host, w.project_path, w.iid, w.sdir)
            self.assertEqual(reloaded.last["sha"], "aaaaaaaa1111")

    def test_events_log_exists_from_the_baseline_run(self):
        # The skill documents events.log as one of the files of a watched MR, so the path has
        # to be there before the first change, not only after one.
        with tempfile.TemporaryDirectory() as tmp:
            mr_state.Watched("https://git.example.com/g/s/-/merge_requests/1", "git.example.com", "g/s", 1, pathlib.Path(tmp) / "mr-1")
            self.assertTrue((pathlib.Path(tmp) / "mr-1" / "events.log").exists())

    def test_a_corrupt_state_file_starts_a_new_baseline_instead_of_crashing(self):
        with tempfile.TemporaryDirectory() as tmp:
            sdir = pathlib.Path(tmp) / "mr-1"
            sdir.mkdir(parents=True)
            (sdir / "state.json").write_text("{truncated")
            w = mr_state.Watched("https://git.example.com/g/s/-/merge_requests/1", "git.example.com", "g/s", 1, sdir)
            self.assertIsNone(w.last)


class NotesProbeDegradation(unittest.TestCase):
    """A refused notes endpoint is asked once per run, not once per probe."""

    def watched(self, tmp):
        w = mr_state.Watched("https://git.example.com/g/s/-/merge_requests/1", "git.example.com", "g/s", 1, pathlib.Path(tmp) / "mr-1")
        w.default_branch = "master"
        return w

    def probe_twice(self, notes_result):
        with tempfile.TemporaryDirectory() as tmp:
            w = self.watched(tmp)
            with mock.patch.object(mr_state, "glab_api", return_value=mr_object()), \
                 mock.patch.object(mr_state, "probe_notes", return_value=notes_result) as notes, \
                 mock.patch.object(mr_state, "probe_approvals", return_value={"approved_by": [], "approvals_left": 1, "approved": False}):
                first = w.probe()
                w.commit(first)
                second = w.probe()
            return first, second, notes

    def test_a_refused_notes_probe_is_not_attempted_again_within_the_run(self):
        first, second, notes = self.probe_twice((None, "count-only"))
        self.assertEqual(notes.call_count, 1)
        for snap in (first, second):
            self.assertEqual(snap["notes_probe"], "count-only")
            self.assertIsNone(snap["newest_note"])

    def test_a_working_notes_probe_keeps_being_used(self):
        note = {"id": 7, "updated_at": "2026-09-21T09:00:00.000Z", "author": "bot", "system": False}
        first, second, notes = self.probe_twice((note, "exact"))
        self.assertEqual(notes.call_count, 2)
        self.assertEqual(second["notes_probe"], "exact")

    def test_an_mr_with_no_notes_at_all_is_not_treated_as_a_refusal(self):
        _, _, notes = self.probe_twice((None, "exact"))
        self.assertEqual(notes.call_count, 2)

    def test_a_fresh_run_asks_the_endpoint_again(self):
        # The flag lives on the Watched object, so the next process starts by asking once more.
        with tempfile.TemporaryDirectory() as tmp:
            w = self.watched(tmp)
            w.notes_refused = True
            self.assertFalse(self.watched(tmp).notes_refused)


class ApprovalsProbe(unittest.TestCase):
    """The approvals endpoint is only worth asking again when the MR itself moved."""

    def probe_once(self, last, mr_updated_at):
        with tempfile.TemporaryDirectory() as tmp:
            w = mr_state.Watched("https://git.example.com/g/s/-/merge_requests/1", "git.example.com", "g/s", 1, pathlib.Path(tmp) / "mr-1")
            w.last = last
            w.default_branch = "master"
            mr = mr_object(updated_at=mr_updated_at)
            with mock.patch.object(mr_state, "glab_api", return_value=mr), \
                 mock.patch.object(mr_state, "probe_notes", return_value=(None, "count-only")), \
                 mock.patch.object(mr_state, "probe_approvals", return_value={"approved_by": ["carol"], "approvals_left": 0, "approved": True}) as approvals:
                snap = w.probe()
            return snap, approvals

    def test_a_refused_endpoint_is_not_asked_again_while_the_mr_stands_still(self):
        last = {"updated_at": "2026-09-21T10:00:00.000Z", "approvals": dict(mr_state.APPROVALS_UNAVAILABLE)}
        snap, approvals = self.probe_once(last, "2026-09-21T10:00:00.000Z")
        approvals.assert_not_called()
        self.assertEqual(snap["approvals"], {"unavailable": True})

    def test_a_moved_updated_at_asks_again(self):
        last = {"updated_at": "2026-09-21T10:00:00.000Z", "approvals": dict(mr_state.APPROVALS_UNAVAILABLE)}
        snap, approvals = self.probe_once(last, "2026-09-21T11:00:00.000Z")
        approvals.assert_called_once()
        self.assertEqual(snap["approvals"]["approved_by"], ["carol"])

    def test_approvals_never_read_are_read_once(self):
        last = {"updated_at": "2026-09-21T10:00:00.000Z", "approvals": None}
        _, approvals = self.probe_once(last, "2026-09-21T10:00:00.000Z")
        approvals.assert_called_once()


def clock(*values):
    """A monotonic clock that hands out these readings in order, then repeats the last."""
    seq = list(values)

    def tick():
        return seq.pop(0) if len(seq) > 1 else seq[0]

    return tick


class MainLoop(unittest.TestCase):
    URL = "https://git.example.com/group/service/-/merge_requests/42"

    def run_main(self, extra, probe_side_effect, monotonic=None, seed=None):
        with tempfile.TemporaryDirectory() as tmp:
            sdir = mr_state.state_dir_for("git.example.com", "group/service", 42, pathlib.Path(tmp))
            if seed is not None:
                sdir.mkdir(parents=True, exist_ok=True)
                (sdir / "state.json").write_text(json.dumps({"snapshot": seed, "default_branch": "master"}))
            argv = ["--mr-url", self.URL, "--state-dir", tmp] + extra
            buf = io.StringIO()
            with mock.patch.object(mr_state, "which", lambda _: True), \
                 mock.patch.object(mr_state, "fetch_discussions", lambda *a, **k: None), \
                 mock.patch.object(mr_state, "fetch_pipeline", lambda *a, **k: None), \
                 mock.patch.object(mr_state.time, "sleep", lambda *_: None), \
                 mock.patch.object(mr_state.Watched, "probe", side_effect=probe_side_effect, autospec=True) as probe:
                stack = mock.patch.object(mr_state.time, "monotonic", monotonic) if monotonic else None
                if stack:
                    stack.start()
                try:
                    with redirect_stdout(buf):
                        code = mr_state.main(argv)
                finally:
                    if stack:
                        stack.stop()
            return code, buf.getvalue(), probe

    def test_a_one_shot_run_where_every_mr_failed_exits_five(self):
        code, out, _ = self.run_main([], mr_state.GlabError("boom"))
        self.assertEqual(code, mr_state.EXIT_READ_FAILED)
        self.assertIn("READ_FAILED", out)

    def test_a_one_shot_run_that_read_something_keeps_its_normal_code(self):
        code, _, _ = self.run_main([], lambda _self: snap())
        self.assertEqual(code, mr_state.EXIT_BASELINE)

    def test_a_wait_keeps_probing_through_read_failures_and_reports_each_mr_once(self):
        # A failed read is not a reason to stop watching: the token may come back, and the
        # caller used to get exit 0 on the first failure and loop straight back onto the host.
        code, out, probe = self.run_main(
            ["--wait-for-state-change-timeout-minutes", "2", "--poll-interval-seconds", "30"],
            mr_state.GlabError("boom"),
            monotonic=clock(0, 30, 60, 90, 150),
        )
        self.assertEqual(code, mr_state.EXIT_READ_FAILED)
        self.assertEqual(probe.call_count, 4)
        self.assertEqual(out.count("READ_FAILED"), 1)

    def test_a_wait_does_not_start_a_probe_the_window_cannot_hold(self):
        # Readings 50 and 100 leave 20 s of a 120 s window: less than the 30 s interval, so
        # the run stops at two probes rather than starting a third that would overrun.
        code, out, probe = self.run_main(
            ["--wait-for-state-change-timeout-minutes", "2", "--poll-interval-seconds", "30"],
            lambda _self: snap(),
            monotonic=clock(0, 50, 100),
            seed=snap(),
        )
        self.assertEqual(code, mr_state.EXIT_TIMEOUT)
        self.assertEqual(probe.call_count, 2)
        self.assertIn("scorecard:", out)

    def test_a_wait_that_finds_a_change_still_exits_zero(self):
        code, out, _ = self.run_main(
            ["--wait-for-state-change-timeout-minutes", "2", "--poll-interval-seconds", "30"],
            lambda _self: snap(state="merged"),
            monotonic=clock(0, 50, 100),
            seed=snap(),
        )
        self.assertEqual(code, mr_state.EXIT_CHANGE)
        self.assertIn("STATE_CHANGED", out)

    def test_detail_flags_are_rejected_in_wait_mode(self):
        for flag in ("--all", "--comments", "--pipeline"):
            with self.assertRaises(SystemExit) as raised:
                with redirect_stdout(io.StringIO()), mock.patch.object(mr_state.sys, "stderr", io.StringIO()):
                    mr_state.main(["--mr-url", self.URL, "--wait-for-state-change-timeout-minutes", "2", flag])
            self.assertEqual(raised.exception.code, 2, flag)


if __name__ == "__main__":
    sys.exit(unittest.main())
