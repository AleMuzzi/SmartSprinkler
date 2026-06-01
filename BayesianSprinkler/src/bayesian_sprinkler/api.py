import logging
import time
from contextlib import asynccontextmanager
from threading import Lock

import yaml
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from bayesian_sprinkler.bayesian_network import SmartSprinklerBN
from bayesian_sprinkler.database import init_db, insert_record
from bayesian_sprinkler.sensor_client import ESP32Client, WeatherClient

logger = logging.getLogger(__name__)


class AppState:
    def __init__(self):
        self.config: dict | None = None
        self.bn: SmartSprinklerBN | None = None
        self.esp: ESP32Client | None = None
        self.weather: WeatherClient | None = None
        self.lock = Lock()
        self.scheduler: BackgroundScheduler | None = None
        self._cached_weather: dict = {
            "cloud_cover": "cloudy",
            "rain_forecast": "no",
            "temperature": None,
        }


state = AppState()

POLL_INTERVALS = {
    "low": 60,
    "medium": 30,
    "high": 15,
}
DEFAULT_INTERVAL = 30


# ── Request / Response models ────────────────────────────────────────

class ManualWaterRequest(BaseModel):
    plant_type: str


class EvidenceNode(BaseModel):
    label: str
    score: int
    icon: str


class PlantStatus(BaseModel):
    plant_id: str
    probability_of_need: float
    evidence_nodes: list[EvidenceNode]


class WeatherResponse(BaseModel):
    temperature: float | None
    humidity: float | None
    cloud_cover: str
    rain_forecast: str


class PlantStatusResponse(BaseModel):
    plants: list[PlantStatus]


# ── Lifespan ────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    state.scheduler = BackgroundScheduler()
    _schedule_hourly_poll(state, interval_minutes=60)
    state.scheduler.add_job(
        func=lambda: _poll_weather(state),
        trigger=IntervalTrigger(seconds=30),
        id="weather_poll",
        replace_existing=True,
    )
    poll_s = state.config["esp"]["poll_interval"]
    state.scheduler.add_job(
        func=lambda: _inference_cycle(state),
        trigger="interval",
        seconds=poll_s,
        id="inference_cycle",
        replace_existing=True,
    )
    state.scheduler.start()
    _poll_weather(state)
    logger.info("API server started — scheduler running")
    yield
    if state.scheduler:
        state.scheduler.shutdown(wait=False)
    logger.info("API server stopped")


def _schedule_hourly_poll(st: AppState, interval_minutes: int):
    st.scheduler.add_job(
        func=lambda: _hourly_poll(st),
        trigger=IntervalTrigger(minutes=interval_minutes),
        id="hourly_poll",
        replace_existing=True,
    )


# ── App factory ─────────────────────────────────────────────────────

def create_app(config: dict) -> FastAPI:
    state.config = config
    state.bn = SmartSprinklerBN(config["plants"])
    state.esp = ESP32Client(
        base_url=config["esp"]["base_url"],
        thresholds=config["thresholds"],
    )
    state.weather = WeatherClient(
        latitude=config["weather"]["latitude"],
        longitude=config["weather"]["longitude"],
        cloud_threshold=config["weather"]["cloud_cover_threshold"],
    )
    app = FastAPI(lifespan=lifespan, title="BayesianSprinkler")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    _register_routes(app)
    return app


def _build_evidence_nodes(soil: str, temp: str, humid: str, cloud: str, rain: str) -> list[EvidenceNode]:
    soil_score = {"dry": 100, "moist": 30, "wet": 0}[soil]
    temp_score = {"high": 80, "medium": 40, "low": 0}[temp]
    humid_score = {"low": 60, "medium": 30, "high": 0}[humid]
    cloud_score = {"clear": 50, "cloudy": 0}[cloud]
    rain_score = {"no": 20, "yes": -60}[rain]

    return [
        EvidenceNode(label="Soil Moisture", score=soil_score, icon="water_drop"),
        EvidenceNode(label="Temperature", score=temp_score, icon="thermostat"),
        EvidenceNode(label="Humidity", score=humid_score, icon="air"),
        EvidenceNode(label="Cloud Cover", score=cloud_score, icon="cloud"),
        EvidenceNode(label="Rain Forecast", score=rain_score, icon="cloudy_snowing"),
    ]


def _poll_weather(st: AppState):
    try:
        st._cached_weather = st.weather.fetch()
    except Exception:
        logger.warning("Weather fetch failed — keeping previous cache")


def _register_routes(app: FastAPI):
    @app.post(
        "/api/plants/manual-water",
        tags=["Plants"],
        summary="Trigger manual watering for a plant",
        responses={
            200: {"description": "Watering triggered successfully"},
            422: {"description": "Unknown plant type"},
            503: {"description": "Water level low — blocked"},
        },
    )
    def manual_water(req: ManualWaterRequest):
        if req.plant_type not in state.config["plants"]:
            raise HTTPException(422, f"Unknown plant: {req.plant_type}")

        status = state.esp.get_status()
        wx = state.weather.fetch()
        cfg = state.config["plants"][req.plant_type]

        soil = state.esp.discretize_soil_moisture(float(status["soil_moisture"]))
        temp = state.esp.discretize_temperature(float(status["air_temperature"]))
        humid = state.esp.discretize_humidity(float(status["air_humidity"]))

        for p in state.config["plants"]:
            need = "yes" if p == req.plant_type else "no"
            insert_record(
                plant_type=p,
                soil_moisture=soil,
                air_temperature=temp,
                air_humidity=humid,
                cloud_cover=wx["cloud_cover"],
                rain_forecast=wx["rain_forecast"],
                need_water=need,
            )

        if status.get("water_low_alert") == "on":
            logger.warning("Water low alert — blocked watering for %s", req.plant_type)
            raise HTTPException(
                503,
                f"Water level low — blocked. Use force=true to override."
            )

        logger.info("Manual water triggered for %s — logging snapshot", req.plant_type)
        state.esp.start_watering(cfg["esp_target"])
        time.sleep(cfg["watering_duration"])
        state.esp.stop_watering(cfg["esp_target"])

        return {"status": "ok", "plant": req.plant_type}

    @app.get(
        "/api/health",
        tags=["System"],
        summary="Health check",
        responses={200: {"description": "Server is healthy"}},
    )
    def health():
        return {"status": "ok"}

    @app.get(
        "/api/plants/status",
        response_model=PlantStatusResponse,
        tags=["Plants"],
        summary="Get plant statuses with probability of need",
        responses={
            200: {"description": "Current status for all plants with evidence breakdown"},
        },
    )
    def get_plant_status():
        try:
            esp_status = state.esp.get_status()
        except Exception:
            esp_status = {}

        raw_soil = float(esp_status.get("soil_moisture", 0))
        raw_temp = float(esp_status.get("air_temperature", 25))
        raw_humid = float(esp_status.get("air_humidity", 50))

        soil = state.esp.discretize_soil_moisture(raw_soil)
        temp = state.esp.discretize_temperature(raw_temp)
        humid = state.esp.discretize_humidity(raw_humid)

        plants = []
        for plant_name in state.config["plants"]:
            with state.lock:
                prob = state.bn.query(
                    plant=plant_name,
                    temperature=temp,
                    humidity=humid,
                    cloud_cover=state._cached_weather["cloud_cover"],
                    soil_moisture=soil,
                    rain_forecast=state._cached_weather["rain_forecast"],
                )

            evidence_nodes = _build_evidence_nodes(soil, temp, humid, state._cached_weather["cloud_cover"], state._cached_weather["rain_forecast"])

            plants.append(PlantStatus(
                plant_id=plant_name,
                probability_of_need=round(prob, 2),
                evidence_nodes=evidence_nodes,
            ))

        return PlantStatusResponse(plants=plants)

    @app.get(
        "/api/weather/status",
        response_model=WeatherResponse,
        tags=["Weather"],
        summary="Get current weather data",
        responses={
            200: {"description": "Current weather conditions"},
        },
    )
    def get_weather_status():
        try:
            esp_status = state.esp.get_status()
        except Exception:
            esp_status = {}

        raw_humid = float(esp_status.get("air_humidity", 50))

        return WeatherResponse(
            temperature=state._cached_weather.get("temperature"),
            humidity=raw_humid,
            cloud_cover=state._cached_weather["cloud_cover"],
            rain_forecast=state._cached_weather["rain_forecast"],
        )


# ── Background jobs ─────────────────────────────────────────────────

def _hourly_poll(st: AppState):
    temperature_fallback = None

    try:
        status = st.esp.get_status()
        raw_temp = float(status["air_temperature"])
    except Exception:
        logger.warning("ESP offline — falling back to weather API for temperature")
        try:
            wx = st.weather.fetch()
            raw_temp = wx.get("temperature")
        except Exception:
            raw_temp = None

    if raw_temp is None:
        logger.warning(
            "No temperature source available — "
            "using safe default interval of %d minutes",
            DEFAULT_INTERVAL,
        )
        _reschedule_poll(st, DEFAULT_INTERVAL, None)
        _log_and_insert(st, {"cloud_cover": "cloudy", "rain_forecast": "no"})
        return

    temp_state = _temperature_state(raw_temp, st.config["thresholds"]["temperature"])
    interval = POLL_INTERVALS.get(temp_state, DEFAULT_INTERVAL)

    logger.info(
        "Current temperature is %.1f°C (%s): "
        "adjusting polling interval to %d minutes.",
        raw_temp, temp_state, interval,
    )

    _reschedule_poll(st, interval, raw_temp)

    try:
        wx = st.weather.fetch()
    except Exception:
        wx = {"cloud_cover": "cloudy", "rain_forecast": "no"}

    _log_and_insert(st, wx)


def _temperature_state(temp_celsius: float, thresholds: dict) -> str:
    if temp_celsius < thresholds["low"]:
        return "low"
    if temp_celsius < thresholds["medium"]:
        return "medium"
    return "high"


def _reschedule_poll(st: AppState, interval_minutes: int, temperature: float | None):
    with st.lock:
        existing = st.scheduler.get_job("hourly_poll")
        if existing:
            st.scheduler.modify_job(
                "hourly_poll",
                trigger=IntervalTrigger(minutes=interval_minutes),
            )
        else:
            _schedule_hourly_poll(st, interval_minutes)


def _log_and_insert(st: AppState, wx: dict):
    try:
        status = st.esp.get_status()
        soil = st.esp.discretize_soil_moisture(float(status["soil_moisture"]))
        temp = st.esp.discretize_temperature(float(status["air_temperature"]))
        humid = st.esp.discretize_humidity(float(status["air_humidity"]))
    except Exception:
        logger.warning("ESP offline during hourly poll — using weather-only defaults")
        soil = st.esp.discretize_soil_moisture(0.0)
        temp = "medium"
        humid = "medium"

    try:
        for plant_name in st.config["plants"]:
            insert_record(
                plant_type=plant_name,
                soil_moisture=soil,
                air_temperature=temp,
                air_humidity=humid,
                cloud_cover=wx["cloud_cover"],
                rain_forecast=wx["rain_forecast"],
                need_water="no",
            )
        logger.info("Hourly poll: logged %d plants (need_water=no)",
                    len(st.config["plants"]))
    except Exception:
        logger.exception("Hourly poll failed")


def _inference_cycle(st: AppState):
    try:
        status = st.esp.get_status()
        wx = st.weather.fetch()
        pump_on = status["water_pump"] == "on"

        logger.info(
            "Inference cycle — soil: %s%%, temp: %s°C, humidity: %s%%  |  "
            "sky: %s, rain: %s  |  pump: %s",
            status["soil_moisture"], status["air_temperature"],
            status["air_humidity"], wx["cloud_cover"],
            wx["rain_forecast"], status["water_pump"],
        )

        soil = st.esp.discretize_soil_moisture(float(status["soil_moisture"]))
        temp = st.esp.discretize_temperature(float(status["air_temperature"]))
        humid = st.esp.discretize_humidity(float(status["air_humidity"]))

        for plant_name, cfg in st.config["plants"].items():
            with st.lock:
                prob = st.bn.query(
                    plant=plant_name,
                    temperature=temp,
                    humidity=humid,
                    cloud_cover=wx["cloud_cover"],
                    soil_moisture=soil,
                    rain_forecast=wx["rain_forecast"],
                )
            threshold = cfg["threshold"]
            will_water = prob > threshold and not pump_on

            logger.info(
                "  %s → P=%.2f (thresh=%.2f)%s",
                cfg["display_name"], prob, threshold,
                "  ✓ WATERING" if will_water else "",
            )

            if will_water and status.get("water_low_alert") != "on":
                st.esp.start_watering(cfg["esp_target"])
                time.sleep(cfg["watering_duration"])
                st.esp.stop_watering(cfg["esp_target"])
            elif will_water:
                logger.info("  Skipped — water low alert active")
    except Exception:
        logger.exception("Inference cycle failed")