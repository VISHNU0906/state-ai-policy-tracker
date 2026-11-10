"""GDELT DOC 2.0 API adapter. Free, no key, independent of Google's index.

Used as the second backbone source: it finds articles Google News missed and
gives publisher URLs directly. Limits that shaped the code:
- One request every 5 seconds, otherwise HTTP 429.
- Search terms shorter than 3 letters are rejected, so "AI" cannot be used
  as a keyword. We search for the phrase "artificial intelligence" instead,
  which means GDELT only finds stories that spell the term out.
- At most 250 records per request, so we query in two-month windows.
- `seendate` is when GDELT first crawled the page, usually the publish day.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path

from .base import cached_json, item

API = "https://api.gdeltproject.org/api/v2/doc/doc"


def search(state: str, start: date, end: date, cache_dir: Path) -> list[dict]:
    query = f'"{state}" "artificial intelligence" sourcecountry:IN sourcelang:english'
    params = {
        "query": query, "mode": "artlist", "format": "json", "maxrecords": 250, "sort": "datedesc",
        "startdatetime": start.strftime("%Y%m%d000000"), "enddatetime": end.strftime("%Y%m%d000000"),
    }
    key = f"gdelt|{query}|{start}|{end}"
    try:
        data = cached_json(cache_dir, key, API, params, delay=0.0, pre_delay=6.5, backoff=20.0, retries=3)
    except ValueError:
        return []  # GDELT answers with plain text, not JSON, when a query has no matches
    out = []
    for a in data.get("articles", []):
        seen = a.get("seendate", "")
        ts = datetime.strptime(seen, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc).isoformat() if seen else ""
        out.append(item(title=a.get("title", "").strip(), url=a.get("url", ""), source_domain=a.get("domain", ""),
                        published_utc=ts, origin="gdelt"))
    return out
