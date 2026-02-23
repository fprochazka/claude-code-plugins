# rabbitmqadmin

Skill for inspecting RabbitMQ instances using the [rabbitmqadmin-ng](https://github.com/rabbitmq/rabbitmqadmin-ng) CLI.

## Prerequisites

Install the CLI following the [rabbitmqadmin-ng installation guide](https://github.com/rabbitmq/rabbitmqadmin-ng#installation).

## Recommended: Set Environment Variables

Add the following to `~/.claude/settings.json` under `"env"` to get cleaner output and avoid interactive prompts:

```json
{
  "env": {
    "RABBITMQADMIN_NON_INTERACTIVE_MODE": "",
    "RABBITMQADMIN_TABLE_STYLE": "borderless"
  }
}
```

- `RABBITMQADMIN_TABLE_STYLE=borderless` — produces output that is easy to read and grep/filter (no Unicode box drawing)
- `RABBITMQADMIN_NON_INTERACTIVE_MODE` — suppresses interactive prompts (set to any value, even empty string)
