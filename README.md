# State AI Policy Tracker

This project collects reports of AI-related action by Indian governments, groups reports that appear to describe the same event, and publishes the results with their sources. The release contains **716 records across 13 states**, covering 1 January 2022 to 10 November 2026. The last corrective build was made on 11 November 2026.

[Dashboard](https://vishnu0906.github.io/state-ai-policy-tracker/) | [Trend charts](https://vishnu0906.github.io/state-ai-policy-tracker/trends.html) | [CSV](https://vishnu0906.github.io/state-ai-policy-tracker/data/records.csv) | [Hugging Face](https://huggingface.co/datasets/VKO34/INDIAN-STATE-WISE-AI-POLICY) | [Research notes](https://vishnu0906.github.io/state-ai-policy-tracker/research.html)

## Start here

For the result, open the dashboard or `data/out/records.xlsx`. For the method, read [METHODOLOGY.md](METHODOLOGY.md). For the reasoning behind the choices, read the one-page [RATIONALE.md](RATIONALE.md). [SUBMISSION.md](SUBMISSION.md) is the submission report. [RELEASE_NOTES.md](RELEASE_NOTES.md) records the final corrections.

The unit is a reported action, not a distinct policy or a successful deployment. News coverage, headline wording and source access affect inclusion. A larger count is not evidence that a state has a better AI policy.

## Files and row counts

| File | Rows | Purpose |
|---|---:|---|
| `data/out/records.csv` | 716 | Main records, one per retained cluster |
| `data/out/records.xlsx` | 716 records | Workbook with data dictionary and rejection log |
| `data/out/record_sources.csv` | 1,306 | Reports linked to records by `record_id` |
| `data/out/rejected.csv` | 17,253 | Dropped items and reasons |
| `data/out/tracker.sqlite` | Three tables | Queryable export of the same data |
| `data/reference/events.csv` | 85 | Separate document-led research appendix, not added to tracker totals |
| `data/reference/sources.csv` | 113 | Sources for the reference appendix |
| `data/reference/source_observations.csv` | 137 | Links between reference events and sources |

The reference appendix uses different event and date rules. It may overlap the tracker. Do not add 85 to 716 or join the tables solely on a title match. It is included so a reviewer can inspect information that news discovery tends to miss.

## Rebuild the release

Use Python 3.11 or later. No API key is required for the saved release.

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pytest -q
$env:PIPELINE_OFFLINE = "1"
python -m pipeline.collect
python -m pipeline.build
python -m scripts.validate_release
python -m http.server 8790 --directory docs
```

On bash, use `source .venv/bin/activate` and `export PIPELINE_OFFLINE=1`. Open `http://localhost:8790`. A missing page cache is explicitly marked `offline_cache_miss`; offline mode does not fetch a page or call the optional model. Rebuilding may change binary XLSX or SQLite bytes; compare the CSV tables and chart values. Clear the environment variable to collect live data. The fixed historical window is in `pipeline/config.py`.

## How collection works

Google News RSS is the main discovery source. The stored run contains 3,068 Google query results and 36,855 hits before URL-level collapse. Four query shapes are issued per state per month. None of those Google responses reached the collector's 100-item warning threshold. This does not establish complete search coverage.

GDELT returned 896 hits but much of its coverage failed or was skipped. Bing News RSS contributed 172 hits. Across collection sources there were 391 failed or skipped query attempts in the cached replay. GNews.io, NewsAPI.org and NewsData.io adapters were written but not exercised with live keys. They should not be described as tested redundancy. Provider plans and historical limits need checking before use; no paid plan is required for this release.

Page reading uses trafilatura locally, with a cached Google redirect decoder where needed. Tavily extraction is optional and was not used in the original run. Exa, Firecrawl and Crustdata are not integrated in this repository. The optional model stage is untested and disabled in offline mode. Its presence is not evidence of model-verified data.

## Inclusion and state selection

A report must identify AI, a government actor and a concrete action. Included actions cover policies, institutions, agreements, public-service use, budgets, skills programmes and rules. District bodies and High Courts have separate `gov_level` values. Seven central-government records are retained and labelled `central`; exclude them when analysing state-government activity alone.

Opinion, general advocacy, company news without a government party, party politics and AI misuse without a policy response are excluded. Reason codes remain in `rejected.csv`.

The states are Andhra Pradesh, Assam, Bihar, Gujarat, Karnataka, Kerala, Madhya Pradesh, Maharashtra, Odisha, Rajasthan, Tamil Nadu, Telangana and Uttar Pradesh. A common query across all 28 states informed the initial selection, with geographical variation as a constraint. Three states were added for comparison with the independent reference collection. Search volume is a discovery aid, not a state ranking.

## Review means exactly this

`legacy_headline_screen` marks 545 IDs inherited from the earlier headline-screening pass. The handoff identifies that work as assistant-produced. The flag does not mean the full article or official document was checked by a human. The other 171 records are `auto`. A saved field override uses `override_applied` if present. These labels describe processing history, not truth.

The original 2025-26 screening removed 242 of 785 clusters, including 160 relevance exclusions and 82 duplicates. Those are historical diagnostic counts. The current 2022-26 build has 18,559 collected items, 1,662 passing the relevance rules, 967 clusters before saved exclusions, and 716 retained records. Saved exclusions remove 251 current clusters. Do not substitute the older counts for this build.

## Evaluation and limits

The 140 saved pair labels were assistant-produced. The current diagnostic finds 136 in the rebuilt corpus; the reporting half gives precision 0.96 and recall 1.00 at threshold 0.25. These are development results, not an independent accuracy estimate: 31 headlines occur in both halves, the sample over-represents difficult pairs, and method changes used errors from the whole set.

The earlier approximate coverage check found 37 of 66 in-scope reference events. It used the older 2025-26 snapshot and is not a current recall estimate. Gazette entries, tenders and budget provisions account for important gaps. [Research findings](research/RESEARCH_FINDINGS.md) explains why these gaps change interpretation.

Other limits are English-language discovery, fuzzy state matching, headline-based classification, a five-day comparison window, transitive cluster chains and changing article content. `Government deployment` is the default category and includes 317 records; it is not evidence of 317 operating services. All dates have day precision because feeds supplied timestamps, not because action dates were verified. Record IDs can change when an earlier report changes the cluster seed.

## Repository map

```text
pipeline/       collection, date/state rules, clustering, page reading, export
scripts/        diagnostics, release checks, figures and publication material
tests/          state/date/relevance cases and release regression tests
data/raw/       cached discovery responses and short page extracts
data/review/    saved exclusions, pair labels and historical screening IDs
data/out/       published tables and workbook
data/reference/ separate 85-event evidence appendix
docs/           static dashboard, trends and research page for GitHub Pages
research/       findings and source-selection notes
reports/        counts, checks and release change log
```

## Scheduled collection

GitHub Pages serves `docs/`. The weekly discovery workflow collects a recent 14-day window into an artifact for review. It does not overwrite the published dataset or apply the historical screening flag to new IDs. Scheduled runs depend on GitHub availability and have no exact execution-time guarantee. Artifacts are retained for 30 days; long-term collection history requires a reviewed commit. API keys, if added later, belong in repository secrets, never in files.

## Rights

Headlines, excerpts and source pages remain subject to their publishers' rights. This repository does not grant a new licence to that material. The Hugging Face card separates the tables, describes their provenance and links to the originals. No private writing archive, credentials or personal email correspondence is included.
