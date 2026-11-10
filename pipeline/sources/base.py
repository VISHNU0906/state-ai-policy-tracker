"""Shared helpers for source adapters.

Every adapter returns a list of dicts with the same keys, so later stages do
not care where an item came from:

    title, source_name, source_domain, url, google_link, published_utc,
    description, origin

`url` is the publisher URL when the source gives it directly. Google News
gives only a redirect (`google_link`); pipeline/enrich.py resolves it.

All HTTP responses are cached on disk under data/raw/<adapter>/. A rerun with
a warm cache makes no network calls and produces identical output.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path
from urllib.parse import urlparse

import requests

HEADERS = {"User-Agent": "Mozilla/5.0 (research script; state AI policy tracker)"}
FIELDS = ("title", "source_name", "source_domain", "url", "google_link", "published_utc", "description", "origin")


def load_env(root: Path) -> None:
    """Read KEY=VALUE lines from .env into the environment (no extra dependency)."""
    env = root / ".env"
    if not env.exists():
        return
    for line in env.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            if v.strip():
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def item(**kw) -> dict:
    row = {f: kw.get(f) or "" for f in FIELDS}
    if row["url"] and not row["source_domain"]:
        row["source_domain"] = urlparse(row["url"]).netloc.removeprefix("www.")
    if not row["source_name"]:
        row["source_name"] = row["source_domain"]
    return row


def cached_get(cache_dir: Path, cache_key: str, url: str, params: dict | None = None, *,
               delay: float = 1.0, retries: int = 4, backoff: float = 6.0) -> str:
    """GET with an on-disk cache. `cache_key` must not contain secrets."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    path = cache_dir / (hashlib.sha1(cache_key.encode()).hexdigest()[:16] + ".txt")
    if path.exists():
        return path.read_text(encoding="utf-8")
    last = None
    for attempt in range(retries):
        resp = requests.get(url, params=params, headers=HEADERS, timeout=40)
        last = resp.status_code
        if resp.status_code == 200:
            path.write_text(resp.text, encoding="utf-8")
            time.sleep(delay)
            return resp.text
        if resp.status_code in (401, 403, 426):   # bad key or plan limit: retrying will not help
            break
        time.sleep(backoff * (attempt + 1))
    raise RuntimeError(f"HTTP {last} for {cache_key}")


def cached_json(*args, **kw):
    return json.loads(cached_get(*args, **kw))
