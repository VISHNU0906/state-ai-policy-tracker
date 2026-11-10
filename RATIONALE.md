# Rationale

The same government announcement shows up in many outlets, and a cancellation a few days later reads almost like the original. I wanted a tracker that counts policies, keeps a cancellation apart from the step it cancels, and lets anyone check how each number was reached. Every policy keeps the news reports behind it. Every dropped item keeps its reason.

**Sources.** I used Google News RSS as the main source because it is free, needs no key and can be searched by state and by month. For each state and month I ran four searches: the government itself, policy instruments, public services, and infrastructure and rules. That came to 3,068 searches, and every response is saved so the dataset can be rebuilt offline. GDELT and Bing added a little. GDELT was rate limited on most calls, so I treat it as incomplete. I wrote code for three paid news APIs but never ran it with a key, so I do not count them.

**States.** I ran one common search across all 28 states and picked the working set from how much came back and how the states are spread across the country. I added Andhra Pradesh, Madhya Pradesh and Rajasthan to compare against a separate list built from official documents. The thirteen are Andhra Pradesh, Assam, Bihar, Gujarat, Karnataka, Kerala, Madhya Pradesh, Maharashtra, Odisha, Rajasthan, Tamil Nadu, Telangana and Uttar Pradesh. I searched English news only, so a low count can simply mean a state's news is in another language.

**Collecting and cleaning.** The state is read from the headline, never from the search. The list of names covers spellings like UP and Uttar-Pradesh, common misspellings, and short forms like MP that count only next to a government word. Dates are converted to India time, and an item with no date is dropped, never filled in. Duplicates are matched within a state and within five days, with rare shared words weighing more. A cancellation never merges with the original. The final check found two such wrong merges, and fixing them took the total from 714 to 716 policies, with 1,306 news reports behind them.

**Presentation.** I kept the dashboard simple: big numbers and a growth chart first, then filters and the list, with every policy linked to its news reports. The charts show what was reported. They cannot tell me whether a policy was delivered.

**What is weak.** The headline screening and the duplicate labels were done with an AI assistant, and I have not read every article. The next thing I would do is link each announcement to an order, a tender or a budget line.
