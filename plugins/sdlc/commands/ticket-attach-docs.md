---
description: Attach the session's plan and research documents to the ticket, as tracker documents where they exist and as attachments or comments otherwise
argument-hint: [ticket ref or extra context]
allowed-tools: AskUserQuestion, Read, Glob, Bash, Agent, Skill
---

# Attach Documents to the Ticket

Put the work's durable documents where the next person looks: on the ticket. The plan and the research behind it live in `./.claude/plans/` in one worktree on one machine; the ticket outlives both. Attach only what already exists.

## Scope

$ARGUMENTS

## Process

1. **Resolve the ticket.** Take it from the session; this command usually runs at the end of the work, so the ticket is already in the conversation. The scope above only narrows or overrides that. Fall back to the branch name or the MR title, and ask the user only when the session covered several tickets. Load the skill for the tracker in play if it is not loaded yet. If you do not know which tracker that is, invoke `sdlc:team-workflow-identify` first.
2. **Collect the candidates.** Every file in `./.claude/plans/`, plus any dump this session wrote elsewhere (a chat thread export, a query result, a dashboard reading). Match them to the ticket by ID or slug. Where the slugs do not line up, use what the session knows about which files it wrote.
3. **Judge each candidate** by the rules under "What is worth attaching". Read a file before you attach it; you are copying it to a place other people read.
4. **Inventory the ticket through one subagent** (`model: sonnet`). Open its prompt with the skill-load instruction so it does not guess CLI syntax: `First, invoke the <skill-name> skill to load its usage guidance before running any commands.` Ask it for what the ticket already holds: its documents with their identifiers and titles, its attachments, and any comment that carries an earlier copy of the same material. Name the candidate files' titles so it can compare. Ask it also which carriers the tracker offers: documents, file attachments, comments. It returns the inventory as a list, nothing else. Keep this subagent; step 6 resumes it.
5. **Decide and propose once.** The inventory decides create, update, or skip per file, and it shows which carrier the ticket already uses. Show the user one list: per file, the verdict, the carrier, and whether it creates or updates. Confirm before anything is uploaded.
6. **Resume the same subagent for the upload.** Message it the confirmed list, not a fresh subagent: it already holds the ticket state and the skill, and a new one would load both again. Per file give the path, the title, the carrier, and create or update with the identifier from its own inventory. It reads each file into the command from disk, never pastes content into the prompt or the reply. It returns one line per file: what it did and the URL. It does not judge, reorder, or edit anything. If an upload fails, it reports the failure; it does not retry with another carrier.
7. **Report** what landed where, with URLs, and one line per skipped file saying why.

## What is worth attaching

**Always, without asking:**

- The briefing (`<slug>-briefing.md`): the conclusion in implementation order.
- The implementation plan: the plan-mode file that drove the work, including the decisions recorded into it mid-flight.

**Never:**

- `pre-plan-<slug>-ticket.md`. It is the ticket's own content read back out. Attaching it to the ticket duplicates the ticket.
- Any other file that copies material the ticket already carries.

**Judge the rest.** The test: does this file carry something that exists nowhere else, and would someone have to redo the work to get it back? A chat thread nobody mirrored into the ticket passes. So does a production query with its results, and the pre-plan synthesis when it explains how the code works today. A superseded draft fails. So does anything the wrap-up comment already states, and a file that only restates the diff.

Two things stop an attachment regardless of value:

- **Reach.** A dump from an internal system goes on the ticket only if everyone who can read the ticket may see that content.
- **Secrets.** Never upload tokens, credentials, or connection strings. Skip the file and say so; do not silently edit it.

## Where to put them

The tracker decides. Resolve the carrier at run time, never assume the tracker has documents, and prefer the form the ticket already uses.

1. **A document attached to the ticket.** Best case: it has a stable identifier, so a later run updates the same document instead of adding a second one.
2. **A file attachment on the ticket or on a comment.**
3. **A comment carrying the content inline.** Only for a short file. A long one buries every other comment in the thread.
4. **A link.** If the file is committed on the branch, link to it in a comment instead of copying it. Check that it is actually committed; plan directories are often ignored.

Title every document with the ticket ID and what it is, for example `ABC-123 — implementation plan`. The title is the key that the next run matches on.

## Running it again

Repeat runs are normal: you attach the same work once the plan is approved and again at wrap-up.

- Document carrier: match by title and **update in place**. Never create a second document for the same file.
- Attachment and comment carriers only append. Compare the content first, and upload again only when it changed. Unchanged content is a skip, not an update.

## Hard rules

- Do not change the ticket's state, assignee, labels, project, or priority. Attaching documents is all this command does.
- Do not write, rewrite, or reformat a document to attach it. What is in the file is what goes up.
- Do not go exploring. The candidates are the files the session already has; a document that was never written is not a gap to fill here.
- Do not touch code, git, or the MR.
