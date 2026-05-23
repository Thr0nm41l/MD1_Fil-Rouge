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
| ML4 | `03_evaluation.ipynb` | `plots/*.png` | ❌ Not run |
| ML5 | `apiservice/routers/ml.py` | `/ml/predict` endpoint | ⚠️ Stub (503) |

**Execution order:** ML1 → ML2+ML3 → ML4 → ML5

---

## Directory Structure

```
ml/
├── ROADMAP.md                          ← Implementation guide and code templates
├── requirements.txt                    ← Python dependencies
├── .env / .env.example                 ← DB connection variables
├── data/
│   ├── training_features.parquet       ✅ 2,265,488 rows × 14 features + target
│   └── .gitkeep
├── models/
│   ├── model.pkl                       ✅ Best model: HistGradientBoosting (hgb_v1.0)
│   ├── metadata.json                   ✅ Version, metrics, feature names
│   └── .gitkeep
├── 01_eda_feature_engineering.ipynb    ML1 — EDA & feature engineering
├── 02_training.ipynb                   ML2+ML3 — training, selection, export
├── 02_training_gpu.ipynb               GPU variant (experimental)
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
| Raw rows extracted | 3,033,488 |
| Containers | 4,000 |
| Date range | 2026-04-03 → 2026-05-14 |
| Sampling cadence | **1h** (not 10-min — shifts auto-calculated) |
| Rows after dropna | **2,265,488** |
| Features | 14 |
| Rows dropped | 768,000 (lag/rolling warm-up period) |

> The notebook dynamically computes shift constants from the actual median interval, so it is cadence-agnostic. At 1h cadence: `SHIFT_1H=1`, `SHIFT_24H=24`, `SHIFT_7D=168`.

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
| `fill_rate_1h_ago` | lag | Fill rate ~1h before |
| `fill_rate_24h_ago` | lag | Fill rate ~24h before |
| `fill_rate_7d_ago` | lag | Fill rate ~7 days before |
| `fill_rate_24h_avg` | rolling | Trailing 24h mean (no future leakage) |
| `fill_rate_7d_avg` | rolling | Trailing 7-day mean |
| `fill_rate_change_rate` | derivative | Δ fill_rate per step over the last 1h |
| `capacity_liters` | container | Physical capacity (liters) |
| `type_id` | container | Waste type category (integer) |
| `density_km2` | zone | Active containers per km² in the zone |

**Target:** `fill_rate` 24 hours in the future (`g.shift(-SHIFT_24H)` per container)

---

## ML2+ML3 — Model Training

**Notebook:** `02_training.ipynb`  
**Output:** `models/model.pkl`, `models/metadata.json`

### Split

Temporal 85/15 split (no shuffle — time-series data):

| Set | Rows | Period |
|---|---|---|
| Train | 1,925,664 | 2026-04-10 → 2026-05-03 |
| Test | 339,824 | 2026-05-03 → 2026-05-09 |

Cross-validation: `TimeSeriesSplit(n_splits=5)` on the train set.

### Model comparison (last run)

| Model | CV R² | Test R² | Test RMSE | Test MAE |
|---|---|---|---|---|
| LinearRegression | 0.094 | -0.018 | 20.37 | 17.16 |
| RandomForestRegressor | 0.522 | 0.093 | 19.23 | 14.25 |
| **HistGradientBoosting** | **0.673** | **0.218** | **17.85** | **12.36** |

> **Selected model:** `hgb_v1.0` — best CV R² (0.673, meets the > 0.65 threshold).

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

### Known issue — test R² below L4 target

The test R² (0.218) is well below the target (0.65), even though CV R² meets it. Likely causes:

- **Short history window (~41 days):** the 7-day lag features have limited diversity, so the model has learned a narrow distribution. With more data, the 7d seasonal signal should strengthen.
- **Distribution shift:** the test period (2026-05-03 → 2026-05-09) may have different fill patterns than the training period.

To improve: wait for more `fill_history` rows to accumulate (aim for 60–90 days), then re-run ML1 → ML2 → ML3.

### metadata.json (current)

```json
{
  "version": "hgb_v1.0",
  "trained_at": "2026-05-14T13:15:48.510780+00:00",
  "model_type": "hgb",
  "train_ratio": 0.85,
  "cv_r2": 0.6732,
  "test_r2": 0.2179,
  "test_rmse": 17.8549,
  "test_mae": 12.3613,
  "n_features": 14,
  "train_rows": 1925664,
  "test_rows": 339824
}
```

---

## ML4 — Evaluation

**Notebook:** `03_evaluation.ipynb`  
**Status:** ❌ Not yet run — `plots/` directory does not exist

### To run

```bash
cd ml
jupyter lab 03_evaluation.ipynb
```

Run all cells. The notebook will:
1. Load `models/model.pkl` + `models/metadata.json`
2. Reconstruct the temporal 80/20 test split from the parquet
3. Print RMSE / MAE / R² with pass/fail against L4 thresholds
4. Save 3 plots to `plots/`

### Expected plots

| File | Description |
|---|---|
| `plots/pred_vs_actual.png` | Scatter: predicted vs actual fill rate (2,000-point sample) |
| `plots/error_distribution.png` | Histogram of prediction errors with mean and p95 annotation |
| `plots/feature_importance.png` | Top-15 feature importances (RF) or LR coefficients |

### Known issue in `03_evaluation.ipynb`

The feature importance cell branches on `meta['model_type'] == 'rf'`. Since the current best model is `hgb`, it falls into the `else` branch, which tries to access `model.named_steps['prep']` — **this step does not exist in the HGB pipeline** and will raise a `KeyError`. Fix by adding an `'hgb'` branch before running:

```python
elif meta['model_type'] == 'hgb':
    # HistGradientBoosting exposes feature importances directly
    importances = model.named_steps['model'].feature_importances_
    feat_names  = np.array(FEATURE_COLS)
    top_n       = min(15, len(importances))
    idx_sorted  = np.argsort(importances)[::-1][:top_n]

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar(range(top_n), importances[idx_sorted], color='steelblue')
    ax.set_xticks(range(top_n))
    ax.set_xticklabels(feat_names[idx_sorted], rotation=45, ha='right', fontsize=9)
    ax.set_ylabel('Feature importance')
    ax.set_title(f'Top {top_n} feature importances — {meta["version"]}')
    plt.tight_layout()
    plt.savefig('plots/feature_importance.png', dpi=120)
    plt.show()
```

### Validation targets (L4)

| Metric | Target | Current (hgb_v1.0) | Status |
|---|---|---|---|
| RMSE | < 10 | 17.85 | ❌ |
| MAE | < 7 | 12.36 | ❌ |
| R² | > 0.65 | 0.22 (test) / 0.67 (CV) | ❌ |

---

## ML5 — API Integration

**File:** `apiservice/routers/ml.py`  
**Status:** ⚠️ 503 stub — not yet wired up

### To activate

1. Ensure `models/model.pkl` and `models/metadata.json` are present (done).
2. Choose a deployment option (see below).
3. Replace the stub in `apiservice/routers/ml.py` with the full implementation from `ml/ROADMAP.md § ML5`.
4. Set `MODEL_PATH` env var to the model file path inside the container.

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
  "horizon_hours": 24,
  "predicted_fill_rate": 78.3,
  "predicted_at": "2026-05-08T11:00:00",
  "model_version": "hgb_v1.0"
}
```

At inference time the endpoint reconstructs the 14 features live from the DB (5 indexed queries). Performance target: < 100 ms.

> **Important:** the current model (`hgb_v1.0`) was trained without a `ColumnTransformer`. Feature extraction must produce the same 14 columns in the same order as `FEATURE_COLS` in `metadata.json`. No scaling or encoding step is needed before calling `model.predict()`.

---

## Deployment

Two options to make `model.pkl` available to the API container:

### Option A — Bake into Docker image (simplest)

Add to `apiservice/Dockerfile`:
```dockerfile
COPY ../ml/models/model.pkl     /ml/models/model.pkl
COPY ../ml/models/metadata.json /ml/models/metadata.json
ENV MODEL_PATH=/ml/models/model.pkl
```

Rebuild and push after each model update.

### Option B — PVC mount (recommended for iterative retraining)

Add a `persistentVolumeClaim` volume + mount to `helmcharts/apiservice-deployment.yaml`:

```yaml
# spec.volumes
- name: ml-models
  persistentVolumeClaim:
    claimName: apiservice-ml-models

# spec.containers[0].volumeMounts
- name: ml-models
  mountPath: /ml/models
  readOnly: true

# spec.containers[0].env
- name: MODEL_PATH
  value: "/ml/models/model.pkl"
```

Copy updated model to the PVC after retraining:
```bash
kubectl cp ml/models/model.pkl     datalake/<apiservice-pod>:/ml/models/model.pkl
kubectl cp ml/models/metadata.json datalake/<apiservice-pod>:/ml/models/metadata.json
```

---

## Retraining Checklist

Run this sequence after accumulating more `fill_history` data:

```
1. ML1 — re-run 01_eda_feature_engineering.ipynb
          → replaces data/training_features.parquet

2. ML2+ML3 — re-run 02_training.ipynb
              → replaces models/model.pkl + models/metadata.json

3. ML4 — run 03_evaluation.ipynb (fix HGB branch first — see above)
          → generates plots/ — verify targets are met

4. ML5 — if targets met, deploy model to API container
          → test POST /ml/predict with a real container_id
```

**Risk:** if `fill_history` has < 30 days per container, the 7-day lag rows will be dropped and training set will be too small. Always check the date range after ML1 before proceeding.
