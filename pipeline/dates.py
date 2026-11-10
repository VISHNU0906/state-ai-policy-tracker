"""Date handling. Every record gets a `date` and a `date_precision`.

Rules
- Timestamps are converted to India Standard Time before the day is taken.
  An item stamped 2026-07-07T20:30Z was published on 8 July in India.
- Precision is one of: day, month, quarter, year, unknown. A coarse date is
  stored as the first day of its period and flagged, never passed off as a day.
- Nothing is guessed silently. If no date can be parsed, `date` is empty and
  precision is "unknown". Relative phrases ("yesterday", "3 days ago") are only
  resolved when the caller supplies the day the text was written.
- Numeric dates are read day first (21/09/2026), the Indian convention. The one
  exception is when that is impossible and month first is not (09/21/2026).

Patterns handled, with the precision each gives:

  2026-07-07T20:30:00Z, 2026-07-07 20:30:00, 1783456200        day (India time)
  2026-09-21, 2026/09/21, 21/09/2026, 21-09-26, 21.09.2026     day
  21 Sept 2026, 21st September, 2026, Sept. 21 2026            day
  Tuesday, 10 November 2026; Updated: Nov 10, 2026 10:30 IST   day
  21 Septmber 2026, 3 Febuary 2026 (misspelt months)           day
  today, yesterday, 3 days ago, 5 hours ago (with a reference) day
  Sep 2026, September, 2026, 2026-09, 09/2026                  month
  early March 2026, mid-March 2026, first week of March 2026   month
  last week, last month (with a reference)                     month
  Q1 2026, Jan-Mar 2026                                        quarter
  2026, FY 2025-26, 2025-26 (fiscal year starts 1 April)       year
  "soon", "recently", empty, 31/02/2026                        unknown
"""
from __future__ import annotations

import difflib
import re
from datetime import date, datetime, timedelta, timezone

IST = timezone(timedelta(hours=5, minutes=30))

MONTH_NAMES = ["january", "february", "march", "april", "may", "june", "july", "august",
               "september", "october", "november", "december"]
_MONTH_WORD = r"([a-z]{3,10})\.?"
_NOT_MONTHS = {"mon", "tue", "tues", "wed", "thu", "thur", "thurs", "fri", "sat", "sun", "the", "updated", "published",
               "ist", "est", "utc", "gmt", "last", "early", "late", "mid", "week", "first", "second", "third", "fourth"}


def month_number(word: str):
    """'sep', 'sept', 'september' and close misspellings ('septmber', 'febuary') -> 9, 2. Else None."""
    w = word.lower().strip(".")
    if w in _NOT_MONTHS or len(w) < 3:
        return None
    for i, name in enumerate(MONTH_NAMES, 1):
        if name.startswith(w) or (w == "sept" and i == 9):
            return i
    if len(w) >= 5:
        close = difflib.get_close_matches(w, MONTH_NAMES, n=1, cutoff=0.8)
        if close:
            return MONTH_NAMES.index(close[0]) + 1
    return None


def to_ist_date(iso_timestamp: str) -> date:
    dt = datetime.fromisoformat(iso_timestamp.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(IST).date()


def _year(y: str) -> int:
    n = int(y)
    return n if len(y) == 4 else (2000 + n if n <= 69 else 1900 + n)   # 26 -> 2026, 98 -> 1998


def _day(y, m, d):
    return date(y, m, d).isoformat(), "day"


def parse_date(raw, today: date | None = None) -> tuple[str, str]:
    """Parse a loose date string. Returns (ISO date or "", precision).

    >>> parse_date("2026-07-07T20:30:00+00:00")
    ('2026-07-08', 'day')
    >>> parse_date("21st Septmber, 2026"), parse_date("Updated: Nov 10, 2026 10:30 IST"), parse_date("21-09-26")
    (('2026-09-21', 'day'), ('2026-11-10', 'day'), ('2026-09-21', 'day'))
    >>> parse_date("mid-March 2026"), parse_date("Q1 2026"), parse_date("FY 2025-26"), parse_date("last week")
    (('2026-03-01', 'month'), ('2026-01-01', 'quarter'), ('2025-04-01', 'year'), ('', 'unknown'))
    >>> parse_date("yesterday", today=date(2026, 11, 10))
    ('2026-11-09', 'day')
    """
    if raw is None or not str(raw).strip():
        return "", "unknown"
    s = str(raw).strip()
    low = s.lower()
    try:
        # machine timestamps
        if re.match(r"\d{4}-\d{2}-\d{2}[t ]\d{2}:\d{2}", low):
            return to_ist_date(s.replace(" ", "T", 1)).isoformat(), "day"
        if re.fullmatch(r"\d{10}|\d{13}", s):
            return datetime.fromtimestamp(int(s[:10]), IST).date().isoformat(), "day"

        # relative phrases need to know when they were written
        if today is not None:
            if re.search(r"\btoday\b|\bjust now\b|\b\d+\s*(?:hours?|hrs?|minutes?|mins?)\s+ago\b", low):
                return today.isoformat(), "day"
            if "yesterday" in low:
                return (today - timedelta(days=1)).isoformat(), "day"
            m = re.search(r"\b(\d{1,3})\s+days?\s+ago\b", low)
            if m:
                return (today - timedelta(days=int(m[1]))).isoformat(), "day"
            if re.search(r"\blast week\b|\b\d+\s+weeks?\s+ago\b", low):
                d = today - timedelta(days=7)
                return d.replace(day=1).isoformat(), "month"
            if "last month" in low:
                d = today.replace(day=1) - timedelta(days=1)
                return d.replace(day=1).isoformat(), "month"

        # fully numeric
        m = re.search(r"\b(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})\b", s)
        if m:
            return _day(int(m[1]), int(m[2]), int(m[3]))
        m = re.search(r"\b(\d{1,2})[-/.](\d{1,2})[-/.](\d{4}|\d{2})\b", s)
        if m:
            a, b, y = int(m[1]), int(m[2]), _year(m[3])
            if b > 12 >= a:               # 09/21/2026 can only be month first
                a, b = b, a
            return _day(y, b, a)

        # day, month name, year in either order
        for m in re.finditer(rf"\b(\d{{1,2}})(?:st|nd|rd|th)?[\s,.-]+{_MONTH_WORD}[\s,.-]+(\d{{4}})\b", low):
            mon = month_number(m[2])
            if mon:
                return _day(int(m[3]), mon, int(m[1]))
        for m in re.finditer(rf"\b{_MONTH_WORD}\s+(\d{{1,2}})(?:st|nd|rd|th)?[\s,]+(\d{{4}})\b", low):
            mon = month_number(m[1])
            if mon:
                return _day(int(m[3]), mon, int(m[2]))

        # quarter
        m = re.search(r"\bq([1-4])[\s,-]*(\d{4})\b", low)
        if m:
            return date(int(m[2]), 3 * int(m[1]) - 2, 1).isoformat(), "quarter"
        m = re.search(rf"\b{_MONTH_WORD}\s*(?:-|to|–)\s*{_MONTH_WORD}[\s,]+(\d{{4}})\b", low)
        if m and month_number(m[1]) and month_number(m[2]) and month_number(m[2]) - month_number(m[1]) == 2:
            return date(int(m[3]), month_number(m[1]), 1).isoformat(), "quarter"

        # month and year (also "early March 2026", "first week of March 2026")
        for m in re.finditer(rf"\b{_MONTH_WORD}[\s,]+(\d{{4}})\b", low):
            mon = month_number(m[1])
            if mon:
                return date(int(m[2]), mon, 1).isoformat(), "month"
        m = re.fullmatch(r"(\d{4})[-/](\d{1,2})", s)
        if m and 1 <= int(m[2]) <= 12 and int(m[2]) != int(m[1]) % 100 + 1:   # "2025-26" is a fiscal year, not month 26
            return date(int(m[1]), int(m[2]), 1).isoformat(), "month"
        m = re.fullmatch(r"(\d{1,2})/(\d{4})", s)
        if m:
            return date(int(m[2]), int(m[1]), 1).isoformat(), "month"

        # fiscal year, then bare year
        m = re.search(r"\b(?:fy\s*)?(20\d{2})\s*[-/–]\s*(\d{2}|20\d{2})\b", low)
        if m and _year(m[2]) == int(m[1]) + 1:
            return date(int(m[1]), 4, 1).isoformat(), "year"
        m = re.fullmatch(r"(?:fy\s*)?((?:19|20)\d{2})", low)
        if m:
            return date(int(m[1]), 1, 1).isoformat(), "year"
    except (ValueError, OverflowError, OSError):
        pass   # impossible dates such as 31/02/2026 fall through to unknown
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
