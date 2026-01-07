# no-background-tasks

A Claude Code plugin that prevents background execution by silently rewriting `run_in_background: true` to `false` for Bash and Task tools.

## What it does

When Claude tries to run a command or launch a subagent in background mode, this hook intercepts the call and rewrites the parameter to force foreground execution. This ensures Claude waits for each operation to complete before continuing.

## Installation

```bash
claude plugin install no-background-tasks@fprochazka-claude-code-plugins
```

## How it works

The plugin uses a `PreToolUse` hook that:

1. Matches `Bash` and `Task` tool calls
2. Checks if `run_in_background` is set to `true`
3. Uses `updatedInput` to silently change it to `false`

This approach is token-efficient compared to blocking and requiring a retry.

## Affected tools

| Tool | Effect |
|------|--------|
| `Bash` | Commands run in foreground, Claude waits for output |
| `Task` | Subagents run synchronously, Claude waits for completion |

## Limitations

This plugin prevents background execution but does **not** prevent parallel tool calls in a single message. If Claude sends multiple tool calls simultaneously, they will still execute in parallel (just not in the background).

To also prevent parallel execution, combine this plugin with instructions in your `CLAUDE.md`:

```markdown
NEVER launch subagents in background or in parallel unless explicitly asked.
Always run them one by one, and wait for them to finish.
```
