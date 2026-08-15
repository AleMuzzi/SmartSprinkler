import logging
from json import JSONDecodeError

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
        try:
            resp_json = resp.json()
        except JSONDecodeError:
            logger.error("ESP32 returned invalid JSON: %s", resp.text)
            raise
        return resp_json

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

    def get_firmware_version(self) -> str | None:
        """Read the firmware version reported by the ESP ``/health`` endpoint.

        The version lives inside the ``version`` field of the health payload
        (``{"status":"ok","version":"1.0.0.5"}``). Returns ``None`` when the
        ESP is unreachable or the payload is missing/lacks the field — the
        UI falls back to "unknown" rather than erroring out.
        """
        try:
            resp = requests.get(f"{self.base_url}/health", timeout=5)
            resp.raise_for_status()
        except Exception:
            logger.warning("Failed to read firmware version from ESP (%s)", self.base_url)
            return None
        try:
            payload = resp.json()
        except ValueError:
            logger.error("ESP32 returned invalid JSON on /health: %s", resp.text)
            return None
        version = payload.get("version")
        if not isinstance(version, str) or not version.strip():
            return None
        return version.strip()

    def ota_update(self, filename: str, fileobj, timeout: float = 120.0) -> dict:
        """Stream a firmware image to the ESP ``/update`` endpoint.

        The ESP's OTA handler consumes ``multipart/form-data`` uploads with a
        single file part named ``update``. The whole body is streamed in
        chunks by ``requests`` so we never buffer the (up to ~3 MB) binary
        blobs in memory. Raises on non-2xx responses.
        """
        logger.info("Starting OTA update on %s (%s)", self.base_url, filename)
        try:
            resp = requests.post(
                f"{self.base_url}/update",
                files={"update": (filename, fileobj, "application/octet-stream")},
                timeout=timeout,
            )
            resp.raise_for_status()
        except Exception as e:
            logger.error("OTA update to %s failed: %s", self.base_url, e)
            raise
        logger.info("OTA update to %s completed: %d", self.base_url, resp.status_code)
        return {"status": "ok", "code": resp.status_code, "body": resp.text}


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
            "current": "cloud_cover,temperature_2m",
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
            return {"cloud_cover": "cloudy", "rain_forecast": "no", "temperature": None}

    @staticmethod
    def _parse(data: dict) -> dict:
        current = data.get("current", {})
        daily = data.get("daily", {})

        raw_cloud = current.get("cloud_cover", 100)
        raw_precip = (daily.get("precipitation_sum", [0]) or [0])[0]
        raw_temp = current.get("temperature_2m")

        return {
            "cloud_cover": "cloudy" if raw_cloud >= 50 else "clear",
            "rain_forecast": "yes" if raw_precip > 0 else "no",
            "temperature": raw_temp,
        }
