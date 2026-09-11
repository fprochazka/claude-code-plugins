# mermaid — diagram types

Both GitLab and GitHub run mermaid 11.16.1, so every type below parses on both. Parsing is not the same as working: the opt-in list at the bottom parses and still produces something you would not put in front of a reviewer.

## The four that cover engineering docs

| Type | Use when | Do not use when | Pitfalls |
|---|---|---|---|
| `flowchart` | A process or decision branches; you are showing the path a request takes through components. The default when nothing more specific fits. | The steps are linear (a list); the point is time-ordered messages between actors (`sequenceDiagram`); you are showing structure rather than flow. | `end` as a node id breaks it; a node id starting with `o` or `x` silently becomes a circle or cross arrow head; punctuation in a label needs quotes; layout degrades past about 15 nodes. Use the `flowchart` keyword, not `graph` — they are documented as interchangeable but render with different colors and spacing. |
| `sequenceDiagram` | Time-ordered interaction between two and six participants: an ordering bug, a retry, a race, an auth handshake. | More than about six participants or twenty messages; the ordering is obvious; you are showing structure rather than a protocol. | `;` in message text must be `#59;`; `end` closes every block so it breaks as a bare word; a missing colon after the arrow is a parse error; activation drifts unless you use `->>+` and `-->>-`. |
| `stateDiagram-v2` | One entity has a lifecycle with named states and guarded transitions: order status, job state, feature-flag rollout, saga. | Two states (a sentence); the "states" are really steps with no return (`flowchart`); the entity is a set of independent flags. | Use `stateDiagram-v2`, never the legacy `stateDiagram`. A state name with spaces needs `state "Label" as id`. `classDef` does not apply to `[*]` or to composite states, and a transition between the internals of two different composite states is not allowed. |
| `erDiagram` | Tables and their cardinality for a schema change: which foreign key points where, what is optional. | The change touches one table (post the DDL); you are describing an object model (`classDiagram`). | Cardinality glyphs are order-sensitive and invert easily. `--` is identifying (solid), `..` is non-identifying (dashed). An attribute type name must start with a letter. |

## Secondary, when they clearly fit

| Type | Use when | Do not use when | Pitfalls |
|---|---|---|---|
| `classDiagram` | Inheritance, composition or realization between types is the point; the shape of a domain model. | You want a list of fields (a table); the code is in the diff and the reader can read it. | Class names take alphanumerics, `_` and `-` only. Generics use `~`, and the docs call a comma inside them unsupported (`Store~K, V~`) — 11.17.0 renders it anyway, so do not build on either behavior. Backticks escape special characters; `[Display Name]` sets a label separate from the id. |
| `gitGraph` | A branching strategy, a rebase or merge plan, what a release train looks like. | Describing this MR's commits — the commit list already does that; more than eight branches, after which the theme's colors repeat. | A branch cannot merge with itself. Cherry-picking a merge commit needs an explicit parent id. `mainBranchName` defaults to `main`, so a `master` repo has to set it in frontmatter. |
| `timeline` | Chronology at a coarse grain: a migration's phases across weeks, an incident's public chronology. | You need durations, dependencies or an axis of dates (that is `gantt`, and a `gantt` in a review is almost always the wrong register); the "timeline" is really a sequence of calls. | Indentation is significant. Each event under a period goes on its own line. |

## Opt-in only — use when the user asks for it by name

- **`C4Context` and the other `C4*` types** — officially experimental, and the syntax "can change in future releases". There is no automatic layout: `Lay_U` and friends are unsupported and placement follows statement order, so output is usually wide and ugly. A labeled `flowchart` with C4-style naming is the better trade. Two levels, context and container, cover most needs anyway.
- **`architecture-beta`** — renders non-deterministically: the same source rendered twice can come out differently. Only five icons (`cloud`, `database`, `disk`, `internet`, `server`) are available, because iconify packs need a `registerIconPacks()` call at init that neither host makes, so cloud-provider icon sets silently break.
- **`block-beta`** — an open v11 regression makes column widths ignore their text content, so labels overflow.
- **`mindmap`** — experimental, and the indentation rule is a trap: an indent level that matches nothing existing is reparented to the nearest ancestor with smaller indentation, so one stray space silently restructures the tree. It can only express a tree — no real edges, no ordering.
- **`packet-beta`, `sankey-beta`, `xychart-beta`, `kanban`, `quadrantChart`, `pie`, `journey`, `requirementDiagram`** — each is narrow enough that the reader needs a legend more than the picture. For a before/after measurement in an MR, a two-row markdown table beats `xychart-beta`: it is readable, and it can be copied.

## The hard ceiling

Mermaid refuses a diagram over `maxEdges: 500` with `NNN edges found, but the limit is 500`. `maxEdges` is a secure config, so a diagram cannot raise it from its own frontmatter and neither host raises it for you. In practice GitLab's 2000-character page budget bites first, and readability bites long before that.
