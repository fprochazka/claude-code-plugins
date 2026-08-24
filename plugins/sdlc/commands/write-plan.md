---
description: Enter plan mode and write an implementation plan structured for git-workflow and subagent-driven execution
argument-hint: [what to plan — topic, ticket ref, or path to a pre-plan briefing]
allowed-tools: AskUserQuestion, Read, Glob, Grep, Bash, Agent, Skill, EnterPlanMode
---

# Write an Implementation Plan

Write a plan file for the work described below, then hand it off for execution. The plan must be shaped so that (a) the resulting git history is clean per the git-workflow rules, and (b) the implementation can be driven by **one persistent implementation subagent** that receives the **plan file itself**, not giant inlined excerpts.

This command is normally run **after `/sdlc:pre-plan` and a design discussion**, so most context should already be in hand — don't re-derive what's already been gathered or decided.

## Scope

$ARGUMENTS

If the Scope is empty, use the current conversation context (e.g. a pre-plan briefing already produced in this session). If it's unclear what we're planning, ask the user before proceeding.

## Step 1 — Load the git-workflow skill

Invoke the `git:git-workflow` skill first, and apply its rules to shape the plan around the **ideal git history** rather than the order code happens to get written. The concrete tie-in for this command: **each step in the plan maps onto one intended atomic commit** (or a small, named group), so the plan's structure already encodes the commit sequence.

## Step 2 — Front-load every decision, before plan mode

**Do not enter plan mode yet.** Plan mode restricts what the permission system lets you run, and this phase may still need real work — subagent explorations, data checks, queries against external systems. Enter plan mode only in Step 3, when the only work left is writing.

The plan you write will be executed with minimal supervision — the user may not be at the keyboard while it runs. So the bar is not "do I know enough to start writing": it is **"have I surfaced every decision the user would otherwise be asked mid-implementation"**. A question asked now costs one AskUserQuestion; the same question at step 7 stalls the whole run.

- Walk the intended steps and hunt for the decisions hiding inside them: user-facing naming, product behavior at edge cases, scope trade-offs, anything irreversible. Ask about all of it now (AskUserQuestion) — the goal is that the executing agent never has to stop for a decision.
- Genuine knowledge gaps in the code → fill with targeted, delegated exploration (subagents, not inline spelunking) — only for the gaps, not a fresh sweep.

Don't move on to Step 3 while something material is unresolved.

## Step 3 — Enter plan mode and write the plan

**Enter plan mode now.** Everything is decided and explored, so the plan should come out final — the user reviews it, adjusts at most small details, approves, and lets execution run unattended. Planning only; do not start implementing.

Write the plan to the **plan file specified in the plan-mode system message** — a fresh file; don't append to or carry over a previous plan. The body is the ordered sequence of atomic-commit-sized steps from Step 1, each with: what changes, which files, why, how to verify, the intended commit message, and the step's **check tier** (below).

### Name the implementation model

The plan names the model for the implementation subagent — one line near the top. Use `opus` by default. Use `fable` only when the implementation itself carries hard reasoning: concurrency, transaction and isolation behavior, subtle correctness, cross-system effects. If the difficulty is concentrated in one phase, the plan may schedule a subagent swap at that phase boundary (see the protocol) so the expensive model is spent only on the steps that need it.

### Assign each step a check tier

The orchestrator checks the work after **every** step — that part is fixed. What the plan decides, per step, is **who performs the check**, based on how small and simple the step is expected to be:

- `check: direct` — the orchestrator inspects the staged diff itself. For trivial increments: small mechanical changes, renames, config, code the plan already spells out nearly verbatim.
- `check: validation subagent (opus)` / `check: validation subagent (fable)` — a fresh validation subagent reviews the staged work against the plan's intent. For everything that is not trivial: new logic, anything with edge cases, anything the plan describes by outcome rather than by exact change. Use `fable` when the step carries real reasoning risk — concurrency, transaction and isolation behavior, subtle correctness, cross-system or cross-repo effects, a wide blast radius; `opus` otherwise. Do not spend `fable` by default.

A **phase boundary always gets the subagent tier**, whatever the size of the step. A phase boundary is where the next block of work is built on the assumption that the previous block is already correct, so a defect there is discovered late and expensively. Real boundaries: a schema or migration layer landing before the code that reads it, an abstraction reshaped before the features built on it, a data backfill before its consumers, one service's contract before the caller that depends on it. For each subagent-tier check, write down **what it must confirm** — the acceptance criteria it covers and the specific risks this plan is worried about.

### The final validation checkpoint

Always end the implementation steps with a **final validation checkpoint** as its own numbered step: a fresh validation subagent reviews the finished branch as a whole against the plan's intent. This is not a repeat of the per-step checks — it looks at the sum. Name its model by the same `opus`/`fable` rule.

### End with the MR steps

After the final checkpoint, the plan's last numbered steps are: open the MR (`/sdlc:mr-open`), then drive it to mergeable (`/sdlc:mr-babysit`). They are part of the plan, not an epilogue the orchestrator asks permission for.

## Step 4 — Append the implementation protocol to the plan

At the **end of the plan file**, append a verbatim "## Implementation Protocol" section, so the execution rules travel with the plan even into a fresh session. Keep it lean — exactly this:

```markdown
## Implementation Protocol

One step at a time, never in parallel. The user may not be watching — the default is to keep going, not to stop and wait.

1. **Before step 1**: create a "continue the plan" cron firing every 30 minutes. Each pass re-derives state from scratch (this plan file, `git status`, `git log`) and continues the run if it stalled. Delete it only after the MR babysitting step is done.
2. **One persistent implementation subagent** — spawn it with the model this plan names and reuse it for every step: message it this plan file's path, the step to do, and "stop and report when done". Start a fresh one only when it runs out of context window or this plan schedules a model swap; the fresh one catches up from the plan file and the branch's commits.
3. The subagent implements the step, verifies it (build / lint / relevant tests), **stages everything with `git add -A`, does NOT commit**, and reports: what it did, what verification ran and came back, which parts are tricky.
4. **Check every step at the tier this plan assigns it.** `check: direct` → the orchestrator inspects the staged diff itself. `check: validation subagent` → a fresh subagent with the model the plan names, given *only* this plan file's path, the steps it covers, what to review, and the risks the plan flags — nothing else. Validators read, run the real verification, and report; they never change code.
5. **Findings go back to the implementation subagent** — the orchestrator never fixes code itself. Re-check after the correction; repeat until clean or the rest is consciously accepted. Then the orchestrator commits with the step's intended message and moves to the next step.
6. **Mid-flight decisions**: derivable from code, data, or convention → decide, record the decision in this file, continue. A product decision only the user can make → ask, park the dependent steps, continue everything not blocked. Stop and wait only when proceeding would be damaging or hard to reverse.
7. **Finish without asking**: run the final validation checkpoint, then `/sdlc:mr-open`, then `/sdlc:mr-babysit`, then delete the cron. Skip the MR steps only if the user explicitly said they will handle the MR themselves.
```

### Orchestrator craft — follow this yourself, do not copy it into the plan

- **Per-step message hygiene.** The message to the implementation subagent contains only the plan file path, the step to do, and anything *not* already in the plan (post-plan decisions, gotchas discovered mid-flow). Never paste plan content — the subagent reads the file itself.
- **Why staged-not-committed.** Checks exist to catch problems, so optimize the reject path: staged work is corrected for free, a bad commit has to be `reset`/`amend`-ed. Staging (not leaving unstaged) also keeps `git diff --cached` complete — new files show as full additions — so inspection is one call.
- **How to run a `check: direct`.** Start with the shape (`git diff --cached --stat`), read in full only the regions that carry real logic, and skim bulk/low-signal regions — snapshot dumps, regenerated fixtures, lockfiles, generated code — just enough to confirm they are the expected *kind* of change. Use the subagent's "tricky parts" list as the starting map.
- **Why validators start cold.** Passing them the implementation subagent's report, your own reading of the diff, or "should be fine, just double-check" framing turns a flaw-finder into a bias-confirmer. A validation subagent is a fresh pair of eyes only if the eyes are actually fresh.
- **Commit ownership.** You own the message, atomicity, and history shape (git-workflow rules). If reality drifted — the work should be two commits, or fold into the previous one — reshape it while it is only staged. If a step reveals a prerequisite, land the prerequisite as its own commit first, then resume the step.
- **Why the cron.** Sessions have been seen to announce "next I will do X" and then stop. The cron turns that failure from a dead end into a 30-minute delay.

## Step 5 — Get the user's approval

Call **`ExitPlanMode`** to present the finished plan (body + appended Implementation Protocol) for approval — it reads the plan file you just wrote. Do not start implementing — wait for the user to review and approve.
