#!/usr/bin/env bash
# Feeds SubagentStart payloads to inject-role.sh and checks which role comes out, and that every role file fits
# under the size limit.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOOK="$HERE/inject-role.sh"
fail=0

# The session running the tests may itself have been started with a role, so every case starts from an
# environment without the launcher's and the plugin's variables.
CLEAN_ENV=(-u FP_CC_AUTH_SWITCH_ROLE -u FP_CC_AUTH_SWITCH_ROLE_PROMPT -u FP_CC_AUTH_SWITCH_ROLE_PROMPT_MODE
  -u CLAUDE_PLUGIN_OPTION_DEFAULT_ROLE -u CLAUDE_PLUGIN_OPTION_RESIDENT_AGENT_TYPES -u CLAUDE_PLUGIN_ROOT)

role_of() {  # $1 event, $2 payload, rest: env assignments
  local event="$1" payload="$2"; shift 2
  env "${CLEAN_ENV[@]}" "$@" bash "$HOOK" "$event" <<<"$payload" 2>/dev/null | jq -r '.hookSpecificOutput.additionalContext' | head -1
}

stderr_of() {  # $1 event, rest: env assignments
  local event="$1"; shift
  env "${CLEAN_ENV[@]}" "$@" bash "$HOOK" "$event" <<<'{}' 2>&1 >/dev/null | head -1
}

TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
printf '# Custom role\n' >"$TMP/custom.md"

check() {  # $1 label, $2 expected heading, $3 actual heading
  if [ "$2" = "$3" ]; then echo "ok   $1"; else echo "FAIL $1: expected '$2', got '$3'"; fail=1; fi
}

check "session start is the worker"                 "# Worker role"             "$(role_of SessionStart '{}' A=1)"
check "default_role option picks the role"         "# Task subagent role"      "$(role_of SessionStart '{}' CLAUDE_PLUGIN_OPTION_DEFAULT_ROLE=task-subagent)"
check "default_role none injects nothing"           ""                          "$(role_of SessionStart '{}' CLAUDE_PLUGIN_OPTION_DEFAULT_ROLE=none)"
check "unknown default_role injects nothing"        ""                          "$(role_of SessionStart '{}' CLAUDE_PLUGIN_OPTION_DEFAULT_ROLE=nope)"
check "unknown default_role warns"                  "agent-roles: the default_role option is 'nope', which this plugin has no role file for; no role injected" "$(stderr_of SessionStart CLAUDE_PLUGIN_OPTION_DEFAULT_ROLE=nope)"
check "prompt in the system prompt (append)"        ""                          "$(role_of SessionStart '{}' FP_CC_AUTH_SWITCH_ROLE=worker FP_CC_AUTH_SWITCH_ROLE_PROMPT="$TMP/custom.md" FP_CC_AUTH_SWITCH_ROLE_PROMPT_MODE=append)"
check "prompt in the system prompt (replace)"       ""                          "$(role_of SessionStart '{}' FP_CC_AUTH_SWITCH_ROLE=worker FP_CC_AUTH_SWITCH_ROLE_PROMPT="$TMP/custom.md" FP_CC_AUTH_SWITCH_ROLE_PROMPT_MODE=replace)"
check "mode none injects the launcher's file"       "# Custom role"             "$(role_of SessionStart '{}' FP_CC_AUTH_SWITCH_ROLE=worker FP_CC_AUTH_SWITCH_ROLE_PROMPT="$TMP/custom.md" FP_CC_AUTH_SWITCH_ROLE_PROMPT_MODE=none)"
check "missing launcher file injects nothing"       ""                          "$(role_of SessionStart '{}' FP_CC_AUTH_SWITCH_ROLE=worker FP_CC_AUTH_SWITCH_ROLE_PROMPT="$TMP/gone.md" FP_CC_AUTH_SWITCH_ROLE_PROMPT_MODE=none)"
check "missing launcher file warns"                 "agent-roles: FP_CC_AUTH_SWITCH_ROLE_PROMPT names $TMP/gone.md, which cannot be read; no role injected" "$(stderr_of SessionStart FP_CC_AUTH_SWITCH_ROLE_PROMPT="$TMP/gone.md" FP_CC_AUTH_SWITCH_ROLE_PROMPT_MODE=none)"
check "role name alone picks the plugin's file"     "# Task subagent role"      "$(role_of SessionStart '{}' FP_CC_AUTH_SWITCH_ROLE=task-subagent CLAUDE_PLUGIN_OPTION_DEFAULT_ROLE=worker)"
check "role name alone picks the dispatcher"       "# Dispatcher role"         "$(role_of SessionStart '{}' FP_CC_AUTH_SWITCH_ROLE=dispatcher)"
check "unknown role name injects nothing"           ""                          "$(role_of SessionStart '{}' FP_CC_AUTH_SWITCH_ROLE=nope)"
check "unknown role name warns"                     "agent-roles: FP_CC_AUTH_SWITCH_ROLE is 'nope', which this plugin has no role file for; no role injected" "$(stderr_of SessionStart FP_CC_AUTH_SWITCH_ROLE=nope)"
check "role name cannot leave roles/"               ""                          "$(role_of SessionStart '{}' FP_CC_AUTH_SWITCH_ROLE=../README)"
check "subagents ignore the launcher's role"        "# Task subagent role"      "$(role_of SubagentStart '{}' FP_CC_AUTH_SWITCH_ROLE=worker FP_CC_AUTH_SWITCH_ROLE_PROMPT="$TMP/custom.md" FP_CC_AUTH_SWITCH_ROLE_PROMPT_MODE=none)"
check "the plugin's resident type is resident"      "# Resident subagent role"  "$(role_of SubagentStart '{"agent_type":"agent-roles:resident"}' A=1)"
check "plain subagent is a task subagent"           "# Task subagent role"      "$(role_of SubagentStart '{"agent_type":"general-purpose"}' A=1)"
check "no agent_type is a task subagent"            "# Task subagent role"      "$(role_of SubagentStart '{}' A=1)"
check "no resident type without the option"         "# Task subagent role"      "$(role_of SubagentStart '{"agent_type":"team:sentinel"}' A=1)"
check "bare name does not match the namespaced"     "# Task subagent role"      "$(role_of SubagentStart '{"agent_type":"sentinel"}' CLAUDE_PLUGIN_OPTION_RESIDENT_AGENT_TYPES='team:sentinel')"
check "option as comma list"                        "# Resident subagent role"  "$(role_of SubagentStart '{"agent_type":"team:sentinel"}' CLAUDE_PLUGIN_OPTION_RESIDENT_AGENT_TYPES='x:y,team:sentinel')"
check "option as JSON array"                        "# Resident subagent role"  "$(role_of SubagentStart '{"agent_type":"team:sentinel"}' CLAUDE_PLUGIN_OPTION_RESIDENT_AGENT_TYPES='["team:sentinel"]')"
check "unknown event prints nothing"                ""                          "$(role_of Stop '{}')"

# Claude Code replaces a hook's additionalContext above 10,000 characters with a short preview and a file path.
# Characters, not bytes: count in a UTF-8 locale.
for role in "$HERE"/../roles/*.md; do
  size=$(LC_ALL=C.UTF-8 wc -m <"$role")
  if [ "$size" -le 9500 ]; then echo "ok   $(basename "$role") is $size characters"; else echo "FAIL $(basename "$role") is $size characters, over 9,500"; fail=1; fi
done

exit $fail
