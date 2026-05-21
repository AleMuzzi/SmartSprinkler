#!/usr/bin/env python3
"""
SmartSprinkler CPT Auto-Adjuster
=================================
Reads the weekly validation report, parses metrics, and adjusts CPT weights
in config.yaml to improve performance over time.

Adjustment rules (applied in order):
  1. Brier > 0.20  → reduce base_need by 10% to improve calibration
  2. recall < 0.50 → increase base_need by 15% for chilis (reduce false negatives)
  3. precision < 0.50 → decrease base_need by 15% (reduce false positives)
  4. soil_wet P(NeedWater) > 0.20 → reduce base_need by 20% for affected plant
  5. rain_yes < 0.01 → raise rf suppression from 0.05→0.15 to avoid over-suppression
  6. Each run is capped at ±25% cumulative change per plant to avoid oscillation

Run:  cd BayesianSprinkler && uv run python scripts/auto_adjuster.py
"""

import json
import logging
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import yaml

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [auto_adjuster] %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)

STATE_PATH = Path(__file__).parent.parent / "data" / "validation_state.json"
REPORT_PATH = Path(__file__).parent.parent / "validation_report.md"
CONFIG_PATH = Path(__file__).parent.parent / "config.yaml"
LOG_PATH = Path(__file__).parent.parent / "data" / "adjustment_log.jsonl"

MAX_CUMULATIVE_ADJUSTMENT = 0.25

PLANTS_CHILI = {"habanero", "naga_morich", "carolina_reaper"}
PLANTS_ALL = {"habanero", "naga_morich", "carolina_reaper", "rosmarino"}


def load_state() -> dict:
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text())
    return {"weight_version": 1, "adjustments": [], "last_metrics": {}}


def save_state(state: dict):
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2))


def load_config() -> dict:
    return yaml.safe_load(CONFIG_PATH.read_text())


def save_config(cfg: dict):
    CONFIG_PATH.write_text(yaml.dump(cfg, default_flow_style=False, sort_keys=False))


def parse_report() -> dict:
    if not REPORT_PATH.exists():
        logger.error(f"Report not found at {REPORT_PATH}")
        return {}

    text = REPORT_PATH.read_text()

    metrics = {}

    brier_m = re.search(r"Brier Score\s*\|\s*([\d.]+)", text)
    if brier_m:
        metrics["brier"] = float(brier_m.group(1))

    f1_m = re.search(r"Mean F1-Score\s*\|\s*([\d.]+)", text)
    if f1_m:
        metrics["f1"] = float(f1_m.group(1))

    auc_m = re.search(r"ROC-AUC Score\s*\|\s*([\d.]+)", text)
    if auc_m:
        metrics["roc_auc"] = float(auc_m.group(1))

    prec_m = re.search(r"Mean Precision\s*\|\s*([\d.]+)", text)
    if prec_m:
        metrics["precision"] = float(prec_m.group(1))

    rec_m = re.search(r"Mean Recall\s*\|\s*([\d.]+)", text)
    if rec_m:
        metrics["recall"] = float(rec_m.group(1))

    soil_wet_m = re.search(r"wet\s*\|\s*([\d.]+)", text)
    soil_wet_prob = None
    if soil_wet_m:
        soil_wet_prob = float(soil_wet_m.group(1))
    metrics["soil_wet_prob"] = soil_wet_prob

    rain_yes_prob = None
    rain_m = re.search(r"yes\s*\|\s*([\d.]+)\s*\|", text)
    if rain_m:
        rain_yes_prob = float(rain_m.group(1))
    metrics["rain_yes_prob"] = rain_yes_prob

    logger.info(f"Parsed metrics: {metrics}")
    return metrics


def get_cumulative_adjustment(state: dict, plant: str) -> float:
    total = 0.0
    for adj in state.get("adjustments", []):
        if adj.get("plant") == plant or adj.get("plant") == "all":
            total += adj.get("delta", 0)
    return total


def apply_adjustments(metrics: dict, state: dict) -> list[dict]:
    cfg = load_config()
    plants_cfg = cfg["plants"]
    changes: list[dict] = []

    actionable = (
        metrics.get("brier") is not None
        or metrics.get("f1") is not None
        or metrics.get("recall") is not None
        or metrics.get("precision") is not None
        or metrics.get("soil_wet_prob") is not None
        or metrics.get("rain_yes_prob") is not None
    )
    if not actionable:
        logger.warning("No actionable metrics found in report.")
        return []

    if metrics.get("brier") is not None and metrics["brier"] > 0.20:
        logger.warning(f"Brier {metrics['brier']:.4f} > 0.20 — calibration poor.")
        for plant in PLANTS_ALL:
            curr = plants_cfg[plant]["base_need"]
            delta = -0.10
            cum = get_cumulative_adjustment(state, plant)
            if abs(curr * (delta) + cum) > MAX_CUMULATIVE_ADJUSTMENT:
                delta = (MAX_CUMULATIVE_ADJUSTMENT - cum) * (1 if delta > 0 else -1)
            new_val = round(max(0.05, curr + curr * delta), 4)
            plants_cfg[plant]["base_need"] = new_val
            changes.append({
                "plant": plant,
                "param": "base_need",
                "delta": delta,
                "old": curr,
                "new": new_val,
                "reason": f"brier={metrics['brier']:.4f}>0.20",
            })
            logger.info(f"  {plant}: base_need {curr} → {new_val} ({delta:+.1%})")

    if metrics.get("recall") is not None and metrics["recall"] < 0.50:
        logger.warning(f"Recall {metrics['recall']:.4f} < 0.50 — low true positive rate.")
        for plant in PLANTS_CHILI:
            curr = plants_cfg[plant]["base_need"]
            delta = 0.15
            cum = get_cumulative_adjustment(state, plant)
            if abs(curr * delta + cum) > MAX_CUMULATIVE_ADJUSTMENT:
                delta = (MAX_CUMULATIVE_ADJUSTMENT - cum)
            new_val = round(min(0.99, curr + curr * delta), 4)
            plants_cfg[plant]["base_need"] = new_val
            changes.append({
                "plant": plant,
                "param": "base_need",
                "delta": delta,
                "old": curr,
                "new": new_val,
                "reason": f"recall={metrics['recall']:.4f}<0.50",
            })
            logger.info(f"  {plant}: base_need {curr} → {new_val} ({delta:+.1%})")

    if metrics.get("precision") is not None and metrics["precision"] < 0.50:
        logger.warning(f"Precision {metrics['precision']:.4f} < 0.50 — too many false positives.")
        for plant in PLANTS_CHILI:
            curr = plants_cfg[plant]["base_need"]
            delta = -0.15
            cum = get_cumulative_adjustment(state, plant)
            if abs(curr * delta + cum) > MAX_CUMULATIVE_ADJUSTMENT:
                delta = -(MAX_CUMULATIVE_ADJUSTMENT - cum)
            new_val = round(max(0.05, curr + curr * delta), 4)
            plants_cfg[plant]["base_need"] = new_val
            changes.append({
                "plant": plant,
                "param": "base_need",
                "delta": delta,
                "old": curr,
                "new": new_val,
                "reason": f"precision={metrics['precision']:.4f}<0.50",
            })
            logger.info(f"  {plant}: base_need {curr} → {new_val} ({delta:+.1%})")

    if metrics.get("soil_wet_prob") is not None and metrics["soil_wet_prob"] > 0.20:
        logger.warning(f"Soil=wet P(NeedWater)={metrics['soil_wet_prob']:.4f}>0.20 — chilis over-triggered when wet.")
        for plant in PLANTS_CHILI:
            curr = plants_cfg[plant]["base_need"]
            delta = -0.20
            cum = get_cumulative_adjustment(state, plant)
            if abs(curr * delta + cum) > MAX_CUMULATIVE_ADJUSTMENT:
                delta = -(MAX_CUMULATIVE_ADJUSTMENT - cum)
            new_val = round(max(0.05, curr + curr * delta), 4)
            plants_cfg[plant]["base_need"] = new_val
            changes.append({
                "plant": plant,
                "param": "base_need",
                "delta": delta,
                "old": curr,
                "new": new_val,
                "reason": f"soil_wet_prob={metrics['soil_wet_prob']:.4f}>0.20",
            })
            logger.info(f"  {plant}: base_need {curr} → {new_val} ({delta:+.1%})")

    if metrics.get("rain_yes_prob") is not None and metrics["rain_yes_prob"] < 0.01:
        logger.warning(f"RainForecast=yes P(NeedWater)={metrics['rain_yes_prob']:.4f}<0.01 — over-suppressed.")
        if "rf_suppression_dry" not in cfg:
            cfg["tuning"] = cfg.get("tuning", {})
            cfg["tuning"]["rf_suppression_dry"] = 0.05
            cfg["tuning"]["rf_suppression_other"] = 0.15
            changes.append({
                "plant": "all",
                "param": "rf_suppression_dry",
                "delta": 0.0,
                "old": 0.05,
                "new": 0.15,
                "reason": f"rain_yes_prob={metrics['rain_yes_prob']:.4f}<0.01",
            })
            logger.info("  RainForecast suppression: dry_chili 0.05→0.15, other 0.05→0.15")

    save_config(cfg)
    logger.info(f"Wrote updated config to {CONFIG_PATH}")
    return changes


def log_adjustment(changes: list[dict], state: dict, metrics: dict):
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "weight_version": state["weight_version"],
        "metrics_snapshot": metrics,
        "changes": changes,
    }
    with LOG_PATH.open("a") as f:
        f.write(json.dumps(entry) + "\n")


def main():
    logger.info("=== CPT Auto-Adjuster started ===")

    state = load_state()
    metrics = parse_report()

    if not metrics:
        state["last_run_at"] = datetime.now(timezone.utc).isoformat()
        state["last_successful_run_at"] = None
        save_state(state)
        logger.error("No metrics parsed — aborting.")
        sys.exit(1)

    changes = apply_adjustments(metrics, state)

    if changes:
        state["weight_version"] += 1
        state["adjustments"].extend(changes)
        state["last_successful_run_at"] = datetime.now(timezone.utc).isoformat()
        log_adjustment(changes, state, metrics)
        logger.info(
            f"✓ Applied {len(changes)} adjustment(s). "
            f"Weight version: {state['weight_version']-1} → {state['weight_version']}"
        )
    else:
        state["last_successful_run_at"] = datetime.now(timezone.utc).isoformat()
        logger.info("No adjustments needed — CPTs are within tolerance.")

    state["last_run_at"] = datetime.now(timezone.utc).isoformat()
    state["last_report_path"] = str(REPORT_PATH)
    state["last_metrics"] = {k: v for k, v in metrics.items() if v is not None}
    save_state(state)

    logger.info("=== CPT Auto-Adjuster finished ===")


if __name__ == "__main__":
    main()
