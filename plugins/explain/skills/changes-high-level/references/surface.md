# Stage 1: the surface scan

You answer one question, fast: which areas of the code does the change touch, or would it touch, and which files in each carry a cross-system contract. Your list of contract files becomes the deep dives' checklist, so a contract file you miss can drop out of the page. Budget: 2 minutes. Run `date +%s` when you start and again after each step; when 2 minutes have passed, stop and write what you have.

## What counts as a contract file

A file that declares or uses something another system, another deploy, or stored data depends on: a schema migration, an entity or other mapping to a table, a schema dump, a hand-written query; a queue, exchange, topic or binding declaration, a listener, a publisher, a message class; a served endpoint, an HTTP client of another service, an API spec, a request or response class; a configuration key, feature flag or environment variable another system sets or reads; a scheduled job; a file, cache key or event another system reads. When in doubt, list it: a deep dive marks it "no contract change" in seconds, while a missed file is a hole in the page.

## How

**With a diff** (`REVIEW_BASE` and `REVIEW_HEAD` in your prompt), in the code tree:

1. `git diff --name-status` and `git diff --numstat` over `REVIEW_BASE...REVIEW_HEAD`. The changed paths usually name the contract files outright.
2. Look at the directory layout around the changed files to find module, package and service boundaries.
3. For changed files whose path says nothing, use `git diff -G'<pattern>' --name-only` with the declarations of the stack the repository uses.
4. You may read the first 40 lines of a file to place it.

**Without a diff,** grep the code tree for the objects in the **Named objects** section of `change.md`; the files you find are the files the change would touch.

**With no code in reach,** write the map with the areas as the source describes them (the systems or topics it names), an empty `contract-files.json` (`[]`), and return at once.

## Do not

- read whole files, or the full diff of files that carry no contract;
- follow callers, callees or imports beyond the files you place;
- read the source, its comments or threads (the intake does that at the same time);
- read another service's clone; the deep dives do that for the far side of an interface;
- spawn subagents;
- explain anything. Explaining is the deep dives' job.

## Write `WORK/surface-map.md`

- **Areas.** The subdomains or services the change touches, named in the domain's terms (`invoicing`, `shipments`), taken from module, package or service boundaries where the code has them. Each changed or matched file belongs to exactly one area. Tests, build files and generated code go to the area they serve, or to `other`. Generated code, lockfiles, vendored code and snapshots are listed and never read.
- **Per area:** its packages with their changed-file counts and `+/-` lines, and its contract files with their kind.
- **Shared objects.** An object two areas change (one migration that alters a table both use) is assigned to one area and listed under the other as "also used".
- **Proposed deep dives.** One per area that has logic or a contract change. An area with only tests, renames, formatting or generated files is "surface only".

## Write `WORK/contract-files.json`

Every contract file, one object each, valid against `$defs/contract_files` in `scripts/contracts.schema.json` of this skill; `scripts/fixtures/contract-files.json` is an example. `kind` is one of: `migration`, `entity`, `schema dump`, `query`, `queue declaration`, `listener`, `publisher`, `controller`, `http client`, `api spec`, `config`, `scheduled job`, `other`.

## Reply

The two paths, then one line per proposed deep dive: the area, its changed lines (or matched files without a diff), and its contract-file count. Then the "surface only" areas.
