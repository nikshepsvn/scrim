"""Local-day helpers. Transcripts and metrics store UTC ISO timestamps, but
"today" means the user's calendar day — convert before comparing, or an
evening session in UTC-7 lands on tomorrow's report."""

from __future__ import annotations

from datetime import datetime, timezone


def local_day(ts: str | None) -> str | None:
    """YYYY-MM-DD of an ISO timestamp in the machine's local timezone."""
    if not ts:
        return None
    try:
        t = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
    except ValueError:
        return None
    if t.tzinfo is None:
        t = t.replace(tzinfo=timezone.utc)
    return t.astimezone().date().isoformat()


def today_local() -> str:
    return datetime.now(timezone.utc).astimezone().date().isoformat()
