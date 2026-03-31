# code-review

Multi-agent branch code review plugin for Claude Code. Reviews conventions, architecture, bugs, security, and git history in parallel using specialized subagents.

## Usage

```
/code-review:full [focus area or specific concerns]
```

## How it works

The review runs in 4 phases:

### Phase 1 — Load Context (main thread)

Loads everything into the main context window unsummarized:
- Branch diff and commit list
- MR/PR description, comments, and pipeline status
- Ticket description and acceptance criteria

### Phase 2 — Explore Surrounding Code (single subagent)

An Explore subagent builds understanding of the touched code areas — callers, callees, data flow, downstream effects, and previous state.

### Phase 3 — Parallel Review (5 subagents)

Five specialized review agents run in parallel, each with its own checklist and scope. They receive the branch range and fetch their own git data.

| Agent | Scope | Color |
|---|---|---|
| `review-conventions` | Documented conventions, naming, test structure, annotations | cyan |
| `review-architecture` | Module placement, layers, coupling, abstractions, API design, dependency direction | blue |
| `review-bugs` | Logic errors, edge cases, error handling, race conditions, resource leaks | red |
| `review-security` | Injection, auth, secrets, input validation, XSS, OWASP | yellow |
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
claude plugin install code-review@fprochazka-claude-code-plugins
```
