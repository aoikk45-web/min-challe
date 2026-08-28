from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

JST = timezone(timedelta(hours=9))


def today_jst() -> date:
    return datetime.now(JST).date()


def now_jst() -> datetime:
    return datetime.now(JST).replace(tzinfo=None)


def week_bounds(day: date | None = None) -> tuple[date, date]:
    day = day or today_jst()
    start = day - timedelta(days=day.weekday())
    end = start + timedelta(days=6)
    return start, end
