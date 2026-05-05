# DAG — `lasc__ops_containers`

**File:** `dags/lasc__ops_containers.py`
**Tags:** `lasc`, `operations`
**Schedule:** None (API-triggered only)
**Catchup:** disabled
**Max active runs:** 5

---

## Purpose

Applies a bulk operation to a list of containers in response to a call from an external service (e.g. the Ecotrack API). Each run processes one operation type against one list of containers, as described in the JSON payload passed via `conf`.

---

## API Trigger

```
POST /api/v1/dags/lasc__ops_containers/dagRuns
Authorization: Basic <credentials>
Content-Type: application/json

{
  "conf": {
    "type": "battery",
    "date": "2025-05-05",
    "containers": [12, 47, 203]
  }
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `type` | string | yes | Operation to perform — `battery` or `unload` |
| `date` | string `YYYY-MM-DD` | no | Date of the operation — defaults to now if omitted |
| `containers` | integer array | yes | List of `key_container` values to operate on |

---

## Behaviour

| Condition | Result |
|---|---|
| `containers: []` | No-op — DAG exits cleanly at validation |
| Unknown `type` | Validation fails with a descriptive error |
| Container ID not found | Silently skipped (no row matched) |

---

## Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `conn_id` | string | `Ecotrack` | Airflow connection ID — must point to a PostgreSQL connection |

`conn_id` is the only Airflow param; operation inputs (`type`, `date`, `containers`) are passed via `conf` at trigger time.

---

## Supported Operations

### `battery`
Resets `device.battery_pct` to `100` and updates `device.last_seen` to `date` for every IoT device attached to the listed containers.

**Use case:** a maintenance team has replaced the batteries on a set of devices.

**Tables written:** `public.device`

---

### `unload`
Simulates a container emptying event for each listed container:
- Reads current `fill_rate` and `capacity_liters`
- Inserts one row in `public.collections` (`fill_rate_before` = current fill, `fill_rate_after` = 2–5 %, `collected_at` = `date`, `agent_id` = NULL)
- Updates `containers.fill_rate`, `status = 'empty'`, and `last_updated = date` directly

**Use case:** a collection team has emptied a set of containers and the API reports the operation.

**Tables written:** `public.collections`, `public.containers`

---

## Task Graph

```
start ──► validate ──► branch ──► op_battery ──┐
                                 └──► op_unload ──┘
                                                   └──► end (ALL_DONE)
```

---

## Tasks

### `start`
Empty marker task. Entry point of the DAG.

---

### `validate`
**Operator:** `ShortCircuitOperator`

Reads `dag_run.conf` and:
- Returns `False` (short-circuit, no-op) if `containers` is an empty list
- Raises `ValueError` if `type` is not one of the supported operation types
- Returns `True` and logs the operation summary otherwise

---

### `branch`
**Operator:** `BranchPythonOperator`

Routes to `op_battery` or `op_unload` based on `conf["type"]`. The non-selected branch is skipped; `end` runs regardless via `TriggerRule.ALL_DONE`.

---

### `op_battery`
**Operator:** `PythonOperator`

See [battery](#battery) above.

---

### `op_unload`
**Operator:** `PythonOperator`

See [unload](#unload) above.

---

### `end`
Empty marker task. `TriggerRule.ALL_DONE` — runs regardless of which branch was taken or whether `validate` short-circuited.

---

## Dependencies

```
start >> validate >> branch >> [op_battery, op_unload] >> end
```

---

## Required Airflow Connection

An Airflow connection named `Ecotrack` (or the value passed in `conn_id`) must exist before triggering this DAG. It must be of type **Postgres** and point to the Ecotrack database.

---

## Runtime Notes

- **Expected duration per run:** under 1 second
- **`max_active_runs: 5`** — multiple API calls can execute concurrently (e.g. battery + unload at the same time on different container sets); set lower if DB contention is a concern
- **`retries: 0`** — operations are not automatically retried to avoid double-writing collection events or double-resetting batteries; the caller should re-trigger if needed
- **`agent_id` in collections:** left `NULL` for API-triggered unloads since no specific worker is identified in the payload; extend the JSON schema to include an agent field if needed
