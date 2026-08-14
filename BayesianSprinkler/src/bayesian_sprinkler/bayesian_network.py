import logging
from datetime import datetime
import numpy as np
from pgmpy.factors.discrete import TabularCPD
from pgmpy.inference import VariableElimination
from pgmpy.models import DiscreteBayesianNetwork as BayesianNetwork

logger = logging.getLogger(__name__)

CHILI_PLANTS = {"habanero", "naga_morich", "carolina_reaper"}

# Soil-moisture boost applied per 6 s of watering (matches the simulation
# engine in tests/simulations/engine.py). Keeping the value in one place
# would be cleaner but engine.py lives under tests/, so we duplicate and
# assert in tests that they stay aligned.
_WATERING_BOOST_PERCENT = 30.0

# Hot-hour block during which watering is forbidden (matches the default in
# api._watering_allowed / config.yaml). Used to decide whether we need a
# proactive boost on the watering window right before the block.
HOT_HOUR_START = 11
HOT_HOUR_END = 18
HOT_BLOCK_HOURS = HOT_HOUR_END - HOT_HOUR_START

# How many hours before ``HOT_HOUR_START`` we start pre-loading water.
# 2 hours is wide enough to catch h=10 and h=9, but tight enough that we
# don't over-water on cool mornings.
LOOKAHEAD_HOURS = 2

# Extra soil-moisture buffer (%) added to the deficit when we're in the
# pre-hot window. Designed to cover typical evaporation across the 6 h
# hot block (~4-5 %/h average) with a small safety margin.
PROACTIVE_EVAP_BUFFER = 25.0


def discretize_time_of_day(hour: int) -> str:
    """Bucket the hour of day into time-of-day states.

    - night:    21:00 - 05:00 (no sun, ideal for watering)
    - morning:  05:00 - 11:00 (cool, safe)
    - midday:   11:00 - 17:00 (hot sun, avoid to prevent leaf burn)
    - evening:  17:00 - 21:00 (cooling down, safe)
    """
    if hour < 5 or hour >= 21:
        return "night"
    if hour < HOT_HOUR_START:
        return "morning"
    if hour < HOT_HOUR_END:
        return "midday"
    return "evening"


class SmartSprinklerBN:
    def __init__(self, plant_configs: dict):
        self.plant_configs = plant_configs
        self.plants = list(plant_configs.keys())
        self.model = self._build()
        self.inference = VariableElimination(self.model)

    # ── DAG ──────────────────────────────────────────────────────────

    def _build(self) -> BayesianNetwork:
        model = BayesianNetwork([
            ("AirTemperature", "EvaporationRisk"),
            ("AirHumidity", "EvaporationRisk"),
            ("CloudCover", "EvaporationRisk"),
            ("EvaporationRisk", "NeedWater"),
            ("SoilMoisture", "NeedWater"),
            ("PlantType", "NeedWater"),
            ("RainForecast", "NeedWater"),
        ])

        model.add_cpds(
            self._root_cpd("AirTemperature", 3, [0.2, 0.5, 0.3],
                           ["low", "medium", "high"]),
            self._root_cpd("AirHumidity", 3, [0.2, 0.5, 0.3],
                           ["low", "medium", "high"]),
            self._root_cpd("CloudCover", 2, [0.5, 0.5],
                           ["clear", "cloudy"]),
            self._root_cpd("SoilMoisture", 3, [0.3, 0.4, 0.3],
                           ["dry", "moist", "wet"]),
            self._root_cpd("PlantType", len(self.plants),
                           [1.0 / len(self.plants)] * len(self.plants),
                           self.plants),
            self._root_cpd("RainForecast", 2, [0.3, 0.7],
                           ["yes", "no"]),
            self._build_evaporation_cpt(),
            self._build_need_water_cpt(),
        )

        model.check_model()
        return model

    @staticmethod
    def _root_cpd(name: str, card: int, probs: list, states: list) -> TabularCPD:
        return TabularCPD(
            name, card,
            [[p] for p in probs],
            state_names={name: states},
        )

    # ── CPT: EvaporationRisk (parents: AirTemp, AirHumidity, CloudCover) ──

    def _build_evaporation_cpt(self) -> TabularCPD:
        n_cols = 3 * 3 * 2
        values = np.zeros((3, n_cols))

        col = 0
        for temp in ("low", "medium", "high"):
            for humid in ("low", "medium", "high"):
                for cloud in ("clear", "cloudy"):
                    probs = self._evaporation_probs(temp, humid, cloud)
                    values[0, col] = probs[0]
                    values[1, col] = probs[1]
                    values[2, col] = probs[2]
                    col += 1

        return TabularCPD(
            "EvaporationRisk", 3, values,
            evidence=["AirTemperature", "AirHumidity", "CloudCover"],
            evidence_card=[3, 3, 2],
            state_names={
                "EvaporationRisk": ["low", "med", "high"],
                "AirTemperature": ["low", "medium", "high"],
                "AirHumidity": ["low", "medium", "high"],
                "CloudCover": ["clear", "cloudy"],
            },
        )

    @staticmethod
    def _evaporation_probs(temp: str, humid: str, cloud: str) -> list[float]:
        temp_score = {"high": 1.0, "medium": 0.5, "low": 0.0}[temp]
        humid_score = {"low": 1.0, "medium": 0.5, "high": 0.0}[humid]
        cloud_score = {"clear": 1.0, "cloudy": 0.0}[cloud]

        score = temp_score * 0.4 + humid_score * 0.4 + cloud_score * 0.2

        if score <= 0.2:
            return [0.85, 0.10, 0.05]
        if score <= 0.4:
            return [0.50, 0.40, 0.10]
        if score <= 0.6:
            return [0.10, 0.70, 0.20]
        if score <= 0.8:
            return [0.05, 0.35, 0.60]
        return [0.02, 0.08, 0.90]

    # ── CPT: NeedWater (parents: EvapRisk, PlantType, SoilMoisture, RainForecast) ──

    def _build_need_water_cpt(self) -> TabularCPD:
        n_cols = 3 * len(self.plants) * 3 * 2
        values = np.zeros((2, n_cols))

        col = 0
        for evap in ("low", "med", "high"):
            for plant in self.plants:
                for sm in ("dry", "moist", "wet"):
                    for rf in ("yes", "no"):
                        prob = self._need_water_prob(evap, plant, sm, rf)
                        values[0, col] = prob
                        values[1, col] = 1.0 - prob
                        col += 1

        return TabularCPD(
            "NeedWater", 2, values,
            evidence=["EvaporationRisk", "PlantType", "SoilMoisture", "RainForecast"],
            evidence_card=[3, len(self.plants), 3, 2],
            state_names={
                "NeedWater": ["yes", "no"],
                "EvaporationRisk": ["low", "med", "high"],
                "PlantType": self.plants,
                "SoilMoisture": ["dry", "moist", "wet"],
                "RainForecast": ["yes", "no"],
            },
        )

    def _need_water_prob(self, evap: str, plant: str, sm: str, rf: str) -> float:
        cfg = self.plant_configs[plant]
        evap_score = {"low": 0.0, "med": 0.5, "high": 1.0}[evap]
        sm_score = {"dry": 1.0, "moist": 0.3, "wet": 0.0}[sm]

        score = (
            cfg["base_need"] * 0.20
            + evap_score * 0.30
            + sm_score * 0.50
        )

        if rf == "yes":
            score *= 0.85

        return float(np.clip(score, 0.01, 0.99))

    def query_with_dose(self, plant: str, temperature: str, humidity: str,
                        cloud_cover: str, soil_moisture: str, rain_forecast: str,
                        soil_value: float | None = None,
                        sim_hour: int | None = None,
                        ) -> tuple[float, float]:
        """Return (probability_of_watering_need, recommended_dose_seconds).

        Dose calibration
        ----------------
        When ``soil_value`` is provided (numeric moisture %, 0-100), the dose
        is calibrated to bring the soil back to ``target_soil_moisture`` for
        the plant — instead of a fixed ``prob - threshold`` mapping. This
        prevents over-watering in cool/wet weather where ``NeedWater=yes``
        would otherwise trigger a max-duration pulse even though the soil is
        already near the target.

        Behaviour:
        - ``prob < threshold``                        → dose = 0
        - ``soil_value ≥ target``                     → dose = 0 (no need)
        - ``soil_value < target - 5``                 → dose fills the deficit,
          clamped to ``[min_duration, max_duration]``; otherwise → dose = 0
        - **Proactive boost**: when ``sim_hour`` is provided and we are
          within ``LOOKAHEAD_HOURS`` of the hot-hour block (the window in
          which ``_watering_allowed`` will reject further watering), an
          extra ``PROACTIVE_EVAP_BUFFER`` % is added to the deficit so the
          plant has enough water to survive the block.

        When ``soil_value`` is ``None`` the legacy prob-only formula is used.
        """
        evidence = {
            "AirTemperature": temperature,
            "AirHumidity": humidity,
            "CloudCover": cloud_cover,
            "SoilMoisture": soil_moisture,
            "PlantType": plant,
            "RainForecast": rain_forecast,
        }
        result = self.inference.query(variables=["NeedWater"], evidence=evidence)
        prob = float(result.values[result.name_to_no["NeedWater"]["yes"]])

        cfg = self.plant_configs[plant]
        max_dose_ml = cfg.get("max_dose_ml", cfg.get("watering_duration_max", 6) * 23.0)
        min_dose_ml = cfg.get("min_dose_ml", cfg.get("watering_duration_min", 3) * 23.0)
        target_soil = cfg.get("target_soil_moisture", 75.0)

        if prob < cfg["threshold"]:
            return prob, 0.0

        if soil_value is not None:
            current = float(soil_value)
            deficit = target_soil - current
            # Already at/above target → no need regardless of NeedWater=yes.
            if deficit <= 0.0:
                return prob, 0.0
            # Tiny deficit → skip the pulse entirely (avoids dribbles).
            if deficit < 5.0:
                return prob, 0.0
            # Proactive boost: pre-load water so the plant survives the hot
            # block (when ``_watering_allowed`` will refuse to water).
            if sim_hour is not None:
                hours_until_hot = HOT_HOUR_START - sim_hour
                if 0 < hours_until_hot <= LOOKAHEAD_HOURS:
                    deficit += PROACTIVE_EVAP_BUFFER
                    logger.debug(
                        "Proactive boost for %s at h=%02d: deficit %.1f%% → %.1f%%",
                        plant, sim_hour, deficit - PROACTIVE_EVAP_BUFFER, deficit,
                    )
            # Convert the soil deficit (%) into the mL the plant actually
            # needs, using its pot capacity. mL is the canonical unit; the
            # caller converts to seconds at the pump's flow rate.
            pot_capacity_ml = float(cfg.get("pot_capacity_ml", 500.0))
            dose_ml = deficit / 100.0 * pot_capacity_ml
            dose_ml = max(min_dose_ml, min(max_dose_ml, dose_ml))
            return prob, dose_ml

        # Fallback: prob-only formula (kept for callers that don't pass soil).
        # Uses mL as the canonical unit: dose scales linearly with prob.
        excess = (prob - cfg["threshold"]) / max(1e-9, 1.0 - cfg["threshold"])
        excess = max(0.0, min(1.0, excess))
        dose_ml = min_dose_ml + (max_dose_ml - min_dose_ml) * excess
        return prob, dose_ml

    # ── Inference ────────────────────────────────────────────────────

    def query(self, plant: str, temperature: str, humidity: str,
              cloud_cover: str, soil_moisture: str, rain_forecast: str) -> float:
        evidence = {
            "AirTemperature": temperature,
            "AirHumidity": humidity,
            "CloudCover": cloud_cover,
            "SoilMoisture": soil_moisture,
            "PlantType": plant,
            "RainForecast": rain_forecast,
        }
        result = self.inference.query(variables=["NeedWater"], evidence=evidence)
        return float(result.values[result.name_to_no["NeedWater"]["yes"]])
