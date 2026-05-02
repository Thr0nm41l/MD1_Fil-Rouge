"""
### DAG : test_list_tables_from_connection.py

## Tasks :
- list_tables: Lists all tables in the given schema through an Airflow connection

## Parameters:
- conn_id: Airflow connection ID to use (must be a PostgreSQL connection)
- schema: Database schema to inspect (default: public)

## Schedule:
None
"""

from airflow import DAG
from airflow.providers.standard.operators.python import PythonOperator
from airflow.providers.standard.operators.empty import EmptyOperator
from airflow.sdk import Param
from airflow.task.trigger_rule import TriggerRule
from airflow.providers.postgres.hooks.postgres import PostgresHook
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# =============================================================
# Default arguments for the DAG
# =============================================================

default_args = {
    "start_date": datetime(2024, 1, 21, tzinfo=ZoneInfo("Europe/Paris")),
    "depends_on_past": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=2),
    "max_active_runs": 1,
    "owner": "airflow",
}

# =============================================================
# Task functions
# =============================================================

def list_tables(**context) -> list[str]:
    params = context["params"]
    hook = PostgresHook(postgres_conn_id=params["conn_id"])

    records = hook.get_records(
        """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = %s
          AND table_type = 'BASE TABLE'
        ORDER BY table_name
        """,
        parameters=(params["schema"],),
    )

    tables = [row[0] for row in records]
    print(f"Found {len(tables)} table(s) in schema '{params['schema']}':")
    for table in tables:
        print(f"  - {table}")

    return tables

# =============================================================
# Define the DAG and tasks
# =============================================================

with DAG(
    dag_id="test_list_tables_from_connection",
    owner_links={"test": "https://url_de_la_documentation.io"},
    default_args=default_args,
    schedule=None,
    start_date=datetime(2025, 1, 21),
    doc_md=__doc__,
    catchup=False,
    tags=["test"],
    params={
        "conn_id": Param(
            default="Ecotrack",
            type="string",
            description="Airflow connection ID (must be a PostgreSQL connection)",
        ),
        "schema": Param(
            default="public",
            type="string",
            description="Database schema to inspect",
        ),
    },
) as dag:

    start_task = EmptyOperator(
        task_id="start",
        task_display_name="Start",
        dag=dag,
    )

    list_tables_task = PythonOperator(
        task_id="list_tables",
        task_display_name="List Tables",
        python_callable=list_tables,
        dag=dag,
    )

    end_task = EmptyOperator(
        task_id="end",
        task_display_name="End",
        trigger_rule=TriggerRule.ALL_DONE,
        dag=dag,
    )

start_task >> list_tables_task >> end_task
