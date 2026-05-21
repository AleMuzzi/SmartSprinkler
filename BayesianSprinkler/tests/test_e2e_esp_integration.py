"""End-to-end integration tests: Bayesian server ↔ ESP32 firmware.

Mocks the ESP32 firmware as a simple HTTP server to test the full
communication flow: Bayesian server polls /status, sends /command,
and handles water level alerts.
"""

import json
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from bayesian_sprinkler import api
from bayesian_sprinkler.sensor_client import ESP32Client

TEST_CONFIG = {
    "esp": {"base_url": "http://127.0.0.1:18999", "poll_interval": 3600},
    "weather": {
        "latitude": 44.69,
        "longitude": 10.44,
        "cloud_cover_threshold": 50,
    },
    "thresholds": {
        "soil_moisture": {"dry": 35, "moist": 65},
        "temperature": {"low": 16, "medium": 29},
        "humidity": {"low": 45, "medium": 70},
    },
    "plants": {
        "habanero": {
            "display_name": "Habanero",
            "esp_target": "HABANERO",
            "base_need": 0.65,
            "threshold": 0.50,
            "watering_duration": 0.1,
        },
        "naga_morich": {
            "display_name": "Naga Morich",
            "esp_target": "NAGA_MORICH",
            "base_need": 0.68,
            "threshold": 0.50,
            "watering_duration": 0.1,
        },
    },
}


class MockESPHandler(BaseHTTPRequestHandler):
    """Simulates the ESP32 firmware HTTP API."""

    status_data = {
        "status": "ok",
        "air_temperature": "28.5",
        "air_humidity": "60.0",
        "soil_moisture": "45.0",
        "water_pump": "off",
        "valve_1": "off",
        "valve_2": "off",
        "valve_3": "off",
        "soil_moisture_0": "12000",
        "soil_moisture_1": "15000",
        "soil_moisture_2": "8000",
        "soil_moisture_3": "20000",
        "water_low_alert": "off",
        "blocked_amount_ml": "0",
        "active_plant": "null",
    }
    last_command = None
    last_body = None

    def do_GET(self):
        if self.path == "/status":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(self.status_data).encode())
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path == "/command":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            self.__class__.last_body = body
            command = json.loads(body)
            self.__class__.last_command = command
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok"}).encode())
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass


@pytest.fixture(scope="module")
def mock_esp():
    """Start a mock ESP32 HTTP server on a random port."""
    server = HTTPServer(("127.0.0.1", 18999), MockESPHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    # Reset state
    MockESPHandler.last_command = None
    MockESPHandler.last_body = None
    MockESPHandler.status_data["water_low_alert"] = "off"
    MockESPHandler.status_data["soil_moisture"] = "45.0"
    MockESPHandler.status_data["water_pump"] = "off"
    time.sleep(0.1)
    yield server
    server.shutdown()


@pytest.fixture
def client(mock_esp):
    with patch("bayesian_sprinkler.api.init_db"):
        with patch("bayesian_sprinkler.api.BackgroundScheduler"):
            with patch("bayesian_sprinkler.api.insert_record"):
                app = api.create_app(TEST_CONFIG)
                yield TestClient(app)


class TestESPIntegration:
    def test_bayesian_fetches_esp_status(self, mock_esp):
        esp = ESP32Client(base_url="http://127.0.0.1:18999", thresholds=TEST_CONFIG["thresholds"])
        status = esp.get_status()
        assert status["status"] == "ok"
        assert status["air_temperature"] == "28.5"
        assert status["soil_moisture"] == "45.0"

    def test_bayesian_sends_command_to_esp(self, mock_esp):
        esp = ESP32Client(base_url="http://127.0.0.1:18999", thresholds=TEST_CONFIG["thresholds"])
        result = esp.send_command("START", "HABANERO")
        assert result["status"] == "ok"
        assert MockESPHandler.last_command == {"action": "START", "target": "HABANERO", "amount": 0}

    def test_manual_water_sends_start_and_stop(self, mock_esp, client):
        MockESPHandler.status_data["water_low_alert"] = "off"
        with patch.object(api.state.weather, "fetch") as mock_wx:
            mock_wx.return_value = {"cloud_cover": "clear", "rain_forecast": "no"}
            response = client.post(
                "/api/plants/manual-water",
                json={"plant_type": "habanero"},
            )
        assert response.status_code == 200
        # ESP should have received START then STOP commands
        assert MockESPHandler.last_command is not None
        # last command should be STOP
        assert MockESPHandler.last_command["action"] == "STOP"

    def test_manual_water_blocked_when_alert_active(self, mock_esp, client):
        MockESPHandler.status_data["water_low_alert"] = "on"
        with patch.object(api.state.weather, "fetch") as mock_wx:
            mock_wx.return_value = {"cloud_cover": "clear", "rain_forecast": "no"}
            response = client.post(
                "/api/plants/manual-water",
                json={"plant_type": "habanero"},
            )
        assert response.status_code == 503
        assert "Water level low" in response.json()["detail"]
        # No command should have been sent to ESP
        if MockESPHandler.last_command:
            assert MockESPHandler.last_command["action"] != "START"

    def test_water_low_alert_blocks_then_clears(self, mock_esp, client):
        # First: alert active → blocked
        MockESPHandler.status_data["water_low_alert"] = "on"
        with patch.object(api.state.weather, "fetch") as mock_wx:
            mock_wx.return_value = {"cloud_cover": "clear", "rain_forecast": "no"}
            resp_blocked = client.post(
                "/api/plants/manual-water",
                json={"plant_type": "naga_morich"},
            )
        assert resp_blocked.status_code == 503

        # Then: alert cleared → success
        MockESPHandler.status_data["water_low_alert"] = "off"
        with patch.object(api.state.weather, "fetch") as mock_wx:
            mock_wx.return_value = {"cloud_cover": "clear", "rain_forecast": "no"}
            resp_ok = client.post(
                "/api/plants/manual-water",
                json={"plant_type": "naga_morich"},
            )
        assert resp_ok.status_code == 200

    def test_esp_receives_correct_target_name(self, mock_esp, client):
        MockESPHandler.status_data["water_low_alert"] = "off"
        with patch.object(api.state.weather, "fetch") as mock_wx:
            mock_wx.return_value = {"cloud_cover": "clear", "rain_forecast": "no"}
            response = client.post(
                "/api/plants/manual-water",
                json={"plant_type": "naga_morich"},
            )
        assert response.status_code == 200
        # The ESP should have received the correct esp_target "NAGA_MORICH"
        assert MockESPHandler.last_command is not None
        assert MockESPHandler.last_command["target"] == "NAGA_MORICH"
