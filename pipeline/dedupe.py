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
2. Turn each headline into a bag of content words: lower-cased, hyphenated
   words split, light stemming, common synonyms mapped to one word ("pact",
   "MoU", "agreement"), and stop words removed. The state name and generic
   words ("govt", "AI", "launches") are stop words here because every
   headline in the bucket has them and they say nothing about which event
   it is.
3. Weight words by rarity across the whole corpus (IDF). A shared rare token
   such as "tcs", "70000" or "sandbox" is strong evidence of the same event;
   a shared common token such as "school" is weak evidence.
4. Similarity = the mean of weighted cosine and weighted overlap. Cosine alone
   penalises a short headline matched against a long one. Pairs at or above
   DEDUP_THRESHOLD are linked.
5. Linked pairs are joined into clusters transitively. A big announcement is
   reported in dozens of wordings; no single headline resembles all the
   others, but each resembles some. An earlier version compared every
   headline only with the first one in its cluster and split such stories
   into many records. The cost of transitive linking is that a running story
   (deal signed, questioned, then cancelled within five days) can chain into
   one record. Two guards limit this: a headline that reports a reversal
   (cancelled, scrapped, stayed) is never linked to one that does not, and
   the similarity required rises by DEDUP_GAP_PENALTY for each day beyond
   one that separates two headlines. The measured error rate is in the README.
6. Identical publisher URLs are always merged (the same article found by two
   sources).

The threshold was chosen on hand-labelled pairs in data/review/dedup_pairs.csv.
scripts/eval_dedupe.py prints precision and recall, measured on whether each
labelled pair ends up in the same cluster.
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
ai artificial intelligence based powered driven enabled led ready using use uses used via amid over after into across
launch launches launched unveil unveils unveiled announce announces announced sign signs signed set sets up plan plans
planned get gets soon now all more also under through among how why what key big major top push rolls roll out
""".split())
for _r in REGIONS:
    for _n in (_r.name,) + _r.names + _r.abbrevs + _r.gov_abbrevs:
        STOP.update(re.findall(r"[a-z]+", _n.lower()))

# Different words that headline writers use for the same thing.
SYNONYMS = {
    "varsity": "university", "cr": "crore", "coe": "excellence", "pact": "mou", "agreement": "mou",
    "memorandum": "mou", "deal": "mou", "partner": "mou", "partnership": "mou", "ink": "mou", "tie": "mou",
    "approve": "clear", "nod": "clear", "okay": "clear", "scrap": "cancel", "hub": "center", "computer": "pc",
    "student": "school", "cop": "police", "train": "training", "skilling": "training", "skill": "training",
    "course": "training", "education": "training", "learn": "training", "class": "training", "bag": "win",
    "contract": "win", "bid": "win", "establish": "setup", "build": "setup",
}

# A reversal of an earlier step is a new event, however similar the wording.
REVERSAL = re.compile(
    r"(cancel\w*|scraps?|scrapped|revok\w+|withdraw\w*|rolls? back|rolled back|pulls? (?:the )?plug|suspend\w*|stays?|stayed"
    r"|drops?|dropped|shelv\w+|halts?|halted|quash\w*|terminat\w+)", re.I)

_NUM = re.compile(r"\d[\d,]*(?:\.\d+)?")
_WORD = re.compile(r"[a-z]{3,}")


def _stem(w: str) -> str:
    if not w.endswith("ss"):
        for suf in ("ies", "ing", "ed", "es", "s"):
            if w.endswith(suf) and len(w) - len(suf) >= 3:
                w = w[: -len(suf)] + ("y" if suf == "ies" else "")
                break
    return SYNONYMS.get(w, w)


def tokens(title: str) -> list[str]:
    low = title.lower().replace("’", "'").replace("centre", "center")
    nums = [n.replace(",", "").split(".")[0] for n in _NUM.findall(low)]   # 70,000 -> 70000, 122.6 -> 122
    words = [_stem(w) for w in _WORD.findall(low) if w not in STOP]        # hyphenated words split into parts
    return [w for w in words if w not in STOP] + [n for n in nums if len(n) >= 2]


def build_idf(token_lists) -> dict:
    n = len(token_lists)
    df = Counter(t for toks in token_lists for t in set(toks))
    return {t: math.log((n + 1) / (c + 1)) + 1 for t, c in df.items()}


def similarity(a: list[str], b: list[str], idf: dict) -> float:
    """Mean of rarity-weighted cosine and rarity-weighted overlap, in [0, 1]."""
    sa, sb = set(a), set(b)
    if not sa or not sb:
        return 0.0

    def weight(ts):
        return sum(idf.get(t, 1.0) ** 2 for t in ts)

    shared, wa, wb = weight(sa & sb), weight(sa), weight(sb)
    return 0.5 * shared / math.sqrt(wa * wb) + 0.5 * shared / min(wa, wb)


def cluster(items: list[dict], threshold: float = None, window: int = None, gap_penalty: float = None) -> list[list[int]]:
    """items need: state, date (ISO), title, and optionally url. Returns lists of indexes."""
    threshold = config.DEDUP_THRESHOLD if threshold is None else threshold
    window = config.DEDUP_WINDOW_DAYS if window is None else window
    gap_penalty = config.DEDUP_GAP_PENALTY if gap_penalty is None else gap_penalty
    reversal = [bool(REVERSAL.search(it["title"])) for it in items]
    toks = [tokens(it["title"]) for it in items]
    idf = build_idf(toks)
    days = [date.fromisoformat(it["date"]).toordinal() for it in items]

    parent = list(range(len(items)))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    by_state, by_url = defaultdict(list), {}
    for i, it in enumerate(items):
        by_state[it["state"]].append(i)
        if it.get("url"):
            parent[find(i)] = find(by_url.setdefault(it["url"], i))   # the same article found twice

    for idxs in by_state.values():
        idxs.sort(key=lambda i: (days[i], items[i]["title"]))
        for pos, i in enumerate(idxs):
            for j in idxs[pos + 1:]:
                gap = days[j] - days[i]
                if gap > window:
                    break
                if find(i) == find(j) or reversal[i] != reversal[j]:
                    continue
                # Reports of one announcement bunch within a day or two. The further apart two
                # headlines are, the more alike they must be to count as the same event.
                needed = threshold + gap_penalty * max(0, gap - 1)
                if similarity(toks[i], toks[j], idf) >= needed:
                    parent[find(j)] = find(i)

    groups = defaultdict(list)
    for i in range(len(items)):
        groups[find(i)].append(i)
    return sorted(groups.values(), key=lambda g: (min(days[i] for i in g), items[g[0]]["title"]))
