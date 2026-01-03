# Skill Keyword Reminder

Automatically reminds Claude to load relevant skills when keyword triggers appear in user prompts.

## Overview

Claude Code skills are powerful, but Claude doesn't always remember to load them when they're relevant. You might ask about "Linear issues" and Claude forgets to invoke the `linear` skill first.

This plugin intercepts every user prompt via a `UserPromptSubmit` hook and scans for keywords defined in your skills. When a match is found, it injects a reminder into the context:

```
IMPORTANT: don't forget to load linear-mcp-cli skill and relevant references in it
```

## How It Works

1. User submits a prompt
2. `UserPromptSubmit` hook triggers `scan_skills.py`
3. Script scans for `SKILL.md` files with `trigger-keywords` frontmatter in:
   - `~/.claude/skills/*/SKILL.md` (user-level skills)
   - `$CLAUDE_PROJECT_DIR/.claude/skills/*/SKILL.md` if env var is set
   - Otherwise, `.claude/skills/*/SKILL.md` walking up from cwd to home
4. If any keyword matches the prompt, injects a reminder via `additionalContext`
5. Claude sees the reminder and loads the appropriate skill

Project-level skills take precedence over user-level skills with the same name.

If a skill directory contains a `references/` subdirectory, the reminder also mentions to check references.

**Smart deduplication:** The plugin reads the current session transcript and skips reminders for skills that have already been loaded in this session.

## Configuration

Add `trigger-keywords` to the YAML frontmatter of your `SKILL.md` files:

```yaml
---
name: linear-mcp-cli
description: CLI for querying Linear issues and projects
trigger-keywords: linear, issue, issues, tasks, ticket, tickets
---
```

> **Note:** The `trigger-keywords` attribute is non-standard and only recognized by this plugin. Claude Code may introduce its own keyword triggering mechanism in the future, which could make this plugin obsolete or require migration.

**Keyword matching rules:**
- Comma-separated list
- Case-insensitive matching
- Matched as whole words (e.g., `linear` matches in `linear.app` but not in `nonlinear`)
- Multi-word keywords supported (e.g., `deep research`)

## Example

[Gemini Deep Research](https://github.com/fprochazka/gemini-deep-research) skill with trigger keywords:

```yaml
# ~/.claude/skills/gemini-deep-research/SKILL.md
---
name: gemini-deep-research
trigger-keywords: deep research, deep dive, comprehensive analysis
---
```

## Installation

**From marketplace:**

```bash
claude plugin marketplace add fprochazka/claude-code-plugins
claude plugin install skill-keyword-reminder@fprochazka-claude-code-plugins
```

**Local testing:**

```bash
claude --plugin-dir /path/to/plugins/skill-keyword-reminder
```

## Requirements

- Python 3.10+
- No external dependencies (uses stdlib only)

## Troubleshooting

### Skill not being reminded

**Issue:** Keyword appears in prompt but no reminder is injected

**Solution:**
1. Verify the skill has `trigger-keywords` in its SKILL.md frontmatter
2. Check the keyword is spelled correctly
3. Ensure the SKILL.md is in one of:
   - `~/.claude/skills/<skill-name>/SKILL.md`
   - `.claude/skills/<skill-name>/SKILL.md` (in project or parent directories)
4. Test the script manually: `echo '{"prompt":"test linear","cwd":"/path/to/project"}' | python3 scripts/scan_skills.py`

## Author

Filip Procházka

## License

MIT
