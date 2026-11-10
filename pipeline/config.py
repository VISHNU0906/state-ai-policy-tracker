"""All tunable choices in one place."""
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
INTERIM = ROOT / "data" / "interim"
OUT = ROOT / "data" / "out"
REVIEW = ROOT / "data" / "review"
SITE = ROOT / "docs"

# Collection window. It starts in 2022, before ChatGPT's release, so the build-up of
# state activity can be seen from the beginning. The end date is the last run.
START = date(2022, 1, 1)
END = date(2026, 11, 10)

# The hand review (data/review/overrides.csv) read every record dated on or after this
# day. Earlier records were added by a later backfill and are rule output only; they
# carry review_status "auto".
REVIEWED_FROM = date(2025, 1, 1)

# Prioritised states. Ten were chosen from data/state_sweep.csv (headline counts
# for all 28 states over an identical six month query) with one constraint: at
# least two states from each of four zones, so the dataset is not only the
# southern IT states. Three more (Andhra Pradesh, Madhya Pradesh, Rajasthan)
# were added so the output can be scored against an independently researched
# reference list that covers them (data/review/reference_events.csv). The sweep
# under-counts Andhra Pradesh and Madhya Pradesh because headlines call them
# "AP" and "MP", which a bare-name count misses. See RATIONALE.md.
PRIORITY_STATES = [
    "Karnataka", "Telangana", "Tamil Nadu", "Kerala", "Andhra Pradesh",   # South
    "Maharashtra", "Gujarat", "Rajasthan",                               # West
    "Uttar Pradesh", "Bihar", "Madhya Pradesh",                          # North and Centre
    "Odisha", "Assam",                                                   # East and North-East
]

# Extra search terms per state, OR-ed with the state name. Headlines often use
# a short form ("UP govt"), which a quoted full-name query would miss.
SEARCH_ALIASES = {
    "Uttar Pradesh": ['"UP govt"', '"UP government"', '"Yogi government"'],
    "Tamil Nadu": ['"TN govt"', '"TN government"'],
    "Andhra Pradesh": ['"AP govt"', '"AP government"', '"Andhra"'],
    "Madhya Pradesh": ['"MP govt"', '"MP government"'],
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
DEDUP_GAP_PENALTY = 0.08   # extra similarity required per day of separation beyond one day
DEDUP_WINDOW_DAYS = 5      # two reports further apart than this are never merged
DEDUP_THRESHOLD = 0.25     # similarity needed to link two headlines; best F1 on the tuning half of the labelled pairs

