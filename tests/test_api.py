"""API tests with a fake driver and a temp data dir."""

import pytest
from fastapi.testclient import TestClient

from homebound import app as app_module
from homebound.drivers import DeviceStatus, DriverError
from homebound.geocode import parse_latlon
from homebound.state import Store


class FakeDriver:
    name = "devicectl"

    def __init__(self):
        self.ready = True
        self.calls = []

    def status(self):
        return DeviceStatus(driver=self.name, ready=self.ready, connected=self.ready)

    def set(self, lat, lon):
        if not self.ready:
            raise DriverError("iPhone not ready", "Plug it in")
        self.calls.append(("set", lat, lon))
        return f"set {lat},{lon}"

    def clear(self):
        self.calls.append(("clear",))
        return "cleared"


@pytest.fixture
def client(tmp_path, monkeypatch):
    fake = FakeDriver()
    monkeypatch.setattr(app_module, "store", Store(tmp_path))
    monkeypatch.setattr(app_module, "driver", lambda: fake)
    c = TestClient(app_module.app)
    c.fake = fake
    return c


def test_set_confirm_reapply_clear(client):
    r = client.post("/api/set", json={"lat": 34.07, "lon": -118.45, "label": "Dorm"})
    assert r.json()["ok"] and r.json()["state"]["verified_in_maps"] is False
    assert client.post("/api/confirm").json()["state"]["verified_in_maps"] is True
    r = client.post("/api/reapply").json()
    assert r["ok"] and r["state"]["label"] == "Dorm" and r["state"]["verified_in_maps"] is False
    assert client.post("/api/clear").json()["state"]["active"] is False
    assert [c[0] for c in client.fake.calls] == ["set", "set", "clear"]
    assert any("Re-applied" in e["message"] for e in client.get("/api/log").json())


def test_set_failure_returns_fix(client):
    client.fake.ready = False
    r = client.post("/api/set", json={"lat": 34.0, "lon": -118.0})
    assert r.status_code == 409 and r.json()["fix"] == "Plug it in"


def test_reapply_without_history(client):
    assert client.post("/api/reapply").status_code == 409


def test_presets_roundtrip(client):
    client.post("/api/presets", json={"name": "Dorm", "lat": 34.07, "lon": -118.45})
    client.post("/api/presets", json={"name": "dorm", "lat": 34.08, "lon": -118.46})  # replaces
    assert client.get("/api/presets").json() == [{"name": "dorm", "lat": 34.08, "lon": -118.46}]
    assert client.delete("/api/presets/dorm").json() == []


def test_rejects_bad_coordinates(client):
    assert client.post("/api/set", json={"lat": 95, "lon": 0}).status_code == 422


def test_search_accepts_pasted_coordinates(client):
    assert client.get("/api/search", params={"q": "34.07161, -118.44219"}).json()[0]["lat"] == 34.07161


@pytest.mark.parametrize("text,expected", [
    ("34.07161, -118.44219", (34.07161, -118.44219)),
    ("34.07161 -118.44219", (34.07161, -118.44219)),
    ("Powell Library", None),
    ("200, 10", None),
])
def test_parse_latlon(text, expected):
    assert parse_latlon(text) == expected
