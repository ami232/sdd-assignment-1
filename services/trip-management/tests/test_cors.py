"""CORS: only the UI's origin may call the service from a browser."""

from app import CORS_ORIGIN, app


def test_ui_origin_is_allowed():
    response = app.test_client().get("/health", headers={"Origin": CORS_ORIGIN})
    assert response.headers["Access-Control-Allow-Origin"] == CORS_ORIGIN


def test_other_origin_gets_no_cors_header():
    response = app.test_client().get("/health", headers={"Origin": "https://evil.example"})
    assert "Access-Control-Allow-Origin" not in response.headers


def test_preflight_for_json_post_is_allowed():
    # Browsers send this before a POST with a JSON body from another origin.
    response = app.test_client().options(
        "/trips",
        headers={
            "Origin": CORS_ORIGIN,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type",
        },
    )
    assert response.status_code == 200
    assert response.headers["Access-Control-Allow-Origin"] == CORS_ORIGIN
    assert "POST" in response.headers["Access-Control-Allow-Methods"]
    assert "Content-Type" in response.headers["Access-Control-Allow-Headers"]
