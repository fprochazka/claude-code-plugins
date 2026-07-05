# glab-mr

GitLab MR tools for Claude Code - fix failed CI, resolve comments, and more.

## Commands

### `/glab-mr:babysit`

Watches one or more MRs and drives each toward mergeable, one pass at a time. Each pass, for **every MR in the set**:

1. **Keeps it rebased** onto the target branch (force-with-lease only), resolving mechanical conflicts itself
2. **Fixes failing CI** — triages via `glab-pipeline`, fixes genuine build/test/lint failures (capped at 2 attempts per failure), retries flaky ones while complaining loudly
3. **Resolves review comments** that don't need a product decision — critically evaluated into apply / dismiss / judgment / skip
4. **Pushes once and verifies the push landed** on the remote before reporting it

The MR set is **only** what you name or what the session worked on — it never goes hunting for unrelated MRs. Cross-repo changes (e.g. a service repo + a data/ETL pipelines repo) are babysat together; name both in the loop prompt.

Run `/glab-mr:babysit` once to load the procedure, then drive the ~2-minute cadence with a lightweight native-loop prompt naming the MRs (re-invoking the full command each cycle would needlessly re-inject the whole spec):

```
/loop 2m re-check MR !123 and !456 and run the next babysit pass
```

Each pass returns immediately — no in-pass sleeping. Across passes it naturally waits for the pipeline and gives an automated reviewer time to weigh in. It stops only when **every** MR is green, quiet for a couple of minutes, and has all actionable threads replied to and resolved — then it hands back the judgment calls it deferred. Genuine product/design decisions are collected and surfaced without halting early.

Within the loop the agent is **pre-authorized** to rebase, force-with-lease, push, retry CI, and reply/resolve without stopping to ask — that's the point of an unattended loop. If your permission setup makes Claude Code prompt for those git operations, allowlist them so the loop runs uninterrupted:

```jsonc
// .claude/settings.json → "permissions": { "allow": [ ... ] }
"Bash(git push:*)", "Bash(git rebase:*)", "Bash(git fetch:*)", "Bash(glab ci retry:*)"
```

### `/glab-mr:fix-all`

Fetches comprehensive MR state (comments + pipeline) and helps fix all issues:

1. **Failed CI Jobs** - Analyzes job logs and fixes code issues
2. **Unresolved Comments** - Reviews and addresses discussion threads
3. **Resolved Comments Verification** - Checks for missed actionable feedback

### `/glab-mr:overview`

Fetches comprehensive MR state and presents a clear status overview without taking any action.

### `/glab-mr:comments`

Fetches only MR comments, analyzes them, and proposes what to do:

1. **Unresolved Comments** - Reviews discussion threads and proposes actions
2. **Resolved Comments Verification** - Checks for missed actionable feedback

### `/glab-mr:pipeline`

Fetches only pipeline status and job logs, triages failures and proposes fixes.

## Requirements

- Claude Code **2.1.0 or newer** (see [Known Issue](#known-issue) below)
- [`glab` CLI](https://docs.gitlab.com/cli/) installed and authenticated
- [`glab-discussion`](https://github.com/fprochazka/glab-discussion) for discussion handling (`uv tool install glab-discussion`) — required by the other commands; `/glab-mr:babysit` prefers it but falls back to raw `glab api`
- [`glab-pipeline`](https://github.com/fprochazka/glab-pipeline) for CI triage — `/glab-mr:babysit` prefers it but falls back to raw `glab ci` (`uv tool install glab-pipeline`)
- `jq` for JSON processing

## How it works

The plugin includes a bash script that:

1. Auto-detects the MR from your current git branch
2. Fetches MR info via `glab mr view`
3. Delegates discussion fetching to `glab-discussion read --dump` (per-thread files with incremental updates, bot detection, diff note positions)
4. Fetches pipeline status, job details, and logs in parallel with retry

Output:
- `mr-info.txt` - Full MR details (in `/tmp/glab-mr-<id>-<timestamp>/`)
- `/tmp/glab-discussion/<host>/mr-<iid>/*.txt` - One file per discussion thread (managed by `glab-discussion`)
- `full-pipeline-summary.txt` - Pipeline status and all jobs
- `job-logs/` - Individual log files for each job

## Installation

```bash
claude plugin marketplace add fprochazka/claude-code-plugins --scope user
claude plugin install glab-mr@fprochazka-claude-code-plugins --scope user
```

## Known Issue

This plugin requires Claude Code 2.1.0+ due to a [bug in older versions](https://github.com/anthropics/claude-code/issues/9354) where `${CLAUDE_PLUGIN_ROOT}` was not properly substituted in plugin `allowed-tools` frontmatter.

If you see `Error: Bash command permission check failed`, upgrade Claude Code to 2.1.0 or newer.
