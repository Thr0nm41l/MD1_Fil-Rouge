import json
from collections import defaultdict, deque
from datetime import date, timedelta
from typing import Any, List, Optional

import psycopg2.extras
from fastapi import APIRouter, Depends, Query

from db import get_db
from schemas.analytics import (
    ChoroplethZone,
    CostsRoiPoint,
    FillBucket,
    FillEvolutionPoint,
    IncidentEvent,
    KpiValue,
    KpisResponse,
    RoutePerformancePoint,
    TypeDistributionItem,
    ZoneCollectionItem,
)
from schemas.history import HeatmapPoint

router = APIRouter()

_COST_PER_KM = 1.20   # €/km
_SAVINGS_RATE = 0.20  # 20 % distance reduction vs un-optimised baseline (epic T10)
_CO2_PER_KM   = 0.27  # kg CO₂ per km (collection truck average)


# ── Shared helpers ────────────────────────────────────────────────────────────

def _period_defaults(from_dt, to_dt):
    if from_dt is None:
        from_dt = date.today() - timedelta(days=30)
    if to_dt is None:
        to_dt = date.today()
    return from_dt, to_dt


def _variation(current: float, previous: float) -> float:
    if previous == 0:
        return 0.0
    return round((current - previous) / previous * 100, 1)


def _period_stats(conn, from_dt: date, to_dt: date, zone_id: Optional[int]) -> dict:
    """Fetch the five measurable KPIs for one time window."""
    params: dict[str, Any] = {"from_dt": from_dt, "to_dt": to_dt}
    if zone_id is not None:
        params["zone_id"] = zone_id
    z_cnt = "AND cnt.zone_id = %(zone_id)s" if zone_id is not None else ""
    z_ads = "AND ads.zone_id = %(zone_id)s" if zone_id is not None else ""
    z_r   = "AND r.zone_id   = %(zone_id)s" if zone_id is not None else ""

    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(f"""
            SELECT
                COALESCE(SUM(c.volume_collected_l), 0) AS volume_collected_l,
                COUNT(c.key_collection)                AS collection_count
            FROM collections c
            JOIN containers cnt ON cnt.key_container = c.container_id
            WHERE c.collected_at::date BETWEEN %(from_dt)s AND %(to_dt)s {z_cnt}
        """, params)
        r1 = cur.fetchone()

    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(f"""
            SELECT
                COALESCE(ROUND(AVG(ads.avg_fill_rate)::numeric, 2), 0) AS avg_fill_rate_pct,
                COALESCE(SUM(ads.overflow_count), 0)                   AS overflow_count
            FROM aggregated_daily_stats ads
            WHERE ads.day_bucket BETWEEN %(from_dt)s AND %(to_dt)s {z_ads}
        """, params)
        r2 = cur.fetchone()

    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(f"""
            SELECT COALESCE(SUM(r.distance_m) / 1000.0, 0) AS total_distance_km
            FROM routes r
            WHERE r.scheduled_at BETWEEN %(from_dt)s AND %(to_dt)s {z_r}
        """, params)
        r3 = cur.fetchone()

    return {
        "volume_collected_l": float(r1["volume_collected_l"]),
        "collection_count":   int(r1["collection_count"]),
        "avg_fill_rate_pct":  float(r2["avg_fill_rate_pct"]),
        "overflow_count":     int(r2["overflow_count"]),
        "total_distance_km":  float(r3["total_distance_km"]),
    }


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/kpis", response_model=KpisResponse)
def get_kpis(
    from_dt: Optional[date] = Query(None, alias="from"),
    to_dt:   Optional[date] = Query(None, alias="to"),
    zone_id: Optional[int]  = Query(None),
    conn=Depends(get_db),
):
    """Six KPI cards with current value and % variation vs the previous equivalent period."""
    from_dt, to_dt = _period_defaults(from_dt, to_dt)
    delta     = to_dt - from_dt
    prev_to   = from_dt - timedelta(days=1)
    prev_from = prev_to - delta

    curr = _period_stats(conn, from_dt, to_dt, zone_id)
    prev = _period_stats(conn, prev_from, prev_to, zone_id)

    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM containers WHERE is_active = true")
        active_count = float(cur.fetchone()[0])

    return KpisResponse(
        volume_collected_l=KpiValue(value=curr["volume_collected_l"], variation_pct=_variation(curr["volume_collected_l"], prev["volume_collected_l"])),
        collection_count=  KpiValue(value=curr["collection_count"],   variation_pct=_variation(curr["collection_count"],   prev["collection_count"])),
        avg_fill_rate_pct= KpiValue(value=curr["avg_fill_rate_pct"],  variation_pct=_variation(curr["avg_fill_rate_pct"],  prev["avg_fill_rate_pct"])),
        overflow_count=    KpiValue(value=curr["overflow_count"],     variation_pct=_variation(curr["overflow_count"],     prev["overflow_count"])),
        total_distance_km= KpiValue(value=curr["total_distance_km"],  variation_pct=_variation(curr["total_distance_km"],  prev["total_distance_km"])),
        active_containers= KpiValue(value=active_count,               variation_pct=0.0),
    )


@router.get("/volume-evolution")
def get_volume_evolution(
    from_dt: Optional[date] = Query(None, alias="from"),
    to_dt:   Optional[date] = Query(None, alias="to"),
    zone_id: Optional[int]  = Query(None),
    conn=Depends(get_db),
):
    """Daily collected volume per waste type — stacked area chart source."""
    from_dt, to_dt = _period_defaults(from_dt, to_dt)
    params: dict[str, Any] = {"from_dt": from_dt, "to_dt": to_dt}
    z = "AND cnt.zone_id = %(zone_id)s" if zone_id is not None else ""
    if zone_id is not None:
        params["zone_id"] = zone_id

    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(f"""
            SELECT
                c.collected_at::date            AS date,
                COALESCE(ct.name, 'Unknown')    AS type_name,
                COALESCE(SUM(c.volume_collected_l), 0) AS volume_l
            FROM collections c
            JOIN containers cnt    ON cnt.key_container = c.container_id
            LEFT JOIN container_type ct ON ct.key_type = cnt.type_id
            WHERE c.collected_at::date BETWEEN %(from_dt)s AND %(to_dt)s {z}
            GROUP BY c.collected_at::date, ct.name
            ORDER BY c.collected_at::date, ct.name
        """, params)
        rows = cur.fetchall()

    by_date: dict[str, dict] = defaultdict(dict)
    for r in rows:
        by_date[str(r["date"])][r["type_name"]] = float(r["volume_l"])
    return [{"date": d, **volumes} for d, volumes in sorted(by_date.items())]


@router.get("/type-distribution", response_model=List[TypeDistributionItem])
def get_type_distribution(
    zone_id: Optional[int] = Query(None),
    conn=Depends(get_db),
):
    """Active container count and % per waste type — donut chart source."""
    params: dict[str, Any] = {}
    z = "AND cnt.zone_id = %(zone_id)s" if zone_id is not None else ""
    if zone_id is not None:
        params["zone_id"] = zone_id

    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(f"""
            SELECT
                COALESCE(ct.name, 'Unknown') AS type,
                COUNT(cnt.key_container)     AS count
            FROM containers cnt
            LEFT JOIN container_type ct ON ct.key_type = cnt.type_id
            WHERE cnt.is_active = true {z}
            GROUP BY ct.name
            ORDER BY count DESC
        """, params)
        rows = cur.fetchall()

    total = sum(r["count"] for r in rows) or 1
    return [
        TypeDistributionItem(
            type=r["type"],
            count=r["count"],
            pct=round(r["count"] / total * 100, 1),
        )
        for r in rows
    ]


@router.get("/zone-collections", response_model=List[ZoneCollectionItem])
def get_zone_collections(
    from_dt: Optional[date] = Query(None, alias="from"),
    to_dt:   Optional[date] = Query(None, alias="to"),
    zone_id: Optional[int]  = Query(None),
    conn=Depends(get_db),
):
    """Collection count and volume per zone — horizontal bar chart source."""
    from_dt, to_dt = _period_defaults(from_dt, to_dt)
    params: dict[str, Any] = {"from_dt": from_dt, "to_dt": to_dt}
    z = "AND z.key_zone = %(zone_id)s" if zone_id is not None else ""
    if zone_id is not None:
        params["zone_id"] = zone_id

    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(f"""
            SELECT
                z.key_zone,
                z.name,
                COUNT(c.key_collection)              AS collection_count,
                COALESCE(SUM(c.volume_collected_l), 0) AS volume_l
            FROM zones z
            JOIN containers cnt ON cnt.zone_id = z.key_zone
            JOIN collections c  ON c.container_id = cnt.key_container
            WHERE c.collected_at::date BETWEEN %(from_dt)s AND %(to_dt)s {z}
            GROUP BY z.key_zone, z.name
            ORDER BY volume_l DESC
        """, params)
        rows = cur.fetchall()

    return [
        ZoneCollectionItem(
            zone_id=r["key_zone"],
            zone_name=r["name"],
            collection_count=r["collection_count"],
            volume_l=float(r["volume_l"]),
        )
        for r in rows
    ]


@router.get("/fill-distribution", response_model=List[FillBucket])
def get_fill_distribution(
    from_dt: Optional[date] = Query(None, alias="from"),
    to_dt:   Optional[date] = Query(None, alias="to"),
    zone_id: Optional[int]  = Query(None),
    conn=Depends(get_db),
):
    """Fill rate distribution in 10 % buckets — histogram source."""
    from_dt, to_dt = _period_defaults(from_dt, to_dt)
    params: dict[str, Any] = {"from_dt": from_dt, "to_dt": to_dt}
    z = "AND ads.zone_id = %(zone_id)s" if zone_id is not None else ""
    if zone_id is not None:
        params["zone_id"] = zone_id

    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(f"""
            SELECT
                LEAST(FLOOR(avg_fill_rate / 10) * 10, 90)::int        AS bucket_min,
                LEAST(FLOOR(avg_fill_rate / 10) * 10 + 10, 100)::int  AS bucket_max,
                COUNT(*) AS count
            FROM aggregated_daily_stats ads
            WHERE ads.day_bucket BETWEEN %(from_dt)s AND %(to_dt)s
              AND ads.avg_fill_rate IS NOT NULL {z}
            GROUP BY bucket_min, bucket_max
            ORDER BY bucket_min
        """, params)
        rows = cur.fetchall()

    return [FillBucket(bucket_min=r["bucket_min"], bucket_max=r["bucket_max"], count=r["count"]) for r in rows]


@router.get("/fill-evolution", response_model=List[FillEvolutionPoint])
def get_fill_evolution(
    from_dt:    Optional[date] = Query(None, alias="from"),
    to_dt:      Optional[date] = Query(None, alias="to"),
    zone_id:    Optional[int]  = Query(None),
    moving_avg: bool           = Query(False),
    conn=Depends(get_db),
):
    """Daily average fill rate, with optional 7-day moving average — line chart source."""
    from_dt, to_dt = _period_defaults(from_dt, to_dt)
    params: dict[str, Any] = {"from_dt": from_dt, "to_dt": to_dt}
    z = "AND ads.zone_id = %(zone_id)s" if zone_id is not None else ""
    if zone_id is not None:
        params["zone_id"] = zone_id

    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(f"""
            SELECT
                day_bucket                                  AS date,
                ROUND(AVG(avg_fill_rate)::numeric, 2)       AS avg_fill_rate
            FROM aggregated_daily_stats ads
            WHERE ads.day_bucket BETWEEN %(from_dt)s AND %(to_dt)s {z}
            GROUP BY day_bucket
            ORDER BY day_bucket
        """, params)
        rows = cur.fetchall()

    points = [
        FillEvolutionPoint(date=r["date"], avg_fill_rate=float(r["avg_fill_rate"] or 0))
        for r in rows
    ]

    if moving_avg:
        window: deque = deque(maxlen=7)
        for pt in points:
            window.append(pt.avg_fill_rate)
            pt.moving_avg_7d = round(sum(window) / len(window), 2)

    return points


@router.get("/route-performance", response_model=List[RoutePerformancePoint])
def get_route_performance(
    from_dt: Optional[date] = Query(None, alias="from"),
    to_dt:   Optional[date] = Query(None, alias="to"),
    zone_id: Optional[int]  = Query(None),
    conn=Depends(get_db),
):
    """One point per route (distance vs volume) — scatter / bubble chart source."""
    from_dt, to_dt = _period_defaults(from_dt, to_dt)
    params: dict[str, Any] = {"from_dt": from_dt, "to_dt": to_dt}
    z = "AND r.zone_id = %(zone_id)s" if zone_id is not None else ""
    if zone_id is not None:
        params["zone_id"] = zone_id

    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(f"""
            SELECT
                r.key_route                                   AS route_id,
                COALESCE(r.distance_m / 1000.0, 0)           AS distance_km,
                COALESCE(SUM(c.volume_collected_l), 0)        AS volume_collected_l,
                COUNT(DISTINCT rs.key_step)                   AS container_count
            FROM routes r
            LEFT JOIN collections c  ON c.route_id  = r.key_route
            LEFT JOIN route_steps rs ON rs.route_id = r.key_route
            WHERE r.scheduled_at BETWEEN %(from_dt)s AND %(to_dt)s {z}
            GROUP BY r.key_route, r.distance_m
            ORDER BY r.key_route
        """, params)
        rows = cur.fetchall()

    return [
        RoutePerformancePoint(
            route_id=r["route_id"],
            distance_km=float(r["distance_km"]),
            volume_collected_l=float(r["volume_collected_l"]),
            container_count=int(r["container_count"]),
        )
        for r in rows
    ]


@router.get("/incidents", response_model=List[IncidentEvent])
def get_incidents(
    from_dt:     Optional[date] = Query(None, alias="from"),
    to_dt:       Optional[date] = Query(None, alias="to"),
    zone_id:     Optional[int]  = Query(None),
    type_filter: Optional[str]  = Query(None, alias="type", pattern="^(signalement|notification)$"),
    conn=Depends(get_db),
):
    """Chronological mix of signalements and threshold-breach notifications — timeline source."""
    from_dt, to_dt = _period_defaults(from_dt, to_dt)
    params: dict[str, Any] = {"from_dt": from_dt, "to_dt": to_dt}
    if zone_id is not None:
        params["zone_id"] = zone_id

    parts: list[str] = []

    if type_filter in (None, "signalement"):
        z = "AND s.zone_id = %(zone_id)s" if zone_id is not None else ""
        parts.append(f"""
            SELECT s.created_at AS timestamp, 'signalement'::text AS type,
                   s.zone_id, s.container_id, s.description, NULL::text AS content
            FROM signalements s
            WHERE s.created_at::date BETWEEN %(from_dt)s AND %(to_dt)s {z}
        """)

    if type_filter in (None, "notification"):
        parts.append("""
            SELECT n.created_at AS timestamp, 'notification'::text AS type,
                   NULL::integer AS zone_id, n.container_id, n.title AS description, n.content
            FROM notifications n
            WHERE n.created_at::date BETWEEN %(from_dt)s AND %(to_dt)s
              AND n.type = 'threshold_breach'
        """)

    query = " UNION ALL ".join(parts) + " ORDER BY timestamp"

    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(query, params)
        rows = cur.fetchall()

    return [
        IncidentEvent(
            timestamp=r["timestamp"],
            type=r["type"],
            zone_id=r["zone_id"],
            container_id=r["container_id"],
            description=r["description"],
            content=r["content"],
        )
        for r in rows
    ]


@router.get("/heatmap", response_model=List[HeatmapPoint])
def get_heatmap(
    from_dt: Optional[date] = Query(None, alias="from"),
    to_dt:   Optional[date] = Query(None, alias="to"),
    conn=Depends(get_db),
):
    """Measurement count by (day_of_week × hour_of_day) — heatmap chart source."""
    if from_dt is None:
        from_dt = date.today() - timedelta(days=90)
    if to_dt is None:
        to_dt = date.today()

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


@router.get("/choropleth", response_model=List[ChoroplethZone])
def get_choropleth(conn=Depends(get_db)):
    """Per-zone density and avg fill rate with GeoJSON polygon — Leaflet choropleth source."""
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("""
            SELECT
                zone_id,
                zone_name,
                ST_AsGeoJSON(polygon) AS polygon_json,
                density_km2,
                avg_fill_rate
            FROM get_choropleth_data()
        """)
        rows = cur.fetchall()

    return [
        ChoroplethZone(
            zone_id=r["zone_id"],
            zone_name=r["zone_name"],
            polygon=json.loads(r["polygon_json"]) if r["polygon_json"] else None,
            density_km2=float(r["density_km2"] or 0),
            avg_fill_rate=float(r["avg_fill_rate"] or 0),
        )
        for r in rows
    ]


@router.get("/costs-roi", response_model=List[CostsRoiPoint])
def get_costs_roi(
    from_dt: Optional[date] = Query(None, alias="from"),
    to_dt:   Optional[date] = Query(None, alias="to"),
    zone_id: Optional[int]  = Query(None),
    conn=Depends(get_db),
):
    """Monthly cost and ROI vs un-optimised baseline — mixed bar+line chart source."""
    from_dt, to_dt = _period_defaults(from_dt, to_dt)
    params: dict[str, Any] = {"from_dt": from_dt, "to_dt": to_dt}
    z = "AND r.zone_id = %(zone_id)s" if zone_id is not None else ""
    if zone_id is not None:
        params["zone_id"] = zone_id

    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(f"""
            SELECT
                TO_CHAR(r.scheduled_at, 'YYYY-MM')      AS month,
                COALESCE(SUM(r.distance_m) / 1000.0, 0) AS distance_km
            FROM routes r
            WHERE r.scheduled_at BETWEEN %(from_dt)s AND %(to_dt)s
              AND r.status = 'terminee' {z}
            GROUP BY TO_CHAR(r.scheduled_at, 'YYYY-MM')
            ORDER BY month
        """, params)
        rows = cur.fetchall()

    result = []
    for r in rows:
        distance_km      = float(r["distance_km"])
        total_cost       = round(distance_km * _COST_PER_KM, 2)
        distance_saved   = distance_km * _SAVINGS_RATE
        estimated_savings = round(distance_saved * _COST_PER_KM, 2)
        co2_saved_kg     = round(distance_saved * _CO2_PER_KM, 1)
        result.append(CostsRoiPoint(
            month=r["month"],
            total_cost=total_cost,
            estimated_savings=estimated_savings,
            co2_saved_kg=co2_saved_kg,
        ))
    return result
