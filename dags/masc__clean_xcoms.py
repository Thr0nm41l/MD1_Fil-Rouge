"""
### DAG : masc__clean_xcoms.py

## Tasks :
- clean_xcoms: Deletes all XCom entries from the Airflow metadata database

## Schedule:
None (manual trigger only)
"""

from airflow import DAG
from airflow.providers.standard.operators.python import PythonOperator
from airflow.providers.standard.operators.empty import EmptyOperator
from airflow.task.trigger_rule import TriggerRule
from airflow.models.xcom import XCom
from airflow.utils.session import create_session
from datetime import datetime, timedelta
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
# Task functions
# =============================================================

def clean_xcoms(**context) -> None:
    with create_session() as session:
        count = session.query(XCom).delete()
    print(f"[INFO] Deleted {count} XCom entries.", flush=True)

# =============================================================
# Define the DAG and tasks
# =============================================================

with DAG(
    dag_id="masc__clean_xcoms",
    default_args=default_args,
    schedule=None,
    start_date=datetime(2025, 1, 21),
    doc_md=__doc__,
    catchup=False,
    tags=["masc", "maintenance"],
) as dag:

    start_task = EmptyOperator(
        task_id="start", 
        task_display_name="Start"
    )

    clean_xcoms_task = PythonOperator(
        task_id="clean_xcoms",
        task_display_name="Clean XComs",
        python_callable=clean_xcoms,
    )

    end_task = EmptyOperator(
        task_id="end",
        task_display_name="End",
        trigger_rule=TriggerRule.ALL_DONE,
    )

# Workflow
start_task >> clean_xcoms_task >> end_task
