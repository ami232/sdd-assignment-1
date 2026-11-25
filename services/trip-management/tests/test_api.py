"""Tests for the HTTP endpoints."""

import urllib.error

import pytest

import app as service
import trip_management
from app import app
from trip_management import create_trip, register_student

TRIP = {"name": "Andorra 2027", "destination": "Grandvalira",
        "start_date": "2027-01-20", "end_date": "2027-01-24", "capacity": 10}


@pytest.fixture
def client(test_db):
    return app.test_client()


def make_trip(capacity=10):
    return create_trip("Andorra 2027", "Grandvalira",
                       "2027-01-20", "2027-01-24", capacity)


def test_create_and_list_trips(client):
    response = client.post("/trips", json=TRIP)
    assert response.status_code == 201

    trips = client.get("/trips").get_json()
    assert trips[0]["name"] == "Andorra 2027"
    assert trips[0]["stats"]["places_remaining"] == 10


def test_invalid_trip_returns_400_with_message(client):
    response = client.post("/trips", json={**TRIP, "capacity": 0})

    assert response.status_code == 400
    assert "capacity" in response.get_json()["error"].lower()


def test_get_trip_includes_stats(client):
    trip_id = make_trip()

    response = client.get(f"/trips/{trip_id}")

    assert response.status_code == 200
    assert response.get_json()["name"] == "Andorra 2027"
    assert response.get_json()["stats"]["capacity"] == 10


def test_get_unknown_trip_returns_404(client):
    assert client.get("/trips/999").status_code == 404


def test_register_pay_and_cancel(client):
    trip_id = make_trip()

    response = client.post(f"/trips/{trip_id}/registrations",
                           json={"name": "Ana", "email": "ana@ie.edu"})
    registration_id = response.get_json()["id"]
    assert response.status_code == 201

    assert client.post(f"/registrations/{registration_id}/payment").status_code == 200
    assert client.post(f"/registrations/{registration_id}/cancel").status_code == 200

    listed = client.get(f"/trips/{trip_id}/registrations").get_json()
    assert listed[0]["name"] == "Ana"
    assert listed[0]["status"] == "cancelled"


def test_get_registration_has_trip_and_status_only(client):
    trip_id = make_trip()
    registration_id = register_student(trip_id, "Ana", "ana@ie.edu")

    response = client.get(f"/registrations/{registration_id}")

    assert response.get_json() == {
        "id": registration_id,
        "trip_id": trip_id,
        "status": "pending_payment",
    }


def test_get_unknown_registration_returns_404(client):
    assert client.get("/registrations/999").status_code == 404


def test_my_trip_needs_the_matching_email(client):
    trip_id = make_trip()
    registration_id = register_student(trip_id, "Ana", "ana@ie.edu")

    found = client.post("/my-trip", json={"registration_id": registration_id,
                                          "email": " ANA@ie.edu "})
    assert found.status_code == 200
    assert found.get_json()["registration"]["name"] == "Ana"
    assert found.get_json()["trip"]["destination"] == "Grandvalira"

    wrong = client.post("/my-trip", json={"registration_id": registration_id,
                                          "email": "someone@ie.edu"})
    assert wrong.status_code == 400


def test_my_trip_rejects_a_missing_number(client):
    response = client.post("/my-trip", json={"email": "ana@ie.edu"})

    assert response.status_code == 400
    assert "registration number" in response.get_json()["error"]


def test_release_room_calls_room_allocation(monkeypatch):
    called = []
    monkeypatch.setattr(service.urllib.request, "urlopen",
                        lambda req, timeout: called.append(req.full_url))

    service.release_room(None, 7)

    assert called == [service.ROOMS_URL + "/registrations/7/release"]


def test_cancel_is_rolled_back_when_room_allocation_is_down(client, monkeypatch):
    def unreachable(req, timeout):
        raise urllib.error.URLError("refused")

    monkeypatch.setattr(service.urllib.request, "urlopen", unreachable)
    trip_management.on_registration_cancelled(service.release_room)
    registration_id = register_student(make_trip(), "Ana", "ana@ie.edu")

    response = client.post(f"/registrations/{registration_id}/cancel")

    assert response.status_code == 400
    assert "unavailable" in response.get_json()["error"]
    assert trip_management.get_registration(registration_id)["status"] == "pending_payment"
