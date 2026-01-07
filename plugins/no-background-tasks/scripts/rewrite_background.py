#!/usr/bin/env python3
"""
PreToolUse hook that rewrites run_in_background: true to false.

This ensures all Bash commands and Task (subagent) calls execute
in the foreground, forcing Claude to wait for completion.
"""

import json
import sys


def main():
    try:
        hook_input = json.load(sys.stdin)
    except json.JSONDecodeError:
        sys.exit(0)

    tool_input = hook_input.get("tool_input", {})

    # Check if run_in_background is set to true
    if tool_input.get("run_in_background") is not True:
        # Nothing to rewrite, allow as-is
        sys.exit(0)

    # Rewrite run_in_background to false
    output = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow",
            "updatedInput": {
                "run_in_background": False
            }
        }
    }

    print(json.dumps(output))


if __name__ == "__main__":
    main()
