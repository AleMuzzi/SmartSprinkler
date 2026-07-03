import sqlite3
from datetime import datetime
from typing import Optional

from .database import get_connection


def init_audit_table():
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                category TEXT NOT NULL,
                message TEXT NOT NULL,
                details TEXT
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_audit_log_timestamp
            ON audit_log(timestamp DESC)
        """)
        conn.commit()


def log_event(category: str, message: str, details: Optional[str] = None):
    with get_connection() as conn:
        conn.execute(
            """INSERT INTO audit_log (timestamp, category, message, details)
               VALUES (?, ?, ?, ?)""",
            (datetime.now().isoformat(), category, message, details),
        )
        conn.commit()


def get_log_entries(filter_text: Optional[str] = None,
                    category: Optional[str] = None,
                    limit: int = 200) -> list[sqlite3.Row]:
    query = "SELECT * FROM audit_log WHERE 1=1"
    params: list = []
    if filter_text:
        query += " AND (message LIKE ? OR details LIKE ? OR category LIKE ?)"
        like = f"%{filter_text}%"
        params.extend([like, like, like])
    if category:
        query += " AND category = ?"
        params.append(category)
    query += " ORDER BY timestamp DESC LIMIT ?"
    params.append(limit)
    with get_connection() as conn:
        return conn.execute(query, params).fetchall()


def clear_log():
    with get_connection() as conn:
        conn.execute("DELETE FROM audit_log")
        conn.commit()