"""Tests for the ESP event-log pipeline: ingestion endpoint, combined log
queries, cleanup and retention."""

import pytest
from unittest.mock import patch

from fastapi.testclient import TestClient

from bayesian_sprinkler import api
from bayesian_sprinkler.audit_log import (
    init_audit_table,
    init_esp_events_table,
    insert_esp_event,
    get_esp_events,
    get_all_log_entries,
    delete_esp_events_older_than,
)
from bayesian_sprinkler.local_time import now as now_local

from tests.test_api import TEST_CONFIG


@pytest.fixture
def db(tmp_path, monkeypatch):
    """Point the SQLite layer at a throwaway DB and initialise the tables the
    way the app lifespan would (the TestClient fixture from ``test_api.py`` is
    not used as a context manager, so lifespan never runs there)."""
    from bayesian_sprinkler import database
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "test.db")
    init_audit_table()
    init_esp_events_table()
    yield


@pytest.fixture
def client():
    with patch("bayesian_sprinkler.api.init_db"):
        with patch("bayesian_sprinkler.api.BackgroundScheduler"):
            with patch("bayesian_sprinkler.api.insert_record"):
                app = api.create_app(TEST_CONFIG)
                yield TestClient(app)


SAMPLE_EVENT = {
    "ts": 1776400000,  # a fixed epoch, clearly in the past
    "fw": "1.0.0.20",
    "level": "info",
    "category": "command",
    "event": "command_received",
    "message": "Command received",
    "details": {"action": "START", "target": "ROSMARINO", "amount": 0, "force": False},
}


class TestEspEventsIngest:
    def test_post_accepts_batch_and_returns_server_time(self, db, client):
        resp = client.post(
            "/api/esp/events",
            json={"events": [SAMPLE_EVENT]},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["accepted"] == 1
        # server_time is a usable epoch > 0 (clock fallback for the ESP)
        assert body["server_time"] > 1600000000

        rows = get_esp_events()
        assert len(rows) == 1
        assert rows[0]["event"] == "command_received"
        assert rows[0]["ts"] is not None

    def test_post_rejects_unknown_category(self, db, client):
        payload = {**SAMPLE_EVENT, "category": "evil_payload"}
        resp = client.post("/api/esp/events", json={"events": [payload]})
        assert resp.status_code == 200
        assert resp.json()["accepted"] == 0
        assert get_esp_events() == []

    def test_event_without_clock_gets_server_timestamp(self, db):
        event = {**SAMPLE_EVENT, "ts": 0}
        insert_esp_event(event)
        rows = get_esp_events()
        assert len(rows) == 1
        # ts=0 → server-now timestamp, ts column None
        assert rows[0]["ts"] is None
        assert rows[0]["timestamp"].startswith(now_local().date().isoformat())


class TestCombinedLogs:
    def test_get_logs_source_esp(self, db, client):
        resp = client.post("/api/esp/events", json={"events": [SAMPLE_EVENT]})
        assert resp.status_code == 200
        resp = client.get("/api/logs?source=esp")
        assert resp.status_code == 200
        body = resp.json()
        assert body["count"] == 1
        entry = body["entries"][0]
        assert entry["source"] == "esp"
        assert entry["event"] == "command_received"
        assert entry["fw"] == "1.0.0.20"
        assert entry["level"] == "info"
        assert entry["category"] == "command"

    def test_get_logs_all_combines_server_and_esp(self, db, client):
        api.log_event("inference", "Inference cycle completed", details="x=1")
        resp = client.post("/api/esp/events", json={"events": [SAMPLE_EVENT]})
        assert resp.status_code == 200

        body = client.get("/api/logs?source=all").json()
        assert body["count"] == 2
        sources = {entry["source"] for entry in body["entries"]}
        assert sources == {"server", "esp"}
        # newest first
        assert body["entries"][0]["timestamp"] >= body["entries"][1]["timestamp"]

    def test_get_logs_server_only(self, db, client):
        api.log_event("inference", "server-side event", details="x=1")
        resp = client.post("/api/esp/events", json={"events": [SAMPLE_EVENT]})
        assert resp.status_code == 200
        body = client.get("/api/logs?source=server").json()
        assert body["count"] == 1
        assert body["entries"][0]["source"] == "server"

    def test_get_logs_filter_and_category(self, db, client):
        api.log_event("command", "Watering triggered: Habanero", details="dose=250mL")
        api.log_event("inference", "Inference cycle completed", details="watered=[]")
        resp = client.post(
            "/api/esp/events",
            json={"events": [SAMPLE_EVENT, {**SAMPLE_EVENT, "event": "watering_started",
                                            "category": "watering",
                                            "message": "Pump switched ON"}]},
        )
        assert resp.status_code == 200

        # category filter applies to both sources
        body = client.get("/api/logs?source=all&category=command").json()
        assert body["count"] == 2
        assert all(e["category"] == "command" for e in body["entries"])

        # free-text filter searches ESP `event` column too
        body = client.get("/api/logs?source=all&filter=watering_started").json()
        assert body["count"] == 1
        assert body["entries"][0]["event"] == "watering_started"

    def test_get_logs_per_source_with_category_esp(self, db, client):
        resp = client.post(
            "/api/esp/events",
            json={"events": [SAMPLE_EVENT, {**SAMPLE_EVENT, "event": "watering_started",
                                            "category": "watering",
                                            "message": "Pump switched ON"}]},
        )
        assert resp.status_code == 200
        body = client.get("/api/logs?source=esp&category=watering").json()
        assert body["count"] == 1
        assert body["entries"][0]["event"] == "watering_started"

    def test_audit_log_endpoint_still_server_only(self, db, client):
        api.log_event("inference", "server-side event", details="x=1")
        resp = client.post("/api/esp/events", json={"events": [SAMPLE_EVENT]})
        assert resp.status_code == 200
        body = client.get("/api/audit-log").json()
        assert body["count"] == 1
        assert "source" not in body["entries"][0]


class TestCombinedCleanup:
    def test_delete_logs_source_esp(self, db, client):
        insert_esp_event(SAMPLE_EVENT)
        api.log_event("inference", "server event", details="x=1")
        resp = client.delete("/api/logs?source=esp")
        assert resp.status_code == 200
        assert resp.json()["deleted"] == 1
        assert get_esp_events() == []
        assert get_all_log_entries(source="all").__len__() == 1

    def test_delete_logs_requires_source(self, db, client):
        insert_esp_event(SAMPLE_EVENT)
        api.log_event("inference", "server event", details="x=1")
        resp = client.delete("/api/logs?source=all")
        assert resp.status_code == 200
        assert resp.json()["deleted"] == 2
        assert get_all_log_entries(source="all") == []

    def test_delete_logs_esp_with_date_range(self, db, client):
        from bayesian_sprinkler.local_time import from_epoch
        old_ts = int(now_local().timestamp()) - 3 * 86400
        old_date = from_epoch(old_ts).date().isoformat()
        insert_esp_event({**SAMPLE_EVENT, "ts": old_ts})          # 3 days ago
        insert_esp_event(SAMPLE_EVENT)
        resp = client.delete(
            f"/api/logs?source=esp&start_date={old_date}&end_date={old_date}"
        )
        assert resp.status_code == 200
        # Only the 3-days-ago entry falls in the range; the other stays.
        assert resp.json()["deleted"] == 1
        remaining = get_esp_events()
        assert len(remaining) == 1
        assert remaining[0]["ts"] != old_ts

    def test_export_csv_includes_source_header(self, db, client):
        insert_esp_event(SAMPLE_EVENT)
        api.log_event("inference", "server event", details="x=1")
        resp = client.get("/api/logs/export?source=all")
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/csv")
        text = resp.content.decode()
        assert "timestamp,source,category" in text
        assert "esp" in text
        assert "server" in text


class TestRetention:
    def test_delete_esp_events_older_than(self, db):
        recent_ts = int(now_local().timestamp())
        old_epoch = recent_ts - 20 * 86400  # 20 days ago
        insert_esp_event({**SAMPLE_EVENT, "ts": old_epoch})
        insert_esp_event({**SAMPLE_EVENT, "ts": recent_ts})
        deleted = delete_esp_events_older_than(15)
        assert deleted == 1
        rows = get_esp_events()
        assert len(rows) == 1
        assert rows[0]["event"] == "command_received"