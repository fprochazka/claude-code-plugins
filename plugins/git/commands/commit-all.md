---
allowed-tools: Bash(git status:*), Bash(git branch:*), Bash(git log:*), Bash(git diff:*), Bash(git add:*), Bash(git commit:*)
description: Commit all pending changes following the git-workflow skill rules
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

### Changed files (staged and unstaged)

```
!`git diff HEAD --numstat`
```

## Your task

Load the `git-workflow` skill and commit all pending changes (both staged and unstaged) according to its rules — atomic commits, refactor-first ordering, test-before-bugfix, etc. Read file diffs as needed via `git diff HEAD -- <path>` before staging. Split into multiple commits if the changes don't belong in a single atomic unit.

$ARGUMENTS
