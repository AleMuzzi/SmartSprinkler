import pytest
from unittest.mock import Mock, patch

from fastapi.testclient import TestClient

from bayesian_sprinkler import api


TEST_CONFIG = {
    "esp": {
        "base_url": "http://192.168.1.10",
        "poll_interval": 120,
    },
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
            "watering_duration": 6,
        },
        "naga_morich": {
            "display_name": "Naga Morich",
            "esp_target": "NAGA_MORICH",
            "base_need": 0.68,
            "threshold": 0.50,
            "watering_duration": 6,
        },
        "carolina_reaper": {
            "display_name": "Carolina Reaper",
            "esp_target": "CAROLINA_REAPER",
            "base_need": 0.70,
            "threshold": 0.48,
            "watering_duration": 6,
        },
        "rosmarino": {
            "display_name": "Rosmarino",
            "esp_target": "ROSMARINO",
            "base_need": 0.20,
            "threshold": 0.80,
            "watering_duration": 2,
        },
    },
}


@pytest.fixture
def client():
    with patch("bayesian_sprinkler.api.init_db"):
        with patch("bayesian_sprinkler.api.BackgroundScheduler"):
            with patch("bayesian_sprinkler.api.insert_record") as mock_insert:
                app = api.create_app(TEST_CONFIG)
                yield TestClient(app)


class TestAPI:
    def test_health_endpoint(self, client):
        response = client.get("/api/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_manual_water_unknown_plant(self, client):
        response = client.post("/api/plants/manual-water", json={"plant_type": "basil"})
        assert response.status_code == 422

    def test_manual_water_with_water_low_alert(self, client):
        with patch.object(api.state.esp, "get_status") as mock_status:
            mock_status.return_value = {
                "air_temperature": "28.5",
                "air_humidity": "60.0",
                "soil_moisture": "45.0",
                "water_pump": "off",
                "water_low_alert": "on",
            }
            with patch.object(api.state.weather, "fetch") as mock_wx:
                mock_wx.return_value = {
                    "cloud_cover": "clear",
                    "rain_forecast": "no",
                }
                response = client.post(
                    "/api/plants/manual-water",
                    json={"plant_type": "habanero"},
                )
                assert response.status_code == 503
                assert "Water level low" in response.json()["detail"]

    def test_manual_water_success(self, client):
        with patch.object(api.state.esp, "get_status") as mock_status:
            mock_status.return_value = {
                "air_temperature": "28.5",
                "air_humidity": "60.0",
                "soil_moisture": "45.0",
                "water_pump": "off",
                "water_low_alert": "off",
            }
            with patch.object(api.state.weather, "fetch") as mock_wx:
                mock_wx.return_value = {
                    "cloud_cover": "clear",
                    "rain_forecast": "no",
                }
                with patch.object(api.state.esp, "start_watering") as mock_start:
                    with patch.object(api.state.esp, "stop_watering") as mock_stop:
                        response = client.post(
                            "/api/plants/manual-water",
                            json={"plant_type": "habanero"},
                        )
                        assert response.status_code == 200
                        assert response.json()["status"] == "ok"
                        assert response.json()["plant"] == "habanero"
                        mock_start.assert_called_once_with("HABANERO")
                        mock_stop.assert_called_once_with("HABANERO")

    def test_manual_water_dispatches_correct_esp_target(self, client):
        with patch.object(api.state.esp, "get_status") as mock_status:
            mock_status.return_value = {
                "air_temperature": "20.0",
                "air_humidity": "50.0",
                "soil_moisture": "40.0",
                "water_pump": "off",
                "water_low_alert": "off",
            }
            with patch.object(api.state.weather, "fetch") as mock_wx:
                mock_wx.return_value = {
                    "cloud_cover": "clear",
                    "rain_forecast": "no",
                }
                with patch.object(api.state.esp, "start_watering") as mock_start:
                    with patch.object(api.state.esp, "stop_watering"):
                        response = client.post(
                            "/api/plants/manual-water",
                            json={"plant_type": "naga_morich"},
                        )
                        assert response.status_code == 200
                        mock_start.assert_called_once_with("NAGA_MORICH")

    def test_api_requires_json_body(self, client):
        response = client.post("/api/plants/manual-water")
        assert response.status_code == 422
