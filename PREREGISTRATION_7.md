# Test 7: given a storefront, does Qloo taste predict WHICH cuisine opens there? Pre-registered protocol

Registered 2026-10-11, before any Test 7 code or result. The git commit adding this file is the timestamp.

## Why

Tests 1, 2 and 4 asked where a given cuisine opens; city records won and Qloo added nothing. They never asked
the reverse question a founder or landlord holding a storefront asks: which cuisine fits this spot? Choosing
between cuisines is what taste data describes, so this is the question where Qloo could add what city
records cannot. If it passes, it becomes a product mode ("what should open here?"). If it fails, we report it.

## Sample

DOHMH pull of 2026-10-09, cutoff T = 2024-01-01, four boroughs, the 14 original cuisines (the ones with Qloo
heatmaps from Test 1). Unit: geohash-6 blocks with at least one first opening (pre-permit operational
inspection on or after T) in one of the 14 cuisines and Qloo heatmap coverage for all 14 in the block and its
ring (628 blocks at registration, counted before any model was fitted). For each block and cuisine, y = 1 if
that cuisine had a first opening there on or after T.

## Features (pre-T city records, and Qloo)

- P_c: share of pre-T restaurants (four boroughs) that are cuisine c (how common the cuisine is).
- S_bc: log(1 + pre-T restaurants of c in the block and its 8 neighbours).
- Q_ring_bc (primary Qloo feature): mean Qloo affinity for c over the 8 neighbouring geohash-6 blocks, not
  the block itself (lowers leakage: Qloo is a current snapshot and may reflect the new venue itself),
  z-scored within cuisine across blocks.
- Q_own_bc (secondary): the same for the block itself.

## Models

Logistic regression on stacked (block, cuisine) rows, out-of-fold with GroupKFold(5), groups = geohash-5.
- CITY: [logit(P_c), S_bc]
- CITY+Q: [logit(P_c), S_bc, Q_ring_bc]

## Primary statistic

Mean over blocks of the within-block AUC (cuisines that opened vs those that did not; blocks where all 14
opened are dropped), for CITY+Q minus CITY.

**Supported if both:** (1) the 95% interval from 2,000 block-bootstrap resamples (resampling geohash-5 groups,
seed 0) has its lower bound above 0; and (2) a permutation test passes: Q_ring is shuffled across blocks within
each cuisine 200 times (seed 0), CITY+Q refitted out-of-fold each time, and fewer than 5% of shuffles reach the
observed difference. Condition 2 exists because Test 5 found a no-foresight placebo gaining as much as Qloo.

## Reported, not decisive

Q_own instead of Q_ring; Q alone; top-3 hit rate (share of blocks where an opened cuisine is in the model's
top 3) for each model; per-cuisine results.

## What the product does with the result

Supported: add "What should open here?" ranking cuisines for a storefront with CITY+Q, and say Qloo improves
it by the measured amount. Not supported: no such mode on Qloo; the page reports the null.

## Limitations

Qloo heatmaps are a 2026 snapshot, so some leakage from the 2024 to 2026 openings remains even with the ring
feature; a pass is an upper bound. Openings are not success (Test 5).
