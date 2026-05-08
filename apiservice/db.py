import os
from contextlib import contextmanager
from typing import Generator

import psycopg2
import psycopg2.pool

_pool: psycopg2.pool.ThreadedConnectionPool | None = None


def init_pool() -> None:
    global _pool
    _pool = psycopg2.pool.ThreadedConnectionPool(
        minconn=2,
        maxconn=10,
        host=os.environ["POSTGRES_HOST"],
        database=os.environ["POSTGRES_DB"],
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
        port=int(os.environ.get("POSTGRES_PORT", 5432)),
    )


def close_pool() -> None:
    global _pool
    if _pool:
        _pool.closeall()
        _pool = None


@contextmanager
def get_conn() -> Generator:
    conn = _pool.getconn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        _pool.putconn(conn)


def get_db():
    """FastAPI dependency: yields a pooled connection, commits on success."""
    with get_conn() as conn:
        yield conn


def set_user_context(conn, user_id: int) -> None:
    """Set app.user_id for the current transaction — required by RLS policies."""
    with conn.cursor() as cur:
        cur.execute("SET LOCAL app.user_id = %s", (str(user_id),))
