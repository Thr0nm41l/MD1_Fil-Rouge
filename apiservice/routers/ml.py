import json
import logging
import os
import pickle
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from db import get_db

logger = logging.getLogger(__name__)
router = APIRouter()

# ── Model state (loaded once at startup via load_model()) ─────────────────────

_model = None
_metadata: dict | None = None

FEATURE_COLS = [
    'hour', 'day_of_week', 'day_of_month', 'is_weekend', 'is_peak_hour',
    'fill_rate_1h_ago', 'fill_rate_24h_ago', 'fill_rate_7d_ago',
    'fill_rate_24h_avg', 'fill_rate_7d_avg', 'fill_rate_change_rate',
    'capacity_liters', 'type_id', 'density_km2',
]

# Row-shift constants for 10-min cadence — must match 01_eda_feature_engineering.ipynb
SHIFT_1H  = 6
SHIFT_24H = 144
SHIFT_7D  = 1008


def _model_path() -> Path:
    env = os.environ.get("MODEL_PATH")
    if env:
        return Path(env)
    # Local dev: routers/ → apiservice/ → repo root → ml/models/
    return Path(__file__).parent.parent.parent / "ml" / "models" / "model.pkl"


def load_model() -> None:
    global _model, _metadata
    path = _model_path()
    if not path.exists():
        logger.warning("ML model not found at %s — /ml/predict will return 503", path)
        return
    with open(path, "rb") as f:
        _model = pickle.load(f)
    meta_path = path.parent / "metadata.json"
    if meta_path.exists():
        with open(meta_path) as f:
            _metadata = json.load(f)
    logger.info("ML model loaded: %s", _metadata.get("version") if _metadata else path.name)


# ── Schemas ───────────────────────────────────────────────────────────────────

class PredictRequest(BaseModel):
    container_id: int
    horizon_hours: int = 24


class PredictResponse(BaseModel):
    container_id: int
    predicted_fill_rate: float
    predicted_at: str
    model_version: str
    horizon_hours: int


# ── Endpoint ──────────────────────────────────────────────────────────────────

@router.post("/predict", response_model=PredictResponse)
def predict_fill_rate(body: PredictRequest, conn=Depends(get_db)):
    if _model is None:
        raise HTTPException(
            status_code=503,
            detail="ML model not loaded. Ensure model.pkl exists at MODEL_PATH.",
        )

    container_id = body.container_id

    with conn.cursor() as cur:
        # Container metadata
        cur.execute(
            """
            SELECT capacity_liters, type_id, zone_id
            FROM containers
            WHERE key_container = %s AND is_active = true
            """,
            (container_id,),
        )
        row = cur.fetchone()
        if row is None:
            raise HTTPException(
                status_code=404,
                detail=f"Container {container_id} not found or inactive.",
            )
        capacity_liters, type_id, zone_id = row

        # Zone density — containers per km² (matches EDA query)
        cur.execute(
            """
            SELECT COUNT(c.key_container)::numeric /
                   NULLIF(ST_Area(z.polygon::geography)::numeric / 1e6, 0)
            FROM zones z
            LEFT JOIN containers c ON c.zone_id = z.key_zone AND c.is_active = true
            WHERE z.key_zone = %s
            GROUP BY z.key_zone
            """,
            (zone_id,),
        )
        zone_row = cur.fetchone()
        density_km2 = float(zone_row[0]) if zone_row and zone_row[0] is not None else 0.0

        # Fill history — most recent first, enough for all lag features
        cur.execute(
            """
            SELECT fill_rate FROM fill_history
            WHERE container_id = %s AND NOT is_outlier
            ORDER BY measured_at DESC
            LIMIT %s
            """,
            (container_id, SHIFT_7D + 1),
        )
        rates = [float(r[0]) for r in cur.fetchall()]

    if len(rates) < SHIFT_24H + 1:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Insufficient fill history for container {container_id}: "
                f"{len(rates)} rows available, need at least {SHIFT_24H + 1} "
                f"(24 h of data at 10-min cadence)."
            ),
        )

    # ── Feature vector ────────────────────────────────────────────────────────
    # rates[0] = most recent measurement, rates[N] = N steps (10 min each) ago
    now = datetime.now(timezone.utc)
    fill_latest   = rates[0]
    fill_1h_ago   = rates[SHIFT_1H]  if len(rates) > SHIFT_1H  else fill_latest
    fill_24h_ago  = rates[SHIFT_24H] if len(rates) > SHIFT_24H else fill_latest
    fill_7d_ago   = rates[SHIFT_7D]  if len(rates) > SHIFT_7D  else fill_latest

    # Trailing averages exclude most recent row — matches shift(1).rolling() in training
    fill_24h_avg = float(np.mean(rates[1:SHIFT_24H + 1])) if len(rates) > 1 else fill_latest
    fill_7d_avg  = float(np.mean(rates[1:SHIFT_7D  + 1])) if len(rates) > 1 else fill_latest

    change_rate = (fill_latest - fill_1h_ago) / SHIFT_1H

    X = pd.DataFrame([{
        'hour':                  now.hour,
        'day_of_week':           now.weekday(),
        'day_of_month':          now.day,
        'is_weekend':            int(now.weekday() >= 5),
        'is_peak_hour':          int(now.hour in {7, 8, 9, 17, 18, 19}),
        'fill_rate_1h_ago':      fill_1h_ago,
        'fill_rate_24h_ago':     fill_24h_ago,
        'fill_rate_7d_ago':      fill_7d_ago,
        'fill_rate_24h_avg':     fill_24h_avg,
        'fill_rate_7d_avg':      fill_7d_avg,
        'fill_rate_change_rate': change_rate,
        'capacity_liters':       float(capacity_liters),
        'type_id':               int(type_id),
        'density_km2':           density_km2,
    }])[FEATURE_COLS]

    raw = float(_model.predict(X)[0])
    predicted_fill_rate = round(float(np.clip(raw, 0.0, 100.0)), 2)
    predicted_at = (now + timedelta(hours=body.horizon_hours)).isoformat()

    return PredictResponse(
        container_id=container_id,
        predicted_fill_rate=predicted_fill_rate,
        predicted_at=predicted_at,
        model_version=_metadata.get("version", "unknown") if _metadata else "unknown",
        horizon_hours=body.horizon_hours,
    )
