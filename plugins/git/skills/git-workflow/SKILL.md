---
name: git-workflow
description: Judgment rules for how to shape commits, plan branches, and respond to review — not git mechanics. Use when staging changes, writing commit messages, splitting/reordering commits, planning a branch's structure, addressing review feedback, or deciding how to merge.
trigger-keywords: commit, git, rebase, git history, branch history
---

# git-workflow

How to *think* about commits, branches, and merge requests — the shape the history should take, not the commands to get there.

The underlying principle: **a reviewer should be able to read the branch commit-by-commit and never be confused about what each commit does or why.** Every rule below exists to serve that goal. When a rule fights it, the rule loses.

## What makes a commit atomic

An atomic commit solves **exactly one thing — not less, not more**, with all related changes included and all unrelated changes excluded.

**Is atomic:**
- A feature commit that includes its tests together.
- A bugfix that changes only the lines needed for the fix, ideally with the test that now passes.
- A pure rename/move touching many files but changing no behavior.
- A formatting-only commit that changes no behavior.
- A single typo fix.

**Is not atomic:**
- A feature commit without its tests — the reviewer can't tell if the feature works, and verification is deferred to a later commit.
- A rename/move mixed with a behavior change — the behavior diff is hidden in the move's noise.
- A commit that bundles an unrelated drive-by fix ("while I was here, I also fixed X").
- A commit that mixes formatting/import reordering with real code changes.
- A commit touching multiple unrelated files or modules.
- A "fix previous commit", "oops", or "address review" commit sitting next to the commit it's fixing — should have been a fixup.

**"Too little" beats "too much".** When in doubt, split. But **don't overdo it** — commits aren't line-by-line. A commit must still be atomic in the sense that it builds, runs, and makes sense on its own.

## What makes a branch's history pretty

A pretty branch reads like a deliberate story when you go through it commit-by-commit.

**Is pretty:**
- Refactorings, renames, and formatting fixes come **first**, before behavior changes.
  - **Why:** in review, a large pure-refactor diff is easy to skim while a small pure-behavior diff is easy to scrutinize; mixing them hides the behavior change in noise. Ordering refactorings first also keeps them cherry-pickable if the branch turns out to sit unmerged long enough that early extraction becomes worth it.
- Each commit **stands alone** and tells the reviewer one clear thing.
- **Build and tests pass on every commit.** If you cherry-picked them onto master one by one, none would break the build. Broken intermediate commits are never "pre-existing" — if you touched the code, the failure is yours.
- Bugfixes are preceded by a **test commit capturing the broken behavior**, so the fix commit's test diff shows exactly what behavior changed. Same idea for snapshot tests.
- Commit messages match the project's existing convention, inferred from recent history on the base branch. Don't invent your own style.
- **Semi-linear merge**, not fully linear, not spaghetti.

**Is not pretty:**
- A feature commit followed later by "add tests for feature" — should have been one commit.
- A "fix CI", "address review", or "oops" commit standing on its own — should have been a fixup squashed into its target.
- A refactoring commit ordered after the feature commit that needed it.
- A whole branch squashed into one giant commit — destroys the atomic story you built.
- Commits touching unrelated concerns ("add feature X and fix unrelated bug Y").
- A branch where the commit list alone doesn't tell you what it's doing.

## When to break the atomicity rule

It's acceptable to bend atomicity when doing so makes the **diff better for review**. Example: a repo reorganization that moves 1000+ files unavoidably breaks the build mid-move. Splitting into *"move files"* + *"fix build after move"* is more honest than a single 1000-file commit that also edits imports inline — the reviewer can verify each step.

This is the exception, not the norm. Most violations are rationalizations — the default answer is still "split it."

## Workflow

### Always work in a branch
Feature/fix work happens in a dedicated branch. Working directly on `master`/`main` is acceptable **only on solo projects**. Otherwise: branch first, commit second.

### Plan the history before coding
Before writing code, think about how the work builds on what's there and **plan the work around the ideal git history**. Ask: *what's the smallest sequence of atomic commits that tells this story?* Usually something like:

1. Prerequisite refactorings (moves, renames, extractions).
2. Typo/formatting fixes noticed along the way.
3. Tests capturing current (broken) behavior, if this is a bugfix.
4. The feature or fix itself, with its tests.

Plan this upfront and commit as you go. It's much harder to retroactively split a messy working tree into pretty history than to commit in the right shape from the start. **Cleanup as an after-thought is wrong — it's a waste of time.**

Thinking this way also makes you a better developer: it forces you to name and separate prerequisites instead of tangling them into feature work.

### Pause for prerequisites discovered mid-flow
If you notice, mid-feature, that you need a refactoring, a rename, or a cleanup before you can proceed: **pause**, do the prerequisite, commit it separately, then resume the feature. Don't let it contaminate the in-progress commit.

### Extracting refactorings into a separate MR — only when justified
A refactoring's conflict surface grows every day it sits unmerged. **If** a branch is going to live for days or weeks before merging, it can be worth extracting a refactoring into its own smaller MR that lands quickly, and rebasing the feature branch onto the result.

**But early extraction is not the default.** Opening a separate MR and rebasing costs a second review cycle, a second CI run, a rebase, and context switching. In fast iteration — especially AI-assisted work where a branch may land the same day — that overhead usually costs more than it saves. **Keeping the refactoring in the branch is the default; extract only when you can justify the overhead.**

Signals that extraction is worth it:
- The branch realistically won't merge today, and probably not this week.
- The refactoring touches conflict-prone files that other people are actively working on.
- The refactoring unblocks or parallelizes someone else's work.
- The refactoring is big enough that the reviewer will appreciate seeing it separately from the feature change.

If none of those apply, keep the refactoring ordered first in the branch (per the "pretty history" rule) and ship the whole branch together.

### Addressing review feedback — use fixups
Once a branch is pushed and review/CI feedback starts coming in, **do not** make standalone "address review" or "fix CI" commits. Commit each correction as a **fixup targeting the specific commit it belongs to**, and autosquash the fixups into their targets before merging. The final history shows the intended atomic commits, not the review back-and-forth.

**Why fixups, not standalone fix commits:** the intended mode of reviewing a nice-history branch is *review-by-commits* — the reviewer walks commits one at a time, each with a small focused scope. A standalone "address review" commit forces the reviewer out of that mode and into compare-pushes mode, which is slower, noisier, and error-prone. Nice-history MRs sidestep the "how do I review the fixes" problem by not creating it.

**Fixups are a branch-only tool.** Using fixups on master/main is nonsense — there's nothing to autosquash into, and published commits shouldn't be rewritten. Fixups exist specifically to clean up branch history before merge.

Some corrections can't be expressed as a clean fixup (e.g. moving changes between two existing commits, splitting a commit, reordering). For those you edit the history directly during an interactive rebase — a separate topic.

### Don't limit yourself to one rebase
A branch cleanup doesn't have to be one heroic rebase. **Doing ten small rewrites is safer than doing one big one** — same reasoning as small commits: too much at once and you lose track of what you're doing. Rebase, rebase again, rebase ten times if that's what keeps you in control.

### Don't squash the whole branch
At merge time, **semi-linear history is the goal. Squash only when the branch history is genuinely ugly and can't be salvaged.** Squashing a well-shaped branch into one commit destroys the atomic story you built. If the platform allows it, configure the repo to *allow* (not encourage or require) squash, and reach for escape hatches where tooling forces a squash by default.

### Multi-person branches
**Avoid them.** A branch is easiest to keep clean when one person owns its history. If a shared branch is unavoidable: keep it short-lived, coordinate rebases explicitly (one person rebases, everyone else resets to the new tip before continuing), and merge it as soon as possible.

## What not to do

- Don't amend or rewrite commits on a **shared** branch without explicit coordination — prefer a new commit or a fixup.
- Don't blindly stage everything when the working tree has unrelated changes — add specific paths or hunks.
- Don't create empty "trigger CI" commits unless explicitly asked.
- Don't bypass commit hooks to make an error go away — fix the underlying issue.
- Don't dismiss build, lint, or test failures in code you touched as "pre-existing." If you touched it, it's yours now.
- Don't "clean up" a branch by squashing everything into one commit — that's the opposite of a nice history.
