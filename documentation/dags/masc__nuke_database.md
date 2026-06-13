# DAG — `masc__nuke_database`

**File:** `dags/masc__nuke_database.py`
**Tags:** `masc`, `maintenance`
**Schedule:** None (manual trigger only)
**Catchup:** disabled

---

## Purpose

Wipes every table in the target PostgreSQL schema and resets all sequences (auto-increment counters) to their default start values. Intended to put the database back into a pristine, empty-schema state before a fresh seed run.

The single `TRUNCATE … RESTART IDENTITY CASCADE` statement handles foreign-key ordering automatically via `CASCADE` — there is no need to manually sort tables by dependency.

---

## When to run

Manual trigger only. Typical use cases:

- Before re-running `lasc__seed_data` on a database that already contains data, when a clean slate is needed rather than an upsert pass
- Resetting a staging or development database to a known empty state

---

## Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `conn_id` | string | `Ecotrack` | Airflow connection ID — must point to a PostgreSQL connection |
| `schema` | string | `public` | Schema whose tables will be truncated |
| `confirm` | boolean | `false` | **Safety flag** — must be explicitly set to `true` for the nuke to proceed; defaults to `false` so an accidental trigger is a no-op |

---

## Task Graph

```
start ──► check_confirm ──► nuke_database ──► end (NONE_FAILED_MIN_ONE_SUCCESS)
               │
         (short-circuits if
          confirm = false)
```

---

## Tasks

### `start`
Empty marker task. Entry point of the DAG.

---

### `check_confirm`
**Operator:** `ShortCircuitOperator`

Returns `True` (proceed) only when `confirm = true`. If `false` (the default), the operator short-circuits and the downstream `nuke_database` task is skipped. `end` still runs due to `TriggerRule.NONE_FAILED_MIN_ONE_SUCCESS`.

This gate exists to prevent data loss from accidental DAG triggers.

---

### `nuke_database`
**Operator:** `PythonOperator`

1. Queries `pg_class` / `pg_namespace` / `pg_inherits` to discover all top-level tables in the target schema — regular tables (`relkind = 'r'`) and partitioned table parents (`relkind = 'p'`), excluding partition children.
2. Builds and executes a single SQL statement:

```sql
TRUNCATE TABLE "public"."<table1>", "public"."<table2>", ...
RESTART IDENTITY CASCADE;
```

- **`RESTART IDENTITY`** — resets every sequence owned by a column in the truncated tables back to its `START WITH` value (typically `1`). All 25 named sequences in this schema (`role_key_seq`, `users_key_seq`, `fill_history_key_seq`, etc.) are covered.
- **`CASCADE`** — automatically propagates the truncation to any table that has a foreign key referencing the truncated tables, eliminating the need to order truncations manually.
- **Partitioned tables** — `fill_history` is range-partitioned by month (37 partitions as of the current schema). Only the parent is listed in the `TRUNCATE`; PostgreSQL propagates to all monthly children automatically. Partition children are explicitly excluded from the discovery query via `pg_inherits`.

All changes are committed in a single transaction. On any error the transaction is rolled back.

---

### `end`
Empty marker task. `TriggerRule.NONE_FAILED_MIN_ONE_SUCCESS` — runs whether the nuke proceeded or was short-circuited by the safety gate.

---

## Required Airflow Connection

An Airflow connection named `Ecotrack` (or the value passed in `conn_id`) must exist. It must be of type **Postgres** and point to the target database.

---

## Notes

- **Irreversible** — `TRUNCATE` cannot be undone once committed. Ensure the correct `conn_id` and `schema` are set before enabling `confirm`.
- **Seeded lookup tables are also cleared** — `role`, `container_type`, and `badges` contain static seed data inserted by `setup_complete.sql`. The nuke empties them along with everything else. These must be re-seeded (by re-running the relevant `INSERT` blocks of `setup_complete.sql`) before `lasc__seed_data` can run correctly, since it reads `public.role` to assign user roles and expects `container_type` IDs 1–6 to exist.
- The `confirm` parameter defaults to `false` — triggering the DAG without changing the parameter is always a safe no-op.
