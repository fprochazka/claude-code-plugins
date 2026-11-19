# Database objects

How to write the tables a change touches into a fragment so the page can draw them as a diff. All examples are invented.

## Before and after

The after state is the base state plus the change. A migration shows only the delta, so take the base state of a touched table from a schema dump at the base when the repository has one, else from the earlier migrations that mention the table (`git grep -l <table> REVIEW_BASE`), else from the entity at the base.

List every column, with its type, nullability, default, key and foreign key (`references`, `table.column`; add `"foreign_key": false` when the reference has no constraint on purpose). Set `dialect` to the database the service runs (`postgresql`, `mysql`, …): the page prints each table as its `CREATE TABLE` statement in that dialect, diffed before and after, with each column's, index's and constraint's `note` as a trailing `--` comment. Keep notes short; they explain, they do not repeat the SQL.

A table the change only reads or writes is `"status": "accessed"`, with its `accesses` (`by` a `Class.method`, `kind`, and `what` in a few words) and without columns. An unchanged table that the reader needs for the relationships (the existing `users` a new `user_roles` points at) is `"status": "unchanged"` with a `note` that says why; the relationships diagram draws it grey.

Tell the three kinds of migration apart, because they render differently:

- **A new table:** the table is `added`, and so is every column, index and constraint.
- **An altered table:** the table is `changed`; the columns the migration adds, drops or alters are `added`, `removed` or `changed` (old values under `was`), and every other column is listed `unchanged`.
- **A data migration** (an UPDATE, INSERT or backfill): the statement goes under `data_changes`, as its `sql` when it is short, else as a one-line `summary`. With no schema change the table is `changed` with every column `unchanged`, and the `operations` chip says what happens to the rows (`backfill over existing rows`).

## What the migration does to the running database

`operations` are chips that state a fact about the migration, not a judgment: `index build`, `table rewrite`, `drops data (legacy_ref)`, `backfill over existing rows`, `adds a NOT NULL column with a default`, `renames a column`. Lock levels are not claimed.

## Cost and rollout

- **cost:** a new table no other system reads is usually `data migration`. Dropping or renaming a column that running code still reads is a `multi-step change` (expand, migrate, contract). A dropped column or table also `drops data`. A table another service reads directly means `other consumers must change`.
- **rollout:** `needs deploy order` when the old code breaks against the new schema or the new code against the old one (a dropped column the old version still writes, a new NOT NULL column without a default the old version does not fill). Say which order in `text`, and how the migration runs: once, or once per tenant database or shard, and whether it is transactional on this database. `rollback` says what rolling back means: harmless for an added table, a down migration, or data that cannot come back.

## Fragment shape

```json
{
  "name": "invoice",
  "area": "invoicing",
  "status": "changed",
  "dialect": "postgresql",
  "lead": "Invoices get a required due date, and legacy_ref is dropped with its data.",
  "source": "migration",
  "ref": "billing/src/main/resources/db/migration/V42__invoice_due_date.sql:1",
  "columns": [
    {"name": "id", "status": "unchanged", "type": "bigint", "nullable": false, "key": "primary key"},
    {"name": "customer_id", "status": "unchanged", "type": "bigint", "nullable": false, "references": "customer.id", "foreign_key": false, "note": "customers live in another service"},
    {"name": "due_date", "status": "added", "type": "date", "nullable": false, "default": "current_date"},
    {"name": "status", "status": "changed", "type": "varchar(32)", "nullable": false, "was": {"type": "varchar(16)"}},
    {"name": "legacy_ref", "status": "removed", "type": "varchar(64)", "nullable": true}
  ],
  "indexes": [{"name": "invoice_due_date_idx", "status": "added", "definition": "(due_date)"}],
  "constraints": [{"text": "check (status <> '')", "status": "unchanged"}],
  "data_changes": [{"sql": "UPDATE invoice SET due_date = issued_on + 30;"}],
  "operations": ["index build", "drops data (legacy_ref)"],
  "cost": {"labels": ["data migration", "drops data"], "text": "Putting legacy_ref back needs a restore from a backup."},
  "rollout": {"label": "needs deploy order", "text": "The old version still writes legacy_ref; migrate after every old instance stopped. Runs once per tenant database.", "rollback": "Code rollback is safe; legacy_ref cannot come back."}
}
```

A changed attribute keeps its new value in place and its old value under `was`.
