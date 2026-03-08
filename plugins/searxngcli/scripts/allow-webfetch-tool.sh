#!/bin/sh
INPUT=$(cat)
AGENT=$(echo "$INPUT" | jq -r '.agent_type // empty')

# Only act when called from the searxngcli agent, ignore everything else
if [ "$AGENT" != "searxngcli:agent" ]; then
  exit 0
fi

echo '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"allow","permissionDecisionReason":"WebFetch allowed"}}'
