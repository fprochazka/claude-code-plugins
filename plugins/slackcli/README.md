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

Add the following to `~/.claude/settings.json` to allow the skill to load and auto-approve read-only commands:

```json
{
  "permissions": {
    "allow": [
      "Skill(slackcli)"
    ]
  }
}
```

The skill's `allowed-tools` frontmatter auto-allows read-only commands (`conversations list`, `messages list`, `search messages`, `users list`, `resolve`, etc.) and config/help commands. Write operations (`messages send`, `messages edit`, `reactions add`, etc.) require manual approval.

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
