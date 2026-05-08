# DAG — `masc__clean_xcoms`

**File:** `dags/masc__clean_xcoms.py`
**Tags:** `masc`, `maintenance`
**Schedule:** Every Monday at 09:00 UTC (`0 9 * * 1`)
**Catchup:** disabled

---

## Purpose

Purges XCom entries older than 7 days from the Airflow metadata database. XComs accumulate over time as DAGs push return values between tasks — the `lasc__seed_data` DAG in particular stores large lists (container metadata, user IDs, zone IDs) that can bloat the `xcom` table. This DAG prunes them on a weekly basis while keeping the most recent week of data intact.

---

## When to run

Runs automatically every Monday at 09:00 UTC. Can also be triggered manually:

- Before a re-seed to avoid stale XCom values being pulled by a new run
- After an unusually large batch of DAG runs to reclaim metadata DB space ahead of schedule

---

## Task Graph

```
start ──► clean_xcoms ──► end (NONE_FAILED_MIN_ONE_SUCCESS)
```

---

## Tasks

### `start`
Empty marker task. Entry point of the DAG.

---

### `clean_xcoms`
**Operator:** `KubernetesPodOperator`

Spawns a fresh Kubernetes pod (`apache/airflow:3.0.2`, namespace `airflow`) and runs:

```bash
airflow db clean --table xcom -y --skip-archive \
  --clean-before-timestamp '<execution_date - 7 days>T00:00:00+00:00'
```

The cutoff timestamp is templated from the DAG execution date (`{{ macros.ds_add(ds, -7) }}`), so each Monday run deletes everything older than the previous Monday.

The pod reads the database connection and fernet key directly from Kubernetes secrets (`airflow-metadata-credentials` and `airflow-fernet-key`), bypassing the Airflow 3 task worker restriction on direct metadata DB access. The pod is deleted automatically after completion.

---

### `end`
Empty marker task. `TriggerRule.NONE_FAILED_MIN_ONE_SUCCESS`.

---

## Notes

- Keeps a rolling 7-day window of XCom data — entries newer than 7 days are preserved
- `--skip-archive` ensures rows are physically deleted rather than moved to archive tables
- Irreversible: deleted XComs cannot be recovered
- Uses `KubernetesPodOperator` instead of `PythonOperator` because Airflow 3 blocks direct ORM/DB access from task workers
