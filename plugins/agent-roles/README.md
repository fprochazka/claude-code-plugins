# agent-roles

Two role files, injected into every agent before it takes its first action:

- `roles/orchestrator.md` — the top-level session. It talks to the user, decides, delegates, and synthesizes. It does not grep, build, or explore.
- `roles/worker.md` — every subagent, at any nesting depth. It runs everything in the foreground, waits for nothing it was not asked to wait for, and ends its turn with findings.

A `SessionStart` hook delivers the first, a `SubagentStart` hook the second.

## Installation

```bash
claude plugin marketplace add fprochazka/claude-code-plugins --scope user
claude plugin install agent-roles@fprochazka-claude-code-plugins --scope user
```

Needs Claude Code 2.1.257 or newer. From 2.1.216 to 2.1.252 a plugin's hooks were silently dropped after the first one registered, so on those versions the roles never arrive and nothing reports it. The hook needs `bash`; it uses `jq` when present and falls back to plain output without it.

The plugin also expects `CLAUDE_CODE_FORK_SUBAGENT` set to `0` in `~/.claude/settings.json`:

```json
{ "env": { "CLAUDE_CODE_FORK_SUBAGENT": "0" } }
```

The flag gates a built-in `fork` agent type. A fork inherits the parent's whole conversation, so it starts with the orchestrator role already in context and then receives the worker role from `SubagentStart`. The two contradict each other: the orchestrator delegates its work and runs it in the background, the worker does neither. A fork also inherits the parent's model, against the rule to pick a model per subtask. Nothing selects a fork on its own — the caller asks for `subagent_type: "fork"` — so the flag removes the choice rather than changing a default.

[`noisy-tools-in-subagent`](../noisy-tools-in-subagent/) is a dependency and installs with the plugin. The orchestrator role points at its `noisy-runner` agent for builds, tests, and linters.

## Highlights

- **The main agent stays an orchestrator** — code exploration, code writing, builds, database work, infrastructure checks, and anything with unpredictable output go to a subagent. Bash in the main context is limited to commands whose output is a few known lines
- **At most three subagents in parallel** — a wider fan-out hides what is happening from the user, and the user asks for it explicitly when they want it
- **A killed task taught you nothing** — `Exit code 143`, "timed out" and "moved to the background" are not results. Read the artifact back before reporting on it, and never carry a "green" forward from a task you did not read
- **Workers never background anything** — no `run_in_background`, no `&`, no monitors, no crons, no scheduled wakeups. A subagent dies the moment its last foreground command finishes, taking everything it left running with it, so backgrounded work produces a report about work that never ran
- **A worker ends with findings, never an intention** — "I'll wait for X" and "monitor armed, will report back" are non-answers. A log line that is not there yet is itself the finding: `NOT PRESENT as of <UTC time>`, with the queries that were run
- **Model by subtask, not by habit** — sonnet for mechanical single operations, opus for real work, fable only for the hardest reasoning. An orchestrator does not spawn its own model out of reflex
- **Every delegation names a skill** — when a skill covers the tool the subagent will use, the prompt says to load it first, so the subagent does not spend turns on `--help`

## How the injection works

`hooks/inject-role.sh` receives the event name as an argument, reads the matching file from `roles/`, and prints it as `hookSpecificOutput.additionalContext`. The event name comes from the argument rather than the stdin payload, so the script parses nothing.

The two files are delivered by two separate hooks, and other plugins and your own settings inject on the same events. The order is unspecified, so each role file reads correctly on its own and never refers to anything outside itself.

No hook payload carries a nesting depth or a parent, so a subagent three levels down looks exactly like a subagent one level down. Every subagent gets the same worker role, which is why the worker rules are written to hold at any depth.

The roles are injected markdown, not skills. A skill has to be loaded, and a subagent that skips loading it acts unconstrained; injection puts the rules in place before the subagent's first tool call. The cost is the worker file's tokens in every subagent, at every depth.

## What it isn't

Not a set of agent definitions — the plugin ships no `agents/`, and it constrains how existing agents work rather than adding new ones. Not enforcement either: nothing blocks a tool call, so a command that runs against the rules still runs. For an enforced version of the delegation rule, see [`noisy-tools-in-subagent`](../noisy-tools-in-subagent/), which denies noisy commands in the main context outright.

The rules are calibrated, not neutral. The parallelism cap, the stance against monitors, and the worker's ban on backgrounding come from one person's experience with this harness. Installing the plugin is an opt-in to working that way.

## License

MIT
