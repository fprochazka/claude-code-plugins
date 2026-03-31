# Claude Code Plugins

A collection of Claude Code plugins by Filip Procházka.

## Installation

Add this marketplace to Claude Code:

```bash
claude plugin marketplace add fprochazka/claude-code-plugins
```

Then install plugins:

```bash
claude plugin install skill-keyword-reminder@fprochazka-claude-code-plugins
```

## Upgrading

To upgrade installed plugins to the latest version:

```bash
claude plugin marketplace update fprochazka-claude-code-plugins
claude plugin update skill-keyword-reminder@fprochazka-claude-code-plugins
```

## Available Plugins

| Plugin | Description |
|--------|-------------|
| [skill-keyword-reminder](plugins/skill-keyword-reminder/) | Automatically reminds Claude to load relevant skills when keyword triggers appear in user prompts |
| [gemini-cli](plugins/gemini-cli/) | Skill and review agent for using Gemini CLI with massive context windows (1M tokens) for codebase analysis and second opinions |
| [gemini-deep-research](plugins/gemini-deep-research/) | Skill for conducting autonomous deep research using Google's Gemini Deep Research Agent |
| [glab](plugins/glab/) | Skill for interacting with GitLab using the glab CLI |
| [glab-discussion](https://github.com/fprochazka/glab-discussion) | Standalone CC plugin + CLI for reading and managing GitLab MR discussion threads |
| [glab-mr](plugins/glab-mr/) | GitLab MR tools - fix failed CI, resolve comments, and more |
| [ai-tool-use-validator](plugins/ai-tool-use-validator/) | AI-powered tool use validation using LLM backends (Vertex AI, etc.) to evaluate command safety and correctness |
| [slackcli](plugins/slackcli/) | Skill for interacting with Slack workspaces using the slackcli CLI |
| [migrate-to-uv](plugins/migrate-to-uv/) | Skill for migrating Python projects from Poetry, pipx, or pip to uv |
| [metabasecli](plugins/metabasecli/) | Skill for interacting with Metabase using the metabase CLI |
| [gogcli](plugins/gogcli/) | Skill for interacting with Google services (Gmail, Calendar, Drive, Docs, Sheets, Slides, Contacts, Tasks, Forms, Chat, People) using the gog CLI |
| [rabbitmqadmin](plugins/rabbitmqadmin/) | Skill for inspecting RabbitMQ instances using the rabbitmqadmin CLI (rabbitmqadmin-ng) |
| [searxngcli](plugins/searxngcli/) | Skill for searching the web using a SearXNG instance via the searxngcli CLI |
| [web-researcher](plugins/web-researcher/) | Iterative web research agent that searches, discovers new directions, and synthesizes findings |
| [code-review](plugins/code-review/) | Multi-agent branch code review — conventions, architecture, bugs, security, and git history reviewed in parallel |

## Developing

### Creating a New Plugin

- [ ] Create `plugins/<name>/` directory
- [ ] Create `plugins/<name>/.claude-plugin/plugin.json` with name, version, description
- [ ] Add plugin content (skills/, commands/, agents/, hooks/, etc.)
- [ ] Create `plugins/<name>/README.md`
- [ ] Add entry to `.claude-plugin/marketplace.json` with matching version
- [ ] Add row to "Available Plugins" table in the root README

### Releasing a New Version

- [ ] Update version in `plugins/<name>/.claude-plugin/plugin.json`
- [ ] Update version in `.claude-plugin/marketplace.json`
- [ ] Commit and push

### Notes

- Plugins are pinned to commit SHAs when installed
- Users must run `claude plugin update <name>@fprochazka-claude-code-plugins` to get updates
- Use semantic versioning: MAJOR.MINOR.PATCH

## License

MIT
