---
description: Fix MR pipeline issues (failed CI jobs)
allowed-tools: ["Bash(${CLAUDE_PLUGIN_ROOT}/scripts/fetch-mr-state.sh:*)", "Bash(glab-pipeline:*)"]
---

## Context

```!
${CLAUDE_PLUGIN_ROOT}/scripts/fetch-mr-state.sh --pipeline
```

## Your task

Analyze the MR pipeline state above, no implementation yet.
Help triage any issues by analyzing the logs of any failed jobs and looking up the context and proposing fixes.
If all jobs passed, report the pipeline status and note that no action is needed.

### Reading the pipeline dump

The script already ran `glab-pipeline inspect` for you. Read the dump in this order and stop as soon as you have the cause:

1. **The pipeline summary file** printed above — it names each failed job, its stage, and its failure reason, and it points at the file that explains it. Read it first, never the raw dump directory.
2. **`job-logs/<failed-job>.log`** for a script or runtime failure — the tail carries the error. Read only the logs the summary names. Do not read the logs of jobs that passed.
3. **`test-report.json`** for a test failure — it holds per-test results, which beats grepping a long trace.
4. **`lint.json` and `merged.yml`** for a YAML, `needs`, or config error — they show what GitLab actually parsed.
5. **`downstream/<bridge>-<id>.json`** for a failed child pipeline, then recurse with `glab-pipeline inspect --pipeline-id <id>`.

`summary.json` in the same directory holds the same summary as structured data. Use it when you want to filter with `jq` instead of reading prose.

### Running glab-pipeline yourself

Invoke the `glab-pipeline` skill before you run the CLI directly. Run it again when the dump is stale or incomplete:

- After a retry or a new push, to inspect the new pipeline.
- With `--with-merged-ci-config` when an `include:` resolves differently on the source branch.
- With `--with-test-report` when a test job failed but the report is missing.

Use `glab ci retry <job-name>` to retry a job. `glab-pipeline` inspects only, so it has no retry of its own.

$ARGUMENTS
