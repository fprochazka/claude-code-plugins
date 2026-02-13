# llm-toto

**LLM Tool Output Tokens Optimizer** -- a Claude Code plugin that reduces token consumption and prevents wasteful command re-runs by buffering large command outputs to files.

## Problem

When using AI coding assistants, two costly patterns emerge:

1. **Large outputs fill the context window.** Every token of command output stays in conversation context and is re-sent on every subsequent turn. A 10K-char build log costs the equivalent of 50K+ input tokens over a session.

2. **LLMs re-run slow commands.** Instead of saving output once and reading specific sections, the AI runs `make build`, then `make build | grep ERROR`, then `make build | tail -50` -- each taking 60+ seconds.

## Solution

A PreToolUse hook intercepts Bash commands and wraps them with `llm-toto`:

- **Small output** (below threshold): printed as-is, no overhead
- **Large output** (above threshold): saved to a file, LLM gets a compact summary with keyword analysis and a preview (first 5 + last 10 lines)
- **Pipe stripping**: `./mvnw package | grep ERROR` is rewritten to `llm-toto ./mvnw package` -- the full output is saved, and the LLM can Read specific sections instead of re-running the build

## How it works

```
Claude wants to run: ./mvnw package 2>&1 | grep ERROR

1. Hook intercepts, strips the pipe and 2>&1, wraps:
   → llm-toto --session <id> -- ./mvnw package

2. llm-toto runs the command, output is 8,500 chars (above threshold)
   → Saves to /tmp/llm-toto/<session>/<timestamp>.txt

3. Claude sees:
   Output buffered to /tmp/llm-toto/.../1739445600.txt (312 lines)
   Keyword mentions: error 3, warning 12, fail 1

   Preview:
   [INFO] Scanning for projects...
   [INFO] Building order-service 2.4.1
   [INFO] --------------------------------
   ... (297 lines omitted) ...
   [ERROR] Tests run: 145, Failures: 1, Errors: 0
   [INFO] BUILD FAILURE
   [INFO] Total time: 58.234 s
   ...

4. Claude reads the file selectively if needed
   → No 60-second re-run required
```

## What gets wrapped

The hook wraps "everything except simple file operations":

**Not wrapped** (passthrough):
- File reads: `cat`, `head`, `tail`, `less`, `wc`
- File management: `mkdir`, `cp`, `mv`, `rm`, `chmod`, `touch`
- Non-recursive grep: `grep pattern file.txt`
- `sed`, `awk`, `sort`, `diff` on specific files
- Shell builtins: `echo`, `printf`, `export`, `cd`, `source`
- Git write ops: `add`, `commit`, `push`, `checkout`, `stash`, `rebase`, `merge`, `pull`
- Package installs: `pip install`, `npm install`, `cargo install`, etc.
- Docker build/push

**Wrapped** (everything else):
- Build tools: `make`, `mvnw`, `gradle`, `cargo build`, `go build`
- Test runners: `pytest`, `jest`, `cargo test`, `go test`
- Git read ops: `status`, `diff`, `log`, `show`, `branch`
- Containers: `kubectl`, `docker run/logs/exec`
- Search: `find`, recursive `grep -r`
- CLI tools: `glab`, `gh`, `curl`, `terraform`, MCP CLIs
- Interpreters: `python3`, `node`

## Configuration

**Threshold** (default: 4000 chars, ~100 lines):

```bash
# Environment variable
export LLM_TOTO_THRESHOLD=8000
```

## Installation

```bash
claude plugin marketplace add fprochazka/claude-code-plugins
claude plugin install llm-toto@fprochazka-claude-code-plugins
```

## Requirements

- Python 3.8+
- No external dependencies (stdlib only)
