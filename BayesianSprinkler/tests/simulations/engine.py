"""Shared simulation engine for SmartSprinkler.

Used by:
- tests/simulations/test_simulation.py (batch runs, generates reports)
- tests/simulations/gui.py (interactive GUI)

The engine drives a mock ESP and runs the Bayesian inference cycle, evolving
soil moisture, temperature, humidity and rain over simulated hours. It is
completely independent of pytest and HTTP — it can be driven step by step
from a Flask backend or in batch from a test.
"""

from __future__ import annotations

import json
import math
import random
import threading
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any

# Path of the directory containing user-facing configs (e.g. sunny_day.yaml).
TESTS_DIR = Path(__file__).resolve().parent
# tests/simulations/engine.py → tests/simulations/ → tests/ → BayesianSprinkler/
PROJECT_ROOT = TESTS_DIR.parent.parent
CONFIG_DIR = TESTS_DIR / "configs"


# ── Config loading ────────────────────────────────────────────────────────


def load_sim_config(config_path: Path | str | None = None) -> dict:
    """Load a simulation config (yaml) and merge it with the Bayesian project
    config (``config.yaml``) so the engine knows how each plant is configured.

    The merged config has the keys:

    - the original sim cfg (weather, evaporation, rain, ...)
    - ``plant_ids``: list of plant ids to include in the simulation
    - ``plants_cfg``: dict plant_id -> full Bayesian plant config
      (display_name, esp_target, sensor_index, base_need, threshold,
      watering_duration, watering_duration_min/max, watering_allowed_hours)
    """
    if config_path is None:
        candidates = [CONFIG_DIR / "sim_config.yaml", CONFIG_DIR / "default.yaml"]
        for c in candidates:
            if c.exists():
                config_path = c
                break
        if config_path is None:
            raise FileNotFoundError(f"No config found in {CONFIG_DIR}")
    config_path = Path(config_path)
    import yaml
    with open(config_path) as f:
        sim_cfg = yaml.safe_load(f)

    # Merge with Bayesian project config (for plant details).
    bayesian_cfg_path = PROJECT_ROOT / "config.yaml"
    with open(bayesian_cfg_path) as f:
        bayesian_cfg = yaml.safe_load(f)
    plants_defined = bayesian_cfg.get("plants", {})

    # ``plants`` in the sim cfg is a list of plant ids; resolve to full configs.
    plant_ids = sim_cfg.get("plants") or list(plants_defined.keys())
    sim_cfg["plant_ids"] = plant_ids
    sim_cfg["plants_cfg"] = {
        pid: {**plants_defined[pid]} for pid in plant_ids if pid in plants_defined
    }
    return sim_cfg


def list_available_configs() -> list[Path]:
    if not CONFIG_DIR.is_dir():
        return []
    return sorted(CONFIG_DIR.glob("*.yaml"))


# ── Mock ESP ─────────────────────────────────────────────────────────────


# Default soil moisture gain from a watering pulse. Modelled as percent of
# soil-moisture (0-100). Tuned so that in normal conditions soil moves from
# "dry" (<35%) back up to "moist" (35-65%) after one watering.
WATERING_BOOST_PERCENT = 30.0


class MockESPState:
    """Mutable state shared between the mock HTTP server and the sim engine.

    A single instance lives across the whole simulation; both the test
    batch runner and the GUI backend mutate it directly.
    """

    def __init__(self) -> None:
        self.soil_moisture_by_plant: dict[str, float] = {}
        self.air_temperature: float = 22.0
        self.air_humidity: float = 55.0
        self.water_low_alert: str = "off"
        self.blocked_amount_ml: int = 0
        self.water_pump: str = "off"
        self.active_plant: str = "null"
        self.watering_count: int = 0
        self.last_commands: list[dict] = []
        self.last_doses: dict[str, float] = {}  # new: per-plant dose of last water
        self.transcript: list[dict] = []       # new: lightweight event log
        # Cistern state. ``cistern_level_ml`` is decremented on each
        # watering. When it drops below ~10 % of capacity the engine flips
        # ``water_low_alert`` to "on" so the inference skips watering until
        # the user resets the alert (which the engine interprets as a full
        # refill).
        self.cistern_level_ml: float = 30000.0
        self._prev_water_low_alert: bool = False
        self.cistern_refill_count: int = 0
        self.cistern_low_count: int = 0


def reset_esp_state(state: MockESPState, plant_ids: list[str], initial_soil: float) -> None:
    state.soil_moisture_by_plant = {p: float(initial_soil) for p in plant_ids}
    state.air_temperature = 22.0
    state.air_humidity = 55.0
    state.water_low_alert = "off"
    state.blocked_amount_ml = 0
    state.water_pump = "off"
    state.active_plant = "null"
    state.watering_count = 0
    state.last_commands = []
    state.last_doses = {}
    state.transcript = []
    state.cistern_level_ml = float(state.cistern_level_ml) or 30000.0
    state._prev_water_low_alert = False
    state.cistern_refill_count = 0
    state.cistern_low_count = 0


class _MockESPHandler(BaseHTTPRequestHandler):
    """HTTP handler that serialises state for the Bayesian inference cycle.

    This is the same protocol the real ESP32 firmware implements.
    """

    state: MockESPState = MockESPState()

    def log_message(self, *_args):
        pass

    @classmethod
    def status_payload(cls) -> dict[str, Any]:
        s = cls.state
        plants = list(s.soil_moisture_by_plant.keys())
        avg = (
            sum(s.soil_moisture_by_plant.values()) / max(1, len(plants))
            if s.soil_moisture_by_plant else 50.0
        )
        payload: dict[str, Any] = {
            "status": "ok",
            "air_temperature": f"{s.air_temperature:.2f}",
            "air_humidity": f"{s.air_humidity:.2f}",
            "soil_moisture": f"{avg:.2f}",
            "water_pump": s.water_pump,
            "rotary_position": "1",
            "water_low_alert": s.water_low_alert,
            "blocked_amount_ml": str(s.blocked_amount_ml),
            "active_plant": s.active_plant,
        }
        for i, p in enumerate(plants):
            payload[f"soil_moisture_{i}"] = f"{s.soil_moisture_by_plant[p]:.2f}"
        return payload

    def do_GET(self):
        if self.path == "/status":
            body = json.dumps(self.status_payload()).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path != "/command":
            self.send_response(404)
            self.end_headers()
            return
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        cmd = json.loads(body)
        self._handle_command(cmd)
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"status":"ok"}')

    def _handle_command(self, cmd: dict) -> None:
        s = self.state
        action = cmd.get("action")
        target = cmd.get("target", "")
        s.last_commands.append(cmd)
        if action == "START":
            s.water_pump = "on"
            s.active_plant = target
        elif action == "STOP":
            s.water_pump = "off"
            s.active_plant = "null"


def apply_watering_effect(
    state: MockESPState,
    target_name: str,
    dose_ml: float,
    pot_capacity_ml: float = 500.0,
) -> None:
    """Apply the *side-effect* of a watering pulse to the mock soil.

    The dose is the volume of water the ESP delivered (in mL). The boost
    applied to the soil moisture reading is

        boost_percent = dose_ml / pot_capacity_ml × 100

    where ``pot_capacity_ml`` is the plant's configured "mL needed to lift
    soil by 100 %". With pot_capacity_ml=500 a 115 mL pulse → +23 % soil,
    matching the calibrated behaviour from before the mL refactor.
    """
    if target_name in state.soil_moisture_by_plant:
        current = state.soil_moisture_by_plant[target_name]
        boost = dose_ml / max(1e-9, pot_capacity_ml) * 100.0
        state.soil_moisture_by_plant[target_name] = min(100.0, current + boost)
    state.watering_count += 1
    state.last_doses[target_name] = dose_ml


# ── Weather, evaporation, soil dynamics ───────────────────────────────────


def temperature_at_hour(sim_cfg: dict, hour_in_day: int, rng: random.Random) -> float:
    cfg = sim_cfg["temperature"]
    cycle = (hour_in_day % 24) / 24.0
    base = cfg["min_celsius"] + (
        cfg["max_celsius"] - cfg["min_celsius"]
    ) * (1 - math.cos(cycle * 2 * math.pi)) / 2
    return base + rng.uniform(-cfg["noise_amplitude"], cfg["noise_amplitude"])


def humidity_at_hour(sim_cfg: dict, hour_temp: float, rng: random.Random) -> float:
    cfg = sim_cfg["humidity"]
    base = cfg["base_percent"] - cfg["per_degree_drop"] * max(0, hour_temp - 20)
    value = base + rng.uniform(-cfg["noise_amplitude"], cfg["noise_amplitude"])
    return max(5.0, min(99.0, value))


def probable_rain(sim_cfg: dict, hour: int, last_rain_hour: int, rng: random.Random) -> bool:
    cfg = sim_cfg["rain"]
    if hour - last_rain_hour < cfg["min_gap_hours"]:
        return False
    return rng.random() < cfg["probability_per_hour"]


# Realistic evaporation model:
#
#   loss(%) = base_loss × temp_boost × hum_boost × sky_boost × soil_factor
#
# where temp_boost/hum_boost/sky_boost amplify the base rate based on conditions,
# and ``soil_factor = current / 100`` makes dry soil lose less water than wet
# soil (first-order drying kinetics).
def evaporation_loss_percent(
    sim_cfg: dict,
    current_moisture: float,
    temperature: float,
    humidity: float,
    sky_clear: bool,
) -> float:
    cfg = sim_cfg["evaporation"]
    temp_boost = 1 + cfg["temperature_factor"] * max(0, temperature - 20)
    hum_boost = 1 + cfg["humidity_factor"] * max(0, 60 - humidity)
    sky_boost = 1 + cfg["cloud_factor"] if sky_clear else 1
    soil_factor = max(0.05, current_moisture / 100.0)  # never zero → never fully dry
    return cfg["base_loss_per_hour"] * temp_boost * hum_boost * sky_boost * soil_factor


# ── Main engine ───────────────────────────────────────────────────────────


@dataclass
class SimGUIEvent:
    """A single event published to the GUI during a step."""

    hour: int
    hour_of_day: int
    temperature: float
    humidity: float
    rain_event: bool
    sky: str  # "clear" / "cloudy"
    soil_by_plant: dict[str, float]
    avg_soil: float
    triggered: dict[str, float] = field(default_factory=dict)  # plant -> dose (mL)
    hour_blocked: list[str] = field(default_factory=list)
    inference_notes: list[str] = field(default_factory=list)
    flow_rate_ml_per_min: float | None = None
    cistern_level_ml: float | None = None
    cistern_capacity_ml: float | None = None
    cistern_water_low_alert: bool = False

    def to_public(self) -> dict:
        flow_rate = self.flow_rate_ml_per_min
        dose_seconds_by_plant = (
            {p: round(d * 60.0 / flow_rate, 2) for p, d in self.triggered.items()}
            if flow_rate
            else {}
        )
        return {
            "hour": self.hour,
            "hour_of_day": self.hour_of_day,
            "temperature": round(self.temperature, 2),
            "humidity": round(self.humidity, 2),
            "rain_event": self.rain_event,
            "sky": self.sky,
            "soil_by_plant": {p: round(v, 2) for p, v in self.soil_by_plant.items()},
            "avg_soil": round(self.avg_soil, 2),
            "triggered": {p: round(d, 1) for p, d in self.triggered.items()},  # mL
            "dose_seconds_by_plant": dose_seconds_by_plant,
            "flow_rate_ml_per_min": self.flow_rate_ml_per_min,
            "cistern_level_ml": self.cistern_level_ml,
            "cistern_capacity_ml": self.cistern_capacity_ml,
            "cistern_water_low_alert": self.cistern_water_low_alert,
            "hour_blocked": list(self.hour_blocked),
            "notes": list(self.inference_notes),
        }


class SimulationEngine:
    """Stateful, thread-safe simulation engine.

    Workflow:

    >>> engine = SimulationEngine.from_config(config_path)
    >>> engine.start()
    >>> while engine.running:
    ...     event = engine.step()
    ...     # publish event to GUI / log it
    """

    def __init__(
        self,
        sim_cfg: dict,
        plant_state: MockESPState | None = None,
    ) -> None:
        self.cfg = sim_cfg
        self.plant_ids: list[str] = list(sim_cfg["plants"])
        self.state = plant_state or MockESPState()
        self.rng = random.Random(sim_cfg.get("random_seed"))
        self.hour = 0
        self.last_rain_hour = -999
        self._weather_overrides: dict[str, float | None] = {
            "base_loss_override": None,
            "temperature_offset": 0.0,
            "rain_probability_override": None,
            "rain_amount_override": None,
        }
        self._running = False
        self._paused = False
        self._lock = threading.Lock()

    # ── factory ────────────────────────────────────────────────────

    @classmethod
    def from_config(cls, config_path: Path | str | None = None) -> "SimulationEngine":
        cfg = load_sim_config(config_path)
        return cls(cfg)

    # ── lifecycle ─────────────────────────────────────────────────

    def reset(self) -> None:
        with self._lock:
            reset_esp_state(self.state, self.plant_ids, self.cfg["initial_soil_moisture"])
            self.hour = 0
            self.last_rain_hour = -999
            self._running = False
            self._paused = False

    def start(self) -> None:
        with self._lock:
            self._running = True
            self._paused = False

    def pause(self) -> None:
        with self._lock:
            self._paused = True

    def resume(self) -> None:
        with self._lock:
            self._paused = False

    def stop(self) -> None:
        with self._lock:
            self._running = False

    @property
    def running(self) -> bool:
        return self._running and not self._paused

    # ── GUI knobs ─────────────────────────────────────────────────

    def set_base_loss_override(self, value: float | None) -> None:
        """Force the base evaporation rate. None = use config."""
        with self._lock:
            self._weather_overrides["base_loss_override"] = value

    def set_temperature_offset(self, delta_c: float) -> None:
        with self._lock:
            self._weather_overrides["temperature_offset"] = delta_c

    def set_rain_probability_override(self, value: float | None) -> None:
        with self._lock:
            self._weather_overrides["rain_probability_override"] = value

    def set_rain_amount_override(self, value: float | None) -> None:
        with self._lock:
            self._weather_overrides["rain_amount_override"] = value

    def trigger_manual_rain(self, amount_percent: float | None = None) -> None:
        """Force a rain event on the next step(). Optional ``amount_percent``."""
        with self._lock:
            self._last_rain_hour_override = -999
        # We mark a "force_rain" flag that the next step() consumes.
        self._force_rain_next = True
        self._force_rain_amount = amount_percent

    def refill_cistern(self) -> None:
        """Top the cistern back up to full capacity.

        Mirrors what happens in production when the water_low_alert sensor
        transitions from on → off (the user refilled the tank). Marks the
        ``_prev_water_low_alert`` so the next step records the refill event.
        """
        with self._lock:
            capacity = float(self.cfg.get("__capacity_ml__", 30000.0))
            self.state.cistern_level_ml = capacity
            self.state.water_low_alert = "off"
            self.state._prev_water_low_alert = True  # so step records refill
            self.state.transcript.append({
                "type": "cistern_refill_request",
                "hour": self.hour,
            })

    # ── state snapshot ────────────────────────────────────────────

    def snapshot(self) -> dict:
        with self._lock:
            return {
                "hour": self.hour,
                "running": self._running,
                "paused": self._paused,
                "plants": [
                    {"id": p, "soil": round(self.state.soil_moisture_by_plant.get(p, 0), 2)}
                    for p in self.plant_ids
                ],
                "temperature": round(self.state.air_temperature, 2),
                "humidity": round(self.state.air_humidity, 2),
                "water_low_alert": self.state.water_low_alert,
                "watering_count": self.state.watering_count,
            }

    # ── single step ───────────────────────────────────────────────

    def step(self) -> SimGUIEvent:
        """Advance the simulation by one simulated hour.

        Returns a ``SimGUIEvent`` summarising what happened. Thread-safe.
        """
        with self._lock:
            return self._step_locked()

    # ── batch run (used by pytest reports) ───────────────────────────

    def run_for_hours(self, hours: int) -> list[SimGUIEvent]:
        """Step the simulation forward ``hours`` simulated hours, returning all events."""
        events = []
        for _ in range(hours):
            events.append(self.step())
        return events

    def _step_locked(self) -> SimGUIEvent:
        h = self.hour
        cfg = self.cfg

        # 1. Update environment
        temp_offset = self._weather_overrides["temperature_offset"]
        temp = temperature_at_hour(cfg, h, self.rng) + temp_offset
        hum = humidity_at_hour(cfg, temp, self.rng)

        forced = getattr(self, "_force_rain_next", False)
        if forced:
            self._force_rain_next = False
            rain_amount = (
                self._force_rain_amount
                if self._force_rain_amount is not None
                else cfg["rain"]["amount_when_rains"]
            )
            rain_event = True
            self.last_rain_hour = h
        else:
            rain_prob_override = self._weather_overrides["rain_probability_override"]
            if rain_prob_override is not None:
                rain_event = (
                    h - self.last_rain_hour >= cfg["rain"]["min_gap_hours"]
                    and self.rng.random() < rain_prob_override
                )
            else:
                rain_event = probable_rain(cfg, h, self.last_rain_hour, self.rng)
            rain_amount = self._weather_overrides["rain_amount_override"] or cfg["rain"]["amount_when_rains"]
            if rain_event:
                self.last_rain_hour = h

        # 2. Apply weather to state
        self.state.air_temperature = temp
        self.state.air_humidity = hum

        # 3. Evaporation per plant (now proportional to current moisture)
        loss_pct: dict[str, float] = {}
        for p in self.plant_ids:
            current = self.state.soil_moisture_by_plant[p]
            base_loss = self._weather_overrides["base_loss_override"] or cfg["evaporation"]["base_loss_per_hour"]
            sky_clear = (self.state.water_low_alert == "off")  # cheap proxy
            full_loss = evaporation_loss_percent(cfg, current, temp, hum, sky_clear)
            self.state.soil_moisture_by_plant[p] = max(
                0.0, min(100.0, current - full_loss)
            )
            loss_pct[p] = full_loss

        # 4. Rain (boosts soil)
        if rain_event:
            for p in self.plant_ids:
                self.state.soil_moisture_by_plant[p] = min(
                    100.0,
                    self.state.soil_moisture_by_plant[p] + rain_amount,
                )

        # 5. Build mock status and call the same inference function the api uses
        avg_soil = sum(self.state.soil_moisture_by_plant.values()) / max(1, len(self.plant_ids))
        status = _status_payload_for(self.state, self.plant_ids, self.cfg["plants_cfg"])
        status["_sim_hour"] = h
        status["_blocked_by_hour"] = []

        # Lazy import to avoid pulling the Bayesian server at module import time.
        from bayesian_sprinkler.api import _run_inference_with_status, state as api_state

        # Keep api_state config in sync with our plant configs on first call.
        if not hasattr(self, "_api_initialised"):
            from bayesian_sprinkler.api import (
                SmartSprinklerBN,
                state as api_state_module,
            )
            api_state_module.config = _bayerian_full_config(cfg)
            api_state_module.bn = SmartSprinklerBN(cfg["plants_cfg"])
            api_state_module.esp = SimESPClient(self.state, self.plant_ids, cfg["plants_cfg"])
            # Reset the dosing tracker
            if hasattr(api_state_module, "_last_watered_doses"):
                api_state_module._last_watered_doses = {}
            # Neutralise real-time watering sleep so 504h sims run instantly.
            # The engine applies watering effects via apply_watering_effect() below.
            import bayesian_sprinkler.api as _api_mod
            _api_mod.time.sleep = lambda *_a, **_k: None  # type: ignore[assignment]
            self._api_initialised = True

        # Apply overrides to esp_state before inference
        prev_water_low = self.state.water_low_alert
        self.state.water_low_alert = "off"

        # Mock weather client if real one isn't wired up
        prev_weather = getattr(api_state, "weather", None)
        if prev_weather is None:
            from unittest.mock import MagicMock
            mock_w = MagicMock()
            mock_w.fetch.return_value = {
                "cloud_cover": "clear",
                "rain_forecast": "yes" if rain_event else "no",
                "temperature": temp,
            }
            api_state.weather = mock_w

        try:
            triggered = _run_inference_with_status(api_state, status)
        except Exception as e:
            if h < 3:
                print(f"DEBUG inference error h={h}: {e!r}")
            triggered = {}
        finally:
            self.state.water_low_alert = prev_water_low

        hour_blocked = list(status.get("_blocked_by_hour", []))

        # Apply post-inference watering effects to soil (+ boost per dose)
        cistern_capacity_ml = float(api_state.config.get("cistern_capacity_ml", 30000.0))
        cistern_low_threshold_ml = cistern_capacity_ml * 0.10  # 10 % of capacity
        for plant_name, dose_ml in triggered.items():
            pot_capacity_ml = float(cfg["plants_cfg"].get(plant_name, {}).get("pot_capacity_ml", 500.0))
            apply_watering_effect(self.state, plant_name, dose_ml, pot_capacity_ml)
            # Track cistern water usage (cap at 0).
            self.state.cistern_level_ml = max(
                0.0, self.state.cistern_level_ml - dose_ml
            )

        # Update the water_low_alert sensor based on cistern level. When the
        # level drops below the low threshold, raise the alert; when it
        # rises back above it (the user refilled), reset the alert and top
        # the cistern off to full capacity (the user said refills are
        # always complete).
        was_low = bool(self.state._prev_water_low_alert)
        if self.state.cistern_level_ml <= cistern_low_threshold_ml:
            self.state.water_low_alert = "on"
        else:
            self.state.water_low_alert = "off"

        is_low = self.state.water_low_alert == "on"
        if is_low and not was_low:
            self.state.cistern_low_count += 1
            self.state.transcript.append({
                "type": "cistern_low",
                "hour": h,
                "level_ml": self.state.cistern_level_ml,
                "capacity_ml": cistern_capacity_ml,
            })
        elif not is_low and was_low:
            previous_level = self.state.cistern_level_ml
            self.state.cistern_level_ml = cistern_capacity_ml
            self.state.cistern_refill_count += 1
            self.state.transcript.append({
                "type": "cistern_refill",
                "hour": h,
                "previous_level_ml": previous_level,
                "new_level_ml": cistern_capacity_ml,
                "capacity_ml": cistern_capacity_ml,
            })
        self.state._prev_water_low_alert = is_low

        # 6. Increment hour
        self.hour += 1

        return SimGUIEvent(
            hour=h,
            hour_of_day=h % 24,
            temperature=temp,
            humidity=hum,
            rain_event=rain_event,
            sky="clear",
            soil_by_plant=dict(self.state.soil_moisture_by_plant),
            avg_soil=avg_soil,
            triggered=triggered,
            hour_blocked=hour_blocked,
            inference_notes=[],
            flow_rate_ml_per_min=api_state.config.get("flow_rate_ml_per_min"),
            cistern_level_ml=self.state.cistern_level_ml,
            cistern_capacity_ml=api_state.config.get("cistern_capacity_ml", 30000.0),
            cistern_water_low_alert=self.state.water_low_alert == "on",
        )


# ── Helpers shared by both step paths ────────────────────────────────────


def _status_payload_for(
    state: MockESPState,
    plant_ids: list[str],
    plants_cfg: dict | None = None,
) -> dict[str, Any]:
    """Build the ``status`` payload the api layer expects.

    Each plant's soil reading is exposed on ``soil_moisture_{sensor_index}``
    using the *configured* ``sensor_index`` (matching the physical ESP wiring
    in ``config.yaml``), NOT the positional order of ``plant_ids``. Without
    this the api decides on the wrong plant's soil whenever the config order
    differs from the sensor ordering (e.g. rosmarino on sensor 0).
    """
    avg = sum(state.soil_moisture_by_plant.values()) / max(1, len(plant_ids))
    payload: dict[str, Any] = {
        "air_temperature": f"{state.air_temperature:.2f}",
        "air_humidity": f"{state.air_humidity:.2f}",
        "soil_moisture": f"{avg:.2f}",
        "water_pump": state.water_pump,
        "water_low_alert": state.water_low_alert,
        "active_plant": state.active_plant,
        "blocked_amount_ml": str(state.blocked_amount_ml),
        "rotary_position": "1",
        "status": "ok",
    }
    for i, p in enumerate(plant_ids):
        sensor_index = i
        if plants_cfg is not None:
            sensor_index = int(plants_cfg.get(p, {}).get("sensor_index", i))
        payload[f"soil_moisture_{sensor_index}"] = f"{state.soil_moisture_by_plant[p]:.2f}"
    return payload


# ── ESP wrapper that exposes the API expected by ``_run_inference_with_status`` ───


class SimESPClient:
    """Adapter that makes a ``MockESPState`` look like an ``ESP32Client``.

    The Bayesian inference code calls ``st.esp.discretize_*(value)``,
    ``st.esp.start_watering(target)`` and ``st.esp.stop_watering(target)``.
    The first set is pure local computation; the second mutates the
    side-effects we want to record (soil moisture boost, watering_count).
    """

    def __init__(self, state: MockESPState, plant_ids: list[str],
                 plants_cfg: dict | None = None) -> None:
        self.state = state
        self.plant_ids = plant_ids
        self.plants_cfg = plants_cfg

    # ── discretisation (delegated to the real implementation) ─────────
    def discretize_soil_moisture(self, value: float,
                                 thresholds: dict | None = None) -> str:
        bounds = thresholds if thresholds is not None else {"dry": 35, "moist": 60}
        if value <= bounds.get("dry", 35):
            return "dry"
        if value <= bounds.get("moist", 60):
            return "moist"
        return "wet"

    def discretize_temperature(self, value: float) -> str:
        from bayesian_sprinkler.sensor_client import ESP32Client
        thresholds = {"low": 16, "medium": 29}
        if value <= thresholds["low"]:
            return "low"
        if value <= thresholds["medium"]:
            return "medium"
        return "high"

    def discretize_humidity(self, value: float) -> str:
        from bayesian_sprinkler.sensor_client import ESP32Client
        thresholds = {"low": 45, "medium": 70}
        if value <= thresholds["low"]:
            return "low"
        if value <= thresholds["medium"]:
            return "medium"
        return "high"

    def get_status(self) -> dict:
        return _status_payload_for(self.state, self.plant_ids, self.plants_cfg)

    # ── commands → mutate the mock state ────────────────────────────
    def start_watering(self, target: str) -> dict:
        self.state.water_pump = "on"
        self.state.active_plant = target
        return {"status": "ok"}

    def stop_watering(self, target: str) -> dict:
        self.state.water_pump = "off"
        self.state.active_plant = "null"
        return {"status": "ok"}


def _bayerian_full_config(sim_cfg: dict) -> dict[str, Any]:
    """Translate a simulation config into the full Bayesian app config.

    The api's ``create_app`` expects ``server``, ``esp``, ``weather``,
    ``thresholds``, ``plants`` and ``watering_allowed_hours`` keys; the
    GUI/simulation only cares about ``plants``. The watering window is read
    from the project ``config.yaml`` so the simulated inference uses the
    same global hours the production server does.
    """
    bayesian_cfg_path = PROJECT_ROOT / "config.yaml"
    global_watering_hours: list[int] | None = None
    flow_rate: float | None = None
    if bayesian_cfg_path.exists():
        import yaml
        with open(bayesian_cfg_path) as f:
            bayesian_cfg = yaml.safe_load(f)
        global_watering_hours = bayesian_cfg.get("watering_allowed_hours")
        flow_rate = bayesian_cfg.get("flow_rate_ml_per_min")

    return {
        "server": {"host": "127.0.0.1", "port": 8080},
        "esp": {"base_url": "http://localhost", "poll_interval": 1800},
        "weather": {
            "latitude": sim_cfg.get("weather", {}).get("latitude", 44.69),
            "longitude": sim_cfg.get("weather", {}).get("longitude", 10.44),
            "cloud_cover_threshold": sim_cfg.get("weather", {}).get("cloud_cover_threshold", 45),
        },
        "thresholds": {
            "soil_moisture": {"dry": 35, "moist": 65},
            "temperature": {"low": 16, "medium": 29},
            "humidity": {"low": 45, "medium": 70},
        },
        "flow_rate_ml_per_min": flow_rate,
        "watering_allowed_hours": global_watering_hours,
        "plants": sim_cfg["plants_cfg"],
    }
