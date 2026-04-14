# git

Claude Code skill encoding a personal approach to git commits, branches, and merge requests — the *judgment*, not the mechanics.

This is the writing-side counterpart to [`code-review`](../code-review/)'s `review-git-history` agent: same philosophy, applied while building the branch rather than after.

## Installation

```bash
claude plugin marketplace add fprochazka/claude-code-plugins --scope user
claude plugin install git@fprochazka-claude-code-plugins --scope user
```

## Highlights

- **Atomic commits** — each commit solves exactly one thing
- **Refactor-first ordering** — prerequisites and refactorings at the start of the branch, feature/fix code last
- **Test-before-bugfix** — capture broken behavior first, fix in the next commit
- **Fixups for review feedback** — never standalone "address review" commits
- **Plan the history before coding** — cleanup as an afterthought is a waste of time

Full rules and rationale in [`skills/git-workflow/SKILL.md`](skills/git-workflow/).

## What it isn't

Not a git tutorial. It assumes the agent already knows how to drive `git` and teaches **when and why** to reach for each operation, not command syntax.

## License

MIT
