---
name: rabbitmqadmin
description: CLI for querying RabbitMQ instances (vhosts, queues, exchanges, bindings). Use when inspecting RabbitMQ, listing queues, checking exchange bindings, viewing queue details, or exploring RabbitMQ topology. Triggered by requests involving RabbitMQ data, queue inspection, exchange listing, or message broker exploration.
trigger-keywords: rabbitmq, rabbit
allowed-tools: Bash(rabbitmqadmin --help), Bash(rabbitmqadmin config_file:*)
---

# rabbitmqadmin

Command-line interface for RabbitMQ Management HTTP API (rabbitmqadmin-ng). Read-only inspection of vhosts, queues, exchanges, and bindings.

## First Step: List Available Connections

**Always start by listing configured connections:**

```bash
rabbitmqadmin config_file show
```

This shows all configured RabbitMQ instances (passwords masked). Present the list to the user and ask which one to use. If the user's request already implies a specific connection, use it directly.

All commands below use `<NODE>` as a placeholder — replace it with the actual connection name from the config.

## Virtual Hosts

After selecting a connection, list available vhosts to determine the `--vhost` value:

```bash
rabbitmqadmin --node <NODE> vhosts list
```

All commands below use `<VHOST>` as a placeholder — replace it with the actual vhost name from the list.

## Queues

### List Queues

```bash
rabbitmqadmin --node <NODE> queues list --vhost <VHOST>
```

### Inspect a Queue

```bash
rabbitmqadmin --node <NODE> queues show --name <QUEUE> --vhost <VHOST>
```

## Exchanges

```bash
rabbitmqadmin --node <NODE> exchanges list --vhost <VHOST>
```

## Bindings

```bash
rabbitmqadmin --node <NODE> bindings list --vhost <VHOST>
```

## Filtering

The CLI has no built-in name filtering. To filter results, pipe through `grep`:

```bash
rabbitmqadmin --node <NODE> --vhost <VHOST> queues list | grep <PATTERN>
rabbitmqadmin --node <NODE> --vhost <VHOST> exchanges list | grep <PATTERN>
```

## Shorthand Listing via `list` Command

The `list` command provides quick access to many resource types:

```bash
rabbitmqadmin --node <NODE> list queues
rabbitmqadmin --node <NODE> list exchanges
rabbitmqadmin --node <NODE> list bindings
rabbitmqadmin --node <NODE> list vhosts
rabbitmqadmin --node <NODE> list connections
rabbitmqadmin --node <NODE> list channels
rabbitmqadmin --node <NODE> list consumers
```

## Cluster Overview

```bash
rabbitmqadmin --node <NODE> show overview
rabbitmqadmin --node <NODE> show churn
rabbitmqadmin --node <NODE> show memory_breakdown_in_bytes
rabbitmqadmin --node <NODE> show memory_breakdown_in_percent
```

## Global Flags

| Flag | Description |
|------|-------------|
| `--node, -N` | Connection name from config file (default: "default") |
| `--vhost, -V` | Target virtual host (default: "/") |
| `--non-interactive` | Implies borderless style, removes headers, flattens newlines (set via `RABBITMQADMIN_NON_INTERACTIVE_MODE=true` env, do not pass explicitly). Mutually exclusive with `--table-style`. |

## Advanced Usage

For commands and options not covered here, read the `--help` of the relevant subcommand:

```bash
rabbitmqadmin queues --help
rabbitmqadmin queues list --help
rabbitmqadmin exchanges --help
rabbitmqadmin bindings --help
rabbitmqadmin connections list --help
rabbitmqadmin channels list --help
```

The CLI also supports write operations (`declare`, `delete`, `purge`, `publish`, `get messages`) — run `rabbitmqadmin --help` for the full command list, and `rabbitmqadmin <command> --help` for details on any specific command.
