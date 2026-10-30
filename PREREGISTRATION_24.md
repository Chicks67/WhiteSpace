# Test 24: do older acts that young people took up show a younger crowd in Qloo? Pre-registered protocol

Registered 2026-10-14, before any code for this test was written and before any act in its sample was looked up in
Qloo for this test. The git commit adding this file is the timestamp.

## Why

A candidate product ("Comeback", IDEAS.md): scan older acts for a crowd much younger than their peers', and propose
who should tour, reunite or be reissued. It rests on Qloo's age skew for an artist meaning something. This test
checks that against an outside record of which older acts young people actually took up.

## What had been seen before this file

- A probe on Oct 14 (IDEAS.md): 12 older acts we named as rediscovered and 12 peers we named; the rediscovered act
  had the younger skew 0.792 of the time. Both lists were our own choice, which is why this test takes its list
  from a published source. The 24 probe acts are flagged and results are given with and without them.
- The three source pages below were fetched and the first twelve headings of each were read, to confirm they are
  lists of the form "artist, song". No act from them was looked up in Qloo.

## The outside record

Three published week-by-week lists of songs that trended on TikTok, from one music site (uDiscover Music): "The
Songs That Trended In 2022", "TikTok Songs That Trended In 2023", "Songs That Trended In 2024". TikTok's users are
mostly young, so an older act on these lists is one young people were engaging with. Copies as fetched on Oct 14 are
kept privately.

- An entry is a heading of the form "artist, dash, song". The act is the first artist named (text before "&",
  "feat", "ft", "x" or a comma).
- **Older act:** MusicBrainz (the open music database) returns an artist of the same name among its first three
  search results, and that artist is a group formed in 2000 or earlier, or a person born in 1980 or earlier.
- **Trended older acts:** all acts that pass, shuffled (seed 24), the first 60 that Qloo's artist search returns
  under the same name.

## Peers (fixed rule, no choosing by hand)

For each trended act: Qloo's 50 artists with the highest fan overlap, in order. The first two that (a) are named
nowhere in the three lists, (b) pass the same "older act" rule, and (c) started within 10 years of the trended act
(formation year for a group, birth year for a person, compared like with like). At most 15 candidates are checked
per act. An act with fewer than two peers is dropped. Choosing peers by fan overlap makes the test harder for Qloo:
acts with the same fans should have the same ages.

## Measures

For each set of three (one trended act, two peers), from Qloo's demographics for each artist:
- **Primary:** the trended act's "24 and younger" score minus the mean of its two peers'. Mean over sets, with a 95%
  interval from 2,000 bootstrap resamples of sets (seed 0).
- How often the trended act has the youngest score of the three (chance is one in three).
- The same two figures for Qloo's popularity score in place of age, to see whether age skew is only fame.
- Model arms (GPT-6 Astra, CometAPI), on the same sets with the three names shuffled and no labels. Alone: "For
  each act give a score from 0 to 100 for how much of its audience today is under 25." With Qloo: the same, with
  each act's Qloo age scores shown. Measured the same way: how often the trended act gets the highest score.

Fewer than 20 sets: "too few to say".

## Readings (fixed)

1. **Primary's lower bound above 0.** "Older acts that trended with young people show a younger crowd in Qloo than
   their closest peers of the same era." Otherwise: "not shown".
2. If 1 holds and the popularity difference also has a lower bound above 0, add: "they are also more famous in Qloo,
   so the age gap is not separated from fame here."
3. Model with Qloo against model alone, on the share of sets where the trended act scores highest (difference with a
   bootstrap interval): above, below, or no different.

Results are also given leaving out sets that contain any of the 24 acts in the Oct 14 probe.

## Limitations, stated before the result

The outside record is one site's editorial list, published by a record company's catalogue arm, so it leans toward
that company's artists. A song trending is not the same as an act having a lasting young audience, and some peers
will have trended too without being listed, which works against Qloo. Qloo's data is from today, after these
trends, so this tests whether Qloo reflects what happened, not whether it could have seen it coming. The model has
read about the famous cases. MusicBrainz dates decide who is "older" and who is a peer, and a birth year is a rough
stand-in for when a solo artist was active. Nothing here tests whether a young crowd buys tickets.
