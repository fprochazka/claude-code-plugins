#!/usr/bin/env python3
"""
PreToolUse hook for the `noisy-tools-in-subagent` plugin.

Rejects Bash tool calls in the main agent context when they invoke noisy
commands (builds, tests, linters, static analysis) that would pollute the
main context with large volumes of output. The main agent is instructed to
delegate such commands to the `noisy-runner` subagent, which interprets the
output in its own context and reports back a concise summary.

Behavior:
- Only acts on Bash tool calls (matcher handles this, but we double-check).
- Passes through when the payload's `agent_type` matches an exempt pattern
  (the built-in defaults plus the `exempt_agent_types` plugin option). Every
  other agent is subject to the whitelist, at any nesting depth.
- Parses the bash command using `bash-classify` (tree-sitter based) to walk
  every command in pipelines / subshells / chains. Matches each command's
  argv against a regex whitelist.
- On match: emits JSON with `permissionDecision: "deny"` on stdout and
  exits 0. The denial reason explains why and how to delegate.
- If `bash-classify` is not installed: same deny path with install
  instructions as the reason.

Why explicit JSON-deny and not `exit 2`:

Multiple PreToolUse:Bash hooks can run in parallel (e.g. bash-classify-hook
also hooks Bash and returns `permissionDecision: "allow"` for low-risk
commands). Claude Code's hook aggregation precedence is
`deny > defer > ask > allow`, but this only works with *explicit*
`permissionDecision` values. Returning `exit 2` with stderr is classified
as a hook "error", not a "deny", and loses the vote to another hook's
explicit "allow". So we must emit `{"permissionDecision": "deny"}` to win
the aggregation and actually block the tool call.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys


# ---------------------------------------------------------------------------
# Whitelist of noisy commands that MUST run in a subagent.
#
# Each entry is a regex matched against the full argv of a single command
# (joined with spaces) as returned by bash-classify. Any command in a pipe
# / chain / subshell matching any regex triggers a block.
#
# Tuning philosophy: for build tools with distinct "small" subcommands
# (mvn help:*, gradle tasks, mvn dependency:tree) we match on lifecycle
# phases so those small introspection commands pass through.
# ---------------------------------------------------------------------------

# `compile\w*` covers the per-language variants Gradle generates (`compileJava`,
# `compileTestJava`, `compileKotlin`). The suffixed `test*` and `install*` task
# names are listed one by one instead: a blanket `test\w*` also matches project
# paths like `:testing-typed-ids:dependencies`, which must stay unblocked.
_MVN_GRADLE_PHASES = (
    r"\b("
    r"clean|compile\w*|package|install|installDist|deploy|site|"
    r"build|assemble|jar|war|shadowJar|bootJar|publishToMavenLocal|"
    r"test|testClasses|testCodeCoverageReport|verify|check|"
    r"integrationTest|functionalTest|e2e|"
    r"javadoc|dokka"
    r")\b"
)

# Static analysis runs as ordinary tasks, not lifecycle phases, so it needs its
# own list. The `\w*` tail catches the per-source-set names Gradle derives
# (`checkstyleMain`, `checkstyleTest`, `spotbugsMain`, `jacocoTestReport`).
_JVM_ANALYSIS_TASKS = (
    r"\b("
    r"checkstyle|spotbugs|pmd|detekt|ktlint|jacoco|sonarqube"
    r")\w*\b"
)

# Wrappers are invoked by absolute path as often as by `./`, especially from a
# git worktree or a parent directory.
_WRAPPER_PATH = r"(?:\S*/)?"

_NODE_KEYWORDS = (
    r"\b("
    r"build|test|lint|check|typecheck|tsc|tscheck|tsCheck|"
    r"e2e|unit|integration|coverage|prettier|"
    r"vitest|jest|karma|cypress|playwright"
    r")\b"
)

# Nx task runner targets that are noisy (they fan out into builds/tests/lints).
# Deliberately EXCLUDES cheap introspection targets (`graph`, `list`, `show`,
# `report`) so those pass through. The `(?::\w+)?` tail catches the
# `affected:test` / `run-many:build` colon-suffixed forms, while a separate
# `--target=<noisy>` branch catches `nx run-many --target=test`.
_NX_TARGETS = (
    r"(?:"
    r"\b(?:build|test|lint|e2e|serve|run|run-many|affected|migrate)(?::\w+)?\b"
    r"|--target[=\s]+(?:build|test|lint|e2e|serve)\b"
    r")"
)

WHITELIST: list[re.Pattern[str]] = [
    # --- Maven / Gradle (JVM) — only on lifecycle phases ---
    re.compile(rf"^mvn\s+.*(?:{_MVN_GRADLE_PHASES}|{_JVM_ANALYSIS_TASKS})"),
    re.compile(rf"^{_WRAPPER_PATH}mvnw\s+.*(?:{_MVN_GRADLE_PHASES}|{_JVM_ANALYSIS_TASKS})"),
    re.compile(rf"^gradle\s+.*(?:{_MVN_GRADLE_PHASES}|{_JVM_ANALYSIS_TASKS})"),
    re.compile(rf"^{_WRAPPER_PATH}gradlew\s+.*(?:{_MVN_GRADLE_PHASES}|{_JVM_ANALYSIS_TASKS})"),

    # --- Node / JS / TS ---
    re.compile(rf"^(?:npm|pnpm|yarn|npx)\s+.*{_NODE_KEYWORDS}"),
    # Nx invoked via its own binary or npx. The yarn/npm/pnpm-prefixed forms
    # (`yarn nx test`) already match the node pattern above; these catch the
    # bare `nx test` and `npx nx test` invocations.
    re.compile(rf"^npx\s+nx\s+.*{_NX_TARGETS}"),
    re.compile(rf"^nx\s+.*{_NX_TARGETS}"),
    re.compile(r"^tsc(?:\s|$)"),
    re.compile(r"^eslint(?:\s|$)"),
    re.compile(r"^biome\s+(?:check|lint|ci)\b"),

    # --- Python ---
    # Bare invocations and common runner-wrapped forms (`uv run <tool>`,
    # `poetry run <tool>`). The wrapper prefix is optional so one pattern
    # covers both `pytest` and `uv run pytest`.
    re.compile(r"^(?:(?:uv|poetry)\s+run\s+)?pytest(?:\s|$)"),
    re.compile(r"^(?:(?:uv|poetry)\s+run\s+)?tox(?:\s|$)"),
    re.compile(r"^(?:(?:uv|poetry)\s+run\s+)?nox(?:\s|$)"),
    re.compile(r"^(?:(?:uv|poetry)\s+run\s+)?ruff\s+(?:check|format)\b"),
    re.compile(r"^(?:(?:uv|poetry)\s+run\s+)?mypy(?:\s|$)"),
    re.compile(r"^(?:(?:uv|poetry)\s+run\s+)?pyright(?:\s|$)"),
    re.compile(r"^(?:(?:uv|poetry)\s+run\s+)?pylint(?:\s|$)"),
    re.compile(r"^(?:(?:uv|poetry)\s+run\s+)?flake8(?:\s|$)"),

    # --- Rust ---
    re.compile(r"^cargo\s+(?:build|test|check|clippy|bench|doc)\b"),

    # --- Go ---
    re.compile(r"^go\s+(?:build|test|vet|generate)\b"),
    re.compile(r"^golangci-lint(?:\s|$)"),

    # --- Kubernetes ---
    # Only `logs`. `kubectl get/describe` is usually a short status check the
    # caller reads directly.
    re.compile(r"^kubectl\s+logs\b"),

    # --- Make / Bazel / generic ---
    re.compile(r"^make(?:\s|$)"),
    re.compile(r"^bazel\s+(?:build|test)\b"),
    re.compile(r"^buck2?\s+(?:build|test)\b"),
]


# ---------------------------------------------------------------------------
# Agents exempt from the whitelist.
#
# A blocked agent has to be able to delegate, and some cannot: the noisy-runner
# is the delegation target itself, several agents omit the Agent tool from
# their definition, and an agent at the subagent nesting limit is not offered
# the Agent tool at all.
#
# None of that is visible to a hook. Claude Code builds hook input from a fixed
# key set — session_id, transcript_path, cwd, prompt_id, permission_mode,
# agent_id, agent_type, effort — and routes spawn depth and parentAgentId only
# to OpenTelemetry spans and the x-claude-code-parent-agent-id API header. So
# the exempt set is declared, not derived.
#
# Patterns must match the whole `agent_type` (`re.fullmatch`). An over-broad
# pattern silently disables the plugin for that agent, while a missing one
# costs a single denied turn, so the stricter match is the safer default.
# ---------------------------------------------------------------------------

DEFAULT_EXEMPT_AGENT_TYPES = (
    "noisy-tools-in-subagent:noisy-runner",
    "Explore",
    "Plan",
    "code-review:review-.*",
    "searxngcli:agent",
    "web-researcher:agent",
)

# `userConfig.exempt_agent_types` in plugin.json reaches a shell-form hook only
# through the environment: `${user_config.*}` substitution is rejected for
# shell-form hook commands.
EXEMPT_OPTION_ENV_VAR = "CLAUDE_PLUGIN_OPTION_EXEMPT_AGENT_TYPES"


REJECT_MESSAGE_TEMPLATE = """\
Noisy command (matched `{matched_argv}`) — run it in the noisy-runner subagent, not here.

Agent tool:
  subagent_type: "noisy-tools-in-subagent:noisy-runner"
  prompt: the command(s), verbatim

If you have no Agent tool, report this back to your caller instead. Do not retry the command."""

BASH_CLASSIFY_MISSING_MESSAGE = """\
The noisy-tools-in-subagent plugin requires `bash-classify` but it is not on \
PATH.

Install: `uv tool install bash-classify`

See: https://github.com/fprochazka/bash-classify"""


def _reject(message: str) -> "None":
    """Block the tool call via explicit `permissionDecision: "deny"`.

    We use explicit JSON-deny instead of `exit 2` because multiple
    PreToolUse:Bash hooks run in parallel and vote: `exit 2` is classified
    as a hook error and loses to another hook's explicit "allow". Only an
    explicit `"deny"` wins the `deny > … > allow` precedence aggregation.

    `suppressOutput: true` is set to avoid Claude Code rendering the
    rejection reason twice in the tool result (once as a "hook returned
    blocking error" transcript line, once as the structured "Error:" card).
    With suppressOutput on, only the structured card remains — the
    `permissionDecisionReason` still reaches the agent via the denial.
    """
    response = {
        "suppressOutput": True,
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": message,
        },
    }
    json.dump(response, sys.stdout)
    sys.exit(0)


def _passthrough() -> "None":
    """Allow the tool call to proceed by exiting 0 with no output.

    We deliberately do NOT emit an explicit `"allow"` here — that would
    override any other hook that wants to deny this call (e.g. a safety
    hook blocking `rm -rf /`). A silent exit 0 is a non-vote: it neither
    blocks nor short-circuits permission prompts, leaving other hooks and
    the normal permission flow to decide.
    """
    sys.exit(0)


def _classify(command: str) -> "list[dict]":
    """Run bash-classify on the command and return its parsed `commands` list.

    Returns an empty list if classification fails for any reason — the
    caller will then fall back to regex matching against the raw command.
    """
    try:
        result = subprocess.run(
            ["bash-classify"],
            input=command,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (subprocess.TimeoutExpired, OSError):
        return []

    if result.returncode != 0 or not result.stdout:
        return []

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        return []

    commands = data.get("commands", [])
    if not isinstance(commands, list):
        return []
    return commands


def _iter_command_argvs(entry: "dict") -> "Iterator[list[str]]":
    """Yield the argv of `entry` and of every nested inner command.

    Many noisy commands reach us behind a wrapper that swallows the real
    command as its argument tail — `timeout 300 yarn nx test`, `rtk yarn test`,
    `env FOO=1 pytest`, `nice -n 10 cargo test`, even `bash -c "yarn test"`.
    bash-classify already understands these: it keeps the wrapper as a command
    node whose `argv` begins with the wrapper, AND exposes the *unwrapped* real
    command under `inner_commands` (recursively, so stacked wrappers like
    `rtk timeout 300 yarn test` nest several levels deep, each `inner_commands`
    entry carrying the next argv with the wrapper peeled).

    By walking `inner_commands` we let the `^`-anchored WHITELIST patterns match
    the real tool (`yarn`/`pytest`/`cargo`) even when it is hidden behind one or
    more wrappers — without us maintaining any wrapper-specific arg-skipping
    logic ourselves. The wrapper's own top-level argv is also yielded, but it
    harmlessly fails the anchored patterns (it starts with `timeout`/`env`/…).
    Non-wrapper heads like `echo` simply have no `inner_commands`, so
    `echo yarn test` is never mistaken for actually running yarn.
    """
    if not isinstance(entry, dict):
        return
    argv = entry.get("argv")
    if isinstance(argv, list):
        yield [str(a) for a in argv]
    inner = entry.get("inner_commands")
    if isinstance(inner, list):
        for child in inner:
            yield from _iter_command_argvs(child)


def _check_argv(argv: "list[str]") -> "tuple[re.Pattern[str], str] | None":
    """Return (matched pattern, joined argv) if argv triggers the whitelist."""
    if not argv:
        return None
    joined = " ".join(argv)
    for pattern in WHITELIST:
        if pattern.search(joined):
            return (pattern, joined)
    return None


def _parse_exempt_option(raw: "str | None") -> "list[str]":
    """Split the plugin option's raw env value into individual patterns.

    A `multiple` userConfig option has no documented serialization, so accept
    the three plausible shapes: a JSON array, one pattern per line, or a
    comma-separated list. JSON and newlines are tried first because a regex may
    legitimately contain a comma (`a{1,3}`); such a pattern must be written as
    JSON or on its own line.
    """
    raw = (raw or "").strip()
    if not raw:
        return []

    if raw[0] in "[\"":
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            data = None
        if isinstance(data, list):
            return [str(item).strip() for item in data if str(item).strip()]
        if isinstance(data, str):
            raw = data.strip()

    lines = [line.strip() for line in raw.splitlines() if line.strip()]
    if len(lines) > 1:
        return lines
    return [part.strip() for part in raw.split(",") if part.strip()]


def _exempt_patterns() -> "list[re.Pattern[str]]":
    """Compile the built-in exempt patterns plus any the user configured.

    An invalid user pattern is skipped rather than raised: a hook that crashes
    on bad config would block every Bash call in the session.
    """
    compiled = []
    for pattern in list(DEFAULT_EXEMPT_AGENT_TYPES) + _parse_exempt_option(
        os.environ.get(EXEMPT_OPTION_ENV_VAR)
    ):
        try:
            compiled.append(re.compile(pattern))
        except re.error:
            continue
    return compiled


def _is_exempt_agent(agent_type: "str | None") -> bool:
    """Whether `agent_type` names an agent that is allowed to run noisy commands."""
    if not agent_type:
        return False
    return any(pattern.fullmatch(agent_type) for pattern in _exempt_patterns())


def main() -> "None":
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        # Malformed input — fail open, don't block unrelated tool calls.
        _passthrough()

    # Only act on Bash tool calls. The matcher should already handle this,
    # but be defensive.
    if payload.get("tool_name") != "Bash":
        _passthrough()

    # Agents that cannot delegate are exempt. Everything else is enforced,
    # whether it is the main thread or a subagent at any nesting depth.
    if _is_exempt_agent(payload.get("agent_type")):
        _passthrough()

    tool_input = payload.get("tool_input") or {}
    command = tool_input.get("command") or ""
    if not command.strip():
        _passthrough()

    # Require bash-classify before doing anything — we can't reliably parse
    # pipelines / subshells without it, and fail-open would silently defeat
    # the plugin's entire purpose.
    if shutil.which("bash-classify") is None:
        _reject(BASH_CLASSIFY_MISSING_MESSAGE)

    parsed_commands = _classify(command)
    if not parsed_commands:
        # bash-classify ran but gave us nothing usable. Fall back to matching
        # the raw command string — better than failing open on a noisy build.
        match = _check_argv([command.strip()])
        if match is not None:
            _, joined = match
            _reject(REJECT_MESSAGE_TEMPLATE.format(matched_argv=joined))
        _passthrough()

    # Walk every classified command in the pipeline / chain, descending into
    # `inner_commands` so commands hidden behind wrappers (timeout/env/rtk/…)
    # are matched against the WHITELIST too. See `_iter_command_argvs`.
    for entry in parsed_commands:
        for argv in _iter_command_argvs(entry):
            match = _check_argv(argv)
            if match is not None:
                _, joined = match
                _reject(REJECT_MESSAGE_TEMPLATE.format(matched_argv=joined))

    _passthrough()


if __name__ == "__main__":
    main()
