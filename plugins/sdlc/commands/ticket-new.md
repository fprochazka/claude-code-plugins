---
description: Draft and create a ticket from the current conversation context
argument-hint: [additional context]
allowed-tools: AskUserQuestion, Read, Glob, Grep, Bash, Write, Edit, Agent, Skill
---

# Create a Ticket

Use the conversation context to draft and create a ticket in the issue tracker.

$ARGUMENTS

## Ticket title

Short, imperative, specific (e.g., "Add retry logic to payment webhook handler")

## Ticket Description

- **Context**: 1-2 sentences on why this matters
- **Problem / Current behavior**: What's wrong or missing today
- **Desired outcome**: What should be true after this is done
- **Acceptance criteria**: Concrete, verifiable checklist items
- **Technical notes** (optional): Code pointers, implementation hints, constraints

## Writing Style

- Write like a "Product Engineer", not a PM writing a PRD. Be direct and specific, but make sure the business context and "WHY" is captured.
- Prefer concrete code references over abstract descriptions (e.g., "`processWebhook()` in `src/webhooks/handler.ts`" not "the webhook processing logic").
- Omit sections that have no content — don't include empty headings or filler.
- A good ticket is one a developer can pick up and start working on without asking follow-up questions.
- Make sure to not dictate to the implementor details how to solve it, at most point at relevant areas of the system
- **Write the description as if nothing has been implemented yet** — even when the work is already underway or finished in this session. This is not a formality: a ticket that narrates its own progress is unreadable a week later, and the board already tracks progress in the status field.
  - Describe the problem and the desired outcome. Never the work done against them.
  - Banned: "already done in branch X", "remaining work", "we changed Y", "this fixed Z", past tense about the fix, links to the session's branch or MR, and any "as discussed" framing.
  - Acceptance criteria are written as still-open, never pre-checked.
  - If the session revealed a constraint or a code pointer worth keeping, state it as a technical note about the *system*, not as a report of what we tried.

## Division of labor

**You (the orchestrator) write the ticket body yourself — never a subagent.** The title and the description come from the conversation you are holding, and no subagent can see it.

**A subagent does the issue tracker work** — resolving every identifier (team, status, priority, assignee, project, milestone, label) and the create call itself. That work is mechanical lookup against an API, it produces a lot of noise, and it must not eat the orchestrator's context.

## Process

1. Synthesize what you know from the conversation into a ticket draft
2. Write the description to a `<title-in-dashed-case>-description.md` markdown file in the session scratchpad dir
3. Show the user only a high-level summary and make sure to print the path to the file, you don't have to recite it from memory, the user can read it from the file.
4. Iterate if they want changes
5. Ask which **team** to file it under (unless known from previous context). Guess priority. Don't set project or labels unless asked.
6. **Pick status and assignee from the real state of the work** — this is the one place the ticket reflects that work has started:
   - **Not started** — we only discussed, designed, or discovered the problem, and no code has changed: create it in the **backlog**, unassigned.
   - **Already started** — this session (or an earlier one) has changed code for this problem, or a branch or MR for it exists: create it **in progress and assigned to the user driving the session**, so the board is not lying about what is being worked on.
   - An explicit instruction from the user overrides both defaults.
   - The status field is where "we started" belongs. The description still reads as if nothing has been implemented — see Writing Style.
7. Decide the metadata **in plain words** — team name, status name, priority name, assignee as a person, and nothing else unless the user asked for it. Do not look up a single ID yourself.
8. Delegate the creation to ONE subagent (`model: sonnet`) — see below. Wait for it, then report the result to the user.

## Creating the ticket

Spawn one subagent to resolve the identifiers and create the ticket. Its prompt must open with a skill-load instruction naming the installed skill that covers the tracker resolved by `sdlc:team-workflow-identify`: `First, invoke the <skill-name> skill to load its usage guidance before running any commands.`

Give the subagent:

- The **path to the description file**, and the instruction to read it. Never inline the description into the prompt.
- The ticket **title**, verbatim.
- The metadata **as plain words** — "team Platform, status In Progress, priority High, assign to <user>".

Tell the subagent to:

- **Resolve every identifier against the live tracker** — team, workflow state, priority, assignee, and any project or milestone the user asked for. Never guess an ID, never invent a status name that the team does not have. If a requested value has no match, pick the closest one the tracker really offers and say so in the report.
- **Use the description file as the ticket body, byte for byte.** It must not rewrite, reformat, summarize, or "improve" the text. The body is the orchestrator's work product.
- **Create the ticket**, then verify it by reading it back.
- **Report back**: the ticket ID and URL, and the final shape of the metadata — which team, status, priority, assignee, project, milestone and labels the ticket really carries, each as the human-readable name. Also report anything it had to substitute or could not set. Keep the report short — no CLI transcripts, no raw JSON dumps.

If the subagent reports a substitution that changes the meaning of the ticket, tell the user.
