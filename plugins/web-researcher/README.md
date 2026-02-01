# Web Researcher Plugin

Iterative web research agent that searches, discovers new directions, and synthesizes findings - like a human researcher would.

## Installation

```bash
claude plugin install web-researcher@fprochazka-claude-code-plugins
```

## Usage

```
/web-researcher:search <your query>
```

Example:
```
/web-researcher:search how to implement OAuth2 PKCE flow in a CLI application
```

## How It Works

The plugin spawns a dedicated research subagent that:

1. **Searches** with your initial keywords
2. **Reads** 2-3 promising pages to gain context
3. **Discovers** new terminology, related concepts, and authoritative sources
4. **Follows leads** by searching with newly discovered keywords
5. **Repeats** 2-4 iterations until the query is comprehensively answered

The subagent is restricted to only `WebSearch` and `WebFetch` tools, and all exploratory dead ends stay isolated in the subagent context - only the distilled, useful findings are returned.

## Output Format

Results are structured as:
- **Summary** - comprehensive answer to your query
- **Key Findings** - most important points discovered
- **Sources** - only URLs that were actually helpful

## Components

- **`/web-researcher:search`** - Command to trigger research
- **`web-researcher` agent** - The iterative research subagent

## License

MIT
