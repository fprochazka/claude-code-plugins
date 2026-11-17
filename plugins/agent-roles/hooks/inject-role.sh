#!/usr/bin/env bash
# Prints one role file as additionalContext.
#
# SessionStart (the top-level session only, never a subagent) follows the launcher's environment:
#   1. FP_CC_AUTH_SWITCH_ROLE_PROMPT_MODE is append or replace -> nothing; the launcher already put the
#      role into the system prompt, which compaction does not touch.
#   2. FP_CC_AUTH_SWITCH_ROLE_PROMPT is set -> that file, so the launcher config stays the one place that
#      says which file a role uses.
#   3. Only FP_CC_AUTH_SWITCH_ROLE is set (by hand, without a launcher) -> roles/<that name>.md.
#   4. Nothing is set -> roles/<default_role plugin option>.md, worker when the option is unset.
# A file that does not exist and a role name this plugin does not ship inject nothing and print a
# warning to stderr.
#
# SubagentStart -> roles/task-subagent.md for every subagent, except the agent types listed as
#                  resident, which get roles/resident-subagent.md. A launcher cannot reach subagents.
#
# On SubagentStart the payload's `agent_type` decides between the two subagent roles; no payload
# carries a nesting depth, so depth never enters into it. Without jq, or without the field, every
# subagent gets the task subagent role.
#
# Other hooks write their own additionalContext on the same events and the order is unspecified, so a
# role file must read correctly on its own and must never refer to anything outside itself.
set -euo pipefail

# Agent types that stay alive for a run and report by message come only from the
# `resident_agent_types` plugin option, which reaches a shell hook only as this environment variable.
RESIDENT_OPTION="${CLAUDE_PLUGIN_OPTION_RESIDENT_AGENT_TYPES:-}"

PAYLOAD=$(cat)

PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
ROLE_FILE=""

# A role name becomes a path under roles/, so it may hold only the characters role files are named with.
role_file_for() {
  case "$1" in
    *[!a-z0-9-]* | "") return 1 ;;
  esac
  [ -r "${PLUGIN_ROOT}/roles/$1.md" ] || return 1
  printf '%s' "${PLUGIN_ROOT}/roles/$1.md"
}

case "${1:-}" in
  SessionStart)
    case "${FP_CC_AUTH_SWITCH_ROLE_PROMPT_MODE:-}" in
      append | replace) exit 0 ;;
    esac
    if [ -n "${FP_CC_AUTH_SWITCH_ROLE_PROMPT:-}" ]; then
      ROLE_FILE="$FP_CC_AUTH_SWITCH_ROLE_PROMPT"
      if [ ! -r "$ROLE_FILE" ]; then
        echo "agent-roles: FP_CC_AUTH_SWITCH_ROLE_PROMPT names $ROLE_FILE, which cannot be read; no role injected" >&2
        exit 0
      fi
    elif [ -n "${FP_CC_AUTH_SWITCH_ROLE:-}" ]; then
      if ! ROLE_FILE=$(role_file_for "$FP_CC_AUTH_SWITCH_ROLE"); then
        echo "agent-roles: FP_CC_AUTH_SWITCH_ROLE is '$FP_CC_AUTH_SWITCH_ROLE', which this plugin has no role file for; no role injected" >&2
        exit 0
      fi
    else
      DEFAULT_ROLE="${CLAUDE_PLUGIN_OPTION_DEFAULT_ROLE:-worker}"
      [ "$DEFAULT_ROLE" = none ] && exit 0
      if ! ROLE_FILE=$(role_file_for "$DEFAULT_ROLE"); then
        echo "agent-roles: the default_role option is '$DEFAULT_ROLE', which this plugin has no role file for; no role injected" >&2
        exit 0
      fi
    fi
    ;;
  SubagentStart) ROLE=task-subagent ;;
  *) exit 0 ;;
esac

if [ "${ROLE:-}" = task-subagent ] && command -v jq >/dev/null 2>&1; then
  AGENT_TYPE=$(printf '%s' "$PAYLOAD" | jq -r '.agent_type // empty' 2>/dev/null || true)
  if [ -n "$AGENT_TYPE" ]; then
    # The option may be a JSON array (multiple: true) or a comma-separated string; accept both.
    OPTION_TYPES=$(printf '%s' "$RESIDENT_OPTION" | jq -r 'if type == "array" then .[] else . end' 2>/dev/null || printf '%s' "$RESIDENT_OPTION")
    for candidate in $(printf '%s' "$OPTION_TYPES" | tr ',' ' '); do
      [ "$candidate" = "$AGENT_TYPE" ] && ROLE=resident-subagent && break
    done
  fi
fi

if [ "$1" = SubagentStart ]; then
  ROLE_FILE="${PLUGIN_ROOT}/roles/${ROLE}.md"
  # A missing role file leaves the agent unconstrained rather than breaking the subagent start.
  [ -r "$ROLE_FILE" ] || exit 0
fi

if command -v jq >/dev/null 2>&1; then
  jq -n --arg event "$1" --rawfile ctx "$ROLE_FILE" \
    '{hookSpecificOutput: {hookEventName: $event, additionalContext: $ctx}}'
else
  # Plain stdout on exit 0 is promoted to additionalContext verbatim.
  cat -- "$ROLE_FILE"
fi
