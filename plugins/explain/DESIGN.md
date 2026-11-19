# explain: design

Read this before you change the plugin. It records why the plugin exists, what it must not become, and what was already tried. A change that contradicts a principle or reverses a decision needs the maintainer's explicit approval and a new entry under [Decisions](#decisions).

## Purpose

A tech lead whose team produces many merge requests, tickets and design documents needs to judge each change on the parts that are hard to change, without reading the source in full. Code is cheap to change. A database schema, a queue topology or an API contract is not: changing it again often needs downtime, a failover, a multi-step sequence over several merge requests, or other teams. The source hides these parts in migrations, nested DTOs and configuration classes, and a ticket or design document is often too dense to read in one pass.

This plugin turns a change into one HTML page the reader can go over instead of the source, with confidence that nothing important is missing. It answers "what is this change", where `code-review` answers "is this change right".

## Goals

- One skill, `explain:changes-high-level`, usable as a command and loaded when the user asks what a change does or asks for a dense ticket or document to be explained.
- Any source the session's tools can read: a merge request, a pull request, the current branch, a ticket, a document, a chat thread, a URL, a file, pasted text. One intake step, then the same stages for every source.
- The page order: a short framing, then a change map (the services involved, and one flow per entry point, with every box linking to its diff), then every interface between systems as a diff with its full shape and its cost and rollout labels, then placement per package (counts, and by name only the classes that sit on an interface), then code internals, last and short. A contract file that no part of the run covered is listed, not dropped.
- The same layout on every page; the length follows the number of contract changes, not the size of the diff.
- About 10 minutes of wall clock for a typical change, about 15 for a large one.
- One self-contained HTML file that works offline in light and dark mode, opened in the user's browser on every run (with the user's own opener when their instruction files name one) and published where the user wants.

## Non-goals and scope

- **Not a review.** No findings, severities, verdicts or suggestions. The cost and rollout labels state facts; whether that is acceptable is the reader's call. Reviews belong to `code-review`.
- **Not a design or a plan.** For a change that is not implemented, the page shows where it lands in today's code and what the source says would differ; it does not fill in the missing design.
- **Changes to a software service only.** A source with no change to code or design in it is out of scope; the run says so and stops.
- **No writes anywhere but the page.** Nothing is posted to a forge, a tracker, a wiki or a chat. No subagent connects to a database, a broker or a running service.
- **No writes to other repositories.** A deep dive may read another service's clone that is already on disk, for the far side of an interface the change touches, and the page names the clone and commit as possibly stale. It never fetches, checks out or adds a worktree there.
- **No catalogue knowledge in the skill.** Which migration tools, ORMs, brokers, frameworks or HTTP libraries exist, and where they keep their files, is what the model already knows or reads from the repository at run time. The references carry only what the model would get wrong without them: what counts as a contract change, how to write it into the fragment so it renders as a diff, and its cost and rollout judgment.

## Principles

1. **Explain, never judge.** Every sentence describes the change or quotes someone.
2. **Interfaces first, complete.** The surface scan's list of contract files is each deep dive's checklist, and the build shows any contract file that no fragment covered at the top of the page.
3. **Only the difference, in the reader's own notation.** A table is its `CREATE TABLE` statement in the service's SQL dialect and a payload a JSON-like structure, each as a unified diff with the notes as aligned trailing comments; long unchanged runs fold and stay one click away. Glyph and color both carry the status. Every card opens with one sentence that says what changed and what it means, so the reader can decide whether to read on.
4. **Facts with their origin.** Every fact cites `path:line` at a pinned SHA, or the sentence in the source. A proposed element is marked as proposed. What could not be read is named as unknown, never guessed.
5. **Fixed layout, generated data.** The page's structure is the JSON Schemas next to `build.py`, and its look is `template.html`. Subagents write JSON and Mermaid that the build validates, never markup.
6. **The page needs nothing at view time.** Diagrams are inline SVG rendered with `mmdc` at build time; a pinned CDN import is the fallback for a missing `mmdc`. The overview diagrams (services, change flows, table relationships) are generated by `build.py` from the fragments, not drawn by a model, so they cannot disagree with the cards they link to.
7. **Split by the problem, not by the concern.** A quick surface scan names the areas; one deep dive per area covers every kind of interface inside it.
8. **Ten minutes, not thirty.** Intake, a surface scan (sonnet, 2 minutes), the driver's decision, at most six deep dives in one parallel wave and never a second (opus, 5 minutes each), and one separate render subagent (sonnet, 2.5 minutes). Budgets are time only; each subagent keeps its own time with `date +%s`. A large change gets grouped areas and more unknowns, never more time per stage. A change that adds a serial step or raises a budget says what it costs in minutes.
9. **The session's own tools.** The intake fetches the source with whatever tool the session has for it, and that tool's skill says which command to prefer. The plugin names no forge or tracker CLI and depends on no CLI plugin.

## Decisions

| Date | Decision | Reason |
|---|---|---|
| 2026-11-19 | After the first test run, from the maintainer's review of its page: budgets in minutes only, kept by each subagent with `date +%s` (no counts of tool calls); a wider page with the prose at the header's width; tables as diffed `CREATE TABLE` statements and payloads as JSON-like diffs, both generated from the structured data; a database tab with a foreign-key diagram; a generated change map whose boxes link to the cards; a one-sentence lead on every card; read-only reads of other services' clones already on disk, for the far side of an interface | The custom column grid was hard to read, a subagent can read a clock with `date`, and a far-side read gave the test page its only complete payload |
| 2026-11-19 | Initial design, from the maintainer's review of the plan: the page order and level of detail above, any source with one intake, four stages with at most six parallel deep dives, the page built by `build.py` from `template.html` and JSON validated by JSON Schema, Mermaid rendered locally by `mmdc`, no dependency on `teamwork`, `glab` or `noisy-tools-in-subagent` (a ticket comes from the tracker tool the memory files name), the page opened locally on every run, no evals, and no catalogue of tools and file conventions in the references | A detailed decision log starts after the first version has been used |

## How changes are checked

`make all`, which runs `test_build.py`: the schemas, the merge and its coverage gaps, the path-located validation errors, the ref check, the fixed section order, the SQL and payload diffs, the generated diagrams and their links, the escaping, the SVG inlining, the offline check, and the time-budget and clone rules in the skill's text, against the invented fixture in `skills/changes-high-level/scripts/fixtures/`. The tests need `jsonschema`, not `mmdc`. A change to `build.py`, a schema or the template also gets a smoke test: run `build.py merge` and `build.py diagrams`, render the `.mmd` files with `mmdc`, run `build.py page` into the scratchpad, and look at the page once in a browser at about 1700 pixels wide, light and dark, and click a diagram box.

There is no eval suite. A change to `SKILL.md` or a reference is checked by the maintainer using the skill on real changes. A session that changes one says so in its summary instead of claiming the change was measured.
