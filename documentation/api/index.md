# API Service — ECOTRACK

**File:** `apiservice/main.py`
**Framework:** FastAPI 0.115 + uvicorn
**Database driver:** psycopg2-binary 2.9.9
**Port:** 8000

---

## Purpose

REST API layer for the ECOTRACK platform. Exposes all data stored in the PostgreSQL/PostGIS database to frontend dashboards, IoT devices, and the ML prediction pipeline.

---

## File Structure

```
apiservice/
├── main.py              # App entry point — lifespan, router registration
├── db.py                # Connection pool, get_db() FastAPI dependency, RLS helper
├── utils.py             # GeoJSON serialization helpers, pagination utility
├── requirements.txt     # Python dependencies (phased)
├── Dockerfile           # python:3.12-slim image
├── .env                 # Local environment variables (not committed)
├── .env.example         # Environment variable template
├── schemas/
│   ├── common.py        # PaginatedResponse[T]
│   ├── containers.py    # ContainerCreate/Update/Out, MeasureCreate/Out
│   └── zones.py         # ZoneCreate/Update/Out
└── routers/
    ├── containers.py    # Phase 1
    ├── zones.py         # Phase 1
    ├── history.py       # Phase 2
    ├── routes.py        # Phase 2
    ├── analytics.py     # Phase 3
    ├── dashboard.py     # Phase 3
    ├── gamification.py  # Phase 4
    ├── ml.py            # Phase 4
    └── reports.py       # Phase 4
```

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `POSTGRES_HOST` | — | PostgreSQL host |
| `POSTGRES_PORT` | `5432` | PostgreSQL port |
| `POSTGRES_DB` | — | Database name (`Ecotrack`) |
| `POSTGRES_USER` | — | Database user |
| `POSTGRES_PASSWORD` | — | Database password |

---

## Endpoint Phases

| Phase | Sprint | Status | Document |
|---|---|---|---|
| Foundation (pool, schemas, utils) | Pre-S3 | ✅ Done | [foundation.md](foundation.md) |
| Phase 1 — Containers & Zones | S3–4 | ✅ Done | [phase1-containers-zones.md](phase1-containers-zones.md) |
| Phase 2 — IoT History & Routes | S5–6 | ✅ Done | [phase2-history-routes.md](phase2-history-routes.md) |
| Phase 3 — Analytics & Dashboard | S7–8 | ✅ Done | [phase3-analytics.md](phase3-analytics.md) |
| Phase 4 — Gamification, ML & Reports | S9–12 | ⚠️ Partial (ML pending model) | [phase4-gamification-ml-reports.md](phase4-gamification-ml-reports.md) |

---

## Quick Start (local)

```bash
cd apiservice
pip install -r requirements.txt
cp .env.example .env
# fill in .env with your database credentials
uvicorn main:app --reload --port 8000
```

Interactive docs available at `http://localhost:8000/docs` once the server is running.

---

## Endpoints Summary

| Method | Path | Phase | Status |
|--------|------|-------|--------|
| `GET` | `/health` | Foundation | ✅ |
| `GET` | `/containers` | 1 | ✅ |
| `GET` | `/containers/critical` | 1 | ✅ |
| `GET` | `/containers/stats` | 1 | ✅ |
| `GET` | `/containers/map` | 1 | ✅ |
| `GET` | `/containers/{id}` | 1 | ✅ |
| `POST` | `/containers` | 1 | ✅ |
| `PUT` | `/containers/{id}` | 1 | ✅ |
| `DELETE` | `/containers/{id}` | 1 | ✅ |
| `GET` | `/containers/{id}/history` | 1 | ✅ |
| `POST` | `/containers/{id}/measures` | 1 | ✅ |
| `GET` | `/zones` | 1 | ✅ |
| `POST` | `/zones` | 1 | ✅ |
| `PUT` | `/zones/{id}` | 1 | ✅ |
| `DELETE` | `/zones/{id}` | 1 | ✅ |
| `GET` | `/zones/{id}/containers` | 1 | ✅ |
| `GET` | `/zones/stats` | 1 | ✅ |
| `GET` | `/zones/density` | 1 | ✅ |
| `GET` | `/history/{container_id}` | 2 | ✅ |
| `GET` | `/history/heatmap-data` | 2 | ✅ |
| `POST` | `/containers/import` | 2 | ✅ |
| `GET` | `/containers/export` | 2 | ✅ |
| `GET` | `/routes` | 2 | ✅ |
| `GET` | `/routes/stats` | 2 | ✅ |
| `GET` | `/routes/{id}` | 2 | ✅ |
| `POST` | `/routes/{id}/export` | 2 | ✅ |
| `GET` | `/analytics/kpis` | 3 | ✅ |
| `GET` | `/analytics/volume-evolution` | 3 | ✅ |
| `GET` | `/analytics/type-distribution` | 3 | ✅ |
| `GET` | `/analytics/zone-collections` | 3 | ✅ |
| `GET` | `/analytics/fill-distribution` | 3 | ✅ |
| `GET` | `/analytics/fill-evolution` | 3 | ✅ |
| `GET` | `/analytics/route-performance` | 3 | ✅ |
| `GET` | `/analytics/incidents` | 3 | ✅ |
| `GET` | `/analytics/heatmap` | 3 | ✅ |
| `GET` | `/analytics/choropleth` | 3 | ✅ |
| `GET` | `/analytics/costs-roi` | 3 | ✅ |
| `GET` | `/dashboard/config` | 3 | ✅ |
| `PUT` | `/dashboard/config` | 3 | ✅ |
| `GET` | `/leaderboard` | 4 | ✅ |
| `GET` | `/leaderboard/weekly` | 4 | ✅ |
| `GET` | `/leaderboard/monthly` | 4 | ✅ |
| `GET` | `/users/{id}/badges` | 4 | ✅ |
| `GET` | `/users/{id}/impact` | 4 | ✅ |
| `GET` | `/defis` | 4 | ✅ |
| `POST` | `/defis/{id}/join` | 4 | ✅ |
| `POST` | `/ml/predict` | 4 | ⚠️ stub — pending model |
| `POST` | `/reports/generate` | 4 | ✅ |
| `GET` | `/reports/{id}/download` | 4 | ✅ |
