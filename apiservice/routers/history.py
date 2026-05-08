from datetime import datetime, timedelta
from typing import List, Optional

import psycopg2.extras
from fastapi import APIRouter, Depends, HTTPException, Query

from db import get_db
from schemas.history import HeatmapPoint, HistoryBucket

router = APIRouter()


# ── Static routes (must be declared before /{container_id}) ──────────────────

@router.get("/heatmap-data", response_model=List[HeatmapPoint])
def get_heatmap_data(
    from_dt: Optional[datetime] = Query(None, alias="from"),
    to_dt:   Optional[datetime] = Query(None, alias="to"),
    conn=Depends(get_db),
):
    """Measurement counts by (day_of_week × hour_of_day) for the A8 heatmap chart."""
    if from_dt is None:
        from_dt = datetime.utcnow() - timedelta(days=90)
    if to_dt is None:
        to_dt = datetime.utcnow()

    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(
            "SELECT day_of_week, hour_of_day, cnt FROM get_heatmap_data(%s, %s)",
            (from_dt, to_dt),
        )
        rows = cur.fetchall()
    return [
        HeatmapPoint(day_of_week=r["day_of_week"], hour_of_day=r["hour_of_day"], count=r["cnt"])
        for r in rows
    ]


# ── Single resource ───────────────────────────────────────────────────────────

@router.get("/{container_id}", response_model=List[HistoryBucket])
def get_container_history(
    container_id: int,
    from_dt:     Optional[datetime] = Query(None, alias="from"),
    to_dt:       Optional[datetime] = Query(None, alias="to"),
    granularity: str                = Query("raw", pattern="^(raw|hourly|daily)$"),
    conn=Depends(get_db),
):
    """
    Time series for one container.
    - raw:    one row per IoT tick (fill_history, capped at 10 000)
    - hourly: aggregated_hourly_stats
    - daily:  aggregated_daily_stats
    """
    with conn.cursor() as cur:
        cur.execute(
            "SELECT 1 FROM containers WHERE key_container = %s AND is_active = true",
            (container_id,),
        )
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Container not found")

    if from_dt is None:
        from_dt = datetime.utcnow() - timedelta(days=7)
    if to_dt is None:
        to_dt = datetime.utcnow()

    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        if granularity == "raw":
            cur.execute(
                """
                SELECT
                    measured_at  AS bucket,
                    fill_rate    AS avg_fill_rate,
                    fill_rate    AS min_fill_rate,
                    fill_rate    AS max_fill_rate,
                    1            AS measurement_count
                FROM fill_history
                WHERE container_id = %(id)s
                  AND measured_at BETWEEN %(from_dt)s AND %(to_dt)s
                ORDER BY measured_at ASC
                LIMIT 10000
                """,
                {"id": container_id, "from_dt": from_dt, "to_dt": to_dt},
            )
        elif granularity == "hourly":
            cur.execute(
                """
                SELECT
                    hour_bucket       AS bucket,
                    avg_fill_rate,
                    min_fill_rate,
                    max_fill_rate,
                    measurement_count
                FROM aggregated_hourly_stats
                WHERE container_id = %(id)s
                  AND hour_bucket BETWEEN %(from_dt)s AND %(to_dt)s
                ORDER BY hour_bucket ASC
                """,
                {"id": container_id, "from_dt": from_dt, "to_dt": to_dt},
            )
        else:  # daily
            cur.execute(
                """
                SELECT
                    day_bucket::timestamp AS bucket,
                    avg_fill_rate,
                    min_fill_rate,
                    max_fill_rate,
                    measurement_count
                FROM aggregated_daily_stats
                WHERE container_id = %(id)s
                  AND day_bucket BETWEEN %(from_dt)s::date AND %(to_dt)s::date
                ORDER BY day_bucket ASC
                """,
                {"id": container_id, "from_dt": from_dt, "to_dt": to_dt},
            )
        rows = cur.fetchall()

    return [
        HistoryBucket(
            bucket=r["bucket"],
            avg_fill_rate=float(r["avg_fill_rate"] or 0),
            min_fill_rate=float(r["min_fill_rate"]) if r["min_fill_rate"] is not None else None,
            max_fill_rate=float(r["max_fill_rate"]) if r["max_fill_rate"] is not None else None,
            measurement_count=int(r["measurement_count"]),
        )
        for r in rows
    ]
