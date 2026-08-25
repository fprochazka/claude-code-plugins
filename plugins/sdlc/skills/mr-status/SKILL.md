---
name: mr-status
description: Determine the review-and-merge status of one merge request or a set of them — draft, rebase, pipeline, approvals, AI-reviewer verdicts, human threads, and what actually blocks the merge. Use when asked "what is the status of MR X", "which MRs are ready to merge", "build the review queue overview", "is this MR green", "who still has to review this", or when a command needs the current review state before it acts. The sdlc and code-review commands invoke this skill by name.
trigger-keywords: mr status, merge request status, review queue, mr overview, is the mr ready, review state, what blocks the merge
---

# mr-status

Determine the review-and-merge status of one merge request, or of a set of them. Is it rebased, is CI green, who reviewed it, what is still unresolved, and what blocks the merge right now. Every value is read at run time from the host API and from the MR threads.

Load the **glab** skill and the **glab-discussion** skill before the first call. The command recipes live in [`references/gitlab-commands.md`](references/gitlab-commands.md). Read that file before running anything. One reference file per git host, so a `github-commands.md` can sit beside it later.

Prefer `glab-discussion read --dump` for all comment data. It writes one file per thread and it handles pagination. The raw discussions API is the fallback when that CLI is absent.

## The mistake this skill exists to prevent

**Read the latest summary verdict per reviewer, plus the count of currently unresolved threads. Never infer "this MR has problems" from the presence of historical finding notes.** A reviewer can post major findings on Monday, see them fixed on Tuesday, and post a clean summary on Wednesday. The old notes stay in the thread list forever. Counting them as live problems produces a false "found issues" status. Exactly two signals are authoritative: the newest summary verdict per reviewer, and the number of threads whose header says `Resolved: no`.

## Inputs

Normalize every MR reference to `<repo-path>!<iid>`:

- a full MR URL
- `repo!iid`
- a bare `!iid` — only when the caller gave a default repo, otherwise ask.

A set of MRs can span repos. One change often needs an MR in the service repo and another in a deployment or pipelines repo. Carry the host and the repo per MR. Never assume the current directory's repo.

## Per-MR data to collect

1. **Identity** — title, ticket reference from the branch name or the title, author, source and target branch, created and updated time.
2. **Draft** — yes or no.
3. **Rebased** — `diverged_commits_count` against the target branch: up to date, or behind by N. State that this is a snapshot. The target branch keeps moving.
4. **Mergeable** — `merge_status`, `has_conflicts`, `detailed_merge_status`. Say whether a clean rebase is possible or a conflict exists.
5. **Pipeline** — the latest result and which pipeline it belongs to, head or merge result. **The accepted-green set is `success` alone.** `canceled` is not green — nothing ran to completion and the job list shows no red, which is why people misread it. `manual` is an unfinished blocking gate. `skipped` means no pipeline ran for this head. `running` and `pending` are not evidence yet, so re-read instead of judging.
6. **Approvals** — who approved, and how many approvals are still required.
7. **Size** — added and removed lines, and the file count. A reader needs the scale of the change.
8. **AI reviewers** — one entry per reviewer found on the MR. See the next section.
9. **Human review** — did a real person open a thread or comment? Exclude every AI reviewer identity. **Separate reviewer threads from the MR author's own comments.** Authors post acceptance reports and self-notes, and those are not review. Count resolved and unresolved separately. Human approvals come from the approvals endpoint, not from the threads.
10. **Merge gate** — what blocks the merge right now: red CI, draft status, unresolved threads, conflicts, a missing approval, a blocking review. And **whose court the ball is in**: the author fixes, rebases or replies, or the reviewer reviews and approves.

Be economical. Filter threads by author and by resolved state before reading bodies. Read a full note only to get the verdict text out of it.

## AI reviewers — profile each one, assume nothing

An MR carries zero, one, or several AI reviewers, and they do not behave alike. Identify each reviewer present on the MR at hand, then derive its behavior from its own threads before reading any verdict. Answer five questions per reviewer.

1. **What does it post?** Inline finding threads, one summary comment, or both.
2. **How does it maintain the summary?** Updated in place, or re-posted once per pass. This decides where the latest verdict lives — the newest note by that author that carries a verdict, or the single edited note.
3. **Does it post non-verdict notes?** Some reviewers post an acknowledgement, or a "review skipped, no code change since the last pass" note after a rebase. Those are not verdicts. Walk back to the newest note that carries a real one.
4. **Does it read replies?** A reviewer that reads replies and interacts with threads turns an unresolved thread with a substantive human reply into an active dialogue, not a missed finding. A reviewer that does not read replies makes a reply worth nothing — the finding clears only when the code or the documentation changes and a human then resolves the thread. Getting this backwards either invents a blocker or hides one.
5. **How do you identify it?** By `author.name`, by the username, or by a `[BOT]` marker in the dump. **Record the exact string observed on this MR.** A service-account username can be an opaque hash, and the `author.bot` flag is not reliably set. Match on what you saw, never on what you expected.

### Persist the profile

Once a profile is derived, **propose a Claude memory that holds it** — one memory per reviewer identity, keyed by host plus author string. A later run then reads the profile instead of inferring it again.

If such a memory is already in context, use it, and verify it once against the newest note by that reviewer. If the memory and the MR disagree, report the disagreement and derive the profile again. Never keep a stale profile silently.

An illustrative profile block, with fictional values:

```
reviewer: @qa-review-bot   (host: git.example.com, author.name: "QA Review Bot")
posts: inline findings + one summary comment
summary: re-posted per pass — take the newest note that carries a verdict line
non-verdict notes: "review skipped, head unchanged" after a rebase
reads replies: no — a finding clears by a code change plus a manual resolve
verdict vocabulary: "Ready to merge" / "Needs work" / "No blocking findings"
```

The names, the verdict words and the behavior differ per reviewer. Copy nothing from this example into a report.

## Overview mode — a set of MRs

Run this mode as a subagent when the caller hands over a list. Write ONE consolidated Markdown file to:

```
<scratchpad>/mr-status/<scope-slug>-<YYYYMMDD-HHMM>.md
```

Create the directory first. `<scope-slug>` names the set, for example `review-queue` or `single-4711`. **Choose the path once and keep it.** On a resume, update the same file in place. Refresh the generated timestamp and the changed sections. A stable filename keeps the caller's link valid.

File shape:

- A short header: scope, generated timestamp, the absolute file path, and one line on how to refresh it.
- Then **one heading per MR, with all of that MR's data under it**, and nothing else. No overview table. The caller builds any roll-up it wants, so status lives in exactly one place and never gets maintained twice.
- Each heading carries the identifier and a short label, for example `## group/service!4711 — cache eviction on tenant delete`. Never a bare number.
- Under it, the same labeled fields for every MR: `author`, `draft`, `rebased`, `mergeable`, `pipeline`, `approvals`, `size`, one line per AI reviewer, `human review`, `merge-gate`. Add free detail lines only where a field needs them.

Keep the prose factual. State findings. Promise no future work.

### Resume contract

Reply to the caller with three things: the absolute file path, a one-paragraph summary with counts (ready, blocked, waiting on the author) that names every MR, and this instruction — **resume this subagent to refresh, rather than starting a new one.** The subagent keeps the MR list and updates the same file. A resume can also change scope: add MRs, drop MRs, or re-check a subset. Never silently start over.
