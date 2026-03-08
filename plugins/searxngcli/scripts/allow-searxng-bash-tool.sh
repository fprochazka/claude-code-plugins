#!/bin/sh
INPUT=$(cat)
AGENT=$(echo "$INPUT" | jq -r '.agent_type // empty')
CMD=$(echo "$INPUT" | jq -r '.tool_input.command')

# Only act when called from the searxngcli agent, ignore everything else
if [ "$AGENT" != "searxngcli:agent" ]; then
  exit 0
fi

case "$CMD" in
  searxng\ *|searxng)
    echo '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"allow","permissionDecisionReason":"searxng command allowed"}}'
    exit 0
    ;;
  *)
    echo "Only searxng commands are allowed in this agent" >&2
    exit 2
    ;;
esac
