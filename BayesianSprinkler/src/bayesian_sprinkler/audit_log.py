import sqlite3
from typing import Optional

from .database import get_connection
from .local_time import now as now_local


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
            (now_local().isoformat(), category, message, details),
        )
        conn.commit()


def get_log_entries(filter_text: Optional[str] = None,
                    category: Optional[str] = None,
                    limit: int = 200,
                    start_date: Optional[str] = None,
                    end_date: Optional[str] = None) -> list[sqlite3.Row]:
    query = "SELECT * FROM audit_log WHERE 1=1"
    params: list = []
    if filter_text:
        query += " AND (message LIKE ? OR details LIKE ? OR category LIKE ?)"
        like = f"%{filter_text}%"
        params.extend([like, like, like])
    if category:
        query += " AND category = ?"
        params.append(category)
    if start_date:
        query += " AND substr(timestamp, 1, 10) >= ?"
        params.append(start_date)
    if end_date:
        query += " AND substr(timestamp, 1, 10) <= ?"
        params.append(end_date)
    query += " ORDER BY timestamp DESC LIMIT ?"
    params.append(limit)
    with get_connection() as conn:
        return conn.execute(query, params).fetchall()


def delete_log_entries(start_date: Optional[str] = None,
                       end_date: Optional[str] = None) -> int:
    """Delete log entries scoped to the given date range (inclusive). When
    no date is supplied every entry is removed. Returns the row count."""
    query = "DELETE FROM audit_log WHERE 1=1"
    params: list = []
    if start_date:
        query += " AND substr(timestamp, 1, 10) >= ?"
        params.append(start_date)
    if end_date:
        query += " AND substr(timestamp, 1, 10) <= ?"
        params.append(end_date)
    with get_connection() as conn:
        cur = conn.execute(query, params)
        conn.commit()
        return cur.rowcount


def clear_log():
    with get_connection() as conn:
        conn.execute("DELETE FROM audit_log")
        conn.commit()