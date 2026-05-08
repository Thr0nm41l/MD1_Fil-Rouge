# Phase 3 — Analytics & Dashboard

**Sprint:** S7–8
**Epic refs:** E6 (A1–A10), E7 (DA3–DA5)
**Status:** ✅ Done
**Router files:** `routers/analytics.py`, `routers/dashboard.py`
**Livrable:** L3 — 8 charts + heatmap + choropleth
**Prerequisite:** Phase 2 complete, ≥ 30 days of `aggregated_daily_stats` data

---

## Common Query Parameters

All analytics endpoints accept a time window:

| Param | Type | Default | Description |
|---|---|---|---|
| `from` | date? | 30 days ago | Start of analysis period |
| `to` | date? | today | End of analysis period |
| `zone_id` | int? | — | Restrict to one zone |

---

## Analytics

### `GET /analytics/kpis` — DA3
**Status:** ✅

Six KPI cards with current value and % variation vs the previous equivalent period.

**Response:**
```json
{
  "volume_collected_l":     { "value": 1842000, "variation_pct": +12.4 },
  "collection_count":       { "value": 4821,    "variation_pct": -2.1  },
  "avg_fill_rate_pct":      { "value": 54.3,    "variation_pct": +1.8  },
  "overflow_count":         { "value": 83,      "variation_pct": -18.3 },
  "total_distance_km":      { "value": 3840.5,  "variation_pct": -5.6  },
  "active_containers":      { "value": 2000,    "variation_pct": 0     }
}
```

Sources: `aggregated_daily_stats` (fill rates, overflows), `collections` (volume, count), `routes` (distance).

---

### `GET /analytics/volume-evolution` — A1
**Status:** ✅

Time series of collected volume grouped by waste type — feeds the stacked area chart (Recharts).

**Response:**
```json
[
  { "date": "2026-04-01", "Verre": 12400, "Plastique": 34800, "Papier": 22100, ... },
  ...
]
```

Source: `collections` JOINed with `containers` and `container_type`.

---

### `GET /analytics/type-distribution` — A2
**Status:** ✅

Percentage and absolute count of containers per waste type — feeds the donut chart (Chart.js).

**Response:**
```json
[
  { "type": "Plastique", "count": 680, "pct": 34.0 },
  { "type": "Verre",     "count": 420, "pct": 21.0 },
  ...
]
```

---

### `GET /analytics/zone-collections` — A3
**Status:** ✅

Total collections (count and volume) per zone over the period, sorted by volume descending — feeds the horizontal bar chart (Chart.js).

**Response:**
```json
[
  { "zone_id": 3, "zone_name": "Part-Dieu", "collection_count": 842, "volume_l": 420000 },
  ...
]
```

---

### `GET /analytics/fill-distribution` — A4
**Status:** ✅

Distribution of fill rates in 10 % buckets — feeds the histogram (Chart.js).

**Response:**
```json
[
  { "bucket_min": 0,  "bucket_max": 10,  "count": 42  },
  { "bucket_min": 10, "bucket_max": 20,  "count": 118 },
  ...
  { "bucket_min": 90, "bucket_max": 100, "count": 83  }
]
```

Source: `aggregated_daily_stats.avg_fill_rate` grouped into `width_bucket` intervals.

---

### `GET /analytics/fill-evolution` — A5
**Status:** ✅

Daily average fill rate across all active containers, with optional 7-day moving average — feeds the line chart (Recharts).

| Query param | Type | Description |
|---|---|---|
| `moving_avg` | bool | Default `false` — if true, adds a `moving_avg_7d` field per row |

**Response:**
```json
[
  { "date": "2026-04-01", "avg_fill_rate": 52.1, "moving_avg_7d": 51.4 },
  ...
]
```

Source: `aggregated_daily_stats` averaged across all containers per day.

---

### `GET /analytics/route-performance` — A6
**Status:** ✅

One data point per route: distance vs volume collected — feeds the scatter plot (Recharts, bubble = container count).

**Response:**
```json
[
  { "route_id": 12, "distance_km": 18.4, "volume_collected_l": 84200, "container_count": 71 },
  ...
]
```

Source: `routes` JOINed with `collections` and `route_steps`.

---

### `GET /analytics/incidents` — A7
**Status:** ✅

Chronological list of signalements and threshold-breach notifications — feeds the timeline chart (D3.js).

| Query param | Type | Description |
|---|---|---|
| `type` | string? | `signalement` / `notification` / both (default) |

**Response:**
```json
[
  { "timestamp": "2026-05-08T09:14:00", "type": "signalement", "zone_id": 2, "description": "Conteneur renversé" },
  { "timestamp": "2026-05-08T09:22:00", "type": "notification", "container_id": 104, "content": "Seuil dépassé: 91.3%" },
  ...
]
```

---

### `GET /analytics/heatmap` — A8
**Status:** ✅

Measurement counts grouped by `(day_of_week × hour_of_day)` — feeds the Nivo/D3.js heatmap.

Delegates directly to `get_heatmap_data(p_from, p_to)` SQL function (same as `/history/heatmap-data` but scoped to analytics context with default 90-day window).

**Response:** `[{"day_of_week": 1, "hour_of_day": 8, "count": 2134}, ...]`

---

### `GET /analytics/choropleth` — A9
**Status:** ✅

Per-zone density and average fill rate with polygon geometry — feeds the Leaflet choropleth map.

Delegates to `get_choropleth_data()` SQL function.

**Response:**
```json
[
  {
    "zone_id": 1,
    "zone_name": "Confluence",
    "polygon": { "type": "Polygon", "coordinates": [...] },
    "density_km2": 14.32,
    "avg_fill_rate": 61.4
  },
  ...
]
```

Requires zones to have polygon geometry set (Phase 1 prerequisite).

---

### `GET /analytics/costs-roi` — A10
**Status:** ✅

Cost and ROI analysis comparing actual vs theoretical unoptimized routes — feeds the mixed bar+line chart (Recharts).

| Computed metric | Formula |
|---|---|
| `cost_per_km` | Fixed rate (configurable, default €1.20/km) |
| `total_cost` | `distance_km × cost_per_km` |
| `estimated_savings` | Distance reduction vs baseline (20 % target from T10) |
| `co2_saved_kg` | `distance_saved_km × 0.27` (avg CO₂ per km) |

**Response:**
```json
[
  { "month": "2026-04", "total_cost": 4608.60, "estimated_savings": 921.72, "co2_saved_kg": 210.8 },
  ...
]
```

---

## Dashboard

### `GET /dashboard/config` — DA4
**Status:** ✅

Returns the saved layout configuration for the authenticated user.

**Response:**
```json
{
  "user_id": 42,
  "layout_config": {
    "charts": ["kpis", "volume-evolution", "heatmap", "choropleth"],
    "grid": [["kpis", "volume-evolution"], ["heatmap", "choropleth"]]
  },
  "updated_at": "2026-05-01T14:22:00"
}
```

Returns `{}` layout if the user has no saved config yet.
Requires `set_user_context(conn, user_id)` before querying (RLS on `dashboard_config`).

---

### `PUT /dashboard/config` — DA5
**Status:** ✅

Saves or updates the authenticated user's dashboard layout. Uses `INSERT … ON CONFLICT (user_id) DO UPDATE`.

**Request body:**
```json
{
  "layout_config": {
    "charts": ["kpis", "fill-evolution", "type-distribution"],
    "grid": [["kpis"], ["fill-evolution", "type-distribution"]]
  }
}
```

**Response:** saved config (same shape as GET)
