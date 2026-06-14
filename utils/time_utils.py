"""
Timezone and formatting helpers.

All Activity datetimes are stored as UTC; this module converts them to
the event's local timezone (Europe/Kyiv by default, see config) for
display.
"""

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from config import settings

_TZ = ZoneInfo(settings.event_timezone)


def to_local(dt: datetime) -> datetime:
    """
    Convert a datetime to the event's local timezone.

    SQLite has no real timezone-aware column type: SQLAlchemy stores
    datetimes as naive strings and returns naive datetimes on read,
    regardless of what tzinfo they had when inserted. To keep this
    consistent, ALL Activity datetimes are stored as naive UTC
    (see db.seed). A naive datetime here is therefore assumed to be
    UTC; an aware one is converted normally.
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    return dt.astimezone(_TZ)


def format_time(dt: datetime) -> str:
    """Format a datetime as HH:MM in the event's local timezone."""
    return to_local(dt).strftime("%H:%M")


def format_time_range(start: datetime, end: datetime) -> str:
    """Format a start-end pair as 'HH:MM-HH:MM' in the event's local timezone."""
    return f"{format_time(start)}-{format_time(end)}"
