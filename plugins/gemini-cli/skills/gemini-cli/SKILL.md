---
name: gemini-cli
description: Use Gemini CLI in non-interactive mode for tasks requiring massive context windows (1M tokens). Best delegated to subagents for iterative analysis and summarization. Invoke when analyzing large codebases, requesting deep analysis, getting second opinions on complex problems, or when Claude's context limits are insufficient. Triggers include phrases like "use gemini", "analyze with gemini", "get second opinion", "deep analysis of codebase", or when processing files exceeding Claude's context capacity. IMPORTANT - Always delegate to a subagent using the Task tool for better iteration and result summarization.
trigger-keywords: gemini cli, gemini-cli
---

# Gemini CLI Integration

Always run through subagents for better iteration and summarization. Make the subagent always ask Gemini to provide evidence, and make the subagent verify the findings before summarizing for the main agent.

**NEVER use `--approval-mode yolo` or `--yolo`.** Gemini must not auto-approve destructive actions.

## Quick Reference

```bash
# Basic one-shot query (non-interactive mode)
gemini "Explain this codebase architecture"

# Specify model (by alias or full ID)
gemini -m flash "Standard analysis task"
gemini -m pro "Deep reasoning task"
gemini -m gemini-2.5-flash "Use specific GA model"

# Include additional directories in context
gemini --include-directories ./libs,./shared "Analyze dependencies"

# Multi-line prompt using heredoc
gemini <<'__GEMINI_PROMPT__'
Analyze this codebase for security vulnerabilities.
Focus on: SQL injection, XSS, authentication issues
__GEMINI_PROMPT__

# Output formats
gemini -o json "query"         # structured JSON output
gemini -o text "query"         # default
gemini -o stream-json "query"  # real-time JSONL events
```

## Available Models

### Model Aliases (recommended for `-m` flag)

| Alias | Resolves to | Use case |
|-------|------------|----------|
| `auto` | `gemini-3-pro-preview` | Default, auto-routing |
| `pro` | `gemini-3-pro-preview` | Deep reasoning |
| `flash` | `gemini-3-flash-preview` | Fast agentic coding |
| `flash-lite` | `gemini-2.5-flash-lite` | Lowest latency/cost |

### Full Model IDs

**Gemini 3 (Preview):**
- `gemini-3-pro-preview` - Most powerful, deep reasoning
- `gemini-3-flash-preview` - Best for agentic coding (78% SWE-bench), 1/4 cost of Pro

**Gemini 2.5 (GA):**
- `gemini-2.5-pro` - Stable, balanced performance
- `gemini-2.5-flash` - Stable, fast
- `gemini-2.5-flash-lite` - Lowest latency and cost

## Headless Mode Tool Restrictions

In non-interactive mode (positional query or `-p` flag), Gemini restricts certain tools by default:

| Default | Excluded: shell, edit, write_file, web_fetch |
|---------|-----------------------------------------------|
| `--approval-mode auto_edit` | Excluded: shell only |

Override specific restrictions with `--allowed-tools` when needed:
```bash
gemini --allowed-tools ShellTool "Run the test suite and report results"
```

## Subagent Delegation Pattern

**CRITICAL:** Always delegate Gemini tasks to a subagent using the Task tool for multiple retry attempts, better summarization, and error handling.

### Pattern: Using Task Tool with Gemini

```
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

```
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

## Additional Resources

- **`references/prompt_patterns.md`** - Effective prompt templates for codebase analysis, security audits, performance analysis, second opinions, and context maximization tips

## Troubleshooting

**Model not available:** Gemini 3 models are still in preview. Fall back to Gemini 2.5 models for GA stability.

**Slow responses:** Large context takes time. Narrow scope with `--include-directories` or use `flash-lite`.

**Tools not running in headless mode:** Default headless excludes write tools. Use `--allowed-tools` to selectively enable specific tools.
