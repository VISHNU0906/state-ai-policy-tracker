"""Stage 6. Write the dataset and everything the dashboard reads.

  data/out/records.csv        the dataset
  data/out/records.xlsx       same rows, plus a data dictionary and the rejected log
  data/out/rejected.csv       every item that was dropped, with the reason
  docs/data/records.json      the dashboard's only data file

The dashboard reads the JSON written here and nothing else, so the page and
the CSV cannot drift apart.
"""
from __future__ import annotations

import csv
import json
import shutil
from collections import Counter

from . import config
from .states import BY_NAME

COLUMNS = [
    ("record_id", "Stable ID: state code, date, short hash of the earliest headline."),
    ("state", "Canonical state name, taken from the article text, not from the search query."),
    ("date", "Date of the earliest report of the event, India time, ISO format."),
    ("date_precision", "day, month, year or unknown. A month-precision date is stored as the 1st of the month."),
    ("title", "Headline of the article chosen to represent the event."),
    ("summary", "One line on what happened."),
    ("category", "Kind of step taken. One value from the fixed list in pipeline/taxonomy.py."),
    ("sector", "Area of government concerned."),
    ("gov_level", "state, local (district or city body) or judiciary (High Court)."),
    ("source_name", "Publisher of the representative article."),
    ("source_url", "Link to the representative article."),
    ("n_outlets", "Number of distinct outlets that reported the event (after deduplication)."),
    ("other_outlets", "The other outlets, separated by semicolons."),
    ("confidence", "high when the headline itself names the state, AI, a concrete instrument and an action; else medium."),
    ("summary_basis", "Where the summary came from: publisher_description, article_text, headline, written_in_review or llm_from_article_text."),
    ("review_status", "auto (rules only), reviewed (hand-checked) or llm_checked."),
]
FIELDS = [c for c, _ in COLUMNS]
REJ_FIELDS = ["reason", "state", "date", "title", "source_name", "origin", "google_link", "url"]


def write_all(records: list[dict], rejected: list[dict], funnel: dict) -> None:
    config.OUT.mkdir(parents=True, exist_ok=True)
    (config.SITE / "data").mkdir(parents=True, exist_ok=True)

    with (config.OUT / "records.csv").open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
        w.writeheader()
        w.writerows(records)

    rejected = sorted(rejected, key=lambda r: (r["reason"], r.get("date") or "", r["title"]))
    with (config.OUT / "rejected.csv").open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=REJ_FIELDS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rejected)

    _write_xlsx(records, rejected)
    shutil.copyfile(config.OUT / "records.csv", config.SITE / "data" / "records.csv")   # the page's download link

    log_path = config.INTERIM / "collect_log.json"
    collect = json.loads(log_path.read_text(encoding="utf-8")) if log_path.exists() else {}
    site = {
        "meta": {
            "window_start": config.START.isoformat(),
            "window_end": config.END.isoformat(),
            "states": config.PRIORITY_STATES,
            "state_codes": {s: BY_NAME[s].code for s in config.PRIORITY_STATES},
            "funnel": funnel,
            "hits_per_source": collect.get("hits_per_source", {}),
            "reject_reasons": dict(Counter(r["reason"].split(":")[0] for r in rejected).most_common()),
            "record_origins": dict(Counter(o for r in records for o in r.get("_origins", []))),
        },
        "records": [{k: r[k] for k in FIELDS} for r in records],
    }
    (config.SITE / "data" / "records.json").write_text(json.dumps(site, ensure_ascii=False, indent=1), encoding="utf-8")


def _write_xlsx(records, rejected) -> None:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter

    wb = Workbook()
    head_font, head_fill = Font(bold=True, color="FFFFFF"), PatternFill("solid", fgColor="1F3A5F")

    def sheet(ws, fields, rows, widths):
        ws.append(fields)
        for r in rows:
            ws.append([r.get(k, "") for k in fields])
        for i, cell in enumerate(ws[1], 1):
            cell.font, cell.fill = head_font, head_fill
            ws.column_dimensions[get_column_letter(i)].width = widths.get(fields[i - 1], 16)
        ws.freeze_panes = "A2"
        ws.auto_filter.ref = ws.dimensions

    ws = wb.active
    ws.title = "records"
    sheet(ws, FIELDS, records, {"title": 70, "summary": 90, "source_url": 50, "other_outlets": 40, "record_id": 22,
                                "category": 28, "sector": 28})
    for row in ws.iter_rows(min_row=2):
        for cell in row:
            cell.alignment = Alignment(vertical="top", wrap_text=cell.column_letter in ("E", "F"))

    wd = wb.create_sheet("data_dictionary")
    sheet(wd, ["column", "meaning"], [{"column": c, "meaning": m} for c, m in COLUMNS], {"column": 20, "meaning": 110})

    wr = wb.create_sheet("rejected")
    sheet(wr, REJ_FIELDS, rejected, {"title": 90, "reason": 36, "google_link": 30, "url": 30})
    wb.save(config.OUT / "records.xlsx")
