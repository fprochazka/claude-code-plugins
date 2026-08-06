---
description: Enter plan mode and write an implementation plan structured for git-workflow and subagent-driven execution
argument-hint: [what to plan — topic, ticket ref, or path to a pre-plan briefing]
allowed-tools: AskUserQuestion, Read, Glob, Grep, Bash, Agent, Skill, EnterPlanMode
---

# Write an Implementation Plan

Write a plan file for the work described below, then hand it off to be implemented by a sequence of subagents. The plan must be shaped so that (a) the resulting git history is clean per the git-workflow rules, and (b) the implementation can be driven by subagents that each receive the **plan file itself**, not giant inlined excerpts.

This command is normally run **after `/sdlc:pre-plan` and a design discussion**, so most context should already be in hand — don't re-derive what's already been gathered or decided.

## Scope

$ARGUMENTS

If the Scope is empty, use the current conversation context (e.g. a pre-plan briefing already produced in this session). If it's unclear what we're planning, ask the user before proceeding.

## Step 1 — Load the git-workflow skill

Invoke the `git:git-workflow` skill first, and apply its rules to shape the plan around the **ideal git history** rather than the order code happens to get written. The concrete tie-in for this command: **each step in the plan maps onto one intended atomic commit** (or a small, named group), so the plan's structure already encodes the commit sequence.

## Step 2 — Enter plan mode and confirm readiness

**Enter plan mode now.** Then, before writing anything, take stock: do you actually have everything needed to write a concrete plan? Explicitly tell the user what — if anything — still needs to be **clarified, confirmed, or explored**, and resolve it first:

- Open decisions only the user can make → ask (AskUserQuestion).
- Genuine knowledge gaps in the code → fill with targeted, delegated exploration (subagents, not inline spelunking) — only for the gaps, not a fresh sweep.

Don't barrel into writing the plan while something material is unresolved. Planning only; do not start implementing.

## Step 3 — Write the plan

Write the plan to the **plan file specified in the plan-mode system message** — a fresh file; don't append to or carry over a previous plan. The body should be organized as the ordered sequence of atomic-commit-sized steps from Step 1, each with: what changes, which files, why, how to verify, and the intended commit message.

## Step 4 — Append the implementation protocol to the plan

At the **end of the plan file**, append a verbatim "## Implementation Protocol" section so the execution rules travel with the plan and reinforce themselves. Use this content:

```markdown
## Implementation Protocol

This plan is implemented by a **sequence of subagents**, run one at a time, never in parallel or in the background — so the user keeps visibility into each step.

- The subagent prompt should contain only: the **path to this plan file** (told to read it), **which step(s) / section(s) to focus on**, and any extra context *not* already in the plan (post-plan decisions, clarifications, gotchas discovered mid-flow). Do **not** paste large chunks of the plan into the prompt — that wastes the orchestrator's tokens duplicating content the subagent can read itself.
- Each subagent's scope should map to one atomic commit (or a small named group). The subagent implements that step, verifies it (build / lint / relevant tests), **stages its work with `git add -A`, and stops — it does NOT commit.** The **main agent owns committing** (and thus the message, atomicity, and history shape — per the git-workflow rules).
  - Why staged-not-committed: inspection exists *to catch problems*, so optimize the reject path. Uncommitted work is discarded or re-instructed for free; a bad commit has to be `reset`/`amend`-ed. Staging (not leaving unstaged) keeps `git diff --cached` complete — new files show as full additions — so inspection is still one call.
- **The subagent reports back, in its final message:** (1) a summary of what it implemented, (2) a summary of verification — what it ran and the result, (3) the parts of the staged work that are **tricky or non-obvious** and worth the main agent's eyes to confirm they're correct. This report is the subagent's hand-off; it points the main agent's attention.
- **The main agent reads that report, thinks about it, and decides what — if anything — to inspect.** It doesn't reflexively read the whole diff. Use the subagent's "tricky parts" as the starting map, plus your own judgment about where this step's risk really lies. When you do look, start with the shape (`git diff --cached --stat`), then read in full only the regions that carry real logic; skim or skip bulk/low-signal regions — snapshot/approval dumps, regenerated fixtures, lockfiles, generated code — reading just enough to confirm they're the expected *kind* of change. Spend the attention budget where a bug could actually hide.
- Once satisfied, **commit with the intended message from the plan step.** If reality drifted — the work should be two commits, or fold into the previous one — reshape it now (it's only staged), don't accept a wrong shape.
- **If inspection turns up a problem, the main agent does NOT fix it itself — it dispatches a subagent to correct it** (re-instruct the same subagent, or spawn a fresh corrective one with the specifics). The main agent stays an orchestrator; fixing code inline between steps breaks that. The work is still uncommitted, so the corrective subagent just adjusts the staged changes — nothing to undo.
- After committing, decide whether the next step's scope needs adjusting before launching the next subagent.
- If a subagent discovers a needed prerequisite mid-step, pause, land the prerequisite as its own commit first, then resume — don't let it contaminate the in-progress change.
```

## Step 5 — Get the user's approval

Call **`ExitPlanMode`** to present the finished plan (body + appended Implementation Protocol) for approval — it reads the plan file you just wrote. Do not start implementing — wait for the user to review and approve.
