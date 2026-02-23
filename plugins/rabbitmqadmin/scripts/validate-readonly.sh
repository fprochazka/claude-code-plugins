#!/usr/bin/env bash
set -euo pipefail

# PreToolUse hook: auto-allow read-only rabbitmqadmin commands.
# Only allows --node with configured connections, rejects inline connection flags.
# Allows piping to grep/head/tail, file redirects, and 2>&1.
# Exit 0 with no output = no opinion (normal permission flow).
# Exit 0 with JSON = allow/deny decision.

allow() {
  echo "{\"hookSpecificOutput\":{\"hookEventName\":\"PreToolUse\",\"permissionDecision\":\"allow\",\"permissionDecisionReason\":\"$1\"}}"
  exit 0
}

INPUT=$(cat)
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty')

# Only handle commands that start with rabbitmqadmin
[[ "$COMMAND" =~ ^rabbitmqadmin([[:space:]]|$) ]] || exit 0

# Reject command chaining (;, &&, ||) — only pipes and redirects are allowed
if echo "$COMMAND" | grep -qE ';|&&|\|\||\$\(|`'; then
  exit 0
fi

# Split into: rabbitmqadmin command, and the tail after the first pipe or redirect
RMQ_CMD="$COMMAND"
TAIL=""
if [[ "$COMMAND" =~ ^([^|]+)\|(.+)$ ]]; then
  RMQ_CMD="${BASH_REMATCH[1]}"
  TAIL="${BASH_REMATCH[2]}"
elif [[ "$COMMAND" =~ ^([^>]+)(>[[:space:]]*.+)$ ]]; then
  RMQ_CMD="${BASH_REMATCH[1]}"
  TAIL="${BASH_REMATCH[2]}"
fi

# Trim trailing whitespace from RMQ_CMD
RMQ_CMD=$(echo "$RMQ_CMD" | sed 's/[[:space:]]*$//')

# Validate the tail (everything after the rabbitmqadmin command)
if [[ -n "$TAIL" ]]; then
  # Trim whitespace
  TAIL_TRIMMED=$(echo "$TAIL" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')

  # Allow: pipe to grep/head/tail (with any flags and arguments)
  # Allow: file redirect (> or >> to a path)
  # Allow: 2>&1 stderr redirect
  # Strip 2>&1, then validate what remains as a whole.
  # Use regex on the entire tail instead of splitting on | (which breaks quoted args like grep -E 'foo|bar').
  TAIL_CLEAN=$(echo "$TAIL_TRIMMED" | sed -E 's/2>&1//g' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')

  if [[ -n "$TAIL_CLEAN" ]]; then
    # Validate each pipe segment individually.
    # Use perl to split on unquoted pipes (respecting single and double quotes).
    SEGMENTS=$(echo "$TAIL_CLEAN" | perl -e '
      $_ = <STDIN>;
      chomp;
      my @segs;
      my $cur = "";
      my $q = "";
      for my $c (split //, $_) {
        if ($q) {
          $cur .= $c;
          $q = "" if $c eq $q;
        } elsif ($c eq "\"" || $c eq "'\''") {
          $cur .= $c;
          $q = $c;
        } elsif ($c eq "|") {
          push @segs, $cur;
          $cur = "";
        } else {
          $cur .= $c;
        }
      }
      push @segs, $cur if $cur ne "";
      print join("\n", @segs);
    ')

    while IFS= read -r segment; do
      segment=$(echo "$segment" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
      [[ -z "$segment" ]] && continue

      # Reject shell substitution in any pipe segment
      if [[ "$segment" =~ \$\( ]] || [[ "$segment" =~ \` ]]; then
        exit 0
      fi

      # Allow: grep/head/tail with any arguments
      if [[ "$segment" =~ ^(grep|head|tail)([[:space:]]|$) ]]; then
        continue
      fi

      # Allow: file redirect (> or >> followed by a path), but reject /dev/tcp and /dev/udp
      if [[ "$segment" =~ ^[\>]+[[:space:]]*/dev/(tcp|udp)/ ]]; then
        exit 0
      fi
      if [[ "$segment" =~ ^[\>]+[[:space:]]*[^[:space:]]+ ]]; then
        continue
      fi

      # Unknown pipe target — require manual approval
      exit 0
    done <<< "$SEGMENTS"
  fi
fi

# Check for --help or -h anywhere in the rabbitmqadmin command
if [[ "$RMQ_CMD" =~ --help ]] || [[ "$RMQ_CMD" =~ [[:space:]]-h$ ]]; then
  allow "rabbitmqadmin help"
fi

# Reject inline connection flags — only pre-configured --node connections allowed
if [[ "$RMQ_CMD" =~ [[:space:]]--(host|port|base-uri|username|password)[[:space:]] ]] \
  || [[ "$RMQ_CMD" =~ [[:space:]]-[HPUup][[:space:]] ]]; then
  exit 0
fi

# If --node/-N is used, validate it against configured connections from ~/.rabbitmqadmin.conf
CONFIG_FILE="${HOME}/.rabbitmqadmin.conf"
if [[ "$RMQ_CMD" =~ [[:space:]](--node|-N)[[:space:]]+([^[:space:]]+) ]]; then
  NODE="${BASH_REMATCH[2]}"
  if [[ -f "$CONFIG_FILE" ]]; then
    CONFIGURED_NODES=$(grep '^\[' "$CONFIG_FILE" | sed 's/\[//;s/\]//')
    if ! echo "$CONFIGURED_NODES" | grep -qxF "$NODE"; then
      exit 0  # unknown node — require manual approval
    fi
  else
    exit 0  # no config file — require manual approval
  fi
fi

# Strip 'rabbitmqadmin' prefix
REST="${RMQ_CMD#rabbitmqadmin}"

# Strip safe flags with values: --node X, -N X, --vhost X, -V X, --table-style X, etc.
REST=$(echo "$REST" | sed -E \
  -e 's/(^|[[:space:]])--(node|vhost|table-style|timeout|path-prefix|config|tls-ca-cert-file|tls-cert-file|tls-key-file)[[:space:]]+[^[:space:]]+//g' \
  -e 's/(^|[[:space:]])-[NVc][[:space:]]+[^[:space:]]+//g')

# Strip safe flags without values: --use-tls, --insecure, -k, --non-interactive, --quiet, -q
REST=$(echo "$REST" | sed -E \
  -e 's/(^|[[:space:]])--(use-tls|insecure|non-interactive|quiet)//g' \
  -e 's/(^|[[:space:]])-[kq]([[:space:]]|$)/ /g')

# Trim leading/trailing whitespace
REST=$(echo "$REST" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')

# Allow-list of read-only subcommand prefixes
READONLY_PATTERNS=(
  "vhosts list"
  "queues list"
  "queues show"
  "exchanges list"
  "bindings list"
  "channels list"
  "connections list"
  "list "
  "show "
  "show$"
  "config_file show"
  "health_check"
  "auth_attempts"
  "nodes"
  "plugins"
  "deprecated_features"
  "feature_flags"
)

for pattern in "${READONLY_PATTERNS[@]}"; do
  if [[ "$REST" =~ ^$pattern ]]; then
    allow "rabbitmqadmin read-only command"
  fi
done

# Not a recognized read-only command — let normal permission flow handle it
exit 0
