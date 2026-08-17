import sqlite3
from pathlib import Path

from .local_time import now as now_local

DB_DIR = Path(__file__).resolve().parent.parent.parent / "data"
DB_PATH = DB_DIR / "sprinkler.db"


def get_connection() -> sqlite3.Connection:
    DB_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sensor_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                plant_type TEXT NOT NULL,
                soil_moisture TEXT NOT NULL,
                air_temperature TEXT NOT NULL,
                air_humidity TEXT NOT NULL,
                cloud_cover TEXT NOT NULL,
                rain_forecast TEXT NOT NULL,
                need_water TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_sensor_history_timestamp
            ON sensor_history(timestamp)
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS service_config (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS plant_telemetry (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                plant_type TEXT NOT NULL,
                soil_moisture_pct REAL,
                air_temperature_c REAL,
                air_humidity_pct REAL
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_plant_telemetry_timestamp
            ON plant_telemetry(timestamp)
        """)
        conn.commit()


def get_service_config(key: str, default: str | None = None) -> str | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT value FROM service_config WHERE key = ?", (key,)
        ).fetchone()
    if row is None:
        return default
    return row["value"]


def set_service_config(key: str, value: str) -> None:
    with get_connection() as conn:
        conn.execute(
            """INSERT INTO service_config (key, value)
               VALUES (?, ?)
               ON CONFLICT(key) DO UPDATE SET value = excluded.value""",
            (key, value),
        )
        conn.commit()


def get_all_service_config() -> dict:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT key, value FROM service_config ORDER BY key"
        ).fetchall()
    return {row["key"]: row["value"] for row in rows}


def insert_record(plant_type: str, soil_moisture: str, air_temperature: str,
                  air_humidity: str, cloud_cover: str, rain_forecast: str,
                  need_water: str):
    with get_connection() as conn:
        conn.execute(
            """INSERT INTO sensor_history
               (timestamp, plant_type, soil_moisture, air_temperature,
                air_humidity, cloud_cover, rain_forecast, need_water)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (now_local().isoformat(), plant_type, soil_moisture,
             air_temperature, air_humidity, cloud_cover, rain_forecast,
             need_water),
        )
        conn.commit()


def get_all_records() -> list[sqlite3.Row]:
    with get_connection() as conn:
        return conn.execute(
            "SELECT * FROM sensor_history ORDER BY timestamp"
        ).fetchall()


def insert_plant_telemetry(plant_type: str, soil_moisture_pct: float,
                           air_temperature_c: float,
                           air_humidity_pct: float) -> None:
    """Store one raw sensor snapshot for a single plant.

    Unlike ``insert_record`` (which persists the discretised BN states),
    this keeps the raw percentages/°C so the web/app charts show real
    values over time. Written once per plant per inference cycle.
    """
    with get_connection() as conn:
        conn.execute(
            """INSERT INTO plant_telemetry
               (timestamp, plant_type, soil_moisture_pct,
                air_temperature_c, air_humidity_pct)
               VALUES (?, ?, ?, ?, ?)""",
            (now_local().isoformat(), plant_type,
             soil_moisture_pct, air_temperature_c, air_humidity_pct),
        )
        conn.commit()


def get_plant_telemetry(start_date: str | None = None,
                        end_date: str | None = None,
                        limit: int = 20000) -> list[sqlite3.Row]:
    """Raw sensor snapshots (ascending time) scoped to a date range."""
    query = (
        "SELECT id, timestamp, plant_type, soil_moisture_pct, "
        "air_temperature_c, air_humidity_pct "
        "FROM plant_telemetry WHERE 1=1"
    )
    params: list = []
    if start_date:
        query += " AND substr(timestamp, 1, 10) >= ?"
        params.append(start_date)
    if end_date:
        query += " AND substr(timestamp, 1, 10) <= ?"
        params.append(end_date)
    query += " ORDER BY timestamp ASC LIMIT ?"
    params.append(limit)
    with get_connection() as conn:
        return conn.execute(query, params).fetchall()
