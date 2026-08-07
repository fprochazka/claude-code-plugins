# code-review

Multi-agent branch code review plugin for Claude Code. Reviews conventions, architecture, design craft, bugs, performance, security, release readiness, and git history in parallel using specialized subagents.

## Usage

```
/code-review:full [focus area or specific concerns]
/code-review:post
/code-review:watch [focus area or specific concerns]
```

- `/code-review:full` — runs the multi-phase review and writes a report.
- `/code-review:post` — posts the report from the current session to the GitLab MR as inline diff comments + one summary comment. Requires a `/code-review:full` run earlier in the same session. GitLab-only.
- `/code-review:watch` — full + post, then follows the MR across review rounds until every blocker and suggestion is settled. GitLab-only.

## Watching an MR across review rounds

`/code-review:watch` reviews, posts, and then keeps following the MR until the findings are resolved. It is the **reviewer** side of an MR — the mirror image of `/sdlc:mr-babysit`, which is the author side. It never edits code, never commits, and never pushes.

**The ticket status is the handshake.** After posting a round of findings, the command moves the ticket to the author's working state. Only when the author moves it back to the review state does the next round run. This keeps the review out of work-in-progress instead of commenting on every half-finished push. Projects without a ticket fall back to a push gate.

```
review → post → ticket to WORK_STATE → [wait] → author moves ticket to REVIEW_STATE
   → sync the local branch onto the author's new head
   → revisit every open thread, reply, resolve what is settled
   → review the delta, post new findings
   → anything still open? ticket back to WORK_STATE and wait again
   → nothing open? stop
```

A cron job drives the cadence every 30 minutes. Most passes end at the gate and post nothing — a watch that stays quiet for hours is working correctly.

Details worth knowing:

- **Rebase is server-side and happens once.** If the MR is behind its target branch, the command triggers GitLab's own rebase through `glab mr rebase`. It never rebases locally. Any failure — conflicts, a fork without maintainer edits, a missing push permission — becomes a finding for the author.
- **Reviews read `origin/<source_branch>`, not local `HEAD`**, so a stale or dirty checkout cannot corrupt a review. Each round also resets the local branch onto the author's head, guarded so it never runs over uncommitted work or local-only commits.
- **Deltas use `git range-diff`, not `git diff`.** After a rebase, a plain diff mixes the author's edits with everything master gained. `range-diff` compares patch series, so carried-over commits show as unchanged and the author's real work stands out. What master brought in is checked separately, as its own question.
- **Findings close on evidence, not assertion.** A reply saying "fixed" is a pointer to verify, not proof. Every round revisits every open finding, replies in its thread, and resolves only what it confirmed.
- **State lives in a ledger** at `.claude/review-report/<topic>.watch.md`, so a round survives context compaction.
- Only `Blocking` and `Suggestion` findings gate termination. Nitpicks never keep the watch alive.

## How it works

The review runs in 4 phases:

### Phase 1 — Load Context (main thread)

Loads everything into the main context window unsummarized:
- Branch diff and commit list
- MR/PR description, comments, and pipeline status
- Ticket description and acceptance criteria

### Phase 2 — Explore Surrounding Code (single subagent)

An Explore subagent builds understanding of the touched code areas — callers, callees, data flow, downstream effects, and previous state.

### Phase 3 — Parallel Review (8 subagents)

Eight specialized review agents run in parallel, each with its own checklist and scope. They receive the branch range and fetch their own git data.

| Agent | Scope | Color |
|---|---|---|
| `review-conventions` | Documented conventions, naming, test structure, annotations | cyan |
| `review-architecture` | Module placement, layers, coupling, abstractions, API design, dependency direction | blue |
| `review-code-design` | Opinionated design-craft improvement hints: functional-core purity, rich domain models, value objects, right-sized abstraction, intent-revealing clarity | orange |
| `review-bugs` | Logic errors, edge cases, error handling, race conditions, lost updates, resource leaks | red |
| `review-performance` | Data-access efficiency (N+1, eager/lazy loading, preload-before-logic), query cost, transaction scope, caching, memory | purple |
| `review-security` | Injection, auth, secrets, input validation, XSS, OWASP | yellow |
| `review-release` | Deployment risks: migrations, messaging infra, config changes, API contracts, rollback safety | magenta |
| `review-git-history` | Commit atomicity, refactoring separation, fixup detection, message format | green |

Each agent returns structured findings with confidence ratings (0-100).

### Phase 4 — Validate & Report (main thread)

The main agent validates every finding against its full unsummarized context. Findings that can't be verified are dropped. The final report is written to `.claude/review-report/<topic>.md` in the project directory.

## Design decisions

- **Context stays unsummarized** — Phase 1 loads MR/ticket/diff directly into main context so validation in Phase 4 has full fidelity
- **Agents fetch their own git data** — the orchestrator passes only the branch range (`<base>...HEAD`), avoiding context-passing errors
- **Each agent knows its boundaries** — explicit "Out of Scope" sections prevent duplicate findings across agents
- **No automatic filtering by confidence** — the main agent verifies findings manually rather than relying on a numeric threshold
- **Platform-agnostic** — works with any code hosting platform and issue tracker

## Installation

```bash
claude plugin marketplace add fprochazka/claude-code-plugins --scope user
claude plugin install code-review@fprochazka-claude-code-plugins --scope user
```
