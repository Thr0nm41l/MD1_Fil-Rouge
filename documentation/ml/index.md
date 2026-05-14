# ML Module — ECOTRACK

**Epic:** E10 — Machine Learning Prédictif  
**Objective:** Predict container fill rate 24 hours ahead to anticipate overflows  
**Deliverable:** L4 — trained model (R² > 0.65) + functional `/ml/predict` API endpoint  
**Sprint:** S9–10

---

## Directory Structure

```
ml/
├── ROADMAP.md                          ← Implementation guide (feature list, code templates)
├── data/
│   ├── training_features.parquet       # Output of ML1 — 14 engineered features + target
│   └── .gitkeep
├── models/
│   ├── model.pkl                       # Output of ML3 — best serialized sklearn Pipeline
│   ├── metadata.json                   # Version, metrics, feature names
│   └── .gitkeep
├── 01_eda_feature_engineering.ipynb    # ML1 — data extraction, EDA, feature engineering
├── 02_training.ipynb                   # ML2+ML3 — temporal split, LR + RF, model export
└── 03_evaluation.ipynb                 # ML4 — metrics, 3 required plots
```

---

## Notebooks

| # | Notebook | Epic ref | Status | Input | Output |
|---|---|---|---|---|---|
| ML1 | `01_eda_feature_engineering.ipynb` | ML1–ML2 | ❌ | DB (fill_history, containers, zones) | `data/training_features.parquet` |
| ML2+ML3 | `02_training.ipynb` | ML3 | ❌ | `data/training_features.parquet` | `models/model.pkl`, `models/metadata.json` |
| ML4 | `03_evaluation.ipynb` | ML4 | ❌ | model + parquet | `plots/*.png` |
| ML5 | `apiservice/routers/ml.py` | ML5 | ⚠️ stub | `models/model.pkl` | `/ml/predict` endpoint |

**Execution order:** ML1 → ML2+ML3 → ML4 → ML5 (API wire-up)

---

## Prerequisites

Before running any notebook, verify the database is populated:

```sql
-- ≥ 30 days of fill_history data
SELECT MIN(measured_at), MAX(measured_at), COUNT(*) FROM fill_history;

-- aggregated_hourly_stats populated
SELECT COUNT(*) FROM aggregated_hourly_stats;

-- container types seeded
SELECT * FROM container_type;

-- zones have polygon data
SELECT COUNT(*) FROM zones WHERE polygon IS NOT NULL;
```

**Minimum dataset:** 2,000+ containers × 30 days × ~144 readings/day ≈ 8.6M rows in `fill_history`.

**Python environment (install once):**
```bash
pip install scikit-learn==1.5.2 pandas==2.2.3 numpy==1.26.4 \
    matplotlib seaborn statsmodels psycopg2-binary python-dotenv openpyxl==3.1.5
```

**Environment variables** — create a `.env` at the repo root (or copy from `apiservice/.env.example`):
```
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=Ecotrack
POSTGRES_USER=...
POSTGRES_PASSWORD=...
```

---

## Features

14 features engineered in ML1, consumed by the trained model and reproduced at inference time in `apiservice/routers/ml.py`:

| Feature | Type | Description |
|---|---|---|
| `hour` | temporal | Hour of day (0–23) |
| `day_of_week` | temporal | Day of week (0=Mon, 6=Sun) |
| `day_of_month` | temporal | Day of month (1–31) |
| `is_weekend` | temporal | 1 if Saturday or Sunday |
| `is_peak_hour` | temporal | 1 if hour in {7,8,9,17,18,19} |
| `fill_rate_1h_ago` | lag | Fill rate ~1h before (shift 6 rows) |
| `fill_rate_24h_ago` | lag | Fill rate ~24h before (shift 144 rows) |
| `fill_rate_7d_ago` | lag | Fill rate ~7 days before (shift 1008 rows) |
| `fill_rate_24h_avg` | rolling | Trailing 24h mean (no future leakage) |
| `fill_rate_7d_avg` | rolling | Trailing 7-day mean |
| `fill_rate_change_rate` | derivative | Δ fill_rate per 10-min step over the last 1h |
| `capacity_liters` | container | Physical capacity |
| `type_id` | container | Waste type category (categorical) |
| `density_km2` | zone | Containers per km² in the zone |

**Target:** `fill_rate` 24 hours in the future (`shift(-144)` at 10-min cadence)

---

## Models

Two models are trained and compared in `02_training.ipynb`:

| Model | Preprocessing | Notes |
|---|---|---|
| `LinearRegression` | `StandardScaler` (numerical) + `OneHotEncoder` (type_id) | Baseline, interpretable |
| `RandomForestRegressor` | Same `ColumnTransformer` | `n_estimators=200, max_depth=15, min_samples_leaf=10` |

Best model selected by `TimeSeriesSplit(n_splits=5)` cross-validated R².

---

## Validation Targets (L4)

| Metric | Target |
|---|---|
| RMSE | < 10 (fill rate is 0–100 scale) |
| MAE | < 7 |
| R² | > 0.65 |

Evaluated on the held-out **temporal 20% test set** (most recent rows — no random shuffle).

---

## API Integration

Once `models/model.pkl` is produced:

1. **Choose a deployment option** (see `ROADMAP.md` § Deployment):
   - **Option A** — Bake into Docker image (simpler, rebuild on each model update)
   - **Option B** — Dedicated PVC (recommended for iterative updates)

2. **Update `apiservice/routers/ml.py`** — replace the 503 stub with the full implementation from `ROADMAP.md` § ML5.

3. **Set the `MODEL_PATH` env var** in the deployment YAML (or `.env` for local dev).

The endpoint signature:

```http
POST /ml/predict
Content-Type: application/json

{ "container_id": 104, "horizon_hours": 24 }
```

```json
{
  "container_id": 104,
  "horizon_hours": 24,
  "predicted_fill_rate": 78.3,
  "predicted_at": "2026-05-08T11:00:00",
  "model_version": "rf_v1.0"
}
```

Performance target: < 100 ms (feature lookups are 5 indexed queries).
