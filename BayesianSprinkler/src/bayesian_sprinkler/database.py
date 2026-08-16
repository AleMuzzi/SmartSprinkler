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
        conn.commit()


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
