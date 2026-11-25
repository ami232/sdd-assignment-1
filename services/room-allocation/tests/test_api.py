"""Tests for the HTTP endpoints, with Trip Management faked."""

import pytest

from app import app


@pytest.fixture
def client(test_db):
    return app.test_client()


def test_create_room_and_assign_student(client, trips):
    trip_id = trips.add_trip()
    student = trips.add_student(trip_id)

    room = client.post(f"/trips/{trip_id}/rooms", json={"name": "Room 101", "capacity": 2})
    room_id = room.get_json()["id"]
    assert room.status_code == 201

    assigned = client.post(f"/rooms/{room_id}/assignments", json={"registration_id": student})
    assert assigned.status_code == 201

    assert client.get(f"/trips/{trip_id}/rooms").get_json()[0]["occupied"] == 1
    assert client.get(f"/trips/{trip_id}/assignments").get_json() == [
        {"registration_id": student, "room_id": room_id, "room_name": "Room 101"}
    ]
    assert client.get(f"/registrations/{student}/room").get_json() == {
        "name": "Room 101", "capacity": 2, "occupied": 1,
    }


def test_rule_breaks_return_400_with_message(client, trips):
    trip_id = trips.add_trip()

    response = client.post(f"/trips/{trip_id}/rooms", json={"name": "Huge", "capacity": 9})

    assert response.status_code == 400
    assert "between 1 and 6" in response.get_json()["error"]


def test_student_without_room_gets_null(client, trips):
    assert client.get("/registrations/1/room").get_json() is None


def test_preferences_are_listed_per_trip(client, trips):
    trip_id = trips.add_trip()
    ana = trips.add_student(trip_id)
    ben = trips.add_student(trip_id)
    other_trip = trips.add_trip()
    cara = trips.add_student(other_trip)
    dan = trips.add_student(other_trip)

    client.post("/preferences", json={"registration_id": ana, "preferred_registration_id": ben})
    client.post("/preferences", json={"registration_id": cara, "preferred_registration_id": dan})

    assert client.get(f"/trips/{trip_id}/preferences").get_json() == [
        {"registration_id": ana, "preferred_registration_id": ben}
    ]


def test_release_frees_the_bed(client, trips):
    trip_id = trips.add_trip()
    student = trips.add_student(trip_id)
    room_id = client.post(f"/trips/{trip_id}/rooms", json={"name": "A", "capacity": 2}).get_json()["id"]
    client.post(f"/rooms/{room_id}/assignments", json={"registration_id": student})

    assert client.post(f"/registrations/{student}/release").status_code == 200
    assert client.get(f"/trips/{trip_id}/rooms").get_json()[0]["occupied"] == 0
