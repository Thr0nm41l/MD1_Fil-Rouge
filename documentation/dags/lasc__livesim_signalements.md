# DAG — `lasc__livesim_signalements`

**File:** `dags/lasc__livesim_signalements.py`
**Tags:** `lasc`, `simulation`
**Schedule:** `*/30 * * * *` (every 30 minutes)
**Catchup:** disabled
**Max active runs:** 1

---

## Purpose

Simulates citizen reporting activity by periodically creating new container reports and advancing existing ones through their resolution lifecycle. Complements `lasc__livesim_fill` by keeping the `signalements` table and citizen point balances alive and evolving.

Row triggers are kept active so `signalement_award_points` fires on each new report and credits +10 points to the reporting citizen.

**Prerequisite:** `lasc__seed_data` must have been run with `skip_users=false` — this DAG reads citizen users from the database and returns early if none are found.

---

## Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `conn_id` | string | `Ecotrack` | Airflow connection ID — must point to a PostgreSQL connection |
| `n_reports` | integer ≥ 1 | `3` | Number of new signalements to create per run; status progression advances `n_reports // 2` per transition |

---

## Task Graph

```
start ──► simulate_signalements ──► progress_statuses ──► end (ALL_DONE)
```

---

## Tasks

### `start`
Empty marker task. Entry point of the DAG.

---

### `simulate_signalements`
**Operator:** `PythonOperator`

Creates `n_reports` new signalement rows, each with status `ouvert` and `created_at = now()`. Containers and citizen users are both picked at random from the full population in the database.

Rows are inserted **one at a time** (not batched) so the `signalement_award_points` trigger fires on each insert and credits +10 points to the reporting citizen.

Returns early without inserting if no citizen users or no containers are found in the database.

**Tables read:** `public.users`, `public.user_role`, `public.role`, `public.containers`
**Tables written:** `public.signalements`, `public.user_points` (via trigger)

---

### `progress_statuses`
**Operator:** `PythonOperator`

Advances a random sample of existing reports through their lifecycle so reports don't accumulate indefinitely as `ouvert`. Runs two UPDATE passes per tick:

| Pass | Transition | Max rows |
|---|---|---|
| 1 | `ouvert` → `en_traitement` | `n_reports // 2` |
| 2 | `en_traitement` → `resolu` (sets `resolved_at = now()`) | `n_reports // 2` |

Selection is random (`ORDER BY RANDOM() LIMIT n`) — no guarantee that the reports advanced in pass 1 are the ones resolved in pass 2.

**Tables written:** `public.signalements`

---

### `end`
Empty marker task. `TriggerRule.ALL_DONE` — runs regardless of upstream failures.

---

## Dependencies

```
start >> simulate_signalements >> progress_statuses >> end
```

---

## Report Descriptions

New reports are drawn at random from a fixed list of 8 realistic French descriptions:

| Description |
|---|
| Poubelle débordante, nécessite une collecte urgente. |
| Couvercle cassé, accès aux déchets non sécurisé. |
| Odeur nauséabonde, probablement déchets organiques. |
| Conteneur renversé suite aux intempéries. |
| Déchets déposés à côté du conteneur. |
| Vandalisme constaté sur le conteneur. |
| Conteneur saturé, collecte manquée. |
| Mélange de déchets non conformes. |

---

## Relation to other simulation DAGs

| | `lasc__livesim_fill` | `lasc__livesim_signalements` |
|---|---|---|
| Schedule | Every 10 minutes | Every 30 minutes |
| Scope | IoT measurements, container fill state | Citizen reports, user points |
| Triggers | Active (fill pipeline) | Active (`signalement_award_points`) |
| Requires users | No | Yes (`skip_users=false` in seed) |

---

## Required Airflow Connection

An Airflow connection named `Ecotrack` (or the value passed in `conn_id`) must exist before running this DAG. It must be of type **Postgres** and point to the Ecotrack database.

---

## Runtime Notes

- **Expected duration per run:** under 1 second
- **`n_reports` tuning:** with the default of 3 and a 30-minute schedule, the DAG creates ~144 reports/day and resolves ~72 per day, keeping a realistic open backlog
- **No zone_id:** `zone_id` is left `NULL` on inserted rows — it can be derived from the container if needed
- **Idempotent:** `progress_statuses` is safe to re-run; advancing an already-advanced report is a no-op since the `WHERE status = 'ouvert'` / `'en_traitement'` filters exclude it
