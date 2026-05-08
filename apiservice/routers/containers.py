import json
from datetime import datetime, timedelta
from typing import Any, List, Optional

import psycopg2.extras
from fastapi import APIRouter, Depends, HTTPException, Query

from db import get_db
from schemas.common import PaginatedResponse
from schemas.containers import (
    ContainerCreate,
    ContainerDetail,
    ContainerOut,
    ContainerStats,
    ContainerUpdate,
    HistoryPoint,
    MeasureCreate,
    MeasureOut,
)
from utils import geojson_collection, geojson_feature

router = APIRouter()

# Reusable SELECT projection — extracts lat/lng from PostGIS Point
_COLS = """
    c.key_container,
    ST_Y(c.location) AS lat,
    ST_X(c.location) AS lng,
    c.type_id,
    c.zone_id,
    c.capacity_liters,
    c.fill_rate,
    c.status,
    c.fill_threshold_pct,
    c.last_updated,
    c.is_active
"""


def _to_container(row: dict) -> ContainerOut:
    return ContainerOut(**dict(row))


def _fetch_or_404(conn, container_id: int) -> ContainerOut:
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(
            f"SELECT {_COLS} FROM containers c"
            " WHERE c.key_container = %(id)s AND c.is_active = true",
            {"id": container_id},
        )
        row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Container not found")
    return _to_container(row)


# ── Static routes (must be declared before /{container_id}) ──────────────────

@router.get("/critical", response_model=List[ContainerOut])
def list_critical_containers(conn=Depends(get_db)):
    """Containers whose current fill_rate exceeds their configured threshold."""
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(
            f"SELECT {_COLS} FROM containers c"
            " WHERE c.is_active = true AND c.fill_rate > c.fill_threshold_pct"
            " ORDER BY c.fill_rate DESC"
        )
        rows = cur.fetchall()
    return [_to_container(r) for r in rows]


@router.get("/stats", response_model=ContainerStats)
def get_container_stats(conn=Depends(get_db)):
    """Global KPIs across all active containers."""
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("""
            SELECT
                COUNT(*)                                                                    AS total_active,
                ROUND(AVG(fill_rate)::numeric, 2)                                           AS avg_fill_rate,
                ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY fill_rate)::numeric, 2)   AS median_fill_rate,
                ROUND(
                    100.0 * COUNT(*) FILTER (WHERE fill_rate > fill_threshold_pct)
                    / NULLIF(COUNT(*), 0), 2
                )                                                                           AS overflow_rate_pct,
                COUNT(*) FILTER (WHERE status = 'empty')    AS status_empty,
                COUNT(*) FILTER (WHERE status = 'normal')   AS status_normal,
                COUNT(*) FILTER (WHERE status = 'full')     AS status_full,
                COUNT(*) FILTER (WHERE status = 'critical') AS status_critical
            FROM containers
            WHERE is_active = true
        """)
        r = cur.fetchone()
    return ContainerStats(
        total_active=r["total_active"],
        avg_fill_rate=float(r["avg_fill_rate"] or 0),
        median_fill_rate=float(r["median_fill_rate"] or 0),
        overflow_rate_pct=float(r["overflow_rate_pct"] or 0),
        by_status={
            "empty":    r["status_empty"],
            "normal":   r["status_normal"],
            "full":     r["status_full"],
            "critical": r["status_critical"],
        },
    )


@router.get("/map")
def get_containers_map(conn=Depends(get_db)):
    """GeoJSON FeatureCollection of all active containers for Leaflet."""
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("""
            SELECT
                key_container,
                fill_rate,
                status,
                type_id,
                zone_id,
                ST_AsGeoJSON(location) AS geojson
            FROM containers
            WHERE is_active = true
        """)
        rows = cur.fetchall()
    features = [
        geojson_feature(
            r["geojson"],
            {
                "key_container": r["key_container"],
                "fill_rate":     float(r["fill_rate"]),
                "status":        r["status"],
                "type_id":       r["type_id"],
                "zone_id":       r["zone_id"],
            },
        )
        for r in rows
    ]
    return geojson_collection(features)


# ── Collection ────────────────────────────────────────────────────────────────

@router.get("", response_model=PaginatedResponse[ContainerOut])
def list_containers(
    zone_id:       Optional[int]   = Query(None),
    type_id:       Optional[int]   = Query(None),
    status:        Optional[str]   = Query(None, pattern="^(empty|normal|full|critical)$"),
    fill_rate_min: Optional[float] = Query(None, ge=0, le=100),
    fill_rate_max: Optional[float] = Query(None, ge=0, le=100),
    is_active:     bool            = Query(True),
    page:          int             = Query(1, ge=1),
    per_page:      int             = Query(20, ge=1, le=100),
    conn=Depends(get_db),
):
    where: list[str] = ["c.is_active = %(is_active)s"]
    params: dict[str, Any] = {"is_active": is_active}

    if zone_id is not None:
        where.append("c.zone_id = %(zone_id)s")
        params["zone_id"] = zone_id
    if type_id is not None:
        where.append("c.type_id = %(type_id)s")
        params["type_id"] = type_id
    if status is not None:
        where.append("c.status = %(status)s")
        params["status"] = status
    if fill_rate_min is not None:
        where.append("c.fill_rate >= %(fill_rate_min)s")
        params["fill_rate_min"] = fill_rate_min
    if fill_rate_max is not None:
        where.append("c.fill_rate <= %(fill_rate_max)s")
        params["fill_rate_max"] = fill_rate_max

    where_sql = " AND ".join(where)

    with conn.cursor() as cur:
        cur.execute(f"SELECT COUNT(*) FROM containers c WHERE {where_sql}", params)
        total = cur.fetchone()[0]

    offset = (page - 1) * per_page
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(
            f"SELECT {_COLS} FROM containers c WHERE {where_sql}"
            " ORDER BY c.key_container"
            " LIMIT %(limit)s OFFSET %(offset)s",
            {**params, "limit": per_page, "offset": offset},
        )
        rows = cur.fetchall()

    return PaginatedResponse(
        page=page, per_page=per_page, total=total,
        items=[_to_container(r) for r in rows],
    )


@router.post("", response_model=ContainerOut, status_code=201)
def create_container(body: ContainerCreate, conn=Depends(get_db)):
    """
    Insert a new container. The assign_zone_to_container trigger automatically
    sets zone_id based on the GPS position via ST_Within.
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO containers (location, type_id, capacity_liters, fill_threshold_pct)
            VALUES (
                ST_SetSRID(ST_MakePoint(%(lng)s, %(lat)s), 4326),
                %(type_id)s, %(capacity_liters)s, %(fill_threshold_pct)s
            )
            RETURNING key_container
            """,
            {
                "lng": body.lng, "lat": body.lat,
                "type_id": body.type_id,
                "capacity_liters": body.capacity_liters,
                "fill_threshold_pct": body.fill_threshold_pct,
            },
        )
        key = cur.fetchone()[0]
    return _fetch_or_404(conn, key)


# ── Single resource ───────────────────────────────────────────────────────────

@router.get("/{container_id}", response_model=ContainerDetail)
def get_container(container_id: int, conn=Depends(get_db)):
    """Container detail with its most recent IoT measurement."""
    container = _fetch_or_404(conn, container_id)
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(
            """
            SELECT key_history, container_id, fill_rate, temperature, battery_pct, is_outlier, measured_at
            FROM fill_history
            WHERE container_id = %s
            ORDER BY measured_at DESC
            LIMIT 1
            """,
            (container_id,),
        )
        row = cur.fetchone()
    last_measure = MeasureOut(**dict(row)) if row else None
    return ContainerDetail(**container.model_dump(), last_measure=last_measure)


@router.put("/{container_id}", response_model=ContainerOut)
def update_container(container_id: int, body: ContainerUpdate, conn=Depends(get_db)):
    """Partial update. Providing lat requires lng and vice-versa."""
    set_parts: list[str] = []
    params: dict[str, Any] = {}

    if body.lat is not None and body.lng is not None:
        set_parts.append("location = ST_SetSRID(ST_MakePoint(%(lng)s, %(lat)s), 4326)")
        params["lat"] = body.lat
        params["lng"] = body.lng
    elif body.lat is not None or body.lng is not None:
        raise HTTPException(status_code=400, detail="lat and lng must be provided together")
    if body.type_id is not None:
        set_parts.append("type_id = %(type_id)s")
        params["type_id"] = body.type_id
    if body.capacity_liters is not None:
        set_parts.append("capacity_liters = %(capacity_liters)s")
        params["capacity_liters"] = body.capacity_liters
    if body.fill_threshold_pct is not None:
        set_parts.append("fill_threshold_pct = %(fill_threshold_pct)s")
        params["fill_threshold_pct"] = body.fill_threshold_pct

    if not set_parts:
        raise HTTPException(status_code=400, detail="No fields to update")

    set_parts.append("last_updated = NOW()")
    params["id"] = container_id

    with conn.cursor() as cur:
        cur.execute(
            f"UPDATE containers SET {', '.join(set_parts)}"
            " WHERE key_container = %(id)s AND is_active = true"
            " RETURNING key_container",
            params,
        )
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Container not found")

    return _fetch_or_404(conn, container_id)


@router.delete("/{container_id}")
def delete_container(container_id: int, conn=Depends(get_db)):
    """Soft delete — sets is_active = false, never removes the row."""
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE containers SET is_active = false, last_updated = NOW()"
            " WHERE key_container = %s AND is_active = true"
            " RETURNING key_container",
            (container_id,),
        )
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Container not found")
    return {"deleted": True}


@router.get("/{container_id}/history", response_model=List[HistoryPoint])
def get_container_history(
    container_id: int,
    from_dt: Optional[datetime] = Query(None, alias="from"),
    to_dt:   Optional[datetime] = Query(None, alias="to"),
    conn=Depends(get_db),
):
    """Raw fill_history time series. Defaults to the last 7 days. Capped at 5 000 rows."""
    _fetch_or_404(conn, container_id)

    if from_dt is None:
        from_dt = datetime.utcnow() - timedelta(days=7)
    if to_dt is None:
        to_dt = datetime.utcnow()

    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(
            """
            SELECT fill_rate, temperature, battery_pct, is_outlier, measured_at
            FROM fill_history
            WHERE container_id = %(id)s
              AND measured_at >= %(from_dt)s
              AND measured_at <= %(to_dt)s
            ORDER BY measured_at ASC
            LIMIT 5000
            """,
            {"id": container_id, "from_dt": from_dt, "to_dt": to_dt},
        )
        rows = cur.fetchall()
    return [HistoryPoint(**dict(r)) for r in rows]


@router.post("/{container_id}/measures", response_model=MeasureOut, status_code=201)
def ingest_measure(container_id: int, body: MeasureCreate, conn=Depends(get_db)):
    """
    Ingest one IoT measurement.
    - Rejects duplicates within the same clock-minute (C14).
    - Flags outliers when the delta from the current fill_rate exceeds 40 % (C15).
    - DB triggers update containers.fill_rate / status and fire threshold alerts (C16, C17).
    """
    with conn.cursor() as cur:
        cur.execute(
            "SELECT fill_rate FROM containers WHERE key_container = %s AND is_active = true",
            (container_id,),
        )
        row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Container not found")

    current_fill = float(row[0])
    measured_at = body.measured_at or datetime.utcnow()

    with conn.cursor() as cur:
        cur.execute("SELECT is_duplicate_measurement(%s, %s)", (container_id, measured_at))
        if cur.fetchone()[0]:
            raise HTTPException(
                status_code=409,
                detail="Duplicate — a reading for this container already exists within the same minute",
            )

    is_outlier = abs(body.fill_rate - current_fill) > 40

    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(
            """
            INSERT INTO fill_history
                (container_id, device_id, fill_rate, temperature, battery_pct, is_outlier, measured_at)
            VALUES
                (%(container_id)s, %(device_id)s, %(fill_rate)s, %(temperature)s,
                 %(battery_pct)s, %(is_outlier)s, %(measured_at)s)
            RETURNING key_history, container_id, fill_rate, temperature, battery_pct, is_outlier, measured_at
            """,
            {
                "container_id": container_id,
                "device_id":    body.device_id,
                "fill_rate":    body.fill_rate,
                "temperature":  body.temperature,
                "battery_pct":  body.battery_pct,
                "is_outlier":   is_outlier,
                "measured_at":  measured_at,
            },
        )
        result = cur.fetchone()
    return MeasureOut(**dict(result))
