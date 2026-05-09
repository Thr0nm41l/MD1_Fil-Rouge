import re
from datetime import date, datetime, timedelta
from typing import List, Optional

import psycopg2
import psycopg2.extras
from fastapi import APIRouter, Depends, HTTPException, Query

from db import get_db
from schemas.gamification import (
    DefiOut,
    EarnedBadge,
    LeaderboardEntry,
    NextBadge,
    UserBadgesResponse,
    UserImpact,
)

router = APIRouter()

_CO2_PER_COLLECTION   = 0.27   # kg — ~1 km avoided per collection × 0.27 kg CO₂/km
_CO2_PER_SIGNALEMENT  = 0.135  # kg — ~0.5 km avoided per early report


def _call_leaderboard(conn, p_from: Optional[datetime], p_to: Optional[datetime]) -> List[LeaderboardEntry]:
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(
            "SELECT rank, user_id, name, first_name, total_points FROM get_leaderboard(100, %s, %s)",
            (p_from, p_to),
        )
        rows = cur.fetchall()
    return [
        LeaderboardEntry(
            rank=r["rank"],
            user_id=r["user_id"],
            name=r["name"],
            first_name=r["first_name"],
            total_points=r["total_points"],
        )
        for r in rows
    ]


# ── Leaderboard (static sub-paths first) ─────────────────────────────────────

@router.get("/leaderboard/weekly", response_model=List[LeaderboardEntry])
def get_leaderboard_weekly(conn=Depends(get_db)):
    """Top 100 ranked by points earned in the current ISO week."""
    today = date.today()
    week_start = datetime.combine(today - timedelta(days=today.weekday()), datetime.min.time())
    return _call_leaderboard(conn, week_start, None)


@router.get("/leaderboard/monthly", response_model=List[LeaderboardEntry])
def get_leaderboard_monthly(conn=Depends(get_db)):
    """Top 100 ranked by points earned in the current calendar month."""
    month_start = datetime.combine(date.today().replace(day=1), datetime.min.time())
    return _call_leaderboard(conn, month_start, None)


@router.get("/leaderboard", response_model=List[LeaderboardEntry])
def get_leaderboard(conn=Depends(get_db)):
    """Top 100 citizens ranked by cumulative all-time points."""
    return _call_leaderboard(conn, None, None)


# ── Users ─────────────────────────────────────────────────────────────────────

@router.get("/users/{user_id}/badges", response_model=UserBadgesResponse)
def get_user_badges(user_id: int, conn=Depends(get_db)):
    """Earned badges + first unearned badge per category with progress."""
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(
            """
            SELECT ub.badge_id, b.name, b.category, ub.earned_at
            FROM user_badges ub
            JOIN badges b ON b.key_badge = ub.badge_id
            WHERE ub.user_id = %s
            ORDER BY ub.earned_at DESC
            """,
            (user_id,),
        )
        earned_rows = cur.fetchall()
    earned_ids = [r["badge_id"] for r in earned_rows]

    # Count actions per category for progress computation
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM signalements WHERE user_id = %s", (user_id,))
        sig_count = cur.fetchone()[0]
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM collections WHERE agent_id = %s", (user_id,))
        col_count = cur.fetchone()[0]
    with conn.cursor() as cur:
        cur.execute("SELECT COALESCE(SUM(points), 0) FROM user_points WHERE user_id = %s", (user_id,))
        total_pts = int(cur.fetchone()[0])

    progress_by_category = {
        "signalement": sig_count,
        "collecte":    col_count,
        "streak":      total_pts,
        "zone":        total_pts,
        "defi":        total_pts,
        "special":     total_pts,
    }

    # First unearned badge in each category, sorted by difficulty (points_value ASC)
    exclude = earned_ids if earned_ids else [0]
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(
            """
            SELECT DISTINCT ON (category) key_badge, name, category, condition_sql
            FROM badges
            WHERE key_badge != ALL(%s)
            ORDER BY category, points_value ASC
            """,
            (exclude,),
        )
        next_rows = cur.fetchall()

    def _target(condition_sql: Optional[str]) -> int:
        if condition_sql:
            m = re.search(r'>=\s*(\d+)', condition_sql)
            if m:
                return int(m.group(1))
        return 1

    return UserBadgesResponse(
        earned=[EarnedBadge(**dict(r)) for r in earned_rows],
        next=[
            NextBadge(
                badge_id=r["key_badge"],
                name=r["name"],
                category=r["category"],
                target=_target(r["condition_sql"]),
                current_progress=progress_by_category.get(r["category"], 0),
            )
            for r in next_rows
        ],
    )


@router.get("/users/{user_id}/impact", response_model=UserImpact)
def get_user_impact(user_id: int, conn=Depends(get_db)):
    """Environmental impact summary for one citizen."""
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(
            """
            SELECT COALESCE(SUM(points), 0) AS total_points, MIN(earned_at) AS since
            FROM user_points
            WHERE user_id = %s
            """,
            (user_id,),
        )
        pts = cur.fetchone()

    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM signalements WHERE user_id = %s", (user_id,))
        sig_count = cur.fetchone()[0]
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM collections WHERE agent_id = %s", (user_id,))
        col_count = cur.fetchone()[0]

    co2 = round(col_count * _CO2_PER_COLLECTION + sig_count * _CO2_PER_SIGNALEMENT, 1)

    return UserImpact(
        user_id=user_id,
        total_points=int(pts["total_points"]),
        signalement_count=sig_count,
        collection_count=col_count,
        co2_saved_kg=co2,
        since=pts["since"],
    )


# ── Défis ─────────────────────────────────────────────────────────────────────

@router.get("/defis", response_model=List[DefiOut])
def list_defis(conn=Depends(get_db)):
    """Active challenges with real-time collective progress."""
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(
            """
            SELECT
                d.key_defi, d.title, d.type, d.target_value, d.reward_points, d.ends_at,
                COUNT(DISTINCT dp.user_id)    AS participant_count,
                COALESCE(SUM(dp.progress), 0) AS collective_progress
            FROM defis d
            LEFT JOIN defi_participations dp ON dp.defi_id = d.key_defi
            WHERE d.is_active = true
              AND (d.ends_at IS NULL OR d.ends_at > NOW())
            GROUP BY d.key_defi, d.title, d.type, d.target_value, d.reward_points, d.ends_at
            ORDER BY d.key_defi
            """
        )
        rows = cur.fetchall()

    return [
        DefiOut(
            key_defi=r["key_defi"],
            title=r["title"],
            type=r["type"],
            target_value=r["target_value"],
            reward_points=r["reward_points"],
            ends_at=r["ends_at"],
            participant_count=r["participant_count"],
            collective_progress=int(r["collective_progress"]),
            progress_pct=round(int(r["collective_progress"]) / max(r["target_value"], 1) * 100, 1),
        )
        for r in rows
    ]


@router.post("/defis/{defi_id}/join", status_code=201)
def join_defi(
    defi_id: int,
    user_id: int = Query(..., description="Authenticated user ID"),
    conn=Depends(get_db),
):
    """Register the authenticated user in a challenge. 409 if already joined."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT 1 FROM defis WHERE key_defi = %s AND is_active = true"
            " AND (ends_at IS NULL OR ends_at > NOW())",
            (defi_id,),
        )
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Défi not found or no longer active")

    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO defi_participations (defi_id, user_id) VALUES (%s, %s)",
                (defi_id, user_id),
            )
    except psycopg2.errors.UniqueViolation:
        conn.rollback()
        raise HTTPException(status_code=409, detail="Already registered in this défi")

    return {"joined": True, "defi_id": defi_id}
