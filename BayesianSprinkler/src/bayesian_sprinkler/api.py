import logging
import time
from contextlib import asynccontextmanager
from threading import Lock

import yaml
from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI, HTTPException
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


state = AppState()


# ── Request models ──────────────────────────────────────────────────

class ManualWaterRequest(BaseModel):
    plant_type: str


# ── Lifespan ────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    state.scheduler = BackgroundScheduler()
    _schedule_jobs(state)
    state.scheduler.start()
    logger.info("API server started — scheduler running")
    yield
    if state.scheduler:
        state.scheduler.shutdown(wait=False)
    logger.info("API server stopped")


def _schedule_jobs(st: AppState):
    st.scheduler.add_job(
        func=lambda: _hourly_poll(st),
        trigger="interval",
        hours=1,
        id="hourly_poll",
        replace_existing=True,
    )
    poll_s = st.config["esp"]["poll_interval"]
    st.scheduler.add_job(
        func=lambda: _inference_cycle(st),
        trigger="interval",
        seconds=poll_s,
        id="inference_cycle",
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
    _register_routes(app)
    return app


def _register_routes(app: FastAPI):
    @app.post("/api/plants/manual-water")
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

        logger.info("Manual water triggered for %s — logging snapshot", req.plant_type)
        state.esp.start_watering(cfg["esp_target"])
        time.sleep(cfg["watering_duration"])
        state.esp.stop_watering(cfg["esp_target"])

        return {"status": "ok", "plant": req.plant_type}

    @app.get("/api/health")
    def health():
        return {"status": "ok"}


# ── Background jobs ─────────────────────────────────────────────────

def _hourly_poll(st: AppState):
    try:
        status = st.esp.get_status()
        wx = st.weather.fetch()

        soil = st.esp.discretize_soil_moisture(float(status["soil_moisture"]))
        temp = st.esp.discretize_temperature(float(status["air_temperature"]))
        humid = st.esp.discretize_humidity(float(status["air_humidity"]))

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

            if will_water:
                st.esp.start_watering(cfg["esp_target"])
                time.sleep(cfg["watering_duration"])
                st.esp.stop_watering(cfg["esp_target"])
    except Exception:
        logger.exception("Inference cycle failed")
