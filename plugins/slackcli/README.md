# slackcli

Skill for interacting with Slack workspaces using the slackcli command-line tool.

## Requirements

- [slackcli](https://github.com/fprochazka/slackcli) installed and configured

See the [slackcli repository](https://github.com/fprochazka/slackcli) for installation and configuration instructions.

## Installation

```bash
claude plugin marketplace add fprochazka/claude-code-plugins
claude plugin install slackcli@fprochazka-claude-code-plugins
```

## Permissions

The skill declares `allowed-tools: Bash(slack:*)` to auto-approve slack commands. Due to a [known bug](https://github.com/anthropics/claude-code/issues/14956), this may not work yet.

As a workaround, add read-only commands to your `~/.claude/settings.json`:

```json
{
  "permissions": {
    "allow": [
      "Bash(slack --help)",
      "Bash(slack config:*)",
      "Bash(slack conversations list:*)",
      "Bash(slack messages list:*)",
      "Bash(slack search messages:*)",
      "Bash(slack search files:*)",
      "Bash(slack users list:*)",
      "Bash(slack users search:*)",
      "Bash(slack users get:*)",
      "Bash(slack files download:*)",
      "Bash(slack pins list:*)",
      "Bash(slack scheduled list:*)",
      "Bash(slack resolve:*)"
    ]
  }
}
```

Or allow all slack commands (including write operations):

```json
{
  "permissions": {
    "allow": ["Bash(slack:*)"]
  }
}
```

## Usage

The skill is automatically loaded when needed. It teaches Claude how to use the `slack` CLI to:

- List and search conversations (channels, DMs, groups)
- Read messages with time filters and thread support
- Search messages and files
- Look up users by name, email, or ID
- Download files
- Send, edit, and delete messages
- Add and remove emoji reactions
- Pin and unpin messages
- Schedule messages for future delivery
- Resolve Slack message URLs

## Author

Filip Procházka

## License

MIT
