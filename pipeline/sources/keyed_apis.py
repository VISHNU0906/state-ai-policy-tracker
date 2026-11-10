"""Adapters for news APIs that need a key: GNews.io, NewsAPI.org, NewsData.io.

Role: redundancy for the most recent month. Their free plans cannot serve a
22 month backfill (NewsAPI.org and GNews.io search only the last 30 days and
allow 100 requests a day; NewsData.io's free plan has no archive), so they
run one query per state and add whatever the backbone sources missed.

Each adapter is skipped, with a log line, when its key is not in the
environment or in .env. Keys are never written to the cache or to logs.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

from .base import cached_json, item

Q = '"{state}" AND (AI OR "artificial intelligence")'


def _iso(s: str) -> str:
    if not s:
        return ""
    s = s.replace("Z", "+00:00").replace(" ", "T")
    dt = datetime.fromisoformat(s)
    return (dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)).isoformat()


def gnews_io(state: str, cache_dir: Path, day: str) -> list[dict]:
    key = os.environ.get("GNEWS_API_KEY")
    if not key:
        return []
    q = Q.format(state=state)
    data = cached_json(cache_dir, f"gnews_io|{q}|{day}", "https://gnews.io/api/v4/search",
                       {"q": q, "lang": "en", "country": "in", "max": 10, "apikey": key})
    return [item(title=a.get("title"), description=a.get("description"), url=a.get("url"),
                 source_name=(a.get("source") or {}).get("name"), published_utc=_iso(a.get("publishedAt", "")),
                 origin="gnews_io") for a in data.get("articles", [])]


def newsapi_org(state: str, cache_dir: Path, day: str) -> list[dict]:
    key = os.environ.get("NEWSAPI_KEY")
    if not key:
        return []
    q = Q.format(state=state)
    data = cached_json(cache_dir, f"newsapi_org|{q}|{day}", "https://newsapi.org/v2/everything",
                       {"q": q, "language": "en", "sortBy": "publishedAt", "pageSize": 100, "apiKey": key})
    return [item(title=a.get("title"), description=a.get("description"), url=a.get("url"),
                 source_name=(a.get("source") or {}).get("name"), published_utc=_iso(a.get("publishedAt", "")),
                 origin="newsapi_org") for a in data.get("articles", [])]


def newsdata_io(state: str, cache_dir: Path, day: str) -> list[dict]:
    key = os.environ.get("NEWSDATA_API_KEY")
    if not key:
        return []
    q = Q.format(state=state)
    data = cached_json(cache_dir, f"newsdata_io|{q}|{day}", "https://newsdata.io/api/1/latest",
                       {"q": q, "country": "in", "language": "en", "apikey": key})
    return [item(title=a.get("title"), description=a.get("description"), url=a.get("link"),
                 source_name=a.get("source_name") or a.get("source_id"), published_utc=_iso(a.get("pubDate", "")),
                 origin="newsdata_io") for a in data.get("results", [])]


ADAPTERS = {"gnews_io": ("GNEWS_API_KEY", gnews_io), "newsapi_org": ("NEWSAPI_KEY", newsapi_org),
            "newsdata_io": ("NEWSDATA_API_KEY", newsdata_io)}
