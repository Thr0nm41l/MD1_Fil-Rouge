import json
from datetime import datetime

import psycopg2.extras
from fastapi import APIRouter, Depends, Query

from db import get_db, set_user_context
from schemas.dashboard import DashboardConfig, DashboardConfigUpdate

router = APIRouter()


@router.get("/config", response_model=DashboardConfig)
def get_dashboard_config(
    user_id: int = Query(..., description="Authenticated user ID"),
    conn=Depends(get_db),
):
    """Returns the saved layout config for the user. Returns empty layout if none saved yet."""
    set_user_context(conn, user_id)
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(
            "SELECT user_id, layout_config, updated_at FROM dashboard_config WHERE user_id = %s",
            (user_id,),
        )
        row = cur.fetchone()

    if not row:
        return DashboardConfig(
            user_id=user_id,
            layout_config={},
            updated_at=datetime.utcnow(),
        )
    return DashboardConfig(
        user_id=row["user_id"],
        layout_config=row["layout_config"],
        updated_at=row["updated_at"],
    )


@router.put("/config", response_model=DashboardConfig)
def upsert_dashboard_config(
    body: DashboardConfigUpdate,
    user_id: int = Query(..., description="Authenticated user ID"),
    conn=Depends(get_db),
):
    """Saves or updates the user's dashboard layout (upsert on user_id unique constraint)."""
    set_user_context(conn, user_id)
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(
            """
            INSERT INTO dashboard_config (user_id, layout_config, updated_at)
            VALUES (%(user_id)s, %(layout_config)s, NOW())
            ON CONFLICT (user_id) DO UPDATE
                SET layout_config = EXCLUDED.layout_config,
                    updated_at    = NOW()
            RETURNING user_id, layout_config, updated_at
            """,
            {
                "user_id":       user_id,
                "layout_config": json.dumps(body.layout_config),
            },
        )
        row = cur.fetchone()
    return DashboardConfig(
        user_id=row["user_id"],
        layout_config=row["layout_config"],
        updated_at=row["updated_at"],
    )
