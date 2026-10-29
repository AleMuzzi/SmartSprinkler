"""Watering mode + notification centre.

Covers the ``notification`` watering mode (dry-run inference: same doses,
no ESP command) and the notification history/badge endpoints used by the
portal's bell and by the mobile app.
"""

import pytest
from unittest.mock import patch

from fastapi.testclient import TestClient

from bayesian_sprinkler import api, database
from tests.test_api import TEST_CONFIG


@pytest.fixture
def db(tmp_path, monkeypatch):
    """Throwaway SQLite file so tests never touch the real sprinkler.db."""
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "test.db")
    yield


@pytest.fixture(autouse=True)
def reset_watering_mode():
    """``state`` is a module singleton — always start/end on automatic."""
    api.state._watering_mode = "automatic"
    yield
    api.state._watering_mode = "automatic"


@pytest.fixture
def client(db):
    with patch("bayesian_sprinkler.api.BackgroundScheduler"):
        with patch("bayesian_sprinkler.api.insert_record"):
            with patch("bayesian_sprinkler.api.insert_plant_telemetry"):
                app = api.create_app(TEST_CONFIG)
                yield TestClient(app)


def _dry_hot_status() -> dict:
    """Status snapshot where every plant is thirsty.

    ``_sim_hour=4`` keeps the cycle inside the default watering window so the
    result doesn't depend on the wall clock.
    """
    return {
        "air_temperature": "32.0",
        "air_humidity": "25.0",
        "soil_moisture": "10.0",
        "soil_moisture_0": "10.0",
        "soil_moisture_1": "10.0",
        "soil_moisture_2": "10.0",
        "soil_moisture_3": "10.0",
        "water_pump": "off",
        "water_low_alert": "off",
        "_sim_hour": 4,
    }


def _run_inference(client, status: dict | None = None):
    """POST /api/inference/run with mocked ESP/weather/sleep."""
    weather = {"cloud_cover": "clear", "rain_forecast": "no"}
    with patch.object(api.state.esp, "get_status", return_value=status or _dry_hot_status()):
        with patch.object(api.state.weather, "fetch", return_value=weather):
            with patch.object(api.state.esp, "start_watering") as start:
                with patch.object(api.state.esp, "stop_watering") as stop:
                    with patch("time.sleep"):
                        response = client.post("/api/inference/run")
    return response, start, stop


def _set_mode(client, mode: str):
    return client.post("/api/service/watering-mode", json={"mode": mode})


class TestWateringMode:
    def test_defaults_to_automatic(self, client):
        assert api.state._watering_mode == "automatic"
        assert database.get_service_config("watering_mode") is None

    def test_set_notification_mode_persists(self, client):
        response = _set_mode(client, "notification")
        assert response.status_code == 200
        assert response.json() == {
            "status": "ok",
            "mode": "notification",
            "previous": "automatic",
        }
        assert api.state._watering_mode == "notification"
        assert database.get_service_config("watering_mode") == "notification"

    def test_set_automatic_mode_records_previous(self, client):
        _set_mode(client, "notification")
        response = _set_mode(client, "automatic")
        assert response.json()["previous"] == "notification"
        assert database.get_service_config("watering_mode") == "automatic"

    def test_unknown_mode_is_rejected(self, client):
        response = _set_mode(client, "manual")
        assert response.status_code == 422
        assert api.state._watering_mode == "automatic"

    def test_mode_is_visible_through_service_config(self, client):
        _set_mode(client, "notification")
        config = client.get("/api/service/config").json()["config"]
        assert config["watering_mode"] == "notification"


class TestNotificationModeDryRun:
    def test_computes_doses_without_watering(self, client):
        cistern_before = api.state._cistern_level_ml
        _set_mode(client, "notification")

        response, start, stop = _run_inference(client)

        assert response.status_code == 200
        body = response.json()
        assert body["mode"] == "notification"
        # Same values the automatic mode would have dispensed: mL, above the
        # hardware pulse floor.
        assert body["watered"], "expected at least one thirsty plant"
        assert all(dose >= api._MIN_DOSE_ML for dose in body["watered"].values())
        # Nothing was actually dispensed.
        start.assert_not_called()
        stop.assert_not_called()
        assert api.state._cistern_level_ml == cistern_before
        assert api.state._last_watered_doses == {}

    def test_creates_one_notification_matching_the_doses(self, client):
        _set_mode(client, "notification")

        response, _, _ = _run_inference(client)
        doses = response.json()["watered"]

        listing = client.get("/api/notifications").json()
        assert listing["unread_count"] == 1
        assert len(listing["notifications"]) == 1
        notification = listing["notifications"][0]
        assert notification["doses"] == pytest.approx(doses)
        assert notification["unread"] is True
        assert notification["source"] == "manual"
        assert notification["opened_at"] is None
        assert notification["read_at"] is None
        assert str(int(doses["habanero"])) in notification["body"]

    def test_automatic_mode_waters_and_notifies_nothing(self, client):
        response, start, stop = _run_inference(client)

        assert response.status_code == 200
        assert response.json()["mode"] == "automatic"
        start.assert_called()
        stop.assert_called()

        listing = client.get("/api/notifications").json()
        assert listing["notifications"] == []
        assert listing["unread_count"] == 0

    def test_automatic_mode_refills_never_notifies(self, client):
        # The low-water gate still applies in dry-run mode: a tank-empty
        # cycle proposes nothing, exactly like it wouldn't water.
        _set_mode(client, "notification")
        status = _dry_hot_status()
        status["water_low_alert"] = "on"

        response, start, _ = _run_inference(client, status)

        assert response.status_code == 200
        assert response.json()["watered"] == {}
        start.assert_not_called()
        assert client.get("/api/notifications").json()["unread_count"] == 0


class TestNotificationCentre:
    @staticmethod
    def _seed(client, source="manual"):
        """Insert a notification straight through the DB layer."""
        return database.insert_notification(
            source=source,
            doses={"habanero": 138.0},
            title="1 pianta da innaffiare",
            body="Habanero 138 ml — totale 138 ml",
        )

    def test_listing_returns_newest_first(self, client):
        first = self._seed(client)
        second = self._seed(client, source="scheduled")

        notifications = client.get("/api/notifications").json()["notifications"]
        assert [n["id"] for n in notifications] == [second, first]
        assert notifications[0]["doses"] == {"habanero": 138.0}

    def test_open_clears_the_badge(self, client):
        notification_id = self._seed(client)
        assert client.get("/api/notifications").json()["unread_count"] == 1

        response = client.post(f"/api/notifications/{notification_id}/open")
        assert response.status_code == 200
        assert response.json()["unread_count"] == 0

        entry = client.get("/api/notifications").json()["notifications"][0]
        assert entry["unread"] is False
        assert entry["opened_at"] is not None
        assert entry["read_at"] is None

    def test_read_clears_the_badge(self, client):
        notification_id = self._seed(client)
        response = client.post(f"/api/notifications/{notification_id}/read")
        assert response.status_code == 200
        assert response.json()["unread_count"] == 0
        entry = client.get("/api/notifications").json()["notifications"][0]
        assert entry["read_at"] is not None

    def test_read_all_clears_every_badge(self, client):
        self._seed(client)
        self._seed(client, source="scheduled")
        assert client.get("/api/notifications").json()["unread_count"] == 2

        response = client.post("/api/notifications/read-all")
        assert response.status_code == 200
        assert response.json() == {"status": "ok", "updated": 2, "unread_count": 0}

    def test_open_is_idempotent(self, client):
        notification_id = self._seed(client)
        first = client.post(f"/api/notifications/{notification_id}/open").json()
        second = client.post(f"/api/notifications/{notification_id}/open").json()
        assert first["unread_count"] == second["unread_count"] == 0

    def test_unknown_notification_returns_404(self, client):
        assert client.post("/api/notifications/9999/open").status_code == 404
        assert client.post("/api/notifications/9999/read").status_code == 404

    def test_limit_is_honoured(self, client):
        for _ in range(5):
            self._seed(client)
        assert len(client.get("/api/notifications?limit=2").json()["notifications"]) == 2

    def test_rotation_keeps_history_bounded(self, client):
        for _ in range(database.MAX_NOTIFICATIONS + 5):
            self._seed(client)
        listing = client.get("/api/notifications?limit=500").json()
        assert len(listing["notifications"]) == database.MAX_NOTIFICATIONS
        assert listing["unread_count"] == database.MAX_NOTIFICATIONS
