"""Interactive simulation HTTP/SSE router.

Exposes the ``SimulationEngine`` from ``tests/simulations/engine.py`` to the
web frontend so engineers can scrub through a virtual day and watch the
Bayesian inference make watering decisions in real time.

The engine itself runs in a background thread that ticks at a configurable
"sim-minutes per real-second" rate. Each completed hour publishes a
``SimGUIEvent`` to an in-memory queue which the SSE endpoint streams to
the browser.

Endpoints
=========
- ``GET  /api/simulation/configs``        list available YAML scenarios
- ``GET  /api/simulation/state``          current snapshot (hour, plants, weather)
- ``POST /api/simulation/start``          load a config + start the runner
- ``POST /api/simulation/pause``          pause the runner
- ``POST /api/simulation/resume``         resume the runner
- ``POST /api/simulation/reset``          reset hour=0, restore soil
- ``POST /api/simulation/stop``           stop + unload engine
- ``POST /api/simulation/step``           advance one step manually
- ``POST /api/simulation/speed``          set simulated minutes/second (int)
- ``POST /api/simulation/override``       tweak temperature / evaporation / rain
- ``POST /api/simulation/trigger-rain``   force a rain event on next step
- ``GET  /api/simulation/events/stream``  SSE feed of ``SimGUIEvent`` JSON
"""

from __future__ import annotations

import asyncio
import json
import logging
import threading
from collections import deque
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# ── Locate the engine module ──────────────────────────────────────────────

_REPO_ROOT = Path(__file__).resolve().parents[2]  # BayesianSprinkler/
_CONFIGS_DIR = _REPO_ROOT / "tests" / "simulations" / "configs"
_TESTS_DIR = _REPO_ROOT / "tests" / "simulations"

# engine.py lives in tests/simulations and is shipped as part of the package
# for the GUI; sys.path manipulation is contained here so the rest of the
# application doesn't need to know about the test tree.
import sys

if str(_TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(_TESTS_DIR))

try:
    from engine import SimulationEngine, load_sim_config, SimGUIEvent  # type: ignore
except Exception:  # pragma: no cover — only triggered if engine.py is missing
    logger.exception("Failed to import SimulationEngine; sim endpoints disabled")
    SimulationEngine = None  # type: ignore
    load_sim_config = None  # type: ignore
    SimGUIEvent = None  # type: ignore


# ── Pydantic request bodies ───────────────────────────────────────────────


class StartRequest(BaseModel):
    config: str = Field("sunny_day", description="Scenario name (stem of the YAML file).")


class SpeedRequest(BaseModel):
    minutes_per_second: int = Field(60, ge=1, le=600,
                                    description="Simulated minutes per real second.")


class OverrideRequest(BaseModel):
    temperature_offset: float | None = Field(None, description="Δ°C added to the diurnal cycle.")
    base_loss_override: float | None = Field(None, ge=0, le=20, description="Override evaporation % per hour.")
    rain_probability_override: float | None = Field(None, ge=0, le=1, description="Override P(rain) per hour.")
    rain_amount_override: float | None = Field(None, ge=0, le=100, description="Override rain amount (% soil).")


class StepRequest(BaseModel):
    count: int = Field(1, ge=1, le=24, description="Number of hours to step through.")


class TriggerRainRequest(BaseModel):
    amount_percent: float | None = Field(None, ge=0, le=100)


# ── Runtime state ─────────────────────────────────────────────────────────


class _SimulationSession:
    """One-process singleton that owns the engine and the event queue."""

    def __init__(self) -> None:
        self.engine: SimulationEngine | None = None
        self.events: deque[dict[str, Any]] = deque(maxlen=500)
        self.subscribers: list[asyncio.Queue] = []
        self.runner_thread: threading.Thread | None = None
        self.runner_stop = threading.Event()
        self.minutes_per_second: int = 60
        self.loop: asyncio.AbstractEventLoop | None = None

    # ── engine lifecycle ────────────────────────────────────────────

    def load(self, config_name: str) -> dict:
        if SimulationEngine is None:
            raise HTTPException(503, "Simulation engine not available")
        cfg_path = _CONFIGS_DIR / f"{config_name}.yaml"
        if not cfg_path.exists():
            raise HTTPException(404, f"Unknown simulation config: {config_name}")
        sim_cfg = load_sim_config(cfg_path)
        sim_cfg["__config_name__"] = config_name
        self.engine = SimulationEngine(sim_cfg)
        self.engine.reset()
        self.engine.start()
        self.events.clear()
        return self.engine.snapshot()

    def reset(self) -> dict:
        if not self.engine:
            raise HTTPException(400, "No simulation loaded")
        self.engine.reset()
        self.engine.start()
        self.events.clear()
        return self.engine.snapshot()

    def pause(self) -> dict:
        if not self.engine:
            raise HTTPException(400, "No simulation loaded")
        self.engine.pause()
        return self.engine.snapshot()

    def resume(self) -> dict:
        if not self.engine:
            raise HTTPException(400, "No simulation loaded")
        self.engine.resume()
        return self.engine.snapshot()

    def stop(self) -> dict:
        self._stop_runner()
        if self.engine:
            self.engine.stop()
        return {"ok": True}

    def step(self, count: int) -> list[dict]:
        if not self.engine:
            raise HTTPException(400, "No simulation loaded")
        out = []
        for _ in range(count):
            ev = self.engine.step()
            self._publish(ev.to_public())
            out.append(ev.to_public())
        return out

    # ── knobs ───────────────────────────────────────────────────────

    def set_speed(self, minutes_per_second: int) -> None:
        self.minutes_per_second = max(1, minutes_per_second)

    def override(self, req: OverrideRequest) -> dict:
        if not self.engine:
            raise HTTPException(400, "No simulation loaded")
        if req.temperature_offset is not None:
            self.engine.set_temperature_offset(req.temperature_offset)
        if req.base_loss_override is not None:
            self.engine.set_base_loss_override(req.base_loss_override)
        elif req.base_loss_override == 0:
            self.engine.set_base_loss_override(0.0)
        if req.rain_probability_override is not None:
            self.engine.set_rain_probability_override(req.rain_probability_override)
        if req.rain_amount_override is not None:
            self.engine.set_rain_amount_override(req.rain_amount_override)
        return self.engine.snapshot()

    def trigger_rain(self, amount_percent: float | None) -> dict:
        if not self.engine:
            raise HTTPException(400, "No simulation loaded")
        self.engine.trigger_manual_rain(amount_percent)
        return {"ok": True, "queued": True}

    def refill_cistern(self) -> dict:
        if not self.engine:
            raise HTTPException(400, "No simulation loaded")
        self.engine.refill_cistern()
        return {"ok": True}

    # ── streaming ───────────────────────────────────────────────────

    def _publish(self, payload: dict) -> None:
        self.events.append(payload)
        # Push to every subscriber's asyncio queue (non-blocking).
        for q in list(self.subscribers):
            try:
                q.put_nowait(payload)
            except asyncio.QueueFull:  # pragma: no cover — bounded queues
                pass
            except Exception:  # noqa: BLE001
                logger.exception("Failed to push sim event to subscriber")

    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=200)
        self.subscribers.append(q)
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        try:
            self.subscribers.remove(q)
        except ValueError:
            pass

    # ── background runner ───────────────────────────────────────────

    def start_runner(self) -> None:
        if self.runner_thread and self.runner_thread.is_alive():
            return
        self.runner_stop.clear()
        self.runner_thread = threading.Thread(
            target=self._runner_loop, name="sim-runner", daemon=True
        )
        self.runner_thread.start()

    def _stop_runner(self) -> None:
        self.runner_stop.set()
        if self.runner_thread:
            self.runner_thread.join(timeout=2.0)
        self.runner_thread = None

    def _runner_loop(self) -> None:
        """Pump ``engine.step()`` at ``minutes_per_second`` rate."""
        while not self.runner_stop.is_set():
            engine = self.engine
            if engine is None or engine._paused or not engine._running:
                self.runner_stop.wait(0.1)
                continue
            # Simulated minutes per real second → step interval (seconds per hour).
            # Default 60 min/s  →  1 step per second
            # 600 min/s          →  10 steps per second
            seconds_per_hour = 60.0 / max(1, self.minutes_per_second)
            try:
                ev = engine.step()
            except Exception:  # noqa: BLE001
                logger.exception("Simulation step failed")
                self.runner_stop.wait(0.5)
                continue
            self._publish(ev.to_public())
            # Sleep, but stay responsive to stop/pause.
            self.runner_stop.wait(seconds_per_hour)


session = _SimulationSession()


# ── HTTP routes ───────────────────────────────────────────────────────────


def _list_configs() -> list[dict[str, str]]:
    if not _CONFIGS_DIR.exists():
        return []
    return [
        {"name": p.stem, "path": str(p.relative_to(_REPO_ROOT))}
        for p in sorted(_CONFIGS_DIR.glob("*.yaml"))
    ]


def create_router() -> APIRouter:
    router = APIRouter(prefix="/api/simulation", tags=["Simulation"])

    @router.get("/configs", summary="List available simulation scenarios")
    def list_configs() -> list[dict[str, str]]:
        return _list_configs()

    @router.get("/state", summary="Current engine snapshot")
    def state() -> dict:
        if not session.engine:
            return {"loaded": False}
        snap = session.engine.snapshot()
        snap["loaded"] = True
        snap["speed_minutes_per_second"] = session.minutes_per_second
        return snap

    @router.post("/start", summary="Load a scenario and start the runner")
    def start(req: StartRequest) -> dict:
        snap = session.load(req.config)
        session.start_runner()
        snap["loaded"] = True
        snap["speed_minutes_per_second"] = session.minutes_per_second
        return snap

    @router.post("/pause", summary="Pause the runner")
    def pause() -> dict:
        return session.pause()

    @router.post("/resume", summary="Resume the runner")
    def resume() -> dict:
        return session.resume()

    @router.post("/reset", summary="Reset hour=0 and restart")
    def reset() -> dict:
        snap = session.reset()
        session.start_runner()
        snap["loaded"] = True
        snap["speed_minutes_per_second"] = session.minutes_per_second
        return snap

    @router.post("/stop", summary="Stop and unload the engine")
    def stop() -> dict:
        return session.stop()

    @router.post("/step", summary="Advance N hours synchronously")
    def step(req: StepRequest) -> dict:
        events = session.step(req.count)
        return {"events": events, "state": session.engine.snapshot() if session.engine else {}}

    @router.post("/speed", summary="Set simulated minutes per real second")
    def speed(req: SpeedRequest) -> dict:
        session.set_speed(req.minutes_per_second)
        return {"speed_minutes_per_second": session.minutes_per_second}

    @router.post("/override", summary="Override weather knobs")
    def override(req: OverrideRequest) -> dict:
        return session.override(req)

    @router.post("/trigger-rain", summary="Force a rain event on the next step")
    def trigger_rain(req: TriggerRainRequest) -> dict:
        return session.trigger_rain(req.amount_percent)

    @router.post("/refill-cistern", summary="Top the cistern back to full capacity")
    def refill_cistern() -> dict:
        session.refill_cistern()
        return {"ok": True, "refilled": True}

    @router.get("/events/stream", summary="SSE stream of SimGUIEvent JSON")
    async def stream():
        # Capture the running loop so background-thread publishes can hop in.
        session.loop = asyncio.get_running_loop()
        q = session.subscribe()
        # Replay recent events so a fresh connection gets immediate context.
        for ev in list(session.events):
            try:
                q.put_nowait(ev)
            except asyncio.QueueFull:
                break

        async def event_gen():
            try:
                # Initial hello so the EventSource onOpen fires immediately.
                yield f"data: {json.dumps({'type': 'hello'})}\n\n"
                while True:
                    try:
                        ev = await asyncio.wait_for(q.get(), timeout=15.0)
                    except asyncio.TimeoutError:
                        # Heartbeat keeps proxies from closing the connection.
                        yield ": keep-alive\n\n"
                        continue
                    yield f"data: {json.dumps({'type': 'event', **ev})}\n\n"
            finally:
                session.unsubscribe(q)

        return StreamingResponse(
            event_gen(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
                "Connection": "keep-alive",
            },
        )

    return router