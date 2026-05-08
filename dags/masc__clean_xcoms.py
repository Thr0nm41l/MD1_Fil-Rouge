"""
### DAG : masc__clean_xcoms.py

## Tasks :
- clean_xcoms: Deletes all xcom entries older than 7 days from the Airflow metadata database

## Schedule:
Weekly (every Monday at 9:00 AM UTC)
"""

from airflow import DAG
from airflow.providers.cncf.kubernetes.operators.pod import KubernetesPodOperator
from airflow.providers.standard.operators.empty import EmptyOperator
from airflow.task.trigger_rule import TriggerRule
from datetime import datetime
from zoneinfo import ZoneInfo
from kubernetes.client import models as k8s

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

    clean_xcoms_task = KubernetesPodOperator(
        task_id="clean_xcoms",
        task_display_name="Clean xcoms",
        name="airflow-clean-xcoms",
        namespace="airflow",
        image="apache/airflow:3.0.2",
        # KubernetesPodOperator creates a fresh pod outside the SDK task runner,
        # so the DB connection env var is read directly from the K8s secret.
        cmds=["airflow"],
        arguments=[
            "db", "clean",
            "--table", "xcom",
            "-y",
            "--skip-archive",
            "--clean-before-timestamp",
            "{{ macros.ds_add(ds, -7) }}T00:00:00+00:00",
        ],
        env_vars=[
            k8s.V1EnvVar(
                name="AIRFLOW__DATABASE__SQL_ALCHEMY_CONN",
                value_from=k8s.V1EnvVarSource(
                    secret_key_ref=k8s.V1SecretKeySelector(
                        name="airflow-metadata-credentials",
                        key="connection",
                    )
                ),
            ),
            k8s.V1EnvVar(
                name="AIRFLOW__CORE__FERNET_KEY",
                value_from=k8s.V1EnvVarSource(
                    secret_key_ref=k8s.V1SecretKeySelector(
                        name="airflow-fernet-key",
                        key="fernet-key",
                    )
                ),
            ),
        ],
        is_delete_operator_pod=True,
        get_logs=True,
        do_xcom_push=False,
    )

    end_task = EmptyOperator(
        task_id="end",
        task_display_name="End",
        trigger_rule=TriggerRule.NONE_FAILED_MIN_ONE_SUCCESS,
    )

# Workflow
start_task >> clean_xcoms_task >> end_task
