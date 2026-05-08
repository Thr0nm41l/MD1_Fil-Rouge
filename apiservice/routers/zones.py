import json
from typing import Any, List

import psycopg2
import psycopg2.extras
from fastapi import APIRouter, Depends, HTTPException

from db import get_db
from schemas.containers import ContainerOut
from schemas.zones import ZoneCreate, ZoneDensity, ZoneOut, ZoneStats, ZoneUpdate

router = APIRouter()


def _row_to_zone(row: dict) -> ZoneOut:
    d = dict(row)
    if d.get("polygon") and isinstance(d["polygon"], str):
        d["polygon"] = json.loads(d["polygon"])
    return ZoneOut(**d)


def _fetch_or_404(conn, zone_id: int) -> ZoneOut:
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(
            "SELECT key_zone, name, postal_code, ST_AsGeoJSON(polygon) AS polygon"
            " FROM zones WHERE key_zone = %s",
            (zone_id,),
        )
        row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Zone not found")
    return _row_to_zone(row)


# ── Static routes (must be declared before /{zone_id}) ───────────────────────

@router.get("/stats", response_model=List[ZoneStats])
def get_zones_stats(conn=Depends(get_db)):
    """Aggregated stats per zone: container count, average fill rate, 30-day overflow count."""
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("""
            SELECT
                z.key_zone,
                z.name,
                COUNT(DISTINCT c.key_container)       AS container_count,
                ROUND(AVG(c.fill_rate)::numeric, 2)   AS avg_fill_rate,
                COALESCE(SUM(ads.overflow_count), 0)  AS overflow_count_30d
            FROM zones z
            LEFT JOIN containers c
                   ON c.zone_id = z.key_zone AND c.is_active = true
            LEFT JOIN aggregated_daily_stats ads
                   ON ads.zone_id = z.key_zone
                  AND ads.day_bucket >= CURRENT_DATE - INTERVAL '30 days'
            GROUP BY z.key_zone, z.name
            ORDER BY z.key_zone
        """)
        rows = cur.fetchall()
    return [
        ZoneStats(
            zone_id=r["key_zone"],
            zone_name=r["name"],
            container_count=r["container_count"],
            avg_fill_rate=float(r["avg_fill_rate"] or 0),
            overflow_count_30d=int(r["overflow_count_30d"]),
        )
        for r in rows
    ]


@router.get("/density", response_model=List[ZoneDensity])
def get_zones_density(conn=Depends(get_db)):
    """Active containers per km² for every zone that has polygon geometry."""
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("""
            SELECT
                z.key_zone,
                z.name,
                ROUND(
                    COUNT(c.key_container)::numeric /
                    NULLIF(ST_Area(z.polygon::geography)::numeric / 1e6, 0),
                    4
                ) AS density_km2
            FROM zones z
            LEFT JOIN containers c
                   ON ST_Within(c.location, z.polygon) AND c.is_active = true
            WHERE z.polygon IS NOT NULL
            GROUP BY z.key_zone, z.name, z.polygon
            ORDER BY z.key_zone
        """)
        rows = cur.fetchall()
    return [
        ZoneDensity(
            zone_id=r["key_zone"],
            zone_name=r["name"],
            density_km2=float(r["density_km2"] or 0),
        )
        for r in rows
    ]


# ── Collection ────────────────────────────────────────────────────────────────

@router.get("", response_model=List[ZoneOut])
def list_zones(conn=Depends(get_db)):
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(
            "SELECT key_zone, name, postal_code, ST_AsGeoJSON(polygon) AS polygon"
            " FROM zones ORDER BY key_zone"
        )
        rows = cur.fetchall()
    return [_row_to_zone(r) for r in rows]


@router.post("", response_model=ZoneOut, status_code=201)
def create_zone(body: ZoneCreate, conn=Depends(get_db)):
    """
    Create a zone with a GeoJSON polygon. The polygon is stored as
    GEOMETRY(Polygon, 4326) via ST_GeomFromGeoJSON.
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO zones (name, postal_code, polygon)
            VALUES (
                %(name)s, %(postal_code)s,
                ST_SetSRID(ST_GeomFromGeoJSON(%(polygon_json)s), 4326)
            )
            RETURNING key_zone
            """,
            {
                "name": body.name,
                "postal_code": body.postal_code,
                "polygon_json": json.dumps(body.polygon),
            },
        )
        key = cur.fetchone()[0]
    return _fetch_or_404(conn, key)


# ── Single resource ───────────────────────────────────────────────────────────

@router.get("/{zone_id}", response_model=ZoneOut)
def get_zone(zone_id: int, conn=Depends(get_db)):
    return _fetch_or_404(conn, zone_id)


@router.put("/{zone_id}", response_model=ZoneOut)
def update_zone(zone_id: int, body: ZoneUpdate, conn=Depends(get_db)):
    set_parts: list[str] = []
    params: dict[str, Any] = {}

    if body.name is not None:
        set_parts.append("name = %(name)s")
        params["name"] = body.name
    if body.postal_code is not None:
        set_parts.append("postal_code = %(postal_code)s")
        params["postal_code"] = body.postal_code
    if body.polygon is not None:
        set_parts.append("polygon = ST_SetSRID(ST_GeomFromGeoJSON(%(polygon_json)s), 4326)")
        params["polygon_json"] = json.dumps(body.polygon)

    if not set_parts:
        raise HTTPException(status_code=400, detail="No fields to update")

    params["id"] = zone_id
    with conn.cursor() as cur:
        cur.execute(
            f"UPDATE zones SET {', '.join(set_parts)} WHERE key_zone = %(id)s RETURNING key_zone",
            params,
        )
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Zone not found")

    return _fetch_or_404(conn, zone_id)


@router.delete("/{zone_id}")
def delete_zone(zone_id: int, conn=Depends(get_db)):
    """
    Hard delete. Returns 409 if containers or routes still reference this zone.
    Call DELETE /containers/{id} (soft-delete) first to clear references.
    """
    try:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM zones WHERE key_zone = %s RETURNING key_zone",
                (zone_id,),
            )
            if not cur.fetchone():
                raise HTTPException(status_code=404, detail="Zone not found")
    except psycopg2.errors.ForeignKeyViolation:
        conn.rollback()
        raise HTTPException(
            status_code=409,
            detail="Zone cannot be deleted — containers or routes still reference it",
        )
    return {"deleted": True}


@router.get("/{zone_id}/containers", response_model=List[ContainerOut])
def get_zone_containers(zone_id: int, conn=Depends(get_db)):
    """
    Active containers whose GPS position falls inside the zone polygon.
    Uses the get_containers_in_zone() SQL function (ST_Within + GIST index).
    """
    _fetch_or_404(conn, zone_id)
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(
            """
            SELECT
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
            FROM get_containers_in_zone(%(zone_id)s) AS c
            ORDER BY c.key_container
            """,
            {"zone_id": zone_id},
        )
        rows = cur.fetchall()
    return [ContainerOut(**dict(r)) for r in rows]
