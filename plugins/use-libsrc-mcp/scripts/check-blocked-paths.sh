#!/usr/bin/env bash
set -euo pipefail

# PreToolUse hook: blocks attempts to extract/inspect source code from
# dependency cache directories and redirects to the libsrc MCP tool.
#
# Allowed: reading POMs, checking cache presence (ls/find), rm for cleanup.
# Blocked: jar/unzip/zipinfo commands, reading .java/.class/.jar files directly.
#
# Exit 0 with no output = no opinion (normal permission flow).
# Exit 2 with stderr = deny with message fed back to Claude.

INPUT=$(cat)
TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // ""')

deny() {
  cat >&2 <<'EOF'
BLOCKED: Do not extract or inspect source code from ~/.m2/repository directly.

Instead, use the mcp__libsrc__get_library_sources MCP tool:
  - To list all dependencies: call with project_dir="/path/to/project"
  - To get source code: call with project_dir="/path/to/project", library_name="<substring>"
    (e.g. library_name="hibernate" matches "org.hibernate:hibernate-core:6.4.1")

The tool resolves dependencies, clones source repos, and returns local filesystem paths to version-specific source code.
EOF
  exit 2
}

# Blocked path patterns - add new entries here
BLOCKED_PATTERNS=(
  '.m2/repository'
)

matches_blocked_path() {
  local text="$1"
  for pattern in "${BLOCKED_PATTERNS[@]}"; do
    if [[ "$text" == *"$pattern"* ]]; then
      return 0
    fi
  done
  return 1
}

case "$TOOL_NAME" in
  Bash)
    CMD=$(echo "$INPUT" | jq -r '.tool_input.command // ""')
    if matches_blocked_path "$CMD"; then
      # Extract the base command (first word, ignoring leading whitespace)
      TRIMMED="${CMD#"${CMD%%[![:space:]]*}"}"
      BASE="${TRIMMED%% *}"
      case "$BASE" in
        jar|unzip|zipinfo)
          deny
          ;;
      esac
    fi
    ;;
  Read)
    FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // ""')
    if matches_blocked_path "$FILE_PATH"; then
      case "$FILE_PATH" in
        *.java|*.class|*.jar)
          deny
          ;;
      esac
    fi
    ;;
esac

# No opinion
exit 0
