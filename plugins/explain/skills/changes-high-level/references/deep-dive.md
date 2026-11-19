# Stage 3: a deep dive into one area

You explain one area of a change for a tech lead who judges the parts that are hard to change. You write data, not prose for its own sake: one JSON fragment and at most one Mermaid diagram. Another subagent builds the page from every area's fragment.

Before you write any prose field, load the `prose:technical-writing` skill. Before you write a diagram, load the `diagrams:mermaid` skill for its authoring rules; the deviations for this page are under "Diagram" below.

## Spend the budget in this order

5 minutes. Run `date +%s` when you start and again between steps, and subtract. Spend the time in this order, and when 5 minutes have passed, write the fragment with what you have, even if the later parts are thin:

1. **Interfaces.** Every item on your checklist (the contract files listed for your area under "Deep dives" in `surface-map.md`), then any other database, messaging, HTTP or other cross-system object your area's code changes. Each one complete and in full shape. This is most of the budget.
   - **Meaning, not only shape.** An endpoint or a message whose response is computed by changed code is in scope even when its controller or class did not change. A field whose type is the same but whose value now means something else (a count that now includes other rows, a status with a new cause) is `"status": "semantics changed"`, with the new meaning in its `note`.
   - **Read paths.** When the change adds or moves a read, say in the access's `what` how often it runs and what it scans, and whether it reads a replica: a read right after a write on a replica can miss that write.
2. **Entry points.** Every endpoint, consumer, scheduled job or command in your area that the change adds, changes or removes, under `entry_points`, with one action per table it reads or writes, message it publishes or consumes, and endpoint it calls. The build draws one change-flow diagram per entry point from them, and every box links to its card, so each action's `target` must name an object in `contracts` the way the build keys it (an endpoint as `server POST /path`, a route as `exchange | key | queue`, a boundary as `kind name`). Also list the services your area touches under `services` (the one you work in is `changed`) and the interfaces between them under `service_links`.
3. **Placement.** Per package: what it got, and the classes that sit on an interface.
4. **Internals,** only as far as the reader needs them to understand 1 and 2: the main flow in at most five steps.

A value you cannot settle within the budget is written as unknown with the reason ("the type comes from a shared base class outside this area"), never chased further. Missing an internal detail is acceptable; missing a contract change is not.

## Scope

Read your area's files in full and one hop around them: the direct callers and callees, and the declaration of any table, queue or endpoint involved.

- **With a diff:** "before" is the base (`git show REVIEW_BASE:<path>`), "after" is the head.
- **Without a diff:** "before" is the current code, and "after" is what `change.md` says would change. Mark every such element `"proposed": true`. When the source asks for a change without the detail ("store the reminder date" with no column named), show the current object with the source's sentence as its `note`, and invent no field.
- **With no code in reach:** explain your part from the text alone: the systems named, the decisions and alternatives the source records, and contract changes only as far as the text states them, with `"source": "source text"`.

Do not explore other areas. When your code calls into another area, record the call in `notes.calls` and stop there.

**Other services' clones.** For the far side of an interface your area touches (the consumer of a message it publishes, the server of an endpoint it calls, a contract library it bumps), you may read that service's clone when it is already on disk, found through the user's memory files or next to this clone. Read only: no fetch, no checkout, no worktree, no other write. Record each one under `far_side_reads` with the clone's absolute path, `git -C <clone> rev-parse HEAD`, and what you read there; the page marks it as possibly stale.

**Confirm what the source claims.** `change.md` lists the objects and claims the source names as not confirmed. Find each one your area touches in the code at the head. When you cannot find it, write it with `"source": "source text"` and say in the text that only the source states it ("the description says the frontend stays behind a flag; no such flag is in the code"). Never state a safety net, a flag or a guard as fact on the source's word alone.

For each kind of interface, read the matching reference in this directory: `database.md`, `messaging.md`, `http.md`. Read only the ones your checklist needs. Configuration keys, environment variables, feature flags, scheduled jobs, files, caches and events that another system relies on go into `boundaries`.

## Every interface object

- **`status`:** `added`, `removed`, `changed`, `unchanged` (shown as context), or `accessed` (read or written, not changed). Nested elements (columns, indexes, constraints, payload fields, queue arguments, route elements) carry their own `status`; a changed attribute keeps its new value in place and its old value under `was`.
- **Complete:** every column of a touched table, every field of a changed payload, including the unchanged ones, with `"status": "unchanged"`. The page folds the unchanged ones; the reader can open them. Use `unchanged_columns` or `unchanged_fields` (a count) only when you could not list them within the budget.
- **`lead`:** one sentence a reader can decide on before any detail: what changed and what it means for rollout or the callers ("A new required column with a backfill; the migration must run before the new code"). A fact, not a verdict. Endpoints that get exactly the same change (three list endpoints that share one item type) are one object, with the others under `same_change_on`.
- **Its origin:** `source` (`migration`, `entity`, `schema dump`, `spec`, `declaration`, `code`, `config`, `source text`, `inferred`) and `ref`, a `path:line` at the head, or `base:path:line` at the base, or a quote reference into the source for a proposed change.
- **`cost`: what it takes to change it again later.** One or more labels: `code change only`, `data migration`, `multi-step change` (expand and contract over several deploys or MRs), `downtime or failover`, `other consumers must change`, `drops data`. Add `text` with the concrete reason when it is not obvious: "the broker refuses to redeclare a queue with other arguments".
- **`rollout`: what the change as written does to what is already running.** One label: `backward compatible`, `needs deploy order` (a migration before or after the code, a provider before its consumer), `breaks existing callers`, or `unknown`. Add `text` that names who is affected and how, and `rollback`: what rolling the deploy back does to this object.

Both are descriptions of facts, not verdicts: "drops data (legacy_ref)", never "dangerous". Whether that is acceptable is the reader's call.

## Packages

One entry per package or module the change touches in your area:

- `new_classes`, `changed_classes`, `removed_classes`: counts. Every class that does not sit on an interface is only counted, never listed or described.
- `interface_classes`: by name, only the classes that sit on an interface (a class that never leaves the process, such as an in-process event record, is not one and never a `message`), each with its `role` (`entity`, `migration`, `listener`, `publisher`, `declaration`, `controller`, `client`, `spec`) and its `target`, the interface object it implements (`{"kind": "table", "name": "invoice_reminder"}`). The target must also be in your `contracts`, in full.
- `placement`: one sentence when the placement says something, measured against the service's existing structure: "a new package next to `billing.dunning`, with the same split into service, scheduler and messaging config". Leave it out when the package is an ordinary place for the change.

## Checklist

`checklist` has one entry per contract file on your checklist: `covered` (its objects are in `contracts`), `no contract change` (the file carries a contract but the change does not alter it), or `unknown` with a `note` saying what you could not settle. The build compares it with `contract-files.json` and shows every file that no fragment covered at the top of the page, so do not drop a file in silence.

## Notes

Short, for the render subagent:

- `summary`: one or two sentences on what the area does after the change, or today with where the change would plug in.
- `steps`: the main flow, at most five steps, each with a `ref` and at most one real code excerpt (at most 15 lines) where the code says it better than a sentence. Real code, never pseudocode.
- `crossings`: boundaries the change crosses for the first time ("the first direct call from `shipments` to `customer-service`"). Before you call anything first, new or only, search the base for it (`git grep <pattern> REVIEW_BASE`) and cite the search; when the base already has it, it is not a crossing.
- `dependencies`: new libraries or services the area depends on.
- `calls`: calls into other areas.
- `unknowns`: what you could not settle, and why.

No invented rationale: when the source does not say why, say the reason is not recorded.

## Diagram

Write `WORK/diagrams/<slug>-flow.mmd` only when the area's main flow crosses three or more components: a `sequenceDiagram` (or an `erDiagram` when two or more touched tables reference each other). List its id (`<slug>-flow`) in `diagrams`. Do not render it; the render subagent renders every diagram in one batch. Deviations from `diagrams:mermaid` for this page: the GitLab size budget does not apply, no validator subagent runs, and the 12 to 15 node ceiling stays.

## Write `WORK/subdomain-<slug>.json`

It must validate against `$defs/fragment` in `scripts/contracts.schema.json` (next to `build.py`, one directory up from this file); the schema is the authority for the structure, and `scripts/fixtures/subdomain-*.json` are complete examples. Prose fields take a markdown subset: `` `code` ``, `**bold**` and `[text](https://...)`. The build merges fragments by key (a table and a message by name, a route by exchange, binding key and queue, an endpoint by direction, method and path, a boundary by kind and name, a package by name), so use the same name another area would. Check the fragment yourself before you reply:

```bash
uv run --script <skill dir>/scripts/build.py merge WORK/subdomain-<slug>.json --out /dev/null
```

Every error is printed with its JSON path. Fix them and run it again.

## Reply

The fragment path, the diagram path if any, and the counts: "2 tables, 1 route, 1 message, 3 endpoints, 1 boundary, 4 packages, 1 unknown".
