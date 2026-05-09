# Phase 4 — Gamification, ML & Reports

**Sprint:** S9–12
**Epic refs:** E9 (GAM3–GAM11), E10 (ML5), E7 (R4–R5)
**Status:** ⚠️ Partial — gamification, reports, leaderboard ✅ · ML pending trained model
**Router files:** `routers/gamification.py`, `routers/ml.py`, `routers/reports.py`
**Livrable:** L4 — ML R²>0.65, API prédiction, rapports PDF/Excel
**Prerequisite:** Phase 3 complete + ML model trained (ML1–ML4) + ≥ 30 days `fill_history`

**Additional dependencies to add to `requirements.txt` before starting:**
```
scikit-learn==1.5.2
pandas==2.2.3
numpy==1.26.4
openpyxl==3.1.5
```

---

## Gamification

### `GET /leaderboard` — GAM3
**Status:** ❌

Top 100 citizens ranked by cumulative points. Delegates to `get_leaderboard(limit=100)` SQL function.

**Response:**
```json
[
  { "rank": 1, "user_id": 812, "name": "Dupont", "first_name": "Marie", "total_points": 4820 },
  ...
]
```

---

### `GET /leaderboard/weekly` — GAM4
**Status:** ❌

Same as `/leaderboard` but filtered to the current ISO week (`date_trunc('week', now())`).

Calls `get_leaderboard(p_from=start_of_week, p_to=now)`.

**Response:** same shape as `/leaderboard`

---

### `GET /leaderboard/monthly` — GAM4
**Status:** ❌

Same as `/leaderboard` but filtered to the current calendar month.

Calls `get_leaderboard(p_from=start_of_month, p_to=now)`.

**Response:** same shape as `/leaderboard`

---

### `GET /users/{id}/badges` — GAM7
**Status:** ❌

Badges earned by a user plus progress towards the next unearned badge in each category.

**Response:**
```json
{
  "earned": [
    { "badge_id": 1, "name": "Premier Signalement", "category": "signalement", "earned_at": "2026-03-12T08:44:00" },
    ...
  ],
  "next": [
    { "badge_id": 2, "name": "Sentinelle", "category": "signalement", "target": 10, "current_progress": 4 },
    ...
  ]
}
```

Progress for count-based badges computed from `signalements`, `collections`, or `user_points` depending on `category`.

---

### `GET /users/{id}/impact` — GAM11
**Status:** ❌

Environmental impact summary for one citizen.

**Response:**
```json
{
  "user_id": 42,
  "total_points": 1240,
  "signalement_count": 34,
  "collection_count": 12,
  "co2_saved_kg": 18.4,
  "since": "2026-01-15T00:00:00"
}
```

CO₂ saved: derived from `collections.volume_collected_l` (avoided transport distance heuristic) or from `user_points` actions.

---

### `GET /defis` — GAM9
**Status:** ❌

All active challenges with real-time collective progress.

**Response:**
```json
[
  {
    "key_defi": 3,
    "title": "1000 signalements en mai",
    "type": "signalement",
    "target_value": 1000,
    "reward_points": 500,
    "ends_at": "2026-05-31T23:59:59",
    "participant_count": 284,
    "collective_progress": 612,
    "progress_pct": 61.2
  },
  ...
]
```

Filters: `WHERE is_active = true AND (ends_at IS NULL OR ends_at > now())`.

---

### `POST /defis/{id}/join` — GAM8
**Status:** ❌

Registers the authenticated user in a challenge.

**Behaviour:**
- Returns 409 if the user is already registered
- Returns 404 if the defi does not exist or is no longer active

**Response:** `{"joined": true, "defi_id": 3}` (201 Created)

---

## Machine Learning

### `POST /ml/predict` — ML5
**Status:** ❌

Predicts the fill rate of a container at a given time horizon. Returns the prediction and stores it in `ml_predictions` for later accuracy evaluation.

**Prerequisite:** A trained model file must exist on the filesystem (output of ML1–ML4 Jupyter notebooks).

**Request body:**
```json
{
  "container_id": 104,
  "horizon_hours": 24
}
```

**Feature engineering (performed at request time):**

| Feature | Source |
|---|---|
| `hour`, `day_of_week`, `day_of_month`, `is_weekend`, `is_peak_hour` | Current timestamp + horizon offset |
| `fill_rate_1h_ago`, `fill_rate_24h_ago`, `fill_rate_7d_ago` | `fill_history` lookups |
| `fill_rate_24h_avg`, `fill_rate_7d_avg`, `fill_rate_change_rate` | Rolling queries on `fill_history` |
| `capacity`, `type_encoded`, `zone_density` | `containers` + `get_zone_density()` |

**Response:**
```json
{
  "container_id": 104,
  "horizon_hours": 24,
  "predicted_fill_rate": 78.3,
  "predicted_at": "2026-05-08T11:00:00",
  "model_version": "rf_v1.0"
}
```

**Performance target:** < 100 ms

Stores result in `ml_predictions` with `actual_fill_rate = NULL` (filled later by a batch for accuracy tracking).

---

## Reports

### `POST /reports/generate` — R4
**Status:** ❌

Triggers an asynchronous report generation. Creates a `reports` record with `status = 'pending'` and enqueues the generation task via FastAPI `BackgroundTasks`.

**Request body:**
```json
{
  "report_type": "monthly",
  "format": "pdf",
  "period_start": "2026-04-01",
  "period_end": "2026-04-30",
  "zone_id": null
}
```

| `report_type` | Content |
|---|---|
| `monthly` | KPIs, evolutions, top zones, incidents, N-1 comparison |
| `weekly` | Abbreviated KPIs + top 5 containers by fill rate |
| `zone` | Performance breakdown for a specific zone |
| `route` | Distance, duration, collections, avg fill rate per route |

**Response:** `{"report_id": 17, "status": "pending"}` (202 Accepted)

**Background task:**
1. Queries the required aggregates
2. Generates PDF (via `reportlab`) or Excel (via `openpyxl`)
3. Writes file to `reports/` directory
4. Updates `reports.file_path` and `reports.status = 'ready'`

---

### `GET /reports/{id}/download` — R5
**Status:** ❌

Downloads a generated report file.

**Behaviour:**
- Returns 404 if the report does not exist
- Returns 202 with `{"status": "processing"}` if not yet ready
- Returns 500 with `{"status": "error"}` if generation failed
- Streams the file on `status = 'ready'`

**Response (ready):**
- PDF: `Content-Type: application/pdf`, `Content-Disposition: attachment; filename=report_monthly_2026-04.pdf`
- Excel: `Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`

---

## DB Triggers Invoked by This Phase

| Trigger | Table | Fires on | Effect |
|---|---|---|---|
| `signalement_award_points` | `signalements` | INSERT | Awards +10 pts to the reporting user via `award_points()` |
| `user_badges_award_points` | `user_badges` | INSERT | Awards badge points + inserts a `notifications` row |
