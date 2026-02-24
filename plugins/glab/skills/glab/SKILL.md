---
name: glab
description: GitLab CLI for merge requests, issues, CI/CD pipelines, repositories, and more. Use when working with GitLab to list/view MRs, check CI status, browse issues, or any GitLab API operation. Triggered by requests involving GitLab data, merge requests, CI pipelines, or GitLab project management.
trigger-keywords: gitlab, glab, merge request, MR
allowed-tools: Bash(glab --help), Bash(glab help:*), Bash(glab alias --help), Bash(glab api --help), Bash(glab auth --help), Bash(glab changelog --help), Bash(glab ci --help), Bash(glab ci artifact --help), Bash(glab ci cancel --help), Bash(glab ci config --help), Bash(glab ci delete --help), Bash(glab ci get --help), Bash(glab ci lint --help), Bash(glab ci list --help), Bash(glab ci retry --help), Bash(glab ci run --help), Bash(glab ci run-trig --help), Bash(glab ci status --help), Bash(glab ci trace --help), Bash(glab ci trigger --help), Bash(glab ci view --help), Bash(glab cluster --help), Bash(glab config --help), Bash(glab deploy-key --help), Bash(glab duo --help), Bash(glab gpg-key --help), Bash(glab incident --help), Bash(glab issue --help), Bash(glab issue board --help), Bash(glab issue close --help), Bash(glab issue create --help), Bash(glab issue delete --help), Bash(glab issue list --help), Bash(glab issue note --help), Bash(glab issue reopen --help), Bash(glab issue subscribe --help), Bash(glab issue unsubscribe --help), Bash(glab issue update --help), Bash(glab issue view --help), Bash(glab iteration --help), Bash(glab iteration list --help), Bash(glab job --help), Bash(glab label --help), Bash(glab mcp --help), Bash(glab mcp serve --help), Bash(glab milestone --help), Bash(glab mr --help), Bash(glab mr approve --help), Bash(glab mr approvers --help), Bash(glab mr checkout --help), Bash(glab mr close --help), Bash(glab mr create --help), Bash(glab mr delete --help), Bash(glab mr diff --help), Bash(glab mr for --help), Bash(glab mr issues --help), Bash(glab mr list --help), Bash(glab mr merge --help), Bash(glab mr note --help), Bash(glab mr rebase --help), Bash(glab mr reopen --help), Bash(glab mr revoke --help), Bash(glab mr subscribe --help), Bash(glab mr todo --help), Bash(glab mr unsubscribe --help), Bash(glab mr update --help), Bash(glab mr view --help), Bash(glab opentofu --help), Bash(glab release --help), Bash(glab repo --help), Bash(glab schedule --help), Bash(glab securefile --help), Bash(glab snippet --help), Bash(glab ssh-key --help), Bash(glab stack --help), Bash(glab token --help), Bash(glab user --help), Bash(glab variable --help), Bash(glab issue list:*), Bash(glab issue view:*), Bash(glab ci artifact:*), Bash(glab ci get:*), Bash(glab ci lint:*), Bash(glab ci list:*), Bash(glab ci status:*), Bash(glab ci trace:*), Bash(glab job artifact:*), Bash(glab mr approvers:*), Bash(glab mr diff:*), Bash(glab mr issues:*), Bash(glab mr list:*), Bash(glab mr view:*), Bash(glab schedule list:*), Bash(glab-search-code:*)
---

# glab - GitLab CLI

Command-line interface for GitLab. Binary name: `glab`.

## Repository Context

glab auto-detects the GitLab project from the git remote in the current directory. Override with `--repo` (`-R`):

```bash
glab mr list                              # auto-detected from git remote
glab mr list -R group/project             # explicit project
glab mr list -R group/namespace/project
```

## Identifying MRs

MR commands accept an MR IID number, a branch name, or nothing (current branch):

```bash
glab mr view 123           # by MR IID
glab mr view feature-x     # by branch name
glab mr view               # current branch's MR
```

---

## Temp Files

When writing content to temp files (MR descriptions, job logs, etc.), use filenames unique to the MR or job — include the MR number, branch name, or job name as a slug (e.g., `/tmp/mr-desc-123.md`, `/tmp/mr-desc-feature-auth.md`, `/tmp/glab-job-build-123.log`).

**Reuse the same file for the same MR/entity** across multiple edits — the Write tool shows diffs, so the user can see exactly what changed between revisions.

**Never use generic fixed filenames** like `/tmp/mr-description.md` — they collide across different MRs.

---

## Creating a Merge Request

```bash
glab mr create --fill --fill-commit-body --yes -b main --draft -a user1 --reviewer user2 -l bug
```

| Flag | Short | Description |
|------|-------|-------------|
| `--title` | `-t` | MR title |
| `--description` | `-d` | Description (`"-"` opens editor) |
| `--fill` | `-f` | Use commit info, auto-push branch |
| `--fill-commit-body` | | Include all commit bodies (with `--fill`) |
| `--draft` | | Create as draft |
| `--assignee` | `-a` | Assign by username (comma-separated or repeated) |
| `--reviewer` | | Request review by username |
| `--label` | `-l` | Add labels |
| `--milestone` | `-m` | Assign milestone |
| `--target-branch` | `-b` | Target branch |
| `--source-branch` | `-s` | Source branch (default: current) |
| `--push` | | Push branch before creating |
| `--remove-source-branch` | | Remove source branch on merge |
| `--squash-before-merge` | | Squash commits on merge |
| `--related-issue` | `-i` | Link to issue IID |
| `--copy-issue-labels` | | Copy labels from linked issue |
| `--yes` | `-y` | Skip confirmation prompt |
| `--web` | `-w` | Continue in browser |

---

## Viewing Current MR

```bash
glab mr view --comments -F json
```

| Flag | Short | Description |
|------|-------|-------------|
| `--comments` | `-c` | Include comments and activities |
| `--system-logs` | `-s` | Include system activities |
| `--output` | `-F` | Format: `text`, `json` |
| `--web` | `-w` | Open in browser |
| `--page` | `-p` | Page number for comments |
| `--per-page` | `-P` | Items per page (default 20) |

---

## Updating MR Title and Description

```bash
glab mr update 123 --title "New title" --description "New description" --ready -l bug --reviewer +user2
```

Assignee/reviewer prefix modifiers: `+` to add, `!` or `-` to remove. No prefix replaces all.

| Flag | Short | Description |
|------|-------|-------------|
| `--title` | `-t` | MR title |
| `--description` | `-d` | Description (`"-"` opens editor) |
| `--draft` | | Mark as draft |
| `--ready` | `-r` | Mark as ready |
| `--label` | `-l` | Add labels |
| `--unlabel` | `-u` | Remove labels |
| `--assignee` | `-a` | Set assignees (`+` add, `!` remove, bare replaces all) |
| `--unassign` | | Remove all assignees |
| `--reviewer` | | Set reviewers (`+` add, `!` remove, bare replaces all) |
| `--milestone` | `-m` | Set milestone (`""` or `0` to unset) |
| `--target-branch` | | Change target branch |
| `--remove-source-branch` | | Toggle remove source branch on merge |
| `--squash-before-merge` | | Toggle squash on merge |
| `--lock-discussion` | | Lock discussion |
| `--unlock-discussion` | | Unlock discussion |
| `--yes` | `-y` | Skip confirmation |

---

## MR Discussions and Notes

`glab mr note` can add comments, but listing discussions and replying to threads requires the API.

### Add a Comment

```bash
glab mr note 123 -m "Looks good!"
```

| Flag | Short | Description |
|------|-------|-------------|
| `--message` | `-m` | Comment text |
| `--unique` | | Skip if identical comment already exists |

### List MR Discussions (API)

Discussions are threaded conversations. Each discussion has an `id` and contains `notes`.

```bash
glab api projects/:id/merge_requests/123/discussions --paginate
```

### Reply to a Discussion Thread (API)

```bash
glab api -X POST projects/:id/merge_requests/123/discussions/<discussion_id>/notes \
  -f body="Reply text"
```

### Create a New Discussion Thread (API)

```bash
glab api -X POST projects/:id/merge_requests/123/discussions \
  -f body="Starting a new thread"
```

### Resolve / Unresolve a Discussion (API)

```bash
glab api -X PUT projects/:id/merge_requests/123/discussions/<discussion_id> \
  -F resolved=true
```

---

## MR Pipeline and Job Logs

### View Pipeline Status

```bash
glab ci status --compact
glab ci get --with-job-details -F json
```

| Command | Description |
|---------|-------------|
| `glab ci status` | Current branch pipeline status |
| `glab ci status --live` | Real-time updates until done |
| `glab ci status --compact` | Compact view |
| `glab ci get` | Pipeline details with job list |
| `glab ci get --with-job-details` | Extended job info |
| `glab ci get -F json` | JSON output |

### View Job Logs

**Always redirect job logs to a temp file** — the output can be thousands of lines and will waste context tokens.

```bash
glab ci trace <job-name> > /tmp/glab-job-<job-name>-$(date +%s).log 2>&1
```

**DO NOT** run `glab ci trace` without redirecting to a file.

| Flag | Short | Description |
|------|-------|-------------|
| `--branch` | `-b` | Branch to search for the job |
| `--pipeline-id` | `-p` | Pipeline ID to search for the job |

### Retry / Trigger Jobs

```bash
glab ci retry <job-name>           # retry a failed job
glab ci trigger <job-name>         # trigger a manual job
```

---

## API (Raw HTTP Requests)

Direct GitLab API access for anything not covered by dedicated commands.

```bash
glab api projects/:id/members                                    # GET (default)
glab api projects/:id/labels -f name=bug -f color=#FF0000        # POST (default when params present)
glab api -X PUT projects/:id -f name="new-name"                  # explicit method
```

### Pagination

`--paginate` fetches **all pages** sequentially. Without it, you only get the first page.

```bash
glab api projects/:id/issues --paginate --output ndjson | jq 'select(.state == "opened")'
```

Output formats:
- `json` (default) — pretty-printed, arrays merged into a single JSON array
- `ndjson` — one JSON object per line, memory-efficient, works with `jq`

### Endpoint Placeholders

Auto-resolved from the git remote: `:id`, `:fullpath`, `:group`, `:namespace`, `:repo`, `:branch`, `:user`, `:username`

### Parameter Flags

| Flag | Short | Description |
|------|-------|-------------|
| `--raw-field` | `-f` | String parameter |
| `--field` | `-F` | Typed parameter (`true`/`false`/integers auto-converted, `@file` reads from file) |
| `--method` | `-X` | HTTP method (default: GET without params, POST with) |
| `--paginate` | | Fetch all pages |
| `--output` | | Format: `json` (default), `ndjson` |
| `--header` | `-H` | Additional HTTP header |
| `--hostname` | | Override GitLab host |
| `--include` | `-i` | Include response headers |
| `--input` | | Request body from file (`-` for stdin) |
| `--silent` | | Don't print response body |

---

## Other Commands

Discover flags with `--help`:

| Group | Description |
|-------|-------------|
| `mr list`, `mr diff`, `mr merge`, `mr approve`, `mr rebase`, `mr checkout` | MR management |
| `issue list`, `issue view`, `issue create`, `issue update`, `issue close` | Issues |
| `ci list`, `ci run`, `ci lint`, `ci cancel` | CI/CD pipelines |
| `job artifact` | Download job artifacts |
| `repo view`, `repo list`, `repo clone` | Repositories |
| `release list`, `release view`, `release create` | Releases |
| `variable list`, `variable get`, `variable set` | CI/CD variables |
| `schedule list`, `schedule create`, `schedule run` | Pipeline schedules |
| `label list`, `label create` | Labels |
| `milestone list`, `milestone create` | Milestones |
| `glab-search-code <query>` | Code search |

```bash
glab <command> --help
glab <command> <subcommand> --help
```
