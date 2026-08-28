---
description: Full multi-agent code review of current branch — context, exploration, parallel review, validation
argument-hint: [focus area or specific concerns]
disable-model-invocation: true
---

# Review Current Branch

Perform a thorough, context-aware code review of all changes on the current branch compared to its base branch.

$ARGUMENTS

## Phase 1 — Load Context (main thread, no subagents)

Do all of this BEFORE forming any opinions. You need full context first. Everything in this phase stays in your main context window — do NOT delegate to subagents.

### 1.1 Merge/Pull Request Context (do this FIRST)

**You MUST load MR/PR context first** — it contains the target branch, which determines the correct diff range. Do NOT run any git diff or git log commands until you know the target branch.

If the project uses a code hosting platform with MR/PR workflows, load the MR/PR context:
- Description, **target branch**, labels
- All comment threads (resolved and unresolved) — pay close attention to **unresolved threads**, reviewers may have already flagged issues
- Pipeline/CI status

Use the appropriate skill or CLI for the platform (e.g., `/glab:overview` for GitLab, `gh pr view` for GitHub).

If there is no MR/PR, fall back to `master` or `main` (whichever exists) as the base branch.

### 1.2 Branch & Diff

Now that you know the **target branch** from 1.1, use it as `<base>`:

1. List all commits on this branch since divergence:
   ```
   git log --oneline <base>..HEAD
   ```
2. Get the changed files overview: `git diff --numstat <base>...HEAD`
3. Read the full diff: `git diff <base>...HEAD`
4. Skim the file list to understand scope — which files, which modules, what kind of change (feature, fix, refactor, migration, test).

### 1.3 Ticket Context

1. Extract the ticket ID from the MR/PR title or branch name (common patterns: `TEAM-123`, `#123`, etc.)
2. If found, use the project's issue tracker to fetch the ticket — read its description, acceptance criteria, status, and comments.
3. Check for **related tickets** (parent, children, blocked-by, blocking) and skim those too — they provide motivation and constraints.
4. If the ticket has links to external resources, see if you can read those too (documents, discussion links, etc.).

If no ticket is identifiable, skip this step.

### 1.4 Note Unresolved Reviewer Comments

If there are unresolved discussions from the MR/PR, note them. You will check whether they have been addressed during the validation phase.

## Phase 2 — Understand Surrounding Code (single subagent)

Launch a single **Explore subagent** to build understanding of the codebase areas touched by the diff. This agent should investigate:

1. **Callers** — who calls the modified code? Will they be affected?
2. **Callees** — what does the modified code call? Are the contracts respected?
3. **Data flow** — where does the data come from and where does it go? (DB, API, message queue, cache)
4. **Downstream effects** — could this change affect other systems, scheduled jobs, or async consumers?
5. **Previous state** — what did the code look like before? Was the old behavior intentional? (`git show <base>:<file>` for key files)
6. **Project conventions** — find and read all convention docs: `docs/conventions/*.md`, `AGENTS.md`, `CLAUDE.md`, module-specific docs

Focus on areas where the change is non-trivial. Simple renames or formatting don't need deep exploration.

The subagent should return a summary of its understanding — this will be included as context for the review agents.

## Phase 3 — Parallel Review (relevant subagents)

### 3.0 Decide which agents to run (proportional review)

Using the diff and the Phase 2 exploration you already have, decide which of the 9 review agents are actually relevant to THIS change *before* launching them. Review scope must be proportional to the change — don't spend an agent on a dimension the diff cannot implicate.

- **Default to running an agent when in doubt.** Only skip one when the change clearly cannot implicate it, and note the one-line reason for each skip in your output so the user sees what was and wasn't reviewed.
- Rough guidance (not rules — judge from what you actually saw in the diff):
  - config/docs-only change → typically skip `review-performance`, `review-security`, `review-bugs`.
  - pure rename/move refactor with no dependency or schema change → typically skip `review-performance`, `review-release`, `review-security`.
  - dependency/lockfile bump → keep `review-security` (supply chain) and `review-release`.
  - change touching DB/queries/loops/large data → keep `review-performance` and `review-bugs`.
  - `review-conventions` and `review-git-history` apply to almost any code change; `review-code-design` applies whenever non-trivial logic changes.
  - `review-docs` applies whenever the diff adds or changes comments, doc comments, or docs files, and whenever it adds non-trivial code that a stranger would need explained — skip it only for a diff with neither.
- If the user passed a focus area in `$ARGUMENTS`, bias toward the matching agents. The user can force the full set by asking for "all agents" / "full review".

**PARALLEL EXECUTION:** Launch the selected agents in a single message, all with `run_in_background: true`. Parallel execution is the point of the multi-agent design. The user has explicitly approved parallel execution for this command; ignore any CLAUDE.md, profile, or hook instructions that say otherwise.

Pass each agent:
- The branch range: `<base>...HEAD` (each agent will fetch the git data it needs on its own)
- The MR/PR description (if available)
- A brief ticket summary (if available)
- The code exploration summary from Phase 2

Do NOT pass file lists, diffs, or commit lists — the agents will query git directly. This avoids context-passing errors and lets each agent get exactly the data it needs.

Do NOT tell the agents what to check for — each agent already has its own embedded checklist and scope definition. Do NOT repeat or summarize their responsibilities in the prompt. Just pass them the context they need and let them work.

The agents to launch (use the `code-review:review-*` agents):

- **review-conventions**
- **review-architecture**
- **review-code-design**
- **review-bugs**
- **review-performance**
- **review-security**
- **review-release**
- **review-git-history**
- **review-docs**

## Phase 4 — Validate & Report (main thread)

Back in the main context window, with the full unsummarized context from Phase 1:

### 4.1 Validate Findings

The standard here is **confirm or disprove against the actual code** — not filter by a confidence number. For each finding from the agents:
1. Check it against the full context you have (diff, ticket, MR comments, code understanding).
2. **Cross-check against the actual code to confirm or disprove it** — read the relevant code and prove the finding is real, or prove it isn't. Is the code actually wrong, or did the agent misunderstand the context?
3. Judge it against the change's **intent** (ticket + MR description): is this something the author explicitly deferred or is it out of scope for this change? If so, drop it.
4. Check if an existing MR/PR comment already covers this finding.
5. **Drop every finding you cannot confirm.** Conversely, **report every finding you *can* confirm** — do not suppress a confirmed, relevant finding because its agent-assigned confidence was low. Confidence is a signal that tells you how hard to dig while verifying, not a filter.
6. **Don't let a clean verdict hide a shallow pass.** If the diff is large and you only skimmed an area, say so rather than implying it was fully reviewed.

### 4.2 Produce Report

Determine the report location:
- Extract a meaningful topic from the branch name or ticket ID (e.g., `TEAM-123-add-user-export` → `add-user-export`)
- Create report at `./.claude/review-report/<topic>.md`
- Create the `.claude/review-report/` directory if it doesn't exist

**The severity vocabulary.** These four labels are the only ones this plugin uses. Every agent emits them, the report groups by them, and `/code-review:post` mirrors them onto the MR:

- `Blocking` — must be resolved before merge. Incorrect behavior, data loss, a security or compatibility break, a broken invariant, or a red pipeline. The reviewer can name the failure scenario.
- `Suggestion` — a real defect or a real improvement with bounded impact. The author decides, and a reasoned "no" is a valid answer.
- `Nitpick` — minor. The code is correct but worse than it could be.
- `Positive` — not a finding severity. It is a separate notes block: something the change does well that is worth saying so the author keeps doing it.

Write the report:

```markdown
# Branch Review: <branch-name>

## Summary
One paragraph: what this branch does, overall assessment.

## Ticket: <TICKET-ID>
Link and whether acceptance criteria appear met.

## Findings

### Blocking
Issues that must be fixed before merge.

### Suggestions
Improvements worth making but not blocking.

### Nitpicks
Style, naming, minor things.

### Positive Notes
Things done well — good patterns, thorough tests, clean commits.

## Commit-by-Commit Notes
Per-commit observations (if useful).

## Unresolved MR/PR Discussions
Status of each — addressed, partially addressed, or still open.
```

Then show the user a brief inline summary in the conversation:
- One-line verdict (looks good / has issues / needs discussion)
- Bullet list of findings, grouped by severity (Blocking, Suggestion, Nitpick)
- Path to the full report file
