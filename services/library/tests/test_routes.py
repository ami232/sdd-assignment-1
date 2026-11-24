import pytest

import app
import database


@pytest.fixture
def client():
    """give each test a library app that starts from an empty, freshly seeded database"""
    return app.create_app().test_client()

def test_home_page_reports_the_app_is_up(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.get_json()["status"] == "ok"

def test_unknown_url_returns_json_not_html(client):
    response = client.get("/does-not-exist")
    assert response.status_code == 404
    assert response.get_json() == {"error": "not found"}

def test_adding_an_invalid_game_returns_400_with_the_reason(client):
    response = client.post("/games", json={"title": "Dune"})
    assert response.status_code == 400
    assert "missing field" in response.get_json()["error"]

def test_get_game_returns_its_id_and_title(client):
    response = client.get("/games/1")
    assert response.status_code == 200
    assert response.get_json() == {"id": 1, "title": "Catan"}

def test_get_game_returns_404_for_an_unknown_id(client):
    response = client.get("/games/999")
    assert response.status_code == 404
    assert response.get_json() == {"error": "no game with id 999"}

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