# research

Skill for researching a question on the web. Claude searches, reads the best sources, follows the terms and leads they reveal, searches again until the question is answered, and returns an answer that cites its sources.

The skill describes the method only. It uses whatever web search and page fetching the session has, so it works with the built-in web tools, a SearXNG CLI, or any other search backend you set up.

## Installation

```bash
claude plugin marketplace add fprochazka/claude-code-plugins --scope user
claude plugin install research@fprochazka-claude-code-plugins --scope user
```

## Usage

Run it as a command:

```
/research:research-loop how do I implement the OAuth2 PKCE flow in a CLI application
```

Claude also loads the skill on its own when you ask it to research something on the web or look something up online.

The skill runs in the context of the agent that loads it. To keep the search path and the dead ends out of the main session, ask Claude to run the research in a subagent.

## Permissions

To load the skill without a permission prompt, add it to `~/.claude/settings.json`:

```json
{
  "permissions": {
    "allow": [
      "Skill(research:research-loop)"
    ]
  }
}
```

The permissions for the search and fetch tools themselves stay with the tools you use.

## License

MIT
