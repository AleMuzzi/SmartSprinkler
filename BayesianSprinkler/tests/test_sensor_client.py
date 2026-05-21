import pytest
from unittest.mock import Mock, patch

from bayesian_sprinkler.sensor_client import ESP32Client, WeatherClient


THRESHOLDS = {
    "soil_moisture": {"dry": 35, "moist": 65},
    "temperature": {"low": 16, "medium": 29},
    "humidity": {"low": 45, "medium": 70},
}


@pytest.fixture
def esp_client():
    return ESP32Client(base_url="http://192.168.1.10", thresholds=THRESHOLDS)


class TestESP32Client:
    def test_init_sets_base_url(self, esp_client):
        assert esp_client.base_url == "http://192.168.1.10"

    def test_discretize_soil_moisture_dry(self, esp_client):
        assert esp_client.discretize_soil_moisture(20) == "dry"

    def test_discretize_soil_moisture_moist(self, esp_client):
        assert esp_client.discretize_soil_moisture(50) == "moist"

    def test_discretize_soil_moisture_wet(self, esp_client):
        assert esp_client.discretize_soil_moisture(80) == "wet"

    def test_discretize_soil_moisture_boundary_dry(self, esp_client):
        assert esp_client.discretize_soil_moisture(34) == "dry"
        assert esp_client.discretize_soil_moisture(36) == "moist"

    def test_discretize_temperature_low(self, esp_client):
        assert esp_client.discretize_temperature(10) == "low"

    def test_discretize_temperature_medium(self, esp_client):
        assert esp_client.discretize_temperature(22) == "medium"

    def test_discretize_temperature_high(self, esp_client):
        assert esp_client.discretize_temperature(35) == "high"

    def test_discretize_humidity_low(self, esp_client):
        assert esp_client.discretize_humidity(30) == "low"

    def test_discretize_humidity_medium(self, esp_client):
        assert esp_client.discretize_humidity(55) == "medium"

    def test_discretize_humidity_high(self, esp_client):
        assert esp_client.discretize_humidity(85) == "high"

    @patch("bayesian_sprinkler.sensor_client.requests.get")
    def test_get_status(self, mock_get, esp_client):
        mock_get.return_value = Mock(status_code=200)
        mock_get.return_value.json.return_value = {
            "air_temperature": "28.5",
            "air_humidity": "60.0",
            "soil_moisture": "45.0",
            "water_pump": "off",
            "water_low_alert": "off",
        }
        status = esp_client.get_status()
        assert status["air_temperature"] == "28.5"
        assert status["water_low_alert"] == "off"
        mock_get.assert_called_once_with("http://192.168.1.10/status", timeout=10)

    @patch("bayesian_sprinkler.sensor_client.requests.get")
    def test_get_status_water_low_alert(self, mock_get, esp_client):
        mock_get.return_value = Mock(status_code=200)
        mock_get.return_value.json.return_value = {
            "water_low_alert": "on",
            "blocked_amount_ml": "250",
        }
        status = esp_client.get_status()
        assert status["water_low_alert"] == "on"
        assert status["blocked_amount_ml"] == "250"

    @patch("bayesian_sprinkler.sensor_client.requests.post")
    def test_send_command(self, mock_post, esp_client):
        mock_post.return_value = Mock(status_code=200)
        mock_post.return_value.json.return_value = {"status": "ok"}
        result = esp_client.send_command("START", "HABANERO")
        mock_post.assert_called_once_with(
            "http://192.168.1.10/command",
            json={"action": "START", "target": "HABANERO", "amount": 0},
            timeout=10,
        )
        assert result["status"] == "ok"

    @patch("bayesian_sprinkler.sensor_client.requests.post")
    def test_start_watering(self, mock_post, esp_client):
        mock_post.return_value = Mock(status_code=200)
        mock_post.return_value.json.return_value = {"status": "ok"}
        result = esp_client.start_watering("NAGA_MORICH")
        mock_post.assert_called_once_with(
            "http://192.168.1.10/command",
            json={"action": "START", "target": "NAGA_MORICH", "amount": 0},
            timeout=10,
        )
        assert result["status"] == "ok"

    @patch("bayesian_sprinkler.sensor_client.requests.post")
    def test_stop_watering(self, mock_post, esp_client):
        mock_post.return_value = Mock(status_code=200)
        mock_post.return_value.json.return_value = {"status": "ok"}
        result = esp_client.stop_watering("NAGA_MORICH")
        mock_post.assert_called_once_with(
            "http://192.168.1.10/command",
            json={"action": "STOP", "target": "NAGA_MORICH", "amount": 0},
            timeout=10,
        )
        assert result["status"] == "ok"


class TestWeatherClient:
    @pytest.fixture
    def weather_client(self):
        return WeatherClient(latitude=44.69, longitude=10.44, cloud_threshold=50)

    def test_parse_cloudy(self, weather_client):
        data = {"current": {"cloud_cover": 75}, "daily": {"precipitation_sum": [0]}}
        result = weather_client._parse(data)
        assert result["cloud_cover"] == "cloudy"

    def test_parse_clear(self, weather_client):
        data = {"current": {"cloud_cover": 20}, "daily": {"precipitation_sum": [0]}}
        result = weather_client._parse(data)
        assert result["cloud_cover"] == "clear"

    def test_parse_rain_yes(self, weather_client):
        data = {"current": {"cloud_cover": 50}, "daily": {"precipitation_sum": [5.0]}}
        result = weather_client._parse(data)
        assert result["rain_forecast"] == "yes"

    def test_parse_rain_no(self, weather_client):
        data = {"current": {"cloud_cover": 50}, "daily": {"precipitation_sum": [0]}}
        result = weather_client._parse(data)
        assert result["rain_forecast"] == "no"

    def test_parse_edge_cloud_threshold(self, weather_client):
        data = {"current": {"cloud_cover": 50}, "daily": {"precipitation_sum": [0]}}
        result = weather_client._parse(data)
        assert result["cloud_cover"] == "cloudy"

    def test_parse_defaults_on_missing_data(self, weather_client):
        data = {"current": {}, "daily": {}}
        result = weather_client._parse(data)
        assert result["cloud_cover"] == "cloudy"
        assert result["rain_forecast"] == "no"

    @patch("bayesian_sprinkler.sensor_client.requests.get")
    def test_fetch_api_success(self, mock_get, weather_client):
        mock_get.return_value = Mock(status_code=200)
        mock_get.return_value.json.return_value = {
            "current": {"cloud_cover": 30},
            "daily": {"precipitation_sum": [0]},
        }
        result = weather_client.fetch()
        assert result["cloud_cover"] == "clear"
        assert result["rain_forecast"] == "no"

    @patch("bayesian_sprinkler.sensor_client.requests.get")
    def test_fetch_api_failure_returns_defaults(self, mock_get, weather_client):
        mock_get.side_effect = Exception("Connection error")
        result = weather_client.fetch()
        assert result["cloud_cover"] == "cloudy"
        assert result["rain_forecast"] == "no"
