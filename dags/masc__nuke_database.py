"""
### DAG : masc__nuke_database.py

## Tasks :
- check_confirm: Safety gate — aborts the run unless `confirm` is explicitly set to `true`
- nuke_database: Truncates every table in the target schema with RESTART IDENTITY CASCADE

## Schedule:
None (manual trigger only)
"""

from airflow import DAG
from airflow.providers.standard.operators.python import PythonOperator, ShortCircuitOperator
from airflow.providers.standard.operators.empty import EmptyOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.sdk import Param
from airflow.task.trigger_rule import TriggerRule
from datetime import datetime
from zoneinfo import ZoneInfo

# =============================================================
# Default arguments for the DAG
# =============================================================

default_args = {
    "start_date": datetime(2025, 1, 21, tzinfo=ZoneInfo("Europe/Paris")),
    "depends_on_past": False,
    "retries": 0,
    "owner": "airflow",
}

# =============================================================
# Task callables
# =============================================================

def task_check_confirm(**context) -> bool:
    confirmed = context["params"]["confirm"]
    if not confirmed:
        print("confirm param is false — aborting nuke. Set confirm=true to proceed.")
    return confirmed


def task_nuke_database(**context) -> None:
    conn_id = context["params"]["conn_id"]
    schema  = context["params"]["schema"]

    hook = PostgresHook(postgres_conn_id=conn_id)
    conn = hook.get_conn()
    conn.autocommit = False

    try:
        with conn.cursor() as cur:
            # Exclude:
            # - partition children (pg_inherits) — TRUNCATE on the parent cascades to them
            # - extension-owned tables (pg_depend deptype='e') — e.g. PostGIS spatial_ref_sys,
            #   which lives in the public schema but must never be truncated
            cur.execute(
                """
                SELECT c.relname
                FROM pg_class c
                JOIN pg_namespace n ON n.oid = c.relnamespace
                WHERE n.nspname = %s
                  AND c.relkind IN ('r', 'p')
                  AND NOT EXISTS (
                      SELECT 1 FROM pg_inherits WHERE inhrelid = c.oid
                  )
                  AND NOT EXISTS (
                      SELECT 1
                      FROM pg_depend d
                      JOIN pg_extension e ON e.oid = d.refobjid
                      WHERE d.objid = c.oid
                        AND d.deptype = 'e'
                  )
                ORDER BY c.relname
                """,
                (schema,),
            )
            tables = [row[0] for row in cur.fetchall()]

            if not tables:
                print(f"No tables found in schema '{schema}' — nothing to do.")
                return

            print(f"Found {len(tables)} tables in schema '{schema}': {', '.join(tables)}")

            # Single TRUNCATE statement handles FK ordering via CASCADE.
            # RESTART IDENTITY resets all sequences (auto-increment counters) to their default start value.
            table_list = ", ".join(f'"{schema}"."{t}"' for t in tables)
            cur.execute(f"TRUNCATE TABLE {table_list} RESTART IDENTITY CASCADE")

            print(f"Successfully truncated {len(tables)} tables with RESTART IDENTITY CASCADE.")

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
    dag_id="masc__nuke_database",
    default_args=default_args,
    schedule=None,
    start_date=datetime(2025, 1, 21),
    doc_md=__doc__,
    catchup=False,
    tags=["masc", "maintenance"],
    params={
        "conn_id": Param(
            default="Ecotrack",
            type="string",
            description="Airflow connection ID (must be a PostgreSQL connection)",
        ),
        "schema": Param(
            default="public",
            type="string",
            description="PostgreSQL schema to nuke (all BASE TABLE tables in this schema will be truncated)",
        ),
        "confirm": Param(
            default=False,
            type="boolean",
            description="Safety flag — must be set to true for the nuke to proceed",
        ),
    },
) as dag:

    start_task = EmptyOperator(
        task_id="start",
        task_display_name="Start",
    )

    check_confirm_task = ShortCircuitOperator(
        task_id="check_confirm",
        task_display_name="Confirm? (safety gate)",
        python_callable=task_check_confirm,
        ignore_downstream_trigger_rules=True,
    )

    nuke_database_task = PythonOperator(
        task_id="nuke_database",
        task_display_name="Nuke database",
        python_callable=task_nuke_database,
    )

    end_task = EmptyOperator(
        task_id="end",
        task_display_name="End",
        trigger_rule=TriggerRule.NONE_FAILED_MIN_ONE_SUCCESS,
    )

# Workflow
start_task >> check_confirm_task >> nuke_database_task >> end_task
