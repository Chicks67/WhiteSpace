# Progress (Oct 31, 2026)

## Product

Whitespace is the project: a site-selection agent for independent restaurant founders in New York City, live at
https://whitespace-nyc.vercel.app. A founder describes a concept and customers; the agent scouts vacant storefronts,
ranks them on city records, sizes up every rival with Qloo, writes a positioning brief, and answers follow-ups.
Finished runs play back with no API calls. Live runs use GPT-6 Astra through Kie.

## Results behind the product

- Closing-time check: asked when 30 real NYC restaurants close on Friday, GPT-6 Astra was right 0 times alone and
  29 times with Qloo's record; Gemini 3.8 Flash 3 and 29.
- Hours and prices: Qloo's Friday closing times match Google Maps for 29 of 30 places; price levels for 25 of 27.
- Competitor coverage: Qloo finds 92.4% of real competitors.
- Briefs: written with Qloo, preferred 78% of the time by human raters and 76% by a blind judge.
- Lease score: AUC 0.893 with Qloo against 0.851 from city records alone (0.887 across 25 cuisines).
- Cuisine heatmaps 0.812 against 0.742 for restaurant count; storefront cuisine +0.087 AUC over city records.

## Where Qloo did not move the number

- Survival: Qloo taste added +0.013, a placebo +0.016; no survival claim is made.
- Audience tags: 2 of 7 matched the census, so demographics come from the census.
- Brief from place records: the registered rule was not met.
- Restaurant scene: specific to each restaurant but not validated, so it never chooses where to open.

Full table: README "What we tested", and on the site under Results and How we know.

## Open

- Shared rate limits: run `vercel integration add upstash`, then redeploy; the code switches on by itself.
- One live test run on the site, to confirm the Kie key has credit.
