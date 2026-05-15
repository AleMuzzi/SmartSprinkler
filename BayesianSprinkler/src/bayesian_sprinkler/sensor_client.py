import logging
from datetime import datetime

import requests

logger = logging.getLogger(__name__)

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"


class ESP32Client:
    def __init__(self, base_url: str, thresholds: dict):
        self.base_url = base_url.rstrip("/")
        self.thresholds = thresholds

    def get_status(self) -> dict:
        resp = requests.get(f"{self.base_url}/status", timeout=10)
        resp.raise_for_status()
        return resp.json()

    def discretize_soil_moisture(self, value: float) -> str:
        if value <= self.thresholds["soil_moisture"]["dry"]:
            return "dry"
        if value <= self.thresholds["soil_moisture"]["moist"]:
            return "moist"
        return "wet"

    def discretize_temperature(self, value: float) -> str:
        if value <= self.thresholds["temperature"]["low"]:
            return "low"
        if value <= self.thresholds["temperature"]["medium"]:
            return "medium"
        return "high"

    def discretize_humidity(self, value: float) -> str:
        if value <= self.thresholds["humidity"]["low"]:
            return "low"
        if value <= self.thresholds["humidity"]["medium"]:
            return "medium"
        return "high"

    def send_command(self, action: str, target: str, amount: int = 0) -> dict:
        payload = {"action": action, "target": target, "amount": amount}
        logger.info("Sending command: %s", payload)
        resp = requests.post(f"{self.base_url}/command", json=payload, timeout=10)
        resp.raise_for_status()
        return resp.json()

    def start_watering(self, target: str) -> dict:
        return self.send_command("START", target)

    def stop_watering(self, target: str) -> dict:
        return self.send_command("STOP", target)


class WeatherClient:
    def __init__(self, latitude: float, longitude: float,
                 cloud_threshold: float = 50):
        self.lat = latitude
        self.lon = longitude
        self.cloud_threshold = cloud_threshold

    def fetch(self) -> dict:
        params = {
            "latitude": self.lat,
            "longitude": self.lon,
            "current": "cloud_cover",
            "daily": "precipitation_sum",
            "timezone": "auto",
            "forecast_days": 1,
        }
        try:
            resp = requests.get(OPEN_METEO_URL, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            return self._parse(data)
        except Exception:
            logger.warning("Weather API unavailable, using conservative defaults")
            return {"cloud_cover": "cloudy", "rain_forecast": "no"}

    @staticmethod
    def _parse(data: dict) -> dict:
        current = data.get("current", {})
        daily = data.get("daily", {})

        raw_cloud = current.get("cloud_cover", 100)
        raw_precip = (daily.get("precipitation_sum", [0]) or [0])[0]

        return {
            "cloud_cover": "cloudy" if raw_cloud >= 50 else "clear",
            "rain_forecast": "yes" if raw_precip > 0 else "no",
        }
