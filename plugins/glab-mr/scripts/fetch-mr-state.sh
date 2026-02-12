#!/usr/bin/env bash
#
# GitLab MR Full State Fetcher
#
# Fetches comprehensive merge request information including:
# - MR details (description, link, author, etc.)
# - All comments and notes (split by resolved/unresolved, human/bot)
# - Latest pipeline status and job details
# - Job logs (fetched in parallel with retry)
#

set -euo pipefail

MAX_RETRIES=5
INITIAL_RETRY_DELAY=1
MAX_PARALLEL_JOBS=10

# ==============================================================================
# Utility Functions
# ==============================================================================

die() {
    echo "Error: $1" >&2
    exit 1
}

fix_paginated_json() {
    # Merge multiple JSON arrays from paginated output into one
    jq -s 'add // []'
}

sanitize_filename() {
    echo "$1" | sed 's/[^a-zA-Z0-9._-]/_/g'
}

glab_api_with_retry() {
    local url="$1"
    local output_file="$2"
    local retry=0
    local delay=$INITIAL_RETRY_DELAY

    while (( retry < MAX_RETRIES )); do
        if glab api "$url" > "$output_file" 2>/dev/null; then
            return 0
        fi
        retry=$((retry + 1))
        if (( retry < MAX_RETRIES )); then
            local jitter=$(( RANDOM % (delay / 2 + 1) ))
            sleep $(( delay + jitter ))
            delay=$(( delay * 2 ))
        fi
    done

    echo "ERROR: Failed to fetch $url after $MAX_RETRIES retries" > "$output_file"
    return 1
}

# Fetches a paginated API endpoint with retry, merges arrays, and validates JSON.
# Outputs the merged JSON array to stdout. Returns 1 on failure.
glab_api_paginated_with_retry() {
    local url="$1"
    local retry=0
    local delay=$INITIAL_RETRY_DELAY
    local result

    while (( retry < MAX_RETRIES )); do
        local raw
        if raw=$(glab api "$url" --paginate 2>/dev/null); then
            if result=$(echo "$raw" | fix_paginated_json) && echo "$result" | jq empty 2>/dev/null; then
                echo "$result"
                return 0
            fi
        fi
        retry=$((retry + 1))
        if (( retry < MAX_RETRIES )); then
            local jitter=$(( RANDOM % (delay / 2 + 1) ))
            sleep $(( delay + jitter ))
            delay=$(( delay * 2 ))
        fi
    done

    echo "[]"
    return 1
}

# ==============================================================================
# User Cache (bot detection)
# ==============================================================================

# Extracts GitLab hostname from a web URL (e.g. https://gitlab.example.com/foo -> gitlab.example.com)
extract_hostname() {
    echo "$1" | sed -E 's|https?://([^/]*).*|\1|'
}

# Fetches user JSON, caching to ~/.cache/gitlab/<hostname>/user_<id>.json
fetch_user_cached() {
    local user_id="$1"
    local hostname="$2"
    local cache_dir="$HOME/.cache/gitlab/$hostname"
    local cache_file="$cache_dir/user_${user_id}.json"

    if [[ -f "$cache_file" ]]; then
        cat "$cache_file"
        return 0
    fi

    mkdir -p "$cache_dir"
    local temp_file
    temp_file=$(mktemp)

    if glab_api_with_retry "users/$user_id" "$temp_file"; then
        if jq empty < "$temp_file" 2>/dev/null; then
            mv "$temp_file" "$cache_file"
            cat "$cache_file"
            return 0
        fi
    fi

    rm -f "$temp_file"
    echo '{}'
    return 1
}

# Builds a JSON object mapping author IDs to bot status: {"870": false, "867": true}
build_bot_author_map() {
    local comments_json="$1"
    local hostname="$2"
    local bot_map="{}"

    local author_ids
    author_ids=$(echo "$comments_json" | jq -r '[.[].author.id] | unique | .[]')

    for user_id in $author_ids; do
        local user_json
        user_json=$(fetch_user_cached "$user_id" "$hostname")
        local is_bot
        is_bot=$(echo "$user_json" | jq -r '.bot // false')
        bot_map=$(echo "$bot_map" | jq --arg id "$user_id" --argjson bot "$is_bot" '. + {($id): $bot}')
    done

    echo "$bot_map"
}

# ==============================================================================
# Setup
# ==============================================================================

setup_output_directory() {
    local mr_id="$1"
    OUTPUT_DIR="${TMPDIR:-/tmp}/glab-mr-${mr_id}-$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$OUTPUT_DIR"

    MR_INFO_FILE="$OUTPUT_DIR/mr-info.txt"
    COMMENTS_RESOLVED_FILE="$OUTPUT_DIR/comments-resolved.txt"
    COMMENTS_UNRESOLVED_FILE="$OUTPUT_DIR/comments-unresolved.txt"
    COMMENTS_BOT_RESOLVED_FILE="$OUTPUT_DIR/comments-bot-resolved.txt"
    COMMENTS_BOT_UNRESOLVED_FILE="$OUTPUT_DIR/comments-bot-unresolved.txt"
    PIPELINE_SUMMARY_FILE="$OUTPUT_DIR/full-pipeline-summary.txt"
    JOBS_DIR="$OUTPUT_DIR/job-logs"
    mkdir -p "$JOBS_DIR"
}

# ==============================================================================
# MR Information
# ==============================================================================

fetch_mr_info() {
    # Check if we're in a git repository
    git rev-parse --git-dir &>/dev/null || die "Not in a git repository. Please run from within a GitLab repository."

    # Fetch MR data
    local mr_json
    if ! mr_json=$(glab mr view --output=json 2>&1); then
        if [[ "$mr_json" == *"no open merge request"* ]] || [[ "$mr_json" == *"could not find"* ]]; then
            echo "Error: No open merge request found for the current branch" >&2
            echo "" >&2
            echo "Make sure you:" >&2
            echo "  1. Are on a branch that has an open MR" >&2
            echo "  2. Have pushed the branch to GitLab" >&2
            echo "  3. Have created a merge request for this branch" >&2
            echo "" >&2
            echo "Current branch: $(git branch --show-current 2>/dev/null || echo 'unknown')" >&2
            exit 1
        elif [[ "$mr_json" == *"authentication"* ]] || [[ "$mr_json" == *"401"* ]]; then
            die "GitLab authentication failed. Please run 'glab auth login' to authenticate."
        else
            die "Failed to fetch MR data: $mr_json"
        fi
    fi

    # Extract fields
    MR_ID=$(echo "$mr_json" | jq -r '.iid')
    PROJECT_ID=$(echo "$mr_json" | jq -r '.project_id')
    MR_TITLE=$(echo "$mr_json" | jq -r '.title')
    MR_AUTHOR=$(echo "$mr_json" | jq -r '.author.name')
    MR_STATE=$(echo "$mr_json" | jq -r '.state')
    MR_URL=$(echo "$mr_json" | jq -r '.web_url')
    MR_JSON="$mr_json"

    setup_output_directory "$MR_ID"

    # Write MR info
    local mr_view
    mr_view=$(glab mr view "$MR_ID" 2>/dev/null || echo "Could not fetch text view")

    {
        echo "MERGE REQUEST INFORMATION"
        echo "========================="
        echo
        echo "$mr_view"
        echo
        echo "RAW JSON DATA"
        echo "============="
        echo
        echo "$mr_json" | jq .
    } > "$MR_INFO_FILE"
}

# ==============================================================================
# Comments
# ==============================================================================

write_comment() {
    local idx="$1"
    local comment_json="$2"

    local author=$(echo "$comment_json" | jq -r '.author.name // "Unknown"')
    local created_at=$(echo "$comment_json" | jq -r '.created_at // "Unknown"')
    local body=$(echo "$comment_json" | jq -r '.body // ""')
    local note_type=$(echo "$comment_json" | jq -r '.type // ""')
    local system=$(echo "$comment_json" | jq -r '.system // false')

    echo "[$idx] $author - $created_at"
    [[ "$system" == "true" ]] && echo "[SYSTEM NOTE]"
    [[ -n "$note_type" && "$note_type" != "null" ]] && echo "Type: $note_type"

    # Code position
    local has_position=$(echo "$comment_json" | jq -r '.position // null')
    if [[ "$has_position" != "null" ]]; then
        local commit=$(echo "$comment_json" | jq -r '.position.head_sha // ""' | cut -c1-8)
        local file_path=$(echo "$comment_json" | jq -r '.position.new_path // .position.old_path // ""')
        local line_num=$(echo "$comment_json" | jq -r '.position.new_line // .position.old_line // ""')
        if [[ -n "$commit" && -n "$file_path" ]]; then
            echo -n "Code: $commit $file_path"
            [[ -n "$line_num" && "$line_num" != "null" ]] && echo -n ":$line_num"
            echo
        fi
    fi

    echo "---"
    echo "$body"
    echo
}

write_comments_file() {
    local title="$1"
    local output_file="$2"
    local comments_json="$3"
    local count
    count=$(echo "$comments_json" | jq 'length')

    {
        echo "$title (Total: $count)"
        echo "=========================================="
        echo
        local idx=1
        while IFS= read -r comment; do
            write_comment "$idx" "$comment"
            idx=$((idx + 1))
        done < <(echo "$comments_json" | jq -c '.[]')
    } > "$output_file"

    echo "$count"
}

fetch_comments() {
    local comments_json
    if ! comments_json=$(glab_api_paginated_with_retry "projects/$PROJECT_ID/merge_requests/$MR_ID/notes?per_page=100"); then
        echo "Warning: Could not fetch comments after $MAX_RETRIES retries" >&2
        return
    fi

    # Build bot author map
    local hostname
    hostname=$(extract_hostname "$MR_URL")
    local bot_map
    bot_map=$(build_bot_author_map "$comments_json" "$hostname")

    # Split by bot/human, then by resolved/unresolved
    local human_resolved human_unresolved bot_resolved bot_unresolved
    human_resolved=$(echo "$comments_json" | jq --argjson bots "$bot_map" '[.[] | select(($bots[(.author.id | tostring)] // false) == false) | select(.resolvable == false or .resolved == true)]')
    human_unresolved=$(echo "$comments_json" | jq --argjson bots "$bot_map" '[.[] | select(($bots[(.author.id | tostring)] // false) == false) | select(.resolvable == true and .resolved == false)]')
    bot_resolved=$(echo "$comments_json" | jq --argjson bots "$bot_map" '[.[] | select(($bots[(.author.id | tostring)] // false) == true) | select(.resolvable == false or .resolved == true)]')
    bot_unresolved=$(echo "$comments_json" | jq --argjson bots "$bot_map" '[.[] | select(($bots[(.author.id | tostring)] // false) == true) | select(.resolvable == true and .resolved == false)]')

    RESOLVED_COUNT=$(write_comments_file "RESOLVED COMMENTS" "$COMMENTS_RESOLVED_FILE" "$human_resolved")
    UNRESOLVED_COUNT=$(write_comments_file "UNRESOLVED COMMENTS" "$COMMENTS_UNRESOLVED_FILE" "$human_unresolved")
    BOT_RESOLVED_COUNT=$(write_comments_file "BOT RESOLVED COMMENTS" "$COMMENTS_BOT_RESOLVED_FILE" "$bot_resolved")
    BOT_UNRESOLVED_COUNT=$(write_comments_file "BOT UNRESOLVED COMMENTS" "$COMMENTS_BOT_UNRESOLVED_FILE" "$bot_unresolved")
}

# ==============================================================================
# Pipeline & Jobs
# ==============================================================================

fetch_pipeline_info() {
    local pipeline_json=$(echo "$MR_JSON" | jq '.head_pipeline // null')

    if [[ "$pipeline_json" == "null" ]]; then
        PIPELINE_STATUS=""
        return
    fi

    local pipeline_id=$(echo "$pipeline_json" | jq -r '.id')
    PIPELINE_STATUS=$(echo "$pipeline_json" | jq -r '.status')

    local jobs_json
    if ! jobs_json=$(glab_api_paginated_with_retry "projects/$PROJECT_ID/pipelines/$pipeline_id/jobs?per_page=100"); then
        echo "Warning: Could not fetch jobs after $MAX_RETRIES retries" >&2
        return
    fi

    JOBS_JSON="$jobs_json"
    local jobs_count=$(echo "$jobs_json" | jq 'length')

    # Write pipeline summary
    {
        echo "PIPELINE SUMMARY"
        echo "================"
        echo
        echo "Pipeline ID: $(echo "$pipeline_json" | jq -r '.id')"
        echo "Status: $(echo "$pipeline_json" | jq -r '.status')"
        echo "Ref: $(echo "$pipeline_json" | jq -r '.ref')"
        echo "Created: $(echo "$pipeline_json" | jq -r '.created_at')"
        echo "Web URL: $(echo "$pipeline_json" | jq -r '.web_url')"
        echo
        echo "JOBS ($jobs_count total)"
        echo "========================"
        echo

        while IFS= read -r job; do
            local job_id=$(echo "$job" | jq -r '.id')
            local job_name=$(echo "$job" | jq -r '.name')
            local job_status=$(echo "$job" | jq -r '.status')
            local stage=$(echo "$job" | jq -r '.stage')
            local safe_name=$(sanitize_filename "$job_name")

            echo "Job: $job_name"
            echo "  ID: $job_id"
            echo "  Status: $job_status"
            echo "  Stage: $stage"
            echo "  Web URL: $(echo "$job" | jq -r '.web_url')"
            echo "  Log File: $JOBS_DIR/${safe_name}-${job_id}.log"
            echo
        done < <(echo "$jobs_json" | jq -c '.[]')
    } > "$PIPELINE_SUMMARY_FILE"
}

fetch_single_job_log() {
    local job_json="$1"
    local job_id=$(echo "$job_json" | jq -r '.id')
    local job_name=$(echo "$job_json" | jq -r '.name')
    local job_status=$(echo "$job_json" | jq -r '.status')
    local stage=$(echo "$job_json" | jq -r '.stage')
    local safe_name=$(sanitize_filename "$job_name")
    local log_file="$JOBS_DIR/${safe_name}-${job_id}.log"

    local temp_trace=$(mktemp)
    glab_api_with_retry "projects/$PROJECT_ID/jobs/$job_id/trace" "$temp_trace"

    {
        echo "Job: $job_name"
        echo "ID: $job_id"
        echo "Status: $job_status"
        echo "Stage: $stage"
        echo "================"
        echo
        cat "$temp_trace"
    } > "$log_file"

    rm -f "$temp_trace"
}

fetch_job_logs() {
    [[ -z "${JOBS_JSON:-}" ]] && return

    local jobs_count=$(echo "$JOBS_JSON" | jq 'length')
    (( jobs_count == 0 )) && return

    export PROJECT_ID JOBS_DIR MAX_RETRIES INITIAL_RETRY_DELAY
    export -f glab_api_with_retry sanitize_filename fetch_single_job_log

    local running=0
    while IFS= read -r job; do
        while (( running >= MAX_PARALLEL_JOBS )); do
            wait -n 2>/dev/null || true
            running=$((running - 1))
        done
        fetch_single_job_log "$job" &
        running=$((running + 1))
    done < <(echo "$JOBS_JSON" | jq -c '.[]')

    wait
}

# ==============================================================================
# Summary
# ==============================================================================

print_summary() {
    echo
    echo "MR Information:"
    echo "  Title: $MR_TITLE"
    echo "  Author: $MR_AUTHOR"
    echo "  State: $MR_STATE"
    echo "  URL: $MR_URL"
    echo
    echo "Files Created:"
    echo "  MR Info:                   $MR_INFO_FILE"
    echo "  Comments (resolved):       $COMMENTS_RESOLVED_FILE ($RESOLVED_COUNT comments)"
    echo "  Comments (unresolved):     $COMMENTS_UNRESOLVED_FILE ($UNRESOLVED_COUNT comments)"
    echo "  Bot comments (resolved):   $COMMENTS_BOT_RESOLVED_FILE ($BOT_RESOLVED_COUNT comments)"
    echo "  Bot comments (unresolved): $COMMENTS_BOT_UNRESOLVED_FILE ($BOT_UNRESOLVED_COUNT comments)"

    [[ -n "${PIPELINE_STATUS:-}" ]] && echo "  Pipeline:              $PIPELINE_SUMMARY_FILE (status: $PIPELINE_STATUS)"

    # Show failed jobs
    if [[ -n "${JOBS_JSON:-}" ]]; then
        local failed_jobs=$(echo "$JOBS_JSON" | jq -c '[.[] | select(.status == "failed")]')
        local failed_count=$(echo "$failed_jobs" | jq 'length')

        if (( failed_count > 0 )); then
            echo
            echo "Failed Jobs ($failed_count):"
            while IFS= read -r job; do
                local job_id=$(echo "$job" | jq -r '.id')
                local job_name=$(echo "$job" | jq -r '.name')
                local safe_name=$(sanitize_filename "$job_name")
                echo "  $job_name: $JOBS_DIR/${safe_name}-${job_id}.log"
            done < <(echo "$failed_jobs" | jq -c '.[]')
        fi
    fi

    echo
    echo "All files in: $OUTPUT_DIR"
}

# ==============================================================================
# Main
# ==============================================================================

main() {
    command -v glab &>/dev/null || die "glab CLI is not installed"
    command -v jq &>/dev/null || die "jq is not installed"

    RESOLVED_COUNT=0
    UNRESOLVED_COUNT=0
    BOT_RESOLVED_COUNT=0
    BOT_UNRESOLVED_COUNT=0

    fetch_mr_info
    fetch_comments
    fetch_pipeline_info
    fetch_job_logs
    print_summary
}

main "$@"
