import logging
import time
import traceback
from contextlib import asynccontextmanager
from datetime import datetime
from threading import Lock

import yaml
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from bayesian_sprinkler.audit_log import init_audit_table, log_event, get_log_entries, delete_log_entries
from bayesian_sprinkler.bayesian_network import SmartSprinklerBN
from bayesian_sprinkler.database import init_db, insert_record
from bayesian_sprinkler.local_time import configure as configure_timezone
from bayesian_sprinkler.local_time import now as now_local
from bayesian_sprinkler.notifier import send_email_alert
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
        # Latest ESP status payload, pushed by the ESP via
        # POST /api/esp/status. The server NEVER pulls from the ESP anymore
        # — this is the single source of truth for the app.
        self._esp_status: dict = {}
        self._esp_status_updated_at: datetime | None = None
        self._cached_weather: dict = {
            "cloud_cover": "cloudy",
            "rain_forecast": "no",
            "temperature": None,
        }
        self._water_low_alert: bool = False
        self._cistern_level_ml: float = 30000.0  # default; reset by create_app from config
        self._last_watered_doses: dict[str, float] = {}


state = AppState()

# Maximum accepted firmware image size for POST /api/esp/ota. Slightly above
# the ~1.75MB OTA slot so a full valid image always passes.
OTA_MAX_BYTES = 1_800_000


def _plant_soil_thresholds(plant_cfg: dict) -> dict:
    """Per-plant soil-moisture discretisation bounds.

    Each plant may set ``soil_moisture_thresholds: {dry: .., moist: ..}`` so
    the raw sensor % maps to the BN states ``dry`` / ``moist`` / ``wet``
    differently per plant (e.g. drought-tolerant rosemary only counts as
    "dry" below 10 %). Unset keys fall back to the global
    ``thresholds.soil_moisture`` values.
    """
    plant = plant_cfg.get("soil_moisture_thresholds") or {}
    global_sm = state.config.get("thresholds", {}).get("soil_moisture", {})
    return {
        "dry": plant.get("dry", global_sm.get("dry", 35)),
        "moist": plant.get("moist", global_sm.get("moist", 60)),
    }


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
    threshold: float
    soil_moisture: float | None
    evidence_nodes: list[EvidenceNode]


class WeatherResponse(BaseModel):
    temperature: float | None
    humidity: float | None
    cloud_cover: str
    rain_forecast: str


class PlantStatusResponse(BaseModel):
    plants: list[PlantStatus]


class DashboardResponse(BaseModel):
    esp: dict
    esp_healthy: bool
    water_low_alert: bool
    plants: list[PlantStatus]
    weather: WeatherResponse
    pump_on: bool


# ── Lifespan ────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    init_audit_table()
    state.scheduler = BackgroundScheduler()
    state.scheduler.add_job(
        func=lambda: _poll_weather(state),
        trigger=IntervalTrigger(minutes=30),
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
    _inference_cycle(state)
    logger.info("API server started — scheduler running")
    yield
    if state.scheduler:
        state.scheduler.shutdown(wait=False)
    logger.info("API server stopped")


def create_app(config: dict) -> FastAPI:
    state.config = config
    configure_timezone(config.get("timezone", "Europe/Rome"))
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
    # Cistern starts full. The state survives across inference cycles; the
    # simulation engine keeps its own copy.
    state._cistern_level_ml = float(config.get("cistern_capacity_ml", 30000))
    app = FastAPI(lifespan=lifespan, title="BayesianSprinkler")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ],
        # Also accept any RFC1918 private-network host so the web UI works
        # from phones / tablets on the LAN without editing this list every
        # time the router hands out a new IP. Public origins still need to
        # be added to ``allow_origins`` explicitly.
        allow_origin_regex=(
            r"^http://("
            r"localhost|127\.0\.0\.1"
            r"|10\.\d{1,3}\.\d{1,3}\.\d{1,3}"
            r"|192\.168\.\d{1,3}\.\d{1,3}"
            r"|172\.(1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3}"
            r")(:\d+)?$"
        ),
        # The ESP firmware is the one pushing to POST /api/esp/status; it
        # doesn't send an Origin header so we add a wildcard for the
        # status push endpoint specifically via the per-route allow below.
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    _register_routes(app)

    # Mount the interactive simulation router (optional: silently no-op if
    # the engine module is missing — e.g. slim production builds).
    try:
        from bayesian_sprinkler.simulation_router import create_router
        app.include_router(create_router())
    except Exception:  # pragma: no cover
        logger.exception("Failed to mount simulation router")

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


def _to_float(value) -> float | None:
    """Coerce a value to ``float``, tolerating the text payloads the ESP
    serialises (e.g. ``"21.5"``, ``"nan"``, ``"undef"``). Returns ``None``
    when the value is missing or not a usable number so callers can
    fall back to cached weather instead of crashing on a ``<`` compare.
    """
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        text = value.strip().lower()
        if text in ("", "nan", "null", "none", "undef", "-"):
            return None
        try:
            return float(value.strip())
        except (ValueError, TypeError):
            return None
    return None


def _register_routes(app: FastAPI):
    @app.get(
        "/api/cistern",
        tags=["Cistern"],
        summary="Current cistern level estimate",
    )
    def cistern_status() -> dict:
        capacity = float(state.config.get("cistern_capacity_ml", 30000))
        level = float(state._cistern_level_ml)
        pct = (level / capacity * 100.0) if capacity > 0 else 0.0
        return {
            "level_ml": level,
            "capacity_ml": capacity,
            "level_pct": round(pct, 1),
            "water_low_alert": state._water_low_alert,
        }

    @app.post(
        "/api/cistern/refill",
        tags=["Cistern"],
        summary=(
            "Force the cistern estimate back to full. Mirrors what happens "
            "automatically when the water_low_alert sensor transitions from "
            "on → off. Useful for ops/testing without physically refilling."
        ),
    )
    def cistern_refill() -> dict:
        capacity = float(state.config.get("cistern_capacity_ml", 30000))
        previous_level = float(state._cistern_level_ml)
        state._cistern_level_ml = capacity
        # Also clear the alert since the cistern is now full.
        state._water_low_alert = False
        logger.info(
            "Cistern manually refilled: %.0f mL → %.0f mL", previous_level, capacity
        )
        log_event(
            "alert",
            "Cistern manually refilled",
            details=(
                f"previous_level={previous_level:.0f}mL "
                f"new_level={capacity:.0f}mL (manual override via API)"
            ),
        )
        return {
            "level_ml": state._cistern_level_ml,
            "capacity_ml": capacity,
            "refilled_from_ml": previous_level,
        }

    @app.get(
        "/api/esp/status",
        tags=["ESP"],
        summary=(
            "Last ESP status payload observed by the server. The server "
            "already reads the ESP during its scheduled inference cycles, "
            "so this is the most recent snapshot — no extra polling. The "
            "mobile app should call this endpoint instead of hitting the "
            "ESP directly."
        ),
    )
    def esp_status() -> dict:
        payload = dict(state._esp_status)
        payload["server_received_at"] = (
            state._esp_status_updated_at.isoformat() + "Z"
            if state._esp_status_updated_at else None
        )
        return payload

    @app.get(
        "/api/esp/version",
        tags=["ESP"],
        summary="ESP firmware version (relayed from GET /health)",
        responses={
            200: {"description": "Firmware version as reported by the ESP"},
        },
    )
    def esp_firmware_version():
        version = state.esp.get_firmware_version()
        return {"version": version if version is not None else "-"}

    @app.post(
        "/api/esp/ota",
        tags=["ESP"],
        summary="Upload a firmware image and stream it to the ESP",
        responses={
            200: {"description": "Firmware flashed successfully"},
            400: {"description": "Invalid file (extension or size)"},
            502: {"description": "ESP unreachable or upload failed"},
        },
    )
    def esp_ota(file: UploadFile = File(...)):
        if not (file.filename or "").lower().endswith(".bin"):
            raise HTTPException(400, "Expected a .bin firmware image")
        if file.size and file.size > OTA_MAX_BYTES:
            raise HTTPException(400, f"Firmware too large (max {OTA_MAX_BYTES} bytes)")
        try:
            state.esp.ota_update(file.filename or "firmware.bin", file.file)
        except Exception as e:
            logger.error("OTA upload to ESP failed: %s", e)
            log_event("ota", "Firmware update failed",
                      details=f"filename={file.filename} error={e}")
            raise HTTPException(502, f"ESP unreachable or update failed: {e}")
        log_event("ota", "Firmware update completed",
                  details=f"filename={file.filename}")
        return {"status": "ok", "filename": file.filename}

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
        _capture_esp_status(state, status)
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
            log_event("command", f"Manual watering blocked: {cfg['display_name']}",
                      details=f"reason=water_low_alert")
            raise HTTPException(
                503,
                f"Water level low — blocked. Use force=true to override."
            )

        logger.info("Manual water triggered for %s — logging snapshot", req.plant_type)
        state.esp.start_watering(cfg["esp_target"])
        time.sleep(cfg["watering_duration"])
        state.esp.stop_watering(cfg["esp_target"])
        log_event("command", f"Manual watering: {cfg['display_name']}",
                  details=f"target={cfg['esp_target']} duration={cfg['watering_duration']}s")

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
        "/api/audit-log",
        tags=["System"],
        summary="Audit log of inferences and ESP commands",
        responses={200: {"description": "Audit log entries (newest first)"}},
    )
    def audit_log(
        filter: str | None = None,
        category: str | None = None,
        limit: int = 200,
        start_date: str | None = None,
        end_date: str | None = None,
    ):
        from fastapi import Query
        rows = get_log_entries(
            filter_text=filter,
            category=category,
            limit=limit,
            start_date=start_date,
            end_date=end_date,
        )
        return {
            "entries": [
                {
                    "id": row["id"],
                    "timestamp": row["timestamp"],
                    "category": row["category"],
                    "message": row["message"],
                    "details": row["details"],
                }
                for row in rows
            ],
            "count": len(rows),
            "filter": filter,
            "category": category,
        }

    @app.delete(
        "/api/audit-log",
        tags=["System"],
        summary="Clear audit log entries",
        description=(
            "Deletes all entries matching the optional date range "
            "(start_date / end_date, format YYYY-MM-DD, inclusive). "
            "Without a date range the whole log is cleared."
        ),
    )
    def audit_log_clear(
        start_date: str | None = None,
        end_date: str | None = None,
    ):
        deleted = delete_log_entries(start_date=start_date, end_date=end_date)
        return {"status": "ok", "deleted": deleted}

    @app.get(
        "/api/audit-log/export",
        tags=["System"],
        summary="Download audit log as CSV",
        responses={
            200: {
                "description": "CSV file",
                "content": {"text/csv": {}},
            },
        },
    )
    def audit_log_export(
        filter: str | None = None,
        category: str | None = None,
    ):
        from fastapi.responses import StreamingResponse
        rows = get_log_entries(filter_text=filter, category=category, limit=1_000_000)
        import csv
        import io

        def csv_gen():
            buf = io.StringIO()
            writer = csv.writer(buf)
            writer.writerow(["id", "timestamp", "category", "message", "details"])
            yield buf.getvalue()
            buf.seek(0)
            buf.truncate()
            for row in rows:
                writer.writerow([
                    row["id"],
                    row["timestamp"],
                    row["category"],
                    row["message"],
                    row["details"] or "",
                ])
                yield buf.getvalue()
                buf.seek(0)
                buf.truncate()

        from datetime import datetime
        filename = f"audit_log_{now_local().strftime('%Y%m%d_%H%M%S')}.csv"
        return StreamingResponse(
            csv_gen(),
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

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
            _capture_esp_status(state, esp_status)
        except Exception:
            esp_status = {}

        raw_soil = _to_float(esp_status.get("soil_moisture")) if esp_status else None
        raw_temp = _to_float(esp_status.get("air_temperature")) if esp_status else None
        raw_humid = _to_float(esp_status.get("air_humidity")) if esp_status else None
        if raw_soil is None:
            raw_soil = 0
        if raw_temp is None:
            raw_temp = 25
        if raw_humid is None:
            raw_humid = 50

        soil = state.esp.discretize_soil_moisture(raw_soil)
        temp = state.esp.discretize_temperature(raw_temp)
        humid = state.esp.discretize_humidity(raw_humid)

        plants = []
        for plant_name in state.config["plants"]:
            sensor_idx = state.config["plants"][plant_name].get("sensor_index", 0)
            raw_sm = esp_status.get(f"soil_moisture_{sensor_idx}") if esp_status else None
            plant_sm = _to_float(raw_sm)
            if plant_sm is None:
                plant_sm = raw_soil
            plant_soil = state.esp.discretize_soil_moisture(
                plant_sm, _plant_soil_thresholds(
                    state.config["plants"][plant_name]))

            with state.lock:
                prob = state.bn.query(
                    plant=plant_name,
                    temperature=temp,
                    humidity=humid,
                    cloud_cover=state._cached_weather["cloud_cover"],
                    soil_moisture=plant_soil,
                    rain_forecast=state._cached_weather["rain_forecast"],
                )

            evidence_nodes = _build_evidence_nodes(plant_soil, temp, humid, state._cached_weather["cloud_cover"], state._cached_weather["rain_forecast"])

            plants.append(PlantStatus(
                plant_id=plant_name,
                probability_of_need=round(prob, 2),
                threshold=state.config["plants"][plant_name].get("threshold", 0.5),
                soil_moisture=plant_sm,
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
        raw_temp = None
        raw_humid = None

        try:
            esp_status = state.esp.get_status()
            _capture_esp_status(state, esp_status)
            raw_temp = _to_float(esp_status.get("air_temperature"))
            raw_humid = _to_float(esp_status.get("air_humidity"))
        except Exception:
            pass

        # Fall back to the cached weather forecast when the ESP didn't
        # report usable values. Only return None if BOTH sources are empty
        # so the UI can show "--" instead of misleading fake numbers.
        if raw_temp is None or raw_temp < 0:
            raw_temp = _to_float(state._cached_weather.get("temperature"))
        if raw_humid is None or raw_humid < 0:
            raw_humid = _to_float(state._cached_weather.get("humidity"))

        return WeatherResponse(
            temperature=raw_temp,
            humidity=raw_humid,
            cloud_cover=state._cached_weather["cloud_cover"],
            rain_forecast=state._cached_weather["rain_forecast"],
        )

    @app.get(
        "/api/dashboard",
        response_model=DashboardResponse,
        tags=["Dashboard"],
        summary="Combined ESP + plants + weather in one request",
        responses={200: {"description": "Combined dashboard data"}},
    )
    def get_dashboard():
        esp_status = {}
        pump_on = False
        esp_healthy = False
        try:
            esp_status = state.esp.get_status()
            _capture_esp_status(state, esp_status)
            pump_on = esp_status.get("water_pump") == "on"
            esp_healthy = True
        except Exception:
            pass

        raw_soil_avg = _to_float(esp_status.get("soil_moisture")) if esp_status else 0
        raw_temp = _to_float(esp_status.get("air_temperature")) if esp_status else None
        raw_humid = _to_float(esp_status.get("air_humidity")) if esp_status else None
        if raw_soil_avg is None:
            raw_soil_avg = 0
        if raw_temp is None:
            raw_temp = 25
        if raw_humid is None:
            raw_humid = 50

        if raw_temp < 0:
            raw_temp = _to_float(state._cached_weather.get("temperature")) or 25.0
        if raw_humid < 0:
            raw_humid = 50.0

        temp = state.esp.discretize_temperature(raw_temp)
        humid = state.esp.discretize_humidity(raw_humid)

        plants = []
        for plant_name in state.config["plants"]:
            sensor_idx = state.config["plants"][plant_name].get("sensor_index", 0)
            raw_sm = esp_status.get(f"soil_moisture_{sensor_idx}") if esp_status else None
            plant_sm = _to_float(raw_sm)
            if plant_sm is None:
                plant_sm = raw_soil_avg
            plant_soil = state.esp.discretize_soil_moisture(
                plant_sm, _plant_soil_thresholds(
                    state.config["plants"][plant_name]))

            with state.lock:
                prob = state.bn.query(
                    plant=plant_name,
                    temperature=temp,
                    humidity=humid,
                    cloud_cover=state._cached_weather["cloud_cover"],
                    soil_moisture=plant_soil,
                    rain_forecast=state._cached_weather["rain_forecast"],
                )
            evidence_nodes = _build_evidence_nodes(
                plant_soil, temp, humid,
                state._cached_weather["cloud_cover"],
                state._cached_weather["rain_forecast"],
            )
            plants.append(PlantStatus(
                plant_id=plant_name,
                probability_of_need=round(prob, 2),
                threshold=state.config["plants"][plant_name].get("threshold", 0.5),
                soil_moisture=plant_sm,
                evidence_nodes=evidence_nodes,
            ))

        return DashboardResponse(
            esp=esp_status,
            esp_healthy=esp_healthy,
            water_low_alert=esp_status.get("water_low_alert") == "on",
            plants=plants,
            weather=WeatherResponse(
                temperature=state._cached_weather.get("temperature"),
                humidity=raw_humid,
                cloud_cover=state._cached_weather["cloud_cover"],
                rain_forecast=state._cached_weather["rain_forecast"],
            ),
            pump_on=pump_on,
        )


# ── Background jobs ─────────────────────────────────────────────────


def _inference_cycle(st: AppState):
    try:
        status = st.esp.get_status()
        _capture_esp_status(st, status)
        _run_inference_with_status(st, status)
    except Exception as e:
        tb = traceback.format_exc()
        logger.exception("Inference cycle failed")
        log_event("error", f"Inference cycle failed: {e}", details=tb)


# Hard, model-independent floor on watering pulse volume. Any dose the BN
# recommends below this is dropped before the ESP command is sent, so we
# never spin the pump for a dribble that doesn't move the soil needle.
# Lives in api.py (not bayesian_network.py) on purpose: this is a
# hardware-level constraint, not part of the probabilistic model.
# 115 mL ≈ 5 s at 1380 mL/min — the previous floor.
_MIN_DOSE_ML = 115.0


def _watering_allowed(plant_cfg: dict, hour: int, st: AppState | None = None) -> bool:
    """Return True if the plant may be watered at the given hour.

    The allowed hours are configured globally in ``config.yaml`` at the root
    level as ``watering_allowed_hours``. They apply uniformly to every plant
    in the system. Per-plant overrides are no longer supported.

    If neither ``st.config["watering_allowed_hours"]`` nor the per-plant
    field is set, falls back to a sensible default (night/morning/evening,
    excluding 11-16).
    """
    allowed: list[int] | None = None
    if st is not None and st.config is not None:
        allowed = st.config.get("watering_allowed_hours")
    if allowed is None:
        allowed = plant_cfg.get("watering_allowed_hours")  # legacy fallback
    if allowed is None:
        allowed = list(range(0, 11)) + list(range(17, 24))
    return hour in allowed


def _capture_esp_status(st: AppState, status: dict) -> None:
    """Cache the latest ESP payload so ``GET /api/esp/status`` can serve it
    without re-polling the device. The server already reads the ESP for
    inference / manual watering, so we just remember what we saw.
    """
    # Coerce string numerics (the ESP serialises everything as text).
    normalised: dict = {}
    for key, value in status.items():
        if isinstance(value, str):
            try:
                if "." in value:
                    normalised[key] = float(value)
                else:
                    normalised[key] = int(value)
                continue
            except (ValueError, TypeError):
                pass
        normalised[key] = value
    st._esp_status = normalised
    st._esp_status_updated_at = datetime.utcnow()


def _run_inference_with_status(st: AppState, status: dict) -> dict[str, float]:
    """Run inference using a pre-fetched status dict.

    Shared between the scheduled inference cycle and simulations/tests that
    supply their own status snapshot (e.g. a mock ESP).

    Returns
    -------
    dict[str, float]
        ``{plant_name: dose_seconds}`` for the plants that were *actually*
        watered by THIS inference call. Plants skipped due to the hour-window
        block, ``will_water=False``, or pump-already-on are NOT included.
        The caller (e.g. ``SimulationEngine._step_locked``) uses this dict
        to apply the post-watering soil boost — using ``_last_watered_doses``
        for that is unsafe because it is a persistent dict that survives
        across calls.
    """
    triggered_doses: dict[str, float] = {}
    try:
        wx = st.weather.fetch()
        pump_on = status["water_pump"] == "on"

        water_low = status.get("water_low_alert") == "on"
        if water_low and not st._water_low_alert:
            # Off → On: low-alert just triggered. Email the user and log it.
            logger.warning("WATER LOW ALERT DETECTED!")
            cistern_capacity = st.config.get("cistern_capacity_ml", 30000)
            send_email_alert(
                st.config,
                subject="SmartSprinkler: Water Tank Low!",
                body=(
                    "The water tank is running low. Please refill the cistern. "
                    f"Estimated remaining: {st._cistern_level_ml:.0f} mL "
                    f"of {cistern_capacity:.0f} mL capacity."
                ),
            )
            log_event(
                "alert",
                "Water tank low alert triggered",
                details=(
                    f"ESP status: water_low_alert=on, "
                    f"estimated_level={st._cistern_level_ml:.0f}mL, "
                    f"capacity={cistern_capacity:.0f}mL"
                ),
            )
        elif not water_low and st._water_low_alert:
            # On → Off: cistern has been refilled. We assume it's filled to
            # full capacity (no partial refills — the user said so).
            cistern_capacity = st.config.get("cistern_capacity_ml", 30000)
            previous_level = st._cistern_level_ml
            st._cistern_level_ml = cistern_capacity
            logger.info(
                "Water tank refilled: %.0f mL → %.0f mL",
                previous_level, cistern_capacity,
            )
            log_event(
                "alert",
                "Water tank refilled",
                details=(
                    f"ESP status: water_low_alert=off, "
                    f"previous_level={previous_level:.0f}mL, "
                    f"new_level={cistern_capacity:.0f}mL"
                ),
            )
        st._water_low_alert = water_low

        raw_temp = _to_float(status.get("air_temperature"))
        raw_humid = _to_float(status.get("air_humidity"))
        if raw_temp is None or raw_temp < 0:
            # The ESP serialises readings as text ("nan", "undef", "21.5"…).
            # Fall back to the cached forecast before giving up, so a single
            # bad reading doesn't abort the whole cycle.
            raw_temp = _to_float(wx.get("temperature"))
        if raw_humid is None or raw_humid < 0:
            raw_humid = None
        if raw_temp is None:
            raise ValueError(
                f"Inference cycle: invalid air_temperature "
                f"{status.get('air_temperature')!r} and no usable fallback "
                f"(ESP/DHT invalid)"
            )
        if raw_humid is None:
            raise ValueError(
                f"Inference cycle: invalid air_humidity "
                f"{status.get('air_humidity')!r} (ESP/DHT invalid)"
            )
        temp = st.esp.discretize_temperature(raw_temp)
        humid = st.esp.discretize_humidity(raw_humid)

        sim_hour = status.get("_sim_hour")
        hour_now = int(sim_hour if sim_hour is not None else now_local().hour) % 24
        status["_hour_now"] = hour_now

        triggered_plants = []
        triggered_doses = {}
        blocked_by_hour = []
        bn_would_water = []
        status["_blocked_by_hour"] = blocked_by_hour
        for plant_name, cfg in st.config["plants"].items():
            sensor_idx = cfg.get("sensor_index", 0)
            raw_sm = status.get(f"soil_moisture_{sensor_idx}")
            plant_sm = _to_float(raw_sm)
            if plant_sm is None:
                plant_sm = _to_float(status.get("soil_moisture"))
            if plant_sm is None:
                plant_sm = 0.0
            soil = st.esp.discretize_soil_moisture(
                plant_sm, _plant_soil_thresholds(cfg))

            logger.info(
                "Inference cycle — %s: soil=%s (raw=%s), temp: %s°C, humidity: %s%%  |  "
                "sky: %s, rain: %s  |  pump: %s  |  hour=%02d",
                cfg["display_name"], soil, plant_sm, status.get("air_temperature"),
                status.get("air_humidity"), wx["cloud_cover"],
                wx["rain_forecast"], status.get("water_pump"), hour_now,
            )

            with st.lock:
                prob, dose_ml = st.bn.query_with_dose(
                    plant=plant_name,
                    temperature=temp,
                    humidity=humid,
                    cloud_cover=wx["cloud_cover"],
                    soil_moisture=soil,
                    rain_forecast=wx["rain_forecast"],
                    soil_value=plant_sm,
                    sim_hour=hour_now,
                )

            # Every plant snapshot is logged to SQLite so the sensor history
            # stays complete regardless of the watering hour window.
            threshold = cfg["threshold"]
            need = "yes" if prob >= threshold else "no"
            if need == "yes":
                bn_would_water.append(plant_name)
            insert_record(
                plant_type=plant_name,
                soil_moisture=soil,
                air_temperature=temp,
                air_humidity=humid,
                cloud_cover=wx["cloud_cover"],
                rain_forecast=wx["rain_forecast"],
                need_water=need,
            )

            if not _watering_allowed(cfg, hour_now, st=st):
                logger.info(
                    "  %s → hour=%02d not in allowed hours, skip (soil=%s)",
                    cfg["display_name"], hour_now, soil,
                )
                blocked_by_hour.append(plant_name)
                continue

            # Hard, model-independent floor on watering volume. Any pulse
            # below this is dropped — tiny dribbles waste pump cycles and
            # don't meaningfully move the soil-moisture needle. Floor is in
            # mL because that's the canonical unit; conversion to seconds
            # happens below.
            if 0 < dose_ml < _MIN_DOSE_ML:
                logger.info(
                    "  %s → dose %.1fmL below _MIN_DOSE_ML=%.0fmL, skip",
                    cfg["display_name"], dose_ml, _MIN_DOSE_ML,
                )
                log_event(
                    "inference",
                    f"Watering skipped (pulse too small): {cfg['display_name']}",
                    details=f"dose={dose_ml:.1f}mL min={_MIN_DOSE_ML}mL prob={prob:.2f}",
                )
                st._last_watered_doses.pop(plant_name, None)
                continue
            will_water = dose_ml > 0 and not pump_on

            # Convert mL → seconds at the pump's nominal flow rate so the
            # ESP command sleeps the right amount of time.
            flow_rate = float(st.config.get("flow_rate_ml_per_min", 1380.0))
            dose_seconds = dose_ml * 60.0 / flow_rate if dose_ml > 0 else 0.0

            logger.info(
                "  %s → P=%.2f (thresh=%.2f) dose=%.0fmL (%.2fs)%s",
                cfg["display_name"], prob, threshold, dose_ml, dose_seconds,
                "  ✓ WATERING" if will_water else "",
            )

            if will_water and status.get("water_low_alert") != "on":
                st.esp.start_watering(cfg["esp_target"])
                time.sleep(dose_seconds)
                st.esp.stop_watering(cfg["esp_target"])
                st._last_watered_doses[plant_name] = dose_ml
                triggered_doses[plant_name] = dose_ml
                # Track cistern water usage. Cap at 0 — the sensor (water_low_alert)
                # is the source of truth for "tank is empty"; we just keep the
                # estimate conservative.
                previous_level = st._cistern_level_ml
                st._cistern_level_ml = max(0.0, previous_level - dose_ml)
                cistern_capacity = st.config.get("cistern_capacity_ml", 30000)
                if st._cistern_level_ml != previous_level:
                    logger.debug(
                        "Cistern: %.0f → %.0f mL (−%.0f mL for %s)",
                        previous_level, st._cistern_level_ml, dose_ml, cfg["display_name"],
                    )
                log_event(
                    "command",
                    f"Watering triggered: {cfg['display_name']}",
                    details=(
                        f"target={cfg['esp_target']} dose={dose_ml:.0f}mL ({dose_seconds:.2f}s) "
                        f"prob={prob:.2f} threshold={threshold} hour={hour_now} "
                        f"cistern={st._cistern_level_ml:.0f}/{cistern_capacity:.0f}mL"
                    ),
                )
                triggered_plants.append(plant_name)
            else:
                st._last_watered_doses.pop(plant_name, None)
                if will_water and status.get("water_low_alert") == "on":
                    logger.info("  Skipped — water low alert active")
                    log_event("inference", f"Watering skipped (low water): {cfg['display_name']}",
                              details=f"prob={prob:.2f} threshold={threshold}")

        details = (f"plants={[c['display_name'] for c in st.config['plants'].values()]}; "
                   f"soil_moisture={status['soil_moisture']}; "
                   f"air_temp={status['air_temperature']}; air_humid={status['air_humidity']}; "
                   f"cloud_cover={wx['cloud_cover']}; rain={wx['rain_forecast']}; "
                   f"hour={hour_now}; watered={triggered_plants}; "
                   f"hour_blocked={blocked_by_hour}; bn_would_water={bn_would_water}")
        log_event("inference", f"Inference cycle completed ({len(triggered_plants)} watered)",
                  details=details)
    except Exception as e:
        tb = traceback.format_exc()
        logger.exception("Inference cycle failed")
        log_event("error", f"Inference cycle failed: {e}", details=tb)
    return triggered_doses