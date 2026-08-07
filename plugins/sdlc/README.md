# sdlc

Slash commands for the stages around writing code: gather context, agree on a direction, plan, implement through subagents, file the ticket, open the MR, drive it to green.

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
- `/sdlc:mr-open [ticket-id]` — opens a draft MR/PR for the current branch, then rewrites the title and description against the actual diff. The description targets the reviewer: why, gotchas, and where to focus.
- `/sdlc:mr-babysit [MR refs]` — drives one or more MRs toward mergeable: keeps each rebased, fixes failing CI, and answers review comments, handing back only for genuine product decisions. GitLab-only. See below.
- `/sdlc:brief-next-steps [scope hint or slug]` — compresses the session into one short briefing in `./.claude/plans/`: the final proposal in implementation order, plus the decisions you still owe. The conclusion, not the argument.

## Babysitting an MR to green

`/sdlc:mr-babysit` is the **author** side of an MR — the mirror image of `/code-review:watch`, which is the reviewer side. It changes code; the reviewer command never does.

Run it once to load the procedure, then drive the cadence with a lightweight native-loop prompt naming the MRs. Re-invoking the whole command each cycle would needlessly re-inject the entire spec:

```
/loop 2m re-check MR !123 and !456 and run the next babysit pass
```

Each pass covers **every** MR in the set — a change spanning a service repo and a pipelines repo is two MRs, and babysitting only the one in the current directory is the failure this guards against. Per MR, a pass rebases onto the target branch, triages failed CI, works through unresolved comment threads, and pushes everything as one batch.

It runs unattended by design. Rebasing, force-pushing with lease, retrying jobs, and replying to or resolving threads are all pre-authorized, and pausing to ask for them defeats the command. It stops for a rebase conflict that encodes a real product decision, a CI failure it cannot confidently fix, an attempt cap, or oscillation.

If your permission setup makes Claude Code prompt for those git operations, allowlist them once so the loop runs uninterrupted:

```jsonc
// .claude/settings.json → "permissions": { "allow": [ ... ] }
"Bash(git push:*)", "Bash(git rebase:*)", "Bash(git fetch:*)", "Bash(glab ci retry:*)"
```

Review feedback is evaluated, never rubber-stamped. Every thread reaches one of four outcomes — apply, dismiss with a reasoned reply, defer as a judgment call, or skip this pass. A bot's `critical` tag does not exempt a finding from that judgment.

Two optional CLIs make it cleaner, and it falls back to raw `glab` without them:

```bash
uv tool install glab-pipeline glab-discussion
```

## Assumptions

- **Subagent-driven execution.** The plan produced by `/sdlc:write-plan` expects a main agent that orchestrates and subagents that implement, one step at a time. Subagents stage their work and stop. The main agent inspects and owns the commit.
- **A skill per external system.** Most commands never name a specific CLI. They tell the agent to load the skill for the system in play — your issue tracker, your git host, your chat tool — so install those separately. Two commands are deliberate exceptions: `/sdlc:write-plan` loads `git:git-workflow` by name for commit shaping, and `/sdlc:mr-babysit` is GitLab-only because its loop is built on `glab`.
- **Plan files live in `./.claude/plans/`** in the working tree, not in the scratchpad. They are meant to survive the session.

## License

MIT
