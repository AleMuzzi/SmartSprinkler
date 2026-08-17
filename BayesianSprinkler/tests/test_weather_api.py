import pytest

from bayesian_sprinkler.sensor_client import WeatherClient


@pytest.fixture
def weather_client():
    return WeatherClient(latitude=44.695946, longitude=10.443454, cloud_threshold=45)


class TestWeatherAPILive:
    """Integration tests that hit the real Open-Meteo API.

    These tests require internet access. Skip if offline.
    """

    def test_fetch_returns_valid_cloud_cover(self, weather_client):
        result = weather_client.fetch()
        assert "cloud_cover" in result
        assert result["cloud_cover"] in ("clear", "cloudy")

    def test_fetch_returns_valid_rain_forecast(self, weather_client):
        result = weather_client.fetch()
        assert "rain_forecast" in result
        assert result["rain_forecast"] in ("yes", "no")

    def test_fetch_returns_temperature(self, weather_client):
        result = weather_client.fetch()
        assert "temperature" in result
        assert result["temperature"] is None or isinstance(result["temperature"], (int, float))

    def test_fetch_returns_humidity(self, weather_client):
        result = weather_client.fetch()
        assert "humidity" in result
        assert result["humidity"] is None or isinstance(result["humidity"], (int, float))

    def test_fetch_complete_structure(self, weather_client):
        result = weather_client.fetch()
        assert set(result.keys()) == {"cloud_cover", "rain_forecast", "temperature", "humidity"}