# ML Module — ECOTRACK

**Epic:** E10 — Machine Learning Prédictif  
**Objective:** Predict container fill rate 24 hours ahead to anticipate overflows  
**Deliverable:** L4 — trained model (R² > 0.65) + functional `/ml/predict` API endpoint  
**Sprint:** S9–10

---

## Status

| Step | Notebook / File | Output | Status |
|---|---|---|---|
| ML1 | `01_eda_feature_engineering.ipynb` | `data/training_features.parquet` | ✅ Done |
| ML2+ML3 | `02_training.ipynb` | `models/model.pkl`, `models/metadata.json` | ✅ Done |
| ML4 | `03_evaluation.ipynb` | `plots/*.png` | ✅ Done |
| ML5 | `apiservice/routers/ml.py` | `/ml/predict` endpoint | ✅ Done |

**Execution order:** ML1 → ML2+ML3 → ML4 → ML5

---

## Directory Structure

```
ml/
├── data/
│   ├── training_features.parquet       ✅ 6,251,787 rows × 14 features + target
│   └── .gitkeep
├── models/
│   ├── model.pkl                       ✅ Best model: HistGradientBoosting (hgb_v1.0)
│   ├── metadata.json                   ✅ Version, metrics, feature names
│   └── .gitkeep
├── plots/
│   ├── pred_vs_actual.png              ✅
│   ├── error_distribution.png          ✅
│   └── feature_importance.png          ✅ (placeholder — see ML4 notes)
├── 01_eda_feature_engineering.ipynb    ML1 — EDA & feature engineering
├── 02_training.ipynb                   ML2+ML3 — training, selection, export
└── 03_evaluation.ipynb                 ML4 — metrics + 3 required plots
```

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

**Python environment:**
```bash
pip install -r ml/requirements.txt
```

**DB port-forward (Kubernetes):**
```bash
kubectl port-forward svc/postgres-postgresql 5432:5432 -n datalake
```

**Environment variables** — copy `ml/.env.example` and fill in:
```
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=Ecotrack
POSTGRES_USER=...
POSTGRES_PASSWORD=...
```

---

## ML1 — EDA & Feature Engineering

**Notebook:** `01_eda_feature_engineering.ipynb`  
**Output:** `data/training_features.parquet`

### Actual data (last run)

| Metric | Value |
|---|---|
| Raw rows extracted | 8,555,787 |
| Containers | 2,000 |
| Date range | 2026-05-14 → 2026-06-13 |
| Sampling cadence | **10 min** (144 readings/day) |
| Rows after dropna | **6,251,787** |
| Features | 14 |
| Rows dropped | 2,304,000 (lag/rolling warm-up period) |

Shift constants computed from median interval (10 min): `SHIFT_1H=6`, `SHIFT_24H=144`, `SHIFT_7D=1008`.

### EDA plots produced

1. Fill rate distribution by container type (boxplot)
2. Fill rate time series — 5 sample containers (line plot)
3. Missing value heatmap — last 7 days (5 sample containers)
4. Autocorrelation — validates lag feature signal (lags up to 200 steps)
5. Feature correlation matrix

### 14 Features

| Feature | Type | Description |
|---|---|---|
| `hour` | temporal | Hour of day (0–23) |
| `day_of_week` | temporal | Day of week (0=Mon, 6=Sun) |
| `day_of_month` | temporal | Day of month (1–31) |
| `is_weekend` | temporal | 1 if Saturday or Sunday |
| `is_peak_hour` | temporal | 1 if hour in {7, 8, 9, 17, 18, 19} |
| `fill_rate_1h_ago` | lag | Fill rate 6 rows back (shift 6 at 10-min cadence) |
| `fill_rate_24h_ago` | lag | Fill rate 144 rows back (~24h) |
| `fill_rate_7d_ago` | lag | Fill rate 1008 rows back (~7 days) |
| `fill_rate_24h_avg` | rolling | Trailing 24h mean (shift(1).rolling(144) — no leakage) |
| `fill_rate_7d_avg` | rolling | Trailing 7-day mean |
| `fill_rate_change_rate` | derivative | Δ fill_rate per 10-min step over the last 1h |
| `capacity_liters` | container | Physical capacity (liters) |
| `type_id` | container | Waste type category (integer) |
| `density_km2` | zone | Active containers per km² in the zone |

**Target:** `fill_rate` 24 hours in the future (`g.shift(-144)` per container)

---

## ML2+ML3 — Model Training

**Notebook:** `02_training.ipynb`  
**Output:** `models/model.pkl`, `models/metadata.json`

### Split

Temporal 85/15 split (no shuffle — time-series data):

| Set | Rows |
|---|---|
| Train | 5,314,018 |
| Test | 937,769 |

Cross-validation: `TimeSeriesSplit(n_splits=5)` on the train set.

### Model comparison (last run)

| Model | CV R² | Test R² | Test RMSE | Test MAE | CDC pass? |
|---|---|---|---|---|---|
| LinearRegression | ~−2.9×10¹⁹ (unstable) | 0.199 | 17.903 | 13.873 | ❌ |
| RandomForestRegressor | 0.633 | 0.678 | 11.342 | 6.609 | ❌ (RMSE > 10) |
| **HistGradientBoosting** | **0.718** | **0.753** | **9.949** | **5.468** | ✅ |

> **Selected model:** `hgb_v1.0` — best CV R² and only model meeting all three CDC thresholds (RMSE < 10, MAE < 7, R² > 0.65).

**Note on LinearRegression CV R²:** the value of ~−2.9×10¹⁹ is a numerical blowup caused by `StandardScaler` + `TimeSeriesSplit` producing near-degenerate folds at this data scale. It does not affect model selection.

### HistGradientBoosting configuration

```python
HistGradientBoostingRegressor(
    max_iter=300,
    max_depth=6,
    min_samples_leaf=20,
    learning_rate=0.05,
    random_state=42,
)
```

HGB handles mixed numeric/categorical types natively — **no `ColumnTransformer` preprocessing step** in its pipeline. The LinearRegression and RandomForest pipelines use `StandardScaler` (numerical) + `OneHotEncoder` (type_id).

### metadata.json (current)

```json
{
  "version": "hgb_v1.0",
  "trained_at": "2026-06-13T17:47:10.618233+00:00",
  "model_type": "hgb",
  "train_ratio": 0.85,
  "cv_r2": 0.7184,
  "test_r2": 0.7527,
  "test_rmse": 9.9485,
  "test_mae": 5.4679,
  "n_features": 14,
  "train_rows": 5314018,
  "test_rows": 937769
}
```

---

## ML4 — Evaluation

**Notebook:** `03_evaluation.ipynb`  
**Status:** ✅ Done

### Validation targets (L4)

| Metric | Target | Result (hgb_v1.0) | Status |
|---|---|---|---|
| RMSE | < 10 | 9.95 | ✅ |
| MAE | < 7 | 5.47 | ✅ |
| R² | > 0.65 | 0.753 | ✅ |

### Plots produced

| File | Description |
|---|---|
| `plots/pred_vs_actual.png` | Scatter: predicted vs actual fill rate (2,000-point sample) |
| `plots/error_distribution.png` | Histogram of prediction errors with mean and p95 annotation |
| `plots/feature_importance.png` | Placeholder — `HistGradientBoostingRegressor` does not expose `feature_importances_`; permutation importance would require a separate pass |

### Known issues fixed in the notebook

Two Python 3.14 + library version incompatibilities were patched directly in the notebook cells:

- **`sort_values('measured_at')` crash** (pandas 2.x `DatetimeArray` ExtensionArray bug): replaced with `df.iloc[df['measured_at'].to_numpy().argsort(kind='stable')]`
- **`ax.hist(errors, bins=80)` crash** (numpy 2.x histogram edge case): replaced with explicit `bins=np.linspace(errors.min(), errors.max(), 81)` to bypass numpy's internal bin-count calculation

---

## ML5 — API Integration

**File:** `apiservice/routers/ml.py`  
**Status:** ✅ Done

### Endpoint

```http
POST /ml/predict
Content-Type: application/json
```

**Request:**
```json
{ "container_id": 104, "horizon_hours": 24 }
```

**Response:**
```json
{
  "container_id": 104,
  "predicted_fill_rate": 73.4,
  "predicted_at": "2026-06-14T10:30:00+00:00",
  "model_version": "hgb_v1.0",
  "horizon_hours": 24
}
```

### How it works

The model is loaded once at API startup via `load_model()` (called in `main.py`'s lifespan handler). Per request, the endpoint:

1. Queries `containers` for `capacity_liters`, `type_id`, `zone_id`
2. Queries `zones` for `density_km2` via `ST_Area(polygon::geography)`
3. Fetches the last 1,009 `fill_history` rows for the container (ordered most recent first)
4. Computes all 14 features using the same shift constants as the EDA notebook (`SHIFT_1H=6`, `SHIFT_24H=144`, `SHIFT_7D=1008`)
5. Calls `model.predict()` and clips the result to `[0, 100]`

### Error responses

| Code | Condition |
|---|---|
| 503 | Model file not found at startup |
| 404 | Container not found or inactive |
| 422 | Fewer than 145 fill_history rows (< 24h of data at 10-min cadence) |

### Model path configuration

| Context | Path |
|---|---|
| Local dev | Auto-detected: `../ml/models/model.pkl` relative to `apiservice/` |
| Docker / k8s | Set `MODEL_PATH=/app/models/model.pkl` env var |

The Dockerfile copies `ml/models/` into `/app/models/` — the Docker build must run from the repo root:
```bash
docker build -f apiservice/Dockerfile -t thronmail/md1-fil-rouge-api:latest .
```

---

## Retraining Checklist

Run this sequence after accumulating more `fill_history` data:

```
1. (Optional) masc__nuke_database  confirm=true
              lasc__seed_data

2. ML1 — re-run 01_eda_feature_engineering.ipynb
          → replaces data/training_features.parquet

3. ML2+ML3 — re-run 02_training.ipynb
              → replaces models/model.pkl + models/metadata.json

4. ML4 — run 03_evaluation.ipynb
          → verify all three L4 targets pass

5. ML5 — rebuild Docker image (model is baked in) and redeploy
          → test POST /ml/predict with a real container_id
```

**Risk:** if `fill_history` has < 8 days per container, 7-day lag rows will be dropped and the training set will be too small. Always check the date range after ML1 before proceeding.
