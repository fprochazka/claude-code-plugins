#!/usr/bin/env python3
"""
PreToolUse/PostToolUse hook that enforces serial execution.

1. Rewrites run_in_background: true to false
2. Uses session-scoped lock file to prevent parallel tool execution
"""

import json
import os
import sys
from pathlib import Path


def get_lock_path(session_id: str) -> Path:
    """Get session-scoped lock file path."""
    lock_dir = Path.home() / ".claude" / "no-background-tasks"
    lock_dir.mkdir(parents=True, exist_ok=True)
    return lock_dir / f"session-{session_id}.lock"


def acquire_lock(lock_path: Path) -> bool:
    """
    Try to acquire lock using atomic file creation.
    Returns True if lock acquired, False if already held.
    """
    try:
        # O_CREAT | O_EXCL fails if file exists - atomic check-and-create
        fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
        os.write(fd, f"{os.getpid()}\n".encode())
        os.close(fd)
        return True
    except FileExistsError:
        return False
    except Exception:
        return False


def release_lock(lock_path: Path):
    """Release the lock by removing the lock file."""
    try:
        if lock_path.exists():
            lock_path.unlink()
    except Exception:
        pass


def deny(reason: str):
    """Output JSON to deny the tool call."""
    output = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason
        }
    }
    print(json.dumps(output))
    sys.exit(0)


def allow(updated_input: dict = None):
    """Allow the tool call, optionally with modified input."""
    output = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow",
            "permissionDecisionReason": ""
        }
    }
    if updated_input:
        output["hookSpecificOutput"]["updatedInput"] = updated_input
    print(json.dumps(output))
    sys.exit(0)


def main():
    try:
        hook_input = json.load(sys.stdin)
    except json.JSONDecodeError:
        hook_input = {}

    session_id = hook_input.get("session_id", "unknown")
    tool_name = hook_input.get("tool_name", "unknown")
    tool_input = hook_input.get("tool_input", {})

    lock_path = get_lock_path(session_id)

    if "--lock" in sys.argv:
        # Prepare updated input if run_in_background needs rewriting
        updated_input = None
        if tool_input.get("run_in_background") is True:
            updated_input = {"run_in_background": False}

        # Try to acquire session lock for serial execution
        if not acquire_lock(lock_path):
            deny(
                f"Another tool is currently executing in this session. "
                f"Wait for it to complete, then retry this {tool_name} call. "
                f"Do not run multiple tools in parallel! "
            )

        # Lock acquired, allow execution
        allow(updated_input)

    elif "--release" in sys.argv:
        release_lock(lock_path)
        sys.exit(0)

    else:
        print("Usage: rewrite_background.py --lock | --release", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
