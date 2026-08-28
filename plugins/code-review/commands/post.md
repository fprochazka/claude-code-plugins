---
description: Post the existing code-review report to the current GitLab MR as inline diff comments + a summary comment
disable-model-invocation: true
---

# Post Code Review to MR

Post the code-review report from **this session** to the current GitLab merge request as a combination of inline diff comments (for findings anchored to specific file/line locations) and one standalone summary comment (for everything else plus the final verdict).

**This command only posts.** It does not re-run the review and it does not re-analyze the diff. If no review report exists in this session, stop and tell the user to run `/code-review:full` first.

## Phase 1 — Locate the report (in-session only)

The report must already exist in this session's conversation history, produced by an earlier `/code-review:full` run. Do NOT search the filesystem, do NOT re-derive findings from the diff, do NOT re-launch review agents.

- If you can see the report in the current session context → proceed.
- If you cannot → stop immediately and reply with:
  > No code-review report found in this session. Run `/code-review:full` first, then re-run `/code-review:post`.

Do not invent findings. Use only what the existing report says.

## Phase 2 — Load tooling

Before making any GitLab calls, invoke the `glab-discussion` skill to load its usage guidance for MR diff comments, replies, and standalone discussions.

If the skill is unavailable, stop and tell the user.

## Phase 3 — Identify the target MR

You should already know the MR from the `/code-review:full` context loaded earlier in this session. Use that MR. If the MR is ambiguous or missing, ask the user for the MR URL before posting anything.

## Phase 4 — Plan the comment placement

Group every finding from the report into exactly one of two buckets:

- **Inline diff comment** — the finding clearly points at a specific file (and ideally a specific line / hunk) in the MR diff.
- **Summary comment** — the finding is cross-cutting, architectural, about commit hygiene, about release/rollout, about something not visible in the diff, or otherwise has no good single anchor.

Every finding ends up exactly once — never both.

## Phase 5 — Fetch diff info per file (iteratively)

For each file that has at least one inline-bucket finding, run:

```
glab-discussion diff --file <path>
```

Do **not** dump the whole MR diff in one call — iterate per file. This keeps output focused and avoids overwhelming context.

From that output, extract the SHAs and line refs you need to anchor a diff note (base/head/start SHAs, old/new line numbers, position type). The `glab-discussion` skill documents the exact fields required by `glab-discussion write` for a diff note.

If a finding's intended line is not actually present in the diff (e.g. the agent flagged surrounding code that wasn't changed), move that finding to the **summary** bucket — do not post a diff comment on an unchanged line.

## Phase 6 — Post inline diff comments

For each inline finding, post one diff comment with `glab-discussion write`. Use a consistent body format so threads are easy to scan:

```
**[<severity>]** <short title>

<finding body — what's wrong, why it matters>

<suggested fix, if the report has one>

_confidence: <n>/100 · from `/code-review:full` (<agent-name>)_
```

- `<severity>` is one of `Blocking`, `Suggestion`, `Nitpick`, or `Positive` — mirror the section the finding came from in the report.
- One finding per thread. Do **not** batch multiple findings into one comment.
- Keep the body tight; the reviewer can expand if needed.
- Post threads sequentially (not in parallel) so failures are easy to diagnose and the MR doesn't get spammed if something goes wrong mid-run.

If a `glab-discussion write` call fails, stop, show the error, and ask the user how to proceed — do **not** silently skip and continue.

## Phase 7 — Post the summary comment

Post exactly **one** standalone (non-diff) comment on the MR via `glab-discussion write` (no file/line — a plain MR-level discussion). Structure:

```markdown
## Code review summary

<one-paragraph verdict — looks good / has issues / needs discussion>

### Blocking (not anchored to diff)
- ...

### Suggestions (not anchored to diff)
- ...

### Nitpicks (not anchored to diff)
- ...

### Positive notes
- ...

### Unresolved MR discussions
- <thread> — addressed / partially addressed / still open

### Coverage
- Agents run: <list>
- Agents skipped: <agent — one-line reason>, or "none"
- Findings dropped in validation: <n>, or "none"

### Verdict
<final call: approve, request changes, or needs discussion — and why>

_Generated from a `/code-review:full` report and posted via `/code-review:post`._
```

Only include sections that have content. Skip empty sections rather than printing "none". **Coverage is never empty** — at minimum it lists the agents that ran. Carry its lines straight from the report's Coverage section.

Inline-anchored findings live in the diff threads, not here — do not duplicate them in the summary.

## Phase 8 — Report back to the user

After posting, reply in the conversation with:

- Number of inline diff comments posted, grouped by severity
- A link / reference to the summary comment
- Any findings you intentionally moved from inline → summary because their line wasn't in the diff
- Any failures, if you stopped early
