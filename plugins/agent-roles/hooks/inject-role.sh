#!/usr/bin/env bash
# Prints one role file as additionalContext:
#   SessionStart  -> roles/orchestrator.md (the top-level session only, never a subagent)
#   SubagentStart -> roles/task-worker.md for every subagent, except the agent types listed as
#                    resident, which get roles/resident-worker.md
#
# The event name arrives as an argument. On SubagentStart the payload's `agent_type` decides between
# the two worker roles; no payload carries a nesting depth, so depth never enters into it. Without jq,
# or without the field, every subagent gets the task worker role.
#
# Other hooks write their own additionalContext on the same events and the order is unspecified, so a
# role file must read correctly on its own and must never refer to anything outside itself.
set -euo pipefail

# Agent types that stay alive for a run and report by message. Add more through the
# `resident_agent_types` plugin option, which reaches a shell hook only as this environment variable.
DEFAULT_RESIDENT_AGENT_TYPES="glab:mr-watch"
RESIDENT_OPTION="${CLAUDE_PLUGIN_OPTION_RESIDENT_AGENT_TYPES:-}"

PAYLOAD=$(cat)

case "${1:-}" in
  SessionStart)  ROLE=orchestrator ;;
  SubagentStart) ROLE=task-worker ;;
  *) exit 0 ;;
esac

if [ "$ROLE" = task-worker ] && command -v jq >/dev/null 2>&1; then
  AGENT_TYPE=$(printf '%s' "$PAYLOAD" | jq -r '.agent_type // empty' 2>/dev/null || true)
  if [ -n "$AGENT_TYPE" ]; then
    # The option may be a JSON array (multiple: true) or a comma-separated string; accept both.
    OPTION_TYPES=$(printf '%s' "$RESIDENT_OPTION" | jq -r 'if type == "array" then .[] else . end' 2>/dev/null || printf '%s' "$RESIDENT_OPTION")
    for candidate in $DEFAULT_RESIDENT_AGENT_TYPES $(printf '%s' "$OPTION_TYPES" | tr ',' ' '); do
      [ "$candidate" = "$AGENT_TYPE" ] && ROLE=resident-worker && break
    done
  fi
fi

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
