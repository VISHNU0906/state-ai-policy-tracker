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
from concurrent.futures import ThreadPoolExecutor

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


# "BENGALURU: ...", "New Delhi, Nov 10 (PTI): ..." at the start of a description
DATELINE = re.compile(
    r"^[A-Z][A-Za-z.]+(?: [A-Z][A-Za-z.]+)?(?:, [A-Z][a-z]{2,8}\.? \d{1,2})?(?: \((?:PTI|ANI|IANS|UNI)\))?\s*:\s+")
TITLE_TAIL = re.compile(r"\s+[|–]\s+[^|–]{3,40}$")


def source_rank(name: str) -> int:
    n = (name or "").lower()
    if n in PREFERRED:
        return 0
    return 2 if any(w in n for w in LOW) else 1


def rank_group(group: list[dict], idf: dict) -> list[dict]:
    """Order the reports of one event by how well each would represent it.

    First choice is the headline most like all the others (the typical wording of the
    story, not an outlier angle), skipping press-release wires. Ties go to the
    preferred outlets, then to the earliest report.
    """
    toks = [dedupe.tokens(r["title"]) for r in group]

    def centrality(i):
        if len(group) == 1:
            return 0.0
        return sum(dedupe.similarity(toks[i], toks[j], idf) for j in range(len(group)) if j != i) / (len(group) - 1)

    order = sorted(range(len(group)), key=lambda i: (
        source_rank(group[i]["source_name"]) == 2, -round(centrality(i), 2),
        source_rank(group[i]["source_name"]), group[i]["date"], group[i]["title"]))
    return [group[i] for i in order]


def record_id(state: str, day: str, title: str) -> str:
    h = hashlib.sha1(f"{state}|{title.lower().strip()}".encode()).hexdigest()[:6]
    return f"{BY_NAME[state].code}-{day}-{h}"


def load_overrides() -> dict:
    path = config.REVIEW / "overrides.csv"
    if not path.exists():
        return {}
    with path.open(encoding="utf-8-sig", newline="") as f:   # utf-8-sig: the file is often saved from Excel
        return {r["record_id"]: r for r in csv.DictReader(f)}


def pick_summary(title: str, page: dict) -> tuple[str, str]:
    """One line saying what happened. Prefer the publisher's own description."""
    tkey = set(dedupe.tokens(title))
    for basis in ("description", "body_lead"):
        text = DATELINE.sub("", (page.get(basis) or "").strip())
        text = enrich.first_sentences(text, 240)
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
        if a["keep"] and day and not (config.START.isoformat() <= day <= config.END.isoformat()):
            reason = "outside_window"   # sources without date filters (Bing, GDELT) can return older stories
        if a["keep"] and not day:
            reason = "no_date"   # cannot be placed on a timeline or deduplicated; listed, not hidden
        row = {**it, "date": day, "date_precision": precision, "state": a["state"], "state_basis": a["state_basis"],
               "confidence": a["confidence"], "reason": reason}
        (kept if reason == "kept" else rejected).append(row)
    funnel["passed_relevance"] = len(kept)

    clusters = dedupe.cluster(kept)
    idf = dedupe.build_idf([dedupe.tokens(r["title"]) for r in kept])
    funnel["events_after_dedupe"] = len(clusters)

    overrides, seen_drop = load_overrides(), set()
    if do_enrich:
        # Fetch the first-choice page of every event up front, a few at a time. Results land in
        # the on-disk cache, so the loop below reads them back instantly and in a fixed order.
        first = [rank_group([kept[i] for i in members], idf)[0] for members in clusters]
        with ThreadPoolExecutor(max_workers=4) as pool:
            for n, _ in enumerate(pool.map(enrich.enrich, first), 1):
                if n % 50 == 0:
                    print(f"fetched {n}/{len(first)} pages", flush=True)
    records = []
    for n, members in enumerate(clusters, 1):
        group = sorted((kept[i] for i in members), key=lambda r: (r["date"], r["title"]))
        seed = group[0]
        rid = record_id(seed["state"], seed["date"], seed["title"])
        ov = overrides.get(rid, {})
        if ov.get("decision") == "drop":
            seen_drop.add(rid)
            for r in group:
                rejected.append({**r, "reason": "dropped_in_review:" + (ov.get("note") or "")})
            continue

        ranked = rank_group(group, idf)
        rep, page = ranked[0], {}
        if do_enrich:
            for cand in ranked[:3]:                 # fall back to the next outlet if a page is blocked
                page = enrich.enrich(cand)
                rep = cand
                if page.get("fetch_status", "").startswith("ok"):
                    break
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
            "stage": taxonomy.stage(rep["title"]),
            "sector": taxonomy.sector(rep["title"], desc),
            "gov_level": taxonomy.gov_level(rep["title"]),
            "source_name": rep["source_name"],
            "source_url": page.get("url") or rep.get("url") or rep.get("google_link", ""),
            "n_outlets": len(outlets),
            "other_outlets": "; ".join(o for o in outlets if o != rep["source_name"]),
            "confidence": "high" if any(r["confidence"] == "high" for r in group) else "medium",
            "summary_basis": basis,
            # Every record's headline was read once in the review pass that produced overrides.csv.
            "review_status": "reviewed" if overrides else "auto",
            "_body": page.get("body_lead", ""),
            "_members": [{"source_name": r["source_name"], "title": r["title"], "date": r["date"],
                          "link": r.get("url") or r.get("google_link", ""), "origin": r["origin"],
                          "is_representative": int(r is rep)} for r in group],
            "_origins": sorted({r["origin"] for r in group}),
            "_fetch": page.get("fetch_status", "not_fetched"),
        }
        for field in ("state", "category", "stage", "sector", "gov_level", "summary", "date", "date_precision"):
            if ov.get(field):
                rec[field] = ov[field]
        if ov:
            rec["review_status"] = "reviewed"
            if ov.get("summary"):
                rec["summary_basis"] = "written_in_review"
        records.append(rec)

    unused = set(overrides) - {r["record_id"] for r in records} - seen_drop
    if unused:
        print(f"WARNING: {len(unused)} review overrides match no record: {sorted(unused)[:10]}")
    records = llm.refine(records)                    # no-op unless ANTHROPIC_API_KEY is set
    records.sort(key=lambda r: (r["date"], r["state"], r["title"]), reverse=True)
    funnel["final_records"] = len(records)
    funnel["dropped_in_review"] = len(clusters) - len(records)
    export.write_all(records, rejected, dict(funnel))
    print(dict(funnel))
    print("reject reasons:", Counter(r["reason"].split(":")[0] for r in rejected).most_common())


if __name__ == "__main__":
    main()
