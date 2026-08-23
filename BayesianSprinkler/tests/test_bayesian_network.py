import pytest
from bayesian_sprinkler.bayesian_network import SmartSprinklerBN

PLANT_CONFIGS = {
    "habanero": {
        "base_need": 0.65,
        "threshold": 0.50,
        "watering_duration": 6,
    },
    "naga_morich": {
        "base_need": 0.68,
        "threshold": 0.50,
        "watering_duration": 6,
    },
    "carolina_reaper": {
        "base_need": 0.70,
        "threshold": 0.48,
        "watering_duration": 6,
    },
    "rosmarino": {
        "base_need": 0.20,
        "threshold": 0.80,
        "watering_duration": 2,
    },
}


@pytest.fixture
def bn():
    return SmartSprinklerBN(PLANT_CONFIGS)


class TestSmartSprinklerBN:
    def test_build_model_has_correct_structure(self, bn):
        nodes = [n for n in bn.model.nodes()]
        assert "AirTemperature" in nodes
        assert "AirHumidity" in nodes
        assert "CloudCover" in nodes
        assert "EvaporationRisk" in nodes
        assert "SoilMoisture" in nodes
        assert "PlantType" in nodes
        assert "RainForecast" in nodes
        assert "NeedWater" in nodes

    def test_model_has_correct_edges(self, bn):
        edges = [(u, v) for (u, v) in bn.model.edges()]
        assert ("AirTemperature", "EvaporationRisk") in edges
        assert ("AirHumidity", "EvaporationRisk") in edges
        assert ("CloudCover", "EvaporationRisk") in edges
        assert ("EvaporationRisk", "NeedWater") in edges
        assert ("SoilMoisture", "NeedWater") in edges
        assert ("PlantType", "NeedWater") in edges
        assert ("RainForecast", "NeedWater") in edges

    def test_model_has_all_cpds(self, bn):
        cpds = {cpd.variable: cpd for cpd in bn.model.get_cpds()}
        assert "AirTemperature" in cpds
        assert "AirHumidity" in cpds
        assert "CloudCover" in cpds
        assert "EvaporationRisk" in cpds
        assert "SoilMoisture" in cpds
        assert "PlantType" in cpds
        assert "RainForecast" in cpds
        assert "NeedWater" in cpds

    def test_habanero_need_water_high_evap_dry(self, bn):
        """Habanero in hot, dry conditions should have high need probability."""
        prob = bn.query(
            plant="habanero",
            temperature="high",
            humidity="low",
            cloud_cover="clear",
            soil_moisture="dry",
            rain_forecast="no",
        )
        assert prob > 0.7

    def test_rosmarino_low_need_in_mild_conditions(self, bn):
        """Rosmarino should have low need probability in mild, wet conditions."""
        prob = bn.query(
            plant="rosmarino",
            temperature="low",
            humidity="high",
            cloud_cover="cloudy",
            soil_moisture="wet",
            rain_forecast="yes",
        )
        assert prob < 0.3

    def test_naga_morich_super_hot_thirst(self, bn):
        """Naga Morich should have high need when dry."""
        prob = bn.query(
            plant="naga_morich",
            temperature="high",
            humidity="low",
            cloud_cover="clear",
            soil_moisture="dry",
            rain_forecast="no",
        )
        assert prob > 0.7

    def test_carolina_reaper_rain_forecast_reduces_need(self, bn):
        """Rain forecast should reduce watering need."""
        prob_no_rain = bn.query(
            plant="carolina_reaper",
            temperature="medium",
            humidity="medium",
            cloud_cover="cloudy",
            soil_moisture="dry",
            rain_forecast="no",
        )
        prob_rain = bn.query(
            plant="carolina_reaper",
            temperature="medium",
            humidity="medium",
            cloud_cover="cloudy",
            soil_moisture="dry",
            rain_forecast="yes",
        )
        assert prob_rain < prob_no_rain

    def test_all_plants_respond_to_dry_soil(self, bn):
        """All plants should show increased need when soil is dry."""
        for plant in PLANT_CONFIGS:
            prob_dry = bn.query(
                plant=plant,
                temperature="medium",
                humidity="medium",
                cloud_cover="clear",
                soil_moisture="dry",
                rain_forecast="no",
            )
            prob_wet = bn.query(
                plant=plant,
                temperature="medium",
                humidity="medium",
                cloud_cover="clear",
                soil_moisture="wet",
                rain_forecast="no",
            )
            assert prob_dry > prob_wet, f"{plant}: dry should give higher prob than wet"

    def test_rosmarino_threshold_higher_than_habanero(self, bn):
        """Rosmarino should need water less urgently than Habanero in same conditions."""
        prob_rosmarino = bn.query(
            plant="rosmarino",
            temperature="medium",
            humidity="medium",
            cloud_cover="clear",
            soil_moisture="moist",
            rain_forecast="no",
        )
        prob_habanero = bn.query(
            plant="habanero",
            temperature="medium",
            humidity="medium",
            cloud_cover="clear",
            soil_moisture="moist",
            rain_forecast="no",
        )
        assert prob_rosmarino < prob_habanero

    def test_chili_plants_rain_forecast_with_dry_soil(self, bn):
        """Chili plants get reduced need when rain is forecast but soil is dry (40% reduction)."""
        prob_reaper_dry_no_rain = bn.query(
            plant="carolina_reaper",
            temperature="high",
            humidity="low",
            cloud_cover="clear",
            soil_moisture="dry",
            rain_forecast="no",
        )
        prob_reaper_dry_rain = bn.query(
            plant="carolina_reaper",
            temperature="high",
            humidity="low",
            cloud_cover="clear",
            soil_moisture="dry",
            rain_forecast="yes",
        )
        # With rain forecast, chili with dry soil should have ~15% reduction (balcony is covered)
        assert prob_reaper_dry_rain <= prob_reaper_dry_no_rain * 0.85

    def test_evaporation_high_with_hot_dry_clear(self, bn):
        """EvaporationRisk should be highest when hot, dry, and clear."""
        result = bn.inference.query(
            variables=["EvaporationRisk"],
            evidence={
                "AirTemperature": "high",
                "AirHumidity": "low",
                "CloudCover": "clear",
            },
        )
        prob_high = result.values[result.name_to_no["EvaporationRisk"]["high"]]
        assert prob_high > 0.5

    def test_evaporation_low_with_cold_humid_cloudy(self, bn):
        """EvaporationRisk should be lowest when cold, humid, and cloudy."""
        result = bn.inference.query(
            variables=["EvaporationRisk"],
            evidence={
                "AirTemperature": "low",
                "AirHumidity": "high",
                "CloudCover": "cloudy",
            },
        )
        prob_low = result.values[result.name_to_no["EvaporationRisk"]["low"]]
        assert prob_low > 0.5


# ── Regression: replay exact bug scenario from logs_1787484899821.csv ──────

PROD_PLANT_CONFIGS = {
    "habanero": {
        "base_need": 0.52,
        "threshold": 0.58,
        "watering_duration": 6,
    },
    "naga_morich": {
        "base_need": 0.544,
        "threshold": 0.58,
        "watering_duration": 6,
    },
    "carolina_reaper": {
        "base_need": 0.56,
        "threshold": 0.58,
        "watering_duration": 6,
    },
    "rosmarino": {
        "base_need": 0.20,
        "threshold": 0.60,
        "watering_duration": 2,
    },
}


@pytest.fixture
def prod_bn():
    return SmartSprinklerBN(PROD_PLANT_CONFIGS)


class TestNightOverwateringRegression:
    """Regression tests for the 21-22 Aug 2026 overwatering bug.

    The real logs show the BN permitted watering every hour from 01:00 to
    05:00 on 22 Aug despite soil at 24-27% ("dry") and night conditions
    (temp from web fallback, humidity high). The root cause was
    sm_score["dry"]=1.0 producing P(need)>=0.604 at dry+low_evap, above
    the 0.58 threshold.

    After the fix (sm_score["dry"]=0.7), dry+low_evap gives P<0.58 and
    the BN must NOT water. Hot daytime conditions must still water.
    """

    def test_night_dry_low_evap_no_rain_skips_all_chilis(self, prod_bn):
        """Bug scenario: 01:00 on 22 Aug — dry soil, night, no rain."""
        for plant in ["habanero", "naga_morich", "carolina_reaper"]:
            prob = prod_bn.query(
                plant=plant,
                temperature="low",
                humidity="high",
                cloud_cover="clear",
                soil_moisture="dry",
                rain_forecast="no",
            )
            assert prob < 0.58, (
                f"{plant} P(need)={prob:.3f} should be < 0.58 "
                f"at dry+low_evap+no_rain (night)"
            )

    def test_night_dry_low_evap_with_rain_skips(self, prod_bn):
        """22 Aug 00:00 — dry soil, rain=yes (pre-midnight)."""
        for plant in ["habanero", "naga_morich", "carolina_reaper"]:
            prob = prod_bn.query(
                plant=plant,
                temperature="low",
                humidity="high",
                cloud_cover="clear",
                soil_moisture="dry",
                rain_forecast="yes",
            )
            assert prob < 0.58, (
                f"{plant} P(need)={prob:.3f} should be < 0.58 "
                f"at dry+low_evap+rain"
            )

    def test_hot_day_dry_still_waters(self, prod_bn):
        """Sanity: hot dry summer day must still trigger irrigation."""
        for plant in ["habanero", "naga_morich", "carolina_reaper"]:
            prob = prod_bn.query(
                plant=plant,
                temperature="high",
                humidity="low",
                cloud_cover="clear",
                soil_moisture="dry",
                rain_forecast="no",
            )
            assert prob >= 0.58, (
                f"{plant} P(need)={prob:.3f} should be >= 0.58 "
                f"at dry+high_evap+no_rain (hot day)"
            )

    def test_warm_dry_day_still_waters(self, prod_bn):
        """Warm afternoon with dry soil must still water."""
        for plant in ["habanero", "naga_morich", "carolina_reaper"]:
            prob = prod_bn.query(
                plant=plant,
                temperature="medium",
                humidity="medium",
                cloud_cover="clear",
                soil_moisture="dry",
                rain_forecast="no",
            )
            assert prob >= 0.58, (
                f"{plant} P(need)={prob:.3f} should be >= 0.58 "
                f"at dry+med_evap+no_rain (warm day)"
            )

    def test_moist_soil_never_waters(self, prod_bn):
        """Moist soil must never trigger watering regardless of conditions."""
        for plant in PROD_PLANT_CONFIGS:
            for temp in ["low", "medium", "high"]:
                for hum in ["low", "medium", "high"]:
                    for rf in ["yes", "no"]:
                        prob = prod_bn.query(
                            plant=plant,
                            temperature=temp,
                            humidity=hum,
                            cloud_cover="clear",
                            soil_moisture="moist",
                            rain_forecast=rf,
                        )
                        assert prob < 0.58, (
                            f"{plant} moist+{temp}+{hum}+rain={rf}: "
                            f"P={prob:.3f} must be < 0.58"
                        )

    def test_wet_soil_never_waters(self, prod_bn):
        """Wet soil must never trigger watering."""
        for plant in PROD_PLANT_CONFIGS:
            for temp in ["low", "medium", "high"]:
                for hum in ["low", "medium", "high"]:
                    for rf in ["yes", "no"]:
                        prob = prod_bn.query(
                            plant=plant,
                            temperature=temp,
                            humidity=hum,
                            cloud_cover="clear",
                            soil_moisture="wet",
                            rain_forecast=rf,
                        )
                        assert prob < 0.58, (
                            f"{plant} wet+{temp}+{hum}+rain={rf}: "
                            f"P={prob:.3f} must be < 0.58"
                        )

    def test_rain_suppression_works_for_all_chilis(self, prod_bn):
        """Rain forecast must reduce P(need) for all chili plants."""
        for plant in ["habanero", "naga_morich", "carolina_reaper"]:
            prob_no = prod_bn.query(
                plant=plant,
                temperature="medium",
                humidity="medium",
                cloud_cover="clear",
                soil_moisture="dry",
                rain_forecast="no",
            )
            prob_yes = prod_bn.query(
                plant=plant,
                temperature="medium",
                humidity="medium",
                cloud_cover="clear",
                soil_moisture="dry",
                rain_forecast="yes",
            )
            assert prob_yes < prob_no, (
                f"{plant}: rain=yes ({prob_yes:.3f}) should be < "
                f"rain=no ({prob_no:.3f})"
            )
