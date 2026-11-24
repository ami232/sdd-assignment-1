import pytest

import app
import database
from group import library_client

CODENAMES = {"id": 1, "title": "Codenames", "owner": "Jinin", "min_players": 2, "max_players": 8, "playtime_minutes": 15}


def fake_find_games_that_fit(players: int, minutes: int) -> list[dict]:
    """pretend library has one short game that fits any group, so the route tests don't need the real library"""
    return [CODENAMES]


def unreachable_library(players: int, minutes: int) -> list[dict]:
    """pretend library is down, raising the same error library_client raises when the network call fails"""
    raise library_client.LibraryUnavailableError("library could not be reached")


@pytest.fixture
def client(monkeypatch):
    """give each test a fresh group app with an empty database and a pretend library"""
    monkeypatch.setattr(library_client, "find_games_that_fit", fake_find_games_that_fit)
    return app.create_app().test_client()

def test_home_page_reports_the_app_is_up(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.get_json()["status"] == "ok"

def test_unknown_url_returns_json_not_html(client):
    response = client.get("/does-not-exist")
    assert response.status_code == 404
    assert response.get_json() == {"error": "not found"}

def test_unknown_night_returns_404_with_the_reason(client):
    response = client.get("/nights/999")
    assert response.status_code == 404
    assert response.get_json() == {"error": "no night with id 999"}

def test_planning_a_night_through_the_api(client):
    jinin = client.post("/members", json={"name": "Jinin"}).get_json()
    nikita = client.post("/members", json={"name": "Nikita"}).get_json()
    night = client.post(
        "/nights",
        json={
            "night_date": "2026-10-12",
            "available_minutes": 60,
            "attendee_ids": [jinin["id"], nikita["id"]],
        },
    ).get_json()
    response = client.get(f"/nights/{night['id']}/plan")
    assert response.status_code == 200
    assert response.get_json()["player_count"] == 2
    assert len(response.get_json()["games"]) > 0

def test_planning_a_night_returns_503_when_library_is_down(client, monkeypatch):
    monkeypatch.setattr(library_client, "find_games_that_fit", unreachable_library)
    jinin = client.post("/members", json={"name": "Jinin"}).get_json()
    night = client.post(
        "/nights",
        json={"night_date": "2026-10-12", "available_minutes": 60, "attendee_ids": [jinin["id"]]},
    ).get_json()
    response = client.get(f"/nights/{night['id']}/plan")
    assert response.status_code == 503
    assert response.get_json() == {"error": "library is unavailable, try again later"}

def database_is_down() -> bool:
    """stand in for the real health check when the database can't be reached"""
    return False


def test_health_reports_ok_when_the_database_works(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json()["db"] == "ok"


def test_health_returns_503_when_the_database_is_unreachable(client, monkeypatch):
    monkeypatch.setattr(database, "check_database", database_is_down)
    response = client.get("/health")
    assert response.status_code == 503
    assert response.get_json()["db"] == "unavailable"