# Whitespace: notes for Claude Code

Entry for the Qloo Agentic Hackathon (Devpost). The deadline was Oct 30, 2026, 11:45 PM ET and has been extended
(confirm the new date with the team). The live demo must stay up through judging. Team of two.

Whitespace is the whole project and the hackathon entry (Oct 31, 2026). The repository keeps only the tests behind
this product: restaurants, places and briefs. The music, film, sports and other research tests were removed.

## What it is

A site-selection agent for independent restaurant founders in NYC (Brooklyn, Queens, Manhattan, Bronx).
Main path (scout): a founder describes concept and customers; the agent picks neighbourhoods from census data,
finds vacant storefronts (NYC Storefront Registry), ranks them with a city-records lease score, checks
competition and foot traffic, shortlists, writes a positioning brief for the top pick from Qloo taste evidence,
lists local partners and next steps, and answers follow-ups with tools. Other paths: search an area, rank own
addresses.

Run locally (from this folder): `pip install -r requirements.txt`, `python build_data.py` (only if data/ is missing),
`uvicorn app:app --port 8000`. Saved runs replay with no API calls.

## Key files

- agent.py: the run (resolve concept, scout or area or addresses, rank, Qloo evidence, write, verify, repair).
- scout.py: scout tool loop and shortlist checks in code. followup.py: follow-up tools.
- engine.py: lease score, geocoding with street and borough validation, CONCEPTS (25 cuisines).
- storefronts.py, census.py, transit.py, bids.py, partners.py, next_steps.py: city data.
- positioning.py: Qloo evidence, brief name check, repair and drop fallback. llm.py: providers (comet, kie),
  hedged requests, budget and busy detection. qloo.py: cached Qloo client with monthly quota guard.
- evidence.py: the "How we know" panel. static/: the page.
- eval_suite.py, PROBES.md: reliability tests. PREREGISTRATION*.md + backtest*.py + test8.py: the tests.
- PROJECT_LOG.md: full history of decisions and results.
- llms.txt (static/), LICENSE (MIT).

## Rules (do not break)

- Keys live only in .env (git-ignored). Never commit, print or paste them. Scan diffs for keys before commits.
- Qloo data must not be in the public repo (Qloo Support: private server-side caching is fine; Qloo response
  data in a public repo is not). golden/ (saved runs), cache/ and test8_state.json are git-ignored. Public,
  redacted replays are in fixtures/replays (rebuild with `python redact_replays.py` after any re-record).
- Every test is pre-registered: write and commit the protocol before code or results; never change a decision
  rule after seeing data; record deviations honestly. Do not peek at results before the registered analysis.
- Do not create or use extra free accounts to get around provider limits.
- Writing style for user-facing text: no em or en dashes; plain words.

## Test status

The 13 tests behind the product, by the names the site and README use. Results come from the authoritative table in
KAGGLE_RESULTS.md (kept locally and git-ignored, never published; the site and docs give numbers without naming the run).

- Cuisine heatmaps (PREREGISTRATION.md): Qloo 0.812 against 0.742 for restaurant count.
- Brief, human raters (PREREGISTRATION_2.md, blind_test.py): Qloo briefs preferred 78%.
- Lease score (PREREGISTRATION_3.md): 0.893 with Qloo against 0.851; Lease score, 25 cuisines (PREREGISTRATION_6.md): 0.887.
- Survival (PREREGISTRATION_5.md): +0.013 against a placebo +0.016; no survival claim.
- Audience tags (PREREGISTRATION_4.md): 2 of 7 matched the census; demographics come from the census.
- Storefront cuisine (PREREGISTRATION_7.md): +0.087 AUC over city records.
- Brief, blind judge (PREREGISTRATION_8.md): 76% (0.68 to 0.83).
- Brief from place records (PREREGISTRATION_9.md): rule not met; Part B not run. Do not run more cases to chase it.
- Competitor coverage (PREREGISTRATION_10.md): Qloo finds 92.4%.
- Restaurant scene (PREREGISTRATION_11.md): specific, not validated; may be shown with that label, never chooses where to open.
- Hours and prices (PREREGISTRATION_12.md): closing times 29 of 30 (all 29 exact); price levels 25 of 27.
- Closing-time check (PREREGISTRATION_20.md, test20.py): GPT-6 Astra 0 of 30 alone, 29 with Qloo; Gemini 3.8 Flash 3 and 29.

## Pending

1. Optional, not needed: shared rate limits through Upstash (the marketplace has no free plan; a free database from
   console.upstash.com works by setting UPSTASH_REDIS_REST_URL and UPSTASH_REDIS_REST_TOKEN). The Vercel Firewall rule
   and per-instance limits already protect the paid endpoints.
2. Done Oct 31: a live run on Kie succeeded in production.
3. Real prices for the business calculator (now $299 per site report and $50 a month per listing, placeholders).
4. Real founder or broker feedback, and two outside raters for the brief.

The repository is public (github.com/Chicks67/WhiteSpace); the live site is https://whitespace-nyc.vercel.app.
Scan every diff for keys and for team members' names before pushing.
