# Test 4: ranking leases in blocks that may already have the cuisine. Pre-registered protocol

Registered 2026-10-10, before any Test 4 result. The git commit adding this file is the timestamp.

## Why this test exists

The product ranks a founder's candidate leases for one concept. Test 1 scored only blocks with no
restaurant of that cuisine before the cutoff, but most real leases sit in busy blocks that already have
it (for example every Flushing block tried for a Korean cafe). The lease ranking has not been tested on
that population. Test 4 tests it, and asks again whether Qloo taste adds anything there.

Known from Test 1 (so this is not a blind question for Qloo): cuisine heatmap signal is concentrated on
existing venues, so on this population raw taste may look predictive simply because it tracks existing
supply. The primary Qloo question is therefore incremental: does taste add to city-record features?

## Unchanged from Test 1

DOHMH pull of 2026-10-09, cutoff T = 2024-01-01, boroughs (Brooklyn, Queens, Manhattan, Bronx), 14
cuisines and tags, geohash-6 blocks, background = blocks with at least one pre-T restaurant of any
cuisine, Qloo cuisine heatmaps by borough (radius 0) averaged over geohash-7 sub-cells, spatial groups
geohash-5, 2,000 block-bootstrap resamples, seed 0.

## Sample and label

For cuisine c: all background blocks with Qloo heatmap coverage for c, whether or not they already have c.
Label y = 1 if the block has at least one restaurant of c whose first pre-permit operational inspection is
on or after T.

## Scores (all from pre-T data)

- **D** (density): log(1 + pre-T restaurants of any cuisine in the block). Same as Test 1 B1.
- **S** (same-cuisine supply): log(1 + pre-T restaurants of c in the block and its 8 neighbours).
- **DS**: out-of-fold logistic regression on [D, S] (GroupKFold, 5 folds, groups = geohash-5).
- **DSQ**: out-of-fold logistic regression on [D, S, M1], where M1 is raw Qloo taste (Test 1 M1), same folds.
- **M1** alone, reported.

All AUCs are computed within each cuisine (a founder ranks leases for one concept).

## Primary question 1: which city-record score ranks leases

The product's lease score will be whichever of D, S and DS has the highest median within-cuisine AUC
across the 14 cuisines. Reported with per-cuisine AUCs and a sign test for the winner against each other
score.

## Primary question 2: does Qloo taste add to city records?

Statistic: mean over cuisines of AUC(DSQ) minus AUC(DS). 95% interval by block bootstrap (resampling
geohash-5 blocks, recomputing every cuisine's difference on each resample; folds are not refitted).

**Supported if** the interval's lower bound is above 0. If supported, M1 enters the product's lease
score as DSQ and the product says Qloo taste adds the measured amount. If not, the lease score uses city
records only, as now.

## Secondary (reported, not decisive)

- Same analysis excluding new openings within 5 m of any pre-T restaurant (likely replacements at the
  same address; earlier label check: 17.3% of new restaurants share an address with an older record).
- Per-cuisine DeLong for DSQ vs DS.

## Limitations

All Test 1 limitations apply. Labels mean "a restaurant of c opened here", not "it succeeded". Blocks
with existing c restaurants may get replacements rather than new demand. Geohash-6 blocks are about
1.2 km by 0.6 km, so leases in the same block tie.

## Amendments

None.
