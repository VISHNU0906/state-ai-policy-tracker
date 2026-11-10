"""Stage 3. Collapse many reports of one announcement into one record.

Problem: one announcement is reported by many outlets with different
headlines ("Karnataka to set up AI university" / "CM announces India's first
government AI University"). Exact matching on URL or title misses almost all
of these. Matching too loosely merges different announcements by the same
state in the same week.

Method
1. Only compare items attributed to the same state and published within
   DEDUP_WINDOW_DAYS of each other. This removes most false merges up front
   and keeps the comparison count small.
2. Turn each headline into a bag of content words: lower-cased, light
   stemming, stop words removed, and the state name and generic words
   ("govt", "AI", "launches") removed because every headline in the bucket
   has them and they say nothing about which event it is.
3. Weight words by rarity across the whole corpus (IDF). A shared rare token
   such as "tcs", "70000" or "sandbox" is strong evidence of the same event;
   a shared common token such as "school" is weak evidence.
4. Similarity = cosine of the weighted bags. Pairs above DEDUP_THRESHOLD are
   linked.
5. Clusters are built with complete linkage in spirit: an item joins a
   cluster only if it is similar to the cluster's seed (its earliest item),
   not to any member. Plain single linkage chains A~B~C into one cluster even
   when A and C are unrelated.
6. Identical publisher URLs are always merged (the same article found by two
   sources).

The threshold was tuned on hand-labelled pairs in data/review/dedup_pairs.csv;
scripts/eval_dedupe.py prints precision and recall.
"""
from __future__ import annotations

import math
import re
from collections import Counter, defaultdict
from datetime import date

from . import config
from .states import REGIONS

STOP = set("""
a an the and or of to in on for with by at from as is are was were be been will its it this that their his her
govt government state states cm chief minister ministers cabinet says said say new first india indian indias
ai artificial intelligence based powered driven enabled led using use uses used via amid over after into across
launch launches launched unveil unveils unveiled announce announces announced sign signs signed set sets up plan plans
planned get gets soon now all more also under through among how why what key big major top
""".split())
for _r in REGIONS:
    for _n in (_r.name,) + _r.names + _r.abbrevs + _r.gov_abbrevs:
        STOP.update(re.findall(r"[a-z]+", _n.lower()))

_NUM = re.compile(r"\d[\d,]*(?:\.\d+)?")
_WORD = re.compile(r"[a-z][a-z\-]{2,}")


def _stem(w: str) -> str:
    for suf in ("ies", "ing", "ed", "es", "s"):
        if w.endswith(suf) and len(w) - len(suf) >= 4:
            return w[: -len(suf)] + ("y" if suf == "ies" else "")
    return w


def tokens(title: str) -> list[str]:
    low = title.lower().replace("’", "'").replace("centre", "center")
    nums = [n.replace(",", "") for n in _NUM.findall(low)]            # 70,000 -> 70000
    words = [_stem(w.replace("-", "")) for w in _WORD.findall(low) if w not in STOP]
    return [w for w in words if w not in STOP] + [n for n in nums if len(n) >= 2]


def build_idf(token_lists) -> dict:
    n = len(token_lists)
    df = Counter(t for toks in token_lists for t in set(toks))
    return {t: math.log((n + 1) / (c + 1)) + 1 for t, c in df.items()}


def similarity(a: list[str], b: list[str], idf: dict) -> float:
    sa, sb = set(a), set(b)
    if not sa or not sb:
        return 0.0
    dot = sum(idf.get(t, 1.0) ** 2 for t in sa & sb)
    na = math.sqrt(sum(idf.get(t, 1.0) ** 2 for t in sa))
    nb = math.sqrt(sum(idf.get(t, 1.0) ** 2 for t in sb))
    return dot / (na * nb)


def cluster(items: list[dict], threshold: float = None, window: int = None) -> list[list[int]]:
    """items need: state, date (ISO), title, and optionally url. Returns lists of indexes."""
    threshold = config.DEDUP_THRESHOLD if threshold is None else threshold
    window = config.DEDUP_WINDOW_DAYS if window is None else window
    toks = [tokens(it["title"]) for it in items]
    idf = build_idf(toks)
    days = [date.fromisoformat(it["date"]).toordinal() for it in items]

    by_state = defaultdict(list)
    for i, it in enumerate(items):
        by_state[it["state"]].append(i)

    clusters = []
    for idxs in by_state.values():
        idxs.sort(key=lambda i: (days[i], items[i]["title"]))
        seeds = []   # (seed index, member list), in date order
        url_home = {}
        for i in idxs:
            url = items[i].get("url")
            if url and url in url_home:
                url_home[url].append(i)
                continue
            best, best_sim = None, threshold
            for seed, members in reversed(seeds):
                if days[i] - days[seed] > window:
                    break
                s = similarity(toks[i], toks[seed], idf)
                if s >= best_sim:
                    best, best_sim = members, s
            if best is None:
                best = [i]
                seeds.append((i, best))
            else:
                best.append(i)
            if url:
                url_home[url] = best
        clusters.extend(m for _, m in seeds)
    return clusters
