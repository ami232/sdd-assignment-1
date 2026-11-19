"""Trip Management service: trips and registrations.

The domain logic lives in trip_management.py and trip_statistics.py. This
file only turns HTTP requests into calls to them and their answers into JSON.
"""

import os
import urllib.error
import urllib.request

from flask import Flask, jsonify, request

from db import init_db
from trip_management import (
    cancel_registration,
    confirm_payment,
    create_trip,
    find_my_registration,
    get_registration,
    get_trip,
    list_registrations,
    list_trips,
    on_registration_cancelled,
    register_student,
)
from trip_statistics import get_trip_statistics

# Commit SHA of the running image, set by the pipeline at deploy time.
VERSION = os.environ.get("GIT_SHA", "dev")

# Base URL of the Room Allocation service, told about cancellations.
ROOMS_URL = os.environ.get("ROOMS_URL", "http://room-allocation:8000")

app = Flask(__name__)

# Create any missing tables when the service starts. Safe to repeat.
init_db()


def release_room(conn, registration_id):
    """Observer: ask Room Allocation to free a cancelled student's bed.

    It runs inside the cancellation's transaction, so if Room Allocation
    cannot be reached the cancellation is rolled back and the organiser
    sees an error, instead of a cancelled student keeping a bed.
    """
    url = f"{ROOMS_URL}/registrations/{registration_id}/release"
    try:
        urllib.request.urlopen(urllib.request.Request(url, method="POST"), timeout=5)
    except urllib.error.URLError as error:
        raise ValueError("Room Allocation is unavailable, please try again") from error


on_registration_cancelled(release_room)


def body():
    """The request's JSON body, or an empty dict if there is none."""
    return request.get_json(silent=True) or {}


@app.errorhandler(ValueError)
def bad_request(error):
    """Every rule the domain enforces raises ValueError; send it back as a 400."""
    return jsonify(error=str(error)), 400


@app.get("/health")
def health():
    """Report that the service is up. The database check is added with the database."""
    return jsonify(status="ok", service="trip-management", version=VERSION)


@app.get("/trips")
def trips():
    """All trips, each with its registration statistics."""
    return jsonify([
        {**trip, "stats": get_trip_statistics(trip["id"])}
        for trip in list_trips()
    ])


@app.post("/trips")
def new_trip():
    data = body()
    trip_id = create_trip(
        data.get("name", ""), data.get("destination", ""),
        data.get("start_date", ""), data.get("end_date", ""),
        data.get("capacity"),
    )
    return jsonify(id=trip_id), 201


@app.get("/trips/<int:trip_id>")
def trip(trip_id):
    """One trip with its statistics, or 404. Room Allocation uses this too."""
    found = get_trip(trip_id)
    if found is None:
        return jsonify(error="Trip not found"), 404
    return jsonify({**found, "stats": get_trip_statistics(trip_id)})


@app.get("/trips/<int:trip_id>/registrations")
def registrations(trip_id):
    return jsonify(list_registrations(trip_id))


@app.post("/trips/<int:trip_id>/registrations")
def register(trip_id):
    data = body()
    registration_id = register_student(trip_id, data.get("name", ""), data.get("email", ""))
    return jsonify(id=registration_id), 201


@app.get("/registrations/<int:registration_id>")
def registration(registration_id):
    """A registration's trip and status, or 404. Used by Room Allocation."""
    found = get_registration(registration_id)
    if found is None:
        return jsonify(error="Registration not found"), 404
    return jsonify(found)


@app.post("/registrations/<int:registration_id>/payment")
def payment(registration_id):
    confirm_payment(registration_id)
    return jsonify(status="confirmed")


@app.post("/registrations/<int:registration_id>/cancel")
def cancel(registration_id):
    cancel_registration(registration_id)
    return jsonify(status="cancelled")


@app.post("/my-trip")
def my_trip():
    """A student's own registration and trip, checked against their email.

    POST rather than GET so the email is not written to the access log.
    """
    data = body()
    try:
        registration_id = int(data.get("registration_id"))
    except (TypeError, ValueError):
        raise ValueError("Enter your registration number")
    return jsonify(find_my_registration(registration_id, data.get("email", "")))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "8000")))
