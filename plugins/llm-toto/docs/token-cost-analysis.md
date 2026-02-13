# Token Cost Analysis & Threshold Design

Research into Claude API pricing and tool call overhead to determine the optimal threshold for when to buffer command output to a file vs printing inline.

## Claude API Pricing (as of 2026)

| Model | Input (per MTok) | Output (per MTok) |
|-------|-------------------|---------------------|
| Haiku 4.5 | $1 | $5 |
| Sonnet 4.5 | $3 | $15 |
| Opus 4.5 | $5 | $25 |

Long-context surcharge (>200K input tokens): ~2x input price, ~1.5x output price.

Prompt caching: cache reads cost 0.1x base input price.

Sources:
- [Anthropic Pricing](https://platform.claude.com/docs/en/about-claude/pricing)
- [Claude Code Cost Management](https://code.claude.com/docs/en/costs)

## Tool Call Cost Structure

Tool use has **no separate surcharge**. The cost comes from additional tokens consumed by:

1. **Tool definitions** -- JSON schema sent with each request (~55K tokens for a typical 5-server MCP setup)
2. **Tool call results** -- returned data counted as input tokens on all subsequent turns
3. **System prompt additions** -- e.g. ~466-499 tokens for computer use

The compounding effect is critical: every token in a tool result stays in context and is re-sent as input on **every subsequent turn** until compaction.

## Context Accumulation Model

In Claude Code's agentic loop:
- Each turn re-sends the full conversation history as input tokens
- Previous tool results are included in the history
- Context grows linearly until compaction triggers
- Compaction summarizes history but critical state is preserved
- Average session: $6/developer/day, 90th percentile: $12/day

### Compounding Cost of Inline Output

If a command produces X tokens of inline output and there are N remaining turns before compaction:

```
Cost of inline output = X * N * input_price_per_token
```

For a 1,000-token output with 20 remaining turns on Sonnet 4.5:
```
1,000 * 20 * $3/1M = $0.06
```

For a 2,500-token output (10K chars) with 20 remaining turns:
```
2,500 * 20 * $3/1M = $0.15
```

### Cost of Buffered Approach

When output is buffered to file, the inline cost is replaced by:
1. **Summary tokens** (~30 tokens: file path + keyword summary + preview)
2. **Extra Read turn** (~50 output tokens for the model to generate a Read tool call)
3. **Read result tokens** (whatever portion of the file the LLM reads)

```
Cost of buffered = 30 * N * input_price + 50 * output_price + read_tokens * (N-1) * input_price
```

## Break-Even Analysis

### When is buffering worth it?

The net savings depend on:
- **X**: original output size in tokens
- **N**: remaining turns before compaction
- **R**: how much of the file the LLM actually reads (0 to X)

| Output (chars) | Tokens (~4c/tok) | Savings/turn (vs ~30 tok summary) | Over 10 turns | Over 20 turns |
|-----------------|-------------------|---------------------------------------|----------------|----------------|
| 1,000 | 250 | 220 input tokens | $0.007 | $0.013 |
| 2,000 | 500 | 470 input tokens | $0.014 | $0.028 |
| 4,000 | 1,000 | 970 input tokens | $0.029 | $0.058 |
| 10,000 | 2,500 | 2,470 input tokens | $0.074 | $0.148 |
| 20,000 | 5,000 | 4,970 input tokens | $0.149 | $0.298 |

Extra Read call cost: ~50 output tokens = $0.00075 (Sonnet) to $0.00125 (Opus).

**Conclusion:** Even at 1,000 chars (~250 tokens), buffering saves $0.007-$0.013 over 10-20 turns. The extra Read call costs < $0.002. Buffering is cost-positive for outputs above ~500 chars.

### But UX matters more than cost

The pure cost break-even is very low, but there's a UX cost:
- Each buffered command requires an extra tool call (Read) for the LLM to see details
- The LLM might read the whole file, negating savings
- For small outputs, the overhead isn't worth the latency of an extra turn

### Recommended Threshold: ~4,000 chars (~100 lines)

This captures the top ~10% of outputs (P90 = 4,835 chars from our 12,063-command analysis) where:
- Context savings are meaningful ($0.03-$0.15 per command over a session)
- The output is large enough that a preview (first 5 + last 10 lines) provides genuine value
- The LLM is unlikely to need the entire output, so selective reading saves tokens
- Commands producing this much output are typically slow enough that re-run prevention matters

### Preview guardrails

The preview (first 5 + last 10 lines) is only shown when it's genuinely useful:
- **Line length guard**: suppressed if any preview line exceeds 200 chars (e.g. minified JSON, base64, CSV rows). Long lines make the preview noise, not signal.
- **Omission ratio guard**: suppressed if the omitted portion is less than 50% of total output. If the preview shows almost everything, it's pointless -- just the file path + keywords is enough.

When the preview is suppressed, the LLM still gets the file path, line count, and keyword summary, which is enough to decide whether to Read the file.

### Why not lower?

- 68.6% of commands produce < 1,000 chars -- wrapping these adds latency for minimal savings
- For outputs under 2,000 chars, the preview would be nearly the full output anyway
- The keyword summary is redundant for small outputs where the LLM can just read everything

### Why not higher?

- At P95 (9,332 chars), we'd miss 5% of commands that contribute significantly to context bloat
- The top 10% of outputs account for a disproportionate share of total context consumption
- Build/test outputs in the 4K-10K range are common and benefit most from buffering
- `git diff` alone averages 7,531 chars per call -- the single largest context consumer

## Key Insights

1. **Context compounding is the main cost driver.** A single large output gets re-sent as input on every subsequent turn, making even moderate outputs expensive over a session.

2. **The re-run prevention value is separate from token savings.** Even if the token math is marginal, preventing a 60-second build from being re-run is worth it in wall-clock time.

3. **The LLM often doesn't need full output.** Build logs, test results, and query outputs usually only need the error/failure section. The preview (first 5 + last 10 lines) plus keyword summary covers most cases.

4. **Prompt caching helps but doesn't eliminate the problem.** Cached reads cost 0.1x, so a 2,500-token output re-sent 20 times costs $0.015 instead of $0.15. Still non-trivial at scale.

5. **MCP tool definitions are a separate problem.** 55K+ tokens of tool definitions before the conversation starts is a fixed cost that llm-toto doesn't address.
