"""Google News RSS search adapter.

Why this source: free, no key, indexes national dailies, regional English
papers and wire copy in one place, and supports `after:` / `before:` date
operators. Each query returns at most about 100 items, so the collector asks
one month at a time to stay under the cap.

What it does not give us: the publisher URL (links are Google redirects) and a
usable summary (the description is just the headline again). Both are filled
in later by pipeline/enrich.py.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import quote_plus

import requests

BASE = "https://news.google.com/rss/search?q={q}&hl=en-IN&gl=IN&ceid=IN:en"
HEADERS = {"User-Agent": "Mozilla/5.0 (research script; state AI policy tracker)"}
ITEM_CAP = 100  # observed ceiling per query


def _cache_path(cache_dir: Path, query: str) -> Path:
    return cache_dir / (hashlib.sha1(query.encode()).hexdigest()[:16] + ".json")


def search(query: str, cache_dir: Path, delay: float = 1.0, refresh: bool = False) -> list[dict]:
    """Run one search. Results are cached on disk so reruns are deterministic."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    path = _cache_path(cache_dir, query)
    if path.exists() and not refresh:
        return json.loads(path.read_text(encoding="utf-8"))["items"]
    if os.environ.get("PIPELINE_OFFLINE") == "1":
        raise RuntimeError("not in cache (offline run)")

    url = BASE.format(q=quote_plus(query))
    for attempt in range(4):
        resp = requests.get(url, headers=HEADERS, timeout=30)
        if resp.status_code == 200:
            break
        time.sleep(5 * (attempt + 1))  # back off on 429 / 5xx
    else:
        raise RuntimeError(f"Google News RSS failed ({resp.status_code}) for: {query}")

    items = []
    for it in ET.fromstring(resp.content).iter("item"):
        src = it.find("source")
        source_name = (src.text or "").strip() if src is not None else ""
        title = (it.findtext("title") or "").strip()
        # Google appends " - Publisher" to every headline. Strip it.
        if source_name and title.endswith(" - " + source_name):
            title = title[: -len(source_name) - 3].strip()
        pub = it.findtext("pubDate")
        items.append({
            "title": title,
            "source_name": source_name,
            "source_domain": (src.get("url") if src is not None else "") or "",
            "google_link": it.findtext("link") or "",
            "published_utc": parsedate_to_datetime(pub).isoformat() if pub else None,
            "origin": "google_news_rss",
        })
    path.write_text(json.dumps({"query": query, "items": items}, ensure_ascii=False, indent=1), encoding="utf-8")
    time.sleep(delay)
    return items
