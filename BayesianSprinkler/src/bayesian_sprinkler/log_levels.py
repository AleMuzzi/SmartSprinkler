"""Centralised definition of log levels used across the server.

Hierarchy (low → high):

    debug (10)  →  info (20)  →  warn (30)  →  error (40)

The dashboard / app filters logs with a *minimum* level: ``level_min="info"``
shows ``info``, ``warn`` and ``error`` but hides ``debug``. Default is
``info`` everywhere (DB default, API default, UI default).

The firmware ESP emits the level as a free-form string in the event JSON;
``LOG_LEVELS`` defines the closed set accepted by the server validator.
Anything outside the set is rejected with HTTP 422 by ``POST /api/esp/events``.
"""

from typing import Optional

# Closed set of valid levels (kept ordered so iteration is also low → high).
LOG_LEVELS: tuple[str, ...] = ("debug", "info", "warn", "error")

# Numeric rank used for the "minimum level" filter. Higher = more severe.
LOG_LEVEL_RANK: dict[str, int] = {
    "debug": 10,
    "info": 20,
    "warn": 30,
    "error": 40,
}

DEFAULT_LEVEL = "info"


def normalize(value: Optional[str]) -> str:
    """Return ``value`` if it's a valid level, else ``DEFAULT_LEVEL``."""
    if value in LOG_LEVELS:
        return value
    return DEFAULT_LEVEL


def rank(value: Optional[str]) -> int:
    """Numeric rank for ``value``; unknown levels map to ``DEFAULT_LEVEL``."""
    return LOG_LEVEL_RANK[normalize(value)]


def is_valid(value: Optional[str]) -> bool:
    return value in LOG_LEVELS
