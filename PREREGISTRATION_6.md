# Test 4b: does the city-records lease score extend to cuisines we have not tested? Pre-registered protocol

Registered 2026-10-11, before any Test 4b result. The git commit adding this file is the timestamp.

## Why

The product covers 14 cuisines, which hold 50% of active NYC restaurants in the four boroughs. The largest
untested inspection categories (American alone has 4,450) are stopped with "not tested". The lease score
(Test 4 winner, DS) uses only city records, so it can be tested on any category without Qloo.

## Candidates (fixed now)

Every DOHMH cuisine category not in the 14 with at least 100 active restaurants in the four boroughs in the
current pull, except "Other": American, Chicken, Juice/Smoothies, Donuts, Hamburgers, Asian/Asian Fusion,
Spanish, Sandwiches, Frozen Desserts, Jewish/Kosher, Tex-Mex, French, Seafood, Bagels/Pretzels, New American,
Irish, Sandwiches/Salads/Mixed Buffet, Greek, Eastern European, Salads, Southeast Asian, Fusion, Steakhouse,
Peruvian. (Greek is separate from Mediterranean in the inspection data.)

## Method (Test 4's, one change)

Same DOHMH pull, cutoff T = 2024-01-01, four boroughs, geohash-6 blocks, background = blocks with at least
one pre-T restaurant, label = block gets a first opening of the cuisine on or after T, features D and S, DS as
out-of-fold logistic regression (GroupKFold 5, groups geohash-5), AUC within cuisine, 2,000 block-bootstrap
resamples, seed 0.

Change: Test 4 used only blocks with Qloo heatmap coverage for the cuisine; Test 4b uses all background blocks,
since no Qloo feature is involved. For comparability the 14 tested cuisines are re-scored on the same all-block
sample and reported alongside.

## Decision rule (per cuisine)

A cuisine enters the product's lease score if all hold:
1. at least 50 positive blocks;
2. DS within-cuisine AUC at least 0.75 (the 14 tested cuisines ranged 0.781 to 0.895 in Test 4);
3. the lower bound of its 95% bootstrap interval at least 0.70.

Cuisines that fail stay "not tested", and the page names them as failed rather than untested.

## Reported, not decisive

AUC of D alone per cuisine (does same-cuisine supply add anything for that category?); the same with
replacements (new opening within 5 m of an older restaurant) excluded.

## Limitations

Openings are not success (Test 5 found the score does not predict survival). Broad categories such as
American mix very different concepts; a pass means the score finds where that category opens, not where a
particular concept would do well.
