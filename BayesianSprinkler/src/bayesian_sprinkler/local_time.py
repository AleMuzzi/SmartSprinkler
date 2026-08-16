import logging
from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

logger = logging.getLogger(__name__)

_ZONE = ZoneInfo("Europe/Rome")


def configure(timezone: str) -> None:
    """Set the local timezone used for audit/sensor timestamps and the
    allowed watering-hour windows. Falls back to Europe/Rome on error."""
    global _ZONE
    try:
        _ZONE = ZoneInfo(timezone)
    except (ZoneInfoNotFoundError, ValueError):
        logger.exception("Unknown timezone %r — falling back to Europe/Rome",
                         timezone)
        _ZONE = ZoneInfo("Europe/Rome")


def now() -> datetime:
    """Current local datetime, timezone-aware and auto-adjusting for DST."""
    return datetime.now(_ZONE)