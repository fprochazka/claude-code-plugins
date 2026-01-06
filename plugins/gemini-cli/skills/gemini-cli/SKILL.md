---
name: gemini-cli
description: Use Gemini CLI in non-interactive mode for tasks requiring massive context windows (1M tokens). Best delegated to subagents for iterative analysis and summarization. Invoke when analyzing large codebases, requesting deep analysis, getting second opinions on complex problems, or when Claude's context limits are insufficient. Triggers include phrases like "use gemini", "analyze with gemini", "get second opinion", "deep analysis of codebase", or when processing files exceeding Claude's context capacity. IMPORTANT - Always delegate to a subagent using the Task tool for better iteration and result summarization.
trigger-keywords: gemini cli, gemini-cli
---

# Gemini CLI Integration

Always run through subagents for better iteration and summarization. Make the subagent always ask Gemini to provide evidence, and make the subagent verify the findings before summarizing for the main agent.

## Quick Reference

```bash
# Basic one-shot query (non-interactive mode)
gemini "Explain this codebase architecture"

# Specify model
gemini -m gemini-3-flash-preview "Complex analysis task"
gemini -m gemini-2.5-flash "Standard analysis task"
gemini -m gemini-2.5-pro "Deep reasoning task"

# Include additional directories
gemini --include-directories ./libs,./shared "Analyze dependencies"

# Multi-line prompt using heredoc
gemini <<'__GEMINI_PROMPT__'
Analyze this codebase for security vulnerabilities.
Focus on: SQL injection, XSS, authentication issues
__GEMINI_PROMPT__

# Output formats
gemini -o json "query"
gemini -o text "query"        # default
gemini -o stream-json "query"
```

## Available Models

### Gemini 3 (Preview)
- **gemini-3-flash-preview** - Best for agentic coding (78% SWE-bench), 1/4 cost of Pro.
- **gemini-3-pro-preview** - Most powerful for multimodal understanding and deep reasoning.

### Gemini 2.5 (GA)
- **gemini-2.5-flash** - Stable, fast
- **gemini-2.5-pro** - Balanced performance for complex tasks
- **gemini-2.5-flash-lite** - Lowest latency and cost

## Subagent Delegation Pattern

**CRITICAL:** Always delegate Gemini tasks to a subagent using the Task tool for multiple retry attempts, better summarization, and error handling.

### Pattern: Using Task Tool with Gemini

```bash
Task(
  subagent_type: "general-purpose",
  description: "Analyze codebase with Gemini",
  prompt: "Use the gemini-cli skill to analyze /path/to/project.
  Focus on security vulnerabilities and performance issues.
  See references/prompt_patterns.md for effective prompts.
  Ask Gemini to provide evidence for findings.
  Verify findings before summarizing key points in bullet form."
)
```

### Pattern: Second Opinion

```bash
Task(
  subagent_type: "general-purpose",
  description: "Get Gemini second opinion",
  prompt: "Use gemini-cli skill to get Gemini's critique of the analysis.
  See references/prompt_patterns.md for second opinion prompts.
  Highlight disagreements or missing considerations."
)
```

## When to Use Gemini vs Claude

| Use Gemini for | Use Claude for |
| -------------- | -------------- |
| Massive codebase review (>100k tokens) | Quick code questions |
| Cross-validating critical analysis | Small file analysis |
| Multi-file architecture analysis | Interactive coding assistance |
| Tasks exceeding Claude's context | Tasks requiring file edits |
| | Tasks requiring follow-up questions |

## Model Selection Guide

- **Production workloads:** `gemini-2.5-flash` (stable, any endpoint)
- **Cutting-edge agentic coding:** `gemini-3-flash-preview` (requires global endpoint)
- **Complex reasoning:** `gemini-2.5-pro` or `gemini-3-pro-preview`
- **High-volume simple queries:** `gemini-2.5-flash-lite`

## Troubleshooting

**Model not available:**
- Gemini 3 models require `-preview` suffix and `GOOGLE_CLOUD_LOCATION=global`
- Fall back to Gemini 2.5 models which work on all endpoints

**Slow responses:** Large context takes time. Consider narrowing scope or use `gemini-2.5-flash-lite`.
