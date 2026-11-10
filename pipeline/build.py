"""Stages 2 to 6. Turn raw items into the final dataset.

  filter     relevance rules and state attribution   (pipeline/relevance.py)
  dedupe     one record per announcement             (pipeline/dedupe.py)
  enrich     publisher URL, summary, page date       (pipeline/enrich.py)
  classify   category, sector, government level      (pipeline/taxonomy.py)
  review     apply hand corrections, if any          (data/review/overrides.csv)
  export     CSV, XLSX, rejected log, site JSON      (pipeline/export.py)

Run:  python -m pipeline.build              (uses cached pages where present)
      python -m pipeline.build --no-enrich  (skip page fetches; fast dry run)
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
import sys
from collections import Counter

from . import config, dedupe, enrich, export, llm, relevance, taxonomy
from .dates import date_from_url, parse_date
from .sources.base import load_env
from .states import BY_NAME

# Outlets preferred as the representative article for an event: wire services
# and established dailies first, press-release wires last.
PREFERRED = {s.lower() for s in """
PIB|PTI|ANI|ANI News|The Hindu|The Indian Express|The Times of India|Times of India|Hindustan Times|The Economic Times
|Business Standard|Mint|Deccan Herald|The New Indian Express|NDTV|India Today|Moneycontrol.com|The Hindu BusinessLine
|Telangana Today|Deccan Chronicle|ThePrint|Scroll.in|The News Minute|MediaNama|ETGovernment.com|ET Government|ET Education
|ET CIO|ET Enterprise AI|Onmanorama|Mathrubhumi English|The Assam Tribune|Sentinel Assam|OdishaTV|Odisha Bytes
|Free Press Journal|The Federal|The Week|Outlook Business|Business Today|News18|Firstpost|India Today NE
""".replace("\n", "").split("|")}
LOW = ("pr newswire", "business wire", "businesswire", "newswire", "ani pr", "pnn", "tribune india pr")


TITLE_TAIL = re.compile(r"\s+[|–]\s+[^|–]{3,40}$")


def source_rank(name: str) -> int:
    n = (name or "").lower()
    if n in PREFERRED:
        return 0
    return 2 if any(w in n for w in LOW) else 1


def record_id(state: str, day: str, title: str) -> str:
    h = hashlib.sha1(f"{state}|{title.lower().strip()}".encode()).hexdigest()[:6]
    return f"{BY_NAME[state].code}-{day}-{h}"


def load_overrides() -> dict:
    path = config.REVIEW / "overrides.csv"
    if not path.exists():
        return {}
    with path.open(encoding="utf-8", newline="") as f:
        return {r["record_id"]: r for r in csv.DictReader(f)}


def pick_summary(title: str, page: dict) -> tuple[str, str]:
    """One line saying what happened. Prefer the publisher's own description."""
    tkey = set(dedupe.tokens(title))
    for basis in ("description", "body_lead"):
        text = enrich.first_sentences(page.get(basis, ""), 240)
        # A description that only repeats the headline adds nothing.
        if len(text) >= 60 and len(set(dedupe.tokens(text)) - tkey) >= 4:
            return text, "publisher_description" if basis == "description" else "article_text"
    return title, "headline"


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    do_enrich = "--no-enrich" not in argv
    load_env(config.ROOT)

    raw = [json.loads(l) for l in (config.INTERIM / "raw_items.jsonl").open(encoding="utf-8")]
    funnel = Counter(raw_items=len(raw))
    kept, rejected = [], []

    for it in raw:
        it["title"] = TITLE_TAIL.sub("", it["title"]).strip()      # "... | India News" and similar section tags
        day, precision = parse_date(it.get("published_utc"))
        if not day:
            day, precision = date_from_url(it.get("url", ""))
        a = relevance.assess(it["title"], it.get("description", ""), it.get("source_name", ""))
        reason = a["reason"]
        if a["keep"] and a["state"] not in config.PRIORITY_STATES:
            reason = "state_not_prioritised"
        if a["keep"] and not day:
            reason = "no_date"   # cannot be placed on a timeline or deduplicated; listed, not hidden
        row = {**it, "date": day, "date_precision": precision, "state": a["state"], "state_basis": a["state_basis"],
               "confidence": a["confidence"], "reason": reason}
        (kept if reason == "kept" else rejected).append(row)
    funnel["passed_relevance"] = len(kept)

    clusters = dedupe.cluster(kept)
    funnel["events_after_dedupe"] = len(clusters)

    overrides = load_overrides()
    records = []
    for n, members in enumerate(clusters, 1):
        group = sorted((kept[i] for i in members), key=lambda r: (r["date"], r["title"]))
        seed = group[0]
        rid = record_id(seed["state"], seed["date"], seed["title"])
        ov = overrides.get(rid, {})
        if ov.get("decision") == "drop":
            for r in group:
                rejected.append({**r, "reason": "dropped_in_review:" + (ov.get("note") or "")})
            continue

        ranked = sorted(group, key=lambda r: (source_rank(r["source_name"]), r["date"], r["title"]))
        rep, page = ranked[0], {}
        if do_enrich:
            for cand in ranked[:3]:                 # fall back to the next outlet if a page is blocked
                page = enrich.enrich(cand)
                rep = cand
                if page.get("fetch_status", "").startswith("ok"):
                    break
            if n % 50 == 0:
                print(f"enriched {n}/{len(clusters)}", flush=True)
        desc = page.get("description", "") or rep.get("description", "")
        summary, basis = pick_summary(rep["title"], page or {"description": desc})
        outlets = []
        for r in group:
            if r["source_name"] and r["source_name"] not in outlets:
                outlets.append(r["source_name"])

        rec = {
            "record_id": rid,
            "state": seed["state"],
            "date": seed["date"],                    # earliest report, India time
            "date_precision": seed["date_precision"],
            "title": rep["title"],
            "summary": summary,
            "category": taxonomy.categorise(rep["title"], desc),
            "sector": taxonomy.sector(rep["title"], desc),
            "gov_level": taxonomy.gov_level(rep["title"]),
            "source_name": rep["source_name"],
            "source_url": page.get("url") or rep.get("url") or rep.get("google_link", ""),
            "n_outlets": len(outlets),
            "other_outlets": "; ".join(o for o in outlets if o != rep["source_name"]),
            "confidence": "high" if any(r["confidence"] == "high" for r in group) else "medium",
            "summary_basis": basis,
            "review_status": "auto",
            "_body": page.get("body_lead", ""),
            "_origins": sorted({r["origin"] for r in group}),
            "_fetch": page.get("fetch_status", "not_fetched"),
        }
        for field in ("state", "category", "sector", "gov_level", "summary", "date", "date_precision"):
            if ov.get(field):
                rec[field] = ov[field]
        if ov:
            rec["review_status"] = "reviewed"
            if ov.get("summary"):
                rec["summary_basis"] = "written_in_review"
        records.append(rec)

    records = llm.refine(records)                    # no-op unless ANTHROPIC_API_KEY is set
    records.sort(key=lambda r: (r["date"], r["state"], r["title"]), reverse=True)
    funnel["final_records"] = len(records)
    funnel["dropped_in_review"] = len(clusters) - len(records)
    export.write_all(records, rejected, dict(funnel))
    print(dict(funnel))
    print("reject reasons:", Counter(r["reason"].split(":")[0] for r in rejected).most_common())


if __name__ == "__main__":
    main()
