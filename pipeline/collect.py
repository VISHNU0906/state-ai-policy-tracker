"""Stage 1. Collect raw headlines for every priority state, month by month.

Output: data/interim/raw_items.jsonl, one row per unique Google News item,
with the list of queries that returned it (kept for auditing recall).

Run:  python -m pipeline.collect
"""
from __future__ import annotations

import json
from datetime import date

from . import config
from .sources import google_news


def month_windows(start: date, end: date):
    """Yield (first_day, first_day_of_next_month) pairs covering start..end."""
    y, m = start.year, start.month
    while date(y, m, 1) <= end:
        ny, nm = (y + 1, 1) if m == 12 else (y, m + 1)
        yield date(y, m, 1), min(date(ny, nm, 1), date.fromordinal(end.toordinal() + 1))
        y, m = ny, nm


def state_term(state: str) -> str:
    alts = [f'"{state}"'] + config.SEARCH_ALIASES.get(state, [])
    return "(" + " OR ".join(alts) + ")" if len(alts) > 1 else alts[0]


def build_queries():
    for state in config.PRIORITY_STATES:
        for a, b in month_windows(config.START, config.END):
            for qid, tpl in config.QUERY_TEMPLATES.items():
                q = tpl.replace("{S}", state_term(state)) + f" after:{a.isoformat()} before:{b.isoformat()}"
                yield {"state_queried": state, "window": a.strftime("%Y-%m"), "qid": qid, "q": q}


def main():
    queries = list(build_queries())
    pool, at_cap, failed = {}, [], []
    for i, qq in enumerate(queries, 1):
        try:
            items = google_news.search(qq["q"], config.RAW / "google_news")
        except Exception as exc:  # one bad query must not sink the run; it is logged and reported
            failed.append({**qq, "error": str(exc)})
            continue
        if len(items) >= google_news.ITEM_CAP - 2:
            at_cap.append(qq)
        for it in items:
            row = pool.setdefault(it["google_link"], {**it, "found_by": []})
            row["found_by"].append(f'{qq["state_queried"]}|{qq["window"]}|{qq["qid"]}')
        if i % 50 == 0:
            print(f"{i}/{len(queries)} queries, {len(pool)} unique items", flush=True)

    config.INTERIM.mkdir(parents=True, exist_ok=True)
    with (config.INTERIM / "raw_items.jsonl").open("w", encoding="utf-8") as f:
        for row in pool.values():
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    log = {"queries": len(queries), "unique_items": len(pool), "queries_at_cap": at_cap, "failed_queries": failed}
    (config.INTERIM / "collect_log.json").write_text(json.dumps(log, indent=1), encoding="utf-8")
    print(f"done: {len(queries)} queries, {len(pool)} unique items, {len(at_cap)} at cap, {len(failed)} failed")


if __name__ == "__main__":
    main()
