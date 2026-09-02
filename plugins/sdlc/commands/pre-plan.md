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

Delegate to ONE subagent. Goal: load the full ticket and everything it transitively references — the ticket's own content and the external systems it links to. **This subagent never opens the codebase.** Reading code is Phase 3 and Phase 4 work. A ticket subagent that greps a repository or reads source files has left its scope, and what it brings back from there is noise the later phases redo properly.

The subagent must:

- Read title, description, and **all comments**.
- Inspect references, attachments, labels, project, status, links — anything rich.
- Follow links to related tickets, MRs/PRs, design docs, dashboards. Read an MR/PR through the forge CLI (`glab`, `gh`) — description, discussions, and the diff stat (which files changed, how much) — never the diff itself, and never a local checkout of the repository. Whether a diff is relevant is decided later, once the Phase 3 code map exists.
- If the ticket links to chat threads (Slack or similar) and they aren't already mirrored into ticket comments, read those threads too.
- **Dump all findings into `./.claude/plans/pre-plan-<ticket-slug>-ticket.md`** (create the directory if missing) as a single markdown file. Include: full ticket content (title, description, all comments verbatim or near-verbatim where they carry real information), summarized linked context per link, a list of every concrete code/file/table/system reference **that the ticket or its linked items mention — transcribed as written, not searched for, not verified against code** — and a list of any unresolved questions or ambiguities spotted in the ticket.
- **Return ONLY the path to that file** (plus a 2-3 sentence high-level gist). Do NOT inline the full dump into the subagent's reply — the orchestrator will read the file as needed.

The subagent prompt must open with a skill-load instruction so it doesn't waste turns guessing CLI syntax. Resolve the tracker with the `sdlc:team-workflow-identify` skill first, then name the installed skill that covers that tracker: `First, invoke the <skill-name> skill to load its usage guidance before running any commands.`

Do the same for every other system the subagent has to read. If the ticket links to chat threads, add the instruction for the chat tool's skill as well.

The prompt must also state the boundary in the subagent's own terms: `Do not open, grep, or read any repository checkout or source file. Collect only what the ticket and its links say.` Do NOT add domain hints to the prompt ("especially look for table X, class Y, DAG Z") — a hint list reads as a search brief and sends the subagent into the repositories to find the items. If the user restricted the scope (in **Scope** above or in the conversation), pass that restriction into the prompt verbatim.

## Phase 3 — Surface-level codebase exploration

Delegate to ONE subagent (`subagent_type: Explore`, breadth: `medium`). Goal: map the territory, **not** deep-dive.

- Identify the subdomains / modules / areas of the codebase that this work would touch.
- Return a short list of subdomains, each with a one-sentence description and rough pointers (top-level paths, key entrypoints).

This phase exists so the next phase can be split into focused per-subdomain dives. Resist the urge to deep-dive here.

## Phase 4 — Focused per-subdomain deep dives

For each subdomain from Phase 3, spawn a separate subagent (`subagent_type: Explore`, breadth: `very thorough`).

- The phase boundary is what must stay serial: deep dives start only after the Phase 3 surface map exists — the map is what makes them focused.
- Within the phase, **group the dives by overlap**. Dives into subdomains that barely touch each other can run **in parallel** to save wall-clock time. Dives that do overlap — shared code, one subdomain calling into another, or one dive's findings likely to reshape another's scope — run **sequentially**, so the later dive is steered by what the earlier one found.
- After each dive or parallel batch, decide whether the remaining dives' scopes need adjusting based on what was just learned.

Each subagent's goal: deeply understand the relevant code in that subdomain — what it does today, where the change pressure is, gotchas, edge cases, related tests. Return concrete file paths, function names, and current behavior.

## Phase 5 — Synthesize the briefing

Write the briefing to `./.claude/plans/pre-plan-<short-slug>.md` (slug from ticket ID or a topic kebab-case; create the directory if missing). Structure:

- **Problem** — what we're solving and why (from ticket / args / conversation).
- **Current state** — how the relevant code works today, synthesized across subdomains.
- **What would have to change** — areas of pressure. Not a chosen design.
- **Open questions & trade-offs** — what needs the user's input before a plan can be written.
- **Suggested next steps** — a short bulleted list of *directions* to consider (e.g. "approach A: change X here; approach B: extract Y"). Not a committed plan.

Omit sections that have nothing to say. No filler.

## Phase 6 — Brief the conclusion

The Phase 5 file is the argument. The user reads the conclusion first: invoke the `sdlc:brief-next-steps` skill with the same slug. It writes `./.claude/plans/<slug>-briefing.md` — the directions in implementation order, the decisions the user still owes, what is not yet verified — and it defines the chat reply.

## Hard rules

- Do NOT write a plan. Do NOT enter plan mode. Do NOT start implementing.
- Phases run strictly in order — never overlap them. Parallelism is allowed only inside Phase 4, and only for deep dives that barely overlap. No background subagents.
- Do NOT skip Phase 3 to jump straight into deep dives — the surface map is what makes the deep dives focused.
- A constraint the user stated — in **Scope** or in the conversation ("only the Airflow side", "do not touch repo X") — goes into every subagent prompt verbatim. Intersect each phase's template with what the user said. Never expand a template with detail the user did not ask for.
- Reply as `brief-next-steps` prescribes (path, line count, step headings), plus one line naming the Phase 5 file. Then stop and wait for the user to discuss before doing anything else.
