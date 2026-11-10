"""Stage 2. Decide whether a news item is "AI policy activity by a state".

The line we draw
  IN   A state government, or a body that answers to it (departments, state
       police, state-run agencies and universities, district and city
       administrations) or the state's High Court, takes a concrete step that
       involves AI: adopts or drafts a policy, sets up a body or institution,
       signs an agreement, deploys AI in a public function, commits money,
       starts a training programme, or makes a rule.
  OUT  Opinion and explainers. Speeches with no concrete step. Central
       government actions that merely happen in a state. Company news with no
       state body as a party. Crime stories where AI is the tool (deepfake
       fraud) unless the state responds with a rule. Party politics.

Every item gets a decision and a reason code, and rejected items are written
to data/out/rejected.csv, so the line can be audited row by row.

The rules are plain regular expressions on purpose: anyone can read them,
they cost nothing to run, and they give the same answer every time. Their
errors are measured against a hand-labelled sample in data/review/.
"""
from __future__ import annotations

import re

from .states import BY_NAME, find_regions, subject_pattern

# --- signals -----------------------------------------------------------------

AI_TERMS = re.compile(
    r"(?<![A-Za-z])AI(?![A-Za-z])"          # the token AI, upper case only
    r"|\bA\.I\.|artificial intelligence|\bgen(?:erative)?[- ]?AI\b|machine learning"
    r"|deepfakes?|large language models?|\bLLMs?\b|facial recognition|face recognition|chatbots?"
    r"|\bAI[- ](?:powered|based|driven|enabled|led)\b",
    re.I,
)
# re.I above would also match "ai" inside ordinary words for the first branch,
# so that branch is re-checked case-sensitively below.
AI_TOKEN = re.compile(r"(?<![A-Za-z])AI(?![A-Za-z])")
AI_OTHER = re.compile(
    r"\bA\.I\.|artificial intelligence|\bgen(?:erative)?[- ]?ai\b|machine learning|deepfakes?"
    r"|large language models?|\bLLMs?\b|facial recognition|face recognition|chatbots?",
    re.I,
)
# "AI" that is not artificial intelligence.
AI_FALSE = re.compile(r"Air India|AI Express|\bAI[- ]?\d{3,4}\b|AI flight|AIADMK|avian influenza|artificial insemination", re.I)

GOV_ACTOR = re.compile(
    r"\b(govt|government|cabinet|chief minister|minister|ministry|department|dept|secretariat|assembly"
    r"|police|cops|governance|govt[- ]run|commissionerate|collector|district administration|municipal|corporation|civic body"
    r"|state[- ](?:run|owned|level)|high court|\bHC\b|budget|state to|state plans)\b|\bCM\b",
    re.I,
)
# The central government as the actor. "Centre" counts only as a sentence subject or object
# ("Centre approves ...", "with the Centre"), never as the last word of a name
# ("AI Engineering Centre to add jobs").
CENTRAL_ACTOR = re.compile(
    r"(?:^|[:;,|]\s+|\bthe\s+)Centre(?:['’]s)?\s+(?:to|will|approves|clears|sanctions|announces|launches|plans|sets|allocates|okays|nod)\b"
    r"|\b(?:asks|urges|with|from|by) (?:the )?Centre\b"
    r"|\b(?:Union (?:minister|government|govt|cabinet|budget|finance minister|IT minister)|central government|central govt|MeitY|IndiaAI"
    r"|NITI Aayog|PM Modi|Prime Minister|Vaishnaw|Sitharaman|Lok Sabha|Rajya Sabha|Supreme Court|Ministry of Electronics)\b"
)
STATE_GOV_STRONG = re.compile(r"\b(govt|government|cabinet|chief minister|state)\b|\bCM\b", re.I)

INSTRUMENT = re.compile(
    r"\b(policy|policies|mission|roadmap|strategy|task ?force|committee|council|panel|cell"
    r"|cent(?:re|er)s? of excellence|\bCoE\b|university|universities|institute|academy|lab|labs|hub|\bAI city\b"
    r"|data cent(?:re|er)s?|sandbox|MoUs?|memorandum|agreement|pact|tie[- ]up|partnership"
    r"|budget|crore|lakh|fund|grant|incentives?|subsid(?:y|ies)|tender"
    r"|guidelines|rules|regulations?|bill|act|ordinance|framework|ban|advisory"
    r"|scheme|programme|program|project|initiative|curriculum|syllabus|course|training|skilling"
    r"|pilot|portal|platform|app|system|tool|cameras?|surveillance|dashboard|helpline|command cent(?:re|er)"
    r"|attendance|study|survey|audit|agenc(?:y|ies)|AI minister|minister for AI|intelligence minister|norms|boundaries"
    r"|cent(?:re|er)s?|hubs?|park|township|kits?|devices?|dept|department)\b",
    re.I,
)
ACTION = re.compile(
    r"\b(launch(?:es|ed)?|unveil(?:s|ed)?|sign(?:s|ed)?|ink(?:s|ed)?|approv(?:es|ed|al)|clear(?:s|ed)|notif(?:y|ies|ied)"
    r"|announc(?:es|ed)|set(?:s|ting)? up|establish(?:es|ed)?|allocat(?:es|ed)|earmark(?:s|ed)?|sanction(?:s|ed)?"
    r"|roll(?:s|ed)? out|deploy(?:s|ed)?|introduc(?:es|ed)|adopt(?:s|ed)?|draft(?:s|ed)?|form(?:s|ed)?|constitut(?:es|ed)"
    r"|mandat(?:es|ed)|bans?|banned|partner(?:s|ed)?|ties up|join(?:s|ed)? hands|to (?:use|get|have|train|set|launch|deploy|introduce|roll|build|host|frame|open)"
    r"|plans?|propos(?:es|ed)|moots|mulls|release(?:s|d)?|inaugurat(?:es|ed)|start(?:s|ed)?|begin(?:s)?|use(?:s|d)? AI|turn(?:s|ed)? to AI|bring(?:s)?|ropes? in"
    r"|mov(?:es|ed)|develop(?:s|ed)?|build(?:s)?|built|expand(?:s|ed)?|scal(?:es|ed|e up)|push(?:es)?|bets?|eyes|open(?:s|ed)?"
    r"|host(?:s|ed)?|pilot(?:s|ed)?|test(?:s|ed)?|AI (?:helps?|to help|aids?)|with AI|using AI|through AI"
    r"|harness\w*|leverag\w*|integrat\w+|embrac\w+|initiat\w+|appoint\w+|rejigs?|mandatory|direct(?:s|ed)|order(?:s|ed)"
    r"|issu(?:es|ed)|distribut\w+|empower\w*|targets?|identif\w+|trac(?:es|ed|k)|crack(?:s|ed)?|AI (?:\w+ )?helps?|rolls?|sets?)\b",
    re.I,
)

def state_is_subject(title: str, state: str) -> bool:
    """True for "Assam signs ...", "Google, Telangana ink MoU", "Uttar Pradesh to launch ...".
    False for "Kerala startup ...". A state named as the one acting stands for its government.
    """
    for m in subject_pattern(state).finditer(title):
        nxt = m.group(1)
        if nxt.lower() in ("to", "will", "govt", "government") or ACTION.fullmatch(nxt):
            return True
    return False


# Statements and speeches. Kept only when the headline also reports a concrete step.
RHETORIC = re.compile(
    r"(says?|said|urges?|calls? for|stress(?:es|ed)|hails?|asserts?|claims?|warns?|bats for|pitch(?:es)? for|emphasi[sz]es?"
    r"|highlights?|lauds?|vows?|promis(?:es|ed))|^['\"‘“]", re.I)

OPINION = re.compile(
    r"^(opinion|editorial|explained|explainer|analysis|column|interview|podcast|watch|video|photos?|quiz|fact check)\b"
    r"|\b(explained|opinion|editorial|podcast|takeaways|what we know|here'?s (?:why|how|what)|decoded)\b"
    r"|^(why|how|what|can|will|should|is|are|does)\b.*\?$",
    re.I,
)
CRIME_MISUSE = re.compile(
    r"\b(arrest(?:ed|s)?|booked|held|nabbed|FIR|scam(?:s|mers?)?|fraud(?:sters?)?|duped|cheat(?:ed|ing)|extort\w*|morphed|obscene"
    r"|viral (?:AI )?video|AI[- ]generated (?:video|image|photo|clip|content)|fake (?:video|image))\b",
    re.I,
)
REGULATORY = re.compile(r"\b(policy|rules|guidelines|regulat\w+|bill|act|law|ban|advisory|framework|crackdown|task ?force|cell|unit)\b", re.I)
PARTISAN = re.compile(
    r"\b(BJP|Congress|DMK|AIADMK|TMC|BRS|YSRCP|TDP|JD\(U\)|RJD|AAP|Shiv Sena|NCP|CPI\(M\)|BJD|opposition)\b"
    r".*\b(slams?|attacks?|hits out|accus\w+|alleg\w+|mocks?|jibe|campaign|poll|election|manifesto|rally)\b",
    re.I,
)
FOREIGN = re.compile(r"\b(United Kingdom|born in|Pakistan|Lahore|China|Chinese|US |UK |Trump|Labour MP|Britain|Bangladesh|Nepal)\b")
# Reaction and analysis pieces about a state's AI step, not the step itself.
COMMENTARY = re.compile(
    r"here['\u2019]?s why|under fire|red flags?|spark(?:s|ed)? |concerns?\b|oppos(?:es|ed)\b|criticis\w+|wonders?\b|unsung|^exclusive"
    r"|current affairs|what is\b|explains? why|backlash|controvers\w+|activists?\b|\brow\b|urges? .{0,40}\b(?:ban|halt|pause|stop)\b"
    r"|people can['\u2019]?t believe", re.I)
# Meetings and events with no reported outcome.
MEETING = re.compile(
    r"\b(meets?|met with|discuss(?:es|ed)?|interacts?|hosts?|to host|conclave|conference|seminar|workshop|webinar|expo|visits?)\b", re.I)
OUTCOME = re.compile(
    r"\b(sign(?:s|ed)?|ink(?:s|ed)?|MoUs?|pact|launch(?:es|ed)?|approv\w+|clear(?:s|ed)|unveil(?:s|ed)?|announc\w+|set(?:s)? up|establish\w*"
    r"|roll(?:s|ed)? out|deploy\w*|introduc\w+|notif\w+|forms?|allocat\w+|partners?|ties up|inaugurat\w+|opens?|releases?)\b", re.I)

SOCIAL_SOURCES = {"instagram", "facebook", "youtube", "x.com", "twitter", "linkedin", "threads", "reddit", "msn"}


def has_ai(text: str) -> bool:
    if AI_FALSE.search(text):
        stripped = AI_FALSE.sub(" ", text)
    else:
        stripped = text
    return bool(AI_TOKEN.search(stripped) or AI_OTHER.search(stripped))


def assess(title: str, description: str = "", source_name: str = "") -> dict:
    """Return decision, reason code, attributed state and the signals that fired."""
    text = f"{title}. {description}".strip()
    sig = {
        "ai_title": has_ai(title),
        "ai_any": has_ai(text),
        "gov": bool(GOV_ACTOR.search(text)),
        "instrument": bool(INSTRUMENT.search(text)),
        "action": bool(ACTION.search(title)),
        "central": bool(CENTRAL_ACTOR.search(title)),
    }
    out = {"keep": False, "central": False, "reason": "", "state": None, "state_basis": "", "other_states": [], "confidence": "", "signals": sig}

    if source_name.strip().lower() in SOCIAL_SOURCES:
        out["reason"] = "social_or_aggregator_source"
        return out
    if not sig["ai_any"]:
        out["reason"] = "no_ai_term"
        return out

    # State attribution: headline first, description only if the headline names none.
    regions = find_regions(title)
    basis = "headline"
    if not regions and description:
        regions, basis = find_regions(description), "description"
    if not regions:
        out["reason"] = "no_state_named"
        return out
    ranked = sorted(regions.items(), key=lambda kv: (-kv[1]["score"], kv[1]["first"]))
    strong = [n for n, v in ranked if v["score"] >= 3]
    if len(strong) >= 3:
        out["reason"] = "multi_state_roundup"      # e.g. "Karnataka, Tamil Nadu, Telangana compete for..."
        out["other_states"] = strong
        return out
    out["state"] = ranked[0][0]
    out["state_basis"] = basis + ":" + "+".join(ranked[0][1]["evidence"])
    out["other_states"] = [n for n, _ in ranked[1:]]
    # "Assam signs MoUs ..." : the state named as the subject of the headline is the government acting.
    subject = basis == "headline" and state_is_subject(title, out["state"])
    if subject:
        sig["gov"] = True
        sig["state_is_subject"] = True
    if BY_NAME[out["state"]].kind != "state":
        out["reason"] = "union_territory"
        return out

    if OPINION.search(title.strip()):
        out["reason"] = "opinion_or_explainer"
        return out
    if FOREIGN.search(title) and not STATE_GOV_STRONG.search(title):
        out["reason"] = "foreign_story"
        return out
    if PARTISAN.search(title):
        out["reason"] = "party_politics"
        return out
    if CRIME_MISUSE.search(title) and not REGULATORY.search(title):
        out["reason"] = "ai_misuse_or_crime_no_policy_step"
        return out
    if sig["central"] and not subject and not STATE_GOV_STRONG.search(title):
        # The central government acting in or for a named state. Kept, and labelled as
        # central, so it can be filtered apart from the state's own steps.
        out["central"] = True
        sig["gov"] = True
    if not sig["gov"]:
        out["reason"] = "no_government_actor"
        return out
    if not (sig["instrument"] or sig["action"]):
        out["reason"] = "no_concrete_step"
        return out
    if COMMENTARY.search(title) and not subject:
        out["reason"] = "commentary_or_reaction"
        return out
    if MEETING.search(title) and not OUTCOME.search(title):
        out["reason"] = "meeting_or_event_only"
        return out
    if RHETORIC.search(title) and not (sig["action"] and INSTRUMENT.search(title)):
        out["reason"] = "statement_only"
        return out

    out["keep"] = True
    out["reason"] = "kept"
    strong_signals = sig["ai_title"] and sig["instrument"] and sig["action"] and basis == "headline" \
        and "city" not in ranked[0][1]["evidence"][:1]
    out["confidence"] = "high" if strong_signals else "medium"
    return out
