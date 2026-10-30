# Test 16: does a model with Qloo find more real openers than the model alone? Pre-registered protocol

Registered 2026-10-12, before any Test 16 code or comparison. The git commit adding this file is the timestamp.

## Why

Test 15 gave Qloo and a language model the same shortlist of 41 acts per headliner. Qloo's artist-to-artist
affinity was strong (AUC 0.875) and the model alone was stronger (0.976). A shortlist suits a model: it only has to
recognise names. A promoter starts with no shortlist. A model cannot name acts it has barely heard of; Qloo can
search its whole catalogue. The hackathon's rule is "if your submission would work the same without Qloo, you're
building the wrong thing", so the fair question is whether the same model does better with Qloo than without, on
what really happened.

## What had been seen before this file

Test 15's results. Another entrant's README claiming Qloo found more real openers in a top 100 than a model alone
(not verified). No open-ended list from either the model or Qloo had been compared with any bill.

## Sample

Test 15's frame and order: US Music events on Ticketmaster on sale 2026-08-15 to 2026-10-12 with 2 to 4 named
acts, one bill per headliner, shuffled with seed 15. Test 15 used the first 56 headliners in that order. Test 16
starts at the 57th and takes headliners until 60 qualify or 300 more have been tried. A headliner qualifies if it
resolves in Qloo (first artist hit, same name after normalising) and Qloo returns at least 20 similar artists
without error. Its supports are all the other named acts on its bill, whether or not Qloo holds them.

## Arms: each returns up to 50 act names for a headliner, best first

- **Model alone:** GPT-6 Astra is given the headliner's name and asked for the 50 acts most likely to be the
  support act on its current US tour.
- **Qloo alone:** the 50 artists with the highest affinity to the headliner.
- **Model with Qloo:** the same model and the same question, plus Qloo's 100 highest-affinity artists with their
  affinity and popularity. It may use them, reorder them and add acts of its own.

## Measure

A real support is found if its name equals a returned name after normalising (positioning._norm). For each
headliner, recall is the share of its real supports found in the 50. Mean over headliners, 95% interval from
2,000 bootstrap resamples of headliners (seed 0), and the same for the difference between two arms.

Reported, not decisive: the same at 10 names; how many headliners have at least one support found; how many of the
supports found by "model with Qloo" came from Qloo's list and how many the model added.

## Outcomes and the sentence for each (fixed)

- **Model with Qloo above model alone** (lower bound of the difference in recall at 50 above 0). "Starting from
  nothing, the same model found more of the acts that really opened when it could search Qloo. This is the result
  the hackathon asks for: it does not work the same without Qloo."
- **Interval contains 0.** "Not shown. With Qloo the model found about as many real openers as without."
- **Model with Qloo below model alone** (upper bound below 0). "Giving the model Qloo's list made it worse at
  finding real openers."
Qloo alone against the model alone is reported with the same three readings and decides nothing.

## Amendment 1 (2026-10-12, before any comparison existed)

The first run produced no data. The harness asked Qloo for 100 artists in one call; the limit is 50, every
headliner was rejected at that step, no model call was made, and its output file (0 headliners) is discarded.
Looking into it also showed the frame was too small: Test 15's frame holds 106 headliners and Test 15 used 56.

- Qloo's 100 candidates are fetched as two pages of 50.
- Frame: the same events (US Music, on sale 2026-08-15 to 2026-10-12, 2 to 4 named acts, one bill per headliner),
  fetched in daily on-sale windows, up to 1,000 events a day, so that more of them are reached. The 56 headliners
  Test 15 tried are left out by name. Bills are sorted by event id and shuffled with seed 16.
- Headliners are taken until 100 qualify or 400 have been tried.
Everything else is unchanged.

## Limitations, stated before the result

Real supports are few (one to three per headliner) and often chosen for business reasons, so recall will be low
for every arm and 60 headliners may be too few to separate them. Name matching misses variant spellings for all
arms alike. The model may know some tours. One model, one prompt wording per arm. A pass shows the pairing helps
on this task, not that a promoter would use the product.
