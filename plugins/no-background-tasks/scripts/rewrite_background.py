#!/usr/bin/env python3
"""
PreToolUse/PostToolUse hook that enforces serial execution.

1. Rewrites run_in_background: true to false
2. Uses session-scoped lock file to prevent parallel tool execution
"""

import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path


def log_debug(message: str):
    """Write debug message to log file."""
    log_dir = Path.home() / ".claude" / "no-background-tasks"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "debug.log"
    with open(log_file, "a") as f:
        f.write(f"{datetime.now().isoformat()} {message}\n")


def get_lock_path(session_id: str) -> Path:
    """Get session-scoped lock file path."""
    lock_dir = Path.home() / ".claude" / "no-background-tasks"
    lock_dir.mkdir(parents=True, exist_ok=True)
    return lock_dir / f"session-{session_id}.lock"


# Minimum age (seconds) before a lock can be considered stale
STALE_LOCK_THRESHOLD = 2.0


def acquire_lock(lock_path: Path) -> bool:
    """
    Try to acquire lock using atomic file creation.
    Returns True if lock acquired, False if already held.

    If lock exists but is older than STALE_LOCK_THRESHOLD seconds,
    assume it's from a cancelled tool and take it over.
    """
    try:
        # O_CREAT | O_EXCL fails if file exists - atomic check-and-create
        fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
        os.write(fd, f"{os.getpid()}\n".encode())
        os.close(fd)
        return True
    except FileExistsError:
        # Lock exists - check if it's stale (old enough to be from cancelled tool)
        try:
            lock_age = time.time() - lock_path.stat().st_mtime
            if lock_age > STALE_LOCK_THRESHOLD:
                # Lock is old enough to be stale - take it over
                log_debug(f"Stale lock detected (age={lock_age:.1f}s > {STALE_LOCK_THRESHOLD}s), taking over")
                lock_path.unlink()
                # Try to acquire again
                fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
                os.write(fd, f"{os.getpid()}\n".encode())
                os.close(fd)
                return True
            else:
                log_debug(f"Lock exists, age={lock_age:.1f}s (not stale yet)")
        except Exception as e:
            log_debug(f"Error checking stale lock: {e}")
        return False
    except Exception:
        return False


def release_lock(lock_path: Path, release_all: bool = False):
    """Release the lock by removing lock file(s)."""
    try:
        if release_all:
            # Clean all lock files in the directory
            lock_dir = lock_path.parent
            if lock_dir.exists():
                for f in lock_dir.glob("session-*.lock"):
                    try:
                        f.unlink()
                    except Exception:
                        pass
        elif lock_path.exists():
            lock_path.unlink()
    except Exception:
        pass


def deny(reason: str):
    """Deny the tool call - text to stderr + exit 2 (fed back to Claude)."""
    print(reason, file=sys.stderr)
    sys.exit(2)


def allow(updated_input: dict = None):
    """Allow the tool call, optionally with modified input."""
    if updated_input:
        output = {
            "hookSpecificOutput": {
                "permissionDecision": "allow",
                "updatedInput": updated_input
            }
        }
        print(json.dumps(output))
    # Exit 0 = allow (with or without output)
    sys.exit(0)


def main():
    try:
        hook_input = json.load(sys.stdin)
    except json.JSONDecodeError:
        hook_input = {}

    session_id = hook_input.get("session_id", "unknown")
    hook_event = hook_input.get("hook_event_name", "unknown")
    tool_name = hook_input.get("tool_name", "unknown")
    tool_input = hook_input.get("tool_input", {})

    lock_path = get_lock_path(session_id)

    log_debug(f"args={sys.argv} event={hook_event} session={session_id} tool={tool_name} lock={lock_path}")

    if "--lock" in sys.argv:
        # Prepare updated input if run_in_background needs rewriting
        updated_input = None
        if tool_input.get("run_in_background") is True:
            updated_input = {"run_in_background": False}

        # Try to acquire session lock for serial execution
        if not acquire_lock(lock_path):
            log_debug(f"DENY: lock already exists")
            deny(
                f"This tool call is blocked, because the user doesn't want you to run tools and tasks in parallel. "
                f"If you know about a background task, let it finish and then retry sequentially. "
                f"Do not run multiple tools in parallel!"
            )

        # Lock acquired, allow execution
        log_debug(f"ALLOW: lock acquired")
        allow(updated_input)

    elif "--release" in sys.argv:
        exists_before = lock_path.exists()
        release_lock(lock_path, release_all=False)
        log_debug(f"RELEASE: existed={exists_before} exists_after={lock_path.exists()}")
        sys.exit(0)

    elif "--release-all" in sys.argv:
        release_lock(lock_path, release_all=True)
        log_debug(f"RELEASE-ALL")
        sys.exit(0)

    else:
        print("Usage: rewrite_background.py --lock | --release", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
