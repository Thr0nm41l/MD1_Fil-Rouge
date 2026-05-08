# API Endpoint Roadmap — ECOTRACK

**Stack:** FastAPI + psycopg2 · PostgreSQL + PostGIS
**Deployment:** `datalake` namespace (alongside PostgreSQL)

---

## Foundation
*Pre-Sprint 3 — all items completed*

| Item | Status |
|------|--------|
| `db.py` — `ThreadedConnectionPool`, `get_db()` dependency, `set_user_context()` | ✅ Done |
| `utils.py` — `geojson_feature`, `geojson_collection`, `paginate_query` | ✅ Done |
| `schemas/common.py` — `PaginatedResponse[T]` | ✅ Done |
| `schemas/containers.py` — `ContainerCreate/Update/Out`, `MeasureCreate/Out` | ✅ Done |
| `schemas/zones.py` — `ZoneCreate/Update/Out` | ✅ Done |
| `routers/` stubs for all 9 modules | ✅ Done |
| `main.py` — lifespan pool init, all routers registered | ✅ Done |
| `Dockerfile` — fixed entrypoint, copies `routers/` and `schemas/` | ✅ Done |
| `helmcharts/apiservice-deployment.yaml` — fixed and completed | ✅ Done |

---

## K8s Deployment
*`helmcharts/apiservice-deployment.yaml`*

| Item | Decision |
|------|----------|
| Namespace | `datalake` — co-located with PostgreSQL, reuses existing `postgres-credentials` secret |
| `POSTGRES_HOST` | `postgres-postgresql` (short in-namespace DNS) |
| `POSTGRES_PASSWORD` | `secretKeyRef` → `postgres-credentials / postgres-password` |
| Liveness probe | `GET /health` — `initialDelaySeconds: 15`, `periodSeconds: 30` |
| Readiness probe | `GET /health` — `initialDelaySeconds: 5`, `periodSeconds: 10` |
| Service | `ClusterIP` on port 8000 |
| `imagePullPolicy` | `IfNotPresent` (Minikube local image) |

Port-forward to access locally:
```bash
kubectl port-forward svc/apiservice 8000:8000 -n datalake
```

---

## Phase 1 — Containers & Zones Core CRUD (Sprint 1 · S3–4)
*Livrable L2 dependency — pipeline ingestion fonctionnel*

### Prerequisites

| # | Prerequisite | Status |
|---|-------------|--------|
| 1 | PostgreSQL + PostGIS deployed and `setup_complete.sql` applied | ⚠️ SQL written — verify with `SELECT PostGIS_Version();` |
| 2 | `container_type` seeded (Verre, Plastique, Papier…) | ✅ Seeded in `setup_complete.sql` |
| 3 | At least one zone with a polygon seeded | ⚠️ Table exists, no polygon seed — depends on `lasc__seed_data` DAG |
| 4 | DB functions: `assign_zone_to_container`, `is_duplicate_measurement`, `update_container_fill_status`, `generate_fill_alert` | ✅ All defined in `setup_complete.sql` |
| 5 | DB triggers active on `containers` and `fill_history` | ✅ Defined in `setup_complete.sql` |
| 6 | FastAPI + psycopg2 installed | ✅ In `requirements.txt` |
| 7 | `db.py` connection pool module | ✅ Created |
| 8 | Router/schema file structure (`routers/`, `schemas/`) | ✅ Created |
| 9 | Pydantic models for Container, Zone, Measure | ✅ Created in `schemas/` |
| 10 | GeoJSON serialization helper | ✅ `utils.py` — `geojson_feature`, `geojson_collection` |
| 11 | Shared pagination utility | ✅ `utils.py` — `paginate_query` + `schemas/common.py` — `PaginatedResponse` |
| 12 | `Dockerfile` references correct entrypoint | ✅ Fixed |

**All prerequisites met — Phase 1 can start.**

### Endpoints

| Method | Endpoint | Epic ref | Status | Tables / Functions |
|--------|----------|----------|--------|--------------------|
| `GET` | `/containers` | C1 | ✅ | `containers`, `container_type`, `zones` — paginated, filters: `zone_id`, `type_id`, `status`, `fill_rate_min/max`, `is_active` |
| `GET` | `/containers/critical` | C11 | ✅ | `containers` WHERE `fill_rate > fill_threshold_pct` |
| `GET` | `/containers/stats` | C18 | ✅ | `containers`, `aggregated_daily_stats` — avg, median, overflow rate |
| `GET` | `/containers/map` | C6 | ✅ | `containers` — GeoJSON FeatureCollection via `ST_AsGeoJSON` |
| `GET` | `/containers/{id}` | C2 | ✅ | `containers` + latest row from `fill_history` |
| `POST` | `/containers` | C3 | ✅ | INSERT into `containers` — trigger `assign_zone_to_container` auto-fills `zone_id` |
| `PUT` | `/containers/{id}` | C4 | ✅ | UPDATE `containers` (location, type, capacity, thresholds) |
| `DELETE` | `/containers/{id}` | C5 | ✅ | `UPDATE SET is_active = false` — soft delete only |
| `GET` | `/containers/{id}/history` | C10, H5 | ✅ | `fill_history` partitioned table — filterable by `from`/`to` date |
| `POST` | `/containers/{id}/measures` | C12 | ✅ | INSERT into `fill_history` — validate 0–100, dedup via `is_duplicate_measurement()`, triggers `update_container_fill_status` + `generate_fill_alert` |
| `GET` | `/zones` | Z1 | ✅ | `zones` |
| `POST` | `/zones` | Z1 | ✅ | INSERT — polygon as GeoJSON → `GEOMETRY(Polygon, 4326)` |
| `PUT` | `/zones/{id}` | Z1 | ✅ | UPDATE `zones` |
| `DELETE` | `/zones/{id}` | Z1 | ✅ | Hard delete — 409 if FK constraint violated |
| `GET` | `/zones/{id}/containers` | Z2 | ✅ | `get_containers_in_zone()` — `ST_Within` + GIST index |
| `GET` | `/zones/stats` | Z3 | ✅ | `zones` + `containers` + `aggregated_daily_stats` |
| `GET` | `/zones/density` | Z5 | ✅ | direct SQL — `COUNT / ST_Area(polygon::geography)` |

---

## Phase 2 — IoT History & Spatial Features (Sprint 2 · S5–6)
*Completes E3/E4 — feeds dashboard data layer*

### Prerequisites

| # | Prerequisite | Status |
|---|-------------|--------|
| 1 | All Phase 1 endpoints implemented and tested | ✅ Done |
| 2 | `fill_history` populated with simulated data | ✅ `lasc__livesim_fill` DAG runs every 10 min |
| 3 | `aggregated_hourly_stats` / `aggregated_daily_stats` being populated | ✅ Same DAG calls `aggregate_hourly` + `aggregate_daily` |
| 4 | `get_heatmap_data()` DB function present | ✅ Defined in `setup_complete.sql` |
| 5 | `routes`, `route_steps`, `collections` tables present | ✅ Defined in `setup_complete.sql` |
| 6 | `python-multipart` for CSV upload | ⚠️ Commented out in `requirements.txt` — uncomment before `/containers/import` |
| 7 | `reportlab` for PDF route sheets | ⚠️ Commented out in `requirements.txt` — uncomment before `/routes/{id}/export` |

**Blocking items:** #6 (for `/containers/import`), #7 (for `/routes/{id}/export`).

### Endpoints

| Method | Endpoint | Epic ref | Status | Tables / Functions |
|--------|----------|----------|--------|--------------------|
| `GET` | `/history/{container_id}` | H5 | ✅ | `fill_history` / `aggregated_hourly_stats` / `aggregated_daily_stats` — `granularity=raw\|hourly\|daily` |
| `GET` | `/history/heatmap-data` | H7 | ✅ | `get_heatmap_data()` — `{day_of_week, hour_of_day, count}` |
| `POST` | `/containers/import` | C7 | ✅ | Batch CSV/JSON — validate, dedup via `ST_DWithin`, SAVEPOINT per row |
| `GET` | `/containers/export` | C8 | ✅ | `StreamingResponse` CSV or GeoJSON — `format=csv\|geojson` |
| `GET` | `/routes` | T2 | ✅ | `routes` — paginated, filters: `zone_id`, `team_id`, `status`, `date_from/to` |
| `GET` | `/routes/stats` | T8 | ✅ | `routes` + `collections` + `containers` — distance, collections, overflows avoided |
| `GET` | `/routes/{id}` | T3 | ✅ | `routes` + `route_steps` — GeoJSON LineString path + ordered steps |
| `POST` | `/routes/{id}/export` | T6 | ✅ | PDF (reportlab) or JSON route sheet |

---

## Phase 3 — Analytics Endpoints (Sprint 3 · S7–8)
*Livrable L3 — 8 charts + heatmap + choropleth*

### Prerequisites

| # | Prerequisite | Status |
|---|-------------|--------|
| 1 | All Phase 2 endpoints implemented and tested | ✅ Done |
| 2 | `aggregated_daily_stats` with ≥ 30 days of history | ⚠️ Depends on how long `lasc__livesim_fill` has been running |
| 3 | `collections` table has data | ⚠️ Depends on livesim DAGs and seed data |
| 4 | `signalements` table has data | ⚠️ `lasc__livesim_signalements` DAG exists — verify it is active |
| 5 | `get_choropleth_data()` DB function present | ✅ Defined in `setup_complete.sql` |
| 6 | Zones have polygon geometry | ⚠️ Same as Phase 1 prerequisite #3 |
| 7 | `dashboard_config` table present | ✅ Defined in `setup_complete.sql` |

**Blocking items:** #1, #2 and #3 (data volume — start `lasc__livesim_fill` early).

### Endpoints

| Method | Endpoint | Epic ref | Status | Tables / Functions |
|--------|----------|----------|--------|--------------------|
| `GET` | `/analytics/kpis` | DA3 | ✅ | `aggregated_daily_stats`, `collections`, `routes` — 6 KPIs + % variation vs prev period |
| `GET` | `/analytics/volume-evolution` | A1 | ✅ | `collections` + `container_type` — pivoted by type name in Python |
| `GET` | `/analytics/type-distribution` | A2 | ✅ | `containers` + `container_type` — count + pct |
| `GET` | `/analytics/zone-collections` | A3 | ✅ | `collections` + `zones` — count/volume per zone |
| `GET` | `/analytics/fill-distribution` | A4 | ✅ | `aggregated_daily_stats` — `FLOOR(fill/10)*10` buckets |
| `GET` | `/analytics/fill-evolution` | A5 | ✅ | `aggregated_daily_stats` — daily avg + optional 7-day moving avg in Python |
| `GET` | `/analytics/route-performance` | A6 | ✅ | `routes` + `collections` + `route_steps` — scatter points |
| `GET` | `/analytics/incidents` | A7 | ✅ | `signalements` UNION `notifications` — type filter, zone filter |
| `GET` | `/analytics/heatmap` | A8 | ✅ | `get_heatmap_data()` — reuses `HeatmapPoint` from `schemas/history.py` |
| `GET` | `/analytics/choropleth` | A9 | ✅ | `get_choropleth_data()` + `ST_AsGeoJSON` wrapper |
| `GET` | `/analytics/costs-roi` | A10 | ✅ | `routes` monthly distance → cost/savings/CO₂ computed in Python |
| `GET` | `/dashboard/config` | DA4 | ✅ | `dashboard_config` — returns `{}` layout if no config saved |
| `PUT` | `/dashboard/config` | DA5 | ✅ | UPSERT `dashboard_config` on `user_id` unique constraint |

---

## Phase 4 — Gamification, ML & Reports (Sprint 4–5 · S9–12)
*Livrable L4 — ML R²>0.65 + reports + full gamification*

### Prerequisites

| # | Prerequisite | Status |
|---|-------------|--------|
| 1 | All Phase 3 endpoints implemented and tested | ✅ Done |
| 2 | Gamification tables present | ✅ Defined in `setup_complete.sql` |
| 3 | `badges` catalogue seeded (30 badges) | ✅ Seeded in `setup_complete.sql` |
| 4 | `get_leaderboard()` DB function present | ✅ Defined in `setup_complete.sql` |
| 5 | Points triggers active (`signalement_award_points`, `user_badges_award_points`) | ✅ Defined in `setup_complete.sql` |
| 6 | `user_points` has data | ⚠️ Depends on livesim DAGs running with user associations |
| 7 | ML model trained (ML1–ML4) — ≥ 30 days `fill_history`, features engineered, model serialized | ❌ Not started — start in parallel with Phase 3 |
| 8 | `scikit-learn`, `pandas`, `numpy` in `requirements.txt` | ⚠️ Commented out — uncomment before `/ml/predict` |
| 9 | `reportlab` in `requirements.txt` | ⚠️ Commented out — uncomment before `/reports/generate` |
| 10 | `openpyxl` in `requirements.txt` | ⚠️ Commented out — uncomment before `/reports/generate` |
| 11 | Async background task mechanism (`BackgroundTasks`) | ⚠️ FastAPI built-in — no extra dep, just wire it up in `routers/reports.py` |
| 12 | File storage path for generated reports | ❌ Not configured — needs a PVC or local volume mount in the deployment YAML |

**Blocking items:** #1, #7 (longest lead time — start now), #12.

### Endpoints

| Method | Endpoint | Epic ref | Status | Tables / Functions |
|--------|----------|----------|--------|--------------------|
| `GET` | `/leaderboard` | GAM3 | ❌ | `get_leaderboard(limit=100)` |
| `GET` | `/leaderboard/weekly` | GAM4 | ❌ | `get_leaderboard()` filtered to current ISO week |
| `GET` | `/leaderboard/monthly` | GAM4 | ❌ | `get_leaderboard()` filtered to current month |
| `GET` | `/users/{id}/badges` | GAM7 | ❌ | `user_badges` + `badges` — earned + progress toward next |
| `GET` | `/users/{id}/impact` | GAM11 | ❌ | `user_points` + `signalements` + `collections` — CO₂, reports, points |
| `GET` | `/defis` | GAM9 | ❌ | `defis` + `defi_participations` — active challenges + collective progress |
| `POST` | `/defis/{id}/join` | GAM8 | ❌ | INSERT into `defi_participations` |
| `POST` | `/ml/predict` | ML5 | ❌ | Load trained model → `predicted_fill_rate`, store in `ml_predictions` |
| `POST` | `/reports/generate` | R4 | ❌ | INSERT `reports` (pending) → async PDF/Excel via `BackgroundTasks` |
| `GET` | `/reports/{id}/download` | R5 | ❌ | Stream file — check `status = 'ready'` first |

---

## Cross-cutting concerns

| Concern | Implementation | Status |
|---------|----------------|--------|
| DB connection pool | `ThreadedConnectionPool` in `db.py` | ✅ Done |
| GeoJSON serialization | `ST_AsGeoJSON()` + `utils.py` helpers | ✅ Done |
| Pagination | `paginate_query()` + `PaginatedResponse[T]` | ✅ Done |
| RLS context | `set_user_context(conn, user_id)` in `db.py` | ✅ Helper ready — wire up per route |
| Query params validation | FastAPI `Query()` with type hints | ✅ Done |
| Error handling | `HTTPException` for DB errors, 404, 422 | ✅ Done |

---

## File structure

```
apiservice/
├── main.py              # app init, lifespan, router registration
├── db.py                # connection pool, get_db(), set_user_context()
├── utils.py             # geojson_feature/collection, paginate_query
├── requirements.txt     # deps (Phase 2/4 deps commented, uncomment when needed)
├── Dockerfile           # python:3.12-slim — copies main.py, db.py, utils.py, routers/, schemas/
├── routers/
│   ├── containers.py    # Phase 1 — ✅ implemented
│   ├── zones.py         # Phase 1 — ✅ implemented
│   ├── history.py       # Phase 2 — ✅ implemented
│   ├── routes.py        # Phase 2 — ✅ implemented
│   ├── analytics.py     # Phase 3 — ✅ implemented
│   ├── dashboard.py     # Phase 3 — ✅ implemented
│   ├── gamification.py  # Phase 4 — stub
│   ├── ml.py            # Phase 4 — stub
│   └── reports.py       # Phase 4 — stub
└── schemas/
    ├── common.py        # PaginatedResponse[T]
    ├── containers.py    # ContainerCreate/Update/Out, MeasureCreate/Out, ImportReport
    ├── zones.py         # ZoneCreate/Update/Out
    ├── history.py       # HistoryBucket, HeatmapPoint
    ├── routes.py        # RouteOut, RouteDetail, RouteStep, RouteStats
    ├── analytics.py     # KpisResponse, FillEvolutionPoint, ChoroplethZone, etc.
    └── dashboard.py     # DashboardConfig, DashboardConfigUpdate

helmcharts/
└── apiservice-deployment.yaml  # Deployment + Service in datalake namespace
```

**Total: ~40 endpoints** across 4 phases.
