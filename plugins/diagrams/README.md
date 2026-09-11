# diagrams

Diagrams as code, written to be read by a person in a merge request. Two skills:

- `diagrams:mermaid` — the authoring skill: whether a diagram is worth drawing at all, which of the four useful types to pick, the syntax that survives both the GitLab and the GitHub renderer, the size budget, and the validation loop. This is the skill other commands cite.
- `diagrams:mermaid-validate` — the validator: renders one `.mmd` file with `mmdc`, looks at the PNG, and reports whether the picture is correct and clear. Only the subagent spawned from `diagrams:mermaid` loads it.

Mermaid is the default format because it is the only one that renders with no server and no admin action on GitLab (descriptions, comments, issues, wikis), GitHub and Linear alike. Its layout is weaker than D2 with ELK or PlantUML with Graphviz, and that is the price of the diagram being readable where the review happens.

## Installation

```bash
claude plugin marketplace add fprochazka/claude-code-plugins --scope user
claude plugin install diagrams@fprochazka-claude-code-plugins --scope user
```

The skills need `mmdc` from `@mermaid-js/mermaid-cli` on `PATH`. Nothing installs it for you: when it is missing, the skill proposes the install and stops rather than shipping an unvalidated diagram. `skills/mermaid/references/install.md` covers the PATH traps, the Chromium sandbox failure on distros that restrict user namespaces, and the Docker alternative.

## Why a separate validator skill

The author writes the diagram and decides what it says. The validator renders it and says what it sees. Splitting them keeps the render output, the Chromium noise and the pitfall table out of the authoring context, and it keeps the validator small enough that it cannot recurse into spawning a validator of its own. After a fix the author messages the same subagent again instead of spawning a new one, so the validator can compare the new picture against the one it already looked at.

One command does both jobs: `mmdc -i x.mmd -o x.png -s 2` fails on a syntax error, which is the lint, and produces the picture, which is the visual check. There is no separate parse step.

## Highlights

- **A diagram is a sketch** — selective, one idea, thrown away when the work lands. Text wins for a linear relationship, for fewer than three nodes, for a payload, and for exact values. If you cannot say in one sentence what the reader should conclude, there is nothing to draw
- **Every arrow carries a verb** — `writes`, `invalidates`, `polls every 30s`. An unlabeled arrow means "related somehow"
- **12 to 15 nodes, then split** — past that, auto-layout stops producing something a reader can follow
- **The GitLab budget is real** — 2000 characters of mermaid per page, shared across every fence on it, and merge-request descriptions and comments are not exempt. Over budget the diagram does not fail: it becomes a yellow performance warning with a button the reader has to click. Keep a diagram under about 700 characters and a page under three of them
- **The host styles the diagram, not you** — GitLab and GitHub both theme it from the reader's light or dark setting, so `classDef` colors are wasted and a pinned `theme:` is worse than wasted: it forces a light diagram onto a dark page, where the title and the sequence-diagram message labels have no background of their own and disappear. The validator renders against a white page and a dark one and reads both
- **Stable types only** — `flowchart`, `sequenceDiagram`, `stateDiagram-v2`, `erDiagram` first, then `classDiagram`, `gitGraph`, `timeline`. Every `-beta` type, every `C4*` type and `mindmap` are opt-in: they parse on both hosts and still render badly

## Not used here

[`probelabs/maid`](https://github.com/probelabs/maid) validates mermaid without a browser, in about 5 MB instead of Chromium's several hundred, and its error messages are written to be fed back to a model. It is the better choice when all you want is "does this parse". This plugin renders instead, because looking at the picture catches what parsing cannot: an arrow pointing the wrong way, a swallowed subgraph, a label that overlaps its neighbor.

## License

MIT
