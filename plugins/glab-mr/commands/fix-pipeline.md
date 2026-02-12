---
description: Fix MR pipeline issues (failed CI jobs)
allowed-tools: ["Bash(${CLAUDE_PLUGIN_ROOT}/scripts/fetch-mr-state.sh:*)"]
---

## Context

```!
"${CLAUDE_PLUGIN_ROOT}/scripts/fetch-mr-state.sh" --pipeline
```

## Your task

Analyze the MR pipeline state above and help fix any issues:

### Failed CI Jobs
If there are any failed jobs in the pipeline:
- Analyze the job logs to understand what failed
- Fix the issues in the code
- Commit the fixes

If all jobs passed, report the pipeline status and note that no action is needed.

$ARGUMENTS
