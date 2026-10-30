# Test 22 (screen): do model-written NYC plans send people to closed places, and can Qloo check them? Pre-registered protocol

Registered 2026-10-13, before any code for this test was written and before any plan was generated. The git commit
adding this file is the timestamp.

## Why

Test 20 is the one result where a model with Qloo beat the model alone: closing times of real restaurants (0 and 3
of 30 right alone, 29 of 30 with Qloo's record). The team finds that too narrow to be a product. A candidate
product built on it: an agent that takes any plan a chatbot wrote about real places, checks each stop against
Qloo's record (is it still in business, is it open at the hour the plan sends you there) and repairs the plan.
In the hackathon gallery (117 projects, read on Oct 13) at least six plan-making entries say on their own pages that
opening hours are not checked, and one entry (Taste Day Japan) found that a current model did not invent places.
So the open questions are the two below. This screen decides whether the product is worth building. It is not a
test of the product.

## Questions

1. **Does the problem exist?** How often does a plan written by a strong model put a stop at an hour when the place
   is closed, or at a place that has shut for good?
2. **Can Qloo see it?** For what share of the stops in those plans does Qloo hold a record with hours?

## Plans (fixed here)

30 requests: 10 neighbourhoods by 3 occasions.

- Neighbourhoods: Williamsburg, Astoria, East Village, Harlem, Park Slope, Long Island City, Lower East Side,
  Bushwick, Jackson Heights, Upper West Side.
- Occasions: "a Friday night out, 7 pm to 1 am"; "a Sunday, 10 am to 4 pm"; "a Monday evening, 6 pm to 11 pm".
  Monday is in because many restaurants close that day, which is a real way plans go wrong; results are shown per
  occasion so no one occasion can carry the total unseen.
- The request, word for word, with the neighbourhood and occasion filled in: "Plan {occasion} for two people in
  {neighbourhood}, New York City. Give exactly 4 stops at real places to eat or drink, in order. For each stop give
  the place's name, its street address, and the time we arrive and the time we leave, in 24-hour HH:MM." The reply
  format is JSON. Nothing in the request mentions opening hours, checking, or Qloo.
- Models, each read on its own: GPT-6 Astra and gemini-3.8-flash, both through CometAPI, one plan per request.
  240 stops in all.

## Checking a stop against Qloo (fixed here, in code)

- **Found:** Qloo's place search across New York City (the first 5 results) returns a place with the same name
  under Test 10's name rule. If several match, the one whose address has the plan's house number, else the first.
- **Has hours:** the found record has hours for the plan's day.
- **Flagged**, any of: the record is marked closed for good; the day is marked closed; the plan arrives before the
  place opens; the plan leaves more than 15 minutes after it closes (a close before 06:00 counts as after
  midnight; with several slots in a day, the stop must fit inside one of them).

## Measures

Per model, with 95% intervals from 2,000 bootstrap resamples of plans (seed 0):
- coverage: share of stops found with hours;
- share of plans with at least one flagged stop; share of checkable stops flagged; both also per occasion.

## The check by a person (so that Qloo is not marking its own work)

All flagged stops from GPT-6 Astra's plans, and the same number of its unflagged checkable stops drawn at random
(seed 22), go into one shuffled sheet with name, address, day and the planned arrival and leaving times: no flag,
no Qloo data. If that is more than 40 rows, 20 flagged and 20 unflagged are drawn (seed 22). A person looks each
place up on Google Maps and writes down its hours for that day, or "permanently closed". A stop is **confirmed wrong** when,
by Google, the place is permanently closed, closed that day, not yet open at arrival, or closed more than 15
minutes before the leaving time.

- precision: share of flagged stops confirmed wrong;
- miss rate: share of unflagged stops that are wrong by Google.

## Decision (fixed here; GPT-6 Astra's plans decide, the small model is reported beside it)

The product is worth building only if all three hold:
1. coverage is at least 0.70;
2. at least 0.25 of plans have a flagged stop;
3. precision is at least 0.70.

Sentences:
- **All three.** "One in N plans a strong model wrote sent people to a place that was closed at that hour; Qloo's
  records caught it, and a person confirmed the catch on Google Maps X times in Y."
- **1 fails.** "Qloo holds hours for too few of the places models put in plans to check them."
- **1 holds, 2 fails.** "Plans from a strong model rarely send people to a closed place: no problem to solve."
- **1 and 2 hold, 3 fails.** "Qloo's flags are too often wrong to act on."

If the decision is no, the team repositions Whitespace and this idea is dropped. Bars 1 and 2 are read first; the
sheet is made and filled only if both hold.

## Limitations, stated before the result

One city, eat-and-drink stops only, 30 plans per model. A model asked differently (for example told to check
hours) may do better. Google Maps is the reference, and Test 12 suggests Qloo's hours may share a source with it;
that makes precision an easier bar than it looks, and it is a check of Qloo against Google, not against the door of
the place. The 15 minute allowance is our choice. A kitchen may close before the listed hour. The person filling
the sheet is on the team.
