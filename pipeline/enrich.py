"""Stage 4. Read the publisher page for one article.

For the article chosen to represent each event we need three things the
search sources do not reliably give: the publisher URL, a real summary
sentence, and a publish date to cross-check the feed date.

Steps, each cached on disk under data/raw/pages/:
1. Resolve the Google News redirect to the publisher URL (googlenewsdecoder).
2. Fetch the page and extract description, publish date and body text with
   trafilatura, which runs locally and needs no key.
3. If the fetch is blocked and TAVILY_API_KEY is set, ask Tavily's extract
   endpoint for the page text instead. Without a key this step is skipped
   and the record keeps the headline as its summary, flagged as such.

Failures are recorded, never raised: a paywalled page must not stop the run.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import time
from pathlib import Path

import requests

from . import config

CACHE = config.RAW / "pages"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"}


def _cache_file(key: str) -> Path:
    CACHE.mkdir(parents=True, exist_ok=True)
    return CACHE / (hashlib.sha1(key.encode()).hexdigest()[:16] + ".json")


def resolve_google_link(google_link: str) -> str:
    from googlenewsdecoder import gnewsdecoder
    try:
        res = gnewsdecoder(google_link, interval=1)
        return res.get("decoded_url", "") if res.get("status") or res.get("success") else ""
    except Exception:
        return ""


def _tavily_extract(url: str) -> str:
    key = os.environ.get("TAVILY_API_KEY")
    if not key:
        return ""
    try:
        r = requests.post("https://api.tavily.com/extract", json={"urls": [url]},
                          headers={"Authorization": f"Bearer {key}"}, timeout=60)
        results = r.json().get("results", [])
        return results[0].get("raw_content", "") if results else ""
    except Exception:
        return ""


def first_sentences(text: str, limit: int = 240) -> str:
    """Trim to whole sentences within `limit` characters."""
    text = re.sub(r"\s+", " ", text or "").strip()
    if len(text) <= limit:
        return text
    cut = text[:limit]
    end = max(cut.rfind(". "), cut.rfind("? "), cut.rfind("! "))
    return cut[: end + 1] if end > 60 else cut.rsplit(" ", 1)[0] + "..."


def enrich(item: dict) -> dict:
    """Return {url, description, body_lead, page_date, fetch_status} for one raw item."""
    key = item.get("url") or item["google_link"]
    path = _cache_file(key)
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))

    if os.environ.get("PIPELINE_OFFLINE") == "1":
        return {"url": item.get("url", ""), "description": item.get("description", ""),
                "body_lead": "", "page_date": "", "fetch_status": "offline_cache_miss"}

    import trafilatura

    out = {"url": item.get("url", ""), "description": item.get("description", ""), "body_lead": "",
           "page_date": "", "fetch_status": ""}
    if not out["url"]:
        out["url"] = resolve_google_link(item["google_link"])
        if not out["url"]:
            out["fetch_status"] = "redirect_unresolved"
            path.write_text(json.dumps(out), encoding="utf-8")
            return out
    try:
        resp = requests.get(out["url"], headers=UA, timeout=25)
        html = resp.text if resp.status_code == 200 else ""
        out["fetch_status"] = "ok" if html else f"http_{resp.status_code}"
    except Exception as exc:
        html, out["fetch_status"] = "", f"error_{type(exc).__name__}"

    if html:
        doc = trafilatura.bare_extraction(html, url=out["url"], with_metadata=True, favor_precision=True)
        if doc is not None:
            d = doc.as_dict() if hasattr(doc, "as_dict") else dict(doc)
            out["description"] = out["description"] or (d.get("description") or "")
            out["page_date"] = d.get("date") or ""
            out["body_lead"] = first_sentences(d.get("text") or "", 600)
    elif os.environ.get("TAVILY_API_KEY"):
        text = _tavily_extract(out["url"])
        if text:
            out["body_lead"] = first_sentences(text, 600)
            out["fetch_status"] += "+tavily"
    path.write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    time.sleep(0.5)
    return out
