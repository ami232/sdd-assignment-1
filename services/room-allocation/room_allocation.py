
"""Room Allocation domain: rooms, assignments and roommate preferences.

Facade: create_room, assign_student, remove_assignment,
add_roommate_preference, get_rooms, get_assignments, get_preferences,
get_student_room, check_room_on_trip and release_student are this domain's public interface, and become the
endpoints of the Room Allocation service.
"""

import json
import sqlite3
import urllib.error
import urllib.request

import config
from db import get_connection


# Adapter: the functions below are the only code in Room Allocation that
# knows about Trip Management. They ask the Trip Management service over
# HTTP and turn its answers into the simple values this domain needs (does
# the trip exist, which trip and status does a registration have). In the
# monolith they queried Trip Management's tables directly; only these
# functions changed when the domains became separate services.

def _get_json(path):
    """GET a path from Trip Management. None on 404, ValueError if unreachable."""
    try:
        with urllib.request.urlopen(config.TRIPS_URL + path, timeout=5) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        if error.code == 404:
            return None
        raise ValueError("Trip Management is unavailable") from error
    except urllib.error.URLError as error:
        raise ValueError("Trip Management is unavailable") from error


def _trip_exists(trip_id):
    """Adapter: True if Trip Management has a trip with this ID."""
    return _get_json(f"/trips/{trip_id}") is not None


def _get_registration(registration_id):
    """Adapter: a registration as {"trip_id", "status"}, or None."""
    data = _get_json(f"/registrations/{registration_id}")

    if data is None:
        return None
    return {"trip_id": data["trip_id"], "status": data["status"]}


def create_room(trip_id, name, capacity):
    """Create a room for an existing trip and return its ID."""
    if not isinstance(name, str) or not name.strip():
        raise ValueError("Room name cannot be empty")

    if type(capacity) is not int or not 1 <= capacity <= 6:
        raise ValueError("Room capacity must be between 1 and 6")

    # Ask Trip Management before opening the transaction, so the write lock
    # is never held while waiting on the network.
    if not _trip_exists(trip_id):
        raise ValueError("Trip not found")

    conn = get_connection()
    try:
        conn.execute("BEGIN IMMEDIATE")

        cursor = conn.execute(
            "INSERT INTO rooms (trip_id, name, capacity) VALUES (?, ?, ?)",
            (trip_id, name.strip(), capacity)
        )
        conn.commit()
        return cursor.lastrowid

    except sqlite3.IntegrityError as error:
        conn.rollback()
        raise ValueError("A room with this name already exists") from error
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def assign_student(room_id, registration_id):
    """Assign a confirmed student to a room on the same trip."""
    # Ask Trip Management before opening the transaction, so the write lock
    # is never held while waiting on the network.
    student = _get_registration(registration_id)

    conn = get_connection()
    try:
        conn.execute("BEGIN IMMEDIATE")

        room = conn.execute(
            "SELECT trip_id, capacity FROM rooms WHERE id = ?",
            (room_id,)
        ).fetchone()

        if room is None:
            raise ValueError("Room not found")

        if student is None:
            raise ValueError("Registration not found")

        if student["status"] != "confirmed":
            raise ValueError("Only confirmed students can receive rooms")

        if student["trip_id"] != room["trip_id"]:
            raise ValueError("Student and room belong to different trips")

        occupied = conn.execute(
            "SELECT COUNT(*) FROM room_assignments WHERE room_id = ?",
            (room_id,)
        ).fetchone()[0]

        if occupied >= room["capacity"]:
            raise ValueError("Room is full")

        cursor = conn.execute(
            """
            INSERT INTO room_assignments (room_id, registration_id)
            VALUES (?, ?)
            """,
            (room_id, registration_id)
        )

        conn.commit()
        return cursor.lastrowid

    except sqlite3.IntegrityError as error:
        conn.rollback()
        raise ValueError("Student already has a room") from error
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def remove_assignment(registration_id):
    """Remove a student's room assignment, if one exists."""
    conn = get_connection()
    try:
        cursor = conn.execute(
            "DELETE FROM room_assignments WHERE registration_id = ?",
            (registration_id,)
        )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def add_roommate_preference(registration_id, preferred_registration_id):
    """Record that one confirmed student wants to share with another."""
    if registration_id == preferred_registration_id:
        raise ValueError("A student cannot request themselves")

    # Ask Trip Management first; nothing here needs the write lock.
    student = _get_registration(registration_id)
    preferred = _get_registration(preferred_registration_id)

    if student is None or preferred is None:
        raise ValueError("Both registrations must exist")

    if student["status"] != "confirmed" or preferred["status"] != "confirmed":
        raise ValueError("Both students must be confirmed")

    if student["trip_id"] != preferred["trip_id"]:
        raise ValueError("Students must be on the same trip")

    conn = get_connection()
    try:
        conn.execute("BEGIN IMMEDIATE")

        cursor = conn.execute(
            """
            INSERT INTO roommate_preferences
                (trip_id, registration_id, preferred_registration_id)
            VALUES (?, ?, ?)
            """,
            (student["trip_id"], registration_id, preferred_registration_id)
        )
        conn.commit()
        return cursor.lastrowid

    except sqlite3.IntegrityError as error:
        conn.rollback()
        raise ValueError("Roommate preference already exists") from error
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def get_rooms(trip_id):
    """Return rooms for a trip with their current occupancy."""
    if not _trip_exists(trip_id):
        raise ValueError("Trip not found")

    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT rooms.id, rooms.name, rooms.capacity,
                   COUNT(room_assignments.id) AS occupied
            FROM rooms
            LEFT JOIN room_assignments
                ON room_assignments.room_id = rooms.id
            WHERE rooms.trip_id = ?
            GROUP BY rooms.id
            ORDER BY rooms.id
            """,
            (trip_id,)
        ).fetchall()

        return [dict(row) for row in rows]
    finally:
        conn.close()


def get_assignments(trip_id):
    """Return who sleeps where on a trip, as registration and room IDs."""
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT a.registration_id, rooms.id AS room_id, rooms.name AS room_name
            FROM room_assignments AS a
            JOIN rooms ON rooms.id = a.room_id
            WHERE rooms.trip_id = ?
            ORDER BY a.id
            """,
            (trip_id,)
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def get_preferences(trip_id):
    """Return a trip's roommate requests as pairs of registration IDs."""
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT registration_id, preferred_registration_id
            FROM roommate_preferences
            WHERE trip_id = ?
            ORDER BY id
            """,
            (trip_id,)
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def get_student_room(registration_id):
    """Return the room a student sleeps in and how full it is, or None."""
    conn = get_connection()
    try:
        row = conn.execute(
            """
            SELECT rooms.name, rooms.capacity,
                   (SELECT COUNT(*) FROM room_assignments
                    WHERE room_id = rooms.id) AS occupied
            FROM room_assignments AS a
            JOIN rooms ON rooms.id = a.room_id
            WHERE a.registration_id = ?
            """,
            (registration_id,)
        ).fetchone()
        return None if row is None else dict(row)
    finally:
        conn.close()


def check_room_on_trip(trip_id, room_id):
    """Raise ValueError unless the room belongs to this trip."""
    conn = get_connection()
    try:
        room = conn.execute(
            "SELECT trip_id FROM rooms WHERE id = ?", (room_id,)
        ).fetchone()

        if room is None or room["trip_id"] != trip_id:
            raise ValueError("Room not found on this trip")
    finally:
        conn.close()


def release_student(registration_id):
    """Free a cancelled student's bed and drop their roommate preferences.

    In the monolith this was an observer running inside Trip Management's
    cancellation transaction. Across two services that shared transaction
    no longer exists, so Trip Management will call this through an endpoint
    after a cancellation. Running it twice is harmless.
    """
    conn = get_connection()
    try:
        conn.execute(
            "DELETE FROM room_assignments WHERE registration_id = ?",
            (registration_id,)
        )

        # Remove requests made by the student and requests naming them, so no
        # one keeps asking to share with someone who is no longer coming.
        conn.execute(
            """
            DELETE FROM roommate_preferences
            WHERE registration_id = ? OR preferred_registration_id = ?
            """,
            (registration_id, registration_id)
        )
        conn.commit()
    finally:
        conn.close()
