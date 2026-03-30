---
description: Fix MR comment issues (unresolved and missed comments)
allowed-tools: ["Bash(${CLAUDE_PLUGIN_ROOT}/scripts/fetch-mr-state.sh:*)", "Bash(glab-discussion:*)"]
---

## Context

```!
"${CLAUDE_PLUGIN_ROOT}/scripts/fetch-mr-state.sh" --comments
```

## Your task

The discussions have been dumped by `glab-discussion` into per-thread files in the discussions directory listed above.
Read the discussion files to understand each thread, then analyze and propose what to do about them. No implementation yet.

### 1. Unresolved Comments
Review all unresolved discussion threads:
- For each unresolved comment, understand what is being requested
- Propose what to do about each one (fix code, respond, or explain why no action needed)

### 2. Resolved Comments Verification
Review resolved comments as well because:
- Some problems marked as resolved might not actually be fixed
- AI reviewers and other automated tools sometimes post comments that appear in "resolved" instead of "unresolved"
- Look for any actionable feedback that may have been missed

### 3. Interacting with Discussions

Each discussion file includes the `Discussion:` ID in its header. Use `glab-discussion` to interact:

**Reply to a discussion:**
```bash
glab-discussion write --reply-to <discussion_id> --body "Your reply"
```

**Resolve a discussion:**
```bash
glab-discussion resolve <discussion_id>
```

**Add a diff note on a specific line:**
```bash
glab-discussion write --file <path> --new-line <n> --body "Comment"
```

$ARGUMENTS
