"""Shared test setup: a fresh database and a fake Trip Management service."""

import os
import tempfile

# app.py creates its tables on import. Point it at a throwaway folder before
# any test module imports it, so tests never create ./data in the repo.
os.environ.setdefault("DATA_DIR", tempfile.mkdtemp())

import pytest  # noqa: E402

import db  # noqa: E402
import room_allocation  # noqa: E402


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


class FakeTripManagement:
    """Stands in for the Trip Management service in tests.

    Holds trips and registrations in memory and answers the same paths the
    real service does, so the adapter code runs unchanged.
    """

    def __init__(self):
        self.trips = set()
        self.registrations = {}

    def add_trip(self):
        trip_id = len(self.trips) + 1
        self.trips.add(trip_id)
        return trip_id

    def add_student(self, trip_id, status="confirmed"):
        registration_id = len(self.registrations) + 1
        self.registrations[registration_id] = {
            "id": registration_id, "trip_id": trip_id, "status": status,
        }
        return registration_id

    def get_json(self, path):
        kind, _, item_id = path.strip("/").partition("/")
        item_id = int(item_id)
        if kind == "trips":
            return {"id": item_id} if item_id in self.trips else None
        return self.registrations.get(item_id)


@pytest.fixture
def trips(monkeypatch):
    """Replace HTTP calls to Trip Management with an in-memory fake."""
    fake = FakeTripManagement()
    monkeypatch.setattr(room_allocation, "_get_json", fake.get_json)
    return fake
