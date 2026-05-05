"""
### DAG : lasc__ops_containers

## Purpose:
Applies a bulk operation to a list of containers, triggered via the Airflow
REST API. Designed to be called by external services (e.g. the Ecotrack API)
to reflect real-world operations in the database.

## Trigger:
  POST /api/v1/dags/lasc__ops_containers/dagRuns
  {
    "conf": {
      "type": "battery",
      "date": "2025-05-05",
      "containers": [12, 47, 203]
    }
  }

## Supported operations:
- battery : resets device.battery_pct to 100 for all listed containers
- unload  : resets fill_rate to 2–5 %, inserts one collection row per container

## Behaviour:
- containers: [] → no-op, DAG exits cleanly at validation
- Unknown type  → validation fails with a descriptive error

## Schedule:
None (API-triggered only)
"""

from airflow import DAG
from airflow.providers.standard.operators.python import (
    PythonOperator,
    BranchPythonOperator,
    ShortCircuitOperator,
)
from airflow.providers.standard.operators.empty import EmptyOperator
from airflow.sdk import Param
from airflow.task.trigger_rule import TriggerRule
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import random
import psycopg2.extras
from airflow.providers.postgres.hooks.postgres import PostgresHook

# =============================================================
# Supported operation types
# =============================================================

SUPPORTED_TYPES = ("battery", "unload")

# =============================================================
# Default arguments
# =============================================================

default_args = {
    "start_date": datetime(2025, 1, 21, tzinfo=ZoneInfo("Europe/Paris")),
    "depends_on_past": False,
    "retries": 0,
    "owner": "airflow",
}

# =============================================================
# Helpers
# =============================================================

def log(msg: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def _get_conn(params: dict):
    hook = PostgresHook(postgres_conn_id=params["conn_id"])
    conn = hook.get_conn()
    conn.autocommit = False
    return conn


def _parse_date(date_str: str | None) -> datetime:
    if date_str:
        return datetime.strptime(date_str, "%Y-%m-%d")
    return datetime.now()


def _get_conf(context: dict) -> dict:
    return context["dag_run"].conf or {}

# =============================================================
# Task callables
# =============================================================

def task_validate(**context) -> bool:
    """
    Short-circuits the DAG if containers is empty (no-op).
    Raises ValueError for unknown operation types.
    """
    conf       = _get_conf(context)
    containers = conf.get("containers", [])
    op_type    = conf.get("type", "")

    if not containers:
        log("containers list is empty — no-op")
        return False

    if op_type not in SUPPORTED_TYPES:
        raise ValueError(
            f"Unknown operation type: '{op_type}'. "
            f"Expected one of: {SUPPORTED_TYPES}."
        )

    log(f"Operation '{op_type}' on {len(containers)} container(s) — proceeding")
    return True


def task_branch(**context) -> str:
    conf = _get_conf(context)
    return f"op_{conf['type']}"


def task_op_battery(**context) -> None:
    """
    Resets device.battery_pct to 100 % and updates last_seen for every
    device attached to the listed containers.
    """
    conf       = _get_conf(context)
    containers = conf.get("containers", [])
    op_date    = _parse_date(conf.get("date"))

    conn = _get_conn(context["params"])
    try:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE public.device
                SET battery_pct = 100,
                    last_seen   = %s
                WHERE container_id = ANY(%s)
            """, (op_date, containers))
            log(f"  → {cur.rowcount} device(s) battery reset to 100 %")
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def task_op_unload(**context) -> None:
    """
    For each listed container:
      - reads current fill_rate and capacity
      - inserts one row in public.collections (fill_after 2–5 %)
      - updates containers.fill_rate, status and last_updated directly
    """
    conf       = _get_conf(context)
    containers = conf.get("containers", [])
    op_date    = _parse_date(conf.get("date"))

    conn = _get_conn(context["params"])
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT key_container, fill_rate, capacity_liters
                FROM public.containers
                WHERE key_container = ANY(%s)
            """, (containers,))
            rows = cur.fetchall()

            if not rows:
                log("No matching containers found — nothing to unload")
                return

            collection_rows = []
            update_rows     = []

            for key_container, fill_rate, capacity in rows:
                fill_before = fill_rate or 0.0
                fill_after  = round(random.uniform(2.0, 5.0), 2)
                volume      = round(capacity * fill_before / 100.0, 2)
                collection_rows.append((
                    key_container, None, None,
                    op_date, fill_before, fill_after, volume,
                ))
                update_rows.append((fill_after, op_date, key_container))

            psycopg2.extras.execute_values(
                cur,
                """
                INSERT INTO public.collections
                    (container_id, agent_id, route_id, collected_at,
                     fill_rate_before, fill_rate_after, volume_collected_l)
                VALUES %s
                """,
                collection_rows,
            )

            psycopg2.extras.execute_values(
                cur,
                """
                UPDATE public.containers AS c
                SET fill_rate    = v.fill_after,
                    status       = 'empty',
                    last_updated = v.op_date
                FROM (VALUES %s) AS v(fill_after, op_date, key_container)
                WHERE c.key_container = v.key_container
                """,
                update_rows,
                template="(%s::numeric, %s::timestamp, %s::int)",
            )

            log(f"  → {len(rows)} container(s) unloaded, {len(collection_rows)} collection(s) recorded")

        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

# =============================================================
# DAG definition
# =============================================================

with DAG(
    dag_id="lasc__ops_containers",
    owner_links={"lasc": "https://url_de_la_documentation.io"},
    default_args=default_args,
    schedule=None,
    start_date=datetime(2025, 1, 21),
    doc_md=__doc__,
    catchup=False,
    tags=["lasc", "operations"],
    max_active_runs=5,
    params={
        "conn_id": Param(
            default="Ecotrack",
            type="string",
            description="Airflow connection ID (must be a PostgreSQL connection)",
        ),
    },
) as dag:

    start_task = EmptyOperator(task_id="start", task_display_name="Start")

    validate_task = ShortCircuitOperator(
        task_id="validate",
        task_display_name="Validate Payload",
        python_callable=task_validate,
        ignore_downstream_trigger_rules=True,
    )

    branch_task = BranchPythonOperator(
        task_id="branch",
        task_display_name="Branch on Type",
        python_callable=task_branch,
    )

    op_battery_task = PythonOperator(
        task_id="op_battery",
        task_display_name="Reset Batteries",
        python_callable=task_op_battery,
    )

    op_unload_task = PythonOperator(
        task_id="op_unload",
        task_display_name="Unload Containers",
        python_callable=task_op_unload,
    )

    end_task = EmptyOperator(
        task_id="end",
        task_display_name="End",
        trigger_rule=TriggerRule.ALL_DONE,
    )

    start_task >> validate_task >> branch_task >> [op_battery_task, op_unload_task] >> end_task
