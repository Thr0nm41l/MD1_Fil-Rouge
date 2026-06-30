"""
Shared fixtures for the ECOTRACK API test suite.

Two test modes:
  - Unit tests    : use the `client` fixture with a mock DB connection.
                    Run always, no infrastructure required.
  - Integration   : marked @pytest.mark.integration, use `int_client` fixture
                    with a real PostgreSQL connection.
                    Require a running DB and env vars (POSTGRES_HOST, etc.).
                    Skip automatically if the DB is unreachable.

Run unit tests only:
    pytest apiservice/tests/ -m "not integration"

Run all tests (requires port-forward to PostgreSQL):
    kubectl port-forward svc/postgres-postgresql 5432:5432 -n datalake
    pytest apiservice/tests/
"""

import os
import sys
from unittest.mock import MagicMock, patch

import psycopg2
import pytest
from fastapi.testclient import TestClient

# ── Path setup — allow imports from apiservice/ ──────────────────────────────
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from db import get_db
from main import app


# ── Pytest marks ─────────────────────────────────────────────────────────────

def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "integration: mark test as requiring a live PostgreSQL connection",
    )


# ── Unit test client (mock DB) ────────────────────────────────────────────────

@pytest.fixture(scope="session")
def mock_conn():
    """Minimal psycopg2 connection mock — enough to satisfy get_db callers."""
    conn = MagicMock()
    cursor = MagicMock()
    cursor.__enter__ = lambda s: s
    cursor.__exit__ = MagicMock(return_value=False)
    conn.cursor.return_value = cursor
    return conn


@pytest.fixture(scope="session")
def client(mock_conn):
    """TestClient with DB dependency overridden by a mock — no DB required."""
    app.dependency_overrides[get_db] = lambda: mock_conn
    with patch("main.init_pool"), patch("main.close_pool"):
        with TestClient(app, raise_server_exceptions=False) as c:
            yield c
    app.dependency_overrides.clear()


# ── Integration test client (real DB) ────────────────────────────────────────

def _db_available() -> bool:
    try:
        conn = psycopg2.connect(
            host=os.environ.get("POSTGRES_HOST", "localhost"),
            port=int(os.environ.get("POSTGRES_PORT", 5432)),
            database=os.environ.get("POSTGRES_DB", "Ecotrack"),
            user=os.environ.get("POSTGRES_USER", "postgres"),
            password=os.environ.get("POSTGRES_PASSWORD", ""),
            connect_timeout=3,
        )
        conn.close()
        return True
    except Exception:
        return False


@pytest.fixture(scope="session")
def db_conn():
    """Real psycopg2 connection — skips the test session if DB is unreachable."""
    if not _db_available():
        pytest.skip("PostgreSQL unreachable — start port-forward and set env vars")
    conn = psycopg2.connect(
        host=os.environ.get("POSTGRES_HOST", "localhost"),
        port=int(os.environ.get("POSTGRES_PORT", 5432)),
        database=os.environ.get("POSTGRES_DB", "Ecotrack"),
        user=os.environ.get("POSTGRES_USER", "postgres"),
        password=os.environ.get("POSTGRES_PASSWORD", ""),
    )
    yield conn
    conn.close()


@pytest.fixture(scope="session")
def int_client(db_conn):
    """TestClient wired to the real PostgreSQL — for integration tests."""
    app.dependency_overrides[get_db] = lambda: db_conn
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
