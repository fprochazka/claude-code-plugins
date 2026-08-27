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

### Maintained here

| Plugin | Description |
|--------|-------------|
| [sdlc](plugins/sdlc/) | Software delivery workflow commands — gather context, write plans, file tickets, open MRs, babysit them to green, wrap them up, and brief next steps |
| [code-review](plugins/code-review/) | Multi-agent branch code review — conventions, architecture, design craft, bugs, performance, security, release readiness, git history, and documentation reviewed in parallel |
| [git](plugins/git/) | Git workflow skill and commit commands — vertical-slice atomic commits, the sibling/ancestor boundary test, fixups over correction commits, and dependency-ordered branch history |
| [glab](plugins/glab/) | GitLab through the glab CLI — the glab skill, MR commands for pipeline and comment state, and the mr-status review-state skill |
| [noisy-tools-in-subagent](plugins/noisy-tools-in-subagent/) | Forces noisy commands (builds, tests, linters, static analysis) to run inside a Sonnet subagent instead of the main context, preserving main-agent tokens |
| [skill-keyword-reminder](plugins/skill-keyword-reminder/) | Automatically reminds Claude to load relevant skills when keyword triggers appear in user prompts |
| [searxngcli](plugins/searxngcli/) | Skill for searching the web using a SearXNG instance via the searxngcli CLI |
| [web-researcher](plugins/web-researcher/) | Iterative web research agent that searches, discovers new directions, and synthesizes findings |
| [rabbitmqadmin](plugins/rabbitmqadmin/) | Skill for inspecting RabbitMQ instances using the rabbitmqadmin CLI (rabbitmqadmin-ng) |
| [migrate-to-uv](plugins/migrate-to-uv/) | Skill for migrating Python projects from Poetry, pipx, or pip to uv |
| [gemini-cli](plugins/gemini-cli/) | Skill and review agent for using Gemini CLI with massive context windows (1M tokens) for codebase analysis and second opinions |

### Hosted externally

Each of these is a CLI with its own Claude Code plugin in the same repository. The repository is its own marketplace, so add it with `claude plugin marketplace add fprochazka/<name> --scope user` before you install the plugin.

| Plugin | Description |
|--------|-------------|
| [glab-discussion](https://github.com/fprochazka/glab-discussion) | Skill for working with GitLab MR discussions via the glab-discussion CLI |
| [glab-pipeline](https://github.com/fprochazka/glab-pipeline) | Agent-friendly GitLab CI pipeline inspector — dumps full pipeline state and prints a problem-driven summary |
| [bash-classify](https://github.com/fprochazka/bash-classify) | Auto-allows low-risk bash commands in Claude Code using bash-classify |
| [slackcli](https://github.com/fprochazka/slackcli) | Skill for interacting with Slack workspaces using the slackcli CLI |
| [metabasecli](https://github.com/fprochazka/metabasecli) | Skill for interacting with Metabase using the metabase CLI |
| [devin-mcp-cli](https://github.com/fprochazka/devin-mcp-cli) | Skill for interacting with the Devin MCP server using the devin-mcp CLI |
| [gemini-deep-research](https://github.com/fprochazka/gemini-deep-research) | Skill for conducting autonomous deep research using Google's Gemini Deep Research Agent |

### Experiments

Plugins that explore an idea. They work, but the shape can change without notice and they get less care than the ones above.

| Plugin | Description |
|--------|-------------|
| [ai-tool-use-validator](plugins/ai-tool-use-validator/) | AI-powered tool use validation using LLM backends (Vertex AI, etc.) to evaluate command safety and correctness |

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
