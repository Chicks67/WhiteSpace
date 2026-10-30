# Test 10: is Qloo's list of competitors complete and current? Pre-registered protocol

Registered 2026-10-12, before any Test 10 code or comparison. The git commit adding this file is the timestamp.

## Why

Test 9's variant E builds a brief from Qloo's list of same-cuisine places around a storefront, with their prices,
hours and review keywords. A line such as "no Japanese place nearby opens past 22:00" is only true if that list
holds the competitors that exist. An earlier borough-level check found Qloo listed 72 Korean places in Queens
against 198 in city inspection records (PROJECT_LOG.md, section 1). Test 10 measures this at the scale the
product uses, in both directions, and fixes how competitor claims may be worded. It runs before Test 9 Part B.

## What had been seen before this file

Qloo's same-cuisine list (first 12 places) for Test 8 cases 1 and 3, printed during Test 9 development. No Qloo
list had been matched against city records for any case. The Queens Korean figure above.

## Cases

The 30 Test 8 cases (test8_cases.json): storefront point and concept. These are Test 9's development cases. No
Test 9 Part B case is touched.

## Lists

- City list: restaurants in NYC inspection records (active restaurants; the data already loaded by engine.py)
  whose inspection category is the concept's category (engine.CONCEPTS), by distance from the storefront.
- Qloo list: places from /v2/insights with filter.type place and filter.tags set to the concept's cuisine tag (the
  query variant E uses), all pages of 50 up to 200 places, not marked closed, by our own distance from the
  storefront computed from Qloo's coordinates.

## Matching rule (fixed)

Names are normalised with positioning._norm, then the words restaurant, cafe, kitchen, bar, grill, cuisine, house,
shop, food, foods are dropped. A city record and a Qloo place match if they are within 200 m of each other and
their names are equal, or one name's words are the opening words of the other, or the two word sets share at least
half of their union. One Qloo place can match one city record at most (nearest name-matching pair first).

To avoid edge effects, places within 1,500 m on one side are looked for among places within 1,800 m on the other.

## Measures (pooled over all cases; 95% interval from 2,000 bootstrap resamples of cases, seed 0)

- **Coverage:** of city-list restaurants within 1,500 m, the share matched to a Qloo-list place.
- **Existence:** of Qloo-list places within 1,500 m, the share matched to an active city record of any category.

Reported, not decisive: both measures per cuisine and per borough; counts per case. For a random sample of 40
unmatched city-list restaurants (seed 10), one Qloo /search by name near the address, to split "Qloo does not have
it" from "Qloo has it without this cuisine tag". For a random sample of 40 unmatched Qloo places (seed 10), the
names are listed for the team to check by hand; that hand check is reported as unblinded.

## Decision rules (fixed)

Coverage, by its point estimate:
- **80% or more:** competitor findings may be stated from Qloo's list alone.
- **50% to under 80%:** the competitor set shown to the writer and on the page is the union of both lists; city-only
  places appear as "no Qloo detail". Absence claims ("none opens late") must be worded as "among the N we have
  details for".
- **Under 50%:** as above, and no absence claim is made at all.

Existence, by its point estimate:
- **90% or more:** Qloo places may be named as operating.
- **Under 90%:** only Qloo places with a matching active city record are named as operating; the others are
  listed separately as unconfirmed.

Whatever the bands, the frozen arm for Test 9 Part B is worded to comply, and that wording is committed with Part
B's details before any Part B case is sampled.

## Limitations

City inspection categories and Qloo cuisine tags are different taxonomies, so a real restaurant can be in one list
and not the other because of its label, not because it is missing; the /search sample measures how often. City
records lag new openings by weeks and drop closed restaurants. Name matching is imperfect in both directions.
The 1,500 m circles of nearby cases overlap, so cases are not fully independent. 30 storefronts.
