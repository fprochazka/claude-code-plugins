---
name: mr-status
description: Efficiently determine the review-and-merge status of one merge request or a set of them — draft, rebase, pipeline, approvals, AI-reviewer verdicts, human threads, what changed since the last read, and what actually blocks the merge. Use when asked "what is the status of MR X", "which MRs are ready to merge", "is this MR green", "who still has to review this", or when a command needs the current review state before it acts. The sdlc and code-review commands and the mr-watch agent invoke this skill by name.
trigger-keywords: mr status, merge request status, review queue, mr overview, is the mr ready, review state, what blocks the merge
allowed-tools: ["Bash(${CLAUDE_PLUGIN_ROOT}/scripts/mr-state.py:*)", "Bash(glab-discussion read:*)", "Bash(glab-pipeline inspect:*)", "Bash(glab api:*)", "Bash(glab mr view:*)", "Bash(git fetch:*)", "Bash(git rev-list:*)", "Bash(git diff:*)"]
---

# mr-status

One script reads a merge request; you judge it. `${CLAUDE_PLUGIN_ROOT}/scripts/mr-state.py` fetches the MR object, the newest note, approvals, the discussion dump, the pipeline dump and the external commit statuses, remembers what it saw, and prints what changed since the last run. This skill says how to run it, how to read what it prints, and the judgment calls the script cannot make. It covers GitLab, because it ships in the **glab** plugin.

The script needs `glab` (authenticated), [`glab-discussion`](https://github.com/fprochazka/glab-discussion) and [`glab-pipeline`](https://github.com/fprochazka/glab-pipeline). It runs without the last two, but then it cannot fetch threads or pipeline details, and it prints a `DEPENDENCY MISSING` line with the install command. When you see that line, relay it: tell the user which tool is missing, give the install command `uv tool install glab-discussion glab-pipeline`, and ask whether to install it. Do not work around it with raw API calls.

## Running the script

```bash
${CLAUDE_PLUGIN_ROOT}/scripts/mr-state.py                                  # the current branch's MR, full read
${CLAUDE_PLUGIN_ROOT}/scripts/mr-state.py --mr-url <url> [--mr-url <url>]  # a set, across repos and hosts
${CLAUDE_PLUGIN_ROOT}/scripts/mr-state.py --mr-url <url> --wait-for-state-change-timeout-minutes 9
```

- **Always identify an MR by its URL** when it is not the current branch's. A set can span repos and hosts, and `glab` outside a checkout falls back to its default host and returns a wrong answer instead of an error. The script carries the host from the URL on every call.
- **A full read** (no wait flag) fetches everything: `--all` is the default, `--comments` and `--pipeline` narrow it. The first read of an MR establishes a baseline and exits `4`; every later read prints the diff since the previous run and exits `0`.
- **The wait mode** probes every minute and exits the moment a change appears (exit `0`) or the timeout passes (exit `3`). Keep the timeout under your Bash tool's timeout, at most 8 minutes, since the script does not start a probe it could not finish inside the window. On a change it fetches only what the change needs: the discussion dump when a note moved, the pipeline dump when the pipeline moved. A probe is two API calls per MR, the MR object and the newest note, plus approvals when `updated_at` moved and the project's default branch once, so a set of five MRs costs about ten calls a minute.
- **State lives in `<tmp>/glab-state/<host>/<project>/mr-<iid>/`**: `state.json` (the last snapshot), `mr.json` (the raw MR object from the last probe), `events.log` (every change ever printed, UTC), `pipeline/` and `pipeline-summary.txt` after a pipeline fetch, `external-statuses.json`. The script prints the diff, flushes, and only then advances `state.json`, so a run killed in between reports the same change again next time. `--reset` forgets the state and starts a new baseline. The discussion dump is `glab-discussion`'s own, under `/tmp/glab-discussion/<host>/mr-<iid>/`, outside the state directory; `--reset` does not touch it.

## Reading the output

Per MR, the script prints a `== host/project!iid` header, then one line per change, then the detail paths, then a `scorecard:` line. Change lines carry a fixed id:

| Id | Meaning |
|---|---|
| `STATE_CHANGED` | opened, merged, closed, locked |
| `DRAFT_CHANGED` | draft or ready |
| `HEAD_CHANGED` | a push, with the full SHAs; "rebase likely" when the behind count dropped to zero at the same time |
| `TARGET_CHANGED`, `TITLE_CHANGED` | the target branch or the title changed; a target change means the MR was re-stacked |
| `PIPELINE_CHANGED` | a new pipeline or a status change; says when it ran on a superseded base |
| `BEHIND_CHANGED` | commits behind the target branch |
| `MERGE_STATUS_CHANGED` | mergeability or conflicts, transient values already filtered out |
| `NOTES_CHANGED` | a new note, or an edit or resolve of an existing one, with the author; on a count-only probe, the count or an unexplained `updated_at` |
| `DISCUSSIONS_RESOLVED_CHANGED` | the all-blocking-threads-resolved flag flipped |
| `REVIEWERS_CHANGED`, `ASSIGNEES_CHANGED`, `LABELS_CHANGED` | field diffs; reviewer assignment is visible only here, never as a note |
| `APPROVALS_CHANGED` | who approved, how many approvals are left |
| `READ_FAILED` | one MR could not be read this probe; the others were. In wait mode the script keeps probing, and exits `5` only when every probe in the window failed |

Then the details. `discussions:` names the dump directory, one `.txt` per thread, and lists the files the dump rewrote as `updated:`, `new:`, `deleted:`. The dump touches only threads whose newest note moved, so **read only the files it lists, or the files newer than your last pass**. `pipeline dump:` names the `glab-pipeline` directory and lists each failed job with its stage and reason; open only `job-logs/<failed-job>.log`, `test-report.json`, or `lint.json` when the summary points at them. `failed external status:` is a commit status posted by something outside the pipeline, with its URL.

A thread file starts with a header: `Discussion: <full id>`, `Type: General | DiffNote`, `File:` and `Line:` for a DiffNote, `Resolved: yes | no` only on a resolvable thread, then one `[<created_at>] @<username> [BOT] (note:<id>):` block per note. The file shows creation times only, so an edited note looks unchanged inside the file; the dump listing is what tells you it moved. **Refer to a thread by its full discussion id**, never a prefix: the CLI rejects prefixes.

## Judgment rules

**Green is `success` and nothing else.** `canceled` is not green: nothing ran to completion and the job list shows no red, which is why it gets misread. `manual` is an unfinished blocking gate. `skipped` means no pipeline ran for this head. `running` and `pending` are not evidence yet. A pipeline counts only when its SHA equals the MR head; the scorecard says `on an older head` otherwise. A red pipeline on a branch that is behind its target ran on a superseded base, so judge it again after the rebase.

**Profile every AI reviewer on the MR at hand, assume nothing.** Reviewers do not behave alike, and the vocabulary one uses means nothing to another. Before reading any verdict, answer six questions per reviewer from its own threads: what it posts (inline findings, one summary, both); how it maintains the summary (edited in place, or re-posted per pass) and therefore where the latest verdict lives; whether it posts non-verdict notes (an acknowledgement, "review skipped, head unchanged" after a rebase) that you must walk past; whether it reads replies, which decides if an unresolved thread with a substantive reply is an active dialogue or a finding that clears only through a code change plus a manual resolve; the exact author string observed on this MR, since a service account can be an opaque hash and the `[BOT]` marker is not reliably set; and whether the verdict names the commit it reviewed, so you can date it against the head. Read the vocabulary the same way: the words a reviewer uses for "mergeable", "nothing actionable but a human must still review", and "actionable findings open" are its own, and the middle one is the one everyone misreads.

**If a memory already holds a reviewer's profile, use it and verify it once** against that reviewer's newest note. If the memory and the MR disagree, report the disagreement and derive the profile again. Once you derive a profile, **propose a Claude memory** for it, one per reviewer identity keyed by host plus author string, so the next run reads it instead of inferring it again. An illustrative block, with fictional values:

```
reviewer: @qa-review-bot   (host: git.example.com, author.name: "QA Review Bot")
posts: inline findings + one summary comment
summary: edited in place — the last note of its General thread is the current verdict
non-verdict notes: "review skipped, head unchanged" after a rebase
reads replies: no — a finding clears by a code change plus a manual resolve
verdict names its head: yes — trailing "reviewed <short-sha>", compare it with the current head
verdict vocabulary: "Ready to merge" / "Needs work" / "No blocking findings"
```

**Read the latest verdict per reviewer, plus the count of currently unresolved threads. Never infer "this MR has problems" from historical finding notes.** A reviewer can post major findings on Monday, see them fixed on Tuesday, and post a clean summary on Wednesday; the old notes stay forever. A reviewer that edits its summary in place keeps the freshest verdict in one of the oldest thread files, so sort nothing by name. A verdict on a superseded head is stale evidence, not the current state.

**Separate human review from the author's own comments and from bots.** Take every author string from the threads and the MR's `author`, `assignees` and `reviewers` fields; never compute a slug. A human who only replies inside a bot's thread is often the most substantive reviewer on the MR, so count note authors across every thread, not only thread openers. An author's acceptance report is not review. A system note carrying a human's username ("changed this line in version N of the diff") is not a reply. Human approvals come from the approvals data, not from the threads, and an approval by an AI approver alone means the MR is still awaiting human approval.

**Then say what blocks the merge right now, and whose court the ball is in.** Red CI, draft, unresolved threads, conflicts, a missing approval, a blocking review. The author fixes, rebases or replies; the reviewer reviews and approves. State that every value is a snapshot: the target branch keeps moving.

## Reporting a set

When a caller hands over a list, write one Markdown file, one heading per MR with all of that MR's data under it, no overview table: `## <host>/<project>!<iid> — <short label>`, then `author`, `draft`, `rebased`, `mergeable`, `pipeline`, `approvals`, one line per AI reviewer, `human review`, `merge-gate`. Name every MR by its full identifier; an iid alone or an invented nickname is not an identifier. Keep it factual and promise no work.
