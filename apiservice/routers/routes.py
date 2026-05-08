import json
from datetime import date, timedelta
from io import BytesIO
from typing import Any, List, Optional

import psycopg2.extras
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response

from db import get_db
from schemas.common import PaginatedResponse
from schemas.routes import RouteDetail, RouteOut, RouteStats, RouteStep

router = APIRouter()


def _fetch_route_or_404(conn, route_id: int) -> RouteDetail:
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(
            """
            SELECT
                key_route, zone_id, team_id, name, status,
                scheduled_at, started_at, completed_at, distance_m,
                ST_AsGeoJSON(path) AS path_geojson
            FROM routes
            WHERE key_route = %s
            """,
            (route_id,),
        )
        row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Route not found")

    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(
            """
            SELECT key_step, container_id, step_order, collected, collected_at, volume_collected_l
            FROM route_steps
            WHERE route_id = %s
            ORDER BY step_order
            """,
            (route_id,),
        )
        step_rows = cur.fetchall()

    return RouteDetail(
        key_route=row["key_route"],
        zone_id=row["zone_id"],
        team_id=row["team_id"],
        name=row["name"],
        status=row["status"],
        scheduled_at=row["scheduled_at"],
        started_at=row["started_at"],
        completed_at=row["completed_at"],
        distance_m=float(row["distance_m"]) if row["distance_m"] is not None else None,
        path=json.loads(row["path_geojson"]) if row["path_geojson"] else None,
        steps=[RouteStep(**dict(s)) for s in step_rows],
    )


# ── Static routes (must be declared before /{route_id}) ──────────────────────

@router.get("/stats", response_model=RouteStats)
def get_route_stats(
    from_dt: Optional[date] = Query(None, alias="from"),
    to_dt:   Optional[date] = Query(None, alias="to"),
    conn=Depends(get_db),
):
    """Global route KPIs over a date range (default: last 30 days)."""
    if from_dt is None:
        from_dt = date.today() - timedelta(days=30)
    if to_dt is None:
        to_dt = date.today()

    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(
            """
            SELECT
                COUNT(DISTINCT r.key_route)                                                AS total_routes,
                COALESCE(SUM(r.distance_m) / 1000.0, 0)                                   AS total_distance_km,
                COUNT(c.key_collection)                                                    AS total_collections,
                COALESCE(
                    COUNT(c.key_collection)::float / NULLIF(COUNT(DISTINCT r.key_route), 0),
                    0
                )                                                                          AS avg_containers_per_route,
                COUNT(*) FILTER (
                    WHERE c.fill_rate_before IS NOT NULL
                      AND ct.fill_threshold_pct IS NOT NULL
                      AND c.fill_rate_before > ct.fill_threshold_pct
                )                                                                          AS overflows_avoided
            FROM routes r
            LEFT JOIN collections c  ON c.route_id = r.key_route
            LEFT JOIN containers ct  ON ct.key_container = c.container_id
            WHERE r.scheduled_at BETWEEN %(from_dt)s AND %(to_dt)s
            """,
            {"from_dt": from_dt, "to_dt": to_dt},
        )
        r = cur.fetchone()

    return RouteStats(
        total_routes=r["total_routes"],
        total_distance_km=float(r["total_distance_km"] or 0),
        total_collections=r["total_collections"],
        avg_containers_per_route=round(float(r["avg_containers_per_route"] or 0), 1),
        overflows_avoided=r["overflows_avoided"],
    )


# ── Collection ────────────────────────────────────────────────────────────────

@router.get("", response_model=PaginatedResponse[RouteOut])
def list_routes(
    zone_id:   Optional[int]  = Query(None),
    team_id:   Optional[int]  = Query(None),
    status:    Optional[str]  = Query(None, pattern="^(planifiee|en_cours|terminee|annulee)$"),
    date_from: Optional[date] = Query(None),
    date_to:   Optional[date] = Query(None),
    page:      int            = Query(1, ge=1),
    per_page:  int            = Query(20, ge=1, le=100),
    conn=Depends(get_db),
):
    where: list[str] = []
    params: dict[str, Any] = {}

    if zone_id is not None:
        where.append("r.zone_id = %(zone_id)s")
        params["zone_id"] = zone_id
    if team_id is not None:
        where.append("r.team_id = %(team_id)s")
        params["team_id"] = team_id
    if status is not None:
        where.append("r.status = %(status)s")
        params["status"] = status
    if date_from is not None:
        where.append("r.scheduled_at >= %(date_from)s")
        params["date_from"] = date_from
    if date_to is not None:
        where.append("r.scheduled_at <= %(date_to)s")
        params["date_to"] = date_to

    where_sql = ("WHERE " + " AND ".join(where)) if where else ""

    with conn.cursor() as cur:
        cur.execute(f"SELECT COUNT(*) FROM routes r {where_sql}", params)
        total = cur.fetchone()[0]

    offset = (page - 1) * per_page
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(
            f"""
            SELECT
                key_route, zone_id, team_id, name, status,
                scheduled_at, started_at, completed_at, distance_m
            FROM routes r
            {where_sql}
            ORDER BY r.scheduled_at DESC, r.key_route
            LIMIT %(limit)s OFFSET %(offset)s
            """,
            {**params, "limit": per_page, "offset": offset},
        )
        rows = cur.fetchall()

    return PaginatedResponse(
        page=page, per_page=per_page, total=total,
        items=[
            RouteOut(
                key_route=r["key_route"],
                zone_id=r["zone_id"],
                team_id=r["team_id"],
                name=r["name"],
                status=r["status"],
                scheduled_at=r["scheduled_at"],
                started_at=r["started_at"],
                completed_at=r["completed_at"],
                distance_m=float(r["distance_m"]) if r["distance_m"] is not None else None,
            )
            for r in rows
        ],
    )


# ── Single resource ───────────────────────────────────────────────────────────

@router.get("/{route_id}", response_model=RouteDetail)
def get_route(route_id: int, conn=Depends(get_db)):
    return _fetch_route_or_404(conn, route_id)


@router.post("/{route_id}/export")
def export_route(
    route_id: int,
    fmt: str = Query("pdf", alias="format", pattern="^(pdf|json)$"),
    conn=Depends(get_db),
):
    """Route sheet for field agents — PDF or JSON."""
    route = _fetch_route_or_404(conn, route_id)

    if fmt == "json":
        return route

    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    except ImportError:
        raise HTTPException(
            status_code=503,
            detail="PDF generation requires reportlab — uncomment it in requirements.txt",
        )

    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph(f"Route: {route.name or route.key_route}", styles["Title"]))
    story.append(Paragraph(f"Date: {route.scheduled_at or '—'}", styles["Normal"]))
    story.append(Paragraph(f"Status: {route.status}", styles["Normal"]))
    if route.distance_m is not None:
        story.append(Paragraph(f"Distance: {route.distance_m / 1000:.2f} km", styles["Normal"]))
    story.append(Spacer(1, 12))

    if route.steps:
        table_data = [["#", "Container", "Collected", "Volume (L)", "Collected at"]]
        for s in route.steps:
            table_data.append([
                str(s.step_order),
                str(s.container_id),
                "Yes" if s.collected else "No",
                f"{s.volume_collected_l:.1f}" if s.volume_collected_l is not None else "—",
                s.collected_at.strftime("%H:%M") if s.collected_at else "—",
            ])
        t = Table(table_data, hAlign="LEFT")
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4a4a4a")),
            ("TEXTCOLOR",  (0, 0), (-1, 0), colors.whitesmoke),
            ("GRID",       (0, 0), (-1, -1), 0.5, colors.black),
            ("FONTSIZE",   (0, 0), (-1, -1), 9),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f5f5")]),
        ]))
        story.append(t)

    doc.build(story)
    buf.seek(0)
    filename = f"route_{route_id}_{route.scheduled_at or 'undated'}.pdf"
    return Response(
        content=buf.read(),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
