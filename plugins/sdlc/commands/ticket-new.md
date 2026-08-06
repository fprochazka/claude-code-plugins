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
7. Create the ticket in the issue tracker using the appropriate skill.
