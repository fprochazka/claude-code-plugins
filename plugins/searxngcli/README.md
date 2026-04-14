# searxngcli

Skill for searching the web using a SearXNG instance via the searxngcli command-line tool.

## Requirements

- [searxngcli](https://github.com/fprochazka/searxngcli) installed and configured

See the [searxngcli repository](https://github.com/fprochazka/searxngcli) for installation and configuration instructions.

## Installation

```bash
claude plugin marketplace add fprochazka/claude-code-plugins --scope user
claude plugin install searxngcli@fprochazka-claude-code-plugins --scope user
```

## Permissions

Add the following to `~/.claude/settings.json` to allow the skill to load and auto-approve commands:

```json
{
  "permissions": {
    "allow": [
      "Skill(searxngcli)"
    ]
  }
}
```

The skill's `allowed-tools` frontmatter auto-allows all commands (search, engines, categories, config). All operations are read-only.

## Usage

The skill is automatically loaded when needed. It teaches Claude how to use the `searxng` CLI to:

- Search the web with filters (categories, engines, language, time range)
- List available search engines from the configured instance
- List available search categories
- Manage configuration

## Author

Filip Procházka

## License

MIT
