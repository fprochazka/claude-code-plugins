# git

Claude Code skill encoding a personal approach to git commits, branches, and merge requests — the *judgment*, not the mechanics.

This is the writing-side counterpart to [`code-review`](../code-review/)'s `review-git-history` agent: same philosophy, applied while building the branch rather than after.

## Installation

```bash
claude plugin marketplace add fprochazka/claude-code-plugins --scope user
claude plugin install git@fprochazka-claude-code-plugins --scope user
```

## Highlights

- **The sibling/ancestor test** — the one rule that decides every commit boundary. Siblings stay separate; ancestors collapse into one commit
- **Vertical-slice atomic commits** — migration + domain logic + endpoint + generated client + UI + tests ship together, because the order work *gets done* is not the order it should be committed
- **Fixups, with a mechanical trigger** — if a change touches a file an unpushed commit already touched, it's a fixup, not a commit
- **Found bug vs introduced bug** — a pre-existing defect earns its own commit; repairing your own draft does not
- **Dependency ordering, not ritual** — prerequisites first only when they *are* prerequisites; never manufacture a refactor commit
- **Plan the history before coding** — write the MR-title sentence first, then ask what is genuinely separate from it

Full rules and rationale in [`skills/git-workflow/SKILL.md`](skills/git-workflow/).

## Commands

- `/git:commit-all` — commits all pending changes (staged and unstaged) following the `git-workflow` skill rules. Will split into multiple atomic commits when appropriate. Pass extra instructions as arguments.
- `/git:commit-staged` — commits **only what is already staged**, without running `git add`. Use when you've hand-picked the staged hunks and just want a good commit message.

## What it isn't

Not a git tutorial. It assumes the agent already knows how to drive `git` and teaches **when and why** to reach for each operation, not command syntax.

## License

MIT
