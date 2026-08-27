# code-review

Multi-agent branch code review plugin for Claude Code. Reviews conventions, architecture, design craft, bugs, performance, security, release readiness, git history, and documentation in parallel using specialized subagents.

## Usage

```
/code-review:full [focus area or specific concerns]
/code-review:post
/code-review:watch [focus area or specific concerns]
```

- `/code-review:full` — runs the multi-phase review and writes a report.
- `/code-review:post` — posts the report from the current session to the GitLab MR as inline diff comments + one summary comment. Requires a `/code-review:full` run earlier in the same session. GitLab-only.
- `/code-review:watch` — full + post, then follows the MR across review rounds until every blocker and suggestion is settled. It is the reviewer side of an MR, the mirror image of `/sdlc:mr-babysit`. It never edits code, commits, or pushes. GitLab-only. See [the handshake](#the-handshake-with-the-author).

## The handshake with the author

`/code-review:watch` is paced by two flags it shares with `/sdlc:mr-babysit`.

Ready-for-review means the MR is **not draft** AND the ticket is in `REVIEW_STATE`. Back-to-work means the MR is **draft** AND the ticket is in `WORK_STATE`. The two flags always move together, and whoever hands the ball over sets both.

After posting a round of findings, the watch sets the MR to draft and moves the ticket to `WORK_STATE`. Every cron pass then checks both flags and does nothing until both say ready-for-review. A ticket in the review state while the MR is still draft is not a handover, and the pass stays silent. This is what keeps the review out of half-finished pushes.

The author side replies to a `<!-- code-review:watch -->` thread but never resolves one on its own. The watch resolves the threads it verified, so a watch thread resolved without its verdict was closed on a human's decision — by the person, or by the author agent on the person's instruction. When the code at the MR head still shows the problem, the watch un-resolves the thread and names the line that still shows it.

The tracker and its state names are never hardcoded. The command resolves them at run time through the `sdlc:team-workflow-identify` skill, and reads MR state through the `glab:mr-status` skill. Install the **sdlc** and **glab** plugins alongside this one for the full watch. Without them the command falls back to reading the MR through `glab` and listing the tracker's states itself. With no tracker at all it falls back to a push gate on the draft flag plus a new head SHA.

## How it works

The review runs in 4 phases:

### Phase 1 — Load Context (main thread)

Loads everything into the main context window unsummarized:
- Branch diff and commit list
- MR/PR description, comments, and pipeline status
- Ticket description and acceptance criteria

### Phase 2 — Explore Surrounding Code (single subagent)

An Explore subagent builds understanding of the touched code areas — callers, callees, data flow, downstream effects, and previous state.

### Phase 3 — Parallel Review (9 subagents)

Nine specialized review agents run in parallel, each with its own checklist and scope. They receive the branch range and fetch their own git data.

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
| `review-docs` | Comments, doc comments, and docs files: text that repeats the code or narrates the change, non-obvious code left unexplained, knowledge duplicated or documented in the wrong place | pink |

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
