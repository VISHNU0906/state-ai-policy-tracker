# Source options and collection priorities

Checked against provider documentation on 11 November 2026. The comparisons below separate discovery from page extraction. A scraper can read a known URL; it does not by itself provide a comprehensive news index.

## What I would keep free

Use the existing cached Google News RSS collector for broad news discovery and targeted government-site checks for formal instruments. Fetch accessible publisher pages locally with requests and trafilatura. Retain the original URL, publication timestamp, query, source and fetch outcome before classification. Failed requests must remain visible, including requests returning no usable text.

RSS is a structured feed containing items such as titles, links, dates and descriptions. Google News RSS is an unofficial discovery interface, not an archive with a completeness guarantee. Publisher RSS feeds can reduce dependence on Google, but each covers only that publisher's recent feed. A future official-source collector should monitor named Gazette, budget, tender and departmental pages, with document hashes and changed-file checks. That collector is proposed, not implemented here.

The current collection found important gaps in GDELT coverage. Keep it as an independent candidate source, with paced requests and explicit failure logs. Do not label missing responses as zero activity. The SQLite output in this repository is a release export; it does not preserve a durable history of failed requests across scheduled runs.

## Optional services

| Service | Role | Verified access constraints | Status in this repository |
|---|---|---|---|
| NewsAPI | News discovery | Free Developer plan: 100 requests/day, one month of history, 24-hour delay; intended for development and testing | Adapter written, not live-tested |
| GNews.io | News discovery | Free plan: 100 requests/day, ten articles/request, 30-day history, 12-hour delay, non-commercial use. Paid plans advertise a ten-day trial and history since 2020 | Adapter written, not live-tested |
| Tavily | Web discovery and extraction | Documentation lists 1,000 free credits/month; pay-as-you-go is separately billable | Extraction fallback only; not used in the original run |
| Exa | Search with retrieved contents | Search and contents endpoints are documented; account limits must be checked before a benchmark | Not integrated |
| Firecrawl | Scrape, crawl, map and search | Cloud and self-hosting options are documented. Self-hosting still consumes compute and requires maintenance | Not integrated |
| NewsData.io | Additional news discovery | Recheck current account plan and history limits before enabling | Adapter written, not live-tested |
| Crustdata | Candidate additional source | No current plan or relevance benchmark verified in this release | Not integrated; no reliability claim |

Sources: [NewsAPI pricing](https://newsapi.org/pricing), [GNews pricing](https://gnews.io/pricing), [Tavily credits](https://docs.tavily.com/documentation/api-credits), [Exa search](https://exa.ai/docs/reference/search), [Firecrawl documentation](https://docs.firecrawl.dev/introduction).

## How I would decide whether another provider is useful

Run the same state, date and topic query set through each candidate provider. Keep raw responses and request costs. Review a stratified sample including low-volume states, formal rules, budget lines, duplicates and reversals. Measure unique relevant actions added after deduplication, source-date availability, direct-link resolution, missing fields, failure rate and cost per accepted action. Treat a provider's own relevance score as an input, not a review decision.

Use the same event definitions across providers. An agreement and its later cancellation are separate actions; ten syndicated copies of one announcement are one event with ten source observations. Compare errors at both article and event level. Keep tuning and evaluation events disjoint, including paraphrases and syndicated stories.

I would spend optional trial credits on known gaps and failed extraction, with a fixed request cap and no automatic paid overage. I would not run every provider on every query. No trials, paid plans or new keys were activated for this release. Adding a key to the environment does not establish that the adapter works or that the plan permits the intended scheduled use.

## Next implementation priorities

1. Add a persistent request and observation store so failures and query coverage survive artifact expiry.
2. Add explicit state/date evidence fields and abstention for ambiguous matches.
3. Replace inherited screening flags with decisions tied to a source, reviewer, timestamp and reason.
4. Resolve contributing-report redirects separately from representative links.
5. Evaluate clustering on disjoint event groups and inspect long transitive chains.
6. Monitor official documents and link approval, publication, procurement and execution as related milestones.

These are proposed improvements. The release implements cached collection, rule-based normalisation, guarded clustering, saved exclusions, export checks and a weekly review artifact. It does not claim the full proposed system is already built.
