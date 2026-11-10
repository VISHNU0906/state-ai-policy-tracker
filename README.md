# State AI Policy Tracker

A pipeline that collects news about AI-related policy activity by Indian state governments, turns it into one deduplicated record per event, and shows it on a static dashboard.

- **Live dashboard:** https://vishnu0906.github.io/state-ai-policy-tracker/
- **Dataset:** [`data/out/records.csv`](data/out/records.csv) and [`records.xlsx`](data/out/records.xlsx) (543 records, 13 states, 1 January 2025 to 10 November 2026)
- **Rationale note (one page):** [`RATIONALE.md`](RATIONALE.md)

## What is in the dataset

| File | Rows | What it is |
|---|---|---|
| `data/out/records.csv` / `.xlsx` | 543 | One row per event. The main deliverable. |
| `data/out/record_sources.csv` | 1,076 | One row per news report, linked to its record by `record_id`. Merging duplicates loses nothing. |
| `data/out/rejected.csv` | 8,397 | Every item the pipeline dropped, with a reason code. This is how the inclusion line can be audited. |
| `data/out/tracker.sqlite` | 3 tables | The same tables in one file for querying. |

Columns of `records.csv` (the XLSX has a data dictionary sheet):

| Column | Meaning |
|---|---|
| `record_id` | Stable ID: state code, date, short hash of the earliest headline. |
| `state` | Canonical state name, read from the article text, not from the search query. |
| `date`, `date_precision` | Date of the earliest report, India time. Precision is `day`, `month`, `year` or `unknown`. |
| `title`, `summary` | Headline of the representative article and one line on what happened. |
| `category` | Kind of step: Policy and strategy, Regulation and ethics, Institutions and bodies, Funding and budget, Infrastructure and investment, Partnerships and MoUs, Skilling and education, Government deployment. |
| `stage` | announced, signed, approved, launched, reversed or unspecified. |
| `sector` | Area of government (health, agriculture, policing, education and so on). |
| `gov_level` | state, local (district or city body) or judiciary (High Court). |
| `source_name`, `source_url` | Publisher and direct link (never a Google redirect). |
| `n_outlets`, `other_outlets` | How many distinct outlets reported the event, and which. |
| `confidence`, `summary_basis`, `review_status` | How strong the headline signals were, where the summary came from, whether the record was hand-checked. |

## How it works

```
collect  ->  filter  ->  dedupe  ->  read page  ->  classify  ->  review  ->  export
9,473 items  1,417       785 events                               543 records
```

1. **Collect** (`pipeline/collect.py`, `pipeline/sources/`). One adapter per source, all returning the same item shape. Every response is cached on disk, so a rerun makes no network calls and gives identical output.
2. **Filter** (`pipeline/relevance.py`, `pipeline/states.py`). Readable rules decide whether an item is state AI policy activity and which state it belongs to. Every item gets a reason code.
3. **Dedupe** (`pipeline/dedupe.py`). Reports of one announcement are grouped into one record.
4. **Read page** (`pipeline/enrich.py`). For the article chosen to represent each event, resolve the publisher URL and read the page locally to get a real summary sentence.
5. **Classify** (`pipeline/taxonomy.py`). Category, stage, sector, government level.
6. **Review** (`data/review/overrides.csv`). Hand decisions applied by record ID.
7. **Export** (`pipeline/export.py`). All outputs, including the JSON the dashboard reads.

## Sources: what was used and why

| Source | Role | Result |
|---|---|---|
| Google News RSS | Backbone. Free, no key, indexes national and regional English press, and accepts `after:` / `before:` so 22 months can be covered month by month. | 1,196 queries, 16,800 hits, none at the 100-item cap, none failed. |
| GDELT DOC API | Second, independent index. | **Mostly a stub in this run.** The API returned HTTP 429 for most calls even at one request per 6.5 seconds, so only 8 two-month windows were collected (Karnataka and part of Telangana). The adapter is complete and cached; rerunning it later fills the gap. |
| Bing News RSS | Recent weeks only (no date operators). | 172 hits for ten states. |
| GNews.io, NewsAPI.org, NewsData.io | Redundancy for the last 30 days. Their free plans cannot reach back further (100 requests a day, 30 days of history), so they cannot be the backbone. | **Written but never run against the live APIs**, because no keys were available. Treat as untested. |
| trafilatura (local) | Reads the publisher page for a description, lead and page date. Free, no key. | 787 pages attempted; every record has a publisher link, and 96 percent have a summary taken from the page. |
| Tavily extract | Optional fallback for pages that block a plain fetch. | Not used (no key). |

Four query shapes are issued per state per month, each aimed at one part of the brief's definition (government actor, policy instrument, sector deployment, infrastructure and regulation). They overlap on purpose; the deduper removes the overlap.

## Which states, and why

A count sweep ran one identical query for all 28 states over six months (`scripts/state_sweep.py`, results in `data/state_sweep.csv`). Ten states were taken from the top of that ranking with one constraint: at least two from each of four zones, so the dataset is not only the southern IT states. Three more (Andhra Pradesh, Madhya Pradesh, Rajasthan) were added so the output could be scored against an independent reference list that covers them. The sweep under-counts Andhra Pradesh and Madhya Pradesh because headlines call them "AP" and "MP".

Final set: Karnataka, Telangana, Tamil Nadu, Kerala, Andhra Pradesh, Maharashtra, Gujarat, Rajasthan, Uttar Pradesh, Bihar, Madhya Pradesh, Odisha, Assam.

## Where the line is drawn

**In:** a state government, or a body that answers to it (departments, state police, state-run agencies and universities, district and city administrations), or the state's High Court, takes a concrete step involving AI: adopts or drafts a policy, sets up a body or institution, signs an agreement, deploys AI in a public function, commits money, starts a training programme, or makes a rule.

**Out:** opinion and explainers; speeches with no concrete step; central government actions that merely happen in a state; company news with no state body as a party; crime stories where AI is the tool, unless the state responds with a rule; party politics; meetings and conferences with no reported outcome.

Each "out" has a reason code in `rejected.csv`: `no_ai_term`, `no_state_named`, `no_government_actor`, `no_concrete_step`, `opinion_or_explainer`, `statement_only`, `commentary_or_reaction`, `meeting_or_event_only`, `central_government_actor`, `ai_misuse_or_crime_no_policy_step`, `party_politics`, `foreign_story`, `multi_state_roundup`, `union_territory`, `social_or_aggregator_source`, `state_not_prioritised`, `outside_window`, `dropped_in_review`.

## States and dates

**States.** `pipeline/states.py` holds 36 states and union territories with alternative spellings, old names (Orissa, Uttaranchal), the new name Keralam, abbreviations and major cities. "UP", "Uttar Pradesh", "Uttar-Pradesh", "U.P." and "UttarPradesh" all map to Uttar Pradesh. Ambiguous abbreviations are handled deliberately: "MP" is Madhya Pradesh only next to a government word ("MP govt") or at the start of a headline before a verb ("MP to set up..."), never in "Congress MP". "Punjab" beside "Lahore" and "Bengal" in "Bay of Bengal" are rejected. The state comes from the headline; a query for one state often returns stories about another.

**Dates.** `pipeline/dates.py`. Feed timestamps are converted to India time before the day is taken (20:30 UTC on the 7th is the 8th in India). Every record carries `date_precision`. A month-only date is stored as the first of the month and flagged, never passed off as a day. An unparseable date stays empty with precision `unknown`. In this run all 543 records have day precision, because the feeds always supplied a timestamp. The date is the earliest report of the event, which can trail the announcement by a day.

**Date cross-check.** The publisher page's own date was available for 532 of the 543 records. It matches the feed date exactly for 455 (86 percent) and within one day for 485 (91 percent). The 42 that differ by more than 30 days were traced to the page reader, not the feed: two sites return the day the page was fetched and one returns a placeholder date. The feed date is therefore the one kept, and the page date is used only as a check.

## Deduplication

One announcement is reported in many wordings, so URL or exact-title matching is not enough. The method (`pipeline/dedupe.py`):

1. Compare only headlines for the same state within five days.
2. Reduce each headline to content words: hyphenated words split, light stemming, common synonyms mapped ("pact", "MoU", "agreement"), and words every headline shares ("govt", "AI", the state name) removed.
3. Weight words by rarity, so a shared "TCS" or "70,000" counts far more than a shared "school".
4. Similarity is the mean of weighted cosine and weighted overlap. Link a pair when it reaches 0.25, plus 0.08 for each day of separation beyond one.
5. Never link a reversal ("cancels", "scraps") to a non-reversal.
6. Join linked pairs into clusters. The most typical headline in a cluster, from a preferred outlet, represents it.

**Measured accuracy.** 140 headline pairs were sampled evenly across similarity bands, so hard cases are over-represented, and labelled by reading them (`data/review/dedup_pairs.csv`). The threshold was chosen on half of the pairs and the figures below are from the other half (`python -m scripts.eval_dedupe`). Treat them as optimistic: the tokenising and synonym fixes were made after reading errors across all 140 pairs, so only the threshold, not the method, was kept blind to the reporting half.

| Version | Precision | Recall | Change |
|---|---|---|---|
| First | 0.98 | 0.58 | Cosine only; each headline compared with the first in its cluster. |
| Second | 0.91 | 0.92 | Fixed glued hyphenated tokens; synonyms; overlap measure; transitive linking. |
| Current | 0.89 | 1.00 | Lower threshold with the reversal and day-gap guards, added after reading clusters and finding two real false merges. |

**What still slipped through.** The hand review is the better test, and it is less flattering than the table. It found 82 duplicate records among 785 events (10 percent). Of the 80 whose original could be dated, 45 were within the five-day window, where the wording was simply too different for the similarity score, and 35 were late write-ups outside the window, which the method cannot join by design. All were removed by hand.

## Checks on the result

**Hand review.** Every record's headline was read once, in two passes as the pipeline changed, followed by a scan for same-state near-duplicates within 45 days. 242 of 785 events were removed: 160 were not state AI policy activity and 82 were duplicates. So the rules alone are right about relevance 80 percent of the time. Decisions with reasons are in `data/review/overrides.csv`. Only headlines were read; individual articles were not opened and checked against their rows.

**Coverage against an independent list.** `data/review/reference_events.csv` is a list of 85 events researched separately by hand, mostly from official documents. It was not used to build or tune the pipeline. 66 of its events fall inside these states and this window (`python -m scripts.eval_coverage`, measured before the hand review):

| Outcome | Events |
|---|---|
| Present in the dataset | 37 (56%) |
| Collected but dropped by a rule | 5 (8%) |
| Not collected | 24 (36%) |

The 24 misses are mostly procedural steps that do not make headlines: a tender, a request for information, gazette publication of a policy, notification of rules, single budget lines. That is the main limit of a news-based pipeline. Matching is automatic and approximate; `data/review/coverage_check.csv` lists every match so it can be checked.

**Tests.** `python -m pytest -q` runs 51 tests on state aliases, date handling, reason codes and dedup cases.

## Known holes

- **English only.** No Hindi or regional-language reporting. This matters most for Uttar Pradesh, Bihar, Madhya Pradesh and Rajasthan, and partly explains their lower counts.
- **News, not documents.** Steps recorded only in official documents are missed (see the coverage check).
- **Headline-driven.** Relevance, category and stage are read from the headline. A relevant article whose headline names no state is dropped. Leader names ("Naidu", "Revanth") are not mapped to states.
- **GDELT is mostly missing** and the keyed news APIs are untested (see Sources).
- **Counts are reported activity, not policy quality.** A state with a larger English press shows more records.
- **"Government deployment" is the default category** and holds 227 of 543 records. Some belong elsewhere.
- **Stage is a headline cue.** "Announced" includes some loosely worded intentions.
- **One reviewer.** The dedup labels and the review decisions were made by one reviewer, once, from headlines.
- **Late duplicates.** Reports more than five days apart are not merged automatically.
- **Google News RSS is unofficial** and its redirect links are decoded with a third-party library that depends on Google's page format.
- **The optional LLM check step (`pipeline/llm.py`) has not been run.**

## Run it

```
pip install -r requirements.txt
python -m pytest -q
PIPELINE_OFFLINE=1 python -m pipeline.collect     # rebuild the item pool from the committed cache, no network
python -m pipeline.build                          # filter, dedupe, read pages (cached), classify, export
python -m scripts.eval_dedupe
python -m scripts.eval_coverage
python -m http.server 8790 --directory docs       # dashboard at http://localhost:8790
```

On Windows PowerShell, set the variable first: `$env:PIPELINE_OFFLINE = "1"`. Without it, `collect` fetches live (about 40 minutes for 13 states because requests are paced). Optional keys go in `.env`; see `.env.example`.

## Dashboard

`docs/` holds three static files that read `docs/data/records.json`, written by the pipeline, so the page and the CSV cannot drift apart. The main view is a state by month grid; below it are the mix of step types per state, records by sector, and a searchable list where every record links to its source. Chart colours follow a fixed order checked for colour-blind separation.
