# Test 11: is a restaurant's Qloo scene about the restaurant, or only about its location? Pre-registered protocol

Registered 2026-10-12, before any Test 11 code or comparison. The git commit adding this file is the timestamp.

## Why

Tests 1 to 10 used Qloo's location signals and place records. Qloo's core data is entity-to-entity affinity: given
a restaurant, the places its fans also love (here called its scene). The team wants a feature built on it: a
founder names places their customers already love, and the agent maps the scene and searches storefronts there.
Test 1 found Qloo's location maps sit on existing venues. The same could be true here: a scene could be the same
list for every restaurant on a block. Test 11 checks that before the feature says anything about taste.

## What had been seen before this file

Scenes for five hand-picked seeds on Oct 12 (Thai Diner, Win Son, Peppa's Jerk Chicken, Lucali, Jackson Diner).
For the first, second and fourth the scene read as a recognisable set of like-minded restaurants; for the third
and fifth it was mostly nearby places, chains included. No two seeds on the same block had been compared.

## Sample

Blocks are geohash-6 cells in the four boroughs with at least 6 restaurants in city inspection records, taken in
a random order (seed 11). In each block, restaurants are shuffled (seed 11 with the block), names with 5 or more
locations in the records are dropped as chains, and the inspection category with the most restaurants is the
block's main category. Seeds are resolved in that order with one Qloo /search each (by name, near the address; a
hit counts if it matches by Test 10's name-and-200 m rule), until the block has two resolved restaurants of the
main category (A1, A2) with different names and one of another category (B), or 10 searches are used; then the
block is skipped. Blocks are taken until 40 are complete or 200 have been tried.

A seed's scene is the first 30 places from /v2/insights with filter.type place, signal.interests.entities set to
the seed and filter.location.query "New York City", leaving out the three seeds of its block.

## Measures

For two seeds, overlap is the share of places the two scenes have in common out of all places in either (Jaccard).
- Per block: same = overlap(A1, A2); different = mean of overlap(A1, B) and overlap(A2, B).
- **Location share:** mean over blocks of "different". How alike are the scenes of two unlike restaurants that
  share a block.
- **Category effect:** mean over blocks of same minus different, 95% interval from 2,000 bootstrap resamples of
  blocks (seed 0). The inspection category comes from the city, not from Qloo.

Reported, not decisive: share of each scene within 1,500 m of its seed; share of seeds with an empty scene; how
many searches resolved; results per borough.

## Decision rules (fixed)

- **Location share 0.5 or more:** a scene is mostly its location. The feature may show it only as "popular near
  this place", never as taste, and it is not used to choose neighbourhoods.
- **Location share under 0.5 and the category effect's lower bound above 0:** scenes differ between restaurants on
  the same block and follow an independent label. The feature may present a scene as "places this restaurant's
  fans also go", always with the share of the scene that lies within 1.5 km of the seed.
- **Location share under 0.5, category effect not above 0:** scenes differ but nothing independent backs them.
  The feature may show a scene labelled "Qloo's list, not validated" and may not use it to choose neighbourhoods.

In every case the lease ranking stays the city-records score. Nothing here tests whether opening inside a scene
is a good idea; the feature must not say so.

## Limitations

Inspection category is a coarse label, and Qloo may use cuisine itself when computing affinity, so a category
effect shows scenes are not arbitrary, not that they measure taste. Seeds are restaurants Qloo can resolve, which
favours better-known places. Qloo data is a 2026 snapshot that already reflects where venues are today.
