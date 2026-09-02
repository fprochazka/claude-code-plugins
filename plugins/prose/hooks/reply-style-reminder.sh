#!/usr/bin/env bash
# UserPromptSubmit hook: print one static reminder line as additionalContext.
# Static on purpose — hook output is saved in the transcript and replayed on --resume, so nothing here may depend on time or state.
# The line names the skill: on the first turn it makes the agent load it, on every later turn it keeps the loaded rules in force.
set -euo pipefail

cat >/dev/null  # the prompt payload on stdin is not needed

MESSAGE='IMPORTANT: the user expects replies structured per the prose:reply-style skill — load it if it is not loaded yet, then follow it.'

if command -v jq >/dev/null 2>&1; then
  jq -n --arg msg "$MESSAGE" '{hookSpecificOutput: {hookEventName: "UserPromptSubmit", additionalContext: $msg}}'
else
  # Plain stdout on exit 0 is promoted to additionalContext verbatim.
  printf '%s\n' "$MESSAGE"
fi
