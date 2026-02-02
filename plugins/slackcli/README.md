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

As a workaround, add this to your `~/.claude/settings.json`:

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
- Send, edit, and delete messages
- Add and remove emoji reactions
- Resolve Slack message URLs
- Check unread messages

## Author

Filip Procházka

## License

MIT
