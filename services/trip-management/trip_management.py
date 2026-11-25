"""Trip Management domain: trips, registrations, payments and the waitlist.

Facade: the public functions below (create_trip, register_student,
confirm_payment, cancel_registration, check_registration_on_trip,
get_trip, get_registration and on_registration_cancelled) are the only way the rest of the app changes
this domain. Callers never see the SQL, the transactions or the expiry
rules. app.py exposes them as the endpoints of the Trip Management service.
"""
import sqlite3
from datetime import date, datetime, timedelta, timezone

from db import get_connection

# How long a student has to pay before their reserved place is released.
PAYMENT_WINDOW = timedelta(hours=48)

# Observer: functions that want to know when a registration is cancelled.
# Trip Management calls them without knowing what they do, so it never
# writes to another domain's tables. In the monolith Room Allocation
# subscribed here directly; now that it is a separate service, the listener
# will be one that tells Room Allocation over HTTP to free the bed.
_cancellation_listeners = []


def on_registration_cancelled(listener):
    """Subscribe listener(conn, registration_id) to cancellations.

    The listener runs inside the cancellation's transaction, so if it fails
    the whole cancellation is rolled back.
    """
    if listener not in _cancellation_listeners:
        _cancellation_listeners.append(listener)


def _now():
    """Current UTC time. Tests replace this to move the clock forward."""
    return datetime.now(timezone.utc)


def create_trip(name, destination, start_date, end_date, capacity):
    """Create a new ski trip and return its ID."""

    # Check that the trip has a name and destination.
    if not isinstance(name, str) or not name.strip():
        raise ValueError("Trip name cannot be empty")

    if not isinstance(destination, str) or not destination.strip():
        raise ValueError("Destination cannot be empty")

    # Make sure the dates are valid and in the correct order.
    try:
        start = date.fromisoformat(start_date)
        end = date.fromisoformat(end_date)
    except (ValueError, TypeError):
        raise ValueError("Dates must use YYYY-MM-DD format")

    if end < start:
        raise ValueError("End date cannot be before start date")

    # Capacity must be a positive whole number.
    if type(capacity) is not int or capacity <= 0:
        raise ValueError("Capacity must be a positive integer")

    # Save the trip in the database.
    conn = get_connection()

    try:
        cursor = conn.execute(
            """
            INSERT INTO trips
            (name, destination, start_date, end_date, capacity)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                name.strip(),
                destination.strip(),
                start.isoformat(),
                end.isoformat(),
                capacity
            )
        )

        conn.commit()
        return cursor.lastrowid

    finally:
        conn.close()


def _promote_waitlist(conn, trip_id, now):
    """Give free places to the longest-waiting students, oldest first."""

    capacity = conn.execute(
        "SELECT capacity FROM trips WHERE id = ?",
        (trip_id,)
    ).fetchone()["capacity"]

    occupied = conn.execute(
        """
        SELECT COUNT(*)
        FROM registrations
        WHERE trip_id = ?
          AND status IN ('pending_payment', 'confirmed')
        """,
        (trip_id,)
    ).fetchone()[0]

    free_places = capacity - occupied
    if free_places <= 0:
        return

    # id breaks ties if two students registered at the same moment.
    next_in_line = conn.execute(
        """
        SELECT id
        FROM registrations
        WHERE trip_id = ? AND status = 'waitlisted'
        ORDER BY registered_at, id
        LIMIT ?
        """,
        (trip_id, free_places)
    ).fetchall()

    # A promoted student gets a fresh payment window starting now.
    deadline = (now + PAYMENT_WINDOW).isoformat()
    for row in next_in_line:
        conn.execute(
            """
            UPDATE registrations
            SET status = 'pending_payment', payment_deadline = ?
            WHERE id = ?
            """,
            (deadline, row["id"])
        )


def _release_expired(conn, trip_id, now):
    """Cancel unpaid reservations past their deadline, then refill places.

    There is no background job (one process only), so this runs at the
    start of every registration change instead.
    """

    conn.execute(
        """
        UPDATE registrations
        SET status = 'cancelled'
        WHERE trip_id = ?
          AND status = 'pending_payment'
          AND payment_deadline < ?
        """,
        (trip_id, now.isoformat())
    )

    _promote_waitlist(conn, trip_id, now)


def register_student(trip_id, name, email):
    """Register a student or add them to the waiting list."""

    if not isinstance(name, str) or not name.strip():
        raise ValueError("Student name cannot be empty")

    if not isinstance(email, str) or not email.strip():
        raise ValueError("Email cannot be empty")

    name = name.strip()
    email = email.strip().lower()

    conn = get_connection()

    try:
        # Lock the database before checking capacity, so two students
        # cannot both take the last place.
        conn.execute("BEGIN IMMEDIATE")

        trip = conn.execute(
            "SELECT capacity FROM trips WHERE id = ?",
            (trip_id,)
        ).fetchone()

        if trip is None:
            raise ValueError("Trip not found")

        now = _now()
        _release_expired(conn, trip_id, now)

        occupied = conn.execute(
            """
            SELECT COUNT(*)
            FROM registrations
            WHERE trip_id = ?
              AND status IN ('pending_payment', 'confirmed')
            """,
            (trip_id,)
        ).fetchone()[0]

        # _release_expired has just filled any free places from the
        # waitlist, so a free place here means nobody is waiting for it.
        if occupied < trip["capacity"]:
            status = "pending_payment"
            payment_deadline = (now + PAYMENT_WINDOW).isoformat()
        else:
            status = "waitlisted"
            payment_deadline = None

        cursor = conn.execute(
            """
            INSERT INTO registrations
            (trip_id, name, email, status, registered_at, payment_deadline)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                trip_id,
                name,
                email,
                status,
                now.isoformat(),
                payment_deadline
            )
        )

        conn.commit()
        return cursor.lastrowid

    except sqlite3.IntegrityError as error:
        conn.rollback()
        raise ValueError("Student already registered for this trip") from error

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


def confirm_payment(registration_id):
    """Mark a reserved place as paid, if the deadline has not passed."""

    conn = get_connection()

    try:
        conn.execute("BEGIN IMMEDIATE")

        registration = conn.execute(
            "SELECT trip_id FROM registrations WHERE id = ?",
            (registration_id,)
        ).fetchone()

        if registration is None:
            raise ValueError("Registration not found")

        # Expire first, so a late payment finds its place already released.
        _release_expired(conn, registration["trip_id"], _now())

        status = conn.execute(
            "SELECT status FROM registrations WHERE id = ?",
            (registration_id,)
        ).fetchone()["status"]

        if status != "pending_payment":
            # Keep any expiries above even though this payment is refused.
            conn.commit()
            raise ValueError("Registration is not awaiting payment")

        conn.execute(
            """
            UPDATE registrations
            SET status = 'confirmed'
            WHERE id = ?
            """,
            (registration_id,)
        )

        conn.commit()

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()



def cancel_registration(registration_id):
    """Cancel a registration, notify listeners and update the waiting list."""

    conn = get_connection()

    try:
        conn.execute("BEGIN IMMEDIATE")

        registration = conn.execute(
            "SELECT trip_id, status FROM registrations WHERE id = ?",
            (registration_id,)
        ).fetchone()

        if registration is None:
            raise ValueError("Registration not found")

        if registration["status"] == "cancelled":
            raise ValueError("Registration is already cancelled")

        # Keep the registration row so its history stays visible.
        conn.execute(
            "UPDATE registrations SET status = 'cancelled' WHERE id = ?",
            (registration_id,)
        )

        # Tell the other domains (Room Allocation frees the bed).
        for listener in _cancellation_listeners:
            listener(conn, registration_id)

        # Release expired reservations and offer available places
        # to students on the waiting list, in FIFO order.
        _release_expired(conn, registration["trip_id"], _now())

        conn.commit()

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


def check_registration_on_trip(trip_id, registration_id):
    """Raise ValueError unless the registration belongs to this trip."""

    conn = get_connection()

    try:
        registration = conn.execute(
            "SELECT trip_id FROM registrations WHERE id = ?",
            (registration_id,)
        ).fetchone()

        if registration is None or registration["trip_id"] != trip_id:
            raise ValueError("Registration not found on this trip")

    finally:
        conn.close()


def get_trip(trip_id):
    """Return a trip as a dict, or None if it does not exist."""

    conn = get_connection()

    try:
        row = conn.execute(
            "SELECT * FROM trips WHERE id = ?", (trip_id,)
        ).fetchone()
        return None if row is None else dict(row)

    finally:
        conn.close()


def get_registration(registration_id):
    """Return a registration's id, trip_id and status, or None.

    This is what Room Allocation needs to decide who can get a room, so
    names and emails are not included.
    """

    conn = get_connection()

    try:
        row = conn.execute(
            "SELECT id, trip_id, status FROM registrations WHERE id = ?",
            (registration_id,)
        ).fetchone()
        return None if row is None else dict(row)

    finally:
        conn.close()


def list_trips():
    """Return every trip, soonest first."""

    conn = get_connection()

    try:
        rows = conn.execute(
            "SELECT * FROM trips ORDER BY start_date, id"
        ).fetchall()
        return [dict(row) for row in rows]

    finally:
        conn.close()


def list_registrations(trip_id):
    """Return a trip's registrations in the order they signed up."""

    conn = get_connection()

    try:
        rows = conn.execute(
            """
            SELECT id, name, email, status, registered_at, payment_deadline
            FROM registrations
            WHERE trip_id = ?
            ORDER BY registered_at, id
            """,
            (trip_id,)
        ).fetchall()
        return [dict(row) for row in rows]

    finally:
        conn.close()


def find_my_registration(registration_id, email):
    """Return a student's own registration and trip, or raise ValueError.

    The email must match, so knowing a registration number alone is not
    enough to see someone else's trip.
    """

    conn = get_connection()

    try:
        row = conn.execute(
            """
            SELECT id, trip_id, name, status, payment_deadline
            FROM registrations
            WHERE id = ? AND email = ?
            """,
            (registration_id, str(email).strip().lower())
        ).fetchone()

        if row is None:
            raise ValueError("No registration matches that number and email")

        trip = conn.execute(
            "SELECT * FROM trips WHERE id = ?", (row["trip_id"],)
        ).fetchone()

        return {"registration": dict(row), "trip": dict(trip)}

    finally:
        conn.close()
