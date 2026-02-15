---
name: gemini-deep-research
description: Conducts comprehensive, autonomous deep research on specific topics using Google's Gemini Deep Research API. Initiates long-running background research tasks that synthesize multiple sources into detailed reports. Use when users request deep analysis, comprehensive research, or multi-source synthesis on complex topics. Triggered by phrases like "research", "deep dive", "comprehensive analysis", or when simple fact lookups are insufficient.
trigger-keywords: deep research, deep dive, comprehensive analysis
allowed-tools: Bash(gemini-deep-research:*)
---

# Gemini Deep Research

Perform autonomous deep research using the `gemini-deep-research` CLI tool, which leverages Google's Gemini Deep Research API to synthesize information from multiple sources.

## Usage

Execute research with the `gemini-deep-research` command:

```bash
gemini-deep-research research "Your detailed research query here"
```

**Optional flags:**
- `--verbose` - Show detailed progress updates
- `--poll-interval N` - Check status every N seconds (default: 10)

**IMPORTANT**:
- This is a **long-running operation** that typically takes 3-10 minutes or longer depending on query complexity
- The tool saves the report to `/tmp/gemini-deep-research/<timestamp>/research.md`
- You MUST read this file after the command completes to access the research results

## Workflow

1. Run the `gemini-deep-research research` command with the user's query
2. **Wait for the command to complete** - This will take several minutes (typically 3-10+ minutes). Do not timeout or cancel the operation prematurely.
3. Read the generated markdown file at the path printed by the tool
4. Present the research findings to the user

## Commands

### research

Start a new research task:

```bash
gemini-deep-research research "What are the latest developments in quantum computing?"
gemini-deep-research research "Impact of AI on software development" --poll-interval 15
gemini-deep-research research "Future of renewable energy" --verbose
```

### status

Check the status of a running or completed research task:

```bash
gemini-deep-research status <interaction-id>
```

### fetch-results

Retrieve and save completed research results (useful if polling was interrupted):

```bash
gemini-deep-research fetch-results <interaction-id>
```

## Example

User: "Research the history and architectural evolution of transformer models in NLP"

```bash
gemini-deep-research research "Research the history and architectural evolution of transformer models in NLP"
```

After completion, use the Read tool to access the research report at the path printed by the tool (e.g., `/tmp/gemini-deep-research/2025-12-29T08-15-00/research.md`).
