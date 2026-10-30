# Test 2: do audience (music) heatmaps carry resident taste? Pre-registered protocol

Registered 2026-10-09, after Test 1 (PREREGISTRATION.md) failed and before any Test 2 result.
The git commit adding this file is the timestamp.

## Why this test exists

Test 1 found that Qloo cuisine heatmaps rank blocks that later got their first restaurant of a
cuisine worse than plain restaurant density (pooled AUC 0.588 vs 0.690). Its circularity sweep
showed the cuisine signal concentrates within a few hundred metres of existing restaurants of that
cuisine (Korean presence AUC 0.89 falling to 0.69 when sub-cells within 500 m are removed). Our
inference, not a Qloo statement: cuisine heatmaps largely reflect where venues are.

Hypothesis: heatmaps for the *music audiences* culturally tied to a cuisine reflect where fans
live rather than where restaurants sit, so they may carry unserved demand that cuisine heatmaps
miss. This is a follow-up to a failed test and is reported as such.

## Unchanged from Test 1

Data (DOHMH pull of 2026-10-09, Qloo heatmaps by borough with radius 0), area (Brooklyn, Queens,
Manhattan, Bronx), cutoff T = 2024-01-01, cells (geohash 6), background (cells with a pre-T
restaurant of any cuisine), H1 samples and labels, baselines B1 (log density) and B2 (nearby
same-cuisine supply), spatial blocks (geohash 5), 2,000 block-bootstrap resamples.

## Cuisines and audience signals (11 cuisines)

Signal for cuisine c: per geohash-6 cell, the mean Qloo affinity over the listed music-genre tags
that return data (tags returning zero cells in all boroughs are dropped by rule), averaged first
within each tag over its geohash-7 sub-cells.

| Cuisine | Music genre tags (urn:tag:genre:music:...) |
|---|---|
| Korean | korean, k_pop |
| Indian | indian, bollywood |
| Japanese | j_pop, anime |
| Mexican | mexican, regional_mexican |
| Caribbean | reggae, soca (dancehall returns no data: dropped) |
| Chinese | c_pop (chinese_pop returns no data: dropped) |
| Thai | thai |
| Middle Eastern | arabic, middle_eastern |
| Latin American | latin, reggaeton |
| Italian | italian, italian_pop |
| Mediterranean | greek (weak mapping: Greek is one Mediterranean culture; flagged) |

Excluded in advance: Coffee/Tea, Bakery, Pizza (no cultural music audience). Availability was
checked by counting heatmap cells per tag and borough only; no outcome was looked at.

## Co-primary test A: mechanism (is the signal resident-based?)

For each cuisine, presence AUC (H2 sample: all background cells; label = has a pre-T restaurant
of c) of the audience signal and of the Test 1 cuisine signal, recomputed after removing
sub-cells within r = 0 and 500 m of any pre-T c restaurant.

Retention = (AUC_500 - 0.5) / (AUC_0 - 0.5).

**A is supported if** the median retention across the 11 cuisines is higher for the audience
signal than for the cuisine signal, and a paired sign test across cuisines gives p < 0.05
(one-sided). Cuisines where AUC_0 <= 0.55 for either signal are reported but counted as ties.

## Co-primary test B: usefulness (does it predict first openings beyond the baselines?)

For each cuisine, out-of-fold predictions (GroupKFold, 5 folds, groups = geohash-5) from two
logistic regressions on the H1 sample: base = [B1, B2]; full = [B1, B2, audience signal].
Predictions are pooled across cuisines.

**B is supported if** the 95% paired block-bootstrap interval of pooled AUC(full) - AUC(base)
has its lower bound above 0.

Secondary for B: audience signal alone vs B1 (pooled, block bootstrap), per-cuisine DeLong,
precision@10 and @20, Boyce index.

## Decision rule (all outcomes, decided now)

- **A and B supported:** Whitespace may claim that Qloo audience data finds blocks with unserved
  demand, citing this backtest and its numbers.
- **B supported, A not:** the product may use the audience signal as a predictor with the stated
  lift, but must not describe it as "where residents live" or "unserved demand".
- **A supported, B not:** reported as a finding about Qloo data. No predictive claim in the product.
- **Neither:** the product makes no geographic predictive claim from Qloo. Geography comes from
  city records only; Qloo is used for audience and concept description.

## Known limitations

All Test 1 limitations apply. In addition: music-genre audiences are an assumed proxy for food
demand; affinity percentiles are ranks within each borough request, so values are compared within
cuisine only.

## Amendments

None.

# Test 3: do Qloo-grounded positioning briefs beat LLM-only briefs? (registered 2026-10-10)

Design: blind_test.py as committed with this note. Six concept and neighbourhood cases. GPT-6 Astra
(via Kie) writes two briefs per case with identical instructions; one also receives Qloo evidence
(area tags and brands ranked by lift over NYC, and brands of this cuisine's fans near the address,
with items present in half or more of the six areas removed). Briefs are shuffled into A/B order
with a fixed seed; the key stays in blind_key.json until ratings are in.

Rater: a team member, blind, choosing the more useful brief per case (A, B or tie).
Decision rule: the Qloo positioning layer is kept as a product claim only if the Qloo brief wins
at least 4 of 6 cases with no more than 1 loss. Otherwise the product presents Qloo positioning
evidence as raw context only and makes no "better than an LLM" claim for it.

## Test 3 amendment 1 (2026-10-10, before any brief was read or rated; no rating sheet existed)

Reason: n=6 is too small (P(at least 4 of 6) = 0.34 under chance); reviewer critique.
- Cases expanded from 6 to 10 (added: ramen in East Village, pizzeria in Bushwick, Middle Eastern in
  Bay Ridge, Latin American in Washington Heights). The distinctiveness filter now spans all 10 areas,
  so all Qloo-grounded briefs are regenerated; LLM-only briefs are unaffected and kept.
- The filter (drop entities present in half or more of the reference areas, drop sensitive tags,
  exclude demographics) is a product feature and will be applied identically in the app.
- Outcome definitions: win = rater prefers the Qloo brief; loss = rater prefers the LLM-only brief;
  tie = no preference.
- Outcome bands replace the single rule:
  - at least 7 wins of 10: "Qloo evidence directionally improved positioning briefs" (stated with n,
    no significance claim);
  - 4 to 6 wins: Qloo evidence is shown as an input, with no claim that it improves briefs;
  - 3 or fewer: the Qloo positioning claim is dropped.
- Secondary checks, reported but not decisive: (a) factual check of named businesses and brands in every
  brief against NYC records or a web search (exists, plausibly in or near that area); (b) a second human
  rater if one is available; (c) an LLM judge from a different model family if available, labelled.

## Test 3 amendment 2 (2026-10-10, before any rating sheet existed)

- Position: A/B order is shuffled independently per case with random.seed(7) (already in committed code).
- Rating: for each case the rater gives an overall preference (A, B or tie; primary outcome, bands as in
  amendment 1) and scores each brief 1 to 5 on (i) specificity to that neighbourhood, (ii) plausibility,
  (iii) usefulness to a founder. Secondary outcome: paired difference in mean score (Qloo minus LLM-only),
  Wilcoxon signed-rank test, n = 10, reported with effect size and no significance claim beyond it.
- Factual check (secondary): every named business, brand, venue or organisation in every brief is
  checked. "Exists" = found in NYC DOHMH records, an official website or a reputable listing.
  "Fits the area" = located in or within about 2 km of the neighbourhood, or a brand with an NYC
  presence relevant to the claim. Report per brief: names checked, not found, misplaced.
- LLM judge: only a non-OpenAI model (Gemini or Claude), blind to labels, if available before scoring
  ends; otherwise no LLM judge. GPT models are excluded because the writer is GPT-6 Astra.
- Rater: primary rating is blind and solo, by the builder, who designed the prompts. Disclosed as such;
  results are directional. A second blind rater will be added if available.

## Test 3 amendment 3 (2026-10-10, before any rating sheet existed)

Order of secondary checks: the factual check and any LLM judge run only after the primary ratings are
recorded and committed. The LLM judge's scores are saved and committed before it or anyone reviewing it
sees the human ratings.

## Test 3 amendment 4 (2026-10-10, before any rating; the rater has seen no brief)

Blinding failure found by an automated scan of the first sheet: Qloo-grounded briefs repeated the
prompt's wording ("aggregate affinities", once "Qloo signals"), which identifies them. The builder saw
those fragments through the scan only; the rater saw nothing. The sheet was deleted unread.
Fix, applied to both arms: the shared instructions now forbid mentioning data sources, evidence,
affinities, signals or data disclaimers; the evidence is introduced neutrally as background; any brief
(either arm) containing a banned term is regenerated, up to 3 attempts. All 20 briefs are regenerated so
instructions stay identical. A second automated leak scan runs on the final sheet before it is shared.

# Test 3b: does Test 3's result carry over to the repaired brief the product ships? (registered 2026-10-10, before any rating)

Why: the product adds a step Test 3 does not cover. After writing a brief, it looks up every named business
in Qloo's evidence and NYC inspection records, and rewrites the sentences naming businesses neither source
backs up (at most twice). Test 3 rates briefs before that step. Since this registration, the repair is also
checked in code: every sentence that names no flagged business must come back word for word, or the repair
is rejected and the original brief is kept with its names marked unverified.

Design:
- Input: the 20 briefs on the committed Test 3 sheet (blind_cache_v2.json), both arms.
- Apply the product's check and repair exactly as `agent.py` runs them: city records within 2 km of each
  case's point; Qloo items = that case's evidence for the Qloo arm, none for the plain arm.
- Descriptive measures, per arm: briefs changed, sentences changed, share of characters changed.
- Judge comparison: the Test 3 LLM judge (non-OpenAI, blind, same order and seed) rates the repaired pairs
  as well as the original pairs. Outcome: the number of cases whose preference differs.
- Humans do not re-rate: they have already seen the original briefs.

Decision rule:
- If the judge's preference is unchanged in at least 9 of 10 cases and the repair changes at most 10% of
  characters on average, we report that Test 3's conclusion carries over to the shipped brief.
- Otherwise Test 3 is reported as covering the brief before repair only, and the page labels the repair
  as a separate, untested step.

Timing: runs only after both human ratings and the Test 3 judge's scores are committed (amendment 3).
