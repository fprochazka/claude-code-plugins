# Comparison: llm-toto vs rtk (Rust Token Killer)

## Overview

Both tools sit between AI coding assistants and shell commands to reduce token consumption. They solve related but distinct problems with fundamentally different approaches.

## Side-by-Side

| Aspect | rtk | llm-toto |
|--------|-----|----------|
| **Core problem** | LLM sees too many tokens from command output | LLM re-runs slow commands + large output fills context |
| **Approach** | Command-specific compression (24+ hand-crafted modules) | Generic size-based buffering with file redirect |
| **Language** | Rust (~4.1MB binary, 46 source files) | Python (single script) |
| **Coverage** | Only supported commands (git, cargo, npm, grep, ls, etc.) | Any command |
| **Output strategy** | Always inline, semantically compressed | Small: inline as-is; Large: save to file + summary |
| **LLM follow-up** | No follow-up needed, compressed info is inline | LLM uses Read tool for details (selective) |
| **Maintenance** | High -- new Rust module per command type | Low -- generic logic, no per-command knowledge |
| **Token reduction** | 60-90% per command (claimed) | Variable: 0% for small, 95%+ for large outputs |
| **Re-run prevention** | No | Yes -- output saved to file for later reading |
| **Pipe handling** | Wraps entire pipeline | Strips trailing filter pipes, captures full raw output |

## Where llm-toto wins

### 1. Solves the re-run problem
rtk compresses output but doesn't save it. If the LLM needs a different view of a build log, it must re-run the command. llm-toto saves the full output to a file -- the LLM can Read specific sections without re-running anything.

### 2. Generic coverage
rtk handles ~24 command families. Any new tool needs a new Rust module. llm-toto works for everything -- custom build scripts, terraform, ansible, database dumps, proprietary CLIs.

### 3. Simpler architecture
No need to understand output formats. The size threshold + keyword scan + preview is broadly applicable.

### 4. Better for truly large outputs
rtk compresses but still puts everything inline. For a 50,000-line build log, even compressed output is huge. Saving to file and letting the LLM selectively read is fundamentally better.

### 5. Full output preservation
rtk's compression is lossy -- it discards information the LLM might need. llm-toto preserves everything in the file; the LLM can always go back and read the full output.

## Where rtk wins

### 1. No extra round-trip
rtk's inline compressed output is immediately actionable. With llm-toto, the LLM must make an additional Read tool call to see details, costing an extra API turn.

### 2. Semantic compression
rtk knows that `git status` output can be reduced to `M 3 files, ? 2 files`. llm-toto's keyword scan (`error 10, warning 5`) is much less informative for small-to-medium outputs.

### 3. Small-output optimization
For commands producing 200-500 tokens, rtk compresses to 20-50 tokens inline. llm-toto passes them through unmodified (below threshold).

### 4. No behavior change required
rtk's output replaces the original seamlessly. llm-toto changes the interaction pattern -- the LLM must learn to Read saved files instead of re-running commands.

## Complementary use

These tools could theoretically coexist:
- rtk for supported commands where semantic compression adds value (git status, test summaries)
- llm-toto for everything else, especially slow commands and unsupported tools

In practice, choosing one is simpler. llm-toto's generic approach covers more ground with less maintenance.

## Implementation complexity

| Metric | rtk | llm-toto |
|--------|-----|----------|
| Source files | 46 | 2 (script + hook) |
| Lines of code | ~15,000+ (Rust) | ~300 (Python) |
| Build process | Cargo (Rust toolchain) | None (Python script) |
| Binary size | ~4.1 MB | N/A (interpreted) |
| Startup overhead | ~5-15ms | ~30-50ms (Python) |
| Dependencies | rusqlite, clap, regex, serde, etc. | Python stdlib only |
