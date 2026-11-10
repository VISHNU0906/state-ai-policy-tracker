"""Bing News RSS adapter. Free, no key.

Returns about a dozen recent items per query with the publisher URL and a
real one-sentence description. No date operators, so it only helps with the
most recent weeks. Used for extra recall on recent news, not for backfill.
"""
from __future__ import annotations

import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .base import cached_get, item

API = "https://www.bing.com/news/search"
NS = {"News": "https://www.bing.com/news/search?q=news&format=rss"}


def search(query: str, cache_dir: Path, day: str) -> list[dict]:
    xml = cached_get(cache_dir, f"bing|{query}|{day}", API,
                     {"q": query, "format": "rss", "cc": "IN", "setlang": "en-IN"}, delay=1.5)
    out = []
    for it in ET.fromstring(xml.encode("utf-8")).iter("item"):
        link = it.findtext("link") or ""
        real = parse_qs(urlparse(link).query).get("url", [link])[0]   # unwrap Bing's click-tracking link
        src = next((c.text for c in it if c.tag.endswith("Source")), "")
        pub = it.findtext("pubDate")
        out.append(item(title=(it.findtext("title") or "").strip(), description=(it.findtext("description") or "").strip(),
                        url=real, source_name=src or "", origin="bing_news_rss",
                        published_utc=parsedate_to_datetime(pub).isoformat() if pub else ""))
    return out
