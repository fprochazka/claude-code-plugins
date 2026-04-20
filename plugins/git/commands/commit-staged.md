---
allowed-tools: Bash(git status:*), Bash(git branch:*), Bash(git log:*), Bash(git diff:*), Bash(git commit:*)
description: Commit only the currently staged changes with an accurate message
disable-model-invocation: true
---

## Context

- Current branch: !`git branch --show-current`

### Git status

```
!`git status`
```

### Recent commits

```
!`git log -n 10 --oneline --abbrev-commit`
```

### Staged files

```
!`git diff --cached --numstat`
```

## Your task

Load the `git-workflow` skill and create a single commit from the files that are **already staged**.

Strict rules:
- Do **NOT** run `git add` — stage nothing, unstage nothing.
- Do **NOT** touch unstaged or untracked files; ignore them entirely.
- Read the staged diff via `git diff --cached -- <path>` as needed to write an accurate message.
- If the staged set spans multiple unrelated concerns, stop and report that back instead of committing — the user is responsible for how they staged it.

$ARGUMENTS
