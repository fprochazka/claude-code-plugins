# sdlc

Slash commands for the stages around writing code: gather context, agree on a direction, plan, implement through subagents, file the ticket, open the MR, drive it to green.

The commands are deliberately separate. Each one ends by handing control back to you — no command silently rolls into the next stage.

## Installation

```bash
claude plugin marketplace add fprochazka/claude-code-plugins --scope user
claude plugin install sdlc@fprochazka-claude-code-plugins --scope user
```

## Commands

- `/sdlc:pre-plan [ticket ref or problem description]` — gathers the context needed to **discuss** a solution. Reads the ticket and everything it links to, maps the affected subdomains, then runs one focused deep dive per subdomain. Writes the full context file to `./.claude/plans/`, then runs `/sdlc:brief-next-steps` on it so the chat reply is the short conclusion and the long file stays the argument. It does not plan and does not implement.
- `/sdlc:write-plan [topic, ticket ref, or briefing path]` — enters plan mode and writes an implementation plan whose steps map onto the intended atomic commits. Appends an implementation protocol so the execution rules travel with the plan file. Normally run after `/sdlc:pre-plan` and a design discussion.
- `/sdlc:ticket-new [extra context]` — drafts a ticket from the conversation and files it in the issue tracker. Written from the product-engineer angle: business context and acceptance criteria, no solution dictated to the implementor.
- `/sdlc:mr-open [ticket-id]` — opens a draft MR/PR for the current branch, then rewrites the title and description against the actual diff. The description targets the reviewer: why, gotchas, and where to focus.
- `/sdlc:mr-babysit [MR refs]` — drives one or more MRs toward mergeable: keeps each rebased, fixes failing CI, and answers review comments, handing back only for genuine product decisions. When the set is green and settled it marks the MRs ready, moves the ticket to the review state, and keeps waiting on a slow cron in case the reviewer hands the work back. GitLab-only. See below.
- `/sdlc:wrap-up [ticket ref]` — closes finished work out. Posts a dense comment to the ticket — outcome, the production checks with their real numbers, findings the diff does not show, limits, possible follow-ups — then marks the ticket completed. It splits into several comments when one would bury its own best parts. Facts only: it never commits anyone to future work.
- `/sdlc:brief-next-steps [scope hint or slug]` — compresses the session into one short briefing in `./.claude/plans/`: the final proposal in implementation order, plus the decisions you still owe. The conclusion, not the argument.

## Skills

- `sdlc:team-workflow-identify` — resolves the issue tracker, the team, the ticket ID pattern, the branch convention and the workflow state names, then prints them as one block the calling command carries. Reads `CLAUDE.md` / `AGENTS.md` first, the repo `README.md` second, and asks before it falls back to the tracker API — so the answer gets written down instead of rediscovered every run. It hardcodes no team or status name. See [`skills/team-workflow-identify/SKILL.md`](skills/team-workflow-identify/).

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
"Bash(git push:*)", "Bash(git rebase:*)", "Bash(git fetch:*)", "Bash(glab ci retry:*)", "Bash(glab mr update:*)"
```

Review feedback is evaluated, never rubber-stamped. Every thread reaches one of four outcomes — apply, dismiss with a reasoned reply, defer as a judgment call, or skip this pass. A bot's `critical` tag does not exempt a finding from that judgment. One thread type is the exception to the resolve rules: a thread whose last reviewer note is marked `<!-- code-review:watch -->` gets the fix and a reply, and stays unresolved. The reviewer verifies it against the code and resolves it.

### The handshake with the reviewer

Ready-for-review means the MR is **not draft** AND the ticket is in `REVIEW_STATE`. Back-to-work means the MR is **draft** AND the ticket is in `WORK_STATE`. The two flags always move together, and whoever hands the ball over sets both. `/code-review:watch` reads the same two flags and sets them the same way, so a half-set handshake either starts a review of work in progress or leaves a finished MR unreviewed.

`/sdlc:mr-babysit` claims an MR back to draft whenever a pass finds work to do on it — behind its target branch, red pipeline, or open threads. When everything is green, quiet and settled with no judgment call outstanding, it marks the MRs ready and moves the ticket to `REVIEW_STATE`.

Then it does not stop. It swaps the 2-minute `/loop` for a recurring cron every 30 minutes and waits. If the reviewer hands the work back — ticket in `WORK_STATE` or the MR in draft again — it deletes the cron, re-arms the fast loop, and runs a normal pass. It stops for good when the MRs merge or the ticket reaches a terminal state. Say "stop after handoff" to opt out of the wait.

The workflow state names are never hardcoded. Both commands resolve them at run time through the `sdlc:team-workflow-identify` skill, and both read MR state through the `glab:mr-status` skill from the **glab** plugin. With no tracker, the handshake degrades to the draft flag alone.

Two optional CLIs make it cleaner, and it falls back to raw `glab` without them:

```bash
uv tool install glab-pipeline glab-discussion
```

## Assumptions

- **Subagent-driven execution.** The plan produced by `/sdlc:write-plan` expects a main agent that orchestrates and one persistent implementation subagent that works step after step, keeping its repo exploration in context. The subagent stages its work and stops. The main agent checks every step — directly for trivial ones, through a fresh validation subagent for the rest — and owns the commit.
- **A skill per external system.** Most commands never name a specific CLI. They tell the agent to load the skill for the system in play — your issue tracker, your git host, your chat tool — so install those separately. Two commands are deliberate exceptions: `/sdlc:write-plan` loads `git:git-workflow` by name for commit shaping, and `/sdlc:mr-babysit` is GitLab-only because its loop is built on `glab`.
- **Plan files live in `./.claude/plans/`** in the working tree, not in the scratchpad. They are meant to survive the session.

## License

MIT
