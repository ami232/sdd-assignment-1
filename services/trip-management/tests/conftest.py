"""Shared database setup for tests."""

import os
import tempfile

# app.py creates its tables on import. Point it at a throwaway folder before
# any test module imports it, so tests never create ./data in the repo.
os.environ.setdefault("DATA_DIR", tempfile.mkdtemp())

import pytest  # noqa: E402

import db  # noqa: E402


@pytest.fixture
def test_db(tmp_path, monkeypatch):
    """Provide a fresh SQLite connection for each test."""

    db_path = tmp_path / "test.db"

    monkeypatch.setattr(db, "DB_PATH", str(db_path))
    monkeypatch.setattr(db, "DATA_DIR", str(tmp_path))

    db.init_db()

    conn = db.get_connection()

    try:
        yield conn
    finally:
        conn.close()


@pytest.fixture(autouse=True)
def no_cancellation_listeners(monkeypatch):
    """Start every test with no listeners.

    app.py subscribes a listener that calls Room Allocation over HTTP, so
    without this a cancellation in any test would try to reach the network.
    """
    import trip_management

    monkeypatch.setattr(trip_management, "_cancellation_listeners", [])
