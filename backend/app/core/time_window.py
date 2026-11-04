"""Bound historical queries and normalize timestamps to UTC."""

from datetime import datetime, timedelta, timezone


MAX_WINDOW_DAYS = 31


def validated_window(start: datetime, end: datetime) -> tuple[datetime, datetime]:
    if start.tzinfo is None or start.utcoffset() is None:
        raise ValueError("start must include a timezone")
    if end.tzinfo is None or end.utcoffset() is None:
        raise ValueError("end must include a timezone")
    start_utc = start.astimezone(timezone.utc)
    end_utc = end.astimezone(timezone.utc)
    if start_utc >= end_utc:
        raise ValueError("start must be earlier than end")
    if end_utc - start_utc > timedelta(days=MAX_WINDOW_DAYS):
        raise ValueError(f"Range must not exceed {MAX_WINDOW_DAYS} days")
    return start_utc, end_utc
