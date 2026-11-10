# teamwork

The team-process conventions that the `sdlc` and `code-review` plugins share, so that neither has to reach into the other for them. It names no tool: the tracker, the git host and their CLIs are resolved at run time and covered by their own skills.

## Installation

```bash
claude plugin marketplace add fprochazka/claude-code-plugins --scope user
claude plugin install teamwork@fprochazka-claude-code-plugins --scope user
```

`sdlc` and `code-review` declare it as a dependency, so installing either installs it.

## Skills

- `teamwork:workflow-identify` — resolves the issue tracker, the team, the ticket ID pattern, the branch convention and the workflow state names, then prints them as one block the calling command carries. Reads `CLAUDE.md` / `AGENTS.md` first, the repo `README.md` second, and asks before it falls back to the tracker API, so the answer gets written down instead of rediscovered every run. It hardcodes no team or status name. See [`skills/workflow-identify/SKILL.md`](skills/workflow-identify/).
- `teamwork:review-handshake` — the protocol between the author side of an MR and the reviewer side: how the ticket state and the draft flag say whose court the ball is in, what each side may do to the other's threads, how a posted comment is signed, where the run ledgers live, and the rule for text addressed to other people. See [`skills/review-handshake/SKILL.md`](skills/review-handshake/).
- `teamwork:mr-state-judge` — how to judge what an MR status read or a watcher event reports: green is `success` alone and only on the current head, a pipeline or verdict on an older head or a superseded base is stale, each AI reviewer is profiled from its own threads and read by its latest verdict, human review is kept apart from the author and bots, and the answer is what blocks the merge right now and whose turn it is. See [`skills/mr-state-judge/SKILL.md`](skills/mr-state-judge/).

## License

MIT
