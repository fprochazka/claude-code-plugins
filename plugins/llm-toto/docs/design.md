# llm-toto Design Proposal

**llm-toto** = LLM Tool Output Tokens Optimizer

A Claude Code plugin that reduces token consumption and prevents wasteful command re-runs by buffering large command outputs to files and providing the LLM with compact summaries.

## Problems Solved

### 1. LLMs re-run slow commands instead of saving output

Without intervention, LLMs tend to:
1. Run `./mvnw package` (60 seconds)
2. See the output is large, decide to look for errors
3. Run `./mvnw package 2>&1 | grep ERROR` (another 60 seconds)
4. Want to see more context around the error
5. Run `./mvnw package 2>&1 | grep -A 5 ERROR` (another 60 seconds)

With llm-toto:
1. Run `llm-toto ./mvnw package` (60 seconds, output saved to file)
2. LLM sees: file path + keyword summary + preview (first 5 + last 10 lines)
3. LLM reads specific sections of the saved file using Read tool (instant)

### 2. Large outputs fill the context window

Every token of command output stays in the conversation context and is re-sent on every subsequent turn. A 10K-char output (~2,500 tokens) re-sent across 20 turns costs the equivalent of 50K input tokens. Buffering to file replaces this with ~30 tokens of summary.

## Architecture

### Components

```
plugins/llm-toto/
├── .claude-plugin/
│   └── plugin.json          # Plugin manifest
├── scripts/
│   └── llm-toto.py          # Main CLI tool
├── hooks/
│   ├── hooks.json           # Hook configuration
│   └── rewrite-bash.py      # PreToolUse hook script
├── docs/                    # Research and design docs
└── README.md
```

### Flow

```
Claude Code wants to run: ./mvnw package 2>&1 | grep ERROR

1. PreToolUse hook fires
   - Input: {"tool_name": "Bash", "tool_input": {"command": "./mvnw package 2>&1 | grep ERROR"}, "session_id": "abc123"}
   - Hook detects: base command is `./mvnw` (should be wrapped)
   - Hook detects: trailing pipe `| grep ERROR` and `2>&1` (should be stripped)
   - Hook outputs: {"hookSpecificOutput": {"updatedInput": {"command": "llm-toto --session abc123 -- ./mvnw package"}}}

2. llm-toto runs `./mvnw package`
   - Captures stdout+stderr (via subprocess, no 2>&1 needed)
   - Output is 8,500 chars (above 4,000 char threshold)
   - Saves full output to /tmp/llm-toto/abc123/1739445600.txt
   - Prints summary to stdout:

     Output buffered to /tmp/llm-toto/abc123/1739445600.txt (312 lines)
     Keyword mentions: error 3, warning 12, fail 1

     Preview:
     [INFO] Scanning for projects...
     [INFO] Building order-service 2.4.1
     [INFO] --------------------------------
     ...
     [ERROR] Tests run: 145, Failures: 1, Errors: 0
     [INFO] BUILD FAILURE
     [INFO] Total time: 58.234 s
     [INFO] --------------------------------
     [ERROR] Failed to execute goal ...
     [ERROR]   OrderServiceTest.testCancel:145
     [INFO] --------------------------------

3. Claude Code sees the compact summary
   - Knows there are errors (keyword mentions)
   - Sees the tail with failure details (preview)
   - Can Read the file with offset/limit for more context
   - Does NOT need to re-run the 60-second build
```

### Small Output Flow

```
Claude Code wants to run: git status

1. PreToolUse hook fires
   - Hook detects: `git status` (should be wrapped)
   - Rewrites to: llm-toto --session abc123 -- git status

2. llm-toto runs `git status`
   - Output is 450 chars (below 4,000 char threshold)
   - Prints output directly to stdout (no file, no summary)
   - Behaves as if llm-toto wasn't there

3. Claude Code sees the normal git status output
```

## CLI Design

### Usage

```
llm-toto [--session SESSION_ID] [--threshold CHARS] <command...>
```

### Arguments

- `command...` -- The command to run (everything after options)
- `--session` / `-s` -- Session ID for organizing output files (default: "default")
- `--threshold` / `-t` -- Char threshold for buffering (default: 4000)

### Behavior

1. Run the command, capturing combined stdout+stderr
2. Preserve and propagate the command's exit code
3. If output size <= threshold: print output as-is
4. If output size > threshold:
   a. Save full output to `/tmp/llm-toto/<session-id>/<timestamp>.txt`
   b. Count lines matching keywords (case-insensitive): `exception`, `error`, `fail`, `warn`
   c. Print summary (always): `Output buffered to <file> (<N> lines)` + keyword mentions
   d. Print preview (conditionally): first 5 + last 10 lines, **only if**:
      - No preview line exceeds 200 chars (suppressed for minified JSON, base64, CSVs, etc.)
      - The omitted portion is at least 50% of total output (otherwise preview shows almost everything, making it pointless)
      ```
      Output buffered to <file> (<N> lines)
      Keyword mentions: <keyword> <count>, ...

      Preview:
      <first 5 lines>
      ... (N lines omitted) ...
      <last 10 lines>
      ```

### Exit Code

llm-toto always propagates the wrapped command's exit code. If the command exits with non-zero, llm-toto exits with the same code. The summary is still printed regardless of exit code.

## Hook Design

### What gets rewritten

The PreToolUse hook rewrites Bash tool calls where the base command (before any pipes) is NOT a simple file operation.

**Do NOT rewrite (passthrough list):**
- `cat <file>`, `head <file>`, `tail <file>`, `less <file>`, `more <file>`
- `grep <pattern> <specific-file>` (without `-r` or `-R`)
- `sed` / `awk` on specific files
- `echo`, `printf`
- `mkdir`, `cp`, `mv`, `rm`, `chmod`, `chown`, `ln`, `touch`
- `cd`
- `git add`, `git commit`, `git push`, `git checkout`, `git stash`, `git switch`, `git restore`, `git rebase`, `git merge`, `git cherry-pick`, `git tag`
- `source`, `.`, `export`, `eval`
- `pip install`, `npm install`, `yarn add`, `pnpm add`, `uv pip install`
- `docker build`, `docker push`
- Commands already prefixed with `llm-toto`

**Rewrite everything else**, including:
- Build tools: `make`, `mvnw`, `gradle`, `cargo`, `go build`
- Test runners: `pytest`, `jest`, `vitest`, `cargo test`, `go test`, `mvnw test`
- Git read operations: `git status`, `git diff`, `git log`, `git show`, `git branch`
- Container/cloud: `kubectl`, `docker run`, `docker logs`, `docker exec`, `gcloud`, `aws`, `terraform`
- Search: `find`, `grep -r`, `rg` (recursive)
- CLI tools: any MCP CLI, `glab`, `gh`, `curl`, `wget`
- Package managers (run/exec): `npx`, `pnpm exec`, `yarn run`
- Interpreters: `python3`, `node`, `ruby`

### Pipe and redirect stripping

When the hook detects a trailing filter pipe or `2>&1` redirect on a wrappable command, it strips them (llm-toto captures stderr natively via subprocess):

```
Input:  ./mvnw package 2>&1 | grep ERROR | head -20
Output: llm-toto --session abc123 -- ./mvnw package
```

Detected filter pipes (at the end of command):
- `| grep ...`
- `| tail ...`
- `| head ...`
- `| awk ...`
- `| sed ...`
- `| wc ...`
- `| sort ...`
- `| uniq ...`
- `| cut ...`

**Not stripped** (semantic pipes where the pipe provides input or transforms data):
- `echo "data" | command` (pipe before the main command)
- `command | python3 -c "..."` (pipe to interpreter for processing)
- `command | jq .` (structured data transformation)
- `command1 && command2` (command chaining, not piping)

### Session ID passing

The hook extracts `session_id` from the hook input JSON and passes it via `--session`:

```python
session_id = hook_input.get("session_id", "default")
# Rewritten command:
f"llm-toto --session {session_id} -- {base_command}"
```

## Prior Art: rtk (Rust Token Killer)

See `docs/rtk-comparison.md` for detailed comparison.

**Key differences from rtk:**
- rtk does command-specific compression (24+ hand-crafted modules in Rust)
- llm-toto does generic size-based buffering (single Python script)
- rtk's compressed output is immediately actionable (no extra Read call)
- llm-toto captures full raw output for selective reading
- rtk requires ongoing maintenance per command type
- llm-toto is generic and works for any command
- llm-toto solves the re-run problem (output saved to file); rtk doesn't

## Configuration

Default threshold: 4,000 chars (~1,000 tokens, ~100 lines of typical output).

Configurable via:
- CLI flag: `--threshold 8000`
- Environment variable: `LLM_TOTO_THRESHOLD=8000`

## File Organization

Output files are stored at:
```
/tmp/llm-toto/<session-id>/<timestamp>.txt
```

- Session-scoped directories group related outputs
- Timestamp-based filenames prevent collisions
- `/tmp/` ensures automatic cleanup on reboot
- No explicit cleanup needed (OS handles it)

## Future Improvements

- Configurable keyword list
- Token estimation reporting (like rtk's gain tracking)
- Integration with context compaction (PreCompact hook to preserve file references)
- Smarter preview: detect error sections and show those instead of mechanical first/last lines
