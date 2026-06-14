"""
### DAG : lasc__livesim_fill

## Purpose:
Simulates realistic container fill evolution by appending one IoT measurement
per container every 10 minutes. Picks up from the current fill_rate stored in
the containers table — stateful and continuous across runs.

Triggers are kept active (unlike lasc__seed_data), so each fill_history insert
fires the normal pipeline: containers.fill_rate / status / last_updated are
updated automatically.

## Tasks:
- simulate_fill: reads current fill state, computes next value, inserts into fill_history
- run_aggregations: refreshes hourly and daily aggregates for the current window

## Schedule:
*/10 * * * * (every 10 minutes)
"""

from airflow import DAG
from airflow.providers.standard.operators.python import PythonOperator
from airflow.providers.standard.operators.empty import EmptyOperator
from airflow.sdk import Param
from airflow.task.trigger_rule import TriggerRule
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import random
import psycopg2
import psycopg2.extras
from airflow.providers.postgres.hooks.postgres import PostgresHook

# =============================================================
# Constants — mirror lasc__seed_data so simulated data is consistent
# =============================================================

INTERVAL_MINUTES = 10
RATE_SCALE = INTERVAL_MINUTES / 60  # scale hourly fill rates to one tick

FILL_RATE_PER_HOUR = {
    1: 1.2,   # Verre
    2: 2.0,   # Plastique
    3: 1.5,   # Papier
    4: 3.0,   # Organique
    5: 2.5,   # Général
    6: 0.8,   # Métal
}

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

def task_simulate_fill(**context) -> None:
    """
    For each container:
      - reads current fill_rate and device battery from the DB
      - advances fill by the 10-min equivalent of FILL_RATE_PER_HOUR ± noise
      - resets to 2–8 % when the collection threshold is exceeded (unless skip_reset=True)
      - inserts one fill_history row per container
      - batch-updates device.battery_pct
    Triggers are active: containers.fill_rate / status / last_updated are kept
    in sync by the existing fill_history trigger.

    skip_reset=True: disables both resets — fill clamps to 100 % instead of
    triggering a collection event; battery drains to 0 % instead of flooring at 10 %.
    """
    skip_reset = context["params"]["skip_reset"]

    # Snap measured_at to the current 10-min boundary
    now  = datetime.now().replace(second=0, microsecond=0)
    now  = now.replace(minute=(now.minute // INTERVAL_MINUTES) * INTERVAL_MINUTES)
    hour = now.hour
    dow  = now.weekday()  # 0 = Mon, 6 = Sun

    conn = _get_conn(context["params"])
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    c.key_container,
                    c.type_id,
                    c.fill_rate,
                    c.fill_threshold_pct,
                    d.key_device,
                    d.battery_pct
                FROM public.containers c
                JOIN public.device d ON d.container_id = c.key_container
            """)
            rows = cur.fetchall()
            log(f"Simulating fill for {len(rows)} containers at {now}")

            measurements   = []
            battery_updates = []

            for key_container, type_id, fill_rate, threshold, key_device, battery in rows:
                fill_rate = float(fill_rate or 0.0)
                battery   = float(battery   or 50.0)

                # Dead device — no signal emitted
                if battery <= 0.0:
                    continue

                # Advance fill for one 10-min tick
                rate = FILL_RATE_PER_HOUR.get(type_id, 2.0) * RATE_SCALE
                rate *= random.uniform(0.7, 1.3)

                # Temporal multipliers — mirror lasc__seed_data simulation model
                if hour in (7, 8, 9, 17, 18, 19):
                    time_mult = 1.5
                elif 0 <= hour <= 5:
                    time_mult = 0.4
                else:
                    time_mult = 1.0
                if dow >= 5 and type_id in (4, 5):  # weekend boost: organic + general
                    time_mult *= 1.3
                rate *= time_mult

                new_fill = fill_rate + rate + random.gauss(0, 0.15)
                new_fill = max(0.0, new_fill)

                # Collection event: threshold exceeded → container emptied
                if not skip_reset and new_fill >= threshold:
                    new_fill = random.uniform(2.0, 8.0)

                new_fill     = round(min(new_fill, 100.0), 2)
                battery_floor = 0.0 if skip_reset else 10.0
                new_batt     = round(max(battery - random.uniform(0.001, 0.008), battery_floor), 2)
                temp     = round(random.uniform(5.0, 35.0), 1)
                is_out   = random.random() < 0.01

                measurements.append((
                    key_container, key_device, new_fill,
                    temp, new_batt, is_out, now,
                ))
                battery_updates.append((key_device, new_batt))

            # Bulk-insert measurements (ON CONFLICT DO NOTHING ensures idempotency on retry)
            psycopg2.extras.execute_values(
                cur,
                """
                INSERT INTO public.fill_history
                    (container_id, device_id, fill_rate, temperature,
                     battery_pct, is_outlier, measured_at)
                VALUES %s
                ON CONFLICT DO NOTHING
                """,
                measurements,
                page_size=500,
            )
            log(f"  → {len(measurements)} measurements inserted")

            # Sync device battery levels
            psycopg2.extras.execute_values(
                cur,
                """
                UPDATE public.device d
                SET battery_pct = v.battery_pct
                FROM (VALUES %s) AS v(key_device, battery_pct)
                WHERE d.key_device = v.key_device
                """,
                battery_updates,
                template="(%s, %s::numeric)",
                page_size=500,
            )

        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def task_run_aggregations(**context) -> None:
    """Refresh hourly and daily aggregates for the current tick's window."""
    now  = datetime.now().replace(second=0, microsecond=0)
    hour = now.replace(minute=0)
    day  = now.date()

    conn = _get_conn(context["params"])
    try:
        with conn.cursor() as cur:
            cur.execute("CALL public.aggregate_hourly(%s)", (hour,))
            cur.execute("CALL public.aggregate_daily(%s)", (day,))
        conn.commit()
        log(f"  → aggregations refreshed for {hour} / {day}")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

# =============================================================
# DAG definition
# =============================================================

with DAG(
    dag_id="lasc__livesim_fill",
    owner_links={"lasc": "https://url_de_la_documentation.io"},
    default_args=default_args,
    schedule="*/10 * * * *",
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
        "skip_reset": Param(
            default=False,
            type="boolean",
            description="Disable resets: fill clamps to 100 % (no collection event), battery drains to 0 % (no floor at 10 %)",
        ),
    },
) as dag:

    start_task = EmptyOperator(task_id="start", task_display_name="Start")

    simulate_fill_task = PythonOperator(
        task_id="simulate_fill",
        task_display_name="Simulate Fill",
        python_callable=task_simulate_fill,
    )

    run_aggregations_task = PythonOperator(
        task_id="run_aggregations",
        task_display_name="Refresh Aggregations",
        python_callable=task_run_aggregations,
    )

    end_task = EmptyOperator(
        task_id="end",
        task_display_name="End",
        trigger_rule=TriggerRule.NONE_FAILED_MIN_ONE_SUCCESS,
    )

    start_task >> simulate_fill_task >> run_aggregations_task >> end_task
