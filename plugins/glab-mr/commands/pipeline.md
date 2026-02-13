---
description: Fix MR pipeline issues (failed CI jobs)
allowed-tools: ["Bash(${CLAUDE_PLUGIN_ROOT}/scripts/fetch-mr-state.sh:*)"]
---

## Context

```!
"${CLAUDE_PLUGIN_ROOT}/scripts/fetch-mr-state.sh" --pipeline
```

## Your task

Analyze the MR pipeline state above, no implementation yet. 
Help triage any issues by analyzing the logs of any failed jobs and looking up the context and proposing fixes.
If all jobs passed, report the pipeline status and note that no action is needed.

$ARGUMENTS
