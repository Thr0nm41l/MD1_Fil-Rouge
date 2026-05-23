# API Foundation

**Status:** ✅ Done
**Files:** `db.py`, `utils.py`, `schemas/`, `routers/` (stubs), `main.py`

---

## Purpose

Shared infrastructure used by all route handlers: database connection pooling, GeoJSON serialization, pagination, and Pydantic schemas. All Phase 1–4 endpoints depend on this foundation.

---

## `db.py` — Connection Pool

Wraps `psycopg2.pool.ThreadedConnectionPool` with a context manager and a FastAPI dependency.

| Symbol | Type | Description |
|---|---|---|
| `init_pool()` | function | Called on app startup — creates the pool from env vars |
| `close_pool()` | function | Called on app shutdown — releases all connections |
| `get_conn()` | context manager | Acquires a connection, commits on success, rolls back on exception, returns to pool |
| `get_db()` | FastAPI dependency | Yields a connection via `get_conn()` — use with `Depends(get_db)` in route handlers |
| `set_user_context(conn, user_id)` | function | Runs `SET LOCAL app.user_id = ?` — required before any query on RLS-protected tables (`users`, `signalements`, `notifications`, `user_role`) |

**Pool configuration:**

| Parameter | Value |
|---|---|
| `minconn` | 2 |
| `maxconn` | 10 |
| Port default | 5432 |

**Usage in a route handler:**

```python
from fastapi import Depends
from db import get_db

@router.get("/{id}")
def get_item(id: int, conn=Depends(get_db)):
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM items WHERE key = %s", (id,))
        row = cur.fetchone()
    ...
```

---

## `utils.py` — Shared Helpers

### GeoJSON helpers

| Function | Input | Output | Use case |
|---|---|---|---|
| `geojson_feature(geometry_json, properties)` | geometry as JSON string or dict + properties dict | GeoJSON Feature object | Single container or zone |
| `geojson_collection(features)` | list of Feature dicts | GeoJSON FeatureCollection | `GET /containers/map`, `GET /analytics/choropleth` |
| `geojson_geometry(geometry_json)` | JSON string or `None` | dict or `None` | Deserializing a stored polygon/point |

All geometry is serialized from PostgreSQL using `ST_AsGeoJSON(column)` in the SQL query, then parsed by these helpers.

### Pagination helper

```python
paginate_query(query, params, page, per_page) -> (str, tuple)
```

Appends `LIMIT %s OFFSET %s` to a SQL string and returns the updated params tuple. The calling route is responsible for running a separate `COUNT(*)` query to populate `PaginatedResponse.total`.

---

## `schemas/common.py`

| Model | Fields | Description |
|---|---|---|
| `PaginatedResponse[T]` | `page`, `per_page`, `total`, `items: List[T]` | Generic paginated wrapper used by all list endpoints |

---

## `schemas/containers.py`

| Model | Fields | Description |
|---|---|---|
| `ContainerCreate` | `lat`, `lng`, `type_id?`, `capacity_liters`, `fill_threshold_pct` | Body for `POST /containers` |
| `ContainerUpdate` | all fields optional | Body for `PUT /containers/{id}` |
| `ContainerOut` | `key_container`, `lat?`, `lng?`, `type_id?`, `zone_id?`, `capacity_liters`, `fill_rate`, `status`, `fill_threshold_pct`, `last_updated`, `is_active` | Response for all container reads |
| `MeasureCreate` | `fill_rate` (0–100), `temperature?`, `battery_pct?`, `measured_at?`, `device_id?` | Body for `POST /containers/{id}/measures` |
| `MeasureOut` | `key_history`, `container_id`, `fill_rate`, `temperature?`, `battery_pct?`, `is_outlier`, `measured_at` | Response for measure ingestion |

**Notes:**
- `lat`/`lng` are extracted from the PostGIS `location` column using `ST_Y(location)` / `ST_X(location)` in SELECT queries.
- On write, coordinates are converted to `ST_SetSRID(ST_MakePoint(lng, lat), 4326)`.
- `zone_id` is auto-populated by the `assign_zone_to_container` trigger on INSERT/UPDATE of `location`.

---

## `schemas/zones.py`

| Model | Fields | Description |
|---|---|---|
| `ZoneCreate` | `name?`, `postal_code?`, `polygon` (GeoJSON dict) | Body for `POST /zones` |
| `ZoneUpdate` | all fields optional | Body for `PUT /zones/{id}` |
| `ZoneOut` | `key_zone`, `name?`, `postal_code?`, `polygon?` (GeoJSON dict) | Response for all zone reads |

**Notes:**
- `polygon` is stored as `GEOMETRY(Polygon, 4326)` using `ST_GeomFromGeoJSON(json.dumps(polygon))`.
- On read, serialized back to GeoJSON dict via `ST_AsGeoJSON(polygon)`.

---

## `main.py` — App Entry Point

Registers all routers with their prefixes and manages the connection pool lifespan.

| Router | Prefix | Tag | Phase |
|---|---|---|---|
| `containers` | `/containers` | containers | 1 |
| `zones` | `/zones` | zones | 1 |
| `history` | `/history` | history | 2 |
| `routes` | `/routes` | routes | 2 |
| `analytics` | `/analytics` | analytics | 3 |
| `dashboard` | `/dashboard` | dashboard | 3 |
| `gamification` | *(none)* | gamification | 4 |
| `ml` | `/ml` | ml | 4 |
| `reports` | `/reports` | reports | 4 |

The `lifespan` context manager calls `init_pool()` on startup and `close_pool()` on shutdown.

---

## `requirements.txt`

| Package | Version | Phase |
|---|---|---|
| `fastapi` | 0.115.0 | All |
| `uvicorn[standard]` | 0.32.0 | All |
| `psycopg2-binary` | 2.9.9 | All |
| `python-dotenv` | 1.0.1 | All (local dev) |
| `python-multipart` | 0.0.12 | 2 — add before `/containers/import` |
| `reportlab` | 4.2.5 | 2 — add before `/routes/{id}/export` |
| `scikit-learn` | 1.5.2 | 4 — add before `/ml/predict` |
| `pandas` | 2.2.3 | 4 |
| `numpy` | 1.26.4 | 4 |
| `openpyxl` | 3.1.5 | 4 — add before `/reports/generate` |
