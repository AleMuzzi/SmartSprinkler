"""Tests for the log-level feature: rank mapping, DB migration, filter,
and the API surface (Pydantic validation, query parameters)."""

import pytest
from unittest.mock import patch

from fastapi.testclient import TestClient

from bayesian_sprinkler import api
from bayesian_sprinkler.log_levels import (
    DEFAULT_LEVEL,
    LOG_LEVELS,
    LOG_LEVEL_RANK,
    is_valid,
    normalize,
    rank,
)


# ── log_levels module ────────────────────────────────────────────────


class TestLogLevels:
    def test_rank_ordering(self):
        # debug < info < warn < error.
        ranks = [LOG_LEVEL_RANK[level] for level in LOG_LEVELS]
        assert ranks == sorted(ranks)
        assert rank("debug") < rank("info") < rank("warn") < rank("error")

    def test_normalize_unknown_falls_back_to_default(self):
        assert normalize(None) == DEFAULT_LEVEL
        assert normalize("") == DEFAULT_LEVEL
        assert normalize("nope") == DEFAULT_LEVEL
        assert normalize("INFO") == DEFAULT_LEVEL  # case-sensitive
        assert normalize("debug") == "debug"
        assert normalize("error") == "error"

    def test_is_valid(self):
        for level in LOG_LEVELS:
            assert is_valid(level)
        assert not is_valid(None)
        assert not is_valid("")
        assert not is_valid("INFO")  # case-sensitive
        assert not is_valid("debug ")


# ── DB schema + migration ────────────────────────────────────────────


class TestAuditLogLevelColumn:
    @pytest.fixture
    def db(self, tmp_path, monkeypatch):
        from bayesian_sprinkler import database
        from bayesian_sprinkler.audit_log import (
            get_all_log_entries, init_audit_table, init_esp_events_table,
        )
        monkeypatch.setattr(database, "DB_PATH", tmp_path / "levels.db")
        database.init_db()
        init_audit_table()
        init_esp_events_table()
        # Calling init again must be idempotent and not raise (ALTER would fail
        # if the column already existed).
        init_audit_table()
        init_esp_events_table()
        yield get_all_log_entries

    def test_log_event_stores_level(self, db):
        from bayesian_sprinkler.audit_log import log_event
        log_event("command", "Manual watering: Habanero",
                  details="x", level="warn")
        log_event("command", "Manual watering: Rosmarino",
                  details="y")  # default = info
        log_event("command", "Bad level ignored", level="trace")

        rows = db(source="server")
        by_msg = {row["message"]: row["level"] for row in rows}
        assert by_msg["Manual watering: Habanero"] == "warn"
        assert by_msg["Manual watering: Rosmarino"] == "info"
        # Unknown levels get normalised to "info" — the row is still stored.
        assert by_msg["Bad level ignored"] == "info"

    def test_filter_by_level_min_debug_shows_everything(self, db):
        from bayesian_sprinkler.audit_log import log_event
        log_event("a", "debug row",   level="debug")
        log_event("a", "info row",    level="info")
        log_event("a", "warn row",    level="warn")
        log_event("a", "error row",   level="error")

        rows = db(source="server", level_min="debug")
        levels = {row["level"] for row in rows}
        assert levels == {"debug", "info", "warn", "error"}

    def test_filter_by_level_min_info_hides_debug(self, db):
        from bayesian_sprinkler.audit_log import log_event
        log_event("a", "debug row",   level="debug")
        log_event("a", "info row",    level="info")
        log_event("a", "warn row",    level="warn")
        log_event("a", "error row",   level="error")

        rows = db(source="server", level_min="info")
        levels = {row["level"] for row in rows}
        assert "debug" not in levels
        assert levels == {"info", "warn", "error"}

    def test_filter_by_level_min_error_keeps_only_errors(self, db):
        from bayesian_sprinkler.audit_log import log_event
        log_event("a", "debug row",   level="debug")
        log_event("a", "info row",    level="info")
        log_event("a", "warn row",    level="warn")
        log_event("a", "error row",   level="error")

        rows = db(source="server", level_min="error")
        assert [r["level"] for r in rows] == ["error"]

    def test_filter_works_on_esp_events_table_too(self, db):
        from bayesian_sprinkler import database
        from bayesian_sprinkler.audit_log import insert_esp_event
        insert_esp_event({"category": "system", "event": "x",
                          "message": "debug", "level": "debug"})
        insert_esp_event({"category": "system", "event": "y",
                          "message": "info", "level": "info"})

        rows = db(source="esp", level_min="info")
        assert [r["level"] for r in rows] == ["info"]


# ── API: /api/esp/events validation ──────────────────────────────────


class TestEspEventsApi:
    @pytest.fixture
    def client(self):
        with patch("bayesian_sprinkler.api.init_db"), \
             patch("bayesian_sprinkler.api.BackgroundScheduler"), \
             patch("bayesian_sprinkler.api.insert_record"), \
             patch("bayesian_sprinkler.api.insert_plant_telemetry"):
            app = api.create_app(TEST_CONFIG)
            yield TestClient(app)

    def test_valid_level_accepted(self, client):
        resp = client.post(
            "/api/esp/events",
            json={"events": [{
                "category": "system",
                "event": "boot",
                "message": "hi",
                "level": "debug",
            }]},
        )
        assert resp.status_code == 200

    def test_invalid_level_rejected(self, client):
        resp = client.post(
            "/api/esp/events",
            json={"events": [{
                "category": "system",
                "event": "boot",
                "message": "hi",
                "level": "trace",
            }]},
        )
        assert resp.status_code == 422

    def test_missing_level_defaults_to_info(self, client):
        resp = client.post(
            "/api/esp/events",
            json={"events": [{
                "category": "system",
                "event": "boot",
                "message": "hi",
            }]},
        )
        assert resp.status_code == 200

    def test_uppercase_level_rejected(self, client):
        resp = client.post(
            "/api/esp/events",
            json={"events": [{
                "category": "system",
                "event": "boot",
                "message": "hi",
                "level": "INFO",
            }]},
        )
        assert resp.status_code == 422


# ── API: /api/logs query parameters ──────────────────────────────────


TEST_CONFIG = {
    "esp": {"base_url": "http://192.168.1.10", "poll_interval": 120},
    "weather": {"latitude": 44.69, "longitude": 10.44, "cloud_cover_threshold": 50},
    "thresholds": {
        "soil_moisture": {"dry": 35, "moist": 65},
        "temperature": {"low": 16, "medium": 29},
        "humidity": {"low": 45, "medium": 70},
    },
    "plants": {
        "habanero":      {"display_name": "Habanero",      "esp_target": "HABANERO",      "sensor_index": 1, "base_need": 0.52, "threshold": 0.58, "target_soil_moisture": 75.0, "pot_capacity_ml": 730, "min_dose_ml": 115, "max_dose_ml": 550},
        "naga_morich":   {"display_name": "Naga Morich",   "esp_target": "NAGA_MORICH",   "sensor_index": 2, "base_need": 0.544, "threshold": 0.58, "target_soil_moisture": 75.0, "pot_capacity_ml": 890, "min_dose_ml": 115, "max_dose_ml": 670},
        "carolina_reaper":{"display_name":"Carolina Reaper","esp_target":"CAROLINA_REAPER","sensor_index": 3, "base_need": 0.56, "threshold": 0.58, "target_soil_moisture": 75.0, "pot_capacity_ml": 680, "min_dose_ml": 115, "max_dose_ml": 510},
        "rosmarino":     {"display_name": "Rosmarino",     "esp_target": "ROSMARINO",     "sensor_index": 0, "base_need": 0.20, "threshold": 0.60, "target_soil_moisture": 18.0, "pot_capacity_ml": 440, "min_dose_ml": 115, "max_dose_ml": 240},
    },
}


class TestLogsApiLevelFilter:
    @pytest.fixture
    def seeded(self, tmp_path, monkeypatch):
        from bayesian_sprinkler import database
        from bayesian_sprinkler.audit_log import (
            init_audit_table, init_esp_events_table,
            insert_esp_event, log_event,
        )
        monkeypatch.setattr(database, "DB_PATH", tmp_path / "logs_levels.db")
        database.init_db()
        init_audit_table()
        init_esp_events_table()
        log_event("command", "debug evt", level="debug")
        log_event("command", "info evt",  level="info")
        log_event("command", "warn evt",  level="warn")
        log_event("command", "error evt", level="error")
        insert_esp_event({"category": "system", "event": "x",
                          "message": "esp debug", "level": "debug"})
        insert_esp_event({"category": "system", "event": "y",
                          "message": "esp info", "level": "info"})

    @pytest.fixture
    def client(self):
        with patch("bayesian_sprinkler.api.init_db"), \
             patch("bayesian_sprinkler.api.BackgroundScheduler"), \
             patch("bayesian_sprinkler.api.insert_record"), \
             patch("bayesian_sprinkler.api.insert_plant_telemetry"):
            app = api.create_app(TEST_CONFIG)
            yield TestClient(app)

    def test_default_level_min_hides_debug(self, seeded, client):
        resp = client.get("/api/logs")
        assert resp.status_code == 200
        body = resp.json()
        levels = {e["level"] for e in body["entries"]}
        assert "debug" not in levels
        # Default should be "info" → see info+warn+error.
        assert "info" in levels
        assert body["level_min"] == "info"

    def test_explicit_debug_level_min_shows_everything(self, seeded, client):
        resp = client.get("/api/logs?level_min=debug")
        body = resp.json()
        levels = {e["level"] for e in body["entries"]}
        assert "debug" in levels
        assert {"info", "warn", "error"}.issubset(levels)

    def test_error_filter_keeps_only_errors(self, seeded, client):
        resp = client.get("/api/logs?level_min=error")
        body = resp.json()
        assert {e["level"] for e in body["entries"]} == {"error"}

    def test_export_csv_respects_level_min(self, seeded, client):
        resp = client.get("/api/logs/export?level_min=warn")
        assert resp.status_code == 200
        # First line is the header, then each subsequent line has the level
        # in column 5.
        body = resp.text.splitlines()
        header = body[0].split(",")
        assert "level" in header
        for line in body[1:]:
            row = line.split(",")
            level = row[header.index("level")]
            assert level in ("warn", "error")
