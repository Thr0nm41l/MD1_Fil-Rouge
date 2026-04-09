# Airflow 3 — Using a PostgreSQL connection in a DAG

## 1. Register the connection in the UI

Go to **Admin → Connections → +** and fill in:

| Field           | Value                                                 |
|-----------------|-------------------------------------------------------|
| Connection Id   | `ecotrack_postgres`                                   |
| Connection Type | `Postgres`                                            |
| Host            | `postgres-service` (K8s service name, or `localhost`) |
| Schema          | `Ecotrack`                                            |
| Login           | `postgres`                                            |
| Password        | your password                                         |
| Port            | `5432`                                                |

Save. The connection is now available to all DAGs via its **Connection Id**.

---

## 2. Use it in a DAG with `PostgresHook`

`PostgresHook` is the standard way to interact with a Postgres connection inside a task.
It resolves the credentials from the connection registered above — no hardcoded values in the DAG.

```python
from airflow.providers.postgres.hooks.postgres import PostgresHook

CONN_ID = "ecotrack_postgres"

def my_task_function():
    hook = PostgresHook(postgres_conn_id=CONN_ID)

    # Option A — run a query and get results
    records = hook.get_records("SELECT COUNT(*) FROM public.fill_history")
    print(records)

    # Option B — get a raw psycopg2 connection (useful for bulk inserts)
    conn = hook.get_conn()
    with conn.cursor() as cur:
        cur.execute("CALL public.aggregate_hourly(%s)", (some_timestamp,))
    conn.commit()
    conn.close()

    # Option C — run a statement directly
    hook.run("CALL public.aggregate_daily(%s)", parameters=(some_date,))
```

---

## 3. Full DAG example — Airflow 3 style

Airflow 3 uses the `@task` decorator as the preferred pattern.

```python
from datetime import datetime, timedelta

from airflow.decorators import dag, task
from airflow.providers.postgres.hooks.postgres import PostgresHook

CONN_ID = "ecotrack_postgres"


@dag(
    dag_id="aggregate_hourly",
    schedule="@hourly",
    start_date=datetime(2025, 1, 1),
    catchup=False,
    default_args={"retries": 2, "retry_delay": timedelta(minutes=5)},
    tags=["ecotrack", "etl"],
)
def aggregate_hourly_dag():

    @task
    def run_hourly_aggregation(execution_date=None):
        """
        Calls the aggregate_hourly stored procedure for the current execution hour.
        The procedure is idempotent — safe to re-run on failure.
        """
        # Truncate to the hour
        target_hour = execution_date.replace(minute=0, second=0, microsecond=0)

        hook = PostgresHook(postgres_conn_id=CONN_ID)
        hook.run(
            "CALL public.aggregate_hourly(%s)",
            parameters=(target_hour,),
        )

    run_hourly_aggregation()


aggregate_hourly_dag()
```

```python
@dag(
    dag_id="aggregate_daily",
    schedule="0 1 * * *",   # every day at 01:00
    start_date=datetime(2025, 1, 1),
    catchup=False,
    default_args={"retries": 2, "retry_delay": timedelta(minutes=10)},
    tags=["ecotrack", "etl"],
)
def aggregate_daily_dag():

    @task
    def run_daily_aggregation(execution_date=None):
        """
        Calls the aggregate_daily stored procedure for the previous calendar day.
        Runs after all hourly aggregations are done (01:00).
        """
        target_day = (execution_date - timedelta(days=1)).date()

        hook = PostgresHook(postgres_conn_id=CONN_ID)
        hook.run(
            "CALL public.aggregate_daily(%s)",
            parameters=(target_day,),
        )

    run_daily_aggregation()


aggregate_daily_dag()
```

---

## 4. Bulk insert with `execute_values`

When you need high-throughput inserts (e.g. ingesting IoT data), get the raw
`psycopg2` connection from the hook and use `execute_values` directly.

```python
import psycopg2.extras
from airflow.providers.postgres.hooks.postgres import PostgresHook

@task
def ingest_iot_batch(rows: list):
    """
    rows: list of tuples (container_id, device_id, fill_rate, temperature, battery_pct, measured_at)
    """
    hook = PostgresHook(postgres_conn_id=CONN_ID)
    conn = hook.get_conn()
    try:
        with conn.cursor() as cur:
            psycopg2.extras.execute_values(
                cur,
                """
                INSERT INTO public.fill_history
                    (container_id, device_id, fill_rate, temperature, battery_pct, measured_at)
                VALUES %s
                ON CONFLICT DO NOTHING
                """,
                rows,
                page_size=10_000,
            )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
```

---

## 5. Use `PostgresOperator` for plain SQL files

If the task is just executing a SQL file with no Python logic, use `PostgresOperator`.

```python
from airflow.providers.postgres.operators.postgres import PostgresOperator

check_partitions = PostgresOperator(
    task_id="check_partitions",
    postgres_conn_id=CONN_ID,
    sql="sql/check_partitions.sql",   # path relative to the DAGs folder
)
```

---

## 6. Test the connection from the CLI

```bash
# Inside the Airflow pod / container
airflow connections test ecotrack_postgres

# Or run a one-off query
airflow tasks test <dag_id> <task_id> <execution_date>
```

---

## Required provider package

```bash
pip install apache-airflow-providers-postgres
```

In the Helm chart, add it to the `extraPipPackages` list in `values.yaml`:

```yaml
extraPipPackages:
  - apache-airflow-providers-postgres
```
