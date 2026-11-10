"""Generate release figures, reference appendix, dataset card and submission text.

Run from the repository root: python -m scripts.release_material
Optional publishing dependencies: matplotlib, reportlab, markdown.
"""
from pathlib import Path
from collections import Counter
import csv, json, hashlib, html, shutil
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import markdown

ROOT=Path(__file__).resolve().parents[1]
SITE='https://vishnu0906.github.io/state-ai-policy-tracker/'
REPO='https://github.com/VISHNU0906/state-ai-policy-tracker'
HF='https://huggingface.co/datasets/VKO34/INDIAN-STATE-WISE-AI-POLICY'
DRIVE='https://drive.google.com/drive/folders/1eiXw9zKOpTp3EN4HnGmL0P7h-ZHP8095'
DOC='https://docs.google.com/document/d/1D2oONWv0jaM9RBpK6ak79ZqeVRC90CnHwukn5x4e18Y/edit'

def read(name):
    with (ROOT/name).open(encoding='utf-8-sig',newline='') as f: return list(csv.DictReader(f))

def write(name,text):
    p=ROOT/name;p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(text.strip().replace('\u2014', '; ').replace('\u2013','-')+'\n',encoding='utf-8')

def main():
    rows=read('data/out/records.csv'); n=len(rows)
    counts={k:dict(sorted(Counter(r[k] for r in rows).items())) for k in ['state','category','stage','review_status','summary_basis','gov_level']}
    counts['year']=dict(sorted(Counter(r['date'][:4] for r in rows).items()))
    counts['records']=n;counts['source_reports']=len(read('data/out/record_sources.csv'));counts['rejected_items']=len(read('data/out/rejected.csv'))
    counts['date_basis']='earliest report in cluster, IST';counts['cutoff']='2026-11-10'
    write('reports/release_counts.json',json.dumps(counts,indent=2))
    figdir=ROOT/'docs/figures';figdir.mkdir(exist_ok=True)
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    for key,title,caption in [
        ('state','Records by state','Alphabetical order. Counts reflect collection coverage, not policy quality.'),
        ('year','Records by report year','2026 ends on 10 November. Older indexing and screening coverage differ.'),
        ('stage','Stage inferred from the headline','A launch cue does not establish sustained use or measured benefit.'),
        ('summary_basis','Where the summary comes from','Publisher text is extracted, not independently fact-checked.')]:
        fig,ax=plt.subplots(figsize=(8.6,4.8 if key=='state' else 3.5))
        names=list(counts[key]); vals=list(counts[key].values())
        ax.barh([x.replace('_',' ') for x in names],vals,color='#245d73');ax.invert_yaxis()
        ax.set_xlim(0,max(vals)*1.16)
        for i,v in enumerate(vals):ax.text(v+max(vals)*.015,i,str(v),va='center')
        ax.set_title(title,loc='left',fontweight='bold',pad=12);ax.set_xlabel('Records')
        fig.text(.02,.015,caption,fontsize=8.5);fig.tight_layout(rect=(0,.06,1,1))
        for ext in ['png','svg']: fig.savefig(figdir/f'{key}.{ext}',dpi=170,facecolor='white')
        plt.close(fig)

    rationale='''# Rationale

I wanted a tracker where a reader could follow a record back to the report and understand why it was included. The difficult part is deciding whether several headlines describe one action, and whether that action is a proposal, an agreement, an approval or a service already in use.

I kept news discovery and event records separate. Google News RSS supplies most of the material because it is free and can be queried by state and month. Four query shapes cover government actors, policy instruments, public services, and infrastructure or rules. Raw responses stay in the repository so the release can be rebuilt. Bing adds recent reports. GDELT was tried but much of the collection failed or was skipped. The keyed news adapters are present but were not tested with live credentials.

The selection covers thirteen states. The original count sweep compared all twenty-eight states, then used geographical coverage as a constraint. Andhra Pradesh, Madhya Pradesh and Rajasthan were added for comparison with a separately assembled reference list. This gives useful variation in administrative approaches. It does not produce a representative sample of India.

The pipeline reads the state from the headline, falling back to the description. It handles aliases and context-sensitive abbreviations. Dates are stored in ISO format with precision, and an undated item stays in the rejection log. The main date is the earliest report date, not a verified date of government action.

Deduplication compares reports from the same state within five days, gives rare shared words more weight, and preserves every contributing report. A cancellation must remain separate from the agreement it reverses. The final checks found and repaired a broken cancellation rule, separating two records that had been merged. The release now contains 716 records and 1,306 report links.

I kept the dashboard simple: state, time, category and stage filters, charts, and source links. The full dataset, rejection reasons and method are available separately. The most important limitation is the review boundary. Earlier screening and pair labels were produced by an assistant from headlines. They are not independent human verification. The next useful step is to check official orders, tenders and budgets, then connect announcements to evidence of implementation. More headlines alone will not resolve that gap.
'''
    write('RATIONALE.md',rationale)

    readme=f'''# State AI Policy Tracker

This project collects reports of AI-related action by Indian governments, groups reports that appear to describe the same event, and publishes the results with their sources. The release contains **{n} records across 13 states**, covering 1 January 2022 to 10 November 2026. The last corrective build was made on 11 November 2026.

[Dashboard]({SITE}) | [Trend charts]({SITE}trends.html) | [CSV]({SITE}data/records.csv) | [Hugging Face]({HF}) | [Research notes]({SITE}research.html)

## Start here

For the result, open the dashboard or `data/out/records.xlsx`. For the method, read [METHODOLOGY.md](METHODOLOGY.md). For the reasoning behind the choices, read the one-page [RATIONALE.md](RATIONALE.md). [SUBMISSION.md](SUBMISSION.md) is the submission report. [RELEASE_NOTES.md](RELEASE_NOTES.md) records the final corrections.

The unit is a reported action, not a distinct policy or a successful deployment. News coverage, headline wording and source access affect inclusion. A larger count is not evidence that a state has a better AI policy.

## Files and row counts

| File | Rows | Purpose |
|---|---:|---|
| `data/out/records.csv` | {n} | Main records, one per retained cluster |
| `data/out/records.xlsx` | {n} records | Workbook with data dictionary and rejection log |
| `data/out/record_sources.csv` | {counts['source_reports']:,} | Reports linked to records by `record_id` |
| `data/out/rejected.csv` | {counts['rejected_items']:,} | Dropped items and reasons |
| `data/out/tracker.sqlite` | Three tables | Queryable export of the same data |
| `data/reference/events.csv` | 85 | Separate document-led research appendix, not added to tracker totals |
| `data/reference/sources.csv` | 113 | Sources for the reference appendix |
| `data/reference/source_observations.csv` | 137 | Links between reference events and sources |

The reference appendix uses different event and date rules. It may overlap the tracker. Do not add 85 to 716 or join the tables solely on a title match. It is included so a reviewer can inspect information that news discovery tends to miss.

## Rebuild the release

Use Python 3.11 or later. No API key is required for the saved release.

```powershell
python -m venv .venv
.venv\\Scripts\\Activate.ps1
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

`legacy_headline_screen` marks {counts['review_status'].get('legacy_headline_screen',0)} IDs inherited from the earlier headline-screening pass. The handoff identifies that work as assistant-produced. The flag does not mean the full article or official document was checked by a human. The other {counts['review_status'].get('auto',0)} records are `auto`. A saved field override uses `override_applied` if present. These labels describe processing history, not truth.

The original 2025-26 screening removed 242 of 785 clusters, including 160 relevance exclusions and 82 duplicates. Those are historical diagnostic counts. The current 2022-26 build has 18,559 collected items, 1,662 passing the relevance rules, 967 clusters before saved exclusions, and 716 retained records. Saved exclusions remove 251 current clusters. Do not substitute the older counts for this build.

## Evaluation and limits

### Assumptions and gaps

I treat each row as a reported action. The date is the earliest news report, so it can differ from the government order. English news misses some states and quieter steps such as tenders and Gazette notices. Similar headlines can still merge incorrectly, and late reports can remain duplicates. The older screening was assistant-produced, not a full article check. Seven central-government actions are labelled separately. I would check the original source before using a row to make a claim about spending, implementation or results.

The 140 saved pair labels were assistant-produced. The current diagnostic finds 136 in the rebuilt corpus; the reporting half gives precision 0.96 and recall 1.00 at threshold 0.25. These are development results, not an independent accuracy estimate: 31 headlines occur in both halves, the sample over-represents difficult pairs, and method changes used errors from the whole set.

The earlier approximate coverage check found 37 of 66 in-scope reference events. It used the older 2025-26 snapshot and is not a current recall estimate. Gazette entries, tenders and budget provisions account for important gaps. [Research findings](research/RESEARCH_FINDINGS.md) explains why these gaps change interpretation.

Other limits are English-language discovery, fuzzy state matching, headline-based classification, a five-day comparison window, transitive cluster chains and changing article content. `Government deployment` is the default category and includes {counts['category'].get('Government deployment',0)} records; it is not evidence of {counts['category'].get('Government deployment',0)} operating services. All dates have day precision because feeds supplied timestamps, not because action dates were verified. Record IDs can change when an earlier report changes the cluster seed.

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
'''
    write('README.md',readme)

    report=f'''# Work Test Submission SAFL Vishnu Kosuri

## What I set out to build

I wanted a tracker where the collection and filtering decisions can be checked. A reader should be able to open a record, see the report behind it, and understand why several reports became one event. The work focuses on collection, state and date handling, deduplication, and the limits of what the resulting data can establish.

The release contains **716 records across thirteen states**, from 1 January 2022 to 10 November 2026. It includes 1,306 contributing reports and 17,253 dropped items with reasons. The final correction on 11 November separated two reversals that the earlier 714-record build had merged. No original records were removed.

[Submission folder]({DRIVE}) | [Dashboard]({SITE}) | [Trends]({SITE}trends.html) | [Repository]({REPO}) | [Dataset on Hugging Face]({HF}) | [Direct CSV]({SITE}data/records.csv)

The folder contains the dataset and workbook, code ZIP, Git history, method, one-page rationale, research appendix, charts and verification results. The source project and website use the same exported tables.

## What the dataset represents

An event is a concrete reported step involving AI and a government actor. That can be a policy announcement, a signed agreement, a budget provision, an institution, a public-service application or a rule. A proposal, an approval and a launch are different stages. A cancellation is a new event, even if its headline repeats the original agreement.

The selected states are Andhra Pradesh, Assam, Bihar, Gujarat, Karnataka, Kerala, Madhya Pradesh, Maharashtra, Odisha, Rajasthan, Tamil Nadu, Telangana and Uttar Pradesh. The initial count sweep used the same query for all twenty-eight states and kept geographical variation in the selection. Andhra Pradesh, Madhya Pradesh and Rajasthan were then added for comparison with a separate reference collection. This is a selected sample, not a census.

The dataset labels state, local, judiciary and central actions separately. Seven central-government records are included because they concern a named state. They can be excluded for a state-government-only analysis. Opinion, general statements, private company activity without a government party, party politics and misuse stories without a policy response are excluded.

![Records by state](docs/figures/state.png)

## Collection and sources

Google News RSS supplies most of the discovery coverage. It is free, accepts state and date terms, and indexes national and regional English reporting. Four query shapes cover government actors, policy instruments, public services, and infrastructure or regulation. They run by state and calendar month. Overlap is deliberate because different headlines describe the same action in different terms.

The stored Google collection has 3,068 query responses and 36,855 hits. No Google response reached the collector's 100-item warning threshold. GDELT contributed 896 hits but much of its run failed or was skipped. Bing contributed 172 recent hits. The replay records 391 failed or skipped attempts across sources. These gaps remain visible in the logs.

GNews.io, NewsAPI.org and NewsData.io adapters are included but were not tested with live keys. Tavily extraction is an optional fallback and was not used in the original run. Exa, Firecrawl and Crustdata are not integrated in this repository. The release does not depend on paid access. I would test an additional provider on the same query set before treating it as reliable redundancy: useful new records, failed requests and cost per retained event matter more than the number of connected services.

Raw discovery responses and short page extracts are cached. The page reader resolves the representative publisher link and extracts a description or lead with trafilatura. It tries up to three reports in a cluster when a page fails. Offline mode now explicitly avoids network and optional model calls, including when a page is missing from the cache.

![Summary provenance](docs/figures/summary_basis.png)

## State and date handling

The state comes from the headline, then the description if the headline contains no state. It is not assigned from the query. Full names, aliases, common spelling errors and capitals are recognised. Uttar Pradesh, Uttar-Pradesh, UttarPradesh, UP and U.P. resolve to one name. Ambiguous abbreviations need context: MP next to a government word can mean Madhya Pradesh; Congress MP should not.

Long misspellings can be matched by a similarity rule. This increases coverage but can make mistakes, so it is not a substitute for checking difficult cases. City names have lower weight than state names. Union territories are recognised but excluded from this release.

Dates are converted to ISO format. Timestamped feeds are converted to India time before taking the day. Month, quarter and year inputs keep their precision even though storage uses the first day of the period. An unparseable date is empty. If neither the feed nor URL supplies a usable date, the item goes to the rejection log as no_date.

The parser handles named months, common month misspellings, ordinal suffixes, two-digit years and relative expressions with a supplied reference date. Numeric dates use a documented day-first assumption. Naive timestamps are treated as UTC. Relative hours and week expressions have known limitations because the parser receives a date rather than a full reference timestamp; the method note lists these. None of those loose-date paths was needed for the published feed timestamps.

All 716 records have day precision. That is the precision of the report timestamp. It does not establish the day the government acted. The record date is the earliest report in its cluster. A separate official order may give a different action date.

## How duplicates are handled

Collection first collapses repeated source items. Event matching then compares headlines attributed to the same state within five days. It removes common words, maps a small synonym list, keeps number tokens and gives rare shared words more weight. The similarity score is the average of weighted cosine and weighted overlap. The threshold is 0.25, increasing by 0.08 for each day beyond the first.

Linked pairs form a cluster. A typical headline is chosen as the representative, with outlet preference and report time breaking ties. The earliest report supplies the record date and ID seed. Every retained report stays in record_sources.csv, so a reviewer can inspect the group rather than just its representative.

The final check found that the reversal expression contained literal control characters instead of word boundaries. It also found that identical URLs could bypass state and reversal checks. Both are repaired. Regression tests now keep cancellations separate even when a publisher reuses a URL. This separated the Puch AI cancellation in Uttar Pradesh and the Safe Kerala payment halt, bringing the total from 714 to 716. Their publisher links were resolved and fetched. The payment halt is classified as reversed, not announced.

This remains a rule-based matcher. Reports outside the five-day window can survive as duplicates. Transitive links can join a long chain, and decimal amounts lose precision during tokenisation. A shared headline score does not establish event identity. The correct next check is an independently labelled set with disjoint events across tuning and evaluation, followed by cluster-level review.

## What the checks establish

The release passes 97 tests, including nine added regression cases. The offline build produces the three published CSV tables. The release checks validate required fields, unique record IDs, source links, foreign keys, date order, state names and consistency with the dashboard data. These checks establish structural consistency. They do not establish that every source claim is true.

The saved duplicate-pair file contains 140 assistant-labelled pairs. The current diagnostic finds 136 in the corpus and reports precision 0.96 and recall 1.00 on its reporting half. I would not use those figures as an independent accuracy claim. Thirty-one headlines appear in both halves, and the method was changed after inspecting errors across the set. The earlier approximate reference comparison found 37 of 66 in-scope events, but it used the older 2025-26 snapshot and is not recall for this release.

The review labels have also been corrected. There are 545 historical headline-screening IDs and 171 automatic records. The earlier handoff identifies the screening and pair labels as assistant-produced. No claim is made that I personally read every headline or checked every article. The label records processing history; it does not establish independent human verification.

![Records by year](docs/figures/year.png)

## Findings and the next evidence needed

The retained report counts are 23 in 2022, 47 in 2023, 94 in 2024, 163 in 2025 and 389 in 2026 through 10 November. The rise is descriptive of this collection. Older indexing, changing press coverage and different screening coverage make a policy-growth estimate unsupported.

Headline rules classify 334 records as announced, 176 as launched, 85 as signed, 57 as approved, four as reversed and sixty as unspecified. These categories describe wording. They do not establish use, spending or benefit. Government deployment is the fallback category for 317 records, so it particularly needs further checking.

The separate 85-event research appendix adds a different kind of evidence. It preserves official-document links, date explanations and limitations across twelve states. It is not merged into the 716 records because the event definitions and dates differ. Its useful contribution is the distinction between an announcement, a formal instrument and evidence of execution.

For example, Rajasthan's GPU-server request for proposals is dated 24 March 2026 and specifies procurement requirements. It establishes a procurement step, not installed capacity. The appendix records separate Odisha policy approval and Gazette-publication milestones; that distinction would disappear if every milestone inherited a newspaper date. Its Tamil Nadu mission record points to a government order, which is a different evidentiary object from a general mission headline. The Odisha and Tamil Nadu links timed out during the final access check; the inherited source notes remain attached and these examples are not presented as newly reverified.

The two recovered reversal cases show why stage matters. Reporting places the UP agreement on 23 March 2026 and the cancellation decision on 26 March; the tracker retains the report date of 27 March. The Kerala court payment halt is reported on 21 June 2023, while the report describes the preceding day's order. Neither belongs in a count of uninterrupted delivery.

I would next look for award and acceptance records behind tenders, completion counts behind training targets, and usage or evaluation results behind service launches. Budget provisions, private investment promises and expenditure should remain separate. More news sources can improve discovery, but those follow-up documents are what let the tracker say something useful about implementation.

Sources for these examples: [Rajasthan RFP](https://risl.rajasthan.gov.in/uploads/tenders/924cfd3d-e99e-42e1-ac75-ec0be93851ad.pdf), [Odisha Gazette](https://egazette.odisha.gov.in/Archival_ControllerEW/download_gazette/5343), [Tamil Nadu mission order](https://cms.tn.gov.in/cms_migrated/document/GO/it_e_25_2024_Ms.pdf), [UP cancellation report](https://www.newindianexpress.com/states/uttar-pradesh/2026/Mar/27/up-government-cancels-rs-25000-crore-mou-with-puch-ai-over-financial-concerns), [Kerala court report](https://www.scconline.com/blog/post/2023/06/21/kerala-hc-directs-govt-halt-payment-safe-kerala-project-deals/).

## Reading and reproducing the submission

The Google Drive folder has one current location for each deliverable. Start with this document and the one-page rationale. Open the workbook to inspect records, the data dictionary and exclusions. Use the source table to inspect grouped reports. The method note explains the rules and edge cases; the research appendix contains the document-led findings and original source links.

The code ZIP contains the pipeline, tests and caches. The Git bundle preserves the development history. Follow the README to rebuild offline and serve the static site locally. A weekly GitHub workflow collects recent candidates into a review artifact; it does not silently add them to the published dataset. The dataset card describes the separate tables and the limits on reuse of publisher text.
'''
    write('SUBMISSION.md',report)
    hfcard=f'''---
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

716 retained records across thirteen Indian states, covering report dates from 1 January 2022 to 10 November 2026. Corrective release: 11 November 2026. [Dashboard]({SITE}), [trend charts]({SITE}trends.html), [code and method]({REPO}).

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
'''
    write('huggingface_dataset/README.md',hfcard)
    for f in ['records.csv','record_sources.csv','rejected.csv']: shutil.copyfile(ROOT/'data/out'/f, ROOT/'huggingface_dataset'/f)
    for src,dst in [('events.csv','reference_events.csv'),('sources.csv','reference_sources.csv'),('source_observations.csv','reference_links.csv')]:
        if (ROOT/'data/reference'/src).exists():shutil.copyfile(ROOT/'data/reference'/src,ROOT/'huggingface_dataset'/dst)

    css='body{max-width:900px;margin:40px auto;padding:0 22px;font:17px/1.65 system-ui;color:#17232c}h1,h2{line-height:1.2;color:#000}h2{margin-top:36px}a{color:#135b78}img{max-width:100%}table{border-collapse:collapse;font-size:14px}td,th{border:1px solid #ddd;padding:8px}pre{overflow:auto;background:#f5f5f5;padding:16px}'
    body=markdown.markdown(report.replace('docs/figures/','figures/'),extensions=['tables','fenced_code'])
    write('docs/research.html',f'<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>State AI Policy Tracker research and method</title><style>{css}</style><body><nav><a href="index.html">Dashboard</a> | <a href="trends.html">Trends</a></nav>{body}</body></html>')
    # Native Google Docs receives the same structured content, with local figures embedded.
    import base64
    for fig in ['state','year','stage','summary_basis']:
        data=base64.b64encode((figdir/f'{fig}.png').read_bytes()).decode()
        body=body.replace(f'src="figures/{fig}.png"',f'src="data:image/png;base64,{data}" width="580"')
    write('reports/submission_for_google_docs.html',f'<html><body style="font-family:Arial;font-size:11pt;color:#000">{body}</body></html>')
    write('reports/submission_links.json',json.dumps(dict(dashboard=SITE,repository=REPO,huggingface=HF,drive=DRIVE,google_doc=DOC),indent=2))
    print(json.dumps(counts,indent=2))

if __name__=='__main__': main()
