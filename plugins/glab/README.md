# glab

Claude Code plugin for GitLab through the [glab CLI](https://gitlab.com/gitlab-org/cli). It carries the `glab` skill, the `mr-status` skill, and slash commands that dump the state of a merge request.

## Requirements

- Claude Code **2.1.0 or newer** (see [Known issue](#known-issue))
- `glab` CLI installed, on PATH, and authenticated via `glab auth login`
- `jq` for JSON processing
- [`glab-discussion`](https://github.com/fprochazka/glab-discussion) for discussion handling (`uv tool install glab-discussion`)
- [`glab-pipeline`](https://github.com/fprochazka/glab-pipeline) for pipeline triage (`uv tool install glab-pipeline`)

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

## Skills

- `glab:glab` — the CLI reference. Merge requests, discussions, pipelines, issues, repositories, releases, variables, schedules, labels, milestones, and the raw API with pagination and GraphQL.
- `glab:mr-status` — reads the real review-and-merge state of one MR or a whole set: draft, rebase distance, pipeline, approvals, size, every AI reviewer's latest verdict, human threads, and what blocks the merge right now. It profiles each AI reviewer from its own threads instead of assuming how a bot behaves, and it reads the newest verdict plus the currently unresolved threads rather than counting old finding notes as live problems. In overview mode it runs as a subagent and keeps one status file up to date across refreshes. See [`skills/mr-status/SKILL.md`](skills/mr-status/).

## Commands

Each command auto-detects the MR from the current git branch and dumps its state into files before Claude reads anything. None of them changes code.

### `/glab:overview`

Fetches the full MR state — pipeline, comments, external statuses — and presents a status overview without taking any action.

### `/glab:comments`

Fetches only MR comments, analyzes them, and proposes what to do about the unresolved threads. It also re-reads the resolved threads, because AI reviewers post findings that land there and a resolved thread does not prove the problem is fixed.

### `/glab:pipeline`

Fetches only the pipeline status and the job logs, triages the failures, and proposes fixes.

## How it works

`scripts/fetch-mr-state.sh` backs all three commands:

1. Auto-detects the MR from the current git branch
2. Fetches MR info via `glab mr view`
3. Delegates discussion fetching to `glab-discussion read --dump` (per-thread files with incremental updates, bot detection, diff note positions)
4. Fetches pipeline status, job details, and logs in parallel with retry

Output:

- `mr-info.txt` — full MR details, in `/tmp/glab-state-<id>-<timestamp>/`
- `/tmp/glab-discussion/<host>/mr-<iid>/*.txt` — one file per discussion thread, managed by `glab-discussion`
- `full-pipeline-summary.txt` — pipeline status and all jobs
- `job-logs/` — one log file per job

## Related

The unattended loop that drives an MR to green — rebase, fix CI, answer comments — lives in the [`sdlc`](../sdlc/) plugin as `/sdlc:mr-babysit`.

## Known issue

These commands need Claude Code 2.1.0+ because of a [bug in older versions](https://github.com/anthropics/claude-code/issues/9354) where `${CLAUDE_PLUGIN_ROOT}` was not substituted in plugin `allowed-tools` frontmatter. If you see `Error: Bash command permission check failed`, upgrade Claude Code.

## Author

Filip Procházka

## License

MIT
