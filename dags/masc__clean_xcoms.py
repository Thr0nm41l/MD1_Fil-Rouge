"""
### DAG : masc__clean_xcoms.py

## Tasks :
- clean_xcoms: Deletes all xcom entries older than 7 days from the Airflow metadata database

## Schedule:
Weekly (every Monday at 9:00 AM UTC)
"""

from airflow import DAG
from airflow.providers.standard.operators.bash import BashOperator
from airflow.providers.standard.operators.empty import EmptyOperator
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
# Define the DAG and tasks
# =============================================================

with DAG(
    dag_id="masc__clean_xcoms",
    default_args=default_args,
    schedule="0 9 * * 1",
    start_date=datetime(2025, 1, 21),
    doc_md=__doc__,
    catchup=False,
    tags=["masc", "maintenance"],
) as dag:

    start_task = EmptyOperator(
        task_id="start",
        task_display_name="Start",
    )

    clean_xcoms_task = BashOperator(
        task_id="clean_xcoms",
        task_display_name="Clean xcoms",
        bash_command=(
            "airflow db clean --table xcom -y --skip-archive "
            "--clean-before-timestamp '{{ macros.ds_add(ds, -7) }}T00:00:00+00:00'"
        ),
    )

    end_task = EmptyOperator(
        task_id="end",
        task_display_name="End",
        trigger_rule=TriggerRule.ALL_DONE,
    )

# Workflow
start_task >> clean_xcoms_task >> end_task
