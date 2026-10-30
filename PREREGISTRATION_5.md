# Test 5: do restaurants on high-scoring blocks survive? Pre-registered protocol

Registered 2026-10-11, before any comparison between the old snapshot and today's records. The only things
looked at in the snapshot were its file list, column names, row count and latest inspection date. The git
commit adding this file is the timestamp.

## Why this test exists

Every lease result so far predicts where a cuisine opened, not whether it lasted. A founder cares about
lasting. NYC's inspection data drops closed restaurants, so survival needs an older copy of the data.

## Data

- **Snapshot S:** Kaggle dataset `shivanielakurthy/dohmh-new-york-city-restaurant-inspection-results`
  (uploaded 2022-03-11; latest inspection in the file 2021-10-15, so S is dated 2021-10-15). 383,115 rows,
  29,697 restaurants, with coordinates. Downloaded 2026-10-11. Other copies found (Kaggle 2017-08 without
  coordinates; Kaggle 2021-05) are not used, chosen now.
- **Today C:** the DOHMH dataset 43nn-pn8j. Survival is checked against every CAMIS in C, fetched without
  any filter (so a restaurant missing coordinates today still counts as open).

## Cohort

Restaurants in S in Brooklyn, Queens, Manhattan and the Bronx, with coordinates, in one of the 14 tested
cuisines, whose earliest inspection in S is between 2018-10-15 and 2021-10-15 (young restaurants: open at
most about 3 years at S).

## Label

Survived = the restaurant's CAMIS appears in C. Closed = it does not.

## Scores (computed from S only, as of 2021-10-15)

- **D:** log(1 + restaurants in the restaurant's geohash-6 block in S).
- **S:** log(1 + same-cuisine restaurants in the block and its 8 neighbours in S, not counting itself).
- **Lease score:** the product's Test 4 score, `lease_model.json` coefficients applied to D and S.
- **Qloo taste:** Test 1's raw cuisine heatmap affinity for the block. Qloo has no historical data, so this
  is today's map applied to 2021 restaurants; a stated limitation.

## Primary question 1: does the product's lease score predict survival?

Per cuisine: AUC of the lease score for survived vs closed. Statistic: mean of per-cuisine AUCs. 95% interval
by block bootstrap (resampling geohash-5 blocks, 2,000 resamples, seed 0).
- **Supported (higher score, more survival)** if the interval's lower bound is above 0.5.
- **Reversed (higher score, less survival)** if the upper bound is below 0.5. The product then must warn
  that its top-ranked blocks see fewer survivors, and show both rankings.
- Otherwise: no evidence either way; the page says the lease score predicts openings, not survival.

## Primary question 2: does Qloo taste add to city records for survival?

Per cuisine: out-of-fold logistic regression (GroupKFold, 5 folds, groups = geohash-5) on [D, S] vs
[D, S, Qloo taste]. Statistic: mean per-cuisine AUC difference, 95% interval by the same bootstrap.
**Supported** if the lower bound is above 0. If supported, survival-based ranking with Qloo may enter the
product, stating the measured gain.

## Secondary (reported, not decisive)

- Per-cuisine AUCs for D, S, the lease score and Qloo taste alone.
- Survival rate overall and by cuisine.
- Same-cuisine restaurants within 400 m (from S) against survival.

Cuisines with fewer than 15 survivors or fewer than 15 closures in the cohort are reported but left out of
the means.

## Known limitations

Absence from C can mean closure, an ownership change that created a new CAMIS, or a record dropped for
another reason; it is treated as closure. The cohort opened partly during COVID-19. Qloo taste is today's,
not 2021's. The snapshot is a third-party copy of the public dataset; its row and restaurant counts are
reported so others can match it.

## Amendments

None.
