"""
Refine the Bayesian network's NeedWater CPT using collected sensor history.

Runs Bayesian parameter estimation with a Dirichlet prior centred on the
expert-defined CPT, so real-world data smoothly shifts the probabilities
without washing out the initial domain knowledge.

Usage:
    uv run python -m bayesian_sprinkler.refine_weights
    # or via cron:
    0 3 * * 0 cd /path/to/BayesianSprinkler && uv run python -m bayesian_sprinkler.refine_weights
"""

import argparse
import logging
import pickle
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from bayesian_sprinkler.bayesian_network import (
    CHILI_PLANTS,
    SmartSprinklerBN,
)
from bayesian_sprinkler.database import DB_PATH

logger = logging.getLogger(__name__)

MODEL_DIR = Path(__file__).resolve().parent.parent.parent / "data"
MODEL_PATH = MODEL_DIR / "refined_model.pkl"


# ── Deterministic evaporation mapping (mirrors expert CPD mode) ─────

def _evap_mode(temp: str, humid: str, cloud: str) -> str:
    temp_s = {"high": 1.0, "medium": 0.5, "low": 0.0}[temp]
    humid_s = {"low": 1.0, "medium": 0.5, "high": 0.0}[humid]
    cloud_s = {"clear": 1.0, "cloudy": 0.0}[cloud]
    score = temp_s * 0.4 + humid_s * 0.4 + cloud_s * 0.2

    if score <= 0.3:
        return "low"
    if score <= 0.6:
        return "med"
    return "high"


# ── Posterior estimation with expert-guided Dirichlet prior ─────────

def _estimate_need_water_cpt(
    model: SmartSprinklerBN,
    data: pd.DataFrame,
    prior_strength: float = 50.0,
):
    """
    Blend the expert's NeedWater CPT with empirical counts from *data*.

    Each column *j* in the CPT corresponds to a unique parent-state
    combination (EvaporationRisk, PlantType, SoilMoisture, RainForecast).

    Posterior  =  (expert_CPT[:, j] × prior_strength  +  empirical_counts[:, j])
                 ─────────────────────────────────────────────────────────────
                 prior_strength  +  total_rows_in_combination_j

    *prior_strength* controls how much weight the expert prior retains.
    Higher values = slower adaptation; lower values = data dominates faster.
    """
    expert_cpd = model.model.get_cpds("NeedWater")
    expert_vals = expert_cpd.values.reshape(2, -1)

    plants = model.plants
    n_cols = 3 * len(plants) * 3 * 2
    posterior = np.zeros_like(expert_vals)

    col = 0
    for evap in ("low", "med", "high"):
        for plant in plants:
            for sm in ("dry", "moist", "wet"):
                for rf in ("yes", "no"):
                    mask = (
                        (data["evaporation_risk"] == evap)
                        & (data["plant_type"] == plant)
                        & (data["soil_moisture"] == sm)
                        & (data["rain_forecast"] == rf)
                    )
                    total = int(mask.sum())
                    yes = int((mask & (data["need_water"] == "yes")).sum())

                    pseudo_yes = float(expert_vals[0, col]) * prior_strength
                    pseudo_no = float(expert_vals[1, col]) * prior_strength

                    if total + prior_strength > 0:
                        post_yes = (yes + pseudo_yes) / (total + prior_strength)
                    else:
                        post_yes = expert_vals[0, col]

                    posterior[0, col] = float(np.clip(post_yes, 0.01, 0.99))
                    posterior[1, col] = 1.0 - posterior[0, col]
                    col += 1

    expert_cpd.values = posterior.reshape(2, 3, len(plants), 3, 2)


# ── Main ────────────────────────────────────────────────────────────

def refine(plant_configs: dict, db_path: str | Path = DB_PATH,
           prior_strength: float = 50.0, output: str | None = None):
    logger.info("Loading expert network with %d plants", len(plant_configs))
    bn = SmartSprinklerBN(plant_configs)

    logger.info("Loading sensor history from %s", db_path)
    conn = sqlite3.connect(str(db_path))
    df = pd.read_sql_query("SELECT * FROM sensor_history", conn)
    conn.close()

    if df.empty:
        logger.warning("No history data yet — expert CPTs preserved unchanged")
        MODEL_DIR.mkdir(parents=True, exist_ok=True)
        with open(output or MODEL_PATH, "wb") as f:
            pickle.dump(bn.model, f)
        return

    logger.info("Loaded %d rows — assigning evaporation risk...", len(df))
    df["evaporation_risk"] = df.apply(
        lambda r: _evap_mode(r["air_temperature"], r["air_humidity"], r["cloud_cover"]),
        axis=1,
    )

    yes_ratio = (df["need_water"] == "yes").mean()
    logger.info("Label distribution: need_water=yes %.1f%% (%d / %d)",
                yes_ratio * 100, (df["need_water"] == "yes").sum(), len(df))

    logger.info("Estimating NeedWater CPT (prior_strength=%.1f)...", prior_strength)
    _estimate_need_water_cpt(bn, df, prior_strength)

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    path = output or MODEL_PATH
    with open(path, "wb") as f:
        pickle.dump(bn.model, f)
    logger.info("Refined model saved to %s", path)

    # Sanity check on learnt CPT
    cpd = bn.model.get_cpds("NeedWater")
    logger.info("NeedWater CPT shape: %s (total states: %d)",
                cpd.values.shape, cpd.variable_card)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    parser = argparse.ArgumentParser(
        description="Refine BayesianSprinkler CPTs with collected data")
    parser.add_argument("--config", default=None,
                        help="Path to config.yaml")
    parser.add_argument("--db", default=str(DB_PATH),
                        help="Path to SQLite database")
    parser.add_argument("--prior-strength", type=float, default=50.0,
                        help="Dirichlet prior strength (default: 50)")
    parser.add_argument("--output", default=None,
                        help="Output path for refined model pickle")
    args = parser.parse_args()

    if args.config:
        with open(args.config) as f:
            cfg = yaml.safe_load(f)
    else:
        from bayesian_sprinkler.main import load_config
        cfg = load_config()

    refine(cfg["plants"], args.db, args.prior_strength, args.output)
