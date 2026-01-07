# Claude Code Plugins

A collection of Claude Code plugins by Filip Procházka.

## Installation

Add this marketplace to Claude Code:

```bash
claude plugin marketplace add fprochazka/claude-code-plugins
```

Then install plugins:

```bash
claude plugin install skill-keyword-reminder@fprochazka-claude-code-plugins
```

## Upgrading

To upgrade installed plugins to the latest version:

```bash
claude plugin marketplace update fprochazka-claude-code-plugins
claude plugin update skill-keyword-reminder@fprochazka-claude-code-plugins
```

## Available Plugins

| Plugin | Description |
|--------|-------------|
| [skill-keyword-reminder](plugins/skill-keyword-reminder/) | Automatically reminds Claude to load relevant skills when keyword triggers appear in user prompts |
| [gemini-cli](plugins/gemini-cli/) | Skill for using Gemini CLI with massive context windows (1M tokens) for codebase analysis and second opinions |
| [no-background-tasks](plugins/no-background-tasks/) | Prevents background execution by rewriting run_in_background to false |
| [glab-mr-fullstate](plugins/glab-mr-fullstate/) | Command for fixing GitLab MR issues (failed CI, unresolved comments) using glab-mr-fullstate |

## License

MIT
