# Test 21: does Qloo beat the model on lesser-known acts? Pre-registered protocol

Registered 2026-10-13, before any split of Test 15's or Test 16's results by fame was computed or seen. The git
commit adding this file is the timestamp.

## Why

On tour bills the language model alone beat Qloo's artist-to-artist affinity (Test 15: 0.976 against 0.883 on the
same shortlists) and tied with itself plus Qloo's candidates (Test 16). A model knows famous acts from its training
text; for lesser-known acts that knowledge thins out, while Qloo's graph may still hold their links. If Qloo is
ahead on lesser-known headliners, that is a use of the taste graph itself, not of place facts. A reviewer
(DeepSeek) proposed the split; an earlier plan here had queued it and not run it.

## What had been seen before this file

Test 15's and Test 16's overall results. No per-headliner figure had been set beside any fame measure.

## Data: no new model call

- Test 15's 40 headliners, each with Qloo's AUC and the model's AUC on the same shortlist (its supports plus 40
  other acts), as saved.
- Test 16's 46 headliners, each with the share of real supports found in 50 names by the model alone and by the
  model with Qloo's candidates, as saved.
- Fame of a headliner: Qloo's popularity score for it (0 to 1), read from the saved search results.

## Analysis (fixed)

Headliners are split at the median popularity of their test's sample; those at or below the median are "lesser
known".
- **Primary (Test 15 data):** among lesser-known headliners, mean of Qloo's AUC minus the model's AUC, 95% interval
  from 2,000 bootstrap resamples of those headliners (seed 0).
- **Trend (Test 15 data):** Spearman correlation between headliner popularity and (Qloo's AUC minus the model's)
  over all 40, with a bootstrap interval. A negative value means Qloo does relatively better as fame falls.
- **Secondary (Test 16 data):** among lesser-known headliners, mean of recall with Qloo minus recall alone, same
  interval.
Reported beside these: the same figures for the better-known half, and the popularity range of each half.

## Readings and the sentence for each (fixed)

- **Primary's lower bound above 0.** "For lesser-known headliners, Qloo's graph picked the act that really opened
  better than the language model did. The model knows the famous; Qloo knows more of the rest."
- **Primary's interval contains 0, and the trend's upper bound is below 0.** "Qloo closes the gap as acts get less
  famous, without overtaking the model in this sample."
- **Otherwise.** "Qloo was not ahead of the model on lesser-known headliners either."
The secondary is read the same way for "the model found more real openers with Qloo's candidates".

## Limitations, stated before the result

Twenty headliners per half: wide intervals, and a real edge could be missed. "Lesser known" here still means an act
with a Ticketmaster listing that Qloo resolves; truly obscure acts are outside the sample (8 headliners did not
resolve in Test 15). Fame is Qloo's own popularity score. The split was chosen after the overall results were
known, which is why its rule is fixed here first.
