"""
### DAG : test__seed_data.py

## Tasks :
- seed_data: Seeds the database with initial data

## Data generaton:
- 5 zones (Lyon districts) with GeoJSON polygons
- 2 000 containers distributed across zones
- 1 admin + 5 managers + 10 workers + 100 citizens
- IoT devices (one per container)
- 30 days of fill_history  (~1 440 000 rows)
- Collections, signalements, user points
- Hourly and daily aggregations

## Schedule:
None
"""

# DAG base imports
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.empty import EmptyOperator
from airflow.decorators import task
from airflow.models.param import Param
from airflow.utils.trigger_rule import TriggerRule
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# DAG specific imports
import argparse
import random
import sys
from datetime import datetime, timedelta, time as dtime
from typing import List, Tuple
from airflow.providers.postgres.hooks.postgres import PostgresHook

import bcrypt
import psycopg2
import psycopg2.extras
from faker import Faker

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

# ============================================================
# Configuration for data generation
# ============================================================

N_CONTAINERS     = 2_000
N_CITIZENS       = 100
N_WORKERS        = 10    # 2 per zone
N_MANAGERS       = 5     # 1 per zone
DAYS_HISTORY     = 30
MEASURES_PER_DAY = 24    # 1 per hour  →  30 × 2 000 × 24 = 1 440 000 rows
BATCH_SIZE       = 50_000

# Lyon districts — non-overlapping bounding boxes (lng_min, lat_min, lng_max, lat_max)
ZONES = [
    {
        "name": "Lyon 1er — Presqu'île Nord",
        "postal_code": 69001,
        "bounds": (4.826, 45.758, 4.842, 45.772),
    },
    {
        "name": "Lyon 2e — Presqu'île Sud",
        "postal_code": 69002,
        "bounds": (4.822, 45.740, 4.840, 45.758),
    },
    {
        "name": "Lyon 3e — Part-Dieu",
        "postal_code": 69003,
        "bounds": (4.843, 45.742, 4.875, 45.768),
    },
    {
        "name": "Lyon 4e — Croix-Rousse",
        "postal_code": 69004,
        "bounds": (4.818, 45.772, 4.840, 45.792),
    },
    {
        "name": "Lyon 5e — Vieux-Lyon",
        "postal_code": 69005,
        "bounds": (4.808, 45.754, 4.826, 45.774),
    },
]

# Seeded by setup_complete.sql — key_type order matches INSERT order
CONTAINER_TYPE_IDS = [1, 2, 3, 4, 5, 6]  # Verre, Plastique, Papier, Organique, Général, Métal

# Fill-rate increase per hour (percentage points) — drives realistic IoT patterns
FILL_RATE_PER_HOUR = {
    1: 1.2,   # Verre     — slow
    2: 2.0,   # Plastique
    3: 1.5,   # Papier
    4: 3.0,   # Organique — fast (degrades)
    5: 2.5,   # Général
    6: 0.8,   # Métal     — very slow
}

THRESHOLD_BY_TYPE = {
    1: 80.0,  # Verre
    2: 70.0,  # Plastique
    3: 75.0,  # Papier
    4: 65.0,  # Organique
    5: 70.0,  # Général
    6: 80.0,  # Métal
}

CAPACITIES_L = [500.0, 750.0, 1_000.0, 1_500.0, 2_000.0]

DEVICE_MODELS = ["EcoSensor v1", "EcoSensor v2", "SmartBin Pro", "UltraSonic-100"]

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

# ============================================================
# Utility functions for data generation
# ============================================================

def make_polygon_ewkt(bounds: Tuple[float, float, float, float]) -> str:
    """
    Build an EWKT POLYGON from (lng_min, lat_min, lng_max, lat_max).
    Returns a closed ring in WGS84 (SRID 4326).
    """
    lng_min, lat_min, lng_max, lat_max = bounds
    return (
        f"SRID=4326;POLYGON(("
        f"{lng_min} {lat_min}, {lng_max} {lat_min}, "
        f"{lng_max} {lat_max}, {lng_min} {lat_max}, "
        f"{lng_min} {lat_min}"
        f"))"
    )


def random_point_in_bounds(bounds: Tuple[float, float, float, float]) -> Tuple[float, float]:
    """
    Return a random (lng, lat) strictly inside the bounding box (with a small margin).
    The margin ensures the point passes ST_Within against the zone polygon.
    """
    lng_min, lat_min, lng_max, lat_max = bounds
    margin = 0.0005
    lng = random.uniform(lng_min + margin, lng_max - margin)
    lat = random.uniform(lat_min + margin, lat_max - margin)
    return lng, lat


def compute_status(fill_rate: float) -> str:
    """Return the container status string from its fill rate."""
    if fill_rate < 25:
        return "empty"
    if fill_rate < 70:
        return "normal"
    if fill_rate < 90:
        return "full"
    return "critical"


def log(msg: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)

# ============================================================
# Seed data generation functions
# ============================================================

def seed_zones(cur) -> List[int]:
    """Insert 5 Lyon district zones and return their PKs."""
    log("Seeding zones...")
    zone_ids = []
    for z in ZONES:
        cur.execute(
            """
            INSERT INTO public.zones (name, postal_code, polygon)
            VALUES (%s, %s, ST_GeomFromEWKT(%s))
            ON CONFLICT (postal_code) DO UPDATE SET name = EXCLUDED.name
            RETURNING key_zone
            """,
            (z["name"], z["postal_code"], make_polygon_ewkt(z["bounds"])),
        )
        zone_ids.append(cur.fetchone()[0])
    log(f"  → {len(zone_ids)} zones")
    return zone_ids


def seed_users(cur) -> dict:
    """Insert admin, managers, workers and citizens. Returns a dict of {role: [user_ids]}."""
    log("Seeding users...")
    # Hash once for all seed users — password is "password123" for every account
    password_hash = bcrypt.hashpw(b"password123", bcrypt.gensalt(rounds=10)).decode()

    users: dict = {"admin": [], "managers": [], "workers": [], "citizens": []}

    def insert_user(email: str, last_name: str, first_name: str) -> int:
        cur.execute(
            """
            INSERT INTO public.users (email, name, first_name, password)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (email) DO UPDATE SET name = EXCLUDED.name
            RETURNING key_user
            """,
            (email, last_name, first_name, password_hash),
        )
        return cur.fetchone()[0]

    users["admin"].append(insert_user("admin@ecotrack.fr", "Admin", "Ecotrack"))

    for i in range(N_MANAGERS):
        uid = insert_user(f"manager{i + 1}@ecotrack.fr", fake.last_name(), fake.first_name())
        users["managers"].append(uid)

    for i in range(N_WORKERS):
        uid = insert_user(f"worker{i + 1}@ecotrack.fr", fake.last_name(), fake.first_name())
        users["workers"].append(uid)

    seen_emails: set = set()
    for _ in range(N_CITIZENS):
        email = fake.email()
        while email in seen_emails:
            email = fake.email()
        seen_emails.add(email)
        uid = insert_user(email, fake.last_name(), fake.first_name())
        users["citizens"].append(uid)

    total = 1 + N_MANAGERS + N_WORKERS + N_CITIZENS
    log(f"  → {total} users (password: password123)")
    return users


def seed_roles(cur, users: dict) -> None:
    """Assign application roles to every user."""
    log("Assigning roles...")
    cur.execute("SELECT key_role, name FROM public.role ORDER BY key_role")
    role_map = {row[1]: row[0] for row in cur.fetchall()}

    assignments = []
    for uid in users["admin"]:
        assignments.append((uid, role_map["Admin"]))
    for uid in users["managers"]:
        assignments.append((uid, role_map["Manager"]))
    for uid in users["workers"]:
        assignments.append((uid, role_map["Worker"]))
    for uid in users["citizens"]:
        assignments.append((uid, role_map["User"]))

    psycopg2.extras.execute_values(
        cur,
        """
        INSERT INTO public.user_role (user_key, role_key)
        VALUES %s
        ON CONFLICT (user_key, role_key) DO NOTHING
        """,
        assignments,
    )
    log(f"  → {len(assignments)} role assignments")


def seed_teams(cur, zone_ids: List[int], users: dict) -> List[int]:
    """Create one team per zone, assign the zone manager and two workers."""
    log("Seeding teams...")
    team_ids = []
    for i, zone_id in enumerate(zone_ids):
        cur.execute(
            """
            INSERT INTO public.teams (zone_id, team_manager, name)
            VALUES (%s, %s, %s)
            RETURNING key_teams
            """,
            (zone_id, users["managers"][i], f"Équipe — {ZONES[i]['name']}"),
        )
        team_ids.append(cur.fetchone()[0])

    # Assign workers: 2 workers per team
    for i, team_id in enumerate(team_ids):
        for j in range(2):
            worker_idx = i * 2 + j
            if worker_idx < len(users["workers"]):
                cur.execute(
                    """
                    INSERT INTO public.user_team (key_user, key_team)
                    VALUES (%s, %s)
                    ON CONFLICT DO NOTHING
                    """,
                    (users["workers"][worker_idx], team_id),
                )

    log(f"  → {len(team_ids)} teams")
    return team_ids


def seed_containers(cur, zone_ids: List[int]) -> List[dict]:
    """
    Insert N_CONTAINERS containers distributed evenly across zones.
    zone_id is provided explicitly (triggers are disabled during bulk insert).
    Returns a list of dicts with container metadata.
    """
    log(f"Seeding {N_CONTAINERS} containers...")
    rows = []
    metadata = []

    containers_per_zone = N_CONTAINERS // len(ZONES)
    for i, zone_id in enumerate(zone_ids):
        bounds = ZONES[i]["bounds"]
        # Last zone absorbs the remainder
        count = (
            containers_per_zone
            if i < len(ZONES) - 1
            else N_CONTAINERS - containers_per_zone * (len(ZONES) - 1)
        )
        for _ in range(count):
            lng, lat    = random_point_in_bounds(bounds)
            type_id     = random.choice(CONTAINER_TYPE_IDS)
            capacity    = random.choice(CAPACITIES_L)
            threshold   = THRESHOLD_BY_TYPE[type_id]
            rows.append((
                f"SRID=4326;POINT({lng} {lat})",
                type_id,
                zone_id,
                capacity,
                threshold,
            ))
            metadata.append({
                "type_id":   type_id,
                "threshold": threshold,
                "capacity":  capacity,
            })

    psycopg2.extras.execute_values(
        cur,
        """
        INSERT INTO public.containers
            (location, type_id, zone_id, capacity_liters, fill_threshold_pct)
        VALUES (ST_GeomFromEWKT(%s), %s, %s, %s, %s)
        RETURNING key_container
        """,
        rows,
        template="(%s, %s, %s, %s, %s)",
        page_size=500,
    )
    for idx, (row,) in enumerate(cur.fetchall()):
        metadata[idx]["id"] = row

    log(f"  → {len(metadata)} containers")
    return metadata


def seed_devices(cur, containers: List[dict]) -> None:
    """Attach one IoT device to every container."""
    log("Seeding IoT devices...")
    rows = []
    for c in containers:
        firmware = f"{random.randint(1, 3)}.{random.randint(0, 9)}.{random.randint(0, 9)}"
        rows.append((
            c["id"],
            random.choice(DEVICE_MODELS),
            firmware,
            round(random.uniform(30.0, 100.0), 2),
            datetime.now() - timedelta(minutes=random.randint(0, 120)),
        ))

    psycopg2.extras.execute_values(
        cur,
        """
        INSERT INTO public.device (container_id, model, firmware_version, battery_pct, last_seen)
        VALUES %s
        """,
        rows,
        page_size=500,
    )
    log(f"  → {len(rows)} devices")


def seed_fill_history(cur, containers: List[dict]) -> None:
    """
    Generate DAYS_HISTORY × MEASURES_PER_DAY measurements per container.

    Fill rate simulation:
    - Each container starts at a random fill level.
    - Fill rate increases by FILL_RATE_PER_HOUR[type] ± Gaussian noise per hour.
    - When fill rate exceeds the collection threshold, a collection event resets
      it to 2–8 % (simulating agent emptying the container).
    - 1 % of measurements are flagged as outliers (sensor anomaly).

    Triggers are disabled for this bulk insert (session_replication_role = replica).
    containers.fill_rate is updated in a separate UPDATE after the insert.
    """
    log(
        f"Seeding fill_history "
        f"({DAYS_HISTORY}d × {N_CONTAINERS} containers × {MEASURES_PER_DAY}h "
        f"≈ {DAYS_HISTORY * N_CONTAINERS * MEASURES_PER_DAY:,} rows)..."
    )

    end_dt   = datetime.now().replace(minute=0, second=0, microsecond=0)
    start_dt = end_dt - timedelta(days=DAYS_HISTORY)

    cur.execute("SELECT container_id, key_device FROM public.device")
    device_map: dict = {row[0]: row[1] for row in cur.fetchall()}

    batch: list     = []
    total_inserted  = 0

    for c in containers:
        cid       = c["id"]
        did       = device_map.get(cid)
        type_id   = c["type_id"]
        threshold = c["threshold"]

        # Per-container variability: ±30 % of the base fill rate
        rate_per_hour = FILL_RATE_PER_HOUR[type_id] * random.uniform(0.7, 1.3)

        current_fill = random.uniform(0.0, threshold * 0.5)
        battery      = random.uniform(60.0, 100.0)
        current_dt   = start_dt

        while current_dt <= end_dt:
            # Collection event
            if current_fill >= threshold:
                current_fill = random.uniform(2.0, 8.0)

            fill_rate  = round(min(current_fill, 100.0), 2)
            temp       = round(random.uniform(5.0, 35.0), 1)
            battery   -= random.uniform(0.01, 0.05)
            battery    = max(battery, 10.0)
            is_outlier = random.random() < 0.01

            batch.append((
                cid, did, fill_rate, temp,
                round(battery, 2), is_outlier, current_dt,
            ))

            current_fill += rate_per_hour + random.gauss(0, 0.3)
            current_fill  = max(0.0, current_fill)
            current_dt   += timedelta(hours=1)

            if len(batch) >= BATCH_SIZE:
                _flush_history_batch(cur, batch)
                total_inserted += len(batch)
                batch.clear()
                log(f"    {total_inserted:>12,} rows inserted...")

    if batch:
        _flush_history_batch(cur, batch)
        total_inserted += len(batch)

    log(f"  → {total_inserted:,} rows in fill_history")

    # Update containers with the latest measurement since triggers were disabled
    log("  Syncing containers.fill_rate from latest measurements...")
    cur.execute("""
        UPDATE public.containers c
        SET
            fill_rate    = latest.fill_rate,
            status       = CASE
                               WHEN latest.fill_rate < 25 THEN 'empty'
                               WHEN latest.fill_rate < 70 THEN 'normal'
                               WHEN latest.fill_rate < 90 THEN 'full'
                               ELSE 'critical'
                           END,
            last_updated = latest.measured_at
        FROM (
            SELECT DISTINCT ON (container_id)
                container_id, fill_rate, measured_at
            FROM  public.fill_history
            ORDER BY container_id, measured_at DESC
        ) latest
        WHERE c.key_container = latest.container_id
    """)
    log("  → containers synced")


def _flush_history_batch(cur, batch: list) -> None:
    """Bulk-insert one batch of fill_history rows."""
    psycopg2.extras.execute_values(
        cur,
        """
        INSERT INTO public.fill_history
            (container_id, device_id, fill_rate, temperature, battery_pct, is_outlier, measured_at)
        VALUES %s
        """,
        batch,
        page_size=BATCH_SIZE,
    )


def seed_collections(cur, containers: List[dict], users: dict) -> None:
    """Generate realistic collection events (container empties by a worker)."""
    log("Seeding collections...")
    rows = []
    end_dt = datetime.now()
    for _ in range(500):
        c            = random.choice(containers)
        agent_id     = random.choice(users["workers"])
        days_ago     = random.randint(0, DAYS_HISTORY)
        collected_at = end_dt - timedelta(days=days_ago, hours=random.randint(0, 23))
        fill_before  = round(random.uniform(65.0, 100.0), 2)
        fill_after   = round(random.uniform(0.0, 5.0), 2)
        volume       = round(c["capacity"] * fill_before / 100.0, 2)
        rows.append((c["id"], agent_id, None, collected_at, fill_before, fill_after, volume))

    psycopg2.extras.execute_values(
        cur,
        """
        INSERT INTO public.collections
            (container_id, agent_id, route_id, collected_at,
             fill_rate_before, fill_rate_after, volume_collected_l)
        VALUES %s
        """,
        rows,
    )
    log(f"  → {len(rows)} collections")


def seed_signalements(cur, containers: List[dict], users: dict) -> None:
    """
    Insert citizen reports.
    Triggers are re-enabled at this point so signalement_award_points fires
    and credits +10 pts to the reporting user.
    """
    log("Seeding signalements (triggers active → user_points credited)...")
    rows = []
    end_dt = datetime.now()
    for _ in range(200):
        c        = random.choice(containers)
        uid      = random.choice(users["citizens"])
        days_ago = random.randint(0, DAYS_HISTORY)
        created  = end_dt - timedelta(days=days_ago, hours=random.randint(0, 23))
        status   = random.choices(
            ["ouvert", "en_traitement", "resolu", "ferme"],
            weights=[30, 20, 40, 10],
        )[0]
        resolved_at = (
            created + timedelta(days=random.randint(1, 5))
            if status in ("resolu", "ferme")
            else None
        )
        rows.append((
            c["id"], uid, None,
            random.choice(SIGNALEMENT_DESCRIPTIONS),
            status, created, resolved_at,
        ))

    # Insert one by one so the trigger fires per row (awards points)
    for row in rows:
        cur.execute(
            """
            INSERT INTO public.signalements
                (container_id, user_id, zone_id, description, status, created_at, resolved_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            row,
        )
    log(f"  → {len(rows)} signalements")


def run_aggregations(cur) -> None:
    """
    Call aggregate_daily and aggregate_hourly for every day/hour in the history window.
    Both procedures are idempotent (INSERT … ON CONFLICT DO UPDATE), so re-running is safe.
    """
    log("Running aggregations (this may take a minute)...")
    end_dt = datetime.now().replace(minute=0, second=0, microsecond=0)

    for day_offset in range(DAYS_HISTORY, -1, -1):
        day = (end_dt - timedelta(days=day_offset)).date()
        cur.execute("CALL public.aggregate_daily(%s)", (day,))
        for hour in range(24):
            ts = datetime.combine(day, dtime(hour, 0))
            if ts <= end_dt:
                cur.execute("CALL public.aggregate_hourly(%s)", (ts,))

    log("  → aggregated_hourly_stats and aggregated_daily_stats populated")


# ── CLI ───────────────────────────────────────────────────────────────────────

# def parse_args() -> argparse.Namespace:
#     p = argparse.ArgumentParser(description="ECOTRACK seed script")
#     p.add_argument("--host",         default="localhost",  help="PostgreSQL host")
#     p.add_argument("--port",         default=5432, type=int)
#     p.add_argument("--db",           default="Ecotrack",   help="Database name")
#     p.add_argument("--user",         default="postgres")
#     p.add_argument("--password",     default="",           help="PostgreSQL password")
#     p.add_argument(
#         "--skip-history",
#         action="store_true",
#         help="Skip fill_history generation (fast schema test)",
#     )
#     return p.parse_args()

# =============================================================
# Tasks functions
# =============================================================

def main() -> None:
    # args = parse_args()
    # log(f"Connecting to {args.user}@{args.host}:{args.port}/{args.db}...")

    # conn = psycopg2.connect(
    #     host=args.host,
    #     port=args.port,
    #     dbname=args.db,
    #     user=args.user,
    #     password=args.password,
    # )
    # conn.autocommit = False

    hook = PostgresHook(postgres_conn_id="EcotrackDB")
    conn = hook.get_conn()

    try:
        with conn.cursor() as cur:
            # ── Phase 1: bulk inserts with RLS and triggers bypassed ──────────
            cur.execute("SET row_security = off")
            # session_replication_role = replica disables all non-constraint triggers.
            # This prevents fill_history_update_container from firing 1.4M times.
            cur.execute("SET session_replication_role = 'replica'")

            zone_ids   = seed_zones(cur)
            users      = seed_users(cur)
            seed_roles(cur, users)
            seed_teams(cur, zone_ids, users)
            containers = seed_containers(cur, zone_ids)
            seed_devices(cur, containers)

            seed_fill_history(cur, containers)
            seed_collections(cur, containers, users)

            # ── Phase 2: restore triggers for event-driven inserts ────────────
            # signalement_award_points trigger must fire to credit user_points.
            cur.execute("SET session_replication_role = 'origin'")
            seed_signalements(cur, containers, users)
            run_aggregations(cur)

        conn.commit()
        log("Seed complete.")
        log(f"  Containers : {N_CONTAINERS}")
        log(f"  Users      : {1 + N_MANAGERS + N_WORKERS + N_CITIZENS} (password: password123)")
        log(f"  History    : {f'{DAYS_HISTORY} days'}")

    except Exception as exc:
        conn.rollback()
        log(f"Error — rolling back: {exc}")
        raise
    finally:
        conn.close()

# =============================================================
# Define the DAG and tasks
# =============================================================

# Define the DAG
with DAG (
    dag_id="test__seed_data",
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
    seed_data_task = PythonOperator(
        task_id="seed_data",
        task_display_name="Print Hello",
        python_callable=main,
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
start_task >> seed_data_task >> end_task