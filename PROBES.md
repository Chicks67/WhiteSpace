# Scout probes: failure criteria written before running (Oct 11)

Each plan is run once on the scout. A run FAILS on any listed condition. Read the output only after this
file is committed.

## Late night, anywhere except Manhattan (Mexican taqueria)
- Any pick in Manhattan.
- Any claim about opening hours, nightlife, bar density or late-night demand that no tool returned (we have
  no hours or nightlife data). Pass requires the summary or a reason to say that late-night demand is not
  measured.
- Using Qloo to say who is there.

## Families on Staten Island (pizzeria)
- Any shortlist at all: Staten Island is outside our tests (we did not load its data). Pass = the run stops
  with a clear message that Staten Island is not covered, and offers nothing in other boroughs as if it were.
- Note (added after writing the criterion, before the re-test): the prediction was that the scout would
  silently pick elsewhere, because its borough list has only the four tested boroughs. A code stop was
  added; the re-test below checks it fires.

## Concurrent load (three plans at once)
- Criterion written before running. FAIL if any run shows the "budget used up" message while the account has
  credit, or a raw provider error. PASS if every run either finishes or shows "busy, try again in a minute",
  and a run retried afterwards (one at a time) finishes.

## Tourists and hotel guests, walking distance from Times Square or the High Line (Italian trattoria)
- Any pick in another borough.
- Calling residents "the local audience" or using a residential census measure as the main target. Pass
  requires the 'visitors' measure (hotels) or storefronts_near_place for Times Square or the High Line.
- Claiming tourist foot traffic numbers that no tool returned (subway entries are the only traffic proxy).

## Campus re-run: right next to NYU or Columbia (bubble tea and bakery), with storefronts_near_place
- Not calling storefronts_near_place.
- Accepting NYU's Brooklyn campus without saying so or retrying with a Manhattan name.
- Picks with no stated distance to the campus.

## New Test 4b cuisines: burger joint for office workers in Manhattan; bagel shop for families in Brooklyn
- Criteria added before running. FAIL if the concept resolves to anything but Burgers / Bagel shop, if the run
  errors, if any pick is outside the named borough, or if a pick has no cuisine-fit percentile.

# Results

| Probe | Result | Note |
|---|---|---|
| Families on Staten Island | PASS (re-test of the code fix) | Stopped in 0.0 s with the not-covered message; no picks, no model call. Predicted failure (silent picks elsewhere) fixed in code first. |
| Late night outside Manhattan | PASS | No Manhattan picks; every reason says nightlife is unverified; "Not measured" note shown; survival check sent one shortlist back |
| Tourists near Times Square or the High Line | PASS | Visitors (hotel) measure plus storefronts_near_place; "98 metres from Times Square"; recovered when a long place name was not found |
| Campus re-run with storefronts_near_place | FAIL, then PASS after a fix | First run: the Columbia pick (from an area search) had no distance. Fix: every storefront found after a place is matched carries its distance. Re-run: all 3 picks state it (327 m, 410 m, 497 m) |
| Burger joint, office workers, Manhattan (Test 4b cuisine) | PASS | Resolved to Burgers; Manhattan only; fit percentile on every pick |
| Bagel shop, families, Brooklyn (Test 4b cuisine) | PASS | Resolved to Bagel shop; Brooklyn only; subway distances stated |
| Concurrent load, three at once | PASS | All three finished (34 to 56 s); the busy path did not trigger at three |
| Six at once (extra, not pre-registered) | budget path checked | The account ran out mid-batch: five runs showed "budget used up" with the provider's quota error kept in the detail; one finished. The busy message is still untested live |

Also found and fixed during the campus run: the brief's name check replaced "NYU", which the founder had written in the plan. Names the founder wrote now count as sourced ("named in your plan").
