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
- If the call originates from a subagent (hook payload has `agent_id`),
  pass through unconditionally — subagents are allowed to run anything.
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

_MVN_GRADLE_PHASES = (
    r"\b("
    r"clean|compile|package|install|deploy|site|"
    r"build|assemble|jar|war|shadowJar|bootJar|"
    r"test|verify|check|integrationTest|functionalTest|e2e|"
    r"javadoc|dokka"
    r")\b"
)

_NODE_KEYWORDS = (
    r"\b("
    r"build|test|lint|check|typecheck|tsc|"
    r"e2e|unit|integration|coverage|"
    r"vitest|jest|karma|cypress|playwright"
    r")\b"
)

WHITELIST: list[re.Pattern[str]] = [
    # --- Maven / Gradle (JVM) — only on lifecycle phases ---
    re.compile(rf"^mvn\s+.*{_MVN_GRADLE_PHASES}"),
    re.compile(rf"^(?:\./)?mvnw\s+.*{_MVN_GRADLE_PHASES}"),
    re.compile(rf"^gradle\s+.*{_MVN_GRADLE_PHASES}"),
    re.compile(rf"^(?:\./)?gradlew\s+.*{_MVN_GRADLE_PHASES}"),

    # --- Node / JS / TS ---
    re.compile(rf"^(?:npm|pnpm|yarn)\s+.*{_NODE_KEYWORDS}"),
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

    # --- Make / Bazel / generic ---
    re.compile(r"^make(?:\s|$)"),
    re.compile(r"^bazel\s+(?:build|test)\b"),
    re.compile(r"^buck2?\s+(?:build|test)\b"),
]


REJECT_MESSAGE_TEMPLATE = """\
Noisy command (matched `{matched_argv}`) — delegate to the `noisy-runner` subagent.

Call the Task tool with:
  subagent_type: "noisy-tools-in-subagent:noisy-runner"
  prompt: the plain command(s) you want to run"""

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


def _check_argv(argv: "list[str]") -> "tuple[re.Pattern[str], str] | None":
    """Return (matched pattern, joined argv) if argv triggers the whitelist."""
    if not argv:
        return None
    joined = " ".join(argv)
    for pattern in WHITELIST:
        if pattern.search(joined):
            return (pattern, joined)
    return None


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

    # If this call originates from any subagent, allow it unconditionally.
    # See research in conversation history: PreToolUse payloads include
    # `agent_id` (and `agent_type`) iff fired from inside a Task-spawned
    # subagent. The presence check on `agent_id` is the canonical detection.
    if "agent_id" in payload and payload.get("agent_id"):
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

    # Walk every classified command in the pipeline / chain.
    for entry in parsed_commands:
        if not isinstance(entry, dict):
            continue
        argv = entry.get("argv")
        if not isinstance(argv, list):
            continue
        match = _check_argv([str(a) for a in argv])
        if match is not None:
            _, joined = match
            _reject(REJECT_MESSAGE_TEMPLATE.format(matched_argv=joined))

    _passthrough()


if __name__ == "__main__":
    main()
