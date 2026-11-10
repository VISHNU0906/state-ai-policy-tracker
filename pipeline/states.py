"""Canonical list of Indian states and union territories, plus the alias table
used to map free text ("UP", "Uttar-Pradesh", "Lucknow") to one canonical name.

Design notes
- Matching is done on the article text, never on the search query that found it.
  A query for "Telangana AI" routinely returns stories about Andhra Pradesh.
- Short abbreviations are risky. "UP" is also the word "up", "MP" is also
  "Member of Parliament", "AP" is also a news agency. They are matched
  case-sensitively and, for the ambiguous ones, only next to a government word.
- City aliases are weaker evidence than a state name. They carry a lower weight
  and are only used when no state name is present.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Region:
    name: str                     # canonical name used in the dataset
    code: str                     # ISO 3166-2:IN code without the "IN-" prefix
    kind: str                     # "state" or "ut"
    names: tuple = ()             # alternative spellings and old names (case-insensitive)
    abbrevs: tuple = ()           # safe abbreviations (case-sensitive, whole word)
    gov_abbrevs: tuple = ()       # ambiguous abbreviations, need a government word next to them
    cities: tuple = ()            # capital and major cities (weak evidence)
    search: tuple = field(default=())  # extra terms OR-ed into the search query


REGIONS = [
    Region("Andhra Pradesh", "AP", "state", ("Andhra",), (), ("AP",),
           ("Amaravati", "Visakhapatnam", "Vizag", "Vijayawada", "Tirupati")),
    Region("Arunachal Pradesh", "AR", "state", ("Arunachal",), (), (), ("Itanagar",)),
    Region("Assam", "AS", "state", (), (), (), ("Guwahati", "Dispur")),
    Region("Bihar", "BR", "state", (), (), (), ("Patna",)),
    Region("Chhattisgarh", "CG", "state", ("Chattisgarh", "Chhatisgarh"), (), (), ("Raipur", "Nava Raipur")),
    Region("Goa", "GA", "state", (), (), (), ("Panaji", "Panjim")),
    Region("Gujarat", "GJ", "state", (), (), (), ("Gandhinagar", "Ahmedabad", "GIFT City", "Surat")),
    Region("Haryana", "HR", "state", (), (), (), ("Gurugram", "Gurgaon", "Panchkula")),
    Region("Himachal Pradesh", "HP", "state", ("Himachal",), (), ("HP",), ("Shimla",)),
    Region("Jharkhand", "JH", "state", (), (), (), ("Ranchi",)),
    Region("Karnataka", "KA", "state", (), (), (), ("Bengaluru", "Bangalore", "Mysuru", "Mangaluru")),
    Region("Kerala", "KL", "state", (), (), (), ("Thiruvananthapuram", "Kochi", "Kozhikode")),
    Region("Madhya Pradesh", "MP", "state", (), (), ("MP",), ("Bhopal", "Indore")),
    Region("Maharashtra", "MH", "state", ("Maha",), (), (), ("Mumbai", "Pune", "Nagpur", "Navi Mumbai")),
    Region("Manipur", "MN", "state", (), (), (), ("Imphal",)),
    Region("Meghalaya", "ML", "state", (), (), (), ("Shillong",)),
    Region("Mizoram", "MZ", "state", (), (), (), ("Aizawl",)),
    Region("Nagaland", "NL", "state", (), (), (), ("Kohima",)),
    Region("Odisha", "OD", "state", ("Orissa",), (), (), ("Bhubaneswar", "Cuttack")),
    Region("Punjab", "PB", "state", (), (), (), ("Mohali", "Ludhiana", "Amritsar")),
    Region("Rajasthan", "RJ", "state", (), (), (), ("Jaipur", "Jodhpur", "Udaipur")),
    Region("Sikkim", "SK", "state", (), (), (), ("Gangtok",)),
    Region("Tamil Nadu", "TN", "state", ("Tamilnadu",), ("TN",), (), ("Chennai", "Coimbatore", "Madurai")),
    Region("Telangana", "TS", "state", ("Telengana",), (), ("TG",), ("Hyderabad", "Warangal")),
    Region("Tripura", "TR", "state", (), (), (), ("Agartala",)),
    Region("Uttar Pradesh", "UP", "state", (), ("UP", "U.P."), (), ("Lucknow", "Noida", "Kanpur", "Varanasi", "Prayagraj", "Greater Noida")),
    Region("Uttarakhand", "UK", "state", ("Uttaranchal",), (), (), ("Dehradun",)),
    Region("West Bengal", "WB", "state", ("Bengal",), (), ("WB",), ("Kolkata",)),
    # Union territories. Recognised so they are labelled correctly, but they
    # are outside the brief ("28 states") and are not prioritised for collection.
    Region("Delhi", "DL", "ut", ("NCT of Delhi",), (), (), ()),
    Region("Jammu and Kashmir", "JK", "ut", ("Jammu & Kashmir", "Jammu Kashmir", "J&K", "J-K"), (), (), ("Srinagar",)),
    Region("Ladakh", "LA", "ut", (), (), (), ("Leh",)),
    Region("Puducherry", "PY", "ut", ("Pondicherry",), (), (), ()),
    Region("Chandigarh", "CH", "ut", (), (), (), ()),
    Region("Andaman and Nicobar Islands", "AN", "ut", ("Andaman & Nicobar", "Andaman"), (), (), ("Port Blair",)),
    Region("Lakshadweep", "LD", "ut", (), (), (), ()),
    Region("Dadra and Nagar Haveli and Daman and Diu", "DH", "ut", ("Daman and Diu", "Dadra and Nagar Haveli"), (), (), ()),
]

BY_NAME = {r.name: r for r in REGIONS}
STATES = [r for r in REGIONS if r.kind == "state"]

# Words that make an ambiguous abbreviation ("MP", "AP", "HP", "WB", "TG") safe to read as a state.
_GOV = r"(?:govt|government|cm|chief minister|cabinet|police|assembly|budget|minister|state|it minister)"

_LEAD = r"(?:to|plans?|launch(?:es)?|signs?|unveils?|approves?|clears?|sets?|gets?|rolls?|introduces?|adopts?|drafts?|forms?|notifies|bets|eyes|mulls|turns|deploys?)"

# Weights: a full state name is strong evidence, a city is weak.
W_NAME, W_ABBREV, W_CITY = 3, 3, 1


def _flex(term: str) -> str:
    """Turn "Uttar Pradesh" into a pattern that also matches "Uttar-Pradesh" and "UttarPradesh"."""
    parts = re.split(r"[\s\-]+", term.strip())
    return r"[\s\-]*".join(re.escape(p) for p in parts)


def _compile():
    table = []
    for r in REGIONS:
        pats = []
        for n in (r.name,) + r.names:
            pats.append((re.compile(rf"(?<![A-Za-z]){_flex(n)}(?![a-z])", re.I), W_NAME, "name"))
        for a in r.abbrevs:
            pats.append((re.compile(rf"(?<![A-Za-z.]){re.escape(a)}(?![A-Za-z])"), W_ABBREV, "abbrev"))
        for a in r.gov_abbrevs:
            pats.append((re.compile(rf"(?<![A-Za-z]){re.escape(a)}(?:'s)?\s+{_GOV}\b"), W_ABBREV, "abbrev"))
            # At the very start of a headline, "MP to set up ..." means the state, not a legislator.
            pats.append((re.compile(rf"^{re.escape(a)}\s+{_LEAD}\b"), W_ABBREV, "abbrev"))
        for c in r.cities:
            pats.append((re.compile(rf"(?<![A-Za-z]){_flex(c)}(?![a-z])", re.I), W_CITY, "city"))
        table.append((r, pats))
    return table


_TABLE = _compile()

# "Punjab" and "Hyderabad" also exist in Pakistan; "Bengal" appears in "Bay of Bengal".
_FALSE_CONTEXT = {
    "Punjab": re.compile(r"\b(Pakistan|Lahore|Maryam Nawaz)\b", re.I),
    "West Bengal": re.compile(r"\bBay of Bengal\b", re.I),
}


def find_regions(text: str) -> dict:
    """Return {canonical name: {"score", "evidence", "first"}} for every region mentioned.

    `first` is the character position of the first mention, used to break ties.
    """
    hits = {}
    for region, pats in _TABLE:
        best, first = {}, len(text)      # per kind of evidence, the largest match count
        for pat, w, kind in pats:
            found = list(pat.finditer(text))
            if found:
                # "Andhra Pradesh" also matches the alias "Andhra"; count the mention once, not twice.
                best[kind] = max(best.get(kind, 0), w * min(len(found), 3))
                first = min(first, found[0].start())
        score, kinds = sum(best.values()), list(best)
        if score and region.name in _FALSE_CONTEXT and _FALSE_CONTEXT[region.name].search(text):
            continue
        if score:
            hits[region.name] = {"score": score, "evidence": sorted(set(kinds)), "first": first}
    # "Andhra Pradesh" must not also count as a bare "Pradesh" hit elsewhere, and
    # "Bengal" inside "West Bengal" is the same region, so no extra handling needed.
    return hits


def normalize_state(raw: str):
    """Map one free-text state label to a canonical name, or None.

    >>> normalize_state("UP"), normalize_state("Uttar-Pradesh"), normalize_state("uttar pradesh")
    ('Uttar Pradesh', 'Uttar Pradesh', 'Uttar Pradesh')
    """
    if not raw or not raw.strip():
        return None
    s = raw.strip()
    key = re.sub(r"[^a-z&]", "", s.lower())
    for r in REGIONS:
        variants = (r.name,) + r.names + r.abbrevs + r.gov_abbrevs + (r.code,)
        if key in {re.sub(r"[^a-z&]", "", v.lower()) for v in variants}:
            return r.name
    hits = find_regions(s)
    if len(hits) == 1:
        return next(iter(hits))
    return None
