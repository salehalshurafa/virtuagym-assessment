"""Time helpers — single source of truth for "today" in a user's timezone.

Why this exists. The frontend stores plan start/end dates as `YYYY-MM-DD`
strings (no time component). On the backend we resolve those against
`date.today()`, which uses the *server's* local clock. If a NY admin
assigns to a Tokyo user at 11pm NY time, that is already 1pm the next day
in Tokyo — so the user expects today=Tomorrow-NY-date, not today=NY-today.

Every "today" lookup in business logic should go through `today_for(user)`
so the right calendar boundary is used.

Datetimes (created_at, expires_at, etc.) stay UTC — only date math is
timezone-sensitive.
"""

from datetime import date, datetime
from typing import Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from models import User


def zone_or_utc(tz_name: Optional[str]) -> ZoneInfo:
    if not tz_name:
        return ZoneInfo("UTC")
    try:
        return ZoneInfo(tz_name)
    except ZoneInfoNotFoundError:
        # Defensive — corrupt or unknown tz name shouldn't crash the request.
        return ZoneInfo("UTC")


def today_for(user: User, *, now: Optional[datetime] = None) -> date:
    """Return today's date as the user's wall clock would see it.

    `now` is overridable for tests. Default is system UTC.
    """
    base = now if now is not None else datetime.utcnow().replace(tzinfo=ZoneInfo("UTC"))
    if base.tzinfo is None:
        base = base.replace(tzinfo=ZoneInfo("UTC"))
    return base.astimezone(zone_or_utc(user.timezone)).date()


def utc_now() -> datetime:
    """Single source for `datetime.utcnow()` — easier to mock in tests."""
    return datetime.utcnow()
