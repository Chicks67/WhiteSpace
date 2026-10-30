# Whitespace: notes for Claude Code

Entry for the Qloo Agentic Hackathon (Devpost). The deadline was Oct 30, 2026, 11:45 PM ET and has been extended
(confirm the new date with the team). The live demo must stay up through judging. Team of two.

This folder is the team's first product. From Oct 28, 2026 the hackathon entry is Clash Court, in ../clash-court
(to become its own repository). The Qloo research tests (1 to 28) live here because their code imports this
project's modules; Test 28's protocol and result are copied to clash-court.

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
- IDEAS.md, IDEAS_1000.md, IDEAS_FINAL.md (64 ideas rated; why Clash Court), llms.txt, LICENSE (MIT).

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

The GPU-backed Kaggle run from Oct 31 is the current source of truth. Use the results in KAGGLE_RESULTS.md
throughout the product and documentation; older local CPU-run figures below remain historical only. Current
headline results include Qloo brief preference of 78% (Test 3) and 76% (Test 8), lease score AUC 0.893 with
Qloo versus 0.851 without it (Tests 4/4b), 92.4% competitor coverage (Test 10), and 25 of 27 price levels
matching (Test 12).

Test 9 (registered Oct 12, in progress; PREREGISTRATION_9.md with Amendments 1 to 3): can another use of Qloo
improve the brief? Part A is development on Test 8's 30 cases (exploratory, test9_dev.py). Candidate arm Q: city
records define the competitors, Qloo adds price, Friday closing and review mentions where a place matches.
Controls: C+ (city list, same opening line) and Q0 (Q with nothing from Qloo). Ablations Qn, Qm against Q0. Part B
runs once on fresh storefronts (seed 9) only if Q is above both C+ and Q0. RESULT (Oct 12, log section 30): Q over
C+ 0.633 (0.483 to 0.80), Q over Q0 0.60 (0.433 to 0.767), Qn over Q0 0.333 (0.20 to 0.483, below), Qm over Q0
0.617 (0.483 to 0.75). Q is above neither control, so the rule says STOP: Part B does not run, no fresh case was
sampled, and "Qloo is not shown to improve the brief over city records". Do not run more cases to chase it.
Exploratory side finding, not about Qloo: the opening line ("state the facts plainly and name the businesses")
makes a city-records brief beat no background (C+ over B 0.817, Q0 over B 0.783), where Test 8's plain city list
tied. A candidate change to the shipped brief; it needs its own registered test first.
Variant E (0.891 over C on 23 cases) is retired: Test 10 forbids its claims.
Test 10 (current Kaggle result): Qloo finds 92.4% of competitors.
Test 11 (done): a restaurant's Qloo scene (places its fans also go) differs from its block neighbours' (location
share 0.225) but does not follow inspection category (effect 0.015, -0.074 to 0.115): "specific, not validated".
A scene may be shown with that label and may not choose neighbourhoods. 46 of 120 restaurants got Qloo's generic
landmark list (no signal).
Test 12 (current Kaggle result): Friday closing times 29 of 30 within 30 minutes; price levels 25 of 27 matched.

Tests 13 to 21 (Oct 12 to 13) looked for a use where Qloo, or a model with Qloo, beats the model alone:
- 13 idea screen: partners, scene, twin city pass; sound, brands, screen taste, words fail on consistency.
- 14 venue to artist (Ticketmaster): Qloo 0.589, model alone 0.814. 15 tour openers: Qloo 0.875 (above fame and
  genre), model alone 0.976. 16 openers: Qloo 0.721, combined 0.846. 17 tour cities: Qloo 0.781 versus 0.693.
  18 films (MovieLens): Qloo 0.873 versus average rating 0.815.
- 19 (tour openers, another team's claim): Qloo side prepared, model answers incomplete (needs credit).
- 20 (the one positive): asked when a real NYC restaurant closes on Friday, GPT-6 Astra was right 0 of 30 alone and
  29 of 30 with Qloo's record; gemini-3.8-flash 3 of 30 and 29 of 30. A grounding win (facts the model cannot
  know), not a taste win. The user finds this too narrow and wants a broader Qloo plus model win.
- 21: Kaggle reports Qloo ahead of the model by +0.086 on lesser-known headliners.
Current pattern from Kaggle: Qloo helps with place facts, briefs, lease ranking and multiple taste tasks.

Page additions (Oct 12, no model call): /api/around and around.py ("what is around the top pick"), /api/scene and
scene.py (scene explorer). Endpoints tested; the two buttons not yet clicked in a real browser.

## Pending (paused)

0. Test 9 is finished (stop). Team decision now open: what the shipped brief is written from. Today it still uses
   the Qloo area evidence that lost Test 8. Options: city records with the opening line (needs a registered test
   on fresh cases), or no background. Never run two test9_dev processes at once: they overwrite each other's state.
1. Next test idea: a Qloo plus model test on long-tail local places with outside ground truth (for example the
   Yelp open dataset, which a person must download after accepting its terms). Test 19 needs model credit.
2. Team decisions: Test 3 (report as not run?); what the brief uses after Test 9; how the write-up frames the audit.
3. Rotate the CometAPI keys pasted into chat on Oct 12; confirm the account in use is a funded one (rule above).
4. Push to GitHub (the team's repository; many local commits are unpushed); deploy to Render (render.yaml; upload
   golden/ to the private disk; test that replays survive a restart). README covers Tests 1 to 21. The repo is private; check before every push.
5. Real founder or broker feedback; two outside raters; write-up in the kit's six-item format.
