# Bash Tool Call Patterns Analysis

> **Dataset:** 12,063 bash tool calls across 516 sessions (1,623 transcript files) from `~/.claude/projects/`.
> **Date range:** 2026-01-01 to 2026-02-13.
> **Last updated:** 2026-02-13.

## Command Frequency

| Rank | Command Category | Count | Avg Output (chars) | Max Output (chars) |
|------|-----------------|-------|---------------------|---------------------|
| 1 | MCP/custom CLI tools (DB, API, observability, docs) | 2,968 | 2,871 | 128,957 |
| 2 | Build tools (`mvnw`, `make`, `gradle`, etc.) | 908 | 2,755 | 30,030 |
| 3 | Test runners | 812 | 2,095 | 21,342 |
| 4 | Package managers (`pip`, `uv`, `poetry`) | 654 | 2,228 | 825,256 |
| 5 | `git diff` | 628 | 7,531 | 489,352 |
| 6 | `ls` | 531 | 925 | 27,861 |
| 7 | `grep` / `rg` | 506 | 3,352 | 67,227 |
| 8 | `git log` | 476 | 838 | 24,710 |
| 9 | `git` (other subcommands) | 418 | 1,459 | 101,049 |
| 10 | `git status` | 405 | 630 | 13,696 |
| 11 | `kubectl` / `helm` | 397 | 1,343 | 30,030 |
| 12 | `git add` | 371 | 258 | 7,225 |
| 13 | File read (`cat`, `head`, `tail`) | 359 | 3,350 | 168,317 |
| 14 | GitLab CLI (`glab`) | 302 | 3,203 | 188,945 |
| 15 | `find` | 281 | 1,560 | 22,265 |
| 16 | `git show` | 257 | 2,616 | 69,447 |
| 17 | Filesystem ops (`mkdir`, `cp`, `mv`, `rm`) | 201 | 2,657 | 63,385 |
| 18 | `python3` (inline scripts) | 145 | 1,382 | 15,235 |
| 19 | `git commit` | 144 | 470 | 4,535 |
| 20 | GitHub CLI (`gh`) | 104 | 1,307 | 53,564 |
| 21 | `git push` | 70 | 348 | 1,043 |

Total git commands (all subcommands): 2,935 (24.3% of all Bash calls), avg output 2,537 chars.

## Output Size Distribution

| Metric | Value |
|--------|-------|
| Count | 11,561 |
| Mean | 2,318 chars |
| Median (P50) | 280 chars |
| P75 | 1,558 chars |
| P90 | 4,835 chars |
| P95 | 9,332 chars |
| P99 | 26,557 chars |
| Max | 825,256 chars |

### Size Buckets

| Range | Count | Percent |
|-------|-------|---------|
| 0-100 chars | 2,042 | 17.7% |
| 100-500 chars | 4,776 | 41.3% |
| 500-1,000 chars | 1,114 | 9.6% |
| 1,000-2,000 chars | 1,106 | 9.6% |
| 2,000-5,000 chars | 1,406 | 12.2% |
| 5,000-10,000 chars | 581 | 5.0% |
| 10,000-20,000 chars | 328 | 2.8% |
| 20,000-30,000 chars | 119 | 1.0% |
| >30,000 chars | 89 | 0.8% |

68.6% of all commands produce fewer than 1,000 chars. Only ~4.6% exceed 10K chars. Claude Code truncates outputs at ~30K chars, but 0.8% of outputs still exceed that threshold before truncation.

## Re-Run Patterns

### Exact Repeats (same command multiple times in a session)

164 out of 516 sessions (31.8%) contain at least one repeated command. Total re-run instances: 2,111.

| Repeat Instances | Command Category |
|-------|-------------|
| 468 | Test runners (re-running after code fixes) |
| 380 | Build tools (rebuild after changes) |
| 257 | `git status` (checking state repeatedly) |
| 242 | Package managers (dependency resolution retries) |
| 176 | `git` (other subcommands) |
| 116 | MCP/custom CLI tools |
| 105 | `git diff` |
| 72 | `git log` |
| 48 | `sleep` (waiting loops) |
| 29 | `kubectl` |

### Same-Tool Variant Patterns

Commands of the same category but with different arguments within a session:

| Variant Instances | Tool | Example Pattern |
|-------|------|----------------|
| 2,006 | MCP/custom CLI tools | Exploration workflow: `list` -> `get` -> `query` -> refined query |
| 869 | Build tools | Build -> build with different flags/test targets |
| 799 | Test runners | Run test -> fix -> re-run, different test classes |
| 650 | Package managers | Install -> install with different flags/packages |
| 561 | Observability CLI | `search_logs` -> refine query -> different time range |
| 554 | `git diff` | `--staged` -> `--cached` -> specific file paths |
| 479 | `grep` | Iterative search refinement |
| 476 | `ls` | Exploring different directories |
| 396 | `kubectl` | Context switching, namespace exploration |
| 381 | `git log` | Different formats, date ranges, filters |

**Note:** The re-run rate reflects active user intervention to prevent re-runs. Without steering, the AI tends to re-run slow commands with different grep/tail/head variants instead of saving output once and reading it selectively.

## Self-Filtering Patterns

3,219 commands (26.7%) already pipe to `grep`, `tail`, `head`, `wc`, `sort`, or similar.

### Pipe Suffix Distribution

| Suffix | Count |
|--------|-------|
| `\| head` | 1,499 |
| `\| tail` | 927 |
| `\| grep` | 810 |
| `\| sort` | 213 |
| `\| jq` | 150 |
| `\| wc` | 123 |
| `\| uniq` | 78 |
| `\| python3` | 63 |
| `\| sed` | 51 |
| `\| xargs` | 27 |
| `\| tee` | 20 |
| `\| awk` | 17 |
| `\| cut` | 13 |

### Filter Pipe Combinations (base command + pipe)

| Count | Base Command | Filter |
|-------|-------------|--------|
| 604 | Build tools | `\| tail` |
| 302 | `grep` | `\| head` |
| 182 | `kubectl` | `\| grep` |
| 170 | Build tools | `\| grep` |
| 143 | Test runners | `\| tail` |
| 131 | Build tools | `\| head` |
| 129 | `find` | `\| head` |
| 122 | `git diff` | `\| head` |
| 83 | `git log` | `\| head` |
| 75 | `git show` | `\| head` |
| 67 | Package managers | `\| head` |
| 66 | GitLab CLI | `\| jq` |
| 62 | `ls` | `\| head` |
| 62 | `grep` | `\| sort` |
| 61 | `find` | `\| wc` |
| 57 | `grep` | `\| grep` |
| 52 | `kubectl` | `\| head` |

**Important:** Commands with trailing filter pipes should still be wrapped -- the base command is still slow. The hook should strip the pipe and wrap the base command, so the full output is saved for selective reading later.

## Simple File Operations (Should NOT be wrapped)

| Operation | Count | Avg Output | Max Output |
|-----------|-------|-----------|-----------|
| `ls <path>` | 518 | 932 | 27,861 |
| `grep <pattern> <file>` (non-recursive) | 451 | 3,567 | 67,227 |
| `cat <file>` | 281 | 1,916 | 68,090 |
| `head -N <file>` | 42 | 2,285 | 17,246 |
| `tail -N <file>` | 29 | 19,035 | 168,317 |
| `wc <file>` | 21 | 428 | 2,853 |
| `sed` on file | 20 | 2,354 | 16,989 |
| `awk` on file | 17 | 2,364 | 30,032 |
| `diff <file1> <file2>` | 13 | 1,778 | 10,046 |

Total simple file operations: 1,399 out of 12,063 (11.6%).

## Largest Total Context Consumers

Ranked by total chars contributed to context across all calls:

| Total Chars | Count | Avg | Command |
|-------------|-------|-----|---------|
| 4,368,009 | 628 | 7,531 | `git diff` |
| 2,622,725 | 563 | 4,675 | Observability CLI |
| 2,560,345 | 2,019 | 1,271 | MCP/custom CLI tools |
| 2,408,517 | 908 | 2,755 | Build tools |
| 1,695,403 | 812 | 2,095 | Test runners |
| 1,512,088 | 506 | 3,352 | `grep` |
| 1,457,175 | 654 | 2,228 | Package managers |
| 1,115,865 | 359 | 3,350 | File read (`cat`/`head`/`tail`) |
| 1,075,979 | 312 | 3,504 | Project management CLI |
| 916,243 | 302 | 3,203 | GitLab CLI |
| 659,280 | 257 | 2,616 | `git show` |
| 598,226 | 418 | 1,459 | `git` (other) |
| 491,843 | 397 | 1,343 | `kubectl` |
| 486,996 | 531 | 925 | `ls` |
| 425,937 | 281 | 1,560 | `find` |
| 392,514 | 476 | 838 | `git log` |
| 370,318 | 50 | 7,406 | Wiki/docs CLI |

## Timeout Usage

2,754 out of 12,063 commands (22.8%) specify explicit timeouts.

| Timeout Range | Count |
|---------------|-------|
| 0-10s | 13 |
| 10-30s | 473 |
| 30-60s | 415 |
| 60-120s (default) | 252 |
| 120-300s | 1,347 |
| 300s+ | 254 |

The majority of explicit timeouts (48.9%) are in the 120-300s range, indicating long-running operations (builds, tests, deployments) are common and expected.

## Background Execution

77 out of 12,063 commands (0.6%) use `run_in_background=true`. Background execution is rare.

## Largest Individual Outputs

| Output Size | Command |
|-------------|---------|
| 825,256 | Messaging/chat CLI listing conversations |
| 773,573 | `strings` on binary file piped to grep |
| 489,352 | `git diff master...HEAD` (large feature branch) |
| 288,057 | `git checkout` + `git pull` on large deployment repo |
| 258,470 | `git rebase` on large repo |
| 244,213 | `git diff` with path filter on Java source files |
| 188,945 | GitLab MR diff view |
| 168,317 | `tail -100` on large log/scratch file |
| 142,129 | `git diff` piped to `head -3000` |
| 140,347 | `git diff master...HEAD` (another large branch) |
| 135,511 | GitLab MR diff piped to `head -3000` |
| 128,957 | Observability log search query |
| 106,694 | Observability log search (error investigation) |
| 106,507 | Observability log search (refined query) |
| 105,504 | `git diff --staged && git diff` |
| 101,049 | `git diff` on uncommitted changes |
| 100,000 | `curl` API call with large JSON response |
| 94,874 | `git diff` with path filter |
| 84,763 | `tail -500` on CI job log file |
