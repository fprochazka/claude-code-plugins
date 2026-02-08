# metabasecli

Skill for interacting with Metabase using the metabase command-line tool.

## Requirements

- [metabasecli](https://github.com/fprochazka/metabasecli) installed and configured

See the [metabasecli repository](https://github.com/fprochazka/metabasecli) for installation and configuration instructions.

## Installation

```bash
claude plugin marketplace add fprochazka/claude-code-plugins
claude plugin install metabasecli@fprochazka-claude-code-plugins
```

## Permissions

The skill declares `allowed-tools: Bash(metabase:*)` to auto-approve metabase commands. Due to a [known bug](https://github.com/anthropics/claude-code/issues/14956), this may not work yet.

As a workaround, add the skill and read-only commands to your `~/.claude/settings.json`:

```json
{
  "permissions": {
    "allow": [
      "Skill(metabasecli)",
      "Bash(metabase --help)",
      "Bash(metabase auth status:*)",
      "Bash(metabase search:*)",
      "Bash(metabase resolve:*)",
      "Bash(metabase databases list:*)",
      "Bash(metabase databases get:*)",
      "Bash(metabase databases metadata:*)",
      "Bash(metabase databases schemas:*)",
      "Bash(metabase collections tree:*)",
      "Bash(metabase collections get:*)",
      "Bash(metabase collections items:*)",
      "Bash(metabase cards list:*)",
      "Bash(metabase cards get:*)",
      "Bash(metabase cards run:*)",
      "Bash(metabase dashboards list:*)",
      "Bash(metabase dashboards get:*)",
      "Bash(metabase dashboards export:*)",
      "Bash(metabase dashboards revisions:*)"
    ]
  }
}
```

Or allow all metabase commands (including write operations):

```json
{
  "permissions": {
    "allow": ["Bash(metabase:*)"]
  }
}
```

## Usage

The skill is automatically loaded when needed. It teaches Claude how to use the `metabase` CLI to:

- Search across all Metabase entities (cards, dashboards, collections, databases)
- Resolve Metabase URLs to entity details
- Browse and manage collections
- List, view, and run saved questions/cards
- Export dashboards with all referenced cards for context
- Import dashboard layouts and card definitions separately
- Explore database metadata, schemas, tables, and fields
- Manage dashboard revisions and reverts

## Author

Filip Proch&#225;zka

## License

MIT
