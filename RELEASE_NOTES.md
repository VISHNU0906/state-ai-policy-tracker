# Release notes

## Corrective release on 11 November 2026

The collection cutoff remains 10 November 2026. This release uses the same news pool as commit `1796505cc0e0ba7d1f865d373d71f4f116a78901`.

- Repaired literal backspace characters in the reversal regular expression. Added tests for six reversal verbs, both with and without a shared URL.
- Prevented identical URLs from bypassing state and reversal checks.
- Separated `UP-2026-03-27-69d6e4` and `KL-2023-06-21-69af46` from their earlier clusters. The total changes from 714 to 716; none of the original record IDs disappears. The source-report total stays at 1,306. Both new representative URLs were resolved and fetched.
- Corrected the stage matcher to recognise the bare verb halt. The Kerala payment direction is now reversed.
- Replaced the date-based blanket reviewed flag with 545 explicit historical screening IDs. These use `legacy_headline_screen`; 171 other records are `auto`. The historical flags were assistant-produced and do not establish human article verification.
- Made offline page-cache misses explicit and disabled optional model calls in offline mode. Missing pages no longer trigger accidental network access during a cached build.
- Added validation of required values, record IDs, source relationships, dates, sorting and dashboard consistency.
- Rewrote submission material to match the code and saved evidence. Removed claims that the user personally labelled pairs or checked every headline.
- Added a separate 85-event source-research appendix. It is not added to tracker totals.

The 97 tests pass. The pair diagnostic remains a development check: only 136 of 140 labelled pairs are present, 31 headlines cross the tuning/reporting split, and assistant labels have not been independently adjudicated. Reported precision 0.96 and recall 1.00 are not general accuracy estimates.

## What still needs work

The full corpus has not been checked against official documents. Headline-based relevance and stage can be wrong. The five-day comparison window misses late coverage; transitive matching can combine separate milestones. Numeric tokenisation truncates decimals. Relative-hour dates assume the reference day and week phrases use a coarse month approximation. The published rows use ISO feed timestamps, so these loose-date limitations did not supply their dates.

Source failures remain in the collection log. GNews.io, NewsAPI.org and NewsData.io have not been exercised with live credentials. Tavily extraction and the optional model step remain untested. The reference appendix preserves inherited research, with final access failures disclosed in the submission.
