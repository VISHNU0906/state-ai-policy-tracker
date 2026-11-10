"""Tests for the parts the brief calls out: states, dates, relevance, dedup.

Run:  python -m pytest -q
"""
import pytest

from pipeline import dedupe, relevance, taxonomy
from pipeline.dates import date_from_url, parse_date
from pipeline.states import find_regions, normalize_state


# --- states --------------------------------------------------------------------

@pytest.mark.parametrize("raw", ["UP", "Uttar Pradesh", "Uttar-Pradesh", "uttar pradesh", "UTTAR PRADESH", "U.P.", "UttarPradesh"])
def test_uttar_pradesh_is_one_state(raw):
    assert normalize_state(raw) == "Uttar Pradesh"


@pytest.mark.parametrize("raw,want", [
    ("Orissa", "Odisha"), ("TN", "Tamil Nadu"), ("Tamilnadu", "Tamil Nadu"), ("M.P.", "Madhya Pradesh"),
    ("Uttaranchal", "Uttarakhand"), ("Pondicherry", "Puducherry"), ("J&K", "Jammu and Kashmir"),
    ("Bengaluru", "Karnataka"), ("", None), ("Atlantis", None),
])
def test_aliases(raw, want):
    assert normalize_state(raw) == want


def test_ambiguous_abbreviations_need_context():
    assert find_regions("Congress MP slams AI policy") == {}                 # a legislator, not Madhya Pradesh
    assert "Madhya Pradesh" in find_regions("MP govt to set up AI centre")
    assert "Madhya Pradesh" in find_regions("MP to set up three AI universities")
    assert find_regions("Markets up after AI rally") == {}                   # the word "up"
    assert "Uttar Pradesh" in find_regions("UP clears AI policy")
    assert "Andhra Pradesh" not in find_regions("AP photo shows AI robot")   # the news agency


def test_state_comes_from_text_and_handles_lookalikes():
    assert "Punjab" not in find_regions("Punjab CM Maryam Nawaz launches AI plan in Lahore")
    assert "West Bengal" not in find_regions("Cyclone over Bay of Bengal tracked with AI")
    hits = find_regions("Hyderabad to get AI city, says Telangana IT minister")
    assert list(hits) == ["Telangana"]


# --- dates ---------------------------------------------------------------------

def test_utc_timestamp_is_converted_to_india_time():
    assert parse_date("2026-07-07T20:30:00+00:00") == ("2026-07-08", "day")   # 02:00 next day in India
    assert parse_date("2026-07-07T10:00:00Z") == ("2026-07-07", "day")


@pytest.mark.parametrize("raw,want", [
    ("21 Sept 2026", ("2026-09-21", "day")), ("September 21, 2026", ("2026-09-21", "day")),
    ("21/09/2026", ("2026-09-21", "day")), ("2026-09-21", ("2026-09-21", "day")),
    ("Sep 2026", ("2026-09-01", "month")), ("2026-09", ("2026-09-01", "month")),
    ("2026", ("2026-01-01", "year")),
    ("last week", ("", "unknown")), ("", ("", "unknown")), (None, ("", "unknown")), ("31/02/2026", ("", "unknown")),
])
def test_loose_dates(raw, want):
    assert parse_date(raw) == want


def test_date_from_url():
    assert date_from_url("https://x.com/2026/09/21/story") == ("2026-09-21", "day")
    assert date_from_url("https://x.com/story-123") == ("", "unknown")


# --- relevance -----------------------------------------------------------------

@pytest.mark.parametrize("title,reason", [
    ("Assam signs multiple MoUs to scale AI in school education", "kept"),
    ("UP Approves Data Centre Policy 2026 to Expand AI Infrastructure", "kept"),
    ("Hyderabad police to use AI to manage traffic during Ganesh immersion", "kept"),
    ("Air India flight AI 171: Gujarat govt announces aid", "no_ai_term"),
    ("Govt launches national AI mission", "no_state_named"),
    ("Why Kerala needs an AI policy?", "opinion_or_explainer"),
    ("Congress slams Karnataka govt over AI policy in poll rally", "party_politics"),
    ("Man arrested in Pune for AI-generated video of minister", "ai_misuse_or_crime_no_policy_step"),
    ("Centre approves AI centre of excellence in Odisha", "central_government_actor"),
    ("Kerala startup raises funds for AI chips", "no_government_actor"),
    ("Delhi govt launches AI policy", "union_territory"),
    ("Karnataka, Tamil Nadu, Telangana race for AI investments", "multi_state_roundup"),
])
def test_relevance_reason_codes(title, reason):
    assert relevance.assess(title)["reason"] == reason


def test_social_sources_are_dropped():
    assert relevance.assess("Tamil Nadu govt to set up AI City", source_name="Instagram")["reason"] == "social_or_aggregator_source"


def test_state_attribution_uses_first_mention_on_ties():
    a = relevance.assess("Telangana govt signs AI pact, Andhra Pradesh to follow")
    assert a["state"] == "Telangana" and a["other_states"] == ["Andhra Pradesh"]


def test_categories():
    assert taxonomy.categorise("Karnataka cabinet approves AI policy") == "Policy and strategy"
    assert taxonomy.categorise("Kerala bans AI tools in exams, issues guidelines") == "Regulation and ethics"
    assert taxonomy.categorise("Odisha signs MoU with OpenAI") == "Partnerships and MoUs"
    assert taxonomy.categorise("Bihar police use AI to trace missing children") == "Government deployment"
    assert taxonomy.sector("Bihar police use AI to trace missing children") == "Policing and public safety"


# --- dedup ---------------------------------------------------------------------

def _items(rows):
    return [{"state": s, "date": d, "title": t} for s, d, t in rows]


def test_same_event_different_headlines_merge():
    items = _items([
        ("Telangana", "2026-09-20", "Telangana CM Revanth and TCS announce Rs 70,000 crore AI Data Centre in Future City"),
        ("Telangana", "2026-09-21", "TCS to build Rs 70,000 crore AI data centre in Telangana's Future City"),
        ("Telangana", "2026-09-21", "Revanth Reddy, TCS unveil 70,000 cr AI data center plan"),
    ])
    assert len(dedupe.cluster(items)) == 1


def test_different_events_same_state_same_week_stay_apart():
    items = _items([
        ("Karnataka", "2026-07-14", "Karnataka to set up AI university, says CM"),
        ("Karnataka", "2026-07-15", "Karnataka police deploy AI cameras to catch traffic violators"),
    ])
    assert len(dedupe.cluster(items)) == 2


def test_same_headline_other_state_or_far_apart_stays_apart():
    items = _items([
        ("Kerala", "2026-03-01", "Government signs MoU with Google for AI skilling"),
        ("Assam", "2026-03-01", "Government signs MoU with Google for AI skilling"),
        ("Kerala", "2026-06-01", "Government signs MoU with Google for AI skilling"),
    ])
    assert len(dedupe.cluster(items)) == 3


def test_identical_url_always_merges():
    items = [
        {"state": "Odisha", "date": "2026-05-01", "title": "Odisha AI policy cleared", "url": "https://a.in/x"},
        {"state": "Odisha", "date": "2026-05-02", "title": "Cabinet nod for new tech framework", "url": "https://a.in/x"},
    ]
    assert len(dedupe.cluster(items)) == 1
