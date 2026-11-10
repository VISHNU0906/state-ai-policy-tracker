"""Measure the deduplication rule against hand-labelled headline pairs.

Two modes:

  python -m scripts.eval_dedupe sample   write data/review/dedup_pairs_unlabelled.csv
                                         (same-state pairs within the date window,
                                         spread evenly across similarity bands so
                                         easy and hard cases are both present)
  python -m scripts.eval_dedupe          score data/review/dedup_pairs.csv

A pair is labelled 1 when both headlines report the same announcement, 0 when
they report different ones. A follow-up (a deal cancelled days after it was
signed) and a different item from the same budget speech both count as 0.

Scoring clusters the whole corpus at each threshold and asks of every
labelled pair: did the two headlines land in the same cluster? Even-numbered
pairs are used to choose the threshold, odd-numbered pairs to report it, so
the reported figure is not fitted to the pairs it is measured on.
"""
import csv
import json
import random
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pipeline import config, dedupe, relevance  # noqa: E402
from pipeline.build import TITLE_TAIL  # noqa: E402
from pipeline.dates import parse_date  # noqa: E402

PAIRS = config.REVIEW / "dedup_pairs.csv"
BANDS = [(0.0, 0.1), (0.1, 0.2), (0.2, 0.3), (0.3, 0.4), (0.4, 0.5), (0.5, 0.7), (0.7, 1.01)]


def kept_items():
    out = []
    for line in (config.INTERIM / "raw_items.jsonl").open(encoding="utf-8"):
        it = json.loads(line)
        a = relevance.assess(TITLE_TAIL.sub("", it["title"]).strip(), it.get("description", ""), it.get("source_name", ""))
        day = parse_date(it.get("published_utc"))[0]
        if a["keep"] and day and a["state"] in config.PRIORITY_STATES:
            out.append({"state": a["state"], "date": day, "title": it["title"]})
    out.sort(key=lambda r: (r["state"], r["date"], r["title"]))
    return out


def sample(per_band: int = 20, seed: int = 11):
    items = kept_items()
    toks = [dedupe.tokens(i["title"]) for i in items]
    idf = dedupe.build_idf(toks)
    days = [date.fromisoformat(i["date"]).toordinal() for i in items]
    buckets = {b: [] for b in BANDS}
    for a in range(len(items)):
        for b in range(a + 1, len(items)):
            if items[a]["state"] != items[b]["state"] or abs(days[a] - days[b]) > config.DEDUP_WINDOW_DAYS:
                continue
            if items[a]["title"].lower() == items[b]["title"].lower():
                continue   # identical headlines are trivial; leave them out of the test
            s = dedupe.similarity(toks[a], toks[b], idf)
            for lo, hi in BANDS:
                if lo <= s < hi:
                    buckets[(lo, hi)].append((items[a], items[b]))
    rng = random.Random(seed)
    rows = []
    for pairs in buckets.values():
        for x, y in rng.sample(pairs, min(per_band, len(pairs))):
            rows.append({"state": x["state"], "date_a": x["date"], "date_b": y["date"],
                         "title_a": x["title"], "title_b": y["title"], "same_event": ""})
    out = config.REVIEW / "dedup_pairs_unlabelled.csv"
    config.REVIEW.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {len(rows)} pairs to {out}")


def score():
    rows = [r for r in csv.DictReader(PAIRS.open(encoding="utf-8-sig")) if r["same_event"] in ("0", "1")]
    items = kept_items()
    index = {(i["state"], i["date"], i["title"]): n for n, i in enumerate(items)}
    pairs = []
    for r in rows:
        a = index.get((r["state"], r["date_a"], r["title_a"]))
        b = index.get((r["state"], r["date_b"], r["title_b"]))
        if a is not None and b is not None:
            pairs.append((a, b, r["same_event"] == "1"))
    print(f"{len(pairs)} of {len(rows)} labelled pairs found in the corpus, {sum(y for *_, y in pairs)} same-event")
    print("threshold | tune half  P    R    F1 | test half  P    R    F1 | records")
    for t in [0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50]:
        clusters = dedupe.cluster(items, threshold=t)
        home = {i: n for n, c in enumerate(clusters) for i in c}
        out = []
        for half in (0, 1):
            sub = pairs[half::2]
            tp = sum(1 for a, b, y in sub if home[a] == home[b] and y)
            fp = sum(1 for a, b, y in sub if home[a] == home[b] and not y)
            pos = sum(1 for *_, y in sub if y)
            p = tp / (tp + fp) if tp + fp else 0.0
            r = tp / pos if pos else 0.0
            out.append(f"{p:.2f} {r:.2f} {2 * p * r / (p + r) if p + r else 0:.2f}")
        mark = "  <- in use" if abs(t - config.DEDUP_THRESHOLD) < 1e-9 else ""
        print(f"   {t:.2f}   |         {out[0]} |         {out[1]} | {len(clusters)}{mark}")


if __name__ == "__main__":
    sample() if sys.argv[1:] == ["sample"] else score()
