import json
import sqlite3
from typing import Optional

from .database import get_connection
from .local_time import now as now_local
from .local_time import from_epoch
from .log_levels import DEFAULT_LEVEL, LOG_LEVEL_RANK, normalize, rank


def init_audit_table():
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                category TEXT NOT NULL,
                message TEXT NOT NULL,
                details TEXT,
                level TEXT NOT NULL DEFAULT 'info'
            )
        """)
        # Idempotent migration for databases created before the level column
        # was introduced. Existing rows get backfilled to 'info' by the column
        # default. PRAGMA table_info returns ['cid','name','type','notnull',...] tuples.
        cols = [r[1] for r in conn.execute("PRAGMA table_info(audit_log)").fetchall()]
        if "level" not in cols:
            conn.execute(
                "ALTER TABLE audit_log ADD COLUMN level TEXT NOT NULL DEFAULT 'info'"
            )
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_audit_log_timestamp
            ON audit_log(timestamp DESC)
        """)
        conn.commit()


def init_esp_events_table():
    """ESP event log, separate from the server-side audit_log so the two stay
    independent. Kept out of ``audit_log`` on purpose: the ESP pushes its own
    structured events (boot, commands, water-low, OTA, sensor errors…) and we
    want to be able to wipe one source without touching the other."""
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS esp_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                ts INTEGER,
                fw TEXT,
                level TEXT NOT NULL DEFAULT 'info',
                category TEXT NOT NULL,
                event TEXT NOT NULL,
                message TEXT NOT NULL,
                details TEXT
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_esp_events_timestamp
            ON esp_events(timestamp DESC)
        """)
        conn.commit()


def insert_esp_event(event: dict) -> None:
    """Store one ESP event (JSON line as pushed by the firmware).

    ``timestamp`` is derived from the ESP-reported epoch ``ts`` in the local
    timezone; when the ESP had no clock at all (``ts=0`` or missing), we fall
    back to the server's current time so the row is still queryable.
    """
    ts = event.get("ts")
    if isinstance(ts, (int, float)) and ts > 0:
        timestamp = from_epoch(ts).isoformat()
    else:
        timestamp = now_local().isoformat()
        ts = None
    details = event.get("details")
    if isinstance(details, (dict, list)):
        details = json.dumps(details, ensure_ascii=False)
    with get_connection() as conn:
        conn.execute(
            """INSERT INTO esp_events (timestamp, ts, fw, level, category, event, message, details)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                timestamp,
                ts,
                str(event.get("fw")) if event.get("fw") else None,
                str(event.get("level")) or "info",
                str(event.get("category")) or "system",
                str(event.get("event")) or "unknown",
                str(event.get("message")) or "",
                details,
            ),
        )
        conn.commit()


def get_esp_events(filter_text: Optional[str] = None,
                   category: Optional[str] = None,
                   limit: int = 200,
                   start_date: Optional[str] = None,
                   end_date: Optional[str] = None,
                   level_min: Optional[str] = None) -> list[sqlite3.Row]:
    query = (
        "SELECT id, timestamp, ts, category, event, level, fw, message, details "
        "FROM esp_events WHERE 1=1"
    )
    params: list = []
    if filter_text:
        query += " AND (message LIKE ? OR details LIKE ? OR category LIKE ? OR event LIKE ?)"
        like = f"%{filter_text}%"
        params.extend([like, like, like, like])
    if category:
        query += " AND category = ?"
        params.append(category)
    if level_min is not None:
        # 'level' is NOT NULL DEFAULT 'info' (rank 20), so a direct integer
        # comparison works; unknown stored levels would not match any rank.
        min_rank = LOG_LEVEL_RANK.get(level_min, LOG_LEVEL_RANK[DEFAULT_LEVEL])
        query += " AND (CASE level WHEN 'debug' THEN 10 WHEN 'info' THEN 20 "
        query += "WHEN 'warn' THEN 30 WHEN 'error' THEN 40 ELSE 20 END) >= ?"
        params.append(min_rank)
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


def delete_esp_events_older_than(days: int) -> int:
    """Drop ESP events older than ``days`` (local-time date comparison)."""
    from datetime import timedelta
    cutoff = (now_local() - timedelta(days=days)).date().isoformat()
    with get_connection() as conn:
        cur = conn.execute(
            "DELETE FROM esp_events WHERE substr(timestamp, 1, 10) < ?",
            (cutoff,),
        )
        conn.commit()
        return cur.rowcount


def delete_esp_events(start_date: Optional[str] = None,
                      end_date: Optional[str] = None) -> int:
    """Delete ESP events scoped to the given date range (inclusive, local
    date). Without a date range every ESP event is removed."""
    query = "DELETE FROM esp_events WHERE 1=1"
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


def clear_esp_events() -> int:
    with get_connection() as conn:
        cur = conn.execute("DELETE FROM esp_events")
        conn.commit()
        return cur.rowcount


def get_all_log_entries(source: str = "all",
                        filter_text: Optional[str] = None,
                        category: Optional[str] = None,
                        limit: int = 200,
                        start_date: Optional[str] = None,
                        end_date: Optional[str] = None,
                        level_min: Optional[str] = None) -> list[sqlite3.Row]:
    """Combined query over audit_log + esp_events.

    Each row carries a ``source`` column: ``server`` (audit_log) or ``esp``
    (esp_events), so callers can badge or filter per origin.
    ``source`` accepts ``all``, ``server`` or ``esp``.
    ``level_min`` filters out rows below the given level (debug < info <
    warn < error). Default ``None`` returns every level.
    """
    # Reusable CASE that maps the stored level string to its numeric rank.
    # Unknown stored values (legacy NULL before migration, garbled inputs)
    # fall back to the default level (info=20) so they don't get silently
    # dropped or erroneously surfaced as "debug".
    LEVEL_RANK_SQL = (
        "(CASE level WHEN 'debug' THEN 10 WHEN 'info' THEN 20 "
        "WHEN 'warn' THEN 30 WHEN 'error' THEN 40 ELSE 20 END)"
    )

    def _where_clause(extra_columns: list, table_alias: str = "") -> tuple[str, list]:
        query = " WHERE 1=1"
        params: list = []
        if filter_text:
            cols = ["message", "details", "category"] + extra_columns
            query += " AND (" + " OR ".join(f"{c} LIKE ?" for c in cols) + ")"
            like = f"%{filter_text}%"
            params.extend([like] * (len(cols)))
        if category:
            query += " AND category = ?"
            params.append(category)
        if level_min is not None:
            min_rank = LOG_LEVEL_RANK.get(level_min, LOG_LEVEL_RANK[DEFAULT_LEVEL])
            query += f" AND {LEVEL_RANK_SQL} >= ?"
            params.append(min_rank)
        if start_date:
            query += " AND substr(timestamp, 1, 10) >= ?"
            params.append(start_date)
        if end_date:
            query += " AND substr(timestamp, 1, 10) <= ?"
            params.append(end_date)
        return query, params

    selects = []
    params: list = []
    if source in ("all", "server"):
        where, p = _where_clause([])
        selects.append(
            "SELECT id, timestamp, category, message, details, "
            "'server' AS source, "
            "level, "  # server rows now carry the real level (was NULL before)
            "NULL AS event, NULL AS fw "
            "FROM audit_log" + where
        )
        params.extend(p)
    if source in ("all", "esp"):
        where, p = _where_clause(["event"])
        selects.append(
            "SELECT id, timestamp, category, message, details, "
            "'esp' AS source, level, event, fw "
            "FROM esp_events" + where
        )
        params.extend(p)

    if not selects:
        return []

    query = " UNION ALL ".join(selects)
    query += " ORDER BY timestamp DESC, id DESC LIMIT ?"
    params.append(limit)
    with get_connection() as conn:
        return conn.execute(query, params).fetchall()


def log_event(category: str,
              message: str,
              details: Optional[str] = None,
              level: Optional[str] = None):
    """Append a row to ``audit_log``.

    ``level`` is normalised against the closed set in :mod:`log_levels`; any
    unknown value (including ``None``) becomes ``info``.
    """
    effective_level = normalize(level)
    with get_connection() as conn:
        conn.execute(
            """INSERT INTO audit_log (timestamp, category, message, details, level)
               VALUES (?, ?, ?, ?, ?)""",
            (now_local().isoformat(), category, message, details, effective_level),
        )
        conn.commit()


def get_log_entries(filter_text: Optional[str] = None,
                    category: Optional[str] = None,
                    limit: int = 200,
                    start_date: Optional[str] = None,
                    end_date: Optional[str] = None,
                    level_min: Optional[str] = None) -> list[sqlite3.Row]:
    query = "SELECT * FROM audit_log WHERE 1=1"
    params: list = []
    if filter_text:
        query += " AND (message LIKE ? OR details LIKE ? OR category LIKE ?)"
        like = f"%{filter_text}%"
        params.extend([like, like, like])
    if category:
        query += " AND category = ?"
        params.append(category)
    if level_min is not None:
        min_rank = LOG_LEVEL_RANK.get(level_min, LOG_LEVEL_RANK[DEFAULT_LEVEL])
        query += " AND (CASE level WHEN 'debug' THEN 10 WHEN 'info' THEN 20 "
        query += "WHEN 'warn' THEN 30 WHEN 'error' THEN 40 ELSE 20 END) >= ?"
        params.append(min_rank)
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