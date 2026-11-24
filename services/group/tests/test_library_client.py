from group import library_client


def test_timeout_defaults_to_2_seconds(monkeypatch):
    monkeypatch.delenv("LIBRARY_TIMEOUT_S", raising=False)
    assert library_client.get_timeout_seconds() == 2


def test_timeout_is_read_from_the_environment(monkeypatch):
    monkeypatch.setenv("LIBRARY_TIMEOUT_S", "0.5")
    assert library_client.get_timeout_seconds() == 0.5


def test_timeout_falls_back_to_the_default_when_it_is_not_a_number(monkeypatch):
    monkeypatch.setenv("LIBRARY_TIMEOUT_S", "soon")
    assert library_client.get_timeout_seconds() == 2


def test_timeout_falls_back_to_the_default_when_it_is_not_positive(monkeypatch):
    monkeypatch.setenv("LIBRARY_TIMEOUT_S", "0")
    assert library_client.get_timeout_seconds() == 2