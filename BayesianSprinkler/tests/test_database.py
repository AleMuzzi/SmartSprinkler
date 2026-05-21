import os
import tempfile
from pathlib import Path
import pytest
from unittest.mock import patch

from bayesian_sprinkler.database import init_db, insert_record, get_all_records


@pytest.fixture(autouse=True)
def temp_db():
    """Use a temporary database for each test."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    with patch("bayesian_sprinkler.database.DB_PATH", Path(db_path)):
        with patch("bayesian_sprinkler.database.DB_DIR", Path(os.path.dirname(db_path))):
            init_db()
            yield db_path

    os.unlink(db_path)


class TestDatabase:
    def test_init_db_creates_table(self, temp_db):
        insert_record(
            plant_type="habanero",
            soil_moisture="dry",
            air_temperature="high",
            air_humidity="low",
            cloud_cover="clear",
            rain_forecast="no",
            need_water="yes",
        )
        records = get_all_records()
        assert len(records) == 1
        r = records[0]
        assert r["plant_type"] == "habanero"
        assert r["soil_moisture"] == "dry"
        assert r["air_temperature"] == "high"
        assert r["air_humidity"] == "low"
        assert r["cloud_cover"] == "clear"
        assert r["rain_forecast"] == "no"
        assert r["need_water"] == "yes"
        assert r["timestamp"] is not None

    def test_insert_multiple_records(self, temp_db):
        insert_record(
            plant_type="naga_morich",
            soil_moisture="moist",
            air_temperature="medium",
            air_humidity="medium",
            cloud_cover="cloudy",
            rain_forecast="yes",
            need_water="no",
        )
        insert_record(
            plant_type="carolina_reaper",
            soil_moisture="dry",
            air_temperature="high",
            air_humidity="low",
            cloud_cover="clear",
            rain_forecast="no",
            need_water="yes",
        )
        records = get_all_records()
        assert len(records) == 2

    def test_get_all_records_empty(self, temp_db):
        records = get_all_records()
        assert len(records) == 0

    def test_insert_all_plant_types(self, temp_db):
        plants = ["habanero", "naga_morich", "carolina_reaper", "rosmarino"]
        for p in plants:
            insert_record(
                plant_type=p,
                soil_moisture="moist",
                air_temperature="medium",
                air_humidity="medium",
                cloud_cover="cloudy",
                rain_forecast="no",
                need_water="no",
            )
        records = get_all_records()
        assert len(records) == 4
        types = {r["plant_type"] for r in records}
        assert types == set(plants)
