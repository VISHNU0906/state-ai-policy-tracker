"""Stage 1. Collect raw headlines for every priority state from every source.

Sources and their roles (details in each adapter's docstring):
  google_news_rss  backbone, full history, month by month
  gdelt            second backbone, full history, two-month windows
  bing_news_rss    recent weeks only
  gnews_io / newsapi_org / newsdata_io   recent month, only when a key is set

Output: data/interim/raw_items.jsonl, one row per unique item, and
data/interim/collect_log.json with per-source counts, queries that hit the
result cap, and failures. A failing source never stops the run; it is logged
and reported in the README numbers.

Run:  python -m pipeline.collect            (all sources)
      python -m pipeline.collect google_news_rss gdelt   (a subset)
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from datetime import date

from . import config
from .sources import base, bing_news, gdelt, google_news, keyed_apis


def month_windows(start: date, end: date, step: int = 1):
    """Yield (window_start, window_end) pairs of `step` months covering start..end."""
    y, m = start.year, start.month
    stop = date.fromordinal(end.toordinal() + 1)
    while date(y, m, 1) <= end:
        ny, nm = y + (m - 1 + step) // 12, (m - 1 + step) % 12 + 1
        yield date(y, m, 1), min(date(ny, nm, 1), stop)
        y, m = ny, nm


def state_term(state: str) -> str:
    alts = [f'"{state}"'] + config.SEARCH_ALIASES.get(state, [])
    return "(" + " OR ".join(alts) + ")" if len(alts) > 1 else alts[0]


class Pool:
    """Unique items keyed by link, remembering which query found each one."""

    def __init__(self):
        self.rows, self.per_source, self.failed, self.at_cap = {}, Counter(), [], []

    def add(self, items, tag):
        for it in items:
            key = it.get("url") or it.get("google_link")
            if not key or not it.get("title"):
                continue
            row = self.rows.setdefault(key, {**it, "found_by": []})
            row["found_by"].append(tag)
            self.per_source[it["origin"]] += 1


def run_google_news(pool: Pool):
    cache = config.RAW / "google_news"
    for state in config.PRIORITY_STATES:
        for a, b in month_windows(config.START, config.END):
            for qid, tpl in config.QUERY_TEMPLATES.items():
                q = tpl.replace("{S}", state_term(state)) + f" after:{a.isoformat()} before:{b.isoformat()}"
                tag = f"google_news_rss|{state}|{a:%Y-%m}|{qid}"
                try:
                    items = [base.item(**it, url="", description="") for it in google_news.search(q, cache)]
                except Exception as exc:
                    pool.failed.append({"tag": tag, "error": str(exc)})
                    continue
                if len(items) >= google_news.ITEM_CAP - 2:
                    pool.at_cap.append(tag)
                pool.add(items, tag)
        print(f"google_news_rss: {state} done, pool={len(pool.rows)}", flush=True)


def run_gdelt(pool: Pool):
    for state in config.PRIORITY_STATES:
        for a, b in month_windows(config.START, config.END, step=2):
            tag = f"gdelt|{state}|{a:%Y-%m}"
            try:
                items = gdelt.search(state, a, b, config.RAW / "gdelt")
            except Exception as exc:
                pool.failed.append({"tag": tag, "error": str(exc)})
                continue
            if len(items) >= 245:
                pool.at_cap.append(tag)
            pool.add(items, tag)
        print(f"gdelt: {state} done, pool={len(pool.rows)}", flush=True)


def run_bing(pool: Pool):
    day = config.END.isoformat()
    for state in config.PRIORITY_STATES:
        for qid, q in (("gov", f'"{state}" AI government'), ("policy", f'"{state}" "artificial intelligence" policy')):
            tag = f"bing_news_rss|{state}|{qid}"
            try:
                pool.add(bing_news.search(q, config.RAW / "bing_news", day), tag)
            except Exception as exc:
                pool.failed.append({"tag": tag, "error": str(exc)})


def run_keyed(pool: Pool, name: str):
    import os
    env_key, fn = keyed_apis.ADAPTERS[name]
    if not os.environ.get(env_key):
        print(f"{name}: skipped, {env_key} not set", flush=True)
        pool.failed.append({"tag": name, "error": f"skipped: {env_key} not set"})
        return
    day = config.END.isoformat()
    for state in config.PRIORITY_STATES:
        try:
            pool.add(fn(state, config.RAW / name, day), f"{name}|{state}")
        except Exception as exc:
            pool.failed.append({"tag": f"{name}|{state}", "error": str(exc)})


RUNNERS = {
    "google_news_rss": run_google_news,
    "gdelt": run_gdelt,
    "bing_news_rss": run_bing,
    **{n: (lambda pool, n=n: run_keyed(pool, n)) for n in keyed_apis.ADAPTERS},
}


def main(argv=None):
    base.load_env(config.ROOT)
    wanted = (argv or sys.argv[1:]) or list(RUNNERS)
    pool = Pool()
    for name in wanted:
        RUNNERS[name](pool)

    config.INTERIM.mkdir(parents=True, exist_ok=True)
    with (config.INTERIM / "raw_items.jsonl").open("w", encoding="utf-8") as f:
        for row in pool.rows.values():
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    log = {"sources_run": wanted, "unique_items": len(pool.rows), "hits_per_source": dict(pool.per_source),
           "queries_at_cap": pool.at_cap, "failed": pool.failed}
    (config.INTERIM / "collect_log.json").write_text(json.dumps(log, indent=1), encoding="utf-8")
    print(f"done: {len(pool.rows)} unique items; hits per source {dict(pool.per_source)}; "
          f"{len(pool.at_cap)} at cap; {len(pool.failed)} failed or skipped")


if __name__ == "__main__":
    main()
