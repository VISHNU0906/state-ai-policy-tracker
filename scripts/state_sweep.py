"""Count sweep used to decide which states to cover.

For every state, run one identical query over the same six month window and
count the headlines that name the state and mention AI. The output is a rough
measure of how much state-level AI news exists per state. It is a
prioritisation aid, not a dataset.

Run:  python -m scripts.state_sweep
"""
import csv
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pipeline.sources import google_news  # noqa: E402
from pipeline.states import STATES, find_regions  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
WINDOWS = [("2026-05-01", "2026-07-01"), ("2026-07-01", "2026-09-01"), ("2026-09-01", "2026-11-01")]
AI = re.compile(r"\bAI\b|artificial intelligence|\bGenAI\b|machine learning", re.I)


def main():
    rows = []
    for st in STATES:
        seen, capped = set(), 0
        for a, b in WINDOWS:
            q = f'"{st.name}" (AI OR "artificial intelligence") (government OR govt OR policy OR cabinet OR minister) after:{a} before:{b}'
            items = google_news.search(q, ROOT / "data" / "raw" / "sweep")
            capped += len(items) >= 95
            for it in items:
                if AI.search(it["title"]) and st.name in find_regions(it["title"]):
                    seen.add(it["title"].lower())
        rows.append({"state": st.name, "ai_headlines_naming_state": len(seen), "windows_at_cap": capped})
        print(f'{st.name:20s} {len(seen):4d}  capped={capped}')
    rows.sort(key=lambda r: -r["ai_headlines_naming_state"])
    out = ROOT / "data" / "state_sweep.csv"
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print("wrote", out)


if __name__ == "__main__":
    main()
