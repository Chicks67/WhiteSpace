# Test 12: are Qloo's closing times and price levels right? Pre-registered protocol

Registered 2026-10-12, before the sample was drawn and before any Qloo value was compared with another source. The
git commit adding this file is the timestamp.

## Why

The "what is around this address" panel and Test 9's arm Q state Qloo's Friday closing time and price level for
named restaurants. Nothing has checked those against another source. A visitor who looks up one restaurant and
finds the panel wrong has reason to doubt the rest of the page.

## What had been seen before this file

Qloo's closing times and price levels for many places, in Test 9 backgrounds and panel trials. None had been
compared with any other source.

## Sample

Places come from Qloo records that arm Q shows for the 30 Test 8 cases (competitors with details, places Qloo tags
with the cuisine, and neighbours), each matched to an active city inspection record by Test 10's rule. Kept only
if Qloo gives both a Friday closing time and a price level, and the name has fewer than 5 locations in city
records (no chains). Duplicates are removed. The list is sorted by name, shuffled with seed 12, and 40 places are
taken by going round the four boroughs in turn (Bronx, Brooklyn, Manhattan, Queens) and taking the next place
from each until 40 are drawn; a borough that runs out is skipped.

## The check

A sheet lists each place's name and address only. It does not show Qloo's closing time or price level, and the
checker does not open the key file or the panel for these places. For each place the checker records:
- Google Maps: Friday closing time; the price shown (symbols or a dollar range); whether it is marked permanently
  closed.
- The restaurant's own website or reservation page, if it lists hours: Friday closing time.

The checker may be a team member, because the sheet hides Qloo's values. Who checked, and on what date, is
reported.

## Scoring (fixed)

- Reference closing time: the restaurant's own site if it lists Friday hours, otherwise Google Maps. A place with
  neither, or marked permanently closed, is left out of the closing-time and price measures and counted.
- Closing-time agreement: Qloo's time is within 30 minutes of the reference. Exact agreement is also reported.
- Price: Google's symbols count as levels 1 to 4. A dollar range is mapped by its upper bound: up to $20 is level
  1, up to $50 level 2, up to $100 level 3, above that level 4. Price agreement: Qloo's level equals Google's.
  Agreement within one level is also reported.
- 95% intervals from 2,000 bootstrap resamples of places (seed 0).

## Decision rules (fixed, by point estimate)

- **Closing times, 80% or more within 30 minutes:** shown as they are, with the sample result beside them.
  **Under 80%:** closing times are removed from the panel and from any brief the product ships.
- **Price levels, 70% or more equal:** shown, with the sample result. **Under 70%:** price levels are removed from
  the panel and from any brief the product ships.
- **Permanently closed, more than 10% of the sample:** the panel says plainly that some listed places may have
  closed, with the rate.
- If either attribute is removed, any Test 9 Part B result obtained with arm Q is reported as obtained with
  attributes that failed this check, and it supports no claim about the shipped product.

## Amendment 1 (2026-10-12, after the sample was drawn, before any sheet entry)

Seven of the 40 sampled places (sheet rows 3, 4, 15, 20, 24, 28 and 34) had their Qloo closing time or price level
shown in the team's working session earlier the same day, in Test 9 backgrounds and panel trials. A team member
filling the sheet could remember those values. Found by matching the sheet's names in code against every place
whose values had been shown; a reviewer (DeepSeek) raised the risk.

- The seven stay on the sheet, so the checker is not told which rows they are by their absence.
- The decision rules are applied to the 33 places not shown. The result on all 40 is reported beside it.
- The checker does not scroll back through the session or open the panel for any sampled place.

## Amendment 2 (2026-10-13, before any sheet entry)

The team asked whether a language model with no knowledge of this project could fill the sheet instead of a
person. It is blind to Qloo's values, which is what the check needs. The risk is that a model invents closing
times. So it is allowed on these terms, fixed before any entry exists:

- The model must have live web search switched on, and must give a source link for every value it enters. It is
  given the sheet's names and addresses only: never the key file, the panel, or this project's notes.
- The model and the date are recorded.
- Spot check by a person: rows are sorted by id and 10 are drawn with seed 12. The person looks each one up on
  Google Maps without seeing Qloo's values and compares with the model's entry: closing time within 30 minutes, and
  the same price. If more than 1 of the 10 rows disagrees on either field, the model's sheet is discarded and the
  lookups are done by a person.
- If the sheet passes the spot check, it is scored by the rules above. The result is reported as "looked up by a
  language model with web search, spot-checked by a person on 10 of 40", with the spot check's own count.

## Amendment 3 (2026-10-13, before any sheet entry)

The lookups are done by fresh sub-agents started from the team's coding assistant, each given only names and
addresses. They have live web search but cannot open Google Maps itself. So the reference for a closing time is,
in order: the restaurant's own site; Google's listing where a search result shows it; otherwise one other named
listing site (for example Yelp, OpenTable, Resy, Tripadvisor), with its link. Which kind of source was used is
recorded per row and the result is reported split by it. Price level comes from Google's listing or, failing
that, the same listing site's dollar signs. Amendment 2's terms stand: a link for every value, no entry from
memory, and the 10-row spot check by a person, done against Google Maps, which can void the sheet.

## Limitations

Google Maps and restaurant websites can be stale too; agreement is not truth. 40 places, drawn from 30 storefront
areas that are mostly in Manhattan. One day of the week. The dollar-range mapping is ours.
