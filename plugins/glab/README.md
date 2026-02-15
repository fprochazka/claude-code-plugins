# glab

Claude Code skill for interacting with GitLab using the [glab CLI](https://gitlab.com/gitlab-org/cli).

## Requirements

- `glab` CLI installed and on PATH
- Authenticated via `glab auth login`

## Installation

```bash
claude plugin marketplace add fprochazka/claude-code-plugins
claude plugin install glab@fprochazka-claude-code-plugins
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

## Capabilities

- **Merge Requests** - create, view, update title/description, diff, merge, approve, rebase, checkout
- **MR Discussions** - add comments, list/reply to discussion threads, resolve/unresolve threads (via API)
- **CI/CD Pipelines** - view pipeline status, get job details, trace job logs (with file redirect), retry/trigger jobs, lint CI config
- **API** - raw HTTP requests with pagination (`--paginate`), endpoint placeholders, GraphQL support
- **Issues** - list, view, create, update, close (via `--help` discovery)
- **Repositories** - view, list, clone, search (via `--help` discovery)
- **Releases, Variables, Schedules, Labels, Milestones** - via `--help` discovery

## Author

Filip Procházka

## License

MIT
