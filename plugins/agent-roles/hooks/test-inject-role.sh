#!/usr/bin/env bash
# Feeds hook payloads to inject-role.sh and checks which role comes out.
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

check "session start is the orchestrator"         "# Orchestrator role"     "$(role_of SessionStart '{}' A=1)"
check "plain subagent is a task worker"           "# Task worker role"      "$(role_of SubagentStart '{"agent_type":"general-purpose"}' A=1)"
check "no agent_type is a task worker"            "# Task worker role"      "$(role_of SubagentStart '{}' A=1)"
check "unknown event prints nothing"              ""                        "$(bash "$HOOK" Stop <<<'{}' | head -1)"

exit $fail
