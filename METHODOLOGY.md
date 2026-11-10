# Methodology

How each field in the dataset is produced, in the order the pipeline runs. File names refer to `pipeline/`.

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

Every response is written to `data/raw/` keyed by a hash of the query. With `PIPELINE_OFFLINE=1` the collector reads only that cache, so the committed dataset can be rebuilt with no network and no drift. A source that fails is logged in `collect_log.json` and skipped; it never stops the run.

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
| 10 | Not a central government action, unless the state is the subject | `central_government_actor` |
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
5. **Link rule.** Link when similarity >= 0.25 + 0.08 x (days apart - 1). Never link a reversal headline (cancels, scraps, withdraws, stays) to a non-reversal one.
6. **Clusters.** Linked pairs are joined with union-find. Identical publisher URLs are always joined.
7. **Representative.** The headline most similar on average to the rest of its cluster, skipping press-release wires, with ties to established outlets and then the earliest. The record ID is the state code, the earliest date, and a hash of the earliest headline, so it does not change when the representative does.

Measured results and the errors the review found are in the README.

## 6. Page reading (`enrich.py`)

For the representative article: resolve the Google redirect to the publisher URL, fetch the page, and extract the description, a lead of at most 600 characters, and the page date with trafilatura. If the page is blocked, the next-ranked article in the cluster is tried, up to three. The summary is the publisher's description, or the article lead, cut at a sentence end within 240 characters, with datelines ("BENGALURU:") removed. If neither adds anything beyond the headline, the headline is used and `summary_basis` says so.

## 7. Classification (`taxonomy.py`)

All three are read from the headline with ordered keyword rules.

- **Category.** First match in this order: Regulation and ethics, Policy and strategy, Funding and budget, Institutions and bodies, Infrastructure and investment, Partnerships and MoUs, Skilling and education. Anything else is Government deployment.
- **Stage.** The cue word that comes first in the headline decides: signed, approved, launched or announced. "Maharashtra to launch ..." is announced; "Assam signs MoUs to bring ..." is signed. A reversal word anywhere gives reversed.
- **Government level.** High Court gives judiciary; municipal, district or city bodies give local; otherwise state.

## 8. Review (`data/review/overrides.csv`)

A CSV of decisions keyed by record ID: drop a record, or correct a field. The build applies it after classification and warns about any decision that no longer matches a record. Dropped records move to `rejected.csv` with the reviewer's reason.
