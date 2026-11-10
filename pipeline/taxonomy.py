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
        r"|academy|lab|labs|sandbox|innovation hub|AI hub|authority|board|department of AI|AI ministry|ministry for AI"
        r"|intelligence ministry|AI minister|intelligence minister|AI department|research organi[sz]ation)\b", re.I)),
    ("Infrastructure and investment", re.compile(
        r"\b(data cent(?:re|er)s?|AI city|compute|GPU|supercomput\w+|cloud region|campus|invest(?:s|ed|ing|ment|ments|or|ors)?|crore|billion|gigawatt|GW|MW)\b", re.I)),
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
        r"\b(data cent(?:re|er)s?|invest(?:s|ed|ing|ment|ments|or|ors)?|industr\w+|startup\w*|GCC|IT sector|semiconductor|AI city|jobs|MSME)\b", re.I)),
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
    # The headline states the main step, so the category is read from the headline only.
    # Reading it from the article text was tried and dropped: one stray word in the body
    # ("rules", "policy") changed the category of a plain deployment story.
    for name, pat in CATEGORY_RULES[:-1]:
        if pat.search(title):
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


# Stage answers "how far along is it". Announcing a plan, signing an agreement,
# approving a policy and switching a system on are different things, and a
# count that mixes them overstates what exists on the ground.
STAGE_RULES = [   # listed in tie-break order
    ("reversed", re.compile(r"\b(cancel\w*|scraps?|scrapped|revok\w+|withdraw\w*|suspend\w*|shelv\w+|halt(?:s|ed)?|stalls?|stalled)\b", re.I)),
    ("signed", re.compile(r"\b(sign(?:s|ed)|ink(?:s|ed)|MoUs?|LoI|pact|agreement|partners? with|partners\b|ties? up|tie-up|joins? hands|teams? up|collaborat\w+)\b", re.I)),
    ("approved", re.compile(r"\b(approv\w+|clear(?:s|ed)|nod|sanction\w+|okays?|notif(?:y|ies|ied)|allocat\w+|earmark\w*|sets? aside|budget)\b", re.I)),
    ("launched", re.compile(
        r"\b(launch(?:es|ed)|inaugurat\w+|opens?|opened|unveil(?:s|ed)|rolls? out|rolled out|introduc(?:es|ed)|deploy(?:s|ed)|start(?:s|ed)"
        r"|begins?|activat\w+|adopts?|issu(?:es|ed)|releas(?:es|ed)|uses?|used|using|helps?|helped|now|forms?|formed|constitut\w+|sets up|mandat\w+|bans?)\b", re.I)),
    ("announced", re.compile(
        r"\b(to|will|plans?|planned|propos\w+|mulls?|consider\w+|soon|eyes|set to|announc\w+|targets?|aims?|draft\w*|moots)\b", re.I)),
]
STAGES = [name for name, _ in STAGE_RULES] + ["unspecified"]


def stage(title: str) -> str:
    """The stage whose cue word comes first in the headline; listing order breaks ties.

    "Assam signs MoUs to bring AI ..." is signed, not announced, because "signs"
    comes before "to". "Maharashtra to launch ..." is announced: "to" comes first
    and the bare verb "launch" is not a launched cue. A reversal cue anywhere wins.
    """
    if STAGE_RULES[0][1].search(title):
        return "reversed"
    best = None
    for order, (name, pat) in enumerate(STAGE_RULES):
        m = pat.search(title)
        if m and (best is None or (m.start(), order) < best[:2]):
            best = (m.start(), order, name)
    return best[2] if best else "unspecified"
