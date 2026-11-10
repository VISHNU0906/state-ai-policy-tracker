# Rationale

I wanted a tracker where a reader could follow a record back to the report and understand why it was included. The difficult part is deciding whether several headlines describe one action, and whether that action is a proposal, an agreement, an approval or a service already in use.

I kept news discovery and event records separate. Google News RSS supplies most of the material because it is free and can be queried by state and month. Four query shapes cover government actors, policy instruments, public services, and infrastructure or rules. Raw responses stay in the repository so the release can be rebuilt. Bing adds recent reports. GDELT was tried but much of the collection failed or was skipped. The keyed news adapters are present but were not tested with live credentials.

The selection covers thirteen states. The original count sweep compared all twenty-eight states, then used geographical coverage as a constraint. Andhra Pradesh, Madhya Pradesh and Rajasthan were added for comparison with a separately assembled reference list. This gives useful variation in administrative approaches. It does not produce a representative sample of India.

The pipeline reads the state from the headline, falling back to the description. It handles aliases and context-sensitive abbreviations. Dates are stored in ISO format with precision, and an undated item stays in the rejection log. The main date is the earliest report date, not a verified date of government action.

Deduplication compares reports from the same state within five days, gives rare shared words more weight, and preserves every contributing report. A cancellation must remain separate from the agreement it reverses. The final checks found and repaired a broken cancellation rule, separating two records that had been merged. The release now contains 716 records and 1,306 report links.

I kept the dashboard simple: state, time, category and stage filters, charts, and source links. The full dataset, rejection reasons and method are available separately. The most important limitation is the review boundary. Earlier screening and pair labels were produced by an assistant from headlines. They are not independent human verification. The next useful step is to check official orders, tenders and budgets, then connect announcements to evidence of implementation. More headlines alone will not resolve that gap.
