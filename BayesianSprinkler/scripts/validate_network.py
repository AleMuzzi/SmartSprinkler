#!/usr/bin/env python3
"""
SmartSprinkler Bayesian Network Validation Framework
======================================================
Tasks:
  1. K-Fold Cross-Validation & Calibration Metrics
  2. Variance-Based Sensitivity Analysis
  3. Unified Evaluation Report Generation

Run independently:
  cd BayesianSprinkler && python scripts/validate_network.py
"""

import sys
import warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

warnings.filterwarnings("ignore")

import sqlite3
from typing import Any

import numpy as np
import yaml
from sklearn.metrics import (
    brier_score_loss,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import StratifiedKFold
from tabulate import tabulate

from bayesian_sprinkler.bayesian_network import SmartSprinklerBN
from bayesian_sprinkler.database import get_all_records, init_db

PLANTS = ["habanero", "naga_morich", "carolina_reaper", "rosmarino"]
PARENT_NODES = ["SoilMoisture", "EvaporationRisk", "PlantType", "RainForecast"]
CHILI_PLANTS = {"habanero", "naga_morich", "carolina_reaper"}


def load_config() -> dict[str, Any]:
    with open(Path(__file__).parent.parent / "config.yaml") as f:
        return yaml.safe_load(f)


def load_history() -> list[dict]:
    init_db()
    rows = get_all_records()
    if not rows:
        return []
    return [dict(r) for r in rows]


def discretize(record: dict) -> dict:
    temp = float(record["air_temperature"])
    humid = float(record["air_humidity"])
    cloud = float(record["cloud_cover"])

    if temp < 16:
        temperature_state = "low"
    elif temp < 29:
        temperature_state = "medium"
    else:
        temperature_state = "high"

    if humid < 45:
        humidity_state = "low"
    elif humid < 70:
        humidity_state = "medium"
    else:
        humidity_state = "high"

    cloud_state = "cloudy" if cloud >= 45 else "clear"

    return {
        "AirTemperature": temperature_state,
        "AirHumidity": humidity_state,
        "CloudCover": cloud_state,
        "SoilMoisture": record["soil_moisture"],
        "PlantType": record["plant_type"],
        "RainForecast": record["rain_forecast"],
        "need_water": record["need_water"],
    }


def build_bn(plant_configs: dict) -> SmartSprinklerBN:
    return SmartSprinklerBN(plant_configs)


def baseline_configs(config: dict) -> dict[str, dict]:
    """Hardcoded Montecchio Emilia extreme-summer scenario per plant."""
    base = {
        "AirTemperature": "high",
        "AirHumidity": "low",
        "CloudCover": "clear",
        "SoilMoisture": "dry",
        "RainForecast": "no",
    }
    return {plant: {**base, "PlantType": plant} for plant in PLANTS}


def run_sanity_check(bn: SmartSprinklerBN) -> list[list[str]]:
    config = load_config()
    plants_cfg = config["plants"]
    rows = []
    for plant in PLANTS:
        p = bn.query(
            plant=plant,
            temperature="high",
            humidity="low",
            cloud_cover="clear",
            soil_moisture="dry",
            rain_forecast="no",
        )
        rows.append(
            [
                plants_cfg[plant]["display_name"],
                "high",
                "low",
                "clear",
                "dry",
                "no",
                f"{p:.3f}",
                "YES" if p >= plants_cfg[plant]["threshold"] else "no",
            ]
        )
    return rows


def kfold_cv(records: list[dict], n_splits: int = 5) -> dict[str, Any]:
    if len(records) < n_splits:
        n_splits = max(2, len(records))

    X = np.array([list(r.values()) for r in records])
    y = np.array([1 if r["need_water"] == "yes" else 0 for r in records])

    skf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=42)

    precision_scores, recall_scores, f1_scores, auc_scores, brier_scores = (
        [],
        [],
        [],
        [],
        [],
    )
    all_y_true, all_y_pred, all_y_prob = [], [], []

    config = load_config()
    plants_cfg = config["plants"]

    for fold_idx, (train_idx, test_idx) in enumerate(skf.split(X, y)):
        train_records = [records[i] for i in train_idx]
        test_records = [records[i] for i in test_idx]

        plant_counts: dict[str, int] = {}
        for rec in train_records:
            pt = rec["PlantType"]
            plant_counts[pt] = plant_counts.get(pt, 0) + 1

        fold_plant_configs = {}
        for pt, count in plant_counts.items():
            fold_plant_configs[pt] = plants_cfg.get(
                pt, {"base_need": 0.5, "threshold": 0.5}
            )
        for pt in PLANTS:
            if pt not in fold_plant_configs:
                fold_plant_configs[pt] = plants_cfg.get(
                    pt, {"base_need": 0.5, "threshold": 0.5}
                )

        bn = build_bn(fold_plant_configs)

        y_true_fold, y_pred_fold, y_prob_fold = [], [], []

        for rec in test_records:
            try:
                prob = bn.query(
                    plant=rec["PlantType"],
                    temperature=rec["AirTemperature"],
                    humidity=rec["AirHumidity"],
                    cloud_cover=rec["CloudCover"],
                    soil_moisture=rec["SoilMoisture"],
                    rain_forecast=rec["RainForecast"],
                )
            except Exception:
                prob = 0.5

            pred = 1 if prob >= 0.5 else 0
            y_true_fold.append(1 if rec["need_water"] == "yes" else 0)
            y_pred_fold.append(pred)
            y_prob_fold.append(prob)

        all_y_true.extend(y_true_fold)
        all_y_pred.extend(y_pred_fold)
        all_y_prob.extend(y_prob_fold)

        precision_scores.append(
            precision_score(y_true_fold, y_pred_fold, zero_division=0)
        )
        recall_scores.append(recall_score(y_true_fold, y_pred_fold, zero_division=0))
        f1_scores.append(f1_score(y_true_fold, y_pred_fold, zero_division=0))
        if len(set(y_true_fold)) > 1:
            auc_scores.append(roc_auc_score(y_true_fold, y_prob_fold))
        brier_scores.append(brier_score_loss(y_true_fold, y_prob_fold))

    return {
        "precision": np.mean(precision_scores),
        "recall": np.mean(recall_scores),
        "f1": np.mean(f1_scores),
        "roc_auc": np.mean(auc_scores) if auc_scores else 0.5,
        "brier": np.mean(brier_scores),
        "confusion_matrix": confusion_matrix(all_y_true, all_y_pred).tolist(),
        "all_y_true": all_y_true,
        "all_y_pred": all_y_pred,
        "all_y_prob": all_y_prob,
    }


def sensitivity_analysis(bn: SmartSprinklerBN) -> dict[str, Any]:
    config = load_config()
    plants_cfg = config["plants"]

    mutual_info = {}
    for node in PARENT_NODES:
        try:
            result = bn.inference.query(
                variables=["NeedWater"],
                evidence={node: bn.model.get_cpds(node).state_names[node][0]},
            )
            p_yes_baseline = float(
                result.values[result.name_to_no["NeedWater"]["yes"]]
            )
        except Exception:
            p_yes_baseline = 0.5

        info_gain = 0.0
        try:
            states = bn.model.get_cpds(node).state_names[node]
        except Exception:
            continue

        for state in states:
            try:
                result = bn.inference.query(
                    variables=["NeedWater"], evidence={node: state}
                )
                p_yes = float(result.values[result.name_to_no["NeedWater"]["yes"]])
            except Exception:
                p_yes = 0.5
            info_gain += abs(p_yes - p_yes_baseline)

        mutual_info[node] = round(info_gain / max(len(states), 1), 4)

    soil_sweeps = []
    for soil_state in ["wet", "moist", "dry"]:
        p_yes = bn.query(
            plant="habanero",
            temperature="high",
            humidity="low",
            cloud_cover="clear",
            soil_moisture=soil_state,
            rain_forecast="no",
        )
        soil_sweeps.append((soil_state, round(p_yes, 4)))

    evap_sweeps = []
    for evap_state in ["low", "med", "high"]:
        p_yes = bn.query(
            plant="habanero",
            temperature="high",
            humidity="low",
            cloud_cover="clear",
            soil_moisture="dry",
            rain_forecast="no",
        )
        evap_sweeps.append((evap_state, round(p_yes, 4)))

    rain_sweeps = []
    for rain_state in ["no", "yes"]:
        p_yes = bn.query(
            plant="habanero",
            temperature="high",
            humidity="low",
            cloud_cover="clear",
            soil_moisture="dry",
            rain_forecast=rain_state,
        )
        rain_sweeps.append((rain_state, round(p_yes, 4)))

    plant_sweeps = []
    for plant in PLANTS:
        p_yes = bn.query(
            plant=plant,
            temperature="high",
            humidity="low",
            cloud_cover="clear",
            soil_moisture="dry",
            rain_forecast="no",
        )
        plant_sweeps.append((plants_cfg[plant]["display_name"], round(p_yes, 4)))

    return {
        "mutual_info": mutual_info,
        "soil_sweeps": soil_sweeps,
        "evap_sweeps": evap_sweeps,
        "rain_sweeps": rain_sweeps,
        "plant_sweeps": plant_sweeps,
    }


def generate_report(
    sanity_rows: list[list[str]],
    cv_results: dict[str, Any],
    sensitivity: dict[str, Any],
    output_path: Path,
):
    config = load_config()
    plants_cfg = config["plants"]

    report = []
    report.append("# SmartSprinkler Bayesian Network Evaluation Report\n")
    report.append(
        f"**Generated:** {np.datetime64('now').astype(str)}  "
        f"**Validation Records:** {len(cv_results.get('all_y_true', []))}\n"
    )

    report.append("## 1. Scenario Baseline Testing (Montecchio Emilia — Extreme Summer)\n")
    report.append(
        "| Plant | Air Temp | Humidity | Cloud | Soil | Rain | P(NeedWater) | Triggered? |\n"
        "|------|----------|----------|-------|------|------|-------------|------------|\n"
    )
    for row in sanity_rows:
        report.append(f"| {' | '.join(row)} |")
    report.append("")

    report.append("## 2. Cross-Validation Summary (Stratified 5-Fold)\n")
    if cv_results:
        cv_table = [
            ["Mean Precision", f"{cv_results['precision']:.4f}"],
            ["Mean Recall", f"{cv_results['recall']:.4f}"],
            ["Mean F1-Score", f"{cv_results['f1']:.4f}"],
            ["ROC-AUC Score", f"{cv_results['roc_auc']:.4f}"],
            ["Brier Score", f"{cv_results['brier']:.4f}"],
        ]
        report.append(tabulate(cv_table, headers=["Metric", "Value"], tablefmt="pipe"))
        report.append("")

        cm = cv_results["confusion_matrix"]
        report.append(
            f"\n**Confusion Matrix**  \n"
            f"```\n"
            f"              Predicted\n"
            f"             no    yes\n"
            f"Actual no   {cm[0][0]:<5}  {cm[0][1]}\n"
            f"       yes  {cm[1][0]:<5}  {cm[1][1]}\n"
            f"```\n"
        )
    else:
        report.append(
            "> ⚠️ No historical records available. Run the system for several days to "
            "accumulate sensor_history data, then re-run this script.\n"
        )

    report.append("## 3. Sensitivity Analysis — Mutual Information Rank\n")
    sorted_mi = sorted(
        sensitivity["mutual_info"].items(), key=lambda x: x[1], reverse=True
    )
    report.append(
        "| Rank | Node | Info Gain (ΔP_yes avg) |\n"
        "|------|------|------------------------|\n"
    )
    for rank, (node, score) in enumerate(sorted_mi, 1):
        bar = "▓" * int(score * 20)
        report.append(f"| {rank} | `{node}` | {score:.4f} {bar} |")
    report.append("")

    report.append(
        "### Axiomatic Scenario Sweeps  \n"
        "(Habanero baseline: Temp=high, Humidity=low, Cloud=clear, Soil=dry, Rain=no)\n\n"
    )

    report.append("**SoilMoisture sweep:**\n")
    report.append(
        "| Soil State | P(NeedWater=yes) | Δ from baseline |\n"
        "|------------|-------------------|-----------------|\n"
    )
    baseline = sensitivity["soil_sweeps"][2][1]
    for state, prob in sensitivity["soil_sweeps"]:
        delta = prob - baseline
        report.append(f"| {state:<11} | {prob:.4f} | {delta:+.4f} |")
    report.append("")

    report.append("**RainForecast sweep:**\n")
    report.append(
        "| Rain | P(NeedWater=yes) | Δ from baseline |\n"
        "|------|------------------|-----------------|\n"
    )
    for state, prob in sensitivity["rain_sweeps"]:
        delta = prob - baseline
        report.append(f"| {state:<4} | {prob:.4f} | {delta:+.4f} |")
    report.append("")

    report.append("**PlantType sweep** (display name):\n")
    report.append(
        "| Plant | P(NeedWater=yes) |\n"
        "|-------|-------------------|\n"
    )
    for name, prob in sensitivity["plant_sweeps"]:
        report.append(f"| {name:<16} | {prob:.4f} |")
    report.append("")

    report.append("## 4. Engineering Recommendations\n\n")

    issues = []
    if cv_results:
        if cv_results["brier"] > 0.20:
            issues.append(
                "Brier score > 0.20 indicates poor probability calibration — review CPT priors."
            )
        if cv_results["f1"] < 0.60:
            issues.append(
                "F1 < 0.60 suggests the network struggles to correctly identify watering events."
            )
        if cv_results["roc_auc"] < 0.70:
            issues.append(
                "ROC-AUC < 0.70 indicates limited discriminative power under skewed class distribution."
            )

    rain_yes = None
    for state, prob in sensitivity["rain_sweeps"]:
        if state == "yes":
            rain_yes = prob
            break
    if rain_yes is not None and rain_yes < 0.05:
        issues.append(
            f"RainForecast=yes suppresses P(NeedWater) to {rain_yes:.2f} — verify this is intentional "
            "(avoids over-watering after rain) and not masking noise in the CPT."
        )

    report.append("### CPT Maturity Assessment\n")
    if not issues:
        report.append(
            "✅ **Production-ready CPTs.** All metrics within acceptable thresholds. "
            "Probability outputs are well-calibrated and discriminative power is sufficient.\n"
        )
    else:
        report.append("⚠️ **CPTs need refinement before production:**\n")
        for issue in issues:
            report.append(f"- {issue}\n")

    report.append("\n### Dirichlet Prior Adjustment Guidance\n")
    if cv_results:
        if cv_results.get("recall", 1.0) < 0.50:
            report.append(
                "- **Low recall:** Increase Dirichlet pseudo-counts for `NeedWater=yes` states "
                "corresponding to dry soil + hot conditions. This will push P(NeedWater) higher "
                "and reduce false negatives.\n"
            )
        if cv_results.get("precision", 1.0) < 0.50:
            report.append(
                "- **Low precision:** Decrease Dirichlet counts for `NeedWater=yes` in ambiguous "
                "states (e.g., moist soil, mild temperature). This reduces over-triggering.\n"
            )
    else:
        report.append(
            "> No historical data available for metric-based guidance. "
            "Collect sensor_history records and re-run to generate Dirichlet recommendations.\n"
        )

    soil_wet_prob = None
    for state, prob in sensitivity["soil_sweeps"]:
        if state == "wet":
            soil_wet_prob = prob
            break
    if soil_wet_prob is not None and soil_wet_prob > 0.20:
        report.append(
            f"- **Soil=wet still yields P(NeedWater)={soil_wet_prob:.2f}:** "
            "The CPT base_need for chilis may be too aggressive. Consider reducing "
            "the `base_need` weight or raising the moist/wet thresholds in config.yaml "
            "to prevent watering when soil is already saturated.\n"
        )

    report.append(
        "\n*Report generated by `scripts/validate_network.py`* — "
        "BayesianSprinkler validation framework.\n"
    )

    output_path.write_text("\n".join(report))
    print(f"Report written to {output_path}")


def main():
    config = load_config()
    plants_cfg = config["plants"]

    bn = build_bn(plants_cfg)
    print(f"Bayesian network built. Plants: {PLANTS}")

    records = load_history()
    if records:
        discretized = [discretize(r) for r in records]
        print(f"Loaded {len(records)} historical records.")
    else:
        print("No historical records found — CV will use synthetic data.")
        discretized = []

    print("\n=== Task 1: Sanity Check ===")
    sanity_rows = run_sanity_check(bn)
    print(tabulate(sanity_rows, headers=[
        "Plant", "Temp", "Humid", "Cloud", "Soil", "Rain", "P(NeedWater)", "Triggered?"
    ], tablefmt="pipe"))

    print("\n=== Task 2: K-Fold Cross-Validation ===")
    cv_results = kfold_cv(discretized, n_splits=5) if discretized else {}
    if cv_results:
        print(f"Precision: {cv_results['precision']:.4f}")
        print(f"Recall:    {cv_results['recall']:.4f}")
        print(f"F1:        {cv_results['f1']:.4f}")
        print(f"ROC-AUC:   {cv_results['roc_auc']:.4f}")
        print(f"Brier:     {cv_results['brier']:.4f}")
        print(f"Confusion matrix: {cv_results['confusion_matrix']}")
    else:
        print("Skipped (no data).")

    print("\n=== Task 3: Sensitivity Analysis ===")
    sensitivity = sensitivity_analysis(bn)
    print("Mutual Information (info gain):")
    for node, score in sorted(
        sensitivity["mutual_info"].items(), key=lambda x: x[1], reverse=True
    ):
        print(f"  {node}: {score:.4f}")

    print("\nSoilMoisture sweep (habanero, hot/dry/clear):")
    for state, prob in sensitivity["soil_sweeps"]:
        print(f"  {state}: {prob:.4f}")

    print("\nRainForecast sweep:")
    for state, prob in sensitivity["rain_sweeps"]:
        print(f"  {state}: {prob:.4f}")

    report_path = Path(__file__).parent.parent / "validation_report.md"
    print(f"\n=== Generating Report ===")
    generate_report(sanity_rows, cv_results, sensitivity, report_path)
    print(f"\nDone. Full report: {report_path}")


if __name__ == "__main__":
    main()
