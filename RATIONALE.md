# Rationale

The same government announcement can appear in several outlets, while a later cancellation looks almost identical to the original report. I wanted a tracker that preserves that distinction. Each record keeps its source reports, and the method explains why reports were grouped or excluded.

I used Google News RSS as the main discovery source because it is free and supports state and date queries. Four query shapes cover government actors, policy instruments, public services, and infrastructure or rules. Queries run by state and month; raw responses are cached so the release can be rebuilt without paid access. GDELT and Bing provide some additional coverage, but GDELT is incomplete. The keyed news adapters were not live-tested, so I have not counted them as proven redundancy.

The initial sweep used a common query across all 28 states. I used discovery volume and geographical spread to choose the working set, then added Andhra Pradesh, Madhya Pradesh and Rajasthan for comparison with a separate reference collection. The final thirteen are Andhra Pradesh, Assam, Bihar, Gujarat, Karnataka, Kerala, Madhya Pradesh, Maharashtra, Odisha, Rajasthan, Tamil Nadu, Telangana and Uttar Pradesh. This is a selected sample. Lower English-news coverage can hide activity.

The pipeline reads the state from the report, not the query. It handles aliases, common spelling errors and abbreviations that need context. Feed timestamps are converted to India time. Missing dates stay in the rejection log; approximate inputs retain their precision. The record date is the earliest news report, not a verified government-action date.

Duplicate matching compares same-state headlines within five days, gives rare shared terms more weight, and keeps a reversal separate from the action it reverses. Every contributing report remains available. The final checks repaired two incorrect merges, bringing the release to 716 records with 1,306 report links.

I kept the dashboard focused on filters, timelines and source links so a reader can move from a pattern to the underlying reports. Charts describe this collection, not policy quality or successful deployment. Earlier screening and pair labels were assistant-produced from headlines, not independent human article checks. The next useful work is to connect announcements to orders, contract awards, spending and use. More headlines alone will not establish implementation.
