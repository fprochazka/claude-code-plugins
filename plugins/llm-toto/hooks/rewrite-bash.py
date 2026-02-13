#!/usr/bin/env python3
"""
PreToolUse hook for Claude Code that rewrites Bash commands to use llm-toto.

Reads hook input JSON from stdin, decides whether to rewrite the command,
and outputs the appropriate hook response.

Rewriting rules:
- Only rewrites Bash tool calls
- Skips commands already using llm-toto
- Skips simple file operations (cat, head, tail, grep on specific files, etc.)
- Skips file management commands (mkdir, cp, mv, rm, etc.)
- Skips git write operations (add, commit, push, etc.)
- Skips package install commands
- Strips trailing filter pipes (| grep, | tail, | head, etc.) from wrapped commands
- Wraps everything else with llm-toto
"""

import json
import os
import re
import sys

PLUGIN_ROOT = os.environ.get("CLAUDE_PLUGIN_ROOT", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LLM_TOTO_SCRIPT = os.path.join(PLUGIN_ROOT, "scripts", "llm-toto.py")

# Commands that should NOT be wrapped (passthrough)
# These are simple, fast, or write operations where buffering adds no value
PASSTHROUGH_PREFIXES = [
    # Already wrapped
    "llm-toto",
    "python3 " + LLM_TOTO_SCRIPT.split("/")[-1],  # already using our script

    # File read operations
    "cat ",
    "head ",
    "tail ",
    "less ",
    "more ",
    "wc ",
    "file ",
    "stat ",
    "readlink ",

    # File write/management
    "echo ",
    "printf ",
    "mkdir ",
    "cp ",
    "mv ",
    "rm ",
    "rmdir ",
    "chmod ",
    "chown ",
    "chgrp ",
    "ln ",
    "touch ",
    "install ",
    "mktemp ",

    # Directory navigation
    "cd ",

    # Shell builtins and env
    "source ",
    ". ",
    "export ",
    "eval ",
    "alias ",
    "unset ",
    "set ",
    "trap ",
    "true",
    "false",
    ":",
    "test ",
    "[ ",
    "[[ ",

    # Package installation (not execution)
    "pip install",
    "pip3 install",
    "npm install",
    "npm ci",
    "yarn install",
    "yarn add",
    "pnpm install",
    "pnpm add",
    "uv pip install",
    "uv sync",
    "uv add",
    "cargo install",
    "go install",
    "gem install",
    "brew install",
    "apt install",
    "apt-get install",

    # Container build/push (not run/exec/logs)
    "docker build",
    "docker push",
    "docker tag",
    "docker login",
    "docker logout",

    # Git write operations
    "git add",
    "git commit",
    "git push",
    "git checkout",
    "git switch",
    "git restore",
    "git stash",
    "git rebase",
    "git merge",
    "git cherry-pick",
    "git tag",
    "git reset",
    "git clean",
    "git init",
    "git clone",
    "git remote",
    "git config",
    "git worktree",
    "git submodule",
    "git bisect",
    "git am",
    "git apply",
    "git format-patch",
    "git pull",  # pull is a write (merge) operation
    "git fetch",
]

# Patterns for grep/sed/awk on specific files (not recursive)
# These are fast targeted file operations, not search-everything operations
SPECIFIC_FILE_OP_PATTERNS = [
    # grep without -r/-R (not recursive search)
    # Matches: grep pattern file.txt, grep -n 'error' log.txt
    # Does NOT match: grep -r pattern ., grep -R 'error' src/
    re.compile(r"^grep\s+(?!-[rR]\b)(?!.*\s-[rR]\b)"),
    # sed on a file
    re.compile(r"^sed\s+"),
    # awk on a file
    re.compile(r"^awk\s+"),
    # diff between files
    re.compile(r"^diff\s+"),
    # sort/uniq on a file
    re.compile(r"^sort\s+"),
    re.compile(r"^uniq\s+"),
    # cut on a file
    re.compile(r"^cut\s+"),
    # tr
    re.compile(r"^tr\s+"),
    # tee
    re.compile(r"^tee\s+"),
    # xargs
    re.compile(r"^xargs\s+"),
]

# Trailing filter pipes that should be stripped when wrapping
TRAILING_PIPE_PATTERN = re.compile(
    r"""
    \s*\|\s*                           # pipe operator
    (?:grep|tail|head|awk|sed|wc|sort|uniq|cut|tr)  # filter command
    (?:\s+[^\|]*)?                     # optional arguments
    (?:                                # optionally chained filters
        \s*\|\s*
        (?:grep|tail|head|awk|sed|wc|sort|uniq|cut|tr)
        (?:\s+[^\|]*)?
    )*
    \s*$                               # end of string
    """,
    re.VERBOSE,
)

# Stderr-to-stdout redirections that are redundant (llm-toto captures both streams)
STDERR_REDIRECT_PATTERN = re.compile(r"\s*2>&1\s*")


def is_passthrough(command: str) -> bool:
    """Check if the command should be passed through without wrapping."""
    stripped = command.strip()

    # Empty command
    if not stripped:
        return True

    # Check prefix-based passthrough
    for prefix in PASSTHROUGH_PREFIXES:
        if stripped.startswith(prefix) or stripped == prefix.rstrip():
            return True

    # Check if it's a specific file operation (grep without -r, sed, awk, etc.)
    for pattern in SPECIFIC_FILE_OP_PATTERNS:
        if pattern.match(stripped):
            return True

    # Variable assignment
    if re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", stripped):
        return True

    # Command substitution or subshell only
    if stripped.startswith("(") or stripped.startswith("$"):
        return True

    return False


def strip_trailing_pipes(command: str) -> str:
    """Strip trailing filter pipes from the command.

    Examples:
        './mvnw package 2>&1 | grep ERROR | head -20' -> './mvnw package'
        './mvnw package 2>&1 | tail -5' -> './mvnw package'
        'kubectl get pods | grep Running' -> 'kubectl get pods'
    """
    result = TRAILING_PIPE_PATTERN.sub("", command)
    result = STDERR_REDIRECT_PATTERN.sub(" ", result)
    return result.strip()


def extract_base_command(command: str) -> str:
    """Extract the base command before any pipes, for passthrough checking.

    Handles compound commands with && and ; by checking the last segment,
    since that's what produces the output.
    """
    # For compound commands (&&, ;), check the last command segment
    # because that's the one whose output matters
    for sep in ["&&", ";"]:
        if sep in command:
            parts = command.rsplit(sep, 1)
            return parts[-1].strip()

    # For piped commands, the first command is the base
    if "|" in command:
        return command.split("|")[0].strip()

    return command.strip()


def rewrite_command(command: str, session_id: str) -> str | None:
    """Determine if and how to rewrite the command. Returns new command or None."""
    stripped = command.strip()

    # Check if the base command should be passed through
    base = extract_base_command(stripped)
    if is_passthrough(base):
        return None

    # Strip trailing filter pipes
    rewritten = strip_trailing_pipes(stripped)

    # Build the llm-toto command
    return f"python3 {LLM_TOTO_SCRIPT} --session {session_id} -- {rewritten}"


def main():
    try:
        input_data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        # Can't parse input, pass through
        sys.exit(0)

    tool_name = input_data.get("tool_name", "")
    if tool_name != "Bash":
        # Not a Bash tool call, pass through
        sys.exit(0)

    tool_input = input_data.get("tool_input", {})
    command = tool_input.get("command", "")

    if not command:
        sys.exit(0)

    session_id = input_data.get("session_id", "default")

    new_command = rewrite_command(command, session_id)

    if new_command is None:
        # No rewrite needed
        sys.exit(0)

    # Output the rewritten command
    response = {
        "hookSpecificOutput": {
            "updatedInput": {
                "command": new_command
            }
        }
    }

    json.dump(response, sys.stdout)
    sys.exit(0)


if __name__ == "__main__":
    main()
