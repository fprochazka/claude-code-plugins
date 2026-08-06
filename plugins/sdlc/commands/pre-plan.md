---
description: Gather context for a problem (ticket + code exploration) before discussing a solution and writing a plan
argument-hint: [ticket ref or freeform problem description]
allowed-tools: AskUserQuestion, Read, Bash, Agent, Skill
---

# Pre-Planning Context Gathering

Gather everything needed to **discuss a solution with the user**, so a plan can be written afterward and then implemented. You are NOT writing a plan in this command, and you are NOT implementing anything. The output is a context briefing for discussion.

## Scope

$ARGUMENTS

## Phase 1 — Decide the source

Inspect the **Scope** above:

- **Looks like a ticket ref** (e.g. `ABC-1234`, a Linear/GitHub/GitLab URL, `#789`): treat as ticket → run Phase 2.
- **Looks like a freeform problem description**: skip Phase 2, use the description as the brief.
- **Empty**: use the current conversation context. If it's unclear what we're gathering context for, ask the user before proceeding.

## Phase 2 — Read the ticket (only if a ticket ref was given)

Delegate to ONE subagent. Goal: load the full ticket and everything it transitively references.

The subagent must:

- Read title, description, and **all comments**.
- Inspect references, attachments, labels, project, status, links — anything rich.
- Follow links to related tickets, MRs/PRs, design docs, dashboards.
- If the ticket links to chat threads (Slack or similar) and they aren't already mirrored into ticket comments, read those threads too.
- **Dump all findings into `./.claude/plans/pre-plan-<ticket-slug>-ticket.md`** (create the directory if missing) as a single markdown file. Include: full ticket content (title, description, all comments verbatim or near-verbatim where they carry real information), summarized linked context per link, a list of every concrete code/file/system reference found, and a list of any unresolved questions or ambiguities spotted in the ticket.
- **Return ONLY the path to that file** (plus a 2-3 sentence high-level gist). Do NOT inline the full dump into the subagent's reply — the orchestrator will read the file as needed.

The subagent prompt must open with a skill-load instruction so it doesn't waste turns guessing CLI syntax. Name the skill that covers the issue tracker in use — whatever is installed for Linear, Jira, GitHub, GitLab, and so on: `First, invoke the <skill-name> skill to load its usage guidance before running any commands.`

Do the same for every other system the subagent has to read. If the ticket links to chat threads, add the instruction for the chat tool's skill as well.

## Phase 3 — Surface-level codebase exploration

Delegate to ONE subagent (`subagent_type: Explore`, breadth: `medium`). Goal: map the territory, **not** deep-dive.

- Identify the subdomains / modules / areas of the codebase that this work would touch.
- Return a short list of subdomains, each with a one-sentence description and rough pointers (top-level paths, key entrypoints).

This phase exists so the next phase can be split into focused per-subdomain dives. Resist the urge to deep-dive here.

## Phase 4 — Focused per-subdomain deep dives

For each subdomain from Phase 3, spawn a separate subagent (`subagent_type: Explore`, breadth: `very thorough`).

- Run them **one by one, sequentially** — never in parallel, never in the background. The user wants visibility into what each subagent is doing.
- After each dive, decide whether the next dive's scope should be adjusted based on what was just learned.

Each subagent's goal: deeply understand the relevant code in that subdomain — what it does today, where the change pressure is, gotchas, edge cases, related tests. Return concrete file paths, function names, and current behavior.

## Phase 5 — Synthesize the briefing

Write the briefing to `./.claude/plans/pre-plan-<short-slug>.md` (slug from ticket ID or a topic kebab-case; create the directory if missing). Structure:

- **Problem** — what we're solving and why (from ticket / args / conversation).
- **Current state** — how the relevant code works today, synthesized across subdomains.
- **What would have to change** — areas of pressure. Not a chosen design.
- **Open questions & trade-offs** — what needs the user's input before a plan can be written.
- **Suggested next steps** — a short bulleted list of *directions* to consider (e.g. "approach A: change X here; approach B: extract Y"). Not a committed plan.

Omit sections that have nothing to say. No filler.

## Hard rules

- Do NOT write a plan. Do NOT enter plan mode. Do NOT start implementing.
- Do NOT run subagents in parallel or in the background.
- Do NOT skip Phase 3 to jump straight into deep dives — the surface map is what makes the deep dives focused.
- Present the briefing and stop. Wait for the user to discuss before doing anything else.
