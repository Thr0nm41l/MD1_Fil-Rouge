"""
### DAG : test__print_hello.py

## Tasks :
- print_hello: Prints "hello" to the logs

## Schedule:
None
"""
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.empty import EmptyOperator
from airflow.decorators import task
from airflow.models.param import Param
from airflow.utils.trigger_rule import TriggerRule
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

def print_hello():
    """Task function that prints hello to the logs"""
    print("hello")

# =============================================================
# Define the DAG and tasks
# =============================================================

# Define the DAG
with DAG (
    dag_id="test__print_hello",
    owner_links={"test": "https://url_de_la_documentation.io"},
    default_args=default_args,
    schedule=None,
    start_date=datetime(2025, 1, 21),
    doc_md=__doc__,
    catchup=False,
    tags=["test"],
) as dag:

    #Empty start task
    start_task = EmptyOperator(
        task_id="start",
        task_display_name="Start",
        dag=dag,
    )

    # Define the task
    print_hello_task = PythonOperator(
        task_id="print_hello",
        task_display_name="Print Hello",
        python_callable=print_hello,
        dag=dag,
    )

    # Empty end task
    end_task = EmptyOperator(
        task_id="end",
        task_display_name="End",
        trigger_rule=TriggerRule.ALL_DONE,
        dag=dag,
    )

# Workflow
start_task >> print_hello_task >> end_task