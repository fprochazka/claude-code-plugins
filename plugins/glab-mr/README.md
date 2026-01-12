# glab-mr

GitLab MR tools for Claude Code - fix failed CI, resolve comments, and more.

## Commands

### `/glab-mr:fix`

Fetches comprehensive MR state and helps fix issues:

1. **Failed CI Jobs** - Analyzes job logs and fixes code issues
2. **Unresolved Comments** - Reviews and addresses discussion threads
3. **Resolved Comments Verification** - Checks for missed actionable feedback

## Requirements

- Claude Code **2.1.0 or newer** (see [Known Issue](#known-issue) below)
- [`glab` CLI](https://docs.gitlab.com/cli/) installed and authenticated
- `jq` for JSON processing

## How it works

The plugin includes an inline bash script that:

1. Auto-detects the MR from your current git branch
2. Fetches MR info via `glab mr view`
3. Fetches all comments and splits them into resolved/unresolved
4. Fetches pipeline status and job details
5. Fetches job logs in parallel with exponential backoff retry
6. Writes organized output to a temp directory

All data is saved to `/tmp/glab-mr-<id>-<timestamp>/` with:
- `mr-info.txt` - Full MR details
- `comments-resolved.txt` - Resolved threads and non-resolvable comments
- `comments-unresolved.txt` - Active unresolved discussion threads
- `full-pipeline-summary.txt` - Pipeline status and all jobs
- `job-logs/` - Individual log files for each job

## Installation

```bash
claude plugin install glab-mr@fprochazka-claude-code-plugins
```

## Known Issue

This plugin requires Claude Code 2.1.0+ due to a [bug in older versions](https://github.com/anthropics/claude-code/issues/9354) where `${CLAUDE_PLUGIN_ROOT}` was not properly substituted in plugin `allowed-tools` frontmatter.

If you see `Error: Bash command permission check failed`, upgrade Claude Code to 2.1.0 or newer.
