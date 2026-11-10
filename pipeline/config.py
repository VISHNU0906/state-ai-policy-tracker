"""All tunable choices in one place."""
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
INTERIM = ROOT / "data" / "interim"
OUT = ROOT / "data" / "out"
REVIEW = ROOT / "data" / "review"
SITE = ROOT / "docs"

# Collection window. Start of 2025 is when state AI policies began to appear in
# volume; the end date is the day the pipeline was last run.
START = date(2025, 1, 1)
END = date(2026, 11, 10)

# Prioritised states. Chosen from data/state_sweep.csv (headline counts for all
# 28 states over an identical six month query) with one constraint: at least
# two states from each of four zones, so the dataset is not only the southern
# IT states. See RATIONALE.md.
PRIORITY_STATES = [
    "Karnataka", "Telangana", "Tamil Nadu", "Kerala",      # South
    "Maharashtra", "Gujarat",                              # West
    "Uttar Pradesh", "Bihar",                              # North / Hindi belt
    "Odisha", "Assam",                                     # East / North-East
]

# Extra search terms per state, OR-ed with the state name. Headlines often use
# a short form ("UP govt"), which a quoted full-name query would miss.
SEARCH_ALIASES = {
    "Uttar Pradesh": ['"UP govt"', '"UP government"', '"Yogi government"'],
    "Tamil Nadu": ['"TN govt"', '"TN government"'],
    "Andhra Pradesh": ['"AP govt"', '"AP government"'],
    "Maharashtra": ['"Maha govt"'],
    "Odisha": ['"Orissa"'],
}

# Four query shapes per state per month. Each targets one part of the brief's
# definition of AI policy activity. They overlap on purpose; duplicates are
# removed downstream.
QUERY_TEMPLATES = {
    "gov": '{S} (AI OR "artificial intelligence") (government OR govt OR cabinet OR minister OR "chief minister")',
    "instrument": '{S} AI (policy OR mission OR "task force" OR "centre of excellence" OR MoU OR budget OR crore)',
    "sector": '{S} AI (police OR health OR hospital OR agriculture OR farmers OR school OR education OR governance)',
    "infra_reg": '{S} ("data centre" OR "AI city" OR "AI university" OR deepfake OR "AI rules" OR "AI guidelines") (government OR govt OR policy)',
}

# Deduplication
DEDUP_WINDOW_DAYS = 5      # two reports further apart than this are never merged
DEDUP_THRESHOLD = 0.35     # similarity needed to link two headlines; chosen on labelled pairs, see scripts/eval_dedupe.py

