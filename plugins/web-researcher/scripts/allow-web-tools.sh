#!/bin/sh
INPUT=$(cat)
AGENT=$(echo "$INPUT" | jq -r '.agent_type // empty')

# Only act when called from the web-researcher agent, ignore everything else
if [ "$AGENT" != "web-researcher:agent" ]; then
  exit 0
fi

echo '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"allow","permissionDecisionReason":"Web tool allowed"}}'
