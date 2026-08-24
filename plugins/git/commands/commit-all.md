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

### Unpushed commits on this branch (fixup candidates)

```
!`git log --oneline @{u}..HEAD 2>/dev/null || echo "(no upstream tracking branch — every commit below is unpushed)"`
```

### Files touched by those unpushed commits

```
!`git diff --name-only @{u}..HEAD 2>/dev/null | sort -u || true; git rev-parse --abbrev-ref @{u} >/dev/null 2>&1 || echo "(no upstream — determine the branch point yourself before ruling out fixups)"`
```

## Your task

Load the `git-workflow` skill and commit all pending changes (both staged and unstaged) according to its rules. Read file diffs as needed via `git diff HEAD -- <path>` before staging.

Work in this order:

1. **Check for fixups first.** For each pending change ask: would one of the unpushed commits above have looked different if you had known this at the time? If yes it belongs inside that commit — `git commit --fixup <sha>`, not a new commit. Repairing, simplifying or rearranging code this branch introduced is a fixup. Adding new work on top of a commit that was correct as written is not, even when it touches the same files.
2. **Apply the sibling/ancestor test to whatever remains.** Ancestors — pieces that only exist because the next one needs them — are one commit, cut vertically through every layer. Siblings — independent, revertible in any order, each meaningful to someone reading `master` who never saw this branch — stay separate.
3. **Order by dependency**: quarantined noise and standalone prerequisites first, payload next, unlocked cleanups and docs last.

Split into multiple commits only where the sibling test justifies it. Do not split by build order.

$ARGUMENTS
