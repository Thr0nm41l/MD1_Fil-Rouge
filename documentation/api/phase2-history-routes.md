# Phase 2 — IoT History & Routes

**Sprint:** S5–6
**Epic refs:** E4 (H5–H7), E3 (C7–C8), E8 (T2–T3, T6, T8)
**Status:** ❌ Not started
**Router files:** `routers/history.py`, `routers/routes.py`
**Prerequisite:** Phase 1 complete

**Additional dependencies to add to `requirements.txt` before starting:**
```
python-multipart==0.0.12   # for CSV file upload
reportlab==4.2.5           # for PDF route sheets
```

---

## History

### `GET /history/{container_id}` — H5
**Status:** ❌

Time series of fill measurements for one container. Supports three granularities backed by different tables.

| Query param | Type | Description |
|---|---|---|
| `from` | datetime? | Start of window (default: 7 days ago) |
| `to` | datetime? | End of window (default: now) |
| `granularity` | string | `raw` (default) · `hourly` · `daily` |

| Granularity | Source table | Resolution |
|---|---|---|
| `raw` | `fill_history` | One row per IoT measurement |
| `hourly` | `aggregated_hourly_stats` | One row per container per hour |
| `daily` | `aggregated_daily_stats` | One row per container per day |

**Response:**
```json
[
  { "bucket": "2026-05-08T10:00:00", "avg_fill_rate": 67.2, "min": 60.1, "max": 73.5 },
  ...
]
```

---

### `GET /history/heatmap-data` — H7
**Status:** ❌

Measurement counts grouped by `(day_of_week × hour_of_day)` — feeds the A8 heatmap chart. Delegates to the `get_heatmap_data(from, to)` SQL function.

| Query param | Type | Description |
|---|---|---|
| `from` | datetime? | Default: 90 days ago |
| `to` | datetime? | Default: now |

**Response:** `[{"day_of_week": 1, "hour_of_day": 8, "count": 2134}, ...]`
(day_of_week: 1=Mon … 7=Sun, as per ISO DOW)

---

## Containers (batch)

### `POST /containers/import` — C7
**Status:** ❌

Batch import of containers from a CSV or JSON file. Returns an import report.

**Request:** `multipart/form-data` with a `file` field (`.csv` or `.json`)

**CSV columns:** `lat`, `lng`, `type_name`, `capacity_liters`, `fill_threshold_pct`

**Processing:**
1. Parse and validate each row (lat/lng range, type name lookup)
2. Skip rows where `is_duplicate_measurement` equivalent exists (same lat/lng already active)
3. Bulk insert valid rows via `COPY` or batched INSERT

**Response:**
```json
{
  "total": 150,
  "inserted": 143,
  "errors": 4,
  "duplicates": 3,
  "error_details": [{ "row": 12, "reason": "unknown type 'Bois'" }, ...]
}
```

---

### `GET /containers/export` — C8
**Status:** ❌

Exports all active containers as a downloadable file.

| Query param | Type | Description |
|---|---|---|
| `format` | string | `csv` (default) or `geojson` |
| `zone_id` | int? | Filter to one zone |

**Response:**
- `csv`: `Content-Type: text/csv`, `Content-Disposition: attachment; filename=containers.csv`
- `geojson`: `Content-Type: application/geo+json`, GeoJSON FeatureCollection

---

## Routes

### `GET /routes` — T2
**Status:** ❌

Paginated list of collection routes.

| Query param | Type | Description |
|---|---|---|
| `zone_id` | int? | Filter by zone |
| `team_id` | int? | Filter by team |
| `status` | string? | `planifiee` / `en_cours` / `terminee` / `annulee` |
| `date_from` | date? | Filter by `scheduled_at` |
| `date_to` | date? | Filter by `scheduled_at` |
| `page` | int | Default `1` |
| `per_page` | int | Default `20` |

**Response:** `PaginatedResponse[RouteOut]`

---

### `GET /routes/stats` — T8
**Status:** ❌

Global route performance KPIs over a date range.

| Query param | Type | Description |
|---|---|---|
| `from` | date? | Default: 30 days ago |
| `to` | date? | Default: today |

**Response:**
```json
{
  "total_routes": 124,
  "total_distance_km": 3840.5,
  "total_collections": 8920,
  "avg_containers_per_route": 71.9,
  "overflows_avoided": 312
}
```

---

### `GET /routes/{id}` — T3
**Status:** ❌

Full route detail including ordered stops and GeoJSON path.

**Response:**
```json
{
  "key_route": 42,
  "zone_id": 3,
  "status": "terminee",
  "scheduled_at": "2026-05-07",
  "distance_m": 18420,
  "path": { "type": "LineString", "coordinates": [[4.83, 45.76], ...] },
  "steps": [
    { "step_order": 1, "container_id": 101, "collected": true, "collected_at": "...", "volume_collected_l": 820 },
    ...
  ]
}
```

`path` uses `ST_AsGeoJSON(path)` from the `routes.path GEOMETRY(LineString, 4326)` column.

---

### `POST /routes/{id}/export` — T6
**Status:** ❌

Generates and returns a route sheet for field agents as PDF or JSON.

| Query param | Type | Description |
|---|---|---|
| `format` | string | `pdf` (default) or `json` |

**PDF content:** route name, date, team, ordered stop list (address, distance to next stop via `ST_Distance`, fill rate at time of scheduling).

**Response (pdf):** `Content-Type: application/pdf`, file attachment
**Response (json):** structured JSON of the same content

Uses `reportlab` — must be in `requirements.txt`.

---

## Data Dependencies

| Endpoint | Requires data from |
|---|---|
| `/history/{id}` | `fill_history` populated by `lasc__livesim_fill` DAG |
| `/history/heatmap-data` | Same — min. 14 days recommended for a meaningful heatmap |
| `/routes` | `routes` + `route_steps` — populated by seed or ops DAGs |
| `/routes/{id}` | `routes.path` — must have LineString geometry inserted |
| `/routes/stats` | `collections` — requires completed collection records |
