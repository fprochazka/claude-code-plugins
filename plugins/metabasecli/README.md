# metabasecli

Skill for interacting with Metabase using the metabase command-line tool.

## Requirements

- [metabasecli](https://github.com/fprochazka/metabasecli) installed and configured

See the [metabasecli repository](https://github.com/fprochazka/metabasecli) for installation and configuration instructions.

## Installation

```bash
claude plugin marketplace add fprochazka/claude-code-plugins --scope user
claude plugin install metabasecli@fprochazka-claude-code-plugins --scope user
```

## Permissions

Add the following to `~/.claude/settings.json` to allow the skill to load and auto-approve read-only commands:

```json
{
  "permissions": {
    "allow": [
      "Skill(metabasecli)"
    ]
  }
}
```

The skill's `allowed-tools` frontmatter auto-allows read-only commands (`search`, `resolve`, `databases list`, `collections tree`, `cards get`, `dashboards export`, etc.) and auth/help commands. Write operations (`cards create`, `dashboards import`, etc.) require manual approval.

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
