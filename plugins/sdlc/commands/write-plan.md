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

At the **end of the plan file**, append a verbatim "## Implementation Protocol" section so the execution rules travel with the plan and reinforce themselves. Use this content:

```markdown
## Implementation Protocol

This plan is executed by an orchestrating main agent and subagents, one step at a time, never in parallel — so the user keeps visibility into each step. The user may not be watching: the default is to keep going, not to stop and wait.

### Before the first implementation step

**Create a "continue the plan" cron, firing every 30 minutes.** Each pass must re-derive state from scratch: read the plan file, `git status`, and `git log`, work out which step the run is at, and check whether anything is actually in flight. If the session announced work and then stalled, continue from where it stopped. Delete the cron only after the last step of this plan (MR babysitting) is done. This exists because sessions have been seen to say "next I will do X" and then stop — the cron turns that failure from a dead end into a 30-minute delay.

### One persistent implementation subagent

- **Spawn one implementation subagent at step 1, with the model this plan names, and reuse it for the whole run.** For each step, message it: the **path to this plan file**, **which step to do**, and an instruction to stop and report when the step is done. It keeps the repo exploration and every previous step in context — that is the point. A fresh subagent per step re-explores the repo from zero every time, which is slow and wasteful.
- Starting a fresh implementation subagent is right in exactly two cases: the current one ran out of context window, or this plan schedules a model swap at a phase boundary. Tell the fresh one to read the plan file and skim the branch's commits to catch up.
- The per-step message contains only: the plan file path, the step to do, and anything *not* already in the plan (post-plan decisions, gotchas discovered mid-flow). Never paste plan content into it.
- Each step maps to one atomic commit (or a small named group). The subagent implements it, verifies it (build / lint / relevant tests), **stages everything with `git add -A`, and stops — it does NOT commit.** The **main agent owns committing** — the message, atomicity, and history shape, per the git-workflow rules.
  - Why staged-not-committed: checks exist *to catch problems*, so optimize the reject path. Staged work is corrected for free; a bad commit has to be `reset`/`amend`-ed. Staging (not leaving unstaged) also keeps `git diff --cached` complete — new files show as full additions — so inspection is one call.
- **The subagent reports back, in its final message:** (1) what it implemented, (2) what verification it ran and the result, (3) the parts of the staged work that are **tricky or non-obvious** and worth a second pair of eyes.

### After every step: the check

When the subagent stops, the main agent looks at `git status`, then runs the check **at the tier this plan assigned to the step**:

- **`check: direct`** — the main agent inspects the staged work itself. Start with the shape (`git diff --cached --stat`), read in full only the regions that carry real logic, and skim bulk/low-signal regions — snapshot dumps, regenerated fixtures, lockfiles, generated code — just enough to confirm they are the expected *kind* of change. Use the subagent's "tricky parts" list as the starting map.
- **`check: validation subagent`** — dispatch a validation subagent with the model the plan names for this step (rules below).

Then close the loop:

1. Findings and claims from the check go **back to the implementation subagent** as a correction instruction — the main agent does not fix code itself. The work is still uncommitted, so the subagent just adjusts the staged changes.
2. Re-run the check on the corrected work (same tier). Repeat until it comes back clean, or the remaining findings are consciously accepted.
3. **Commit with the intended message from the plan step.** If reality drifted — the work should be two commits, or fold into the previous one — reshape it now, while it is only staged.
4. Message the implementation subagent with the next step.

If a step reveals a needed prerequisite, pause, land the prerequisite as its own commit first, then resume the step — don't let it contaminate the in-progress change.

### Validation subagents

A validation subagent is a fresh pair of eyes, and it only works if the eyes are actually fresh:

- **Always start it fresh — one per checkpoint, never reused, never the implementation subagent.** Give it *only*: the path to this plan file, which steps it covers, what to review (the staged diff, or the whole branch for the final checkpoint), and the specific risks the plan told it to watch. Do **not** pass it the implementation subagent's report, the main agent's own reading of the diff, its hypotheses, or "should be fine, just double-check" framing. Injected context turns a flaw-finder into a bias-confirmer.
- **It does not change code.** It reads and reports. Corrections are dispatched to the implementation subagent like any other finding.
- It checks the work against the plan's *intent*, not just a green build: acceptance criteria actually met, steps quietly skipped or half-done, deviations nobody decided, missing or vacuous tests, dead code left behind, and defects the implementor could not see because it wrote the code itself.
- It runs the real verification — build, lint, the relevant tests — and reports what it ran and what came back. A checkpoint that only reasons about the diff is not a checkpoint.

### Decisions mid-flight

Planning was supposed to surface every user decision up front, so treat a mid-flight decision as rare — and handle it without stalling the run:

- **Mechanical or technical question whose answer can be derived from the code, the data, or project convention** → investigate, pick the best option, record the decision in the plan file, and continue. Do not stop for these.
- **A genuine product decision only the user can make** → ask (AskUserQuestion), but do not block on the answer: park the steps that depend on it and continue with every step that does not. Finish as much as possible.
- **Stop and wait only when proceeding would be damaging or hard to reverse** — destructive migrations, irreversible external actions, anything published to other people.

### Finishing — explicit steps, no confirmation

The user approved this plan; that approval covers everything below. Do not stop to ask "should I open the MR now?" — announce-and-stall is exactly the failure this protocol exists to prevent.

1. Run the final validation checkpoint and route its findings through the implementation subagent until clean.
2. Open the merge request with `/sdlc:mr-open`.
3. Drive it to mergeable with `/sdlc:mr-babysit`.
4. Delete the "continue the plan" cron.

Skip the MR steps only if the user explicitly said they want to handle the MR themselves.
```

## Step 5 — Get the user's approval

Call **`ExitPlanMode`** to present the finished plan (body + appended Implementation Protocol) for approval — it reads the plan file you just wrote. Do not start implementing — wait for the user to review and approve.
