"""
### DAG : lasc__livesim_signalements

## Purpose:
Simulates citizen activity by periodically creating new container reports
(signalements) and advancing existing ones through their lifecycle.

New reports are inserted one by one so the signalement_award_points trigger
fires on each row and credits +10 points to the reporting citizen.

## Tasks:
- simulate_signalements: inserts N new "ouvert" reports from random citizens
  on random containers
- progress_statuses: advances a sample of open reports toward resolution
  (ouvert → en_traitement → resolu)

## Schedule:
*/30 * * * * (every 30 minutes)
"""

from airflow import DAG
from airflow.providers.standard.operators.python import PythonOperator
from airflow.providers.standard.operators.empty import EmptyOperator
from airflow.sdk import Param
from airflow.task.trigger_rule import TriggerRule
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import random
from airflow.providers.postgres.hooks.postgres import PostgresHook

# =============================================================
# Constants
# =============================================================

SIGNALEMENT_DESCRIPTIONS = [
    "Poubelle débordante, nécessite une collecte urgente.",
    "Couvercle cassé, accès aux déchets non sécurisé.",
    "Odeur nauséabonde, probablement déchets organiques.",
    "Conteneur renversé suite aux intempéries.",
    "Déchets déposés à côté du conteneur.",
    "Vandalisme constaté sur le conteneur.",
    "Conteneur saturé, collecte manquée.",
    "Mélange de déchets non conformes.",
]

# =============================================================
# Default arguments
# =============================================================

default_args = {
    "start_date": datetime(2025, 1, 21, tzinfo=ZoneInfo("Europe/Paris")),
    "depends_on_past": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=2),
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

# =============================================================
# Task callables
# =============================================================

def task_simulate_signalements(**context) -> None:
    """
    Picks n_reports random (container, citizen) pairs and inserts one
    "ouvert" signalement each. Inserted one row at a time so the
    signalement_award_points trigger fires and credits the citizen.
    Returns early if no citizen users or containers are found (e.g.
    lasc__seed_data was run with skip_users=true).
    """
    n_reports = context["params"]["n_reports"]
    now = datetime.now()

    conn = _get_conn(context["params"])
    try:
        with conn.cursor() as cur:
            cur.execute("SET row_security = off")

            cur.execute("""
                SELECT u.key_user
                FROM public.users u
                JOIN public.user_role ur ON ur.user_key = u.key_user
                JOIN public.role r ON r.key_role = ur.role_key
                WHERE r.name = 'User'
            """)
            citizen_ids = [row[0] for row in cur.fetchall()]

            if not citizen_ids:
                log("No citizen users found — skipping (run lasc__seed_data without skip_users first)")
                return

            cur.execute("SELECT key_container FROM public.containers")
            container_ids = [row[0] for row in cur.fetchall()]

            if not container_ids:
                log("No containers found — skipping")
                return

            log(f"Creating {n_reports} signalements...")
            for _ in range(n_reports):
                cur.execute(
                    """
                    INSERT INTO public.signalements
                        (container_id, user_id, zone_id, description, status, created_at, resolved_at)
                    VALUES (%s, %s, %s, %s, 'ouvert', %s, NULL)
                    """,
                    (
                        random.choice(container_ids),
                        random.choice(citizen_ids),
                        None,
                        random.choice(SIGNALEMENT_DESCRIPTIONS),
                        now,
                    ),
                )
            log(f"  → {n_reports} signalements created")

        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def task_progress_statuses(**context) -> None:
    """
    Advances a sample of existing signalements through their lifecycle so
    reports don't accumulate indefinitely as 'ouvert'.
      ouvert       → en_traitement  (up to n_reports // 2 per run)
      en_traitement → resolu         (up to n_reports // 2 per run)
    """
    n = max(1, context["params"]["n_reports"] // 2)
    now = datetime.now()

    conn = _get_conn(context["params"])
    try:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE public.signalements
                SET status = 'en_traitement'
                WHERE key_signalement IN (
                    SELECT key_signalement FROM public.signalements
                    WHERE status = 'ouvert'
                    ORDER BY RANDOM()
                    LIMIT %s
                )
            """, (n,))
            advanced = cur.rowcount

            cur.execute("""
                UPDATE public.signalements
                SET status = 'resolu', resolved_at = %s
                WHERE key_signalement IN (
                    SELECT key_signalement FROM public.signalements
                    WHERE status = 'en_traitement'
                    ORDER BY RANDOM()
                    LIMIT %s
                )
            """, (now, n))
            resolved = cur.rowcount

            log(f"  → {advanced} advanced to en_traitement, {resolved} resolved")

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
    dag_id="lasc__livesim_signalements",
    owner_links={"lasc": "https://url_de_la_documentation.io"},
    default_args=default_args,
    schedule="*/30 * * * *",
    start_date=datetime(2025, 1, 21),
    doc_md=__doc__,
    catchup=False,
    tags=["lasc", "simulation"],
    max_active_runs=1,
    params={
        "conn_id": Param(
            default="Ecotrack",
            type="string",
            description="Airflow connection ID (must be a PostgreSQL connection)",
        ),
        "n_reports": Param(
            default=3,
            type="integer",
            minimum=1,
            description="Number of new signalements to create per run; status progression advances n_reports // 2 per transition",
        ),
    },
) as dag:

    start_task = EmptyOperator(task_id="start", task_display_name="Start")

    simulate_signalements_task = PythonOperator(
        task_id="simulate_signalements",
        task_display_name="Simulate Signalements",
        python_callable=task_simulate_signalements,
    )

    progress_statuses_task = PythonOperator(
        task_id="progress_statuses",
        task_display_name="Progress Report Statuses",
        python_callable=task_progress_statuses,
    )

    end_task = EmptyOperator(
        task_id="end",
        task_display_name="End",
        trigger_rule=TriggerRule.NONE_FAILED_MIN_ONE_SUCCESS,
    )

    start_task >> simulate_signalements_task >> progress_statuses_task >> end_task
