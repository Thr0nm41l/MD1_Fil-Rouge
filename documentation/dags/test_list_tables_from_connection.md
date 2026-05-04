# DAG — `test_list_tables_from_connection`

**File:** `dags/test_list_tables_from_connection.py`
**Tags:** `test`
**Schedule:** None (manual trigger only)
**Catchup:** disabled
**Max active runs:** 1

---

## Purpose

Validates that a named Airflow PostgreSQL connection is reachable and lists all base tables in a given schema. Useful for confirming that a connection (e.g. `Ecotrack`) is correctly configured after infrastructure setup or credential rotation, without running any write operations.

---

## Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `conn_id` | string | `Ecotrack` | Airflow connection ID — must point to a PostgreSQL connection |
| `schema` | string | `public` | Database schema to inspect |

---

## Task Graph

```
start ──► list_tables ──► end (ALL_DONE)
```

---

## Tasks

### `start`
Empty marker task. Entry point of the DAG.

---

### `list_tables`
**Operator:** `PythonOperator`
**XCom output:** list of table name strings

Connects to the database via `PostgresHook(postgres_conn_id=conn_id)` and queries `information_schema.tables` for all `BASE TABLE` entries in the target schema:

```sql
SELECT table_name
FROM information_schema.tables
WHERE table_schema = %s
  AND table_type = 'BASE TABLE'
ORDER BY table_name
```

Prints the count and each table name to the task log. Returns the list of names as XCom for downstream inspection if needed.

Example output (for schema `public` on a seeded Ecotrack DB):

```
Found 12 table(s) in schema 'public':
  - aggregated_daily_stats
  - aggregated_hourly_stats
  - collections
  - containers
  - device
  - fill_history
  - role
  - signalements
  - teams
  - user_role
  - user_team
  - users
  - zones
```

---

### `end`
Empty marker task. `TriggerRule.ALL_DONE`.

---

## Notes

- Read-only — no writes to the target database
- No retries configured (`retries: 0`)
- Use this DAG after creating or updating an Airflow connection to verify connectivity before running `lasc__seed_data`
