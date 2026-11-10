"""Date handling. Every record gets a `date` and a `date_precision`.

Rules
- Timestamps are converted to India Standard Time before the day is taken.
  An item stamped 2026-07-07T20:30Z was published on 8 July in India.
- Precision is one of: day, month, year, unknown. A month-precision date is
  stored as the first of that month and flagged, never passed off as a day.
- Nothing is guessed silently. If no date can be parsed, `date` is empty and
  precision is "unknown".
"""
from __future__ import annotations

import re
from datetime import date, datetime, timedelta, timezone

IST = timezone(timedelta(hours=5, minutes=30))

_MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}
_MON = r"(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?"


def to_ist_date(iso_timestamp: str) -> date:
    dt = datetime.fromisoformat(iso_timestamp.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(IST).date()


def parse_date(raw) -> tuple[str, str]:
    """Parse a loose date string. Returns (ISO date or "", precision).

    >>> parse_date("2026-07-07T20:30:00+00:00")
    ('2026-07-08', 'day')
    >>> parse_date("21 Sept 2026"), parse_date("September 21, 2026"), parse_date("21/09/2026")
    (('2026-09-21', 'day'), ('2026-09-21', 'day'), ('2026-09-21', 'day'))
    >>> parse_date("Sep 2026"), parse_date("2026"), parse_date("last week"), parse_date(None)
    (('2026-09-01', 'month'), ('2026-01-01', 'year'), ('', 'unknown'), ('', 'unknown'))
    """
    if not raw or not str(raw).strip():
        return "", "unknown"
    s = str(raw).strip()
    try:
        if re.match(r"\d{4}-\d{2}-\d{2}T", s):
            return to_ist_date(s).isoformat(), "day"
        m = re.fullmatch(r"(\d{4})-(\d{1,2})-(\d{1,2})", s)
        if m:
            return date(int(m[1]), int(m[2]), int(m[3])).isoformat(), "day"
        # Indian convention is day first: 21/09/2026 or 21-09-2026
        m = re.fullmatch(r"(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{4})", s)
        if m:
            return date(int(m[3]), int(m[2]), int(m[1])).isoformat(), "day"
        low = s.lower()
        m = re.search(rf"(\d{{1,2}})(?:st|nd|rd|th)?\s+{_MON},?\s+(\d{{4}})", low)
        if m:
            return date(int(m[3]), _MONTHS[m[2]], int(m[1])).isoformat(), "day"
        m = re.search(rf"{_MON}\s+(\d{{1,2}})(?:st|nd|rd|th)?,?\s+(\d{{4}})", low)
        if m:
            return date(int(m[3]), _MONTHS[m[1]], int(m[2])).isoformat(), "day"
        m = re.fullmatch(rf"{_MON},?\s+(\d{{4}})", low)
        if m:
            return date(int(m[2]), _MONTHS[m[1]], 1).isoformat(), "month"
        m = re.fullmatch(r"(\d{4})-(\d{1,2})", s)
        if m:
            return date(int(m[1]), int(m[2]), 1).isoformat(), "month"
        m = re.fullmatch(r"(19|20)\d{2}", s)
        if m:
            return date(int(s), 1, 1).isoformat(), "year"
    except ValueError:
        pass  # impossible dates such as 31/02/2026 fall through to unknown
    return "", "unknown"


def date_from_url(url: str) -> tuple[str, str]:
    """Many publishers put the date in the path: /2026/09/21/ or /2026-09-21-."""
    m = re.search(r"/(20\d{2})[/\-](\d{1,2})[/\-](\d{1,2})(?:/|-|$)", url or "")
    if m:
        try:
            return date(int(m[1]), int(m[2]), int(m[3])).isoformat(), "day"
        except ValueError:
            pass
    return "", "unknown"
