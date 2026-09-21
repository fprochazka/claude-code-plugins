# sdlc

Slash commands for the stages around writing code: gather context, agree on a direction, plan, implement through subagents, file the ticket, open the MR, drive it to green.

The plugin serves one product engineer on one task. The starting point is a vague problem statement; the work is to establish how the system behaves today — for the agent's benefit more than yours — then to design the change and land it reliably. It is not a tool for starting a project from nothing or for planning a body of work into many tickets: every command assumes a single ticket, a single branch, a single MR set.

The commands are deliberately separate. Each one ends by handing control back to you — no command silently rolls into the next stage.

## The flow

```
pre-plan → (discuss) → write-plan → (implement) → mr-open → mr-babysit → wrap-up
                ticket-new ↗                       ticket-attach-docs ↗
```

1. `/sdlc:pre-plan` reads the ticket, or takes the problem from you, and writes the context file and its briefing. The ticket is not touched.
2. You discuss the briefing. `/sdlc:ticket-new` files the ticket here when there was none; it creates it in progress and assigned to you when the work has already started.
3. `/sdlc:write-plan` turns the agreed direction into a plan whose steps are the intended commits, then hands the plan to the implementation subagent it describes.
4. `/sdlc:mr-open` opens the draft MR and writes the Why into the ticket.
5. `/sdlc:mr-babysit` drives the MR to green, marks it ready and moves the ticket to the review state; when the reviewer hands the work back it moves the ticket to the work state again. The handshake is described below.
6. `/sdlc:wrap-up` attaches the documents through `/sdlc:ticket-attach-docs`, posts the outcome, and marks the ticket completed. `ticket-attach-docs` also runs on its own once the plan is approved, so the plan reaches the ticket before the work starts.

Keep steps 1 to 3 in one context window: the discussion and the plan build on what `pre-plan` learned, and a summary of it is not the same thing. From step 3 on, the plan file in `./.claude/plans/` and the babysit ledger in `./.claude/review-report/` hold the state, so a fresh window can pick up at any later step — `wrap-up` writes the best comment from the session that did the work, because the findings the diff does not show live only there.

## Installation

```bash
claude plugin marketplace add fprochazka/claude-code-plugins --scope user
claude plugin install sdlc@fprochazka-claude-code-plugins --scope user
```

## Slash commands

Each is a skill with `disable-model-invocation` off, so Claude may also reach for one on its own when the situation matches its description.

- `/sdlc:pre-plan [ticket ref or problem description]` — gathers the context needed to **discuss** a solution. Reads the ticket and everything it links to, maps the affected subdomains, then runs one focused deep dive per subdomain. Writes the full context file to `./.claude/plans/`, then runs `/sdlc:brief-next-steps` on it so the chat reply is the short conclusion and the long file stays the argument. Where the current flow or the change pressure reads better as a picture, the file gets a mermaid diagram, drawn and validated through `diagrams:mermaid`, and the briefing carries it over verbatim. It does not plan and does not implement.
- `/sdlc:brief-next-steps [scope hint or slug]` — compresses the session into one short briefing in `./.claude/plans/`: the final proposal in implementation order, plus the decisions you still owe. The conclusion, not the argument.
- `/sdlc:ticket-new [extra context]` — drafts a ticket from the conversation and files it in the issue tracker. Written from the product-engineer angle: business context and acceptance criteria, no solution dictated to the implementor.
- `/sdlc:write-plan [topic, ticket ref, or briefing path]` — enters plan mode and writes an implementation plan whose steps map onto the intended atomic commits. Appends an implementation protocol so the execution rules travel with the plan file. Normally run after `/sdlc:pre-plan` and a design discussion.
- `/sdlc:mr-open [ticket-id]` — opens a draft MR/PR for the current branch, then writes each piece where it belongs. The Why — problem, constraints, the decision behind the approach — goes into the ticket: into the body when it is empty or a stub, as a comment when the body already carries content. The reading guide for the reviewer, the release procedure and the measured results go onto the MR as separate comment threads, each posted only when it has something to say and each signed `<!-- sdlc:mr-open -->`. The description stays one screen: the ticket link, three to six sentences on what the change does, and a pointer to the release comment when there is one. A change a reviewer would follow faster from a picture gets a diagram in the guidelines comment, drawn through `diagrams:mermaid`.
- `/sdlc:mr-babysit [MR refs]` — drives one or more MRs toward mergeable: keeps each rebased, fixes failing CI, and answers review comments, handing back only for genuine product decisions. When the set is green and settled it marks the MRs ready, moves the ticket to the review state, and keeps a background watcher on the MRs in case the reviewer hands the work back. GitLab-only. See below.
- `/sdlc:ticket-attach-docs [ticket ref]` — attaches the documents the work produced to the ticket: the briefing and the implementation plan always, the rest by judgment. It reads what the ticket already holds, then picks the carrier the tracker offers: a document it can update in place, an attachment, an inline comment, or a link to the file on the branch. It never attaches the pre-plan ticket dump, which is the ticket's own content read back out.
- `/sdlc:wrap-up [ticket ref]` — closes finished work out. Attaches the documents first, so they land even when the close decision needs you. Then posts a dense comment to the ticket — outcome, the production checks with their real numbers, findings the diff does not show, limits, possible follow-ups — and marks the ticket completed. It splits into several comments when one would bury its own best parts. Facts only: it never commits anyone to future work.

## Babysitting an MR to green

`/sdlc:mr-babysit` is the **author** side of an MR — the mirror image of `/code-review:watch`, which is the reviewer side. It changes code; the reviewer command never does.

The command runs in your session and decides; it does not watch and it does not write code. The `glab:mr-watch` agent from the **glab** plugin watches the MRs in the background and messages the command every time something moves: a pipeline finishing, a push, new comments, a draft or ticket flip, the merge. An actor subagent — the implementation subagent from the plan when it is still alive, a fresh one otherwise — then reads the evidence and turns every failed job and open thread into a proposal: fix it, dismiss it, or ask you. The command approves or overturns each proposal, keeps the ledger of what is and is not solved, and sends the approved rows back to the actor to implement, post and push. Its rules live in [`skills/mr-babysit/references/actor-brief.md`](skills/mr-babysit/references/actor-brief.md). The watcher sends a heartbeat every 30 minutes, which becomes your progress line whether or not anything moved; a cron on the same interval only checks that the watcher is still alive and speaks only when it has to respawn it.

The watcher covers **every** MR in the set — a change spanning a service repo and a pipelines repo is two MRs, and babysitting only the one in the current directory is the failure this guards against.

It runs unattended by design. Rebasing, force-pushing with lease, retrying jobs, and replying to or resolving threads are all pre-authorized for every subagent, and pausing to ask for them defeats the command. It stops for a rebase conflict that encodes a real product decision, a CI failure it cannot confidently fix, an attempt cap, oscillation, or three hours with nothing moving.

If your permission setup makes Claude Code prompt for those git operations, allowlist them once so the loop runs uninterrupted:

```jsonc
// .claude/settings.json → "permissions": { "allow": [ ... ] }
"Bash(git push:*)", "Bash(git rebase:*)", "Bash(git fetch:*)", "Bash(glab ci retry:*)", "Bash(glab mr update:*)"
```

Review feedback is evaluated, never rubber-stamped. Every thread ends as a fix, a dismissal with a reasoned reply, or a question for you. A bot's `critical` tag does not exempt a finding from that judgment. A thread whose last reviewer note is marked `<!-- code-review:watch -->` is the exception to the resolve rules: it gets the fix and a reply, and stays unresolved. `teamwork:review-handshake` says why.

### The handshake with the reviewer

The protocol lives in the [teamwork plugin](../teamwork/), shared with `/code-review:watch`: `teamwork:review-handshake` for the handover, `teamwork:workflow-identify` for the state names, both read at run time, plus `glab:mr-status` and the `glab:mr-watch` agent from the **glab** plugin for MR state. `/sdlc:mr-babysit` moves the ticket back to the work state, with a comment saying why, whenever it takes work back after a handover — behind its target branch, red pipeline, open threads, or a fix about to land. When everything is green, quiet and settled, it moves the ticket to the review state and marks every MR ready, then keeps watching in case the reviewer hands the work back. It stops for good when the MRs merge, when the ticket reaches a terminal state, or after three hours with nothing moving; say "stop after handoff" to opt out of the wait.

Two CLIs are required, and the command asks you to install them when they are missing:

```bash
uv tool install glab-pipeline glab-discussion
```

## Assumptions

- **Subagent-driven execution.** The plan produced by `/sdlc:write-plan` expects a main agent that orchestrates and one persistent implementation subagent that works step after step, keeping its repo exploration in context. The subagent stages its work and stops. The main agent checks every step — directly for trivial ones, through a fresh validation subagent for the rest — and owns the commit.
- **A skill per external system.** Most commands never name a specific CLI. They tell the agent to load the skill for the system in play — your issue tracker, your git host, your chat tool — so install those separately. Three commands are deliberate exceptions: `/sdlc:write-plan` and `/sdlc:mr-open` load `git:git-workflow` by name for commit shaping, `/sdlc:mr-open` also names `glab-discussion` for the MR comment threads it posts on GitLab, and `/sdlc:mr-babysit` is GitLab-only because its loop is built on `glab`.
- **Plan files live in `./.claude/plans/`** in the working tree, not in the scratchpad. They are meant to survive the session.

## License

MIT
