# Test 14: does Qloo know which artists fit which room? Pre-registered protocol

Registered 2026-10-12, before any Test 14 code or comparison. The git commit adding this file is the timestamp.
It runs beside the idea screen (PREREGISTRATION_13.md) and does not depend on it: its ground truth is outside Qloo.

## Why

One use of Qloo's entity graph is to tell an owner what their room should sound like and who could play there.
For music venues there is a public record of who actually plays: ticket listings. If Qloo's affinity between a
venue and an artist does not rank the artists a venue booked above artists booked elsewhere in the same city, a
sound or booking feature has nothing to stand on. If it does, that is the first use of Qloo in this project
checked against ground truth outside Qloo and passed.

## What had been seen before this file

Ticketmaster: the first 8 upcoming shows at Brooklyn Steel. Qloo: artist lists for Bowery Ballroom and Music Hall
of Williamsburg (indie rock acts), Blue Note (Latin acts; possibly the wrong entity), an error for Brooklyn Steel,
a wrong name match for "SOBs"; affinity scores of six hand-picked artists against Bowery Ballroom (two acts from
its own Qloo list scored highest). No venue's bookings had been compared with its Qloo scores.

## Sample

- Venues: Ticketmaster Discovery venues within 15 km of 40.73, -73.95 that have upcoming events in the Music
  segment, sorted by Ticketmaster id, shuffled with seed 14. Taken in that order until 25 qualify or 150 have been
  tried. A venue qualifies if it has at least 6 different named music acts upcoming, resolves to a Qloo place
  (Test 10's name rule, within 300 m of Ticketmaster's coordinates), and Qloo returns an artist list for it
  without error.
- Acts: for each venue, its first 10 different named acts by show date, each looked up once with Qloo /search
  (artist type); kept if Qloo's first hit has the same name after normalising. A venue needs at least 5 kept acts
  or it is replaced.
- Pool: every kept act from every venue.

## Measures

For each venue, Qloo's affinity of every pool act to that venue (filter.results.entities). An act Qloo returns no
score for gets the lowest score. An act booked at this venue is a positive; every other pool act is a negative.
- **Affinity AUC** per venue, mean over venues, 95% interval from 2,000 bootstrap resamples of venues (seed 0).
- **Popularity AUC:** the same with Qloo's popularity of the act in place of affinity. Large rooms book famous acts,
  so this is the baseline to beat.
- **Gain:** affinity AUC minus popularity AUC per venue, mean and interval the same way.

Reported, not decisive: how many venues and acts failed to resolve; AUC per venue; the result with acts booked at
two or more sampled venues removed.

## Decision rules (fixed)

- **Affinity AUC's lower bound above 0.5 and the gain's lower bound above 0:** Qloo's venue-to-artist affinity
  carries real information about who plays where, beyond fame. A sound or booking feature may be built on it, and
  the page states this result beside it.
- **Affinity AUC's lower bound above 0.5 but the gain not above 0:** Qloo tracks fame, not fit. No feature is built
  on it.
- **Otherwise:** not shown. No feature is built on it.

## Amendment 1 (2026-10-12, while the first run was in progress, before any Test 14 output was read)

A reviewer (DeepSeek) asked for a time split, a genre baseline and named outcomes. Checked against the data first:
of 1,923 Ticketmaster events fetched, 1 is dated before today, so there are no past bookings to split on; 89% of
act listings carry a genre label other than "Other". The first run's output is discarded unread and the test is
rerun with the measures below. The sample, the affinity AUC and the fame baseline are unchanged.

Added baselines, each scored as an AUC per venue over the same acts as the affinity AUC it is compared with:
- **Genre:** an act's score for a venue is the share of that venue's other sampled acts that carry the same
  Ticketmaster genre. An act with no genre label scores 0. This is "knows what kind of music the room books".
- **Language model:** GPT-6 Astra, the product's model, is given the venue's name, "New York City", and a shuffled
  list of that venue's kept acts plus 40 other pool acts drawn with seed 14, and returns a score from 0 to 100 for
  how likely each act is to be booked there. Affinity, fame and genre are also scored on that same list for this
  comparison. This is "what the model knows without Qloo".

Reported with no reading attached: affinity AUC using only acts whose show went on sale in the last 60 days, and
only acts whose show went on sale earlier. Qloo's data date is unknown and an act may have played the room before,
so this cannot separate memory from fit; it is the only handle available.

Outcomes and the sentence the write-up will use for each. "Above" means the lower bound of the 95% interval of
the gain is above 0; the affinity AUC's own lower bound must be above 0.5 in every case but the last.

- **Above fame, genre and the language model.** "Qloo's venue-to-artist affinity ranked the acts New York venues
  actually booked above acts booked elsewhere, better than fame, better than genre, and better than the language
  model's own knowledge. It knows the room, on venues it holds. Whether this carries over to restaurants is
  untested."
- **Above fame and genre, not above the language model.** "Qloo's affinity carries real information about who
  plays where, beyond fame and genre. The language model alone did as well on these well-known venues, so for
  them the feature adds nothing a model lacks. We make no claim that Qloo beats the model here."
- **Above fame, not above genre.** "Qloo's affinity knows what kind of music a room books, not which acts. A
  feature built on it may describe a room's sound and may not suggest specific acts as a fit."
- **Not above fame.** "Qloo's affinity followed how famous an act is. No feature is built on it."
- **Affinity AUC not above 0.5.** "Not shown. No feature is built on it."

## Amendment 2 (2026-10-12, before any Test 14 result was read)

The first run found only 18 qualifying venues: the API pages to 1,000 events, and the soonest 1,000 music events
cover about 93 venues. Its progress lines were read (18 venues, 5 to 10 kept acts each, no errors); its result
files were deleted unread, as was the output of a second run stopped part-way. To reach more venues, the frame is
widened: upcoming Music events within the same 15 km are fetched in six windows of 30 days from 2026-10-12, up to
1,000 events per window; a venue's acts are still its first ten named acts by show date. The target rises from 25 venues to 40,
and up to 400 venues are tried. Everything else is unchanged. This is done to narrow the intervals, and it is
fixed before any result exists; no venue is added after a result is read.

## Limitations, stated before the result

Qloo may have learned a venue's artists partly from who has played there, so this tests whether Qloo knows a room,
not whether it can foresee a booking. Upcoming shows are used, which postdates some of Qloo's data but not all.
Music venues are not restaurants: a pass supports the method, and a restaurant feature still rests on the
assumption that it carries over. Ticketmaster lists ticketed venues only. A pass says nothing about whether an
owner finds the suggestions useful.
