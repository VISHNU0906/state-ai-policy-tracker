# Methodology

The method below describes the corrected 716-record release. The report date is not a verified action date. Historical screening was assistant-produced. File names refer to `pipeline/`.

## 1. Collection (`collect.py`, `sources/`)

Each source has one adapter that returns items in a common shape: title, source name, source domain, publisher URL (or Google redirect), publish time in UTC, description, origin. Later stages do not know which source an item came from.

For Google News RSS, four query shapes are issued for every state and every calendar month:

| Shape | Aimed at | Query (state term in front) |
|---|---|---|
| gov | Government as actor | `(AI OR "artificial intelligence") (government OR govt OR cabinet OR minister OR "chief minister")` |
| instrument | Policy instruments | `AI (policy OR mission OR "task force" OR "centre of excellence" OR MoU OR budget OR crore)` |
| sector | Deployments | `AI (police OR health OR hospital OR agriculture OR farmers OR school OR education OR governance)` |
| infra_reg | Infrastructure and rules | `("data centre" OR "AI city" OR "AI university" OR deepfake OR "AI rules" OR "AI guidelines") (government OR govt OR policy)` |

The state term includes short forms where headlines use them (`"Uttar Pradesh" OR "UP govt" OR "UP government"`). Each query carries `after:` and `before:` for one month. Monthly slicing keeps every query under the feed's 100-item ceiling; the collector logs any query that reaches it (none did).

Every response is written to `data/raw/` keyed by a hash of the query. With `PIPELINE_OFFLINE=1` the collector reads only that cache, so collection reads saved responses without network. Offline page-cache misses are explicit and do not fetch; the CSV outputs are checked for reproducibility. A source that fails is logged in `collect_log.json` and skipped; it never stops the run.

## 2. Relevance (`relevance.py`)

Rules are regular expressions, applied in a fixed order. The first rule that fires sets the reason code.

| Order | Test | Reason code if it fails |
|---|---|---|
| 1 | Source is not a social network or aggregator | `social_or_aggregator_source` |
| 2 | Text has an AI term ("AI" in capitals as a whole word, "artificial intelligence", "generative AI", "machine learning", "deepfake", "LLM", "facial recognition", "chatbot") after removing false ones (Air India, AI 171 flight numbers, artificial insemination) | `no_ai_term` |
| 3 | A state can be attributed (section 3) | `no_state_named` |
| 4 | Fewer than three states are named strongly | `multi_state_roundup` |
| 5 | The state is a state, not a union territory | `union_territory` |
| 6 | Headline is not opinion or an explainer | `opinion_or_explainer` |
| 7 | Not a foreign story | `foreign_story` |
| 8 | Not party politics | `party_politics` |
| 9 | Not a crime or misuse story, unless it reports a rule | `ai_misuse_or_crime_no_policy_step` |
| 10 | If the central government is the actor and the state is not, the item is kept and labelled `gov_level = central` | (kept) |
| 11 | A government actor is present (a government word, or the state name directly followed by a verb: "Assam signs ...") | `no_government_actor` |
| 12 | An instrument or an action is present | `no_concrete_step` |
| 13 | Not commentary or reaction | `commentary_or_reaction` |
| 14 | Not a meeting or event with no outcome | `meeting_or_event_only` |
| 15 | Not a bare statement ("says", "urges") without an action and an instrument | `statement_only` |

## 3. State normalisation (`states.py`)

The state is read from the headline, and from the description only when the headline names none. It is never taken from the search query, because a query for one state often returns stories about another.

| Evidence | Example | Weight | Rule |
|---|---|---|---|
| Full name or alias, any spacing or hyphen | Uttar Pradesh, Uttar-Pradesh, UttarPradesh, Orissa, Keralam | 3 | Case-insensitive whole word |
| Common misspelling | Karnatka, Maharastra, Gujrat, Uttrakhand, Orrisa, Rajastan, Kerela | 3 | Listed as aliases |
| Safe abbreviation | UP, U.P., TN | 3 | Capitals only, whole word ("up" in a sentence does not match) |
| Ambiguous abbreviation | MP, AP, HP, WB, TG | 3 | Only next to a government word ("MP govt") or at the start of a headline before a verb ("MP to set up"). "Congress MP" does not match. |
| Capital or major city | Lucknow, Bengaluru, Hyderabad | 1 | Used only when no state name is present |
| Lookalike context | Punjab with Lahore; Bengal in "Bay of Bengal" | 0 | Rejected |

The state with the highest total weight wins; ties go to the one named first. A name and its own short alias ("Andhra Pradesh", "Andhra") count once. For a single free-text label (a cell in a spreadsheet, not a headline), `normalize_state` also tries the closest canonical name by edit similarity (cutoff 0.84, labels of six letters or more), so "Karnatak" and "Tamil Naddu" resolve and "Goaa" does not.

## 4. Date normalisation (`dates.py`)

Every record has `date` (ISO) and `date_precision`. A coarse date is stored as the first day of its period and flagged; it is never presented as a day. An unparseable date is left empty with precision `unknown`.

| Input | Stored date | Precision |
|---|---|---|
| `2026-07-07T20:30:00Z`, `2026-07-07 20:30:00`, epoch seconds | 2026-07-08 (converted to India time first) | day |
| `2026-09-21`, `2026/09/21`, `21/09/2026`, `21-09-26`, `21.09.2026` | 2026-09-21 (numeric dates are read day first) | day |
| `09/21/2026` | 2026-09-21 (month first only because day first is impossible) | day |
| `21 Sept 2026`, `21st September, 2026`, `Sept. 21 2026` | 2026-09-21 | day |
| `Tuesday, 10 November 2026`, `Updated: Nov 10, 2026 10:30 IST` | 2026-11-10 | day |
| `21st Septmber, 2026`, `3 Febuary 2026` (misspelt month) | resolved to the closest month name | day |
| `today`, `yesterday`, `3 days ago`, `5 hours ago` | resolved only when the writing date is known | day |
| `Sep 2026`, `2026-09`, `09/2026`, `early March 2026`, `mid-March 2026`, `first week of March 2026` | first of the month | month |
| `last week`, `last month` | first of that month, only when the writing date is known | month |
| `Q3 2026`, `Jan-Mar 2026` | first day of the quarter | quarter |
| `2026`, `FY 2025-26`, `2025-26` | 1 January, or 1 April for a fiscal year | year |
| `soon`, `recently`, empty, `31/02/2026`, relative phrases with no writing date | empty | unknown |

Order of preference for a record's date: feed timestamp, then a date in the URL path (`/2026/09/21/`), then unknown. A kept item with no date is moved to the rejected log with reason `no_date`, because it cannot be placed on a timeline or deduplicated. The date of a record is the earliest report in its cluster. As a check, the publisher page's own date is compared with the feed date (README, "Date cross-check").

## 5. Deduplication (`dedupe.py`)

Two levels of identity are kept apart: an article (one row in `record_sources.csv`) and an event (one row in `records.csv`).

1. **Blocking.** Only headlines attributed to the same state and at most five days apart are compared.
2. **Tokens.** Lower-case; split hyphenated words; strip plural and tense endings; map synonyms to one word (pact, agreement, deal, partnership -> mou; varsity -> university; approve, nod, okay -> clear); keep numbers with commas and decimals removed (70,000 -> 70000); drop stop words, including the state's own name and words every headline shares (govt, AI, launches).
3. **Weights.** Each token is weighted by inverse document frequency over all kept headlines, so a rare shared token (a company name, an amount) outweighs a common one (school).
4. **Similarity.** Mean of weighted cosine and weighted overlap coefficient. Cosine alone penalises a short headline matched with a long one.
5. **Link rule.** Link when similarity >= 0.25 + 0.08 x max(0, days apart - 1). Never link a reversal headline (cancels, scraps, withdraws, stays) to a non-reversal one.
6. **Clusters.** Linked pairs are joined with union-find. Identical publisher URLs are joined only when state and reversal status agree. This URL shortcut can span more than five days; it represents article identity, not proof that the article never changed.
7. **Representative.** The headline most similar on average to the rest of its cluster, skipping press-release wires, with ties to established outlets and then the earliest. The record ID is the state code, the earliest date, and a hash of the earliest headline, so it does not change when the representative does.

Measured results and the errors the review found are in the README.

## 6. Page reading (`enrich.py`)

For the representative article: resolve the Google redirect to the publisher URL, fetch the page, and extract the description, a lead of at most 600 characters, and the page date with trafilatura. If the page is blocked, the next-ranked article in the cluster is tried, up to three. The summary is the publisher's description, or the article lead, cut at a sentence end within 240 characters, with datelines ("BENGALURU:") removed. If neither adds anything beyond the headline, the headline is used and `summary_basis` says so.

## 7. Classification (`taxonomy.py`)

Category and stage use the headline. Sector first checks the headline, then the description. Government level combines relevance-stage central attribution with headline rules.

- **Category.** First match in this order: Regulation and ethics, Policy and strategy, Funding and budget, Institutions and bodies, Infrastructure and investment, Partnerships and MoUs, Skilling and education. Anything else is Government deployment.
- **Stage.** The cue word that comes first in the headline decides: signed, approved, launched or announced. "Maharashtra to launch ..." is announced; "Assam signs MoUs to bring ..." is signed. A reversal word anywhere gives reversed.
- **Government level.** Central when the central government is the actor (rule 10 above); High Court gives judiciary; municipal, district or city bodies give local; otherwise state.

## 8. Review (`data/review/overrides.csv`)

A CSV of decisions keyed by record ID: drop a record, or correct a field. The build applies it after classification and warns about any decision that no longer matches a record. Dropped records move to `rejected.csv` with the reviewer's reason.

## 9. Assumptions and limits

- **English only.** No Hindi or regional-language reporting. This matters most for Uttar Pradesh, Bihar, Madhya Pradesh and Rajasthan, and partly explains their lower counts.
- **News, not documents.** Steps recorded only in official documents are missed (see the coverage check).
- **Headline-driven.** Relevance, category and stage are read from the headline. A relevant article whose headline names no state is dropped. Leader names ("Naidu", "Revanth") are not mapped to states.
- **GDELT is mostly missing** and the keyed news APIs are untested (see Sources).
- **Counts are reported activity, not policy quality.** A state with a larger English press shows more records.
- **"Government deployment" is the default category** and holds 317 of 716 records. Some belong elsewhere.
- **Stage is a headline cue.** "Announced" includes some loosely worded intentions.
- **Assistant screening.** The saved dedup labels and review decisions were assistant-produced from headlines. They were not independently human-adjudicated. The explicit historical-ID list prevents newly collected records from inheriting this status merely because their date is after 2025.
- **Late duplicates.** Reports more than five days apart are not merged automatically.
- **Google News RSS is unofficial** and its redirect links are decoded with a third-party library that depends on Google's page format.
- **The optional LLM check step (`pipeline/llm.py`) has not been run.**

## 10. Date and identity limits

Numeric dates such as 03/04/2026 are read day first. That is an assumption, not disambiguating evidence. A naive timestamp is assumed to be UTC. Two-digit years 00 to 69 map to 2000 to 2069; 70 to 99 map to 1970 to 1999. Fuzzy month matching uses a similarity cutoff of 0.8 for words of at least five letters. Preserve the raw source when investigating a difficult date.

Relative-hour phrases use the supplied reference day, so they can be wrong across midnight. Week phrases use a coarse month approximation and do not correctly distinguish every number of weeks. Use only dated source timestamps for the published timeline. These loose-date paths were not used for the released records, whose feed timestamps all parse at day precision. An unknown date is retained in the rejection log rather than assigned the collection date.

A record ID is stable only while its state, earliest report date and earliest headline seed remain stable. A new earlier report or a split cluster can change identity. The final correction logs the two new IDs and confirms that none of the previous IDs disappeared. The SQLite file is an export, not a persistent observation ledger.

## 11. Source relationships and review provenance

Every main record has one representative report and at least one source-table row. All 716 representative links are direct publisher links. The source table preserves discovery URLs; 1,206 of its 1,306 links remain Google News redirects. It would be incorrect to describe every source link as resolved. Distinct outlet names can also refer to the same publisher or syndicated report, so n_outlets is not a count of independent corroborations.

The historical screening flag uses data/review/legacy_screening_ids.json, a list of 545 IDs from the previous release. It is labelled legacy_headline_screen to avoid implying human article verification. Other rows use auto. Saved field overrides use override_applied if present. An assistant made the original screening decisions and pair labels. No article-level verification claim follows from these labels.

The optional model stage is disabled in offline mode. Its configured model and API contract have not been live-tested in this project. Do not enable it merely to reproduce the dataset.

## 12. Interpretation and reproducibility

The published charts count records by report date. They do not estimate state policy quality, spending or programme benefit. The 2026 period ends on 10 November. Older indexing is less complete and review coverage differs across periods, so the rise in counts cannot be attributed solely to growth in policy activity.

Run python -m scripts.validate_release after building. The checks cover required values, unique IDs, dates, sort order, source relationships, the review-label vocabulary and dashboard consistency. scripts.eval_dedupe prints a development diagnostic and the overlap between its halves. It is not a held-out accuracy estimate. The separate 85-event reference appendix is not merged into this release because its event dates and inclusion rules differ.
