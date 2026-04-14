# rabbitmqadmin

Skill for inspecting RabbitMQ instances using the [rabbitmqadmin-ng](https://github.com/rabbitmq/rabbitmqadmin-ng) CLI.

## Requirements

- [rabbitmqadmin-ng](https://github.com/rabbitmq/rabbitmqadmin-ng) installed and configured

See the [rabbitmqadmin-ng repository](https://github.com/rabbitmq/rabbitmqadmin-ng) for installation and configuration instructions.

## Installation

```bash
claude plugin marketplace add fprochazka/claude-code-plugins --scope user
claude plugin install rabbitmqadmin@fprochazka-claude-code-plugins --scope user
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

The plugin includes a `PreToolUse` hook (`scripts/validate-readonly.sh`) that auto-allows read-only commands regardless of `--node` flag positioning. The hook enforces:

- **Read-only subcommands only**: `vhosts list`, `queues list`, `queues show`, `exchanges list`, `bindings list`, `list`, `show`, `config_file show`, `--help`
- **Configured connections only**: `--node` values are validated against `~/.rabbitmqadmin.conf` — inline `--host`/`--username`/`--password` flags are rejected
- **Safe pipes only**: output may be piped to `grep`, `head`, `tail`, redirected to a file, or use `2>&1` — other pipe targets require approval
- **No command chaining**: `;`, `&&`, `||` are rejected

Write operations (`declare`, `delete`, `purge`, `publish`, etc.) always require manual approval.

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

## Development

Run the hook validation tests after editing `scripts/validate-readonly.sh`:

```bash
bash plugins/rabbitmqadmin/scripts/test-validate-readonly.sh
```

## Author

Filip Procházka

## License

MIT
