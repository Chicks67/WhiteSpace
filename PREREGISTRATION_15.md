# Test 15: does Qloo know who should open for whom? Pre-registered protocol

Registered 2026-10-12, before any Test 15 code or comparison. The git commit adding this file is the timestamp.

## Why

Tests 1 to 14 started from a place or a location, and Qloo did not beat simpler sources or a language model on any
of them. Qloo's graph was first built on entertainment. This is the first test on that ground and the first of a
set of new ideas outside restaurants. The user is a promoter, agent or artist building a tour bill; the decision
is which support act fits a headliner. The record of what really happened is public: ticket listings name the
acts on a bill.

## What had been seen before this file

Qloo's similar-artist lists for two artists (Vince Staples, Parquet Courts), both plausible, and its scores for
five hand-picked artists against each. That 1,306 of 5,590 cached New York music events list two or more acts.
That Ticketmaster's on-sale date filter works. No bill had been compared with any Qloo score.

## Sample

- Bills: US Music events on Ticketmaster that went on sale from 2026-08-15 to 2026-10-12, fetched in weekly
  on-sale windows (up to 1,000 events per window). Kept if they list 2 to 4 named acts; the first listed act is
  the headliner and the others are its supports. Events with 5 or more acts are left out as festivals.
- One bill per headliner: bills are sorted by event id, shuffled with seed 15, and the first bill seen for each
  headliner is used. Headliners are taken in that order until 40 qualify or 400 have been tried. A headliner
  qualifies if it resolves in Qloo (first artist hit, same name after normalising), Qloo returns a similar-artist
  list for it without error, and at least one of its supports resolves the same way.
- Pool: every kept support act. For a headliner, its own supports are positives and every other pool act is a
  negative (an act that also headlines a sampled bill is not scored against itself).

## Scorers, each an AUC per headliner, mean over headliners, 95% interval by bootstrap over headliners (seed 0)

- **Qloo affinity** of each pool act to the headliner (filter.results.entities). No score returned counts lowest.
- **Fame:** Qloo's popularity of the act.
- **Genre:** 1 if the act's Ticketmaster genre equals the headliner's, else 0; no label counts 0.
- **Language model:** GPT-6 Astra, given the headliner's name and a shuffled list of its supports plus 40 other pool
  acts (seed 15), scores each from 0 to 100 for how likely it is to be the support act on that headliner's tour.
  Affinity, fame and genre are also scored on that list for this comparison.

## Outcomes and the sentence for each (fixed)

"Above" means the lower bound of the 95% interval of the gain is above 0. The affinity AUC's own lower bound must
be above 0.5 in every case but the last.

- **Above fame, genre and the language model.** "On real tour bills, Qloo's artist-to-artist affinity picked the
  act that actually opened better than fame, genre, or a language model's own knowledge. This is the first use of
  Qloo in this project that beat a language model against what really happened."
- **Above fame and genre, not above the language model.** "Qloo's affinity carries real information about who
  tours with whom, beyond fame and genre. A language model alone did as well, so we make no claim that Qloo beats
  it."
- **Above fame, not above genre.** "Qloo's affinity knows an act's kind of music, not which acts tour together."
- **Not above fame.** "Qloo's affinity followed fame. Nothing is built on it."
- **Affinity AUC not above 0.5.** "Not shown. Nothing is built on it."

## Limitations, stated before the result

Support acts are often chosen for business reasons (same label, same agent), not taste. The first-listed act is
assumed to be the headliner. Recently on-sale shows limit, but do not remove, the chance that the language model
remembers a tour. Qloo may hold these pairings already. A pass shows the engine works on real bills; whether a
product built on it is useful to a promoter is a separate question for people.
