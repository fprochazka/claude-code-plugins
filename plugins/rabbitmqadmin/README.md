# rabbitmqadmin

Skill for inspecting RabbitMQ instances using the [rabbitmqadmin-ng](https://github.com/rabbitmq/rabbitmqadmin-ng) CLI.

## Requirements

- [rabbitmqadmin-ng](https://github.com/rabbitmq/rabbitmqadmin-ng) installed and configured

See the [rabbitmqadmin-ng repository](https://github.com/rabbitmq/rabbitmqadmin-ng) for installation and configuration instructions.

## Installation

```bash
claude plugin marketplace add fprochazka/claude-code-plugins
claude plugin install rabbitmqadmin@fprochazka-claude-code-plugins
```

## Permissions

Add the following to `~/.claude/settings.json` to allow the skill to load and auto-approve read-only commands:

```json
{
  "permissions": {
    "allow": [
      "Skill(rabbitmqadmin)"
    ]
  }
}
```

The skill's `allowed-tools` frontmatter auto-allows help and config commands. Write operations (`declare`, `delete`, `purge`, `publish`, etc.) require manual approval.

## Recommended: Set Environment Variables

Add the following to `~/.claude/settings.json` under `"env"` for compact, grep-friendly output:

```json
{
  "env": {
    "RABBITMQADMIN_NON_INTERACTIVE_MODE": "true"
  }
}
```

- `RABBITMQADMIN_NON_INTERACTIVE_MODE=true` — implies `borderless` table style, removes header rows, and flattens multi-line cell values into single lines. Produces the most compact output for agent consumption.

**Note:** Do not combine with `RABBITMQADMIN_TABLE_STYLE` — `--non-interactive` and `--table-style` are mutually exclusive. The `config_file show` subcommand ignores this setting and always uses its own table format.

## Usage

The skill is automatically loaded when needed. It teaches Claude how to use the `rabbitmqadmin` CLI to:

- List configured connections and select a target node
- List and inspect virtual hosts
- List and inspect queues
- List exchanges and bindings
- View cluster overview and memory breakdowns
- Filter results with grep

## Author

Filip Procházka

## License

MIT
