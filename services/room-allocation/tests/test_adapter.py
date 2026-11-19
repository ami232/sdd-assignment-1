"""Tests for the HTTP adapter that asks Trip Management about trips."""

import io
import urllib.error

import pytest

import room_allocation


def fake_urlopen(answer):
    """Return a urlopen replacement that gives back `answer` or raises it."""
    def urlopen(url, timeout):
        fake_urlopen.last_url = url
        if isinstance(answer, Exception):
            raise answer
        return io.BytesIO(answer.encode())
    return urlopen


def http_error(code):
    return urllib.error.HTTPError("http://x", code, "error", {}, None)


def test_get_registration_reads_trip_and_status(monkeypatch):
    monkeypatch.setattr(room_allocation.config, "TRIPS_URL", "http://trips")
    monkeypatch.setattr(
        room_allocation.urllib.request, "urlopen",
        fake_urlopen('{"id": 7, "trip_id": 2, "status": "confirmed"}'),
    )

    assert room_allocation._get_registration(7) == {
        "trip_id": 2, "status": "confirmed",
    }
    assert fake_urlopen.last_url == "http://trips/registrations/7"


def test_404_means_not_found(monkeypatch):
    monkeypatch.setattr(room_allocation.urllib.request, "urlopen",
                        fake_urlopen(http_error(404)))

    assert room_allocation._trip_exists(1) is False
    assert room_allocation._get_registration(1) is None


def test_server_error_is_reported_as_unavailable(monkeypatch):
    monkeypatch.setattr(room_allocation.urllib.request, "urlopen",
                        fake_urlopen(http_error(500)))

    with pytest.raises(ValueError, match="unavailable"):
        room_allocation._trip_exists(1)


def test_unreachable_service_is_reported_as_unavailable(monkeypatch):
    monkeypatch.setattr(room_allocation.urllib.request, "urlopen",
                        fake_urlopen(urllib.error.URLError("refused")))

    with pytest.raises(ValueError, match="unavailable"):
        room_allocation._get_registration(1)
