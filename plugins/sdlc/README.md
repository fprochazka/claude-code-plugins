# sdlc

Slash commands for the stages around writing code: gather context, agree on a direction, plan, implement through subagents, file the ticket, open the MR.

The commands are deliberately separate. Each one ends by handing control back to you — no command silently rolls into the next stage.

## Installation

```bash
claude plugin marketplace add fprochazka/claude-code-plugins --scope user
claude plugin install sdlc@fprochazka-claude-code-plugins --scope user
```

## Commands

- `/sdlc:pre-plan [ticket ref or problem description]` — gathers the context needed to **discuss** a solution. Reads the ticket and everything it links to, maps the affected subdomains, then runs one focused deep dive per subdomain. Writes a briefing to `./.claude/plans/` and stops. It does not plan and does not implement.
- `/sdlc:write-plan [topic, ticket ref, or briefing path]` — enters plan mode and writes an implementation plan whose steps map onto the intended atomic commits. Appends an implementation protocol so the execution rules travel with the plan file. Normally run after `/sdlc:pre-plan` and a design discussion.
- `/sdlc:ticket-new [extra context]` — drafts a ticket from the conversation and files it in the issue tracker. Written from the product-engineer angle: business context and acceptance criteria, no solution dictated to the implementor.
- `/sdlc:open-mr [ticket-id]` — opens a draft MR/PR for the current branch, then rewrites the title and description against the actual diff. The description targets the reviewer: why, gotchas, and where to focus.
- `/sdlc:brief-next-steps [scope hint or slug]` — compresses the session into one short briefing in `./.claude/plans/`: the final proposal in implementation order, plus the decisions you still owe. The conclusion, not the argument.

## Assumptions

- **Subagent-driven execution.** The plan produced by `/sdlc:write-plan` expects a main agent that orchestrates and subagents that implement, one step at a time. Subagents stage their work and stop. The main agent inspects and owns the commit.
- **A skill per external system.** The commands never name a specific CLI. They tell the agent to load the skill for the system in play — your issue tracker, your git host, your chat tool — so install those separately. `/sdlc:write-plan` is the one exception: it loads `git:git-workflow` by name for commit shaping.
- **Plan files live in `./.claude/plans/`** in the working tree, not in the scratchpad. They are meant to survive the session.

## License

MIT
