# ML Roadmap — Predictive Fill Rate

**Epic:** E10 — Machine Learning Prédictif  
**Objective:** Predict container fill rate 24 hours ahead to anticipate overflows  
**Deliverable:** L4 — trained model (R² > 0.65) + functional `/ml/predict` endpoint  
**Sprint:** S9–10

---

## Directory structure

```
ml/
├── ROADMAP.md                  ← this file
├── data/
│   ├── training_features.parquet   # output of ML1 notebook
│   └── .gitkeep
├── models/
│   ├── model.pkl                   # output of ML3 — best serialized model
│   ├── metadata.json               # version, metrics, feature names
│   └── .gitkeep
├── 01_eda_feature_engineering.ipynb
├── 02_training.ipynb
└── 03_evaluation.ipynb
```

---

## Prerequisites

| Check | How to verify |
|---|---|
| ≥ 30 days of `fill_history` data | `SELECT MIN(measured_at), MAX(measured_at), COUNT(*) FROM fill_history;` |
| `aggregated_hourly_stats` populated | `SELECT COUNT(*) FROM aggregated_hourly_stats;` — should be > 0 |
| `container_type` seeded | `SELECT * FROM container_type;` |
| Zones have polygon + density computable | `SELECT COUNT(*) FROM zones WHERE polygon IS NOT NULL;` |
| Python env with deps | `pip install scikit-learn pandas numpy matplotlib seaborn psycopg2-binary python-dotenv` |

**Minimum viable dataset:** 2 000+ containers × 30 days × ~144 readings/day ≈ 8.6M rows in `fill_history`. If the livesim DAG has been running, this will already be there.

---

## ML1 — EDA & Feature Engineering

**Notebook:** `01_eda_feature_engineering.ipynb`  
**Output:** `data/training_features.parquet`  
**Validation criterion:** 8+ features created and documented

### 1.1 Data extraction

Pull raw history from the DB with a pandas read (avoids complex SQL window functions):

```python
import os
import pandas as pd
import psycopg2
from dotenv import load_dotenv

load_dotenv()  # reads .env at repo root

conn = psycopg2.connect(
    host=os.environ["POSTGRES_HOST"], database=os.environ["POSTGRES_DB"],
    user=os.environ["POSTGRES_USER"], password=os.environ["POSTGRES_PASSWORD"],
)

df_hist = pd.read_sql("""
    SELECT
        fh.container_id,
        fh.measured_at,
        fh.fill_rate,
        c.capacity_liters,
        c.type_id,
        c.zone_id
    FROM fill_history fh
    JOIN containers c ON c.key_container = fh.container_id
    WHERE NOT fh.is_outlier
      AND c.is_active = true
    ORDER BY fh.container_id, fh.measured_at
""", conn)

df_zones = pd.read_sql("""
    SELECT
        key_zone,
        ROUND(
            COUNT(c.key_container)::numeric /
            NULLIF(ST_Area(z.polygon::geography) / 1e6, 0),
        4) AS density_km2
    FROM zones z
    LEFT JOIN containers c ON ST_Within(c.location, z.polygon) AND c.is_active = true
    WHERE z.polygon IS NOT NULL
    GROUP BY key_zone
""", conn)
```

### 1.2 EDA checks (required plots)

- Fill rate distribution per container type (boxplot)
- Time series for 3–5 sample containers (line plot)
- Missing value heatmap
- Autocorrelation plot (fill_rate vs lagged self) — validates that lag features will have signal

### 1.3 Feature engineering

Group by `container_id`, sort by `measured_at`, then apply per-container transformations:

```python
df_hist = df_hist.sort_values(["container_id", "measured_at"])
g = df_hist.groupby("container_id")["fill_rate"]

# ── Temporal ──────────────────────────────────────────────────────────────────
df_hist["hour"]         = df_hist["measured_at"].dt.hour
df_hist["day_of_week"]  = df_hist["measured_at"].dt.dayofweek   # 0=Mon
df_hist["day_of_month"] = df_hist["measured_at"].dt.day
df_hist["is_weekend"]   = (df_hist["day_of_week"] >= 5).astype(int)
df_hist["is_peak_hour"] = df_hist["hour"].isin([7, 8, 9, 17, 18, 19]).astype(int)

# ── Lag — shift by N rows (data sampled every ~10 min, so 1h ≈ 6 rows) ───────
# Use time-based shift: find the reading closest to T-1h, T-24h, T-7d
# Simpler for training: use approximate row shift, then drop rows with NaN
df_hist["fill_rate_1h_ago"]  = g.shift(6)    # ~1h at 10-min cadence
df_hist["fill_rate_24h_ago"] = g.shift(144)  # ~24h
df_hist["fill_rate_7d_ago"]  = g.shift(1008) # ~7d

# ── Rolling averages (trailing windows, no future leakage) ───────────────────
df_hist["fill_rate_24h_avg"] = (
    g.transform(lambda s: s.shift(1).rolling(144, min_periods=12).mean())
)
df_hist["fill_rate_7d_avg"] = (
    g.transform(lambda s: s.shift(1).rolling(1008, min_periods=144).mean())
)
df_hist["fill_rate_change_rate"] = (
    g.transform(lambda s: (s - s.shift(6)) / 6)  # Δ fill_rate per 10-min step
)

# ── Container ─────────────────────────────────────────────────────────────────
df_hist = df_hist.merge(df_zones, left_on="zone_id", right_on="key_zone", how="left")
df_hist["density_km2"] = df_hist["density_km2"].fillna(0)
# type_id is already integer — suitable as-is for tree models; one-hot for linear
```

**Target variable:** `fill_rate` at T + 24h. Since we're predicting future fill rate, the target for row `i` is the fill rate 144 rows later in the same container:

```python
df_hist["target"] = g.shift(-144)  # fill_rate 24h in the future
```

Drop rows with any NaN in features or target, then save:

```python
feature_cols = [
    "hour", "day_of_week", "day_of_month", "is_weekend", "is_peak_hour",
    "fill_rate_1h_ago", "fill_rate_24h_ago", "fill_rate_7d_ago",
    "fill_rate_24h_avg", "fill_rate_7d_avg", "fill_rate_change_rate",
    "capacity_liters", "type_id", "density_km2",
]
df_clean = df_hist[feature_cols + ["target", "container_id", "measured_at"]].dropna()
df_clean.to_parquet("data/training_features.parquet", index=False)
print(f"Training set: {len(df_clean):,} rows, {len(feature_cols)} features")
```

---

## ML2 + ML3 — Model Training

**Notebook:** `02_training.ipynb`  
**Output:** `models/model.pkl`, `models/metadata.json`  
**Validation criterion:** both models trained, no data leakage, R² > 0.65

### 2.1 Temporal train/test split

**Do not use random split** — this is time-series data. The test set must be the most recent 20% of the time range to avoid leakage:

```python
import pandas as pd
from sklearn.model_selection import TimeSeriesSplit

df = pd.read_parquet("data/training_features.parquet")
df = df.sort_values("measured_at")

split_idx = int(len(df) * 0.80)
df_train = df.iloc[:split_idx]
df_test  = df.iloc[split_idx:]

X_train, y_train = df_train[feature_cols], df_train["target"]
X_test,  y_test  = df_test[feature_cols],  df_test["target"]

print(f"Train: {len(df_train):,} rows — up to {df_train['measured_at'].max()}")
print(f"Test:  {len(df_test):,}  rows — from {df_test['measured_at'].min()}")
```

### 2.2 Cross-validation

Use `TimeSeriesSplit` for CV to preserve temporal ordering:

```python
from sklearn.model_selection import TimeSeriesSplit, cross_val_score

tscv = TimeSeriesSplit(n_splits=5)
```

### 2.3 Linear Regression

```python
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline

categorical = ["type_id"]
numerical   = [c for c in feature_cols if c != "type_id"]

preprocessor = ColumnTransformer([
    ("num", StandardScaler(),     numerical),
    ("cat", OneHotEncoder(handle_unknown="ignore"), categorical),
])

lr_pipe = Pipeline([("prep", preprocessor), ("model", LinearRegression())])
lr_pipe.fit(X_train, y_train)

lr_cv_r2 = cross_val_score(lr_pipe, X_train, y_train, cv=tscv, scoring="r2").mean()
print(f"LinearRegression CV R²: {lr_cv_r2:.3f}")
```

### 2.4 Random Forest

```python
from sklearn.ensemble import RandomForestRegressor

rf_pipe = Pipeline([
    ("prep", preprocessor),
    ("model", RandomForestRegressor(
        n_estimators=200,
        max_depth=15,
        min_samples_leaf=10,
        n_jobs=-1,
        random_state=42,
    )),
])
rf_pipe.fit(X_train, y_train)

rf_cv_r2 = cross_val_score(rf_pipe, X_train, y_train, cv=tscv, scoring="r2").mean()
print(f"RandomForest CV R²: {rf_cv_r2:.3f}")
```

### 2.5 Model export

Pick the best model by CV R², serialize it, and write metadata:

```python
import pickle, json
from datetime import datetime

best_model = rf_pipe if rf_cv_r2 >= lr_cv_r2 else lr_pipe
best_name  = "rf" if rf_cv_r2 >= lr_cv_r2 else "lr"

with open("models/model.pkl", "wb") as f:
    pickle.dump(best_model, f)

json.dump({
    "version":      f"{best_name}_v1.0",
    "trained_at":   datetime.utcnow().isoformat(),
    "feature_cols": feature_cols,
    "cv_r2":        max(lr_cv_r2, rf_cv_r2),
    "model_type":   best_name,
}, open("models/metadata.json", "w"), indent=2)

print(f"Saved: {best_name}_v1.0  CV R²={max(lr_cv_r2, rf_cv_r2):.3f}")
```

---

## ML4 — Evaluation

**Notebook:** `03_evaluation.ipynb`  
**Validation criterion:** RMSE < 10 %, MAE < 7 %, R² > 0.65

### 3.1 Metrics on held-out test set

```python
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
import numpy as np

y_pred_lr = lr_pipe.predict(X_test)
y_pred_rf = rf_pipe.predict(X_test)

for name, y_pred in [("LinearRegression", y_pred_lr), ("RandomForest", y_pred_rf)]:
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))
    mae  = mean_absolute_error(y_test, y_pred)
    r2   = r2_score(y_test, y_pred)
    print(f"{name:25s}  RMSE={rmse:.2f}  MAE={mae:.2f}  R²={r2:.3f}")
```

Target: RMSE < 10, MAE < 7, R² > 0.65 (fill_rate is 0–100 scale).

### 3.2 Required plots

**Plot 1 — Predictions vs actuals (scatter)**
```python
import matplotlib.pyplot as plt

plt.figure(figsize=(7, 7))
plt.scatter(y_test[:2000], y_pred_rf[:2000], alpha=0.3, s=8)
plt.plot([0, 100], [0, 100], "r--")
plt.xlabel("Actual fill rate"), plt.ylabel("Predicted fill rate")
plt.title("RandomForest — Predicted vs Actual (test set sample)")
plt.savefig("plots/pred_vs_actual.png", dpi=120)
```

**Plot 2 — Error distribution (histogram)**
```python
errors = y_pred_rf - y_test
plt.figure(figsize=(8, 4))
plt.hist(errors, bins=60, edgecolor="black")
plt.axvline(0, color="red", linestyle="--")
plt.xlabel("Prediction error"), plt.title("Error distribution")
plt.savefig("plots/error_distribution.png", dpi=120)
```

**Plot 3 — Feature importance (bar chart, Random Forest only)**
```python
feat_names = (
    rf_pipe.named_steps["prep"]
    .get_feature_names_out()
)
importances = rf_pipe.named_steps["model"].feature_importances_
idx = np.argsort(importances)[::-1][:15]

plt.figure(figsize=(9, 5))
plt.bar(range(15), importances[idx])
plt.xticks(range(15), feat_names[idx], rotation=45, ha="right")
plt.title("Top 15 feature importances")
plt.tight_layout()
plt.savefig("plots/feature_importance.png", dpi=120)
```

---

## ML5 — API integration

**File:** `apiservice/routers/ml.py`  
Once `models/model.pkl` exists, replace the 503 stub with the real implementation.

### 5.1 Model loading (at startup)

The model is loaded once at module import, not per request:

```python
# routers/ml.py
import os, pickle, json
from pathlib import Path

_MODEL_PATH = Path(os.environ.get("MODEL_PATH", "/ml/models/model.pkl"))
_META_PATH  = _MODEL_PATH.with_suffix("").with_name("metadata.json")

_model = None
_feature_cols = None

def _load_model():
    global _model, _feature_cols
    with open(_MODEL_PATH, "rb") as f:
        _model = pickle.load(f)
    meta = json.loads(_META_PATH.read_text())
    _feature_cols = meta["feature_cols"]
    return meta["version"]

if _MODEL_PATH.exists():
    _version = _load_model()
else:
    _version = None  # endpoint returns 503 until model is mounted
```

### 5.2 Feature extraction at inference time

At request time, look up lag values and rolling stats for the specific container:

```python
def _build_features(conn, container_id: int, horizon_hours: int) -> dict:
    target_at = datetime.utcnow() + timedelta(hours=horizon_hours)

    # Temporal features (from target timestamp)
    feats = {
        "hour":            target_at.hour,
        "day_of_week":     target_at.weekday(),
        "day_of_month":    target_at.day,
        "is_weekend":      int(target_at.weekday() >= 5),
        "is_peak_hour":    int(target_at.hour in (7, 8, 9, 17, 18, 19)),
    }

    # Lag + rolling from fill_history
    with conn.cursor() as cur:
        cur.execute("""
            SELECT
                (SELECT fill_rate FROM fill_history
                 WHERE container_id = %(id)s AND measured_at <= NOW() - INTERVAL '55 min'
                 ORDER BY measured_at DESC LIMIT 1)                     AS r_1h,

                (SELECT fill_rate FROM fill_history
                 WHERE container_id = %(id)s AND measured_at <= NOW() - INTERVAL '23.5 hours'
                 ORDER BY measured_at DESC LIMIT 1)                     AS r_24h,

                (SELECT fill_rate FROM fill_history
                 WHERE container_id = %(id)s AND measured_at <= NOW() - INTERVAL '6.9 days'
                 ORDER BY measured_at DESC LIMIT 1)                     AS r_7d,

                (SELECT ROUND(AVG(fill_rate)::numeric, 2) FROM fill_history
                 WHERE container_id = %(id)s
                   AND measured_at BETWEEN NOW() - INTERVAL '24 hours' AND NOW()) AS avg_24h,

                (SELECT ROUND(AVG(fill_rate)::numeric, 2) FROM fill_history
                 WHERE container_id = %(id)s
                   AND measured_at BETWEEN NOW() - INTERVAL '7 days' AND NOW())   AS avg_7d
        """, {"id": container_id})
        r = cur.fetchone()

    feats["fill_rate_1h_ago"]       = float(r[0] or 0)
    feats["fill_rate_24h_ago"]      = float(r[1] or 0)
    feats["fill_rate_7d_ago"]       = float(r[2] or 0)
    feats["fill_rate_24h_avg"]      = float(r[3] or 0)
    feats["fill_rate_7d_avg"]       = float(r[4] or 0)
    feats["fill_rate_change_rate"]  = (feats["fill_rate_1h_ago"] - feats["fill_rate_24h_ago"]) / 144

    # Container metadata
    with conn.cursor() as cur:
        cur.execute(
            "SELECT capacity_liters, type_id, zone_id FROM containers WHERE key_container = %s",
            (container_id,),
        )
        c = cur.fetchone()
    feats["capacity_liters"] = float(c[0])
    feats["type_id"]         = int(c[1] or 0)
    zone_id = c[2]

    # Zone density
    if zone_id:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT density_km2 FROM get_choropleth_data() WHERE zone_id = %s",
                (zone_id,),
            )
            row = cur.fetchone()
        feats["density_km2"] = float(row[0]) if row else 0.0
    else:
        feats["density_km2"] = 0.0

    return feats
```

### 5.3 Full predict endpoint

```python
@router.post("/predict")
def predict_fill_rate(body: PredictRequest, conn=Depends(get_db)):
    if _model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")

    feats = _build_features(conn, body.container_id, body.horizon_hours)
    X = pd.DataFrame([feats])[_feature_cols]
    predicted = round(float(_model.predict(X)[0]), 2)
    predicted = max(0.0, min(100.0, predicted))  # clamp to valid range

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO ml_predictions
                (container_id, horizon_hours, predicted_fill_rate, model_version)
            VALUES (%s, %s, %s, %s)
            """,
            (body.container_id, body.horizon_hours, predicted, _version),
        )

    return {
        "container_id":       body.container_id,
        "horizon_hours":      body.horizon_hours,
        "predicted_fill_rate": predicted,
        "predicted_at":       datetime.utcnow().isoformat(),
        "model_version":      _version,
    }
```

---

## Deployment — getting the model into the API container

Two options, pick one:

### Option A — Bake into Docker image (simplest)

Add to `apiservice/Dockerfile`:
```dockerfile
COPY ../ml/models/model.pkl  /ml/models/model.pkl
COPY ../ml/models/metadata.json /ml/models/metadata.json
ENV MODEL_PATH=/ml/models/model.pkl
```

Rebuild and push the image after each model update. Works well for the first deployment.

### Option B — Dedicated PVC (recommended for iterative updates)

Add a second PVC and `initContainer` to the deployment YAML:

```yaml
# In helmcharts/apiservice-deployment.yaml — add to spec.volumes:
- name: ml-models
  persistentVolumeClaim:
    claimName: apiservice-ml-models

# Add to spec.containers[0].volumeMounts:
- name: ml-models
  mountPath: /ml/models
  readOnly: true

# Add env var:
- name: MODEL_PATH
  value: "/ml/models/model.pkl"
```

After training, copy the model to the PVC:
```bash
# From your local machine (after kubectl port-forward or via a Job):
kubectl cp ml/models/model.pkl datalake/<apiservice-pod>:/ml/models/model.pkl
kubectl cp ml/models/metadata.json datalake/<apiservice-pod>:/ml/models/metadata.json
```

---

## Summary checklist

| # | Task | Notebook | Output | Done |
|---|------|----------|--------|------|
| ML1 | EDA + feature engineering | `01_eda_feature_engineering.ipynb` | `data/training_features.parquet` | ❌ |
| ML2 | LinearRegression + RandomForest implemented | `02_training.ipynb` | — | ❌ |
| ML3 | Temporal 80/20 split + TimeSeriesSplit CV | `02_training.ipynb` | `models/model.pkl`, `models/metadata.json` | ❌ |
| ML4 | RMSE < 10, MAE < 7, R² > 0.65 + 3 plots | `03_evaluation.ipynb` | `plots/*.png` | ❌ |
| ML5 | `/ml/predict` endpoint wired up | `apiservice/routers/ml.py` | — | ⚠️ stub ready |

**Blocking order:** ML1 → ML2 → ML3 → ML4 → ML5 → deploy  
**Longest step:** ML1 (data prep) — budget at least a full session if working with the live DB  
**Risk:** if `fill_history` has < 30 days of data, lag features for 7d will produce mostly NaN rows — check the data volume first
