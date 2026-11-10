---
language:
- en
pretty_name: Indian State AI Policy Tracker
size_categories:
- n<1K
task_categories:
- tabular-classification
tags:
- india
- public-policy
- artificial-intelligence
configs:
- config_name: records
  default: true
  data_files:
  - split: train
    path: records.csv
- config_name: source_reports
  data_files:
  - split: train
    path: record_sources.csv
- config_name: excluded_items
  data_files:
  - split: train
    path: rejected.csv
- config_name: reference_events
  data_files:
  - split: train
    path: reference_events.csv
- config_name: reference_sources
  data_files:
  - split: train
    path: reference_sources.csv
- config_name: reference_links
  data_files:
  - split: train
    path: reference_links.csv
---

# Indian State AI Policy Tracker

716 retained records across thirteen Indian states, covering report dates from 1 January 2022 to 10 November 2026. Corrective release: 11 November 2026. [Dashboard](https://vishnu0906.github.io/state-ai-policy-tracker/), [trend charts](https://vishnu0906.github.io/state-ai-policy-tracker/trends.html), [code and method](https://github.com/VISHNU0906/state-ai-policy-tracker).

## Tables

| Configuration | Rows | Meaning |
|---|---:|---|
| records | 716 | One retained report cluster per record |
| source_reports | 1,306 | Contributing reports, joined on record_id |
| excluded_items | 17,253 | Rejected candidates and reason codes |
| reference_events | 85 | Separate document-led appendix, not extra tracker rows |
| reference_sources | 113 | Sources attached to reference events |
| reference_links | 137 | Reference event-source relationships |

The `train` split is a file-loading convention. It does not mean these tables are a training set or a benchmark. Different configurations have different schemas. Do not concatenate them.

## Collection and review

Google News RSS supplied most discovery results, with partial GDELT coverage and recent Bing RSS results. Rules select relevance and state, normalise dates, group related headlines and classify category, stage, sector and government level. Descriptions and short leads come from publisher pages where available. The raw release window is fixed; it is not a live census.

`date` means earliest report date in the cluster, in India time. All released rows have day precision from feed timestamps. It is not a verified government-action date. `legacy_headline_screen` marks 545 historical IDs from assistant-produced headline screening; 171 rows are `auto`. Neither label establishes human article verification. Pair labels and earlier exclusions were assistant-produced. `confidence` measures the strength of rule matches, not a probability of truth.

The 85-event reference appendix was assembled separately through source research. It retains action-date explanations, source links and limitations. It overlaps the tracker and must not be added to its totals. The two collections use different inclusion and date rules.

## Fields

Main records: record_id, state, date, date_precision, title, summary, category, stage, sector, gov_level, source_name, source_url, n_outlets, other_outlets, confidence, summary_basis, review_status. The workbook and repository describe the fields and fixed categories. Source reports retain their original links, including Google redirect URLs. All 716 representative links resolve to publisher domains in the release.

## Limits and suitable use

Useful for exploring reported actions and directing source review. Unsuitable as a census, a ranking of policy quality, a measure of expenditure, an estimate of adoption, or ground truth for model evaluation. English indexing, incomplete sources, headline rules, residual duplicates and assistant screening affect coverage. Seven central-government actions are labelled separately. The default Government deployment category is not evidence of an operating service.

The current pair diagnostic is not independent: headlines overlap between tuning and reporting halves, and the method used errors from both. Historical coverage figures refer to an older snapshot. Read the repository's methodology and release notes before interpreting counts.

## Rights and provenance

Headlines, publisher descriptions and excerpts remain subject to the original publishers' rights. No blanket MIT or CC licence is claimed for third-party text. Linking a source does not transfer its rights. Source URLs are provided for attribution and verification; no full articles or private writing archive are included. Check the source terms for your proposed reuse.

## Changes from the 714-record version

The reversal matcher used control characters instead of word boundaries. Repairing it, and enforcing state and reversal guards on shared URLs, separated two previously merged steps. No original records were removed. The report count remains 1,306. The two added IDs are UP-2026-03-27-69d6e4 and KL-2023-06-21-69af46. Review labels now state their actual provenance.
