# gemini-deep-research

Skill for conducting autonomous deep research using [gemini-deep-research](https://github.com/fprochazka/gemini-deep-research) CLI, which leverages Google's Gemini Deep Research Agent.

## Requirements

- `gemini-deep-research` CLI installed and on PATH
- `GEMINI_API_KEY` environment variable set (get one from [Google AI Studio](https://aistudio.google.com/apikey))

See the [gemini-deep-research repository](https://github.com/fprochazka/gemini-deep-research) for installation and configuration instructions.

## Installation

```bash
claude plugin marketplace add fprochazka/claude-code-plugins
claude plugin install gemini-deep-research@fprochazka-claude-code-plugins
```

## Permissions

Add the following to `~/.claude/settings.json` to allow the skill to load and auto-approve commands:

```json
{
  "permissions": {
    "allow": [
      "Skill(gemini-deep-research)"
    ]
  }
}
```

The skill's `allowed-tools` frontmatter auto-allows all `gemini-deep-research` commands.

## Usage

The skill is automatically loaded when needed. It teaches Claude how to use the `gemini-deep-research` CLI to:

- Conduct autonomous deep research on any topic
- Monitor long-running research tasks
- Retrieve and present research reports

## Author

Filip Prochazka

## License

MIT
