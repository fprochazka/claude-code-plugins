# glab-mr

GitLab MR tools for Claude Code - fix failed CI, resolve comments, and more.

## Commands

### `/glab-mr:fix-all`

Fetches comprehensive MR state (comments + pipeline) and helps fix all issues:

1. **Failed CI Jobs** - Analyzes job logs and fixes code issues
2. **Unresolved Comments** - Reviews and addresses discussion threads
3. **Resolved Comments Verification** - Checks for missed actionable feedback

### `/glab-mr:comments`

Fetches only MR comments, analyzes them, and proposes what to do:

1. **Unresolved Comments** - Reviews discussion threads and proposes actions
2. **Resolved Comments Verification** - Checks for missed actionable feedback

### `/glab-mr:pipeline`

Fetches only pipeline status and job logs, triages failures and proposes fixes.

## Requirements

- Claude Code **2.1.0 or newer** (see [Known Issue](#known-issue) below)
- [`glab` CLI](https://docs.gitlab.com/cli/) installed and authenticated
- `jq` for JSON processing

## How it works

The plugin includes an inline bash script that:

1. Auto-detects the MR from your current git branch
2. Fetches MR info via `glab mr view`
3. Fetches all discussions via the Discussions API, filters out system-only threads
4. Groups comments by discussion thread with replies indented, sorted by creation time
5. Includes `Discussion:` and `Note:` IDs so the AI can reply/resolve without extra API lookups
6. Marks bot authors with `[BOT]` label (via cached user lookups)
7. Splits into resolved/unresolved files
8. Fetches pipeline status, job details, and logs in parallel with retry

All data is saved to `/tmp/glab-mr-<id>-<timestamp>/` with:
- `mr-info.txt` - Full MR details
- `comments-resolved.txt` - Resolved comments (bot authors marked with `[BOT]`)
- `comments-unresolved.txt` - Unresolved comments
- `full-pipeline-summary.txt` - Pipeline status and all jobs
- `job-logs/` - Individual log files for each job

User data (for bot detection) is cached at `~/.cache/gitlab/<hostname>/user_<id>.json` to avoid redundant API calls across runs.

## Installation

```bash
claude plugin install glab-mr@fprochazka-claude-code-plugins
```

## Known Issue

This plugin requires Claude Code 2.1.0+ due to a [bug in older versions](https://github.com/anthropics/claude-code/issues/9354) where `${CLAUDE_PLUGIN_ROOT}` was not properly substituted in plugin `allowed-tools` frontmatter.

If you see `Error: Bash command permission check failed`, upgrade Claude Code to 2.1.0 or newer.
