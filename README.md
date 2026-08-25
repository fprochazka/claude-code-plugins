# Claude Code Plugins

A collection of Claude Code plugins by Filip Procházka.

## Installation

Add this marketplace to Claude Code:

```bash
claude plugin marketplace add fprochazka/claude-code-plugins --scope user
```

Then install plugins:

```bash
claude plugin install skill-keyword-reminder@fprochazka-claude-code-plugins --scope user
```

### Plugin dependencies

Some plugins declare `dependencies` in their `plugin.json`. Installing such a plugin installs its dependencies too. Dependencies that live in another marketplace resolve only when that marketplace is already added, so add these before you install `sdlc`, `code-review`, `glab`, or `noisy-tools-in-subagent`:

```bash
claude plugin marketplace add fprochazka/glab-discussion --scope user
claude plugin marketplace add fprochazka/glab-pipeline --scope user
claude plugin marketplace add fprochazka/bash-classify --scope user
```

A dependency installed this way is a Claude Code plugin (skill, hook, agent). It does not install the CLI binary the plugin wraps — `glab`, `jq`, `glab-discussion`, `glab-pipeline`, and `bash-classify` stay a manual install, see each plugin's README.

| Plugin | Depends on |
|--------|-----------|
| `sdlc` | `git`, `code-review`, `glab`, `glab-discussion`, `glab-pipeline` |
| `code-review` | `glab`, `glab-discussion` |
| `glab` | `glab-discussion`, `glab-pipeline` |
| `noisy-tools-in-subagent` | `bash-classify-hook` |

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
| [glab](plugins/glab/) | GitLab through the glab CLI — the glab skill, MR commands for pipeline and comment state, and the mr-status review-state skill |
| [glab-discussion](https://github.com/fprochazka/glab-discussion) | Standalone CC plugin + CLI for reading and managing GitLab MR discussion threads |
| [ai-tool-use-validator](plugins/ai-tool-use-validator/) | AI-powered tool use validation using LLM backends (Vertex AI, etc.) to evaluate command safety and correctness |
| [slackcli](https://github.com/fprochazka/slackcli) | Standalone CC plugin + CLI for interacting with Slack workspaces |
| [migrate-to-uv](plugins/migrate-to-uv/) | Skill for migrating Python projects from Poetry, pipx, or pip to uv |
| [metabasecli](plugins/metabasecli/) | Skill for interacting with Metabase using the metabase CLI |
| [gogcli](plugins/gogcli/) | Skill for interacting with Google services (Gmail, Calendar, Drive, Docs, Sheets, Slides, Contacts, Tasks, Forms, Chat, People) using the gog CLI |
| [rabbitmqadmin](plugins/rabbitmqadmin/) | Skill for inspecting RabbitMQ instances using the rabbitmqadmin CLI (rabbitmqadmin-ng) |
| [searxngcli](plugins/searxngcli/) | Skill for searching the web using a SearXNG instance via the searxngcli CLI |
| [web-researcher](plugins/web-researcher/) | Iterative web research agent that searches, discovers new directions, and synthesizes findings |
| [git](plugins/git/) | Git workflow skill and commit commands — vertical-slice atomic commits, the sibling/ancestor boundary test, fixups over correction commits, and dependency-ordered branch history |
| [code-review](plugins/code-review/) | Multi-agent branch code review — conventions, architecture, design craft, bugs, performance, security, release readiness, and git history reviewed in parallel |
| [sdlc](plugins/sdlc/) | Software delivery workflow commands — gather context, write plans, file tickets, open MRs, babysit them to green, wrap them up, and brief next steps |
| [noisy-tools-in-subagent](plugins/noisy-tools-in-subagent/) | Forces noisy commands (builds, tests, linters, static analysis) to run inside a Sonnet subagent instead of the main context, preserving main-agent tokens |

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
