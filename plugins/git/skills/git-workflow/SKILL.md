---
name: git-workflow
description: Judgment rules for how to shape commits, plan branches, and respond to review — not git mechanics. Use when staging changes, writing commit messages, splitting/reordering commits, planning a branch's structure, addressing review feedback, or deciding how to merge.
trigger-keywords: commit, git, rebase, git history, branch history
---

# git-workflow

How to *think* about commits, branches, and merge requests — the shape the history should take, not the commands to get there.

The underlying principle: **a reviewer should be able to read the branch commit-by-commit and never be confused about what each commit does or why.** Every rule below serves that goal. When a rule fights it, the rule loses.

## The test that decides every commit boundary

Before splitting anything, classify the pieces as **siblings** or **ancestors**.

- **Siblings** — complete on their own terms, revertible in any order, each one meaningful on `master` to somebody who never saw the branch. Siblings stay separate commits.
- **Ancestors** — incomplete halves of a single behaviour, each one meaningful only once the next one lands. Ancestors are **one commit**, no matter how logically they were built in sequence.

The mechanical form: **if commit N+1's subject cannot be understood without the artifact commit N introduced, they are the same commit.**

The order work *gets done* is almost always an ancestor chain: add the columns, persist them, wire them into the callers, expose them on the endpoint, regenerate the client, build the UI. That is a correct working sequence and a wrong commit sequence. The atomic commit is the whole vertical slice — schema, domain logic, transport, generated client, frontend, tests — because none of those halves means anything alone.

## What makes a commit atomic

An atomic commit solves **exactly one thing — not less, not more**, with all related changes included and all unrelated changes excluded. "One thing" is one complete change in what the system does, cut through every layer it needs. Vertical slices can and should be small, but each one is a fully functioning increment: it builds, its tests pass, it makes sense on `master` alone.

**Is atomic:**
- A feature cut vertically: migration + entity + domain logic + endpoint + regenerated client + UI + its tests, in one commit.
- A bugfix that changes only the lines needed for the fix, with the test that now passes.
- A pure rename/move touching many files but changing no behaviour.
- A formatting-only commit, or a single typo fix.

**Is not atomic:**
- Any ancestor chain split across commits.
- A feature commit without its tests — verification deferred to a later commit.
- A rename/move mixed with a behaviour change — the behaviour diff hides in the move's noise.
- A commit that bundles an unrelated drive-by fix ("while I was here, I also fixed X").
- A commit that mixes formatting/import reordering with real code changes.
- A "fix previous commit", "oops", or "address review" commit next to the commit it corrects — that is a fixup.

### Never split these

Each of these pairs is one commit. If you have written both subjects, merge them:

- `Add <X> table/columns/entity` + anything that reads or writes `<X>`.
- `<behaviour>` + `Wire/Expose/Thread/Surface <behaviour> to the API`.
- Any change + `Regenerate the API client`, or + the frontend for that same change, or + `Add tests for <that change>`.
- A stub, scaffold, empty shell, or table nothing reads yet + the commit that gives it meaning.

A useful tell: if you fuse two of your own subjects with "and" to describe the result, that fusion was the correct commit all along.

### These genuinely are separate commits

- **A prerequisite refactoring** — an extraction, a move, a rename, a new self-contained helper with its own tests. This is a legitimate separate commit **even when your feature is the only reason it exists**. If the feature needs to refactor something, that refactoring does not belong in the feature commit. The prerequisite is complete on its own terms: it compiles, its tests pass, a reviewer can verify it without knowing what you plan to build next.
- **A campaign of N identically-shaped independent changes** — `Add updated_at to <Entity>` per entity, one commit per new endpoint. Textbook siblings.
- **A second independently-shippable behaviour** under the same ticket, revertible without touching the first.
- **Incidental noise, quarantined** — dev config, log levels, tracing spans, editor files, dependency bumps. Siblings of the payload, not build steps of it.
- **A pre-existing bug found while working** — see the discriminator under fixups.

The seam to split on is behaviour-neutral vs behaviour-changing. The seam **not** to split on is build order.

## Correcting your own work: fixups, not commits

**Never create a commit that corrects a commit already on this branch.** Use `git commit --fixup <sha>` and autosquash before merge.

Apply this test before writing any commit message:

> **Would an earlier commit on this branch have looked different if I had known this at the time?** If yes, the change belongs *inside* that commit — fixup. If you are adding new work on top of a commit that was correct as written, it is a new commit.

Touching the same files as an earlier commit is a reason to ask the question, not an answer to it. A prerequisite refactor and the feature built on it necessarily touch the same code, and they stay separate commits.

**Found bug vs introduced bug:** a defect that **pre-existed this branch** is its own commit — it would still be worth fixing if your feature were abandoned. A defect in **code this branch introduced** is a fixup — repairing your own new code is a change to your draft, not to the system. Review feedback almost always concerns code the branch introduced, so it almost always becomes a fixup.

**Forbidden subjects** — if you are about to write one of these, you wanted a fixup: `Address MR review findings`, `Review fixes (…)`, `Fix SonarQube issues`, `Fix import order`, `Cleanup: checkstyle/sonar/lint`, and bare `review`, `typo`, `cleanup`, `refactoring`, `WIP`.

Review-by-commits is the intended mode of reading a shaped branch. A standalone "address review" commit forces the reviewer into compare-pushes mode, which is slower and noisier. Fixups are a branch-only tool. A branch's history stays rewritable until it merges — pushing it to origin changes nothing. Once it lands on master/main, rewriting stops. Corrections that a fixup cannot express (moving changes between commits, splitting, reordering) are done in an interactive rebase.

## Planning the history

**Write the one-sentence description of the branch first** — the sentence that would be the MR title, naming the behaviour the system will have afterwards. That sentence is your primary commit. Then ask the only useful follow-up: *what in this work is genuinely separate from that sentence?* Prerequisites, quarantined noise, pre-existing bugs, occasionally a second behaviour. The build steps of the sentence itself are already inside it.

Do not plan the branch as a sequence of construction stages. "Schema, then logic, then wiring, then UI" produces exactly the ancestor chain the boundary test rejects.

Plan upfront and commit as you go. Retroactively splitting a messy working tree into good history is far harder than committing in the right shape from the start. **Cleanup as an after-thought is a waste of time.**

If you notice mid-feature that you need a refactoring, a rename, or a cleanup before you can proceed: **pause and set the uncommitted work aside** — stash it, or commit it as WIP onto a temporary branch. Only the working-tree changes move, never the commits already on the branch — those are done and build-passing, they stay where they are. Do the prerequisite on the now-clean HEAD, so you can prove it compiles and passes tests without the half-done feature mixed in, and commit it. Then bring the uncommitted work back on top and resume. Do not let the prerequisite contaminate the in-progress commit, and do not let the in-progress feature contaminate the prerequisite.

## Ordering within a branch

Order by dependency:

1. **Noise absorbers first** — dev config, log levels, tracing, editor files, typo and formatting fixes.
2. **Prerequisites, in the order the payload needs them** — pure moves and renames, extractions, self-contained helpers, dependency bumps.
3. **The payload** — one commit, or several if they are true siblings.
4. **Cleanups the change unlocked, and docs, last.**

Refactorings and typo fixes come before behaviour changes for two reasons. A large pure-refactor diff is easy to skim while a small pure-behaviour diff is easy to scrutinise, so keeping them apart shrinks the feature's own diff. And prerequisites ordered first stay cherry-pickable, so the branch can be sliced into more MRs later if that becomes worth it. Keep them provably clean — moves as `+N/-N`, extractions that smuggle in no behaviour.

**Do not manufacture a refactor commit to satisfy the pattern.** If nothing needed extracting, the branch starts with the payload.

**Build and tests pass on every commit.** If you cherry-picked them onto master one by one, none would break the build. Broken intermediate commits are never "pre-existing" — if you touched the code, the failure is yours.

## Tests and docs

**Tests ride inside the commit whose behaviour they cover.** A test-only commit is legitimate in exactly two cases: test infrastructure (a fixture builder, a custom extension), and a **characterization test committed *before* the fix it pins**, so the fix commit's test diff shows exactly what behaviour changed. Subjects beginning `Add tests for…`, `Cover…`, or `Regenerate … snapshots` are the tell that you deferred verification.

Docs for a change ride with the change. Standalone docs commits are for documentation that stands on its own.

## Extracting prerequisites into their own MR

**One branch is the default.** A refactoring's conflict surface grows every day it sits unmerged, so extracting prerequisite commits into an MR that lands quickly is sometimes worth it. **That call belongs to the human, not to you.** Never open a prep MR on your own initiative. What you owe is a branch where extraction stays cheap: prerequisites first, self-contained, free of payload behaviour. When asked to extract, move the commits verbatim onto their own branch, merge that first, rebase the feature branch onto the result.

## Commit messages

**The subject names the behaviour, not the work.** Write what the system now does, in one sentence, the way the MR title would say it. When several drafts collapse into one commit, write a new subject describing the whole.

- Match the project's existing convention (prefix, ticket ID, emoji, casing), inferred from recent history on the base branch.
- A subject long enough to name the behaviour *and* its mechanism beats a short vague one.
- Default to no body. The narrative goes in the MR description. Add a body only to record a non-obvious decision — a constraint, a rejected alternative, an operational caveat.
- Never narrate your own process: no `WIP`, `[ci skip]`, `part N`, `step N`.

## Branch size is a signal

A feature branch usually lands as one commit, sometimes a handful. More than ~6 commits is a **signal to re-apply the sibling/ancestor test to your own list**, not a limit. If the commits are genuinely siblings — a campaign of N identically-shaped changes, a run of prerequisites, several independent behaviours — a 20-commit branch is atomic and fine. If the test collapses most of the list, you sliced by build order. Fix that before pushing.

## When the history is beyond saving

If told the history is garbage and to commit at HEAD because it will be squashed: **that is a terminal instruction.** Commit everything at HEAD and stop. Do not propose a cleanup rebase, do not offer to re-split, do not relitigate it later in the branch.

## When to break the atomicity rule

Bend atomicity only when it makes the **diff better for review**. A repo reorganization that moves 1000+ files unavoidably breaks the build mid-move. *"Move files"* + *"fix build after move"* is more honest than one 1000-file commit that also edits imports inline. This is the exception. Most violations are rationalizations — the default answer is still the boundary test.

## Workflow

- **Always work in a branch.** Committing directly to `master`/`main` is acceptable only on solo projects.
- **Do not limit yourself to one rebase.** Ten small rewrites are safer than one heroic one — same reasoning as small commits.
- **Do not squash a branch you shaped.** Semi-linear history is the goal. Squashing a well-shaped branch destroys the atomic story you built. Configure the repo to *allow* squash, never to require it.
- **Avoid multi-person branches.** One person owns a branch's history. If a shared branch is unavoidable: keep it short-lived, one person rebases and everyone else resets to the new tip, merge it as soon as possible.

## What not to do

- Do not split a branch by build order — schema, then logic, then wiring, then UI is one commit, not four.
- Do not amend or rewrite commits on a **shared** branch without explicit coordination.
- Do not blindly stage everything when the working tree has unrelated changes — add specific paths or hunks.
- Do not create empty "trigger CI" commits unless explicitly asked.
- Do not bypass commit hooks to make an error go away — fix the underlying issue.
- Do not dismiss build, lint, or test failures in code you touched as "pre-existing."
- Do not "clean up" a branch by squashing everything into one commit — that is the opposite of a nice history.
