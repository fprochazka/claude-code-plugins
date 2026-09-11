# mermaid — broken and fixed

Read this when a render fails. Find the symptom, apply the fix, render again. Every row below was checked against mermaid-cli 11.17.0; the hosts run 11.16.1.

## Parse errors

| Pitfall | Broken | Fixed |
|---|---|---|
| Parentheses or punctuation in a label | `A[Cache (Redis)]` | `A["Cache (Redis)"]` |
| `end` as a node id or a participant name | `A --> end`, `participant end` | `A --> End`, `A --> E["end"]`, `participant E as end` |
| Single-`%` comment | `% note` | `%% note` |
| Wrong arrow | `A -> B` | `A --> B` |
| Missing colon in a sequence message | `A->>B text` | `A->>B: text` |
| Semicolon in sequence message text | `A->>B: k;v` | `A->>B: k#59;v` |
| Surplus deactivation | `deactivate B` with no `activate B`, or a second `-->>-` on the same activation | one `->>+` per `-->>-` |
| Class name with punctuation | `class Foo.Bar!` | alphanumerics, `_` and `-` only |
| Full-width CJK parentheses | `A（text）` | `A("text")` |
| Missing diagram declaration | the file starts with `A --> B` | prepend `flowchart TD` |

The parser reports `Parse error on line N` with a caret, except for two that report differently: a missing declaration gives `UnknownDiagramError: No diagram type detected`, and a surplus deactivation gives `Trying to inactivate an inactive participant (B)`.

## Parses, and is still wrong

These produce a valid diagram that says something you did not mean. Only looking at the picture, or knowing the rule, catches them.

- **`o` or `x` as the first letter of a target node id.** `A---oB` is read as an edge with a *circle head* into `B`, and `A---xB` as an edge with a cross head. The node `oB` never exists. Write `A--- oB` or `A---Ob`.
- **A mis-set cardinality glyph in an `erDiagram`.** `}o--||` and its neighbors are order-sensitive and invert easily, and `--` (identifying, solid) against `..` (non-identifying, dashed) is mixed up just as often.
- **A surplus `activate`** — the opposite of the error above — renders without complaint and leaves an activation bar running to the bottom of the diagram.
- **`<br/>` in a label** parses locally and renders on GitLab, which rewrites it to `<br>` before handing it to mermaid. GitHub has no such shim. Write `<br>`.
- **A trailing `;`** is legal and has been since v0.2.16. It is noise, not a defect; do not spend a round on it.
- **`%%{init: {...}}%%`** still works and is deprecated. Frontmatter `config:` is the current form.
- **A comma inside generics.** The class-diagram docs call `Store~K, V~` unsupported; 11.17.0 renders it as `Store<K, V>` anyway. Do not build on that — rename or drop the second parameter.

## Sequence diagrams

- **`end` terminates every block** — `loop`, `alt` / `else`, `opt`, `par` / `and`, `critical` / `option`, `break`, `rect`. Message *text* may hold the word (`A->>B: end of stream` renders, even inside a `loop`), but a **participant** named `end` is a parse error. Alias it: `participant E as end`.
- **Balance activation structurally.** `->>+` activates the target and `-->>-` deactivates the sender, so the pair cannot drift. Bare `activate` / `deactivate` can, and that is the single most common defect in generated sequence diagrams.
- **A participant name cannot contain a line break.** Alias it: `participant S as Session store`. Where both an inline alias and an `as` alias exist, the `as` alias wins.
- **`box` takes no hex color** — `rgb()`, `rgba()`, `hsl()` or `transparent`.

## Parses, renders, and is unreadable for half the readers

- **A pinned theme is the one that bites.** `config: theme: neutral` (or `default`, `forest`) renders a light diagram for everybody, including the reader in dark mode; `theme: dark` does the mirror on a light page. Every host picks a theme from the reader's colour scheme — GitLab initialises `neutral`, or `dark` when the page carries `gl-dark` — and `theme` is not one of mermaid's secure options, so the diagram's own frontmatter wins. Write no theme.
- **The frontmatter title takes its colour from `textColor`, not `titleColor`.** `titleColor` colours subgraph and cluster labels. Worth knowing before reaching for a variable that cannot fix the thing you are looking at — and the better answer is a markdown heading above the fence, which no theme can make invisible.
- **Only text with no fill behind it is at risk**: the frontmatter title, sequence-diagram message labels, `loop` guards, and the edge lines themselves. Node labels, notes, edge-label boxes and subgraph titles carry their own background and read on either page.

## Escape hatches

- Numeric entities work inside labels where quoting is not enough: `#35;` renders `#`, `#59;` renders `;`.
- A backtick-quoted label is a markdown string: ``A["`**Bold** label`"]`` supports `**bold**`, `*italic*`, real newlines and automatic wrapping.
- Unicode text belongs in double quotes.
- GitLab pushes a source with more than 30 `&` link-chaining characters behind the same "performance issues" warning as an over-long diagram. Write the edges out.
