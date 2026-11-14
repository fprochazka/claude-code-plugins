# noisy-tools-in-subagent: design

Read this before you change the plugin. It records why the plugin exists, what it must not become, and what was already tried. A change that contradicts a principle or reverses a decision needs the maintainer's explicit approval and a new entry under [Decisions](#decisions).

## Purpose

A build, a test run or a linter can print thousands of lines, and every line lands in the context of the agent that ran it. That context is for the work that needs it. The plugin makes an agent hand such commands to a cheap subagent that runs them, reads them in full, and returns a short verdict plus the path to the full log.

It has two parts. A `PreToolUse` hook on Bash parses the command with `bash-classify`, matches each parsed command against a regex whitelist, and denies a match with a message that names the `noisy-runner` agent. `noisy-runner` has only Bash and Read: it runs what it is given, tees the output to a log, reads the files the output points at, and reports. The plugin was created on 2026-04-15 in session `0da2f284-5804-492d-a229-e64863dd5788`.

## Goals

- A noisy command never prints into the context of an agent that can delegate, at any nesting depth.
- The caller gets an interpretation, not a transcription: "all ok" and a log path when the run is clean, file and line and cause when it is not.
- The full output is always on disk, so the caller can check the verdict.
- The subagent runs without extra permission prompts.
- Cheap commands that the agent needs to read (introspection, `git diff`, `grep`) stay in the agent's context.

## Non-goals and scope

- **Not a summarizer of arbitrary output.** Commands whose literal text the caller needs (`grep`, `sed`, `cat`, `git diff`, `git show`, `find`, schema dumps, document fetches) are never on the whitelist, however large their output.
- **Not a fixer or an explorer.** `noisy-runner` does not edit files, suggest fixes, or read files the output does not name.
- **No routing to other agents.** Every match goes to `noisy-runner`. Noisy research output such as `searxng search` belongs to a research agent, and the hook cannot route per pattern.
- **No long-running servers.** `bootRun`, `yarn dev` and similar stay off the whitelist, because they would hang the subagent.
- **No own Bash parser.** Wrapper and pipeline grammar belongs to `bash-classify`.
- **Windows is not supported, and support is not planned.** The hook calls `python3`, parses Bash, and the agent writes to `/tmp`. A Windows draft was requested on 2026-04-22 and never committed, and no request has come since.

## Principles

1. **Delegate to a real agent loop, do not rewrite the command.** The caller can pass several commands at once, and the subagent can open the files a stack trace points at. A command rewriter would have to rebuild that loop. The maintainer on llm-toto, the rejected rewriter: "llm-toto forces me to reimplement the agent loop to make it really useful".
2. **`bash-classify` parses, the hook matches.** The hook walks every command in pipes, chains and subshells, and every `inner_commands` level that `bash-classify` unwraps from `timeout`, `env`, `rtk` and other wrappers. A hand-written wrapper parser was rejected: "you're supposed to use bash-classify to parse the individual commands".
3. **Whitelist entries come from evidence, and introspection passes.** Patterns match build lifecycle phases and named tasks, not whole tools, so `mvn help:*`, `dependency:tree`, `gradle tasks` and `kubectl get` pass. New patterns are measured against real transcripts, and a pattern that matches project paths or flags is narrowed to explicit task names.
4. **Deny explicitly, never allow.** A match returns `permissionDecision: "deny"` with exit 0. `exit 2` counts as a hook error and loses to another hook's explicit `allow`. A passing command gets no output, because an explicit `allow` would override another hook's legitimate deny.
5. **Fail closed without the classifier, fail open on bad input.** Without `bash-classify` on `PATH` the hook denies every Bash call and says how to install it, because a silent pass would disable the plugin. Malformed hook input passes, so unrelated tool calls are not blocked. Unusable classifier output falls back to matching the raw command string.
6. **The deny message is short and says only what to do.** It names the matched command and the `subagent_type` to call. How to phrase the delegation (no `cd`, no filters, no `tee`) lives in the subagent's prompt. The maintainer cut it from 46 lines to 5: "I don't think we need to be so crazy about the output".
7. **Exemption is declared, not detected.** No hook payload carries the nesting depth or the parent agent; `agent_type` is the only agent signal. An agent that cannot delegate is exempt only when its type fully matches a built-in pattern or one from `exempt_agent_types`. A missing entry costs one denied turn, because the deny message tells an agent without the Agent tool to report back instead of retrying.
8. **The subagent's commands keep a stable prefix.** Literal log paths `/tmp/noisy-runner.<project>.<slug>.<counter>.log`, no shell variables, no `$(…)`, no `cd`, no `echo $?`. Anything else changes the prefix the permission matcher sees and causes prompts: "I dislike the command format its doing, claude keeps asking me for permission". The counter lives in the subagent's context, because `tee` truncates a reused file.
9. **The report is as short as the result allows.** A clean run is "all ok" plus one line per command with its log path. Only a failure gets a structured report.
10. **The cheapest model that passes the evals runs the subagent.** The job is mechanical, so cost decides once quality is equal.

## Decisions

| Date | Decision | Reason |
|---|---|---|
| 2026-04-15 | A hook that denies plus a Bash-and-Read subagent, not a command rewriter (llm-toto) | A rewriter has no agent loop: it cannot take several commands at once or read the files the output names |
| 2026-04-15 | The whitelist is a list of regexes over `bash-classify`'s parsed argv | The maintainer asked for patterns like `npm .*build.*` and `mvn .*` |
| 2026-04-15 | Match lifecycle phases, so `mvn help:*`, `dependency:tree` and `gradle tasks` pass | Always delegating and an env var override were the alternatives. Introspection output is small and the agent needs it |
| 2026-04-15 | A missing `bash-classify` denies every Bash call with install instructions | Failing open would silently disable the plugin |
| 2026-04-15 | Explicit JSON `deny` with exit 0, not `exit 2` | A debug log showed `bash-classify-hook`'s explicit `allow` beating the `exit 2` error, and `./mvnw package` ran in the main context |
| 2026-04-15 | Log paths are literal, with the project and a counter the subagent keeps in context | A `LOG=…$(date)` variable caused permission prompts. `tee -a` was rejected because runs would interleave in one file |
| 2026-04-15 | The deny message is 5 lines and the delegation rules live in the subagent prompt | The 46-line message wasted context on every block |
| 2026-04-15 | `suppressOutput: true`, and the remaining duplicate render is left alone | The duplicate is Claude Code's TUI (anthropics/claude-code#21504, closed as not planned); the model sees the reason once |
| 2026-04-15 | The README names no whitelist entries | "lets not create exhaustive lists of redirected commands, or similar duplications from the code" |
| 2026-04-15 | `uv run` and `poetry run` prefixes match the Python tools | Asked for after `uv run pytest` passed through. Since 2026-06-01 the wrapper recursion also covers them |
| 2026-06-01 | Recurse into `bash-classify`'s `inner_commands` instead of anchoring on argv[0] | `timeout 300 yarn nx test` passed through. A ~140-line wrapper allowlist was written and thrown away |
| 2026-06-01 | The hook gets a stdlib `unittest` suite, with an end-to-end layer that skips without `bash-classify` | The maintainer asked for a simple test |
| 2026-08-24 | The whitelist applies at every nesting depth; the blanket "any `agent_id` passes" rule is gone | A subagent that orchestrates its own workers has a context worth protecting. Only about 8% of Bash output in three months of transcripts came from main sessions |
| 2026-08-24 | No depth check; an exempt `agent_type` list with built-in defaults | Hook payloads carry no depth. Reading `spawnDepth` from the agent's `.meta.json` sidecar was rejected: "I would like to avoid parsing the .meta.json". A retry-once escape, the assistant's recommendation, was rejected in favor of the stateless list |
| 2026-08-24 | Exempt patterns must match the whole agent type | An over-broad pattern silently disables the plugin for that agent; a missing one costs one turn |
| 2026-08-24 | The exempt list is the `exempt_agent_types` plugin option, not a file | `.claude/<plugin>.local.md` and a project JSON file were proposed and dropped for the official `userConfig`. Claude Code reads `pluginConfigs` only from user settings, so a repository cannot ship the list |
| 2026-08-24 | `searxngcli:agent` and `web-researcher:agent` are exempt; `gemini-cli:review-agent` is not | The first has Bash and no Agent tool, so it deadlocked. The second has no Bash and is listed in case that changes. The third has the Agent tool |
| 2026-08-24 | Widen the whitelist from a replay of 222,607 Bash calls: `compile\w*`, JVM analysis tasks, absolute-path wrappers, named suffixed tasks, Node `prettier`/`tscheck`/`npx`, `kubectl logs` | +1,401 commands and +2.9 MB caught, nothing previously blocked lost. Blanket `test\w*` and `war\w*` matched a project path and `--warning-mode`. Reading tools, `searxng search`, schema dumps and dev servers stay out |
| 2026-08-25 | Depend on `bash-classify-hook@fprochazka-bash-classify` | The hook denies every Bash call without the classifier. The dependency does not install the `bash-classify` binary, which stays a manual `uv tool install` |
| 2026-11-14 | `noisy-runner` runs on Haiku instead of Sonnet | On the eval suite Haiku at default effort scored no worse (pass^3 5 of 6 against 4 of 6, mean 0.97 against 0.93, noise ±0.24) at about 1/20 of the subagent cost. `effort: high` gave no measurable gain. Keeping Sonnet was rejected for the cost |

## How changes are checked

`make all` must pass: the repository checks in `scripts/check.sh`, `claude plugin validate --strict`, and the hook tests in `hooks/test_enforce_subagent.py`. The end-to-end tests skip when `bash-classify` is not installed, so run them where it is.

A change to the whitelist is measured against real transcripts: replay the Bash calls from `~/.claude/projects` through the old and the new hook, and compare what each blocks. The change must add the commands it targets and unblock nothing that was blocked, unless that is the point. Add every false positive found on the way as a test.

A change to `noisy-runner` (its prompt, model or effort) runs the eval suite in the private `claude-code-plugins-evals` repository, under `repos/fprochazka/claude-code-plugins/noisy-tools-in-subagent/`, with its `bin/run-cases` runner, which runs `claude -p` in a container. `claude plugin eval` does not fit: its bubblewrap sandbox gives each Bash call a private `/tmp` and denies Read on the logs, so the subagent cannot read its own tee logs. A session without access to that repository says so in its summary instead of claiming the change was checked.

Known limits of the suite as of 2026-11-14:

- The 6 cases are synthetic fixtures, not real sessions.
- The model was measured on the Anthropic API only. On Bedrock or Vertex, `haiku` resolves to Haiku 4.5, which was not tested.
- Untested: whether the `/tmp` tee logs stay readable when a user turns on Claude Code's Bash sandbox in a real session.
