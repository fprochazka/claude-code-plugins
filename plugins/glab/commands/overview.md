---
description: Show MR overview (pipeline status, comments, external statuses)
allowed-tools: ["Bash(${CLAUDE_PLUGIN_ROOT}/scripts/fetch-mr-state.sh:*)", "Bash(glab-pipeline:*)", "Bash(glab-discussion:*)"]
---

## Context

```!
${CLAUDE_PLUGIN_ROOT}/scripts/fetch-mr-state.sh --all
```

## Your task

Report the state of the merge request. Take no action and change no code.

Cover the pipeline, the discussion threads, the external commit statuses, and what blocks the merge right now.

### Reading the pipeline dump

The script already ran `glab-pipeline inspect` for you. Read the pipeline summary file printed above first — it names each failed job, its stage, and its failure reason, and it points at the file that explains it.
Then open only the files the summary names: `job-logs/<failed-job>.log` for a script failure, `test-report.json` for test failures, `lint.json` plus `merged.yml` for a config error, `downstream/<bridge>-<id>.json` for a failed child pipeline.
Do not read the logs of jobs that passed. A green pipeline needs no log at all.

`summary.json` in the same directory holds the same summary as structured data, for `jq` queries.

Invoke the `glab-pipeline` skill before you run the CLI directly, for example to re-inspect after a new push.

### Reading the discussions

`glab-discussion` dumped one file per thread into the discussions directory listed above. Read those files. Do not fetch the discussions again.

$ARGUMENTS
