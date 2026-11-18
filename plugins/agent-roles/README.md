# agent-roles

Four role files, one injected into every agent before it takes its first action:

- `roles/worker.md` — the top-level session, on one task. It talks to the user, decides, delegates, and synthesizes. It does not grep, build, or explore. When a dispatcher's brief names it, it also reports to that dispatcher.
- `roles/dispatcher.md` — a top-level session that runs worker sessions in sibling tmux windows instead of doing task work. It briefs, watches, nudges and compacts them, spot-checks what they claim, and closes the ones it started; each worker rolls out its own change. A session gets it only when asked for, see [Running a dispatcher](#running-a-dispatcher).
- `roles/task-subagent.md` — every subagent, at any nesting depth. It runs everything in the foreground, waits for nothing it was not asked to wait for, and ends its turn with findings.
- `roles/resident-subagent.md` — subagents that stay alive for a whole run and report through `SendMessage`: the plugin's `agent-roles:resident` agent type and the types listed in the `resident_agent_types` plugin option. It waits only the way its brief says, sends a heartbeat so silence means death, and ends its turn only on its stop condition.

A `SessionStart` hook delivers the worker role, unless a launcher gave the session another role. A `SubagentStart` hook delivers one of the two subagent roles, picked by the payload's `agent_type`: the resident role for `agent-roles:resident` and the types in the `resident_agent_types` plugin option, the task role for everything else.

To start a resident subagent, spawn it with `subagent_type: "agent-roles:resident"`, a general-purpose agent with every tool. The agent type is the only value the caller sets that reaches the `SubagentStart` hook: the payload carries no prompt, description or `run_in_background`.

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

The flag gates a built-in `fork` agent type. A fork inherits the parent's whole conversation, so it starts with the worker role already in context and then receives the task subagent role from `SubagentStart`. The two contradict each other: the worker delegates its work and runs it in the background, the task subagent does neither. A fork also inherits the parent's model, against the rule to pick a model per subtask. Nothing selects a fork on its own — the caller asks for `subagent_type: "fork"` — so the flag removes the choice rather than changing a default.

[`noisy-tools-in-subagent`](../noisy-tools-in-subagent/) is a dependency and installs with the plugin. The worker role points at its `noisy-runner` agent for builds, tests, and linters.

## Highlights

- **The worker session delegates** — code exploration, code writing, builds, database work, infrastructure checks, and anything with unpredictable output go to a subagent. Bash in the main context is limited to commands whose output is a few known lines
- **At most three subagents in parallel** — a wider fan-out hides what is happening from the user, and the user asks for it explicitly when they want it
- **A killed task taught you nothing** — `Exit code 143`, "timed out" and "moved to the background" are not results. Read the artifact back before reporting on it, and never carry a "green" forward from a task you did not read
- **Subagents never background anything** — no `run_in_background`, no `&`, no monitors, no crons, no scheduled wakeups. A subagent dies the moment its last foreground command finishes, taking everything it left running with it, so backgrounded work produces a report about work that never ran
- **A task subagent ends with findings, never an intention** — "I'll wait for X" and "monitor armed, will report back" are non-answers. A log line that is not there yet is itself the finding: `NOT PRESENT as of <UTC time>`, with the queries that were run
- **A later write is named in the first prompt** — the auto mode classifier treats a subagent's first prompt as the user's instruction and a later message from the worker as no consent at all. A subagent that a later turn will resume to post, push or move a ticket gets the user's request quoted and the write named up front, never "read-only"
- **A classifier denial goes to the user** — the worker names the exact blocked action and runs it again only after the user answers, in its own session; a subagent never retries it
- **A resident subagent reports by message, never by ending its turn** — a message is a finding delivered, a heartbeat at a fixed interval says it is alive, and only its stop condition ends the turn. Only the agent types named as resident get this role; nothing a brief says turns a task worker into one
- **Model by how much of the method the brief hands down, not by habit** — haiku for a few named commands or extracting given text, with a check behind it, never for search or review; sonnet when the brief spells out the steps, the scope and the check; opus, the default, for the work a strong senior engineer does, from features of any size to research and review; fable for deep theory such as concurrency, distributed consistency and algorithms, a subtle bug across several systems, or where opus fell short. A worker does not spawn its own model out of reflex
- **Every delegation names a skill** — when a skill covers the tool the subagent will use, the prompt says to load it first, so the subagent does not spend turns on `--help`

## Running a dispatcher

The dispatcher needs tmux, [cc-session-tools](https://github.com/fprochazka/claude-code-session-tools) 0.7 or newer on the `PATH`, and a launcher command per Claude Code profile (`claude-<profile>`, from [cc-auth-switch](https://github.com/fprochazka/claude-code-auth-switch)). Start it in its own tmux session, in the directory where it should keep its roster:

```bash
tmux new-session -s oss -c ~/devel/oss
claude-personal --agent-role dispatcher
```

Launch the dispatcher through cc-auth-switch, not with `FP_CC_AUTH_SWITCH_ROLE=dispatcher claude`. The variable alone gives the session the role text, but only the cc-auth-switch start log records the role that `cc-session-tools list-active` shows, and the dispatcher uses that role to tell itself and other dispatchers from its workers. Define the role with `prompt.file` pointing at `roles/dispatcher.md` and `mode: append`, so the role sits in the system prompt and survives compaction. Every other session in that tmux session is managed by it, whoever started it, including permanent sessions for a topic that you use directly and keep open for days. A managed session with a task from the dispatcher in flight is working: the dispatcher drives it to the brief's definition of done. It keeps its roster in `.claude/dispatcher/roster.md` and the briefs it writes in `.claude/dispatcher/briefs/` under its working directory. One `cc-session-tools watch` over the whole tmux session picks sessions up and drops them on its own. The dispatcher compacts every managed session after 50 minutes idle, yours too, because the prompt cache expires at 60 minutes, but only when the session uses at least 15% of its context window. Nudges, the cap of three and the checks on claims apply only to working sessions. A session reports a summary of each turn the dispatcher started. When a turn you started by typing into a session ends, the dispatcher asks that session for a summary or reads the exchange, whichever is cheaper there, to know what you work on, and acts on nothing in it. While a session is working, the dispatcher keeps a cron that wakes it every 30 minutes, which also revives it after a compaction; Claude Code expires a recurring cron after 7 days, so the dispatcher replaces its cron before then. It deletes the cron once no session is working, or while every working session waits on you. It closes only a session it started, once the task is done, or a session you tell it to close.

Workers are plain sessions with the worker role. They must not run in `bypassPermissions` mode, which holds messages from other sessions for the human's approval; the dispatcher tells the human about such a session instead of driving it.

The dispatcher role asks the dispatcher to type into its workers' panes: briefs, `/compact`, `/exit`, and answers to the startup dialogs and permission prompts that the human's authorization covers. Every other dialog goes to the human.

## How the injection works

`hooks/inject-role.sh` receives the event name as an argument, reads the matching file, and prints it as `hookSpecificOutput.additionalContext`.

On `SessionStart` the session's role comes from the environment that [cc-auth-switch](https://github.com/fprochazka/claude-code-auth-switch) sets for a role, checked in this order:

1. `FP_CC_AUTH_SWITCH_ROLE` is `none`: the hook prints nothing, whatever else is set. This is how cc-auth-switch asks for a session without a role (`--agent-role none`), so that the `default_role` option does not apply.
2. `FP_CC_AUTH_SWITCH_ROLE_PROMPT_MODE` is `append` or `replace`: the hook prints nothing. The launcher already put the role into the system prompt, where it survives compaction and has no size limit.
3. `FP_CC_AUTH_SWITCH_ROLE_PROMPT` is set: the hook injects that file, so the launcher config stays the one place that says which file a role uses.
4. Only `FP_CC_AUTH_SWITCH_ROLE` is set, for example by hand without a launcher: the hook injects `roles/<name>.md`.
5. None of them is set: the hook injects the role named by the `default_role` plugin option, `worker` unless you change it. `none` injects nothing, the same as in step 1.

A file that cannot be read, or a role name the plugin has no file for, injects nothing and prints a warning to stderr. The role `none` never warns. Subagents never read these variables; a launcher cannot reach them.

On `SubagentStart` it reads `agent_type` from the payload with `jq` and picks the resident role when the type is `agent-roles:resident` or one of the types in the `resident_agent_types` plugin option; without `jq`, or without the field, it picks the task role. Set a different default role, or add your own resident types, the way the noisy-tools plugin takes its exempt list:

```bash
claude plugin install agent-roles@fprochazka-claude-code-plugins --scope user --config resident_agent_types=my-team:sentinel
claude plugin install agent-roles@fprochazka-claude-code-plugins --scope user --config default_role=none
```

`hooks/test-inject-role.sh` feeds the hook a payload per case and checks which role comes out; `make test` runs it.

The two files are delivered by two separate hooks, and other plugins and your own settings inject on the same events. The order is unspecified, so each role file reads correctly on its own and never refers to anything outside itself.

No hook payload carries a nesting depth or a parent, so a subagent three levels down looks exactly like a subagent one level down. The agent type is the only thing the payload tells apart, which is why the subagent rules are written to hold at any depth and the resident role is keyed on a type, never on what a brief claims.

The roles are injected markdown, not skills. A skill has to be loaded, and a subagent that skips loading it acts unconstrained; injection puts the rules in place before the subagent's first tool call. The cost is the subagent role's tokens in every subagent, at every depth.

## What it isn't

Not a set of agent definitions — the plugin ships one agent type, `agent-roles:resident`, only so a caller can pick the resident role, and otherwise constrains how existing agents work. Not enforcement either: nothing blocks a tool call, so a command that runs against the rules still runs. For an enforced version of the delegation rule, see [`noisy-tools-in-subagent`](../noisy-tools-in-subagent/), which denies noisy commands outright, in the main agent and in every subagent that can delegate.

The rules are calibrated, not neutral. The parallelism cap, the stance against one-off monitors, and the subagents' ban on backgrounding come from one person's experience with this harness. Installing the plugin is an opt-in to working that way.

## License

MIT
