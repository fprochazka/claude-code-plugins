# no-background-tasks

> **Note:** This plugin is a work in progress. There is a known intermittent bug in Claude Code where `permissionDecision: "allow"` responses can cause an error: `undefined is not an object (evaluating 'H.includes')`. See [#16598](https://github.com/anthropics/claude-code/issues/16598) for updates.

A Claude Code plugin that enforces serial execution of Bash and Task tools within a session.

## What it does

1. **Rewrites `run_in_background: true` to `false`** - Silently forces foreground execution
2. **Prevents parallel tool calls** - Uses a session-scoped lock file to ensure only one Bash/Task runs at a time

## Installation

```bash
claude plugin install no-background-tasks@fprochazka-claude-code-plugins
```

## How it works

The plugin uses three hooks:

**UserPromptSubmit:**
- Releases any stale lock from previous turn (safety reset)

**PreToolUse** (Bash|Task):
1. Rewrites `run_in_background: true` to `false` via `updatedInput`
2. Attempts to acquire a session-scoped lock using atomic file creation
3. If lock already held → denies the tool call with a message to retry

**PostToolUse** (Bash|Task):
- Releases the session lock when the tool completes

Lock files are stored at `~/.claude/no-background-tasks/session-{id}.lock`.

## Behavior

When Claude attempts to run multiple tools in parallel:

```
Claude sends:
  - Bash("sleep 5")   ← acquires lock, runs
  - Bash("sleep 3")   ← denied: "Another tool is executing..."
  - Bash("sleep 1")   ← denied: "Another tool is executing..."

Claude retries denied calls sequentially after each completion.
```

## Affected tools

| Tool | Effect |
|------|--------|
| `Bash` | Commands run serially, one at a time |
| `Task` | Subagents run serially, one at a time |

## Token overhead

When parallel calls are denied, Claude sees the denial message and must retry. This uses some additional tokens compared to if Claude sent sequential calls from the start. Consider adding to your `CLAUDE.md`:

```markdown
NEVER launch subagents in background or in parallel unless explicitly asked.
Always run them one by one, and wait for them to finish.
```

This reduces denied attempts since Claude will try to comply with instructions first.
