# DAG — `masc__clean_xcoms`

**File:** `dags/masc__clean_xcoms.py`
**Tags:** `masc`, `maintenance`
**Schedule:** None (manual trigger only)
**Catchup:** disabled

---

## Purpose

Purges all XCom entries from the Airflow metadata database. XComs accumulate over time as DAGs push return values between tasks — the `lasc__seed_data` DAG in particular stores large lists (container metadata, user IDs, zone IDs) that can bloat the `xcom` table. This DAG clears them in bulk.

---

## When to run

- After a `lasc__seed_data` run to reclaim metadata DB space (seed data pushes ~2 000-item lists via XCom)
- Periodically as part of cluster maintenance
- Before a re-seed to avoid stale XCom values being pulled by a new run

---

## Task Graph

```
start ──► clean_xcoms ──► end (ALL_DONE)
```

---

## Tasks

### `start`
Empty marker task. Entry point of the DAG.

---

### `clean_xcoms`
**Operator:** `PythonOperator`

Deletes every row from the `xcom` table by querying the Airflow ORM directly via `create_session()` (a SQLAlchemy session against the metadata database). Prints the count of deleted entries to the task log.

```python
with create_session() as session:
    count = session.query(XCom).delete()
print(f"[INFO] Deleted {count} XCom entries.")
```

This bypasses the Airflow REST API and acts directly on the metadata DB — all DAGs, all runs, all keys are deleted.

---

### `end`
Empty marker task. `TriggerRule.ALL_DONE`.

---

## Notes

- No parameters — the operation is unconditional
- No retries configured (`retries: 0`)
- Irreversible: deleted XComs cannot be recovered. Only run this when old XCom data is no longer needed
