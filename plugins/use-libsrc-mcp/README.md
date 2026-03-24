# use-libsrc-mcp

Blocks attempts to extract or inspect source code from dependency cache directories (`~/.m2/repository`, etc.) and redirects Claude to use the `mcp__libsrc__get_library_sources` MCP tool instead.

## Why

Claude sometimes tries to inspect dependency sources by extracting JARs from `~/.m2/repository` — running `jar tf`, `unzip -p`, or reading `.java`/`.class` files directly. This is fragile, slow, and wastes tokens.

The `libsrc` MCP server provides a proper API: it resolves project dependencies, clones source repos at the correct version, and returns local filesystem paths for inspection.

## What gets blocked

A `PreToolUse` hook on `Bash|Read` checks tool input against blocked path patterns:

**Bash** — only archive extraction commands are blocked:
- `jar` (tf, xf, etc.)
- `unzip`
- `zipinfo`

**Read** — only source/binary file extensions are blocked:
- `.java`, `.class`, `.jar`

**Allowed through** (even when referencing `.m2/repository`):
- Reading POMs and XML files (`cat`, `grep`, `Read`)
- Checking cache presence (`ls`, `find`)
- Cache cleanup (`rm`, `rm -rf`)
- `Glob` and `Grep` tools (no restrictions)

## Adding more blocked paths

Edit `scripts/check-blocked-paths.sh` and add entries to the `BLOCKED_PATTERNS` array.

## Testing

```bash
bash scripts/test-check-blocked-paths.sh
```
