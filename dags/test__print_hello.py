"""
### DAG : test__print_hello.py

## Tasks :
- print_hello: Prints "hello" to the logs

## Schedule:
None
"""

from datetime import datetime
from airflow import DAG
from airflow.operators.python import PythonOperator


def print_hello():
    """Task function that prints hello to the logs"""
    print("hello")


# Define the DAG
dag = DAG(
    "test__print_hello",
    description="Simple DAG that prints hello",
    schedule_interval=None,
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=["test"],
    docstring=__doc__,
)

# Define the task
print_hello_task = PythonOperator(
    task_id="print_hello",
    python_callable=print_hello,
    dag=dag,
)
