#!/usr/bin/env bash
# Feeds SubagentStart payloads to inject-role.sh and checks which role comes out, and that every role file fits
# under the size limit.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOOK="$HERE/inject-role.sh"
fail=0

role_of() {  # $1 event, $2 payload, rest: env assignments
  local event="$1" payload="$2"; shift 2
  env "$@" bash "$HOOK" "$event" <<<"$payload" | jq -r '.hookSpecificOutput.additionalContext' | head -1
}

check() {  # $1 label, $2 expected heading, $3 actual heading
  if [ "$2" = "$3" ]; then echo "ok   $1"; else echo "FAIL $1: expected '$2', got '$3'"; fail=1; fi
}

check "session start is the worker"                 "# Worker role"             "$(role_of SessionStart '{}' A=1)"
check "plain subagent is a task subagent"           "# Task subagent role"      "$(role_of SubagentStart '{"agent_type":"general-purpose"}' A=1)"
check "no agent_type is a task subagent"            "# Task subagent role"      "$(role_of SubagentStart '{}' A=1)"
check "no resident type without the option"         "# Task subagent role"      "$(role_of SubagentStart '{"agent_type":"team:sentinel"}' A=1)"
check "bare name does not match the namespaced"     "# Task subagent role"      "$(role_of SubagentStart '{"agent_type":"sentinel"}' CLAUDE_PLUGIN_OPTION_RESIDENT_AGENT_TYPES='team:sentinel')"
check "option as comma list"                        "# Resident subagent role"  "$(role_of SubagentStart '{"agent_type":"team:sentinel"}' CLAUDE_PLUGIN_OPTION_RESIDENT_AGENT_TYPES='x:y,team:sentinel')"
check "option as JSON array"                        "# Resident subagent role"  "$(role_of SubagentStart '{"agent_type":"team:sentinel"}' CLAUDE_PLUGIN_OPTION_RESIDENT_AGENT_TYPES='["team:sentinel"]')"
check "unknown event prints nothing"                ""                          "$(bash "$HOOK" Stop <<<'{}' | head -1)"

# Claude Code replaces a hook's additionalContext above 10,000 characters with a short preview and a file path.
# Characters, not bytes: count in a UTF-8 locale.
for role in "$HERE"/../roles/*.md; do
  size=$(LC_ALL=C.UTF-8 wc -m <"$role")
  if [ "$size" -le 9500 ]; then echo "ok   $(basename "$role") is $size characters"; else echo "FAIL $(basename "$role") is $size characters, over 9,500"; fail=1; fi
done

exit $fail
