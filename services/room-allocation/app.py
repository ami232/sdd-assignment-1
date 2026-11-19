"""Room Allocation service: rooms, room assignments and roommate preferences.

The domain logic lives in room_allocation.py. This file only turns HTTP
requests into calls to it and its answers into JSON.
"""

import os

from flask import Flask, jsonify, request

from db import init_db
from room_allocation import (
    add_roommate_preference,
    assign_student,
    create_room,
    get_assignments,
    get_preferences,
    get_rooms,
    get_student_room,
    release_student,
)

# Commit SHA of the running image, set by the pipeline at deploy time.
VERSION = os.environ.get("GIT_SHA", "dev")

app = Flask(__name__)

# Create any missing tables when the service starts. Safe to repeat.
init_db()


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
    return jsonify(status="ok", service="room-allocation", version=VERSION)


@app.get("/trips/<int:trip_id>/rooms")
def rooms(trip_id):
    return jsonify(get_rooms(trip_id))


@app.post("/trips/<int:trip_id>/rooms")
def new_room(trip_id):
    data = body()
    room_id = create_room(trip_id, data.get("name", ""), data.get("capacity"))
    return jsonify(id=room_id), 201


@app.get("/trips/<int:trip_id>/assignments")
def assignments(trip_id):
    return jsonify(get_assignments(trip_id))


@app.post("/rooms/<int:room_id>/assignments")
def assign(room_id):
    assignment_id = assign_student(room_id, body().get("registration_id"))
    return jsonify(id=assignment_id), 201


@app.get("/trips/<int:trip_id>/preferences")
def preferences(trip_id):
    return jsonify(get_preferences(trip_id))


@app.post("/preferences")
def new_preference():
    data = body()
    preference_id = add_roommate_preference(
        data.get("registration_id"), data.get("preferred_registration_id")
    )
    return jsonify(id=preference_id), 201


@app.get("/registrations/<int:registration_id>/room")
def student_room(registration_id):
    """The student's room for the personal page, or null if none yet."""
    return jsonify(get_student_room(registration_id))


@app.post("/registrations/<int:registration_id>/release")
def release(registration_id):
    """Called by Trip Management after a cancellation. Safe to repeat."""
    release_student(registration_id)
    return jsonify(status="released")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "8000")))
