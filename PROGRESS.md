# Progress (Oct 31, 2026)

## Product

Whitespace, a site-selection agent for independent restaurant founders in NYC, is built and runs locally
(README "Quick start"). Saved runs replay with no API calls. The hackathon entry since Oct 28 is Clash Court
(../clash-court), which uses Test 28.

## What holds up

- Qloo plus a model answers facts about specific real places: Friday closing times 29 of 30 with Qloo, 0 to 3 of 30
  without (Test 20); Qloo's closing times match Google Maps 29 of 30 (Test 12).
- Qloo taste beats popularity on music audiences (Tests 14, 15, 27, 28), but a model alone does as well or better.

## What does not

- Qloo does not help decide where a cuisine opens or which opens (Tests 1, 2, 4, 5, 7).
- Qloo-backed briefs lost to briefs from city records (Test 8: 0.20) and were not confirmed better in Test 9.
- Qloo's competitor lists are incomplete (Test 10: 37.2%); price levels failed the bar (Test 12: 17 of 27).

Full table of all tests: README "What we tested" and PROJECT_LOG.md.

## External results

A Kaggle results table (Oct 31) is in KAGGLE_RESULTS.md, row by row against this repository. 14 rows match;
9 contradict the recorded tests (the recorded results stand); 6 have no matching test and are unverified.

## Open

Test 3 not run (no outside raters). Team decision on what the shipped brief is written from. Deploy and push.
