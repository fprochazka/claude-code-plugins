#!/usr/bin/env bash
# Repository checks for the plugin marketplace. Every check runs even after an earlier one failed,
# so one run reports every problem instead of only the first.
#
# Output contract, shared with scripts/check-frontmatter.py:
#   FAIL <check-id> <path>: <what is wrong>
#   warn <check-id> <path>: <what is wrong>   (does not fail the run)
#   ok   <check-id> (<n> items)
# Exit 1 if any FAIL line was printed.
#
# Usage: scripts/check.sh [check-id]   -- with an id, run only that check.

set -euo pipefail

# Plugins queued for deletion. They are exempt from the marketplace and README checks until they are removed.
# When you delete the directory, delete its line here in the same commit.
PENDING_REMOVAL=(markitdown use-libsrc-mcp llm-toto)

# Marketplaces other than this one that a cross-marketplace dependency may point at. Kept as a constant
# rather than parsed out of the README, so a typo in the README cannot make a broken dependency pass.
EXTERNAL_MARKETPLACES=(fprochazka-glab-discussion fprochazka-glab-pipeline fprochazka-bash-classify)

# The complete set of top-level keys a plugin.json may carry. Anything else is either a typo or a
# setting Claude Code works out on its own: "skills", "commands" and "agents" are the default
# discovery paths, and "repository" belongs on the marketplace entry, not the manifest.
PLUGIN_JSON_KEYS='["$schema","name","version","description","author","license","homepage","keywords","dependencies","hooks","mcpServers","userConfig"]'
PLUGIN_JSON_DEFAULT_PATH_KEYS=(skills commands agents)
PLUGIN_JSON_DEFAULT_HOOKS='./hooks/hooks.json'
PLUGIN_JSON_AUTHOR='{"name":"Filip Procházka","url":"https://github.com/fprochazka"}'
PLUGIN_JSON_SCHEMA='https://anthropic.com/claude-code/plugin.schema.json'
PLUGIN_JSON_LICENSE='MIT'
PLUGIN_HOMEPAGE_PREFIX='https://github.com/fprochazka/claude-code-plugins/tree/master/plugins/'
PLUGIN_JSON_REQUIRED=('$schema' name version description author license homepage)
MARKETPLACE_CATEGORIES=(productivity security)

# Hook events Claude Code dispatches. A key outside this set is a hook that never fires.
HOOK_EVENTS=(PreToolUse PostToolUse PostToolUseFailure UserPromptSubmit UserPromptExpansion Stop
  SubagentStart SubagentStop SessionStart SessionEnd PreCompact Notification PermissionRequest)

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

MARKETPLACE=".claude-plugin/marketplace.json"

checks=0
fails=0

fail() { printf 'FAIL %s %s: %s\n' "$1" "$2" "$3"; fails=$((fails + 1)); }
warn() { printf 'warn %s %s: %s\n' "$1" "$2" "$3"; }

# Print the ok line only when the check added no FAIL lines since it started.
finish() {
  local id=$1 before=$2 items=$3
  checks=$((checks + 1))
  if [ "$fails" -eq "$before" ]; then
    printf 'ok %s (%d items)\n' "$id" "$items"
  fi
}

in_list() {
  local needle=$1; shift
  local item
  for item in "$@"; do
    [ "$item" = "$needle" ] && return 0
  done
  return 1
}

is_pending() {
  in_list "$1" ${PENDING_REMOVAL[@]+"${PENDING_REMOVAL[@]}"}
}

plugin_dirs() {
  local d
  for d in plugins/*/; do
    [ -d "$d" ] || continue
    basename "$d"
  done
}

# Directory names that must appear in the marketplace: every plugin dir, minus the pending-removal ones
# that have already lost their manifest.
expected_plugin_names() {
  local n
  while read -r n; do
    if [ ! -f "plugins/$n/.claude-plugin/plugin.json" ] && is_pending "$n"; then
      continue
    fi
    printf '%s\n' "$n"
  done < <(plugin_dirs) | sort
}

manifest_names() {
  local n
  while read -r n; do
    if [ -f "plugins/$n/.claude-plugin/plugin.json" ]; then printf '%s\n' "$n"; fi
  done < <(plugin_dirs) | sort
}

check_plugin_manifest() {
  local before=$fails items=0 name manifest value
  while read -r name; do
    manifest="plugins/$name/.claude-plugin/plugin.json"
    if [ ! -f "$manifest" ]; then
      is_pending "$name" || fail plugin-manifest "plugins/$name" "no .claude-plugin/plugin.json"
      continue
    fi
    items=$((items + 1))
    if ! jq -e . "$manifest" >/dev/null 2>&1; then
      fail plugin-manifest "$manifest" "does not parse as JSON"
      continue
    fi
    value=$(jq -r '.name // ""' "$manifest")
    [ "$value" = "$name" ] || fail plugin-manifest "$manifest" ".name is \"$value\", directory is \"$name\""
    value=$(jq -r '.version // ""' "$manifest")
    [[ $value =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || fail plugin-manifest "$manifest" ".version \"$value\" is not MAJOR.MINOR.PATCH"
    if [ "$(jq -r '.description | type' "$manifest")" != "string" ]; then
      fail plugin-manifest "$manifest" ".description is missing or not a string"
    elif [ -z "$(jq -r '.description' "$manifest" | tr -d '[:space:]')" ]; then
      fail plugin-manifest "$manifest" ".description is empty"
    fi
  done < <(plugin_dirs)
  finish plugin-manifest "$before" "$items"
}

# The manifest is the source of truth for a plugin's identity. The marketplace entry and the README
# row are copies, so this check compares them rather than letting them drift apart silently.
check_plugin_json() {
  local before=$fails items=0 name manifest key value expected entry row text mine theirs
  local author_canonical
  author_canonical=$(printf '%s' "$PLUGIN_JSON_AUTHOR" | jq -c .)
  local -a allowed_keys
  mapfile -t allowed_keys < <(printf '%s' "$PLUGIN_JSON_KEYS" | jq -r '.[]')

  while read -r name; do
    manifest="plugins/$name/.claude-plugin/plugin.json"
    # A manifest that does not parse is already reported by plugin-manifest.
    jq -e . "$manifest" >/dev/null 2>&1 || continue
    items=$((items + 1))

    while read -r key; do
      if in_list "$key" "${PLUGIN_JSON_DEFAULT_PATH_KEYS[@]}"; then
        fail plugin-json "$manifest" "\"$key\": default path key, delete it"
      elif ! in_list "$key" "${allowed_keys[@]}"; then
        fail plugin-json "$manifest" "unknown key \"$key\""
      fi
    done < <(jq -r 'keys_unsorted[]' "$manifest")

    if [ "$(jq -r '.hooks // ""' "$manifest")" = "$PLUGIN_JSON_DEFAULT_HOOKS" ]; then
      fail plugin-json "$manifest" "\"hooks\": default hooks path, delete it"
    fi

    for key in "${PLUGIN_JSON_REQUIRED[@]}"; do
      if [ "$(jq --arg k "$key" 'has($k)' "$manifest")" != "true" ]; then
        fail plugin-json "$manifest" "missing required key \"$key\""
      fi
    done

    if [ "$(jq 'has("$schema")' "$manifest")" = "true" ]; then
      value=$(jq -r '."$schema"' "$manifest")
      [ "$value" = "$PLUGIN_JSON_SCHEMA" ] ||
        fail plugin-json "$manifest" "\$schema is \"$value\", expected \"$PLUGIN_JSON_SCHEMA\""
    fi
    if [ "$(jq 'has("license")' "$manifest")" = "true" ]; then
      value=$(jq -r '.license' "$manifest")
      [ "$value" = "$PLUGIN_JSON_LICENSE" ] ||
        fail plugin-json "$manifest" "license is \"$value\", expected \"$PLUGIN_JSON_LICENSE\""
    fi
    if [ "$(jq 'has("homepage")' "$manifest")" = "true" ]; then
      value=$(jq -r '.homepage' "$manifest")
      expected="$PLUGIN_HOMEPAGE_PREFIX$name"
      [ "$value" = "$expected" ] ||
        fail plugin-json "$manifest" "homepage is \"$value\", expected \"$expected\""
    fi
    if [ "$(jq 'has("author")' "$manifest")" = "true" ]; then
      value=$(jq -c '.author' "$manifest")
      [ "$value" = "$author_canonical" ] ||
        fail plugin-json "$manifest" "author is $value, expected $author_canonical"
    fi

    if [ "$(jq 'has("keywords")' "$manifest")" = "true" ]; then
      if [ "$(jq -r '.keywords | type' "$manifest")" != "array" ]; then
        fail plugin-json "$manifest" "keywords is not an array"
      elif [ "$(jq '.keywords | length' "$manifest")" -eq 0 ]; then
        fail plugin-json "$manifest" "keywords is an empty array"
      else
        while read -r value; do
          [ -n "$value" ] || continue
          fail plugin-json "$manifest" "keyword \"$value\" is not a lower-case-hyphenated string"
        done < <(jq -r '.keywords[] | if type != "string" then tostring elif (test("^[a-z0-9]+(-[a-z0-9]+)*$") | not) then . else empty end' "$manifest")
      fi
    fi

    # Marketplace mirror. A missing entry is marketplace-sync's finding, as are version and source.
    entry=$(jq -c --arg n "$name" '.plugins[] | select(.name == $n)' "$MARKETPLACE")
    if [ -n "$entry" ]; then
      for key in description homepage; do
        mine=$(jq -r --arg k "$key" '.[$k] // ""' "$manifest")
        theirs=$(printf '%s' "$entry" | jq -r --arg k "$key" '.[$k] // ""')
        [ "$mine" = "$theirs" ] || fail plugin-json "$MARKETPLACE" "$name $key does not match $manifest"
      done
      mine=$(jq -c '.author // null' "$manifest")
      theirs=$(printf '%s' "$entry" | jq -c '.author // null')
      [ "$mine" = "$theirs" ] || fail plugin-json "$MARKETPLACE" "$name author does not match $manifest"
      value=$(printf '%s' "$entry" | jq -r '.category // ""')
      if [ -z "$value" ]; then
        fail plugin-json "$MARKETPLACE" "$name has no category"
      elif ! in_list "$value" "${MARKETPLACE_CATEGORIES[@]}"; then
        fail plugin-json "$MARKETPLACE" "$name category \"$value\" is not one of: ${MARKETPLACE_CATEGORIES[*]}"
      fi
    fi

    # README mirror. A missing row is readme-table's finding.
    if ! is_pending "$name"; then
      row=$(grep -F "| [$name](plugins/$name/) |" README.md | head -1 || true)
      if [ -n "$row" ]; then
        text=${row#*"](plugins/$name/) |"}
        text=${text%|}
        text=$(printf '%s' "$text" | sed -E 's/^[[:space:]]+//; s/[[:space:]]+$//')
        [ "$text" = "$(jq -r '.description // ""' "$manifest")" ] ||
          fail plugin-json README.md "$name row text does not match the description in $manifest"
      fi
    fi
  done < <(manifest_names)
  finish plugin-json "$before" "$items"
}

check_marketplace_sync() {
  local before=$fails items=0 name mv pv source
  if ! jq -e . "$MARKETPLACE" >/dev/null 2>&1; then
    fail marketplace-sync "$MARKETPLACE" "does not parse as JSON"
    finish marketplace-sync "$before" 0
    return
  fi
  while read -r name; do
    if [ -n "$name" ]; then fail marketplace-sync "$MARKETPLACE" "plugins/$name has no entry"; fi
  done < <(comm -23 <(expected_plugin_names) <(jq -r '.plugins[].name' "$MARKETPLACE" | sort))
  while read -r name; do
    if [ -n "$name" ]; then fail marketplace-sync "$MARKETPLACE" "entry \"$name\" has no plugins/$name directory"; fi
  done < <(comm -13 <(expected_plugin_names) <(jq -r '.plugins[].name' "$MARKETPLACE" | sort))
  while read -r name; do
    [ -n "$name" ] || continue
    items=$((items + 1))
    mv=$(jq -r --arg n "$name" '.plugins[] | select(.name == $n) | .version // ""' "$MARKETPLACE")
    pv=$(jq -r '.version // ""' "plugins/$name/.claude-plugin/plugin.json")
    [ "$mv" = "$pv" ] || fail marketplace-sync "$MARKETPLACE" "$name version $mv, plugin.json says $pv"
    source=$(jq -r --arg n "$name" '.plugins[] | select(.name == $n) | .source // ""' "$MARKETPLACE")
    [ "$source" = "./plugins/$name" ] || fail marketplace-sync "$MARKETPLACE" "$name source is \"$source\", expected \"./plugins/$name\""
  done < <(comm -12 <(manifest_names) <(jq -r '.plugins[].name' "$MARKETPLACE" | sort))
  finish marketplace-sync "$before" "$items"
}

check_readme_table() {
  local before=$fails items=0 name dir
  while read -r name; do
    is_pending "$name" && continue
    items=$((items + 1))
    grep -qF "| [$name](plugins/$name/) |" README.md ||
      fail readme-table README.md "no row for \"$name\" starting with [$name](plugins/$name/)"
  done < <(jq -r '.plugins[].name' "$MARKETPLACE")
  while read -r dir; do
    [ -n "$dir" ] || continue
    if [ ! -d "plugins/$dir" ]; then fail readme-table README.md "row links to plugins/$dir/, which does not exist"; fi
  done < <(grep -oE '^\| \[[^]]+\]\(plugins/[^)]+/\)' README.md | sed -E 's#.*\(plugins/([^)]+)/\)#\1#')
  finish readme-table "$before" "$items"
}

check_dependencies() {
  local before=$fails items=0 name manifest kind dep market row declared listed count
  local mp_names
  mp_names=$(jq -r '.plugins[].name' "$MARKETPLACE")
  while read -r name; do
    manifest="plugins/$name/.claude-plugin/plugin.json"
    while IFS=$'\t' read -r kind dep market; do
      [ -n "$kind" ] || continue
      items=$((items + 1))
      case "$kind" in
        s)
          # shellcheck disable=SC2086 # word splitting is how the newline-separated name list becomes arguments
          in_list "$dep" $mp_names || fail dependencies "$manifest" "dependency \"$dep\" is not a plugin in $MARKETPLACE"
          ;;
        o)
          [ -n "$dep" ] || fail dependencies "$manifest" "object dependency has no .name"
          if [ -z "$market" ]; then
            fail dependencies "$manifest" "dependency \"$dep\" has no .marketplace"
          else
            in_list "$market" "${EXTERNAL_MARKETPLACES[@]}" ||
              fail dependencies "$manifest" "dependency \"$dep\" names unknown marketplace \"$market\""
          fi
          ;;
        *)
          fail dependencies "$manifest" "dependency entry is neither a string nor an object"
          ;;
      esac
    done < <(jq -r '(.dependencies // [])[] | if type == "string" then "s\t" + . + "\t"
                    elif type == "object" then "o\t" + (.name // "") + "\t" + (.marketplace // "")
                    else "x\t\t" end' "$manifest")
  done < <(manifest_names)

  # The README's dependency table is documentation of the manifests; drift there misleads whoever reads it.
  declared=$(while read -r name; do
    if [ "$(jq -r '(.dependencies // []) | length' "plugins/$name/.claude-plugin/plugin.json")" != "0" ]; then printf '%s\n' "$name"; fi
  done < <(manifest_names) | sort)
  listed=$(readme_dependency_rows | cut -f1 | sort)
  while read -r name; do
    if [ -n "$name" ]; then fail dependencies README.md "plugin \"$name\" has dependencies but no row in the \"Depends on\" table"; fi
  done < <(comm -23 <(printf '%s\n' "$declared") <(printf '%s\n' "$listed"))
  while read -r name; do
    if [ -n "$name" ]; then fail dependencies README.md "\"Depends on\" table lists \"$name\", which declares no dependencies"; fi
  done < <(comm -13 <(printf '%s\n' "$declared") <(printf '%s\n' "$listed"))
  while IFS=$'\t' read -r name row; do
    [ -n "$name" ] || continue
    [ -f "plugins/$name/.claude-plugin/plugin.json" ] || continue
    dep=$(jq -r '(.dependencies // [])[] | if type == "string" then . else (.name // "") end' \
      "plugins/$name/.claude-plugin/plugin.json" | sort | tr '\n' ' ')
    market=$(printf '%s\n' "$row" | grep -oE '`[^`]+`' | tr -d '`' | sort | tr '\n' ' ')
    [ "$dep" = "$market" ] || fail dependencies README.md "\"Depends on\" row for \"$name\" lists [$market], manifest declares [$dep]"
  done < <(readme_dependency_rows)
  finish dependencies "$before" "$items"
}

# Rows of the README's "| Plugin | Depends on |" table, as "<plugin name>\t<second cell>".
readme_dependency_rows() {
  awk '
    /^\| Plugin \| Depends on \|/ { inside = 1; next }
    inside && /^\|[- ]*\|[- ]*\|/ { next }
    inside && /^\|/ { print; next }
    inside { exit }
  ' README.md | sed -E 's/^\| *`([^`]+)` *\|/\1\t/'
}

check_hooks_json() {
  local before=$fails items=0 file plugin key command token target
  for file in plugins/*/hooks/hooks.json; do
    [ -f "$file" ] || continue
    items=$((items + 1))
    plugin="${file%/hooks/hooks.json}"
    if ! jq -e . "$file" >/dev/null 2>&1; then
      fail hooks-json "$file" "does not parse as JSON"
      continue
    fi
    if [ "$(jq -r '.hooks | type' "$file")" != "object" ]; then
      fail hooks-json "$file" "no top-level .hooks object"
      continue
    fi
    while read -r key; do
      in_list "$key" "${HOOK_EVENTS[@]}" || fail hooks-json "$file" "\"$key\" is not a hook event"
    done < <(jq -r '.hooks | keys[]' "$file")
    while read -r count; do
      if [ "$count" != "0" ]; then fail hooks-json "$file" "$count command hook(s) without a \"command\" string"; fi
    done < <(jq -r '[.hooks | to_entries[] | .value[]? | .hooks[]? | select(.type == "command") | select((.command | type) != "string")] | length' "$file")
    while read -r command; do
      [ -n "$command" ] || continue
      while read -r token; do
        [ -n "$token" ] || continue
        target="$plugin/${token#\$\{CLAUDE_PLUGIN_ROOT\}/}"
        if [ ! -f "$target" ]; then
          fail hooks-json "$file" "command references $token, missing at $target"
        elif [ ! -x "$target" ]; then
          warn hooks-json "$target" "not executable"
        fi
      done < <(printf '%s\n' "$command" | grep -oE '\$\{CLAUDE_PLUGIN_ROOT\}/[^"'"'"' ]+' || true)
    done < <(jq -r '.hooks | to_entries[] | .value[]? | .hooks[]? | select(.type == "command") | select((.command | type) == "string") | .command' "$file")
  done
  finish hooks-json "$before" "$items"
}

check_shellcheck() {
  local before=$fails items=0 file output
  while read -r file; do
    [ -f "$file" ] || continue
    items=$((items + 1))
    if ! output=$(shellcheck -S warning "$file" 2>&1); then
      fail shellcheck "$file" "shellcheck reported findings"
      printf '%s\n' "$output"
    fi
  done < <({ find plugins scripts -name '*.sh' -type f; find scripts/hooks -type f 2>/dev/null; } | sort -u)
  finish shellcheck "$before" "$items"
}

check_tracked_junk() {
  local before=$fails items=0 file
  items=$(git ls-files | wc -l)
  while read -r file; do
    if [ -n "$file" ]; then fail tracked-junk "$file" "build or editor junk must not be tracked"; fi
  done < <(git ls-files | grep -E '__pycache__/|\.pyc$|\.DS_Store$' || true)
  finish tracked-junk "$before" "$items"
}

# The frontmatter checks live in Python because bash cannot parse YAML block scalars.
# Their output follows the same contract, so it is counted rather than re-formatted.
run_frontmatter() {
  local out ok_n fail_n fail_ids
  out=$(python3 scripts/check-frontmatter.py "$@" 2>&1) || true
  printf '%s\n' "$out"
  ok_n=$(printf '%s\n' "$out" | awk '$1 == "ok" { n++ } END { print n + 0 }')
  fail_n=$(printf '%s\n' "$out" | awk '$1 == "FAIL" { n++ } END { print n + 0 }')
  fail_ids=$(printf '%s\n' "$out" | awk '$1 == "FAIL" { print $2 }' | sort -u | awk 'END { print NR + 0 }')
  checks=$((checks + ok_n + fail_ids))
  fails=$((fails + fail_n))
}

BASH_CHECKS=(plugin-manifest plugin-json marketplace-sync readme-table dependencies hooks-json shellcheck tracked-junk)
PYTHON_CHECKS=(frontmatter-parse frontmatter-keys description skill-name references)

ONLY="${1:-}"
if [ -n "$ONLY" ] && ! in_list "$ONLY" "${BASH_CHECKS[@]}" "${PYTHON_CHECKS[@]}"; then
  printf 'unknown check id: %s\n' "$ONLY" >&2
  printf 'known ids: %s %s\n' "${BASH_CHECKS[*]}" "${PYTHON_CHECKS[*]}" >&2
  exit 2
fi

wanted() { [ -z "$ONLY" ] || [ "$ONLY" = "$1" ]; }

if wanted plugin-manifest; then check_plugin_manifest; fi
if wanted plugin-json; then check_plugin_json; fi
if wanted marketplace-sync; then check_marketplace_sync; fi
if wanted readme-table; then check_readme_table; fi
if wanted dependencies; then check_dependencies; fi
if [ -z "$ONLY" ]; then
  run_frontmatter
elif in_list "$ONLY" "${PYTHON_CHECKS[@]}"; then
  run_frontmatter "$ONLY"
fi
if wanted hooks-json; then check_hooks_json; fi
if wanted shellcheck; then check_shellcheck; fi
if wanted tracked-junk; then check_tracked_junk; fi

printf '%d checks, %d failures\n' "$checks" "$fails"
[ "$fails" -eq 0 ]
