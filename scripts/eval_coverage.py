"""Coverage check against an independently researched reference list.

data/review/reference_events.csv is a list of state AI policy events that was
researched by hand, separately from this pipeline, mostly from official
documents (cabinet notes, budgets, gazettes) and partner press releases. It
was not used to build or tune the pipeline, which makes it a fair test of
recall: for each reference event that falls inside our states and window,
did the pipeline end up with a record for it?

Each reference event gets one of three outcomes:
  in_dataset   a final record matches it
  rejected     a matching news item was collected but a rule dropped it
               (the reason code shows which rule to look at)
  not_found    nothing similar was collected at all (a sourcing gap: the
               event was not reported in the English news we search, or was
               reported in words our queries do not reach)

Matching is by state, date proximity and headline similarity, so it is
approximate. The output file lists the best match for every reference event
so each outcome can be checked by eye.

Run:  python -m scripts.eval_coverage
"""
import csv
import sys
from collections import Counter
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pipeline import config, dedupe  # noqa: E402
from pipeline.dates import parse_date  # noqa: E402

MATCH = 0.30          # minimum similarity to call two headlines the same event
DAY_SLACK = {"day": 21, "month": 45, "year": 400}   # news can trail the formal date by weeks


def _load(path):
    with path.open(encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def main():
    ref = _load(config.REVIEW / "reference_events.csv")
    sources = _load(config.OUT / "record_sources.csv")
    records = {r["record_id"]: r for r in _load(config.OUT / "records.csv")}
    rejected = [r for r in _load(config.OUT / "rejected.csv") if r["state"]]

    for s in sources:
        s["state"] = records[s["record_id"]]["state"]
    idf = dedupe.build_idf([dedupe.tokens(x["title"]) for x in sources + rejected])

    def best(event, pool):
        text = dedupe.tokens(event["title"] + " " + event.get("initiative", ""))
        slack = DAY_SLACK.get(event["date_precision"])
        iso = parse_date(event["date"])[0]          # the reference list writes month-only dates as "2026-07"
        ev_day = date.fromisoformat(iso).toordinal() if iso and slack else None
        top = (0.0, None)
        for x in pool:
            if x["state"] != event["state"]:
                continue
            if ev_day and x.get("date") and abs(date.fromisoformat(x["date"]).toordinal() - ev_day) > slack:
                continue
            sim = dedupe.similarity(text, dedupe.tokens(x["title"]), idf)
            if sim > top[0]:
                top = (sim, x)
        return top

    rows, tally = [], Counter()
    for ev in ref:
        in_scope = ev["state"] in config.PRIORITY_STATES and (not ev["date"] or ev["date"] >= config.START.isoformat())
        if not in_scope:
            tally["out_of_scope"] += 1
            continue
        s1, m1 = best(ev, sources)
        s2, m2 = best(ev, rejected)
        if s1 >= MATCH:
            outcome, match, detail = "in_dataset", m1, m1["record_id"]
        elif s2 >= MATCH:
            outcome, match, detail = "rejected", m2, m2["reason"]
        else:
            outcome, match, detail = "not_found", (m1 or m2), ""
        tally[outcome] += 1
        rows.append({"reference_id": ev["id"], "state": ev["state"], "reference_date": ev["date"], "reference_title": ev["title"],
                     "has_primary_source": ev.get("has_primary_source", ""), "outcome": outcome, "detail": detail,
                     "similarity": f"{max(s1, s2):.2f}", "best_match_title": match["title"] if match else "",
                     "best_match_date": match.get("date", "") if match else ""})

    out = config.REVIEW / "coverage_check.csv"
    with out.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

    n = len(rows)
    print(f"reference events: {len(ref)} total, {n} inside our states and window, {tally['out_of_scope']} outside")
    for k in ("in_dataset", "rejected", "not_found"):
        print(f"  {k:11s} {tally[k]:3d}  ({tally[k] / n:.0%})")
    by_state = Counter((r["state"], r["outcome"]) for r in rows)
    for st in sorted({r["state"] for r in rows}):
        print(f"  {st:16s} in={by_state[(st, 'in_dataset')]} rejected={by_state[(st, 'rejected')]} not_found={by_state[(st, 'not_found')]}")
    print("reject reasons:", Counter(r["detail"].split(":")[0] for r in rows if r["outcome"] == "rejected").most_common())
    print("wrote", out)


if __name__ == "__main__":
    main()
