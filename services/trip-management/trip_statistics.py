"""Registration statistics for the Ski Club dashboard."""

from db import get_connection


def get_trip_statistics(trip_id):
    """Calculate registration statistics for one trip.

    Room counts are not here: rooms live in the Room Allocation service,
    so the UI combines these numbers with that service's room summary.

    Read-only: an unpaid reservation past its deadline is still counted
    until the next registration change for the trip releases it.
    """
    conn = get_connection()

    try:
        trip = conn.execute(
            "SELECT capacity FROM trips WHERE id = ?",
            (trip_id,)
        ).fetchone()

        if trip is None:
            raise ValueError("Trip not found")

        confirmed = conn.execute(
            """
            SELECT COUNT(*) FROM registrations
            WHERE trip_id = ? AND status = 'confirmed'
            """,
            (trip_id,)
        ).fetchone()[0]

        # Reserved but not yet paid. These still hold a place on the trip.
        pending = conn.execute(
            """
            SELECT COUNT(*) FROM registrations
            WHERE trip_id = ? AND status = 'pending_payment'
            """,
            (trip_id,)
        ).fetchone()[0]

        waitlisted = conn.execute(
            """
            SELECT COUNT(*) FROM registrations
            WHERE trip_id = ? AND status = 'waitlisted'
            """,
            (trip_id,)
        ).fetchone()[0]

        capacity = trip["capacity"]
        taken = confirmed + pending

        return {
            "capacity": capacity,
            "confirmed": confirmed,
            "pending_payment": pending,
            "waitlisted": waitlisted,
            "places_remaining": max(0, capacity - taken),
            "occupancy_percent": round(taken / capacity * 100, 1)
        }

    finally:
        conn.close()
