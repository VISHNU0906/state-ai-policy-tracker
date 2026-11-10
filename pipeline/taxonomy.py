"""Category, sector and government level for a kept record.

Category answers "what kind of step did the state take". One category per
record. When several match, the first in CATEGORY_RULES wins; the order runs
from the most binding kind of step (a rule) to the least (a deployment).

Sector answers "which area of government is it about".
"""
from __future__ import annotations

import re

CATEGORY_RULES = [
    ("Regulation and ethics", re.compile(
        r"\b(regulat\w+|guidelines|rules|bill|ordinance|ban(?:s|ned)?|advisory|ethic\w*|responsible AI|safety norms"
        r"|deepfakes?|misuse|privacy|safeguards?|crackdown|legal framework|AI law)\b", re.I)),
    ("Policy and strategy", re.compile(
        r"\b(AI policy|policy|policies|mission|roadmap|strategy|vision document|action plan|blueprint|draft)\b", re.I)),
    ("Funding and budget", re.compile(
        r"\b(budget|allocat\w+|earmark\w*|sanction\w*|outlay|fund(?:s|ing)?|grant|subsid\w+|incentives?)\b", re.I)),
    ("Institutions and bodies", re.compile(
        r"\b(task ?force|committee|council|panel|cell|cent(?:re|er)s? of excellence|CoE|university|universities|institute"
        r"|academy|lab|labs|sandbox|innovation hub|AI hub|authority|board|department of AI)\b", re.I)),
    ("Infrastructure and investment", re.compile(
        r"\b(data cent(?:re|er)s?|AI city|compute|GPU|supercomput\w+|cloud region|campus|invest\w+|crore|billion|gigawatt|GW|MW)\b", re.I)),
    ("Partnerships and MoUs", re.compile(
        r"\b(MoUs?|memorandum|agreement|pact|tie[- ]?up|ties up|partner\w*|collaborat\w+|join(?:s|ed)? hands|ropes? in|ink(?:s|ed)?)\b", re.I)),
    ("Skilling and education", re.compile(
        r"\b(skill\w*|train(?:ing|s|ed)?|curriculum|syllabus|course|students|teachers|school|schools|colleges?|literacy|upskill\w*|classroom)\b", re.I)),
    ("Government deployment", re.compile(r".", re.I)),  # default: AI put to use in a public function
]
CATEGORIES = [c for c, _ in CATEGORY_RULES]

SECTOR_RULES = [
    ("Policing and public safety", re.compile(
        r"\b(police|cops|crime|surveillance|CCTV|cameras?|traffic|challan|facial recognition|cyber ?crime|prison|jail|security|law and order|crowd)\b", re.I)),
    ("Health", re.compile(r"\b(health|hospital|medical|doctor|patients?|disease|cancer|TB|tuberculosis|diagnos\w+|screening|MBBS|clinic)\b", re.I)),
    ("Agriculture", re.compile(r"\b(agricultur\w+|farm\w*|crop\w*|kisan|irrigation|soil|horticultur\w+|fisher\w+|livestock|pest)\b", re.I)),
    ("Education and skilling", re.compile(
        r"\b(school\w*|student\w*|teacher\w*|education|college\w*|universit\w+|curriculum|syllabus|skill\w*|training|exam\w*|classroom|literacy)\b", re.I)),
    ("Judiciary and legal", re.compile(r"\b(high court|HC|court\w*|judiciary|judges?|legal)\b", re.I)),
    ("Transport and urban", re.compile(r"\b(transport|bus(?:es)?|metro|road\w*|highway|urban|municipal|civic|city corporation|waste|water supply|smart city|parking)\b", re.I)),
    ("Revenue and finance", re.compile(r"\b(tax|GST|revenue|excise|land records?|registration|treasury|audit|procurement|graft|corruption)\b", re.I)),
    ("Industry and investment", re.compile(
        r"\b(data cent(?:re|er)s?|invest\w+|industr\w+|startup\w*|GCC|IT sector|semiconductor|AI city|jobs|MSME)\b", re.I)),
    ("Governance and public services", re.compile(
        r"\b(governance|e-?governance|citizen\w*|public services?|grievance\w*|welfare|scheme\w*|ration|pension|chatbot|helpline|administration|officials|employees)\b", re.I)),
]
DEFAULT_SECTOR = "Cross-sector"
SECTORS = [s for s, _ in SECTOR_RULES] + [DEFAULT_SECTOR]

LEVEL_RULES = [
    ("judiciary", re.compile(r"\b(high court|HC)\b", re.I)),
    ("local", re.compile(r"\b(municipal|corporation|civic body|collector|district administration|zilla|panchayat|BBMP|GHMC|BMC|GCC|commissionerate)\b", re.I)),
]


def categorise(title: str, description: str = "") -> str:
    # Headline first: it states the main step. Fall back to the description.
    for text in (title, f"{title}. {description}"):
        for name, pat in CATEGORY_RULES[:-1]:
            if pat.search(text):
                return name
    return CATEGORY_RULES[-1][0]


def sector(title: str, description: str = "") -> str:
    for text in (title, f"{title}. {description}"):
        for name, pat in SECTOR_RULES:
            if pat.search(text):
                return name
    return DEFAULT_SECTOR


def gov_level(title: str) -> str:
    for name, pat in LEVEL_RULES:
        if pat.search(title):
            return name
    return "state"
