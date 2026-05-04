# DAG — `lasc__seed_data`

**File:** `dags/lasc__seed_data.py`
**Tags:** `lasc`, `ingestion`
**Schedule:** None (manual trigger only)
**Catchup:** disabled
**Max active runs:** 1

---

## Purpose

Populates the Ecotrack PostgreSQL database from scratch with a realistic, self-consistent dataset. It is intended to be run once on a fresh schema to produce usable demo / development data without needing production data.

---

## Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `conn_id` | string | `Ecotrack` | Airflow connection ID — must point to a PostgreSQL connection |
| `skip_history` | boolean | `false` | When `true`, skips `seed_fill_history` (useful for fast schema validation runs) |

---

## Generated Dataset

| Entity | Volume |
|---|---|
| Zones (Lyon districts) | 5 |
| Containers | 2 000 |
| IoT Devices | 2 000 (one per container) |
| Users | 116 (1 admin + 5 managers + 10 workers + 100 citizens) |
| Teams | 5 (one per zone) |
| Fill history rows | ~1 440 000 (30 days × 24 h × 2 000 containers) |
| Collections | 500 |
| Signalements | 200 |

All inserts use `ON CONFLICT DO NOTHING / DO UPDATE` — the DAG is safe to re-run on a database that already has data.

---

## Task Graph

```
start
  ├── seed_zones ──────────────────────────────┐
  │                                            ▼
  └── seed_users ──► seed_roles           seed_containers ──► seed_devices ──► check_skip_history
           │                                                                          │
           └──────────────────► seed_teams                                  (skips if skip_history=true)
                                                                                      │
                                                                             seed_fill_history
                                                                                      │
                                                                             seed_collections
                                                                                      │
                                                                             seed_signalements
                                                                                      │
                                                                             run_aggregations
                                                                                      │
                                                                                     end (ALL_DONE)
```

---

## Tasks

### `start`
Empty marker task. Entry point of the DAG.

---

### `seed_zones`
**Operator:** `PythonOperator`
**XCom output:** list of `key_zone` integers

Inserts 5 Lyon district zones into `public.zones`. Each zone has a name, a postal code, and a GeoJSON polygon built from a bounding box (WGS84 / SRID 4326).

| Zone | Postal code | Area |
|---|---|---|
| Lyon 1er — Presqu'île Nord | 69001 | 4.826–4.842 lng / 45.758–45.772 lat |
| Lyon 2e — Presqu'île Sud | 69002 | 4.822–4.840 lng / 45.740–45.758 lat |
| Lyon 3e — Part-Dieu | 69003 | 4.843–4.875 lng / 45.742–45.768 lat |
| Lyon 4e — Croix-Rousse | 69004 | 4.818–4.840 lng / 45.772–45.792 lat |
| Lyon 5e — Vieux-Lyon | 69005 | 4.808–4.826 lng / 45.754–45.774 lat |

Runs with `session_replication_role = 'replica'` and `row_security = off` to bypass row-level triggers and RLS during bulk insert.

---

### `seed_users`
**Operator:** `PythonOperator`
**XCom output:** dict `{admin: [...], managers: [...], workers: [...], citizens: [...]}`

Inserts 116 users into `public.users`. All accounts receive the password `password123` (bcrypt-hashed, rounds=10 — a single hash is computed and reused for all users to keep runtime short).

| Role | Count | Email pattern |
|---|---|---|
| Admin | 1 | `admin@ecotrack.fr` |
| Manager | 5 | `manager{n}@ecotrack.fr` |
| Worker | 10 | `worker{n}@ecotrack.fr` |
| Citizen | 100 | Random (Faker `fr_FR`, collision-safe) |

---

### `seed_roles`
**Operator:** `PythonOperator`
**XCom input:** `seed_users` → users dict

Reads existing role definitions from `public.role` (seeded by the schema SQL), then bulk-inserts into `public.user_role` to assign each user their appropriate application role (`Admin`, `Manager`, `Worker`, `User`).

---

### `seed_teams`
**Operator:** `PythonOperator`
**XCom input:** `seed_zones` → zone_ids, `seed_users` → users dict

Creates one team per zone in `public.teams`, sets the zone's manager as `team_manager`, and assigns 2 workers per team (workers 0–1 → zone 0, workers 2–3 → zone 1, etc.) via `public.user_team`.

---

### `seed_containers`
**Operator:** `PythonOperator`
**XCom input:** `seed_zones` → zone_ids
**XCom output:** list of container metadata dicts `{id, type_id, threshold, capacity}`

Distributes 2 000 containers evenly across zones (400 per zone; the last zone absorbs the remainder). Each container gets:
- A random geo-point strictly inside the zone bounding box (with 0.0005° margin to pass `ST_Within`)
- A random container type (Verre, Plastique, Papier, Organique, Général, Métal)
- A random capacity: 500, 750, 1 000, 1 500, or 2 000 L
- A fill threshold per type (65–80 %)

Inserts into `public.containers` via `execute_values` in batches of 500 with `RETURNING key_container`.

---

### `seed_devices`
**Operator:** `PythonOperator`
**XCom input:** `seed_containers` → containers list

Attaches one IoT device to every container in `public.device`. Device attributes:
- Model: one of `EcoSensor v1`, `EcoSensor v2`, `SmartBin Pro`, `UltraSonic-100`
- Random firmware version (`x.y.z`)
- Random battery level 30–100 %
- `last_seen` within the last 2 hours

---

### `check_skip_history`
**Operator:** `ShortCircuitOperator`

Returns `True` (continue) if `skip_history` param is `false`, `False` (short-circuit) otherwise. When short-circuited, all downstream tasks (`seed_fill_history` through `run_aggregations`) are skipped; `end` still runs due to `TriggerRule.ALL_DONE`.

---

### `seed_fill_history`
**Operator:** `PythonOperator`
**XCom input:** `seed_containers` → containers list

The heaviest task — inserts ~1 440 000 rows into `public.fill_history` (30 days × 24 h × 2 000 containers), batching in chunks of 50 000 rows.

**Simulation model per container:**
- Starts at a random fill level between 0 and 50 % of threshold
- Fill increases by `FILL_RATE_PER_HOUR[type] × U(0.7, 1.3)` per hour, plus Gaussian noise (`σ=0.3`)
- When fill ≥ threshold, a collection event resets fill to 2–8 % (simulating emptying)
- Battery drains 0.01–0.05 % per hour, floored at 10 %
- 1 % of measurements are randomly flagged as `is_outlier = true`

| Type | Base fill rate/h | Threshold |
|---|---|---|
| Verre | 1.2 % | 80 % |
| Plastique | 2.0 % | 70 % |
| Papier | 1.5 % | 75 % |
| Organique | 3.0 % | 65 % |
| Général | 2.5 % | 70 % |
| Métal | 0.8 % | 80 % |

After the bulk insert, runs a single `UPDATE public.containers` to sync each container's `fill_rate`, `status`, and `last_updated` from the latest history row (required because triggers are disabled during the bulk insert).

---

### `seed_collections`
**Operator:** `PythonOperator`
**XCom input:** `seed_containers`, `seed_users`

Inserts 500 collection events into `public.collections`. Each event:
- Random container, random worker agent
- Random timestamp within the last 30 days
- `fill_rate_before` 65–100 %, `fill_rate_after` 0–5 %
- Volume collected = capacity × fill_before / 100

---

### `seed_signalements`
**Operator:** `PythonOperator`
**XCom input:** `seed_containers`, `seed_users`

Inserts 200 citizen reports into `public.signalements`, **one row at a time** (not batched) so that the `signalement_award_points` trigger fires on each insert and credits +10 points to the reporting citizen.

Unlike earlier tasks, this task does **not** set `session_replication_role = 'replica'` — triggers are intentionally left active. Only `row_security = off` is set.

Status distribution (weighted): `ouvert` 30 %, `en_traitement` 20 %, `resolu` 40 %, `ferme` 10 %. Resolved/closed reports also get a `resolved_at` timestamp 1–5 days after creation.

---

### `run_aggregations`
**Operator:** `PythonOperator`

Calls the database stored procedures `CALL public.aggregate_daily(date)` and `CALL public.aggregate_hourly(timestamp)` for every day and hour in the 30-day history window, iterating from oldest to newest.

Both procedures are idempotent (`INSERT … ON CONFLICT DO UPDATE`), so re-running is safe. Populates `aggregated_hourly_stats` and `aggregated_daily_stats`.

---

### `end`
Empty marker task. `TriggerRule.ALL_DONE` — runs regardless of whether `check_skip_history` short-circuited the pipeline.

---

## Dependencies

```
start >> [seed_zones, seed_users]
seed_users >> seed_roles
[seed_zones, seed_users] >> seed_teams
seed_zones >> seed_containers
[seed_containers, seed_roles, seed_teams] >> seed_devices
seed_devices >> check_skip_history
check_skip_history >> seed_fill_history >> seed_collections >> seed_signalements >> run_aggregations >> end
```

---

## Required Airflow Connection

An Airflow connection named `Ecotrack` (or the value passed in `conn_id`) must exist before running this DAG. It must be of type **Postgres** and point to `postgres-postgresql.datalake.svc.cluster.local:5432`, database `airflow` (or the target schema's database).

---

## Runtime Notes

- **Expected duration:** 5–15 minutes depending on cluster resources (dominated by `seed_fill_history`)
- **Fast mode:** trigger with `skip_history = true` — completes in under 1 minute
- **Idempotent:** all inserts use `ON CONFLICT` — safe to re-run, but history rows accumulate if the table is not truncated first
- Bulk inserts run with `session_replication_role = 'replica'` to disable row triggers for performance; `seed_signalements` is the exception (triggers intentionally active)
