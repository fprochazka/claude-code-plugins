# glab

Claude Code plugin for GitLab through the [glab CLI](https://gitlab.com/gitlab-org/cli). It carries the `glab` skill, the `mr-status` skill, and slash commands that dump the state of a merge request.

## Requirements

- Claude Code **2.1.0 or newer** (see [Known issue](#known-issue))
- `glab` CLI installed, on PATH, and authenticated via `glab auth login`
- `jq` for JSON processing
- [`glab-discussion`](https://github.com/fprochazka/glab-discussion) for discussion handling (`uv tool install glab-discussion`)
- [`glab-pipeline`](https://github.com/fprochazka/glab-pipeline) for pipeline dumps and triage (`uv tool install glab-pipeline`)

The plugin declares `glab-discussion` and `glab-pipeline` as plugin dependencies, so their skills load alongside it. The script fails with an install hint when either CLI is missing.

## Installation

```bash
claude plugin marketplace add fprochazka/glab-discussion --scope user
claude plugin marketplace add fprochazka/glab-pipeline --scope user
claude plugin marketplace add fprochazka/claude-code-plugins --scope user
claude plugin install glab@fprochazka-claude-code-plugins --scope user
```

## Permissions

Add the following to `~/.claude/settings.json` to allow the skill to load and auto-approve read-only commands:

```json
{
  "permissions": {
    "allow": [
      "Skill(glab)"
    ]
  }
}
```

The skill's `allowed-tools` frontmatter auto-allows read-only commands (`mr list`, `mr view`, `mr diff`, `ci status`, `ci get`, `ci trace`, etc.) and `--help` for all subcommands. Write operations (`mr create`, `mr update`, `mr merge`, `mr note`, `ci run`, `ci retry`, etc.) require manual approval.

The `/glab:overview` and `/glab:pipeline` commands carry `Bash(glab-pipeline:*)` in their own `allowed-tools`, so pipeline inspection needs no extra approval.

## Skills

- `glab:glab` — the CLI reference. Merge requests, discussions, pipelines, issues, repositories, releases, variables, schedules, labels, milestones, and the raw API with pagination and GraphQL.
- `glab:mr-status` — reads the real review-and-merge state of one MR or a whole set: draft, rebase distance, pipeline, approvals, size, every AI reviewer's latest verdict, human threads, and what blocks the merge right now. It profiles each AI reviewer from its own threads instead of assuming how a bot behaves, and it reads the newest verdict plus the currently unresolved threads rather than counting old finding notes as live problems. In overview mode it runs as a subagent and keeps one status file up to date across refreshes. See [`skills/mr-status/SKILL.md`](skills/mr-status/).

## Commands

Each command auto-detects the MR from the current git branch and dumps its state into files before Claude reads anything. None of them changes code.

### `/glab:overview`

Fetches the full MR state — pipeline, comments, external statuses — and presents a status overview without taking any action. Pipeline triage reads the `glab-pipeline` summary and opens a job log only when a job failed.

### `/glab:comments`

Fetches only MR comments, analyzes them, and proposes what to do about the unresolved threads. It also re-reads the resolved threads, because AI reviewers post findings that land there and a resolved thread does not prove the problem is fixed.

### `/glab:pipeline`

Dumps the pipeline through `glab-pipeline inspect`, triages the failed jobs, and proposes fixes. The command tells Claude to read the summary first and then only the job logs, test report, or lint output that the summary points at.

## How it works

`scripts/fetch-mr-state.sh` backs all three commands:

1. Auto-detects the MR from the current git branch
2. Fetches MR info via `glab mr view`
3. Delegates discussion fetching to `glab-discussion read --dump` (per-thread files with incremental updates, bot detection, diff note positions)
4. Delegates the pipeline to `glab-pipeline inspect --mr-url <url>` (jobs, every job trace, and the conditional lint, test-report, and downstream fetches)
5. Adds the external commit statuses, which live on the commit rather than in the pipeline, so `glab-pipeline` does not report them

Output, in `/tmp/glab-state-<id>-<timestamp>/`:

- `mr-info.txt` — full MR details
- `full-pipeline-summary.txt` — the `glab-pipeline` summary plus the external commit statuses
- `pipeline/` — the `glab-pipeline` dump: `summary.json`, `pipeline.json`, `jobs.json`, `job-logs/<stage>-<name>-<id>.log`, and `lint.json`, `merged.yml`, `test-report.json`, `downstream/` when they apply
- `/tmp/glab-discussion/<host>/mr-<iid>/*.txt` — one file per discussion thread, managed by `glab-discussion`

## Related

The unattended loop that drives an MR to green — rebase, fix CI, answer comments — lives in the [`sdlc`](../sdlc/) plugin as `/sdlc:mr-babysit`.

## Known issue

These commands need Claude Code 2.1.0+ because of a [bug in older versions](https://github.com/anthropics/claude-code/issues/9354) where `${CLAUDE_PLUGIN_ROOT}` was not substituted in plugin `allowed-tools` frontmatter. If you see `Error: Bash command permission check failed`, upgrade Claude Code.

## Author

Filip Procházka

## License

MIT
