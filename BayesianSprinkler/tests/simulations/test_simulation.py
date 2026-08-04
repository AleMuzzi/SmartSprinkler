"""Batch simulation runner used by pytest.

The actual environment/evaporation/Bayesian logic lives in ``engine.py``;
this module owns:

- loading and listing simulation configs
- running a single config for ``duration_hours`` simulated hours
- analysing results and emitting per-sim and aggregate Markdown reports

The same engine is reused by the GUI in ``gui.py``.
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from bayesian_sprinkler import api as api_module

import os
import sys

# Make ``engine`` importable as a sibling module without needing package init.
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
from engine import (  # type: ignore  # noqa: E402
    SimulationEngine,
    list_available_configs,
    load_sim_config,
)

REPORTS_DIR = Path(__file__).parent / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)


# ── Analysis & reports ───────────────────────────────────────────────────


def _analyze(plants: list[str], records: list) -> dict:
    total_hours = len(records)
    waterings = {p: 0 for p in plants}
    min_soil = {p: 100.0 for p in plants}
    max_soil = {p: 0.0 for p in plants}
    hours_dry = {p: 0 for p in plants}
    rain_count = sum(1 for r in records if r.rain_event)

    for r in records:
        for p in plants:
            sm = r.soil_by_plant.get(p, 0.0)
            waterings[p] += 1 if p in r.triggered else 0
            min_soil[p] = min(min_soil[p], sm)
            max_soil[p] = max(max_soil[p], sm)
            if sm < 30.0:
                hours_dry[p] += 1

    avg_temp = sum(r.temperature for r in records) / max(1, total_hours)
    avg_hum = sum(r.humidity for r in records) / max(1, total_hours)
    avg_soil = sum(r.avg_soil for r in records) / max(1, total_hours)

    issues = []
    for p in plants:
        never_watered_ok = waterings[p] == 0 and min_soil[p] > 20.0 and total_hours >= 12
        if waterings[p] == 0 and total_hours >= 12 and not never_watered_ok:
            issues.append(
                f"{p} was never watered in {total_hours}h and min soil "
                f"{min_soil[p]:.1f}% (might indicate a bug)"
            )
        if max_soil[p] > 100.0 or min_soil[p] < 0.0:
            issues.append(f"{p} soil out of bounds: min={min_soil[p]:.1f} max={max_soil[p]:.1f}")
        if waterings[p] > total_hours * 0.4:
            issues.append(
                f"{p} watered very often: {waterings[p]}/{total_hours} hours "
                f"({waterings[p]/total_hours*24:.1f}/day)"
            )

    return {
        "waterings_per_plant": waterings,
        "min_soil": min_soil,
        "max_soil": max_soil,
        "hours_dry_below_30": hours_dry,
        "rain_count": rain_count,
        "avg_temp": avg_temp,
        "avg_humidity": avg_hum,
        "avg_soil": avg_soil,
        "issues": issues,
    }


def _write_report(engine_cfg: dict, engine: SimulationEngine, analysis: dict,
                  run_dir: Path, run_ts: str) -> str:
    config_name = engine_cfg.get("__config_name__", "config")
    out_path = run_dir / f"simulation_report_{config_name}_{run_ts}.md"

    plants = engine.plant_ids
    records = list(engine._events_cache) if hasattr(engine, "_events_cache") else []
    # Use a transient local cache so we don't need to expose it from engine.
    # The engine's ``step()`` already records events into the cache during batch.
    records = list(getattr(engine, "_events_cache", []))

    with open(out_path, "w") as f:
        f.write(f"# SmartSprinkler Bayesian Simulation Report\n\n")
        f.write(f"**Generated:** {datetime.now().isoformat()}\n\n")
        f.write(f"**Duration:** {engine.hour} simulated hours\n\n")
        f.write("**Total waterings (per plant):**\n\n")
        for p, n in analysis["waterings_per_plant"].items():
            f.write(f"- `{p}`: {n}\n")
        f.write(f"\n**Total ESP commands:** {engine.state.watering_count}\n\n")

        f.write("## Configuration Used\n\n```yaml\n")
        f.write(yaml.safe_dump(engine_cfg, sort_keys=False))
        f.write("```\n\n")

        f.write("## Environmental Averages\n\n")
        f.write(f"- Average temperature: **{analysis['avg_temp']:.2f}°C**\n")
        f.write(f"- Average humidity: **{analysis['avg_humidity']:.2f}%**\n")
        f.write(f"- Average soil moisture: **{analysis['avg_soil']:.2f}%**\n")
        f.write(f"- Rain events: **{analysis['rain_count']}**\n\n")

        f.write("## Soil Moisture Range (per plant)\n\n")
        f.write("| Plant | Min | Max | Hours < 30% |\n|-------|-----|-----|-------------|\n")
        for p in plants:
            f.write(
                f"| `{p}` | {analysis['min_soil'][p]:.1f}% | "
                f"{analysis['max_soil'][p]:.1f}% | "
                f"{analysis['hours_dry_below_30'][p]} |\n"
            )
        f.write("\n")

        if records:
            f.write("## Hourly Timeline\n\n")
            f.write("| Hour | Hour-of-day | Temp (°C) | Hum (%) | Rain | Avg Soil (%) | Watered (dose) | Hour-blocked |\n")
            f.write("|------|-------------|-----------|---------|------|--------------|----------------|--------------|\n")
            for r in records[:200]:  # cap at 200 rows for readability
                watered_lines = [
                    f"{p}({d:.2f}s)" for p, d in r.triggered.items()
                ]
                watered = ", ".join(watered_lines) if watered_lines else "—"
                blocked = ", ".join(r.hour_blocked) or "—"
                f.write(
                    f"| {r.hour:3d} | {r.hour_of_day:02d}:00 | {r.temperature:6.2f} | "
                    f"{r.humidity:6.2f} | {'✓' if r.rain_event else ' '} | "
                    f"{r.avg_soil:6.2f} | {watered[:50]} | {blocked[:30]} |\n"
                )
            f.write("\n")

        f.write("## Analysis\n\n")
        if analysis["issues"]:
            f.write("### ⚠️ Potential Issues Detected\n\n")
            for issue in analysis["issues"]:
                f.write(f"- {issue}\n")
            f.write("\n")
        else:
            f.write("### ✅ No Issues Detected\n\n")

    return str(out_path)


# ── Engine batch wrapper ─────────────────────────────────────────────────


def _run_engine(sim_cfg: dict) -> tuple[SimulationEngine, list]:
    """Build an engine, run it for the configured duration, return (engine, events)."""
    plant_ids = sim_cfg["plant_ids"]
    engine = SimulationEngine(sim_cfg)
    engine.reset()
    events = engine.run_for_hours(sim_cfg["duration_hours"])
    return engine, events


# ── pytest entry points ──────────────────────────────────────────────────


@pytest.fixture(scope="module")
def _spy_state() -> dict:
    """Shared state for monkey-patching api.state during all sim runs."""
    return {"patchers": [], "api_state_init": False}


def _setup_api_state(engine: SimulationEngine) -> None:
    """Initialize the api global state so the inference has somewhere to write."""
    # The api module exposes a singleton; we point it at our config & our esp.
    api_module.state.config = {
        "server": {"host": "127.0.0.1", "port": 8080},
        "esp": {"base_url": "http://localhost", "poll_interval": 1800},
        "weather": {
            "latitude": 44.69,
            "longitude": 10.44,
            "cloud_cover_threshold": 45,
        },
        "thresholds": {
            "soil_moisture": {"dry": 35, "moist": 65},
            "temperature": {"low": 16, "medium": 29},
            "humidity": {"low": 45, "medium": 70},
        },
        "plants": engine.cfg["plants_cfg"],
    }
    api_module.state.esp = engine.state  # type: ignore[assignment]


@pytest.mark.parametrize("config_path", list_available_configs(),
                         ids=lambda p: p.stem)
def test_single_simulation(config_path):
    """Run every simulation config individually and emit a Markdown report."""
    sim_cfg = load_sim_config(config_path)
    sim_cfg["__config_name__"] = config_path.stem
    engine = SimulationEngine(sim_cfg)
    engine.reset()
    _setup_api_state(engine)
    with patch.object(api_module, "init_db", lambda: None), \
         patch.object(api_module, "BackgroundScheduler", lambda: None), \
         patch.object(api_module, "init_audit_table", lambda: None), \
         patch.object(api_module, "insert_record", lambda *a, **k: None):
        events = engine.run_for_hours(sim_cfg["duration_hours"])

    record_events = events  # last batch run is the records
    analysis = _analyze(engine.plant_ids, record_events)

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    run_ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = _write_report(sim_cfg, engine, analysis, REPORTS_DIR, run_ts)

    print(f"\n📄 [{config_path.stem}] → {out}")
    assert len(events) == sim_cfg["duration_hours"], \
        "Should have one record per hour"


def test_all_simulations_run():
    """Aggregate view: run all configs and emit one combined report."""
    configs = list_available_configs()
    if not configs:
        pytest.skip(f"No simulation configs in {REPORTS_DIR.parent / 'configs'}")

    results = []
    for config_path in configs:
        sim_cfg = load_sim_config(config_path)
        sim_cfg["__config_name__"] = config_path.stem
        engine = SimulationEngine(sim_cfg)
        engine.reset()
        _setup_api_state(engine)
        with patch.object(api_module, "init_db", lambda: None), \
             patch.object(api_module, "BackgroundScheduler", lambda: None), \
             patch.object(api_module, "init_audit_table", lambda: None), \
             patch.object(api_module, "insert_record", lambda *a, **k: None):
            events = engine.run_for_hours(sim_cfg["duration_hours"])
        analysis = _analyze(engine.plant_ids, events)
        results.append({
            "config_name": config_path.stem,
            "engine": engine,
            "events": events,
            "analysis": analysis,
        })

    aggregate_path = REPORTS_DIR / f"aggregate_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    with open(aggregate_path, "w") as f:
        f.write("# SmartSprinkler Bayesian — Aggregate Simulation Report\n\n")
        f.write(f"**Generated:** {datetime.now().isoformat()}\n\n")
        f.write(f"**Simulations run:** {len(results)}\n\n")
        total_hours = sum(len(r["events"]) for r in results)
        f.write(f"**Total simulated hours:** {total_hours}\n\n")
        f.write("| Simulation | Duration | Days | Total waterings | Rain events | "
                "Avg soil | Avg temp | Avg humidity | Issues |\n")
        f.write("|------------|----------|------|-----------------|-------------|"
                "----------|----------|--------------|--------|\n")
        for r in results:
            a = r["analysis"]
            n = len(r["events"])
            f.write(
                f"| `{r['config_name']}` | {n}h | {n/24:.1f} | "
                f"{sum(a['waterings_per_plant'].values())} | {a['rain_count']} | "
                f"{a['avg_soil']:.1f}% | {a['avg_temp']:.1f}°C | "
                f"{a['avg_humidity']:.1f}% | {len(a['issues'])} |\n"
            )
        f.write("\n## Verdict\n\n")
        all_issues = [f"[{r['config_name']}] {i}" for r in results for i in r["analysis"]["issues"]]
        total_w = sum(sum(r["analysis"]["waterings_per_plant"].values()) for r in results)
        if not all_issues:
            f.write(f"**PASS** — Across {len(results)} simulations ({total_hours}h simulated), "
                    f"the BN made {total_w} watering decisions correctly.\n")
        else:
            f.write(f"**REVIEW** — Some anomalies detected:\n")
            for i in all_issues:
                f.write(f"- {i}\n")

    print(f"\n📊 Ran {len(results)} simulations → {aggregate_path}")
    assert len(results) > 0
