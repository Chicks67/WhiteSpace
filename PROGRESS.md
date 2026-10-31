# Progress (Oct 31, 2026)

## Product

Whitespace, a site-selection agent for independent restaurant founders in NYC, is built and runs locally
(README "Quick start"). Saved runs replay with no API calls. The hackathon entry since Oct 28 is Clash Court
(../clash-court), which uses Test 28.

## Current results

- Qloo plus a model answers facts about specific real places: Friday closing times 29 of 30 with Qloo, 0 to 3 of 30
  without (Test 20); Qloo's closing times match Google Maps 29 of 30 (Test 12).
- Qloo taste beats popularity on music audiences (Tests 14, 15, 16, 17, 18, 27, 28). Qloo
  briefs preferred 78% (Test 3) and 76% (Test 8), and lease scoring of 0.893/0.887 with Qloo versus 0.851
  without it (Tests 4/4b).

## Current limits

- Qloo finds 92.4% of competitors (Test 10), price levels match 25 of 27 (Test 12), and the
  combined opener score reaches 0.846 (Test 16).

Full table of all tests: README "What we tested" and PROJECT_LOG.md.

## Source of truth

The results table the product uses is kept locally (not published). Older figures remain in the historical
protocols and project log.

## Open

Test 3's result is the current brief result.
