"""Migration 002 and the status_changed_at column it adds."""

from datetime import datetime, timedelta, timezone

import db
import trip_management
from trip_management import cancel_registration, confirm_payment, create_trip, register_student


def test_migration_002_kept_existing_rows_and_filled_the_new_column(test_db):
    """Replays 002 on a copy of registrations that only has 001's columns."""
    test_db.execute("INSERT INTO trips (name, destination, start_date, end_date, capacity)"
                    " VALUES ('Alps', 'Tignes', '2027-01-15', '2027-01-20', 5)")
    test_db.execute(
        "SELECT id, trip_id, name, email, status, registered_at, payment_deadline"
        " INTO registrations_before_002 FROM registrations WHERE 1 = 0"
    )
    test_db.execute(
        "INSERT INTO registrations_before_002 (trip_id, name, email, status, registered_at)"
        " VALUES (1, 'Ana', 'ana@example.com', 'confirmed', '2026-11-01T10:00:00')"
    )
    with open(f"{db.MIGRATIONS_DIR}/002_add_status_changed_at.sql") as migration:
        sql = migration.read().replace("registrations", "registrations_before_002")
    sql = sql.replace("df_registrations_before_002_status_changed_at", "df_test_002")
    try:
        test_db.execute(sql)
        row = test_db.execute("SELECT name, status, status_changed_at FROM registrations_before_002").fetchone()
        assert row["name"] == "Ana"
        assert row["status"] == "confirmed"
        assert row["status_changed_at"].startswith("2026-11-01T10:00:00")
    finally:
        test_db.rollback()


def test_every_status_change_updates_status_changed_at(monkeypatch, test_db):
    start = datetime(2026, 11, 1, 10, 0, tzinfo=timezone.utc)
    monkeypatch.setattr(trip_management, "_now", lambda: start)
    trip_id = create_trip("Alps", "Tignes", "2027-01-15", "2027-01-20", 5)
    registration_id = register_student(trip_id, "Ana", "ana@example.com")

    def changed_at():
        return test_db.execute(
            "SELECT status_changed_at FROM registrations WHERE id = ?", (registration_id,)
        ).fetchone()["status_changed_at"]

    assert changed_at().startswith("2026-11-01T10:00:00")

    monkeypatch.setattr(trip_management, "_now", lambda: start + timedelta(hours=1))
    confirm_payment(registration_id)
    test_db.commit()
    assert changed_at().startswith("2026-11-01T11:00:00")

    monkeypatch.setattr(trip_management, "_now", lambda: start + timedelta(hours=2))
    cancel_registration(registration_id)
    test_db.commit()
    assert changed_at().startswith("2026-11-01T12:00:00")
