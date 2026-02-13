---
description: Fix MR comment issues (unresolved and missed comments)
allowed-tools: ["Bash(${CLAUDE_PLUGIN_ROOT}/scripts/fetch-mr-state.sh:*)"]
---

## Context

```!
"${CLAUDE_PLUGIN_ROOT}/scripts/fetch-mr-state.sh" --comments
```

## Your task

Analyze the MR comments above and help fix any issues:

### 1. Unresolved Comments
Review all unresolved discussion threads:
- For each unresolved comment, understand what is being requested
- Propose what to do about each one (fix code, respond, or explain why no action needed)
- Implement fixes where appropriate

### 2. Resolved Comments Verification
Review resolved comments as well because:
- Some problems marked as resolved might not actually be fixed
- AI reviewers and other automated tools sometimes post comments that appear in "resolved" instead of "unresolved"
- Look for any actionable feedback that may have been missed

### 3. Interacting with Discussions

Each comment in the dump includes `Discussion:` and `Note:` IDs. Use these with `glab api` to interact with discussions:

- **Reply to a discussion**: `glab api -X POST "projects/$PROJECT_ID/merge_requests/$MR_IID/discussions/$DISCUSSION_ID/notes" -f body="Your reply"`
- **Resolve a discussion**: `glab api -X PUT "projects/$PROJECT_ID/merge_requests/$MR_IID/discussions/$DISCUSSION_ID" -f resolved=true`

The PROJECT_ID and MR_IID (MR number) are available in the MR info section above.

$ARGUMENTS
