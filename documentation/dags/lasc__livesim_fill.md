# DAG — `lasc__livesim_fill`

**File:** `dags/lasc__livesim_fill.py`
**Tags:** `lasc`, `simulation`
**Schedule:** `*/10 * * * *` (every 10 minutes)
**Catchup:** disabled
**Max active runs:** 1

---

## Purpose

Simulates realistic container fill evolution by appending one IoT measurement per container every 10 minutes. Unlike `lasc__seed_data` which generates bulk historical data in one shot, this DAG runs continuously and picks up from the current state stored in the database — making it suitable for keeping a demo or development environment alive with fresh, evolving data.

Row triggers are kept active, so each `fill_history` insert fires the normal pipeline: `containers.fill_rate`, `status`, and `last_updated` are updated automatically.

---

## Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `conn_id` | string | `Ecotrack` | Airflow connection ID — must point to a PostgreSQL connection |
| `skip_reset` | boolean | `false` | Disable resets: fill clamps to 100 % instead of triggering a collection event; battery drains to 0 % instead of flooring at 10 % |

---

## Fill Simulation Model

Each tick advances every active container by one 10-minute step:

| Parameter | Value |
|---|---|
| Tick interval | 10 minutes |
| Rate scale | `FILL_RATE_PER_HOUR / 6` |
| Per-run variability | ±30 % (`U(0.7, 1.3)`) |
| Gaussian noise | `σ = 0.15` per tick |
| Outlier probability | 1 % (`is_outlier = true`) |
| Battery drain per tick | 0.001–0.008 % |

### Temporal multipliers

Applied on top of the base rate every tick, making `hour`, `day_of_week`, `is_weekend`, and `is_peak_hour` features carry real signal in the time-series data:

| Condition | Multiplier | Affected types |
|---|---|---|
| Peak hours 7–9 h and 17–19 h | ×1.5 | all |
| Night 0–5 h | ×0.4 | all |
| Weekend (Sat/Sun) | ×1.3 additional | Organique (4), Général (5) |
| All other hours | ×1.0 | all |

These multipliers are identical to those in `lasc__seed_data` — ensuring the live simulation and the seeded history share the same temporal dynamics, which is required for ML lag and temporal features to generalise from training data to live data.

### Fill rates and thresholds by container type

| Type | Base fill rate/h | Threshold |
|---|---|---|
| Verre | 1.2 % | 80 % |
| Plastique | 2.0 % | 70 % |
| Papier | 1.5 % | 75 % |
| Organique | 3.0 % | 65 % |
| Général | 2.5 % | 70 % |
| Métal | 0.8 % | 80 % |

### Reset behaviour

| Event | `skip_reset=false` (default) | `skip_reset=true` |
|---|---|---|
| Fill ≥ threshold | Reset to 2–8 % (collection event) | Clamp to 100 %, no reset |
| Battery exhausted | Floor at 10 % | Floor at 0 % |
| Battery = 0 % | No measurement emitted | No measurement emitted |

Dead devices (battery ≤ 0 %) are skipped unconditionally regardless of `skip_reset` — no `fill_history` row is inserted and no battery update is written for them.

---

## Task Graph

```
start ──► simulate_fill ──► run_aggregations ──► end (ALL_DONE)
```

---

## Tasks

### `start`
Empty marker task. Entry point of the DAG.

---

### `simulate_fill`
**Operator:** `PythonOperator`

For each container with a live device (battery > 0 %):

1. Reads current `fill_rate` and `battery_pct` from `containers` and `device`
2. Computes the next fill value for the current 10-min tick
3. Applies a collection reset if fill ≥ threshold (unless `skip_reset=true`)
4. Bulk-inserts one row per active container into `public.fill_history`
5. Batch-updates `device.battery_pct` for all active containers

`measured_at` is snapped to the current 10-minute boundary (`HH:MM0`), ensuring idempotency — if the task is retried within the same tick, `ON CONFLICT DO NOTHING` prevents duplicate rows.

**Tables written:** `public.fill_history`, `public.device`
**Tables read:** `public.containers`, `public.device`

---

### `run_aggregations`
**Operator:** `PythonOperator`

Calls `CALL public.aggregate_hourly(timestamp)` and `CALL public.aggregate_daily(date)` for the current tick's hour and day. Both procedures are idempotent (`INSERT … ON CONFLICT DO UPDATE`).

**Tables written:** `public.aggregated_hourly_stats`, `public.aggregated_daily_stats`

---

### `end`
Empty marker task. `TriggerRule.ALL_DONE` — runs regardless of upstream failures.

---

## Dependencies

```
start >> simulate_fill >> run_aggregations >> end
```

---

## Relation to `lasc__seed_data`

| | `lasc__seed_data` | `lasc__livesim_fill` |
|---|---|---|
| Purpose | One-shot bootstrap | Continuous live simulation |
| Schedule | Manual (`None`) | `*/10 * * * *` |
| Triggers | Disabled (`session_replication_role = replica`) | Active |
| Rows per run | ~8 640 000 (bulk, 10-min cadence) | ~2 000 (one per active container) |
| State source | Computed from scratch | Current DB state |
| Temporal multipliers | ✓ peak hours, night, weekend | ✓ peak hours, night, weekend |

Run `lasc__seed_data` first to populate the schema, then enable `lasc__livesim_fill` to keep data evolving.

---

## Required Airflow Connection

An Airflow connection named `Ecotrack` (or the value passed in `conn_id`) must exist before running this DAG. It must be of type **Postgres** and point to the Ecotrack database.

---

## Runtime Notes

- **Expected duration per run:** under 5 seconds for 2 000 containers
- **Dead devices:** containers whose `device.battery_pct ≤ 0` produce no measurement and no battery update that tick
- **Idempotent:** `ON CONFLICT DO NOTHING` on `fill_history` — safe to retry within the same 10-min window
- **`skip_reset=true` use case:** stress-testing dashboards and alerts by letting containers fill to 100 % and devices drain to 0 % without any automatic recovery
