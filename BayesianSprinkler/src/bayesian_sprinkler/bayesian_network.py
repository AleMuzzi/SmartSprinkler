import logging

import numpy as np
from pgmpy.factors.discrete import TabularCPD
from pgmpy.inference import VariableElimination
from pgmpy.models import DiscreteBayesianNetwork as BayesianNetwork

logger = logging.getLogger(__name__)

CHILI_PLANTS = {"habanero", "naga_morich", "carolina_reaper"}


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
            cfg["base_need"] * 0.35
            + evap_score * 0.25
            + sm_score * 0.40
        )

        if rf == "yes":
            score *= 0.85

        prob = score
        return float(np.clip(prob, 0.01, 0.99))

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
