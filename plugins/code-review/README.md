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

`/code-review:watch` is paced by the ticket state it shares with `/sdlc:mr-babysit`; the protocol, and what each side may do to the other's threads, is in the [teamwork plugin](../teamwork/) — `teamwork:review-handshake` for the handover and `teamwork:workflow-identify` for the state names, both read at run time. After posting a round of findings the watch moves the ticket to `WORK_STATE` and leaves the draft flag alone, then waits for the `glab:mr-watch` agent from the **glab** plugin to report ready-for-review again; its 30-minute heartbeat is the progress line, and a cron on the same interval only respawns a dead watcher. The watch resolves the threads it verified, and un-resolves one whose problem the code at the MR head still shows. The **teamwork** and **glab** plugins are declared dependencies, so installing this one installs both; with no tracker at all the watch falls back to a push gate on the draft flag plus a new head SHA.

## How it works

The review runs in 4 phases:

### Phase 1 — Load Context (main thread)

Loads everything into the main context window unsummarized:
- Branch diff and commit list
- MR/PR description, comments, and pipeline status
- Ticket description and acceptance criteria

### Phase 2 — Explore Surrounding Code and Conventions (two subagents)

Two Explore subagents run in parallel. One builds understanding of the touched code areas — callers, callees, data flow, downstream effects, and previous state. The other maps where the project keeps its rules: convention docs, module docs, and the lint, format, and static-analysis configs, including the ones reachable only by following a pointer out of `CLAUDE.md` or a README. It writes a table of source, what it governs, what enforces it, and which review agents it is relevant to, and it returns only the path. Every review agent reads that map before it forms a convention-shaped opinion.

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
| `review-release` | Deployment risks: migrations, messaging infra, config changes, API contracts, rollback safety; a migration safety assessment per migration | magenta |
| `review-git-history` | Commit atomicity, refactoring separation, fixup detection, message format | green |
| `review-docs` | Comments, doc comments, and docs files: text that repeats the code or narrates the change, non-obvious code left unexplained, knowledge duplicated or documented in the wrong place | pink |

Each agent returns structured findings, each one carrying a severity — `Blocking`, `Suggestion`, or `Nitpick` — and a confidence rating (0-100). An agent may also return a block of positive notes, which is not a severity.

`review-release` also writes a migration safety assessment for every migration in the diff, safe or not — locks, duration, replication effects, and a verdict on when to run it — from the production database's version, schema, and sizes when the session has a read-only database skill, and from the project files otherwise. `/code-review:post` puts each one on the migration file as a diff comment.

### Phase 4 — Validate & Report (main thread)

The main agent validates every finding against its full unsummarized context, walking six named refutation grounds — unreachable, already guarded, sanctioned convention, framework semantics misread, pre-existing, impact inflated. Findings that can't be verified are dropped. The final report is written to `.claude/review-report/<topic>.md` in the project directory, and its Coverage section names which agents ran, which were skipped, and what validation dropped.

A surviving finding that turns on a race, a call ordering, a gap between states, or data crossing three or more components gets a mermaid diagram under it, drawn through the `diagrams:mermaid` skill and rendered before it lands — at most three per review, `Blocking` findings first, because GitLab shares one 2000-character mermaid budget across a page. `/code-review:post` carries those fences onto the MR unchanged. The nine review agents stay text-only; drawing is the main agent's call.

## Design decisions

- **Context stays unsummarized** — Phase 1 loads MR/ticket/diff directly into main context so validation in Phase 4 has full fidelity
- **Agents fetch their own git data** — the orchestrator passes only the branch range (`REVIEW_BASE...REVIEW_HEAD`, resolved to concrete refs), avoiding context-passing errors
- **Each agent knows its boundaries** — explicit "Out of Scope" sections prevent duplicate findings across agents
- **No automatic filtering by confidence** — the main agent verifies findings manually rather than relying on a numeric threshold
- **Platform-agnostic review, GitLab-only watch** — `/code-review:full` works with any code hosting platform and issue tracker; `/code-review:post` and `/code-review:watch` are built on the glab plugin

## Installation

```bash
claude plugin marketplace add fprochazka/claude-code-plugins --scope user
claude plugin install code-review@fprochazka-claude-code-plugins --scope user
```
