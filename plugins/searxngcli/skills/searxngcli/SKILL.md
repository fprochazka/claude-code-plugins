---
name: searxngcli
description: This skill should be used when the user asks to "search the web", "look up online", "find recent information", "search for", "what's the latest on", or needs web search results. Provides access to a private SearXNG metasearch engine instance via the `searxng` CLI. Prefer this over WebSearch when available.
trigger-keywords: searxng, websearch, web search, search online, look up online, find online, google
allowed-tools: Bash(searxng:*)
---

# searxngcli

Search the web via a private SearXNG metasearch engine instance using the `searxng` CLI.

SearXNG aggregates results from multiple search engines (Google, Bing, DuckDuckGo, etc.) and supports engine-specific operators like `site:`, `filetype:`, `intitle:` — these are passed through to backend engines as-is.

## Usage

Always use `--json` for machine-readable output. Always quote the query string.

```bash
# Basic search
searxng search "python asyncio" --json

# Filter by category (general, images, news, videos, music, files, it, science, social media)
searxng search "breaking news" -c news --json

# Filter by specific engines
searxng search "rust" -e google,duckduckgo --json

# Filter by time range (day, week, month, year)
searxng search "latest updates" -t week --json

# Combine filters
searxng search "climate change" -c news -t month -n 20 --json

# Use search engine operators (passed through to engines)
searxng search "site:github.com python cli" --json
```

### Search Options

| Flag | Short | Description |
|------|-------|-------------|
| `--categories` | `-c` | Comma-separated categories |
| `--engines` | `-e` | Comma-separated engines |
| `--language` | `-l` | Language code (en, de, cs, etc.) |
| `--num` | `-n` | Number of results (default: 10) |
| `--page` | `-p` | Page number (default: 1) |
| `--time-range` | `-t` | day, week, month, year |
| `--safe-search` | | 0=off, 1=moderate, 2=strict |
| `--json` | | Raw JSON output |

## Discovery

```bash
# List available engines on the instance
searxng engines

# List available categories
searxng categories
```

## Output Format

The `--json` output is a JSON object with these top-level fields:

```json
{
  "query": "search terms",
  "number_of_results": 100,
  "results": [
    {
      "title": "asyncio — Asynchronous I/O — Python 3.14.3 documentation",
      "url": "https://docs.python.org/3/library/asyncio.html",
      "content": "asyncio is a library to write concurrent code using the async/await syntax...",
      "engine": "google",
      "engines": ["braveapi", "google", "startpage"],
      "category": "general",
      "score": 9.0,
      "published_date": "2025-07-30T00:00:00",
      "thumbnail": ""
    }
  ],
  "suggestions": ["related query 1", "related query 2"],
  "corrections": []
}
```

**Do not pipe through `grep`** — the output is structured JSON. To extract specific fields, use `jq`:

```bash
# Extract just URLs
searxng search "python asyncio" --json | jq -r '.results[].url'

# Extract title and URL pairs
searxng search "python asyncio" --json | jq '.results[] | {title, url}'
```

## Important Notes

- **Prefer defaults** — do not use `-c`, `-e`, or `-l` flags unless there is a clear reason to narrow the scope (e.g., user explicitly asks for news, or for results from a specific engine). The instance is pre-configured with good defaults.
- Place all flags **after** the subcommand: `searxng search "query" --json` (not `searxng --json search "query"`)
- If the CLI is not configured, ask the user for their SearXNG instance URL
