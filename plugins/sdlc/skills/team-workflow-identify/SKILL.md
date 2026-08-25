---
name: team-workflow-identify
description: Identify the project's issue tracker, team, ticket conventions and workflow state names before any command touches a ticket. Use when asked "which status should this move to", "move the ticket", "mark it ready for review", "what is the team workflow", "which issue tracker states exist", or when a ticket has to change state. The sdlc and code-review commands invoke this skill by name and consume its output block.
trigger-keywords: ticket status, workflow states, issue tracker, move the ticket, ready for review, team workflow
---

# team-workflow-identify

Ground the agent in the project's issue tracker, team and workflow states **before** any command reads or moves a ticket. Every value is discovered at run time. This skill hardcodes no team name, no team id and no status name — a skill that carries them turns stale the day someone renames a state.

The output is the block in "Output contract" below. Print it, and the calling command carries it for the rest of the run.

## Source order

The order is fixed. Do not skip ahead.

1. **Context already loaded.** `CLAUDE.md`, `AGENTS.md`, everything they pull in through `@` includes, and any memory already in context. These are free to read and they are the place a team writes its own conventions down. Search the context you already hold first — a `CLAUDE.md` that is a single `@README.md` line answers nothing on disk while its included content sits in your context. Grep the files on disk as a supplement, and follow every `@` include you find:

   ```bash
   grep -rniE 'linear|jira|gitlab issue|github issue|team (key|id)|status|workflow|ticket|branch nam|^@' CLAUDE.md AGENTS.md 2>/dev/null | head -30
   ```

2. **The repo `README.md`.** Many repos repeat the tracker facts there.

3. **The tracker API — last resort, and never silent.** See "Stop before the API".

## Stop before the API

If sources 1 and 2 do not answer, **stop and tell the user what is missing**. Do not go fishing through the API on your own. An API answer that lands nowhere is discovered again on every future run.

Offer two ways to persist the answer, and name the concrete file for each:

- An edit to one of the loaded convention files — say which one, for example `./AGENTS.md` or `./CLAUDE.md`.
- A Claude memory.

The user picks. Then query the tracker API, write the result into the chosen place, and continue. The next run reads it from source 1.

## What to extract

- **Tracker** — Linear, Jira, GitLab issues, GitHub issues, or none.
- **Team** — display name, key, and id where the tracker has one. These are three different strings for one team. Never derive one from another.
- **Ticket ID pattern** — `TEAM-123`, `#123`, or a tracker URL. The commands parse branch names and MR titles with it.
- **Branch convention** — the documented pattern if there is one, for example `<initials>/<TICKET>-<slug>`. Report `none` when nothing documents it, and do not invent one from the branches that happen to exist.
- **Workflow states** — see below.

## Resolve states by name, not by type

**Match every workflow state by its name. Assert its `type` only as a sanity check.** A tracker's type field groups states far too coarsely to identify one. In Linear, `type == "started"` can cover In Progress, In Review, Blocked and Ready To Deploy at once — four states, one type, and the type tells you nothing about which is which.

Map these roles onto the actual state names:

- **`WORK_STATE`** — the author is working on it. Typically "In Progress", "In Development", "Doing".
- **`REVIEW_STATE`** — the author says it is ready to look at. Typically "In Review", "Ready for Review".
- **`DEPLOY_STATE`** — merged and waiting to ship, for example "Ready To Deploy". Many teams have no such state. Report `none` and do not substitute a terminal state for it.
- **Terminal states** — the states that close a ticket, for example "Done" and "Rejected".

Two rules protect this mapping:

- **A role that does not resolve is reported, never approximated.** A renamed state must stop resolving loudly. Falling back to "any state whose type is completed" closes a ticket that never shipped.
- **If several names are plausible for one role, ask the user once, here** — before any command posts or moves anything.

## Disagreement stops the run

If a recorded value and the tracker API disagree — a different team id, a state name that no longer exists — **stop and report the disagreement**. Never pick one silently. The two sources disagree about which team and which board the run is about to act on.

## Gotchas

- **Read the top-level status field on an issue payload.** In Linear, nested `state` blocks belong to sub-issues. Reading one mixes a sub-issue's status into the parent's.
- **Load the skill that matches the resolved tracker for command syntax.** Once this skill has named the tracker, look through the installed skills for the one that covers it and invoke it before the first tracker call. The exact commands live in that skill, never here.
- **No tracker is a valid answer.** Report `tracker: none` and let the caller fall back. `/code-review:watch`, for example, paces itself on the MR head SHA instead of a ticket status.

## Output contract

Print this block at the end of the run. The calling command reads it and re-derives nothing.

```
tracker: <linear|gitlab|github|jira|none>
team: <name> (<key>, <id>)
ticket pattern: <regex or example>
branch convention: <pattern or none>
WORK_STATE: <name>   REVIEW_STATE: <name>   DEPLOY_STATE: <name|none>   terminal: <names>
source: <every file that answered, comma-separated | API + persisted to <where>>
```

The `source` line matters as much as the values. It tells the user whether the run trusted a recorded convention or went to the API, and where a fresh answer landed. When two files answered and agreed, list both. When they disagree, the run has already stopped under "Disagreement stops the run".
