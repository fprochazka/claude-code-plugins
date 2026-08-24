# noisy-tools-in-subagent

Forces noisy commands — builds, tests, linters, static analysis, anything that produces a wall of output — to run inside a Sonnet subagent instead of the calling agent's context window. Those tokens are for work that needs them, not for 2,000 lines of Maven output. This holds at every nesting depth: a nested orchestrator protects its own context the same way the top-level one does.

![Example: main agent's `uv run ruff format --check . && uv run ruff check . && uv run pytest` is blocked by the hook, delegated to the `noisy-runner` subagent, which runs the three commands and reports a 4-line summary back (3 tool uses, 10.9k tokens, 41s) instead of dumping 598 pytest lines into the main context.](example.png)

## Installation

Prereq: install [`bash-classify`](https://github.com/fprochazka/bash-classify), used by the hook to parse Bash commands:

```bash
uv tool install bash-classify
```

Then add the marketplace and install:

```bash
claude plugin marketplace add fprochazka/claude-code-plugins --scope user
claude plugin install noisy-tools-in-subagent@fprochazka-claude-code-plugins --scope user
```

If `bash-classify` isn't on your `PATH`, the hook refuses to proceed and tells the agent to install it.

## How it works

Two pieces:

1. **A `PreToolUse` hook** on `Bash` that parses each command with `bash-classify` (walking pipes, chains, and subshells) and matches every parsed command against a regex whitelist of noisy build/test/lint tools. A match is denied with a short message telling the agent to delegate. The main thread and every subagent are treated alike, except for the agents listed under [Which agents are exempt](#which-agents-are-exempt).

2. **A `noisy-runner` subagent** (Sonnet, strictly scoped to `Bash` and `Read`) that runs the commands it is given, wraps them in `tee` to capture full logs to `/tmp`, reads any files the output references to interpret errors, and reports back a concise summary plus log paths. It does not explore, fix, or modify anything — its only job is *run, read, interpret, report*.

Net effect: when the main agent wants `./mvnw test`, it gets redirected into a "3 tests failed at X:42, Y:87, Z:12 because …, full logs at /tmp/…" summary instead of a flood of output.

The whitelist and its tuning live in `hooks/enforce-subagent.py`. It covers Maven and Gradle lifecycle phases and static-analysis tasks (`checkstyleMain`, `spotbugsMain`, `jacocoTestReport`), Node build/test/lint scripts, the Python, Rust and Go toolchains, and `kubectl logs`. A wrapper counts whether it is invoked as `./gradlew` or by absolute path.

Introspection stays out of the way. `mvn help:*`, `mvn dependency:tree`, `gradle tasks`, `gradle projects`, `dependencies`, `dependencyInsight` and `kubectl get` all pass through.

## Which agents are exempt

Blocking an agent only works if that agent can delegate, and some cannot:

- `noisy-runner` itself. It is the delegation target, so it has to run what it was given.
- Agents whose definition omits the Agent tool — the built-in `Explore` and `Plan`, or this repository's `code-review:review-*` agents.
- Any agent at the subagent nesting limit. At the cap Claude Code drops the Agent tool from the toolset rather than refusing the call, so such an agent has no way to spawn anything.

A hook cannot see any of this. Claude Code builds hook input from a fixed key set — `session_id`, `transcript_path`, `cwd`, `prompt_id`, `permission_mode`, `agent_id`, `agent_type`, `effort` — and routes spawn depth and `parentAgentId` only to OpenTelemetry spans and the `x-claude-code-parent-agent-id` API header. No hook event carries either one. `agent_type` is the only agent signal a hook gets, so the exempt set is declared rather than detected.

These patterns are built in:

```
noisy-tools-in-subagent:noisy-runner
Explore
Plan
code-review:review-.*
searxngcli:agent
web-researcher:agent
```

## Configuration

Add your own agents through the `exempt_agent_types` plugin option:

```bash
claude plugin install noisy-tools-in-subagent@fprochazka-claude-code-plugins --scope user --config exempt_agent_types=my-team:leaf-worker
```

`/plugin` sets the same option interactively. Each entry is a regex that has to match the whole agent type. A partial match would silently disable the plugin for that agent, so `bugs` does not match `my-team:review-bugs` — write `my-team:review-.*` instead. Pass several entries as a JSON array or one per line. A pattern containing a comma, such as `team:a{1,3}`, must use one of those two forms, because a single-line value is also accepted as a comma-separated list.

Claude Code stores the value in your user `settings.json` under `pluginConfigs`, and deliberately ignores `pluginConfigs` in project settings. A repository therefore cannot ship this list for its contributors — each user configures their own.

If an agent you did not exempt reaches the nesting limit, the hook denies its command and tells it to report back instead of retrying. That costs one turn, and the command does not run.

## Using the subagent directly

The `noisy-runner` subagent isn't limited to the hook's whitelist. Invoke it via the Task tool any time you want a command run and *interpreted* rather than transcribed into your context:

```
subagent_type: "noisy-tools-in-subagent:noisy-runner"
prompt: run `./mvnw test -pl foo` and `./gradlew :bar:check`, tell me what broke
```

You can pass multiple commands in one invocation — the subagent runs them sequentially.

## Known Claude Code UI quirk

When the hook denies a command, Claude Code's terminal UI may render the rejection message 2–3 times in the same tool-call block (an empty "blocking error" header, a red `Error:` card, sometimes a side-panel overlay). This is a Claude Code rendering quirk — upstream issues [anthropics/claude-code#34713](https://github.com/anthropics/claude-code/issues/34713) and [#21504](https://github.com/anthropics/claude-code/issues/21504). The model itself only sees the rejection reason once in its context, so it's visual clutter, not token waste.

## Upgrading

```bash
claude plugin marketplace update fprochazka-claude-code-plugins
claude plugin update noisy-tools-in-subagent@fprochazka-claude-code-plugins
```

## License

MIT
