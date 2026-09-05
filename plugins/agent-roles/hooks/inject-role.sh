#!/usr/bin/env bash
# Prints one role file as additionalContext:
#   SessionStart  -> roles/orchestrator.md (the top-level session only, never a subagent)
#   SubagentStart -> roles/worker.md (every subagent, at any nesting depth)
#
# The event name arrives as an argument, so reading the stdin payload is unnecessary and jq is needed
# for the output only. No hook payload carries a nesting depth, so all subagents share one worker role.
#
# Other hooks write their own additionalContext on the same events and the order is unspecified, so a
# role file must read correctly on its own and must never refer to anything outside itself.
set -euo pipefail

cat >/dev/null  # drain the payload on stdin, which this hook does not use

case "${1:-}" in
  SessionStart)  ROLE=orchestrator ;;
  SubagentStart) ROLE=worker ;;
  *) exit 0 ;;
esac

PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
ROLE_FILE="${PLUGIN_ROOT}/roles/${ROLE}.md"

# A missing role file leaves the agent unconstrained rather than breaking the session start.
[ -r "$ROLE_FILE" ] || exit 0

if command -v jq >/dev/null 2>&1; then
  jq -n --arg event "$1" --rawfile ctx "$ROLE_FILE" \
    '{hookSpecificOutput: {hookEventName: $event, additionalContext: $ctx}}'
else
  # Plain stdout on exit 0 is promoted to additionalContext verbatim.
  cat -- "$ROLE_FILE"
fi
