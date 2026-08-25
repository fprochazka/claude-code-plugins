#!/usr/bin/env bash
#
# GitLab MR Full State Fetcher
#
# Fetches comprehensive merge request information including:
# - MR details (description, link, author, etc.)
# - All comments and notes (split by resolved/unresolved, human/bot)
# - Latest pipeline state: jobs, every job trace, lint, test report, downstream pipelines
#

set -euo pipefail

MAX_RETRIES=5
INITIAL_RETRY_DELAY=1

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
# Setup
# ==============================================================================

setup_output_directory() {
    local mr_id="$1"
    OUTPUT_DIR="${TMPDIR:-/tmp}/glab-state-${mr_id}-$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$OUTPUT_DIR"

    MR_INFO_FILE="$OUTPUT_DIR/mr-info.txt"
    PIPELINE_SUMMARY_FILE="$OUTPUT_DIR/full-pipeline-summary.txt"
    PIPELINE_DUMP_DIR="$OUTPUT_DIR/pipeline"
}

# ==============================================================================
# MR Information
# ==============================================================================

fetch_mr_info() {
    # Check if we're in a git repository
    git rev-parse --git-dir &>/dev/null || die "Not in a git repository. Please run from within a GitLab repository."

    # Fetch MR data (stderr captured separately to avoid corrupting JSON output)
    local mr_json mr_stderr_file
    mr_stderr_file=$(mktemp)
    if ! mr_json=$(glab mr view --output=json 2>"$mr_stderr_file"); then
        local mr_err
        mr_err=$(cat "$mr_stderr_file")
        rm -f "$mr_stderr_file"
        if [[ "$mr_err" == *"no open merge request"* ]] || [[ "$mr_err" == *"could not find"* ]]; then
            echo "Error: No open merge request found for the current branch" >&2
            echo "" >&2
            echo "Make sure you:" >&2
            echo "  1. Are on a branch that has an open MR" >&2
            echo "  2. Have pushed the branch to GitLab" >&2
            echo "  3. Have created a merge request for this branch" >&2
            echo "" >&2
            echo "Current branch: $(git branch --show-current 2>/dev/null || echo 'unknown')" >&2
            exit 1
        elif [[ "$mr_err" == *"authentication"* ]] || [[ "$mr_err" == *"401"* ]]; then
            die "GitLab authentication failed. Please run 'glab auth login' to authenticate."
        else
            die "Failed to fetch MR data: $mr_err"
        fi
    fi
    rm -f "$mr_stderr_file"

    # Extract fields
    MR_ID=$(echo "$mr_json" | jq -r '.iid')
    PROJECT_ID=$(echo "$mr_json" | jq -r '.project_id')
    MR_TITLE=$(echo "$mr_json" | jq -r '.title')
    MR_AUTHOR=$(echo "$mr_json" | jq -r '.author.name')
    MR_STATE=$(echo "$mr_json" | jq -r '.state')
    MR_URL=$(echo "$mr_json" | jq -r '.web_url')
    MR_TARGET_BRANCH=$(echo "$mr_json" | jq -r '.target_branch')
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

fetch_comments() {
    local mr_url="$1"
    local output_dir="$2"

    local dump_output
    dump_output=$(glab-discussion read --dump --mr-url "$mr_url" 2>&1)
    local exit_code=$?

    if [ $exit_code -ne 0 ]; then
        echo "ERROR: glab-discussion read failed:"
        echo "$dump_output"
        return 1
    fi

    # Extract the dump directory path from the first line of output
    # Format: "Discussions: /tmp/glab-discussion/<host>/mr-<iid>/"
    local discussions_dir
    discussions_dir=$(echo "$dump_output" | head -1 | sed 's/^Discussions: //' | sed 's/\/$//')

    if [ ! -d "$discussions_dir" ]; then
        echo "WARNING: No discussions directory found at: $discussions_dir"
        echo "$dump_output"
        return 0
    fi

    # Write the full output to the output dir for reference
    echo "$dump_output" > "$output_dir/comments-summary.txt"
    echo "$discussions_dir" > "$output_dir/discussions-dir.txt"

    DISCUSSIONS_DIR="$discussions_dir"
}

# ==============================================================================
# Pipeline & Jobs
# ==============================================================================

fetch_pipeline_info() {
    local pipeline_json
    pipeline_json=$(echo "$MR_JSON" | jq '.head_pipeline // null')

    if [[ "$pipeline_json" == "null" ]]; then
        PIPELINE_STATUS=""
        return
    fi

    PIPELINE_STATUS=$(echo "$pipeline_json" | jq -r '.status')
    local pipeline_sha
    pipeline_sha=$(echo "$pipeline_json" | jq -r '.sha')

    # glab-pipeline owns the pipeline dump: jobs, every job trace, and the conditional
    # lint / test-report / downstream fetches that a failed pipeline needs.
    if ! glab-pipeline inspect --mr-url "$MR_URL" --output-dir "$PIPELINE_DUMP_DIR" > "$PIPELINE_SUMMARY_FILE" 2>&1; then
        echo "Warning: glab-pipeline inspect failed, see $PIPELINE_SUMMARY_FILE" >&2
        return
    fi

    PIPELINE_SUMMARY_JSON="$PIPELINE_DUMP_DIR/summary.json"

    fetch_external_statuses "$pipeline_sha"
}

# External commit statuses (for example SonarQube) live outside the pipeline, so glab-pipeline
# does not report them. Job names from the dump filter out the statuses that pipeline jobs post.
fetch_external_statuses() {
    local pipeline_sha="$1"

    EXTERNAL_STATUSES="[]"
    [[ -z "$pipeline_sha" || "$pipeline_sha" == "null" ]] && return 0

    local commit_statuses
    commit_statuses=$(glab_api_paginated_with_retry "projects/$PROJECT_ID/repository/commits/$pipeline_sha/statuses?per_page=100") || return 0

    local job_names="[]"
    [[ -f "$PIPELINE_DUMP_DIR/jobs.json" ]] && job_names=$(jq '[.[].name]' "$PIPELINE_DUMP_DIR/jobs.json")

    EXTERNAL_STATUSES=$(echo "$commit_statuses" | jq --argjson jobs "$job_names" '[.[] | select(.name as $n | $jobs | index($n) | not)]')

    local external_count
    external_count=$(echo "$EXTERNAL_STATUSES" | jq 'length')
    (( external_count == 0 )) && return 0

    {
        echo
        echo "EXTERNAL COMMIT STATUSES ($external_count)"
        echo "=========================================="
        echo

        while IFS= read -r ext; do
            echo "Status: $(echo "$ext" | jq -r '.name // "Unknown"')"
            echo "  Result: $(echo "$ext" | jq -r '.status // "unknown"')"
            local ext_desc ext_url
            ext_desc=$(echo "$ext" | jq -r '.description // ""')
            ext_url=$(echo "$ext" | jq -r '.target_url // ""')
            [[ -n "$ext_desc" && "$ext_desc" != "null" ]] && echo "  Description: $ext_desc"
            [[ -n "$ext_url" && "$ext_url" != "null" ]] && echo "  URL: $ext_url"
            echo
        done < <(echo "$EXTERNAL_STATUSES" | jq -c '.[]')
    } >> "$PIPELINE_SUMMARY_FILE"
}

# ==============================================================================
# Summary
# ==============================================================================

print_summary() {
    local show_comments="${1:-true}"
    local show_pipeline="${2:-true}"

    echo
    echo "MR Information:"
    echo "  Title: $MR_TITLE"
    echo "  Author: $MR_AUTHOR"
    echo "  State: $MR_STATE"
    echo "  Target Branch: $MR_TARGET_BRANCH"
    echo "  URL: $MR_URL"
    echo
    echo "Files Created:"
    echo "  MR Info:                   $MR_INFO_FILE"

    if [[ "$show_comments" == true ]]; then
        local discussions_dir=""
        if [[ -f "$OUTPUT_DIR/discussions-dir.txt" ]]; then
            discussions_dir=$(cat "$OUTPUT_DIR/discussions-dir.txt")
        fi
        if [[ -n "$discussions_dir" && -d "$discussions_dir" ]]; then
            local thread_count
            thread_count=$(find "$discussions_dir" -maxdepth 1 -name '*.txt' | wc -l)
            echo "  Discussions:               $discussions_dir/*.txt ($thread_count threads)"
        fi
    fi

    if [[ "$show_pipeline" == true ]]; then
        [[ -n "${PIPELINE_STATUS:-}" ]] && echo "  Pipeline summary:          $PIPELINE_SUMMARY_FILE (status: $PIPELINE_STATUS)"
        [[ -d "${PIPELINE_DUMP_DIR:-}" ]] && echo "  Pipeline dump:             $PIPELINE_DUMP_DIR/ (summary.json, pipeline.json, jobs.json, job-logs/)"

        # Show failed jobs
        if [[ -f "${PIPELINE_SUMMARY_JSON:-}" ]]; then
            local failed_count
            failed_count=$(jq '.failed_jobs | length' "$PIPELINE_SUMMARY_JSON")

            if (( failed_count > 0 )); then
                echo
                echo "Failed Jobs ($failed_count):"
                jq -r '.failed_jobs[] | "  \(.name) [\(.stage)] \(.failure_reason // "unknown"): \(.log // "no log")"' "$PIPELINE_SUMMARY_JSON"
            fi
        fi

        # Show failed external commit statuses
        if [[ -n "${EXTERNAL_STATUSES:-}" ]]; then
            local failed_external=$(echo "$EXTERNAL_STATUSES" | jq -c '[.[] | select(.status == "failed")]')
            local failed_ext_count=$(echo "$failed_external" | jq 'length')

            if (( failed_ext_count > 0 )); then
                echo
                echo "Failed External Statuses ($failed_ext_count):"
                while IFS= read -r ext; do
                    local ext_name=$(echo "$ext" | jq -r '.name')
                    local ext_desc=$(echo "$ext" | jq -r '.description // ""')
                    local ext_url=$(echo "$ext" | jq -r '.target_url // ""')
                    echo -n "  $ext_name"
                    [[ -n "$ext_desc" && "$ext_desc" != "null" ]] && echo -n " ($ext_desc)"
                    echo
                    [[ -n "$ext_url" && "$ext_url" != "null" ]] && echo "    URL: $ext_url"
                done < <(echo "$failed_external" | jq -c '.[]')
            fi
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

    if ! command -v glab-discussion &>/dev/null; then
        echo ""
        echo "ERROR: glab-discussion is not installed!"
        echo ""
        echo "Please ask the user to install it:"
        echo "  uv tool install glab-discussion"
        echo ""
        echo "More info: https://github.com/fprochazka/glab-discussion"
        exit 1
    fi

    if ! command -v glab-pipeline &>/dev/null; then
        echo ""
        echo "ERROR: glab-pipeline is not installed!"
        echo ""
        echo "Please ask the user to install it:"
        echo "  uv tool install glab-pipeline"
        echo ""
        echo "More info: https://github.com/fprochazka/glab-pipeline"
        exit 1
    fi

    local fetch_comments_flag=false
    local fetch_pipeline_flag=false

    # Parse arguments
    if [[ $# -eq 0 ]] || [[ "$1" == "--all" ]]; then
        fetch_comments_flag=true
        fetch_pipeline_flag=true
    else
        while [[ $# -gt 0 ]]; do
            case "$1" in
                --comments) fetch_comments_flag=true ;;
                --pipeline) fetch_pipeline_flag=true ;;
                --all) fetch_comments_flag=true; fetch_pipeline_flag=true ;;
                *) die "Unknown option: $1 (use --comments, --pipeline, or --all)" ;;
            esac
            shift
        done
    fi

    fetch_mr_info

    if [[ "$fetch_comments_flag" == true ]]; then
        fetch_comments "$MR_URL" "$OUTPUT_DIR"
    fi

    if [[ "$fetch_pipeline_flag" == true ]]; then
        fetch_pipeline_info
    fi

    print_summary "$fetch_comments_flag" "$fetch_pipeline_flag"
}

main "$@"
