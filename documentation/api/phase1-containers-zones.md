# Phase 1 — Containers & Zones

**Sprint:** S3–4
**Epic refs:** E3 (C1–C18), E2 (Z1–Z5)
**Status:** ✅ Done
**Router files:** `routers/containers.py`, `routers/zones.py`
**Schema files:** `schemas/containers.py`, `schemas/zones.py`

---

## Containers

### `GET /containers` — C1
**Status:** ✅

Paginated list of active containers with optional filters.

| Query param | Type | Description |
|---|---|---|
| `zone_id` | int? | Filter by zone |
| `type_id` | int? | Filter by waste type |
| `status` | string? | `empty` / `normal` / `full` / `critical` |
| `fill_rate_min` | float? | Minimum fill rate (0–100) |
| `fill_rate_max` | float? | Maximum fill rate (0–100) |
| `is_active` | bool | Default `true` |
| `page` | int | Default `1` |
| `per_page` | int | Default `20`, max `100` |

**Response:** `PaginatedResponse[ContainerOut]`
**Performance target:** < 200 ms

---

### `GET /containers/critical` — C11
**Status:** ✅

Returns containers where `fill_rate > fill_threshold_pct`. Threshold is per-container (set at creation or inherited from its `container_type`).

**Response:** `List[ContainerOut]`

---

### `GET /containers/stats` — C18
**Status:** ✅

Global statistics across all active containers.

**Response:**
```json
{
  "total_active": 2000,
  "avg_fill_rate": 54.3,
  "median_fill_rate": 51.0,
  "overflow_rate_pct": 8.2,
  "by_status": { "empty": 120, "normal": 1500, "full": 300, "critical": 80 }
}
```

---

### `GET /containers/map` — C6
**Status:** ✅

Returns a GeoJSON FeatureCollection suitable for rendering on a Leaflet map.

**Response:** GeoJSON FeatureCollection where each feature has:
- `geometry`: Point (lng, lat)
- `properties`: `key_container`, `fill_rate`, `status`, `type_id`, `zone_id`

Uses `ST_AsGeoJSON(location)` in SQL. Serialized via `geojson_feature()` + `geojson_collection()` from `utils.py`.

---

### `GET /containers/{id}` — C2
**Status:** ✅

Single container detail with its latest IoT measurement.

**Response:** `ContainerOut` extended with:
```json
{
  "last_measure": {
    "fill_rate": 72.5,
    "temperature": 18.3,
    "battery_pct": 84.0,
    "measured_at": "2026-05-08T10:40:00"
  }
}
```

Latest measure: `SELECT … FROM fill_history WHERE container_id = %s ORDER BY measured_at DESC LIMIT 1`

---

### `POST /containers` — C3
**Status:** ✅

Creates a new container. `zone_id` is auto-assigned by the `assign_zone_to_container` DB trigger using `ST_Within`.

**Request body:** `ContainerCreate` (`lat`, `lng`, `type_id?`, `capacity_liters`, `fill_threshold_pct`)

**SQL note:** coordinates inserted as `ST_SetSRID(ST_MakePoint(%(lng)s, %(lat)s), 4326)`

**Response:** `ContainerOut` (201 Created)

---

### `PUT /containers/{id}` — C4
**Status:** ✅

Updates mutable fields. If `lat`/`lng` change, the `assign_zone_to_container` trigger re-evaluates `zone_id`.

**Request body:** `ContainerUpdate` (all fields optional)

**Response:** `ContainerOut`

---

### `DELETE /containers/{id}` — C5
**Status:** ✅

Soft delete — sets `is_active = false`. The row is never physically deleted.

**Response:** `{"deleted": true}` (200)

---

### `GET /containers/{id}/history` — C10, H5
**Status:** ✅

Time series of IoT measurements for one container. Queries the partitioned `fill_history` table.

| Query param | Type | Description |
|---|---|---|
| `from` | datetime? | Start of period (default: 7 days ago) |
| `to` | datetime? | End of period (default: now) |
| `granularity` | string? | `raw` (default) / `hourly` / `daily` — `hourly` and `daily` query the aggregate tables |

**Response:**
```json
[
  { "measured_at": "2026-05-08T10:00:00", "fill_rate": 68.1, "is_outlier": false },
  ...
]
```

---

### `POST /containers/{id}/measures` — C12
**Status:** ✅

Ingests a single IoT measurement. Applies validation, deduplication, and outlier flagging before inserting into `fill_history`. DB triggers then update `containers.fill_rate`/`status` and generate a threshold notification if needed.

**Request body:** `MeasureCreate`

**Validation rules (C13):**
- `fill_rate` must be in [0, 100]
- `measured_at` defaults to `NOW()` if omitted

**Deduplication (C14):**
- Calls `is_duplicate_measurement(container_id, measured_at)` — rejects if a row for the same container exists within the same clock-minute

**Outlier detection (C15):**
- `fill_rate` delta > 40 % in a single tick → `is_outlier = true` (inserted but flagged)

**Response:** `MeasureOut` (201 Created)

---

## Zones

### `GET /zones` — Z1
**Status:** ✅

List all zones with their polygon geometry serialized as GeoJSON.

**Response:** `List[ZoneOut]`

---

### `POST /zones` — Z1
**Status:** ✅

Creates a zone with a GeoJSON polygon.

**Request body:** `ZoneCreate`

**SQL note:** polygon stored as `ST_SetSRID(ST_GeomFromGeoJSON(%(polygon_json)s), 4326)`

**Response:** `ZoneOut` (201 Created)

---

### `PUT /zones/{id}` — Z1
**Status:** ✅

**Request body:** `ZoneUpdate` (all fields optional)

**Response:** `ZoneOut`

---

### `DELETE /zones/{id}` — Z1
**Status:** ✅

Hard delete. Will fail (FK constraint) if containers or routes reference this zone — return 409 in that case.

**Response:** `{"deleted": true}` (200)

---

### `GET /zones/{id}/containers` — Z2
**Status:** ✅

Returns all active containers whose GPS position falls inside the zone polygon, via `ST_Within`. Delegates to the `get_containers_in_zone(zone_id)` SQL function (uses the GIST index).

**Response:** `List[ContainerOut]`
**Performance target:** < 200 ms for 2 000 containers

---

### `GET /zones/stats` — Z3
**Status:** ✅

Aggregated statistics per zone.

**Response:**
```json
[
  {
    "zone_id": 1,
    "zone_name": "Part-Dieu",
    "container_count": 142,
    "avg_fill_rate": 61.4,
    "overflow_count_30d": 27
  },
  ...
]
```

Sources: `containers` (count, avg), `aggregated_daily_stats` (overflow count over last 30 days).

---

### `GET /zones/density` — Z5
**Status:** ✅

Containers per km² for each zone with a polygon. Delegates to `get_zone_density(zone_id)` SQL function.

**Response:**
```json
[
  { "zone_id": 1, "zone_name": "Part-Dieu", "density_km2": 14.32 },
  ...
]
```

---

## DB Triggers Invoked by This Phase

| Trigger | Table | Fires on | Effect |
|---|---|---|---|
| `containers_assign_zone` | `containers` | INSERT or UPDATE of `location` | Auto-sets `zone_id` via `ST_Within` |
| `fill_history_update_container` | `fill_history` | INSERT | Updates `containers.fill_rate`, `status`, `last_updated` |
| `fill_history_alert` | `fill_history` | INSERT | Inserts a `notifications` row if `fill_rate > threshold` |
