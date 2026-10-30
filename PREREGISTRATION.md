# Whitespace backtest: pre-registered protocol

Registered 2026-10-09, before any backtest result was computed. The git commit that adds this
file is the timestamp. Any later change to this file is listed under "Amendments" with its reason.

## Question

Whitespace claims that Qloo's taste data can point a founder to blocks where a cuisine is
missing but locals' taste for it is high. The test of that claim: **among NYC blocks that had
restaurants but no place of cuisine c before 1 Jan 2024, does Qloo taste rank the blocks that
later got their first c restaurant above the blocks that did not?**

## Data

- **Supply and openings:** NYC DOHMH restaurant inspection results (Socrata `43nn-pn8j`), pulled
  2026-10-09. One row per restaurant (CAMIS) with cuisine and coordinates. Opening date = earliest
  "Pre-permit (Operational)" inspection. A restaurant with no pre-permit inspection on record is
  treated as existing before the cutoff.
- **Taste:** Qloo `urn:heatmap` for each cuisine tag, one request per borough
  (`filter.location.query` = borough, `filter.location.radius` = 0), pulled once and cached.
- **Area:** Brooklyn, Queens, Manhattan, Bronx. Staten Island excluded (too few restaurants).
- **Cutoff T:** 2024-01-01. Outcome window: T to 2026-10-09.

## Cuisines (14) and Qloo tags

| DOHMH label | Qloo tag |
|---|---|
| Korean | urn:tag:genre:place:restaurant:korean |
| Mexican | urn:tag:genre:place:restaurant:mexican |
| Japanese | urn:tag:genre:place:restaurant:japanese |
| Thai | urn:tag:genre:place:restaurant:thai |
| Indian | urn:tag:genre:place:restaurant:indian |
| Caribbean | urn:tag:genre:place:restaurant:caribbean |
| Coffee/Tea | urn:tag:genre:place:restaurant:coffee_shop (amended, see below) |
| Bakery Products/Desserts | urn:tag:genre:place:restaurant:bakery |
| Chinese | urn:tag:genre:place:restaurant:chinese |
| Pizza | urn:tag:genre:place:restaurant:pizza |
| Italian | urn:tag:genre:place:restaurant:italian |
| Mediterranean | urn:tag:genre:place:restaurant:mediterranean |
| Latin American | urn:tag:genre:place:restaurant:latin_american |
| Middle Eastern | urn:tag:genre:place:restaurant:middle_eastern |

Excluded: Vegan (DOHMH label unreliable: 11 in Queens vs 33 in Qloo); Spanish (DOHMH uses it for
many Dominican and Latin American places, so it does not map to Qloo's Spain-cuisine tag).

## Units and labels

- **Cell:** geohash precision 6 (about 1.2 km by 0.6 km).
- **Background:** cells containing at least one restaurant of any cuisine that existed before T
  (target-group background: negatives come only from places where restaurants operate).
- **H1 sample for cuisine c:** background cells with zero c restaurants before T.
  Label 1 if at least one c restaurant opened in the cell on or after T, else 0.
- **H2 sample (secondary, presence):** all background cells; label 1 if the cell has any c
  restaurant before T.

## Scores

Qloo heatmap cells (geohash 7) are averaged into their geohash-6 parent. Affinity values are
percentile ranks in [0, 1] as returned by Qloo.

- **M1 raw taste:** A_c(g), the mean Qloo affinity for c in cell g.
- **M2 peer lift (primary model):** L_c(g) = A_c(g) - mean over the other 13 cuisines of A_c'(g).
- **M3 combined:** logistic regression on [B1, B2, L_c], fitted and scored out of fold.

Cells with no Qloo value for c are excluded from that cuisine's evaluation; coverage is reported.

## Baselines

- **B1 restaurant density:** log(1 + number of pre-T restaurants of any cuisine in g). Unfitted.
- **B2 nearby same-cuisine supply:** number of pre-T c restaurants in the 8 neighbouring cells.
  Unfitted (a spatial-null score: openings follow existing clusters).
- **B3 LLM-only:** a frontier LLM with no Qloo access, temperature 0, fixed prompt (stored in the
  repo as `llm_baseline_prompt.txt`) asking for the 20 NYC neighbourhoods (NTA names) best suited to
  a new c restaurant as of December 2023. Score of a cell = 21 - rank of its NTA (0 if unlisted).
  Known leak: the model's training data extends past T.
- **B4 random.**

## Validation

- Unfitted scores (M1, M2, B1, B2, B3) are evaluated directly on all cells.
- M3 uses spatial block cross-validation: GroupKFold, 5 folds, groups = geohash-5 parent
  (about 4.9 km). AUC is averaged across folds and also reported pooled.

## Primary test (decided now)

Pooled over the 14 cuisines (stacked H1 samples): AUC(M2) minus AUC(B1), with a 95% interval from a
paired block bootstrap (2,000 resamples of geohash-5 blocks). **H1 is supported if the lower
bound of that interval is above 0.** The same test is reported for M2 vs B2 and M2 vs B3.

## Secondary analyses

- Per cuisine: AUC with DeLong paired test vs B1; precision@10 and @20; Boyce index.
- Sign test of M2 beating B1 across the 14 cuisines.
- M2 vs M1 (does the peer-lift correction help?).
- H2 presence: AUC with an exclusion sweep (Qloo sub-cells within 0, 250, 500, 1000 m of a c
  restaurant removed before averaging) to measure circularity.

## Decision rule

- H1 supported: the product may say "Qloo taste ranked blocks that later got their first c
  restaurant better than restaurant density did (2024 to 2026 NYC backtest)", with the numbers.
- H1 not supported: the product does not make a predictive claim. It presents Qloo taste as
  description, and the write-up reports the negative result.
- All results are published, including losses, per cuisine.

## Known limitations (stated in advance)

1. Qloo heatmaps are a 2026 snapshot and may partly reflect restaurants opened after T, which
   would make the backtest optimistic.
2. DOHMH keeps only currently active restaurants, so places that closed between T and the pull
   date are invisible; some blocks look emptier before T than they were.
3. A pre-permit inspection marks a new permit, which includes ownership changes, not only brand-new
   restaurants, and it follows the real opening by some weeks.
4. An opening is not success; this test does not measure survival or revenue.

## Disclosure of prior looks

Before registering, exploratory runs examined presence (not openings) of Korean, Vegan and Mexican
restaurants in Brooklyn and Queens using Qloo place data, and the correlation between cuisine
heatmaps. No opening-based (H1) result has been computed. Per-cuisine counts of openings were
inspected to choose T and the cuisine list.

## Amendments

1. 2026-10-09, during the first run. The registered tag `urn:tag:genre:place:restaurant:coffee`
   returned an empty heatmap for every borough, so Coffee/Tea had zero cells and the run crashed.
   Replaced with `urn:tag:genre:place:restaurant:coffee_shop`, which returns data. No Coffee/Tea
   result had been produced. Because coffee is a peer in every other cuisine's lift, all cuisines
   are rerun. Results for six cuisines printed before the crash (with coffee absent from the peer
   set) were seen; they are superseded by the rerun and also disclosed here:
   Korean, Mexican, Japanese, Thai and Indian had AUC(M2) below AUC(B1); Caribbean above.
