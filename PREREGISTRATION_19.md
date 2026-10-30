# Test 19: on another team's 115 real tours, does Qloo lift a small model, and a large one? Pre-registered protocol

Registered 2026-10-13, before any Test 19 code or comparison. The git commit adding this file is the timestamp.

## Why

Another entry in this hackathon, "advance" (github.com/bisale24-ops/advance), reports that Qloo's top 100 artists for
a headliner contain 109 of 619 real openers, against 37 for a language model alone and 17 for a genre chart. Our
Test 16 found a tie between GPT-6 Astra alone and the same model with Qloo's candidates. Reading their code shows
the main difference: their model is Apertus 70B, a mid-sized open model, and ours is a frontier model. Their tour
list is larger than ours (115 tours from Wikipedia, about 5.6 support acts each). This test reruns their design on
their tours with a small model and a large one, each with and without Qloo.

## What had been seen before this file

Their README's numbers (above; at 10 names 26 against 21, at 25 names 48 against 32). Their scripts' logic as
summarised by a reader: Qloo's list is the plain top 100 artists by affinity to the headliner, the headliner
excluded; names match on Qloo id or on lower-cased name with "&" as "and"; only openers Qloo resolves are counted.
The first three entries of their tours file. Test 16's result. No list of ours had been compared with their tours.

## Data

Their data/tours.json as published (115 tours: headliner, support acts), used as a list of public facts with credit.
A tour is used if its headliner resolves in Qloo (first artist hit, same name after their normalisation) and Qloo
returns 100 similar artists. An opener counts if it resolves in Qloo the same way (their denominator).

## Arms: each returns up to 100 names for a headliner, best first

- **Qloo alone:** the 100 artists with the highest affinity to the headliner, in two pages of 50.
- **Small model alone:** gemini-3.8-flash with their prompt: "List 100 different artists who would be good opening
  acts for a {name} concert tour, best fit first."
- **Small model with Qloo:** the same prompt, plus Qloo's 100 names with affinity and popularity, and the line
  "Use this list as you see fit: pick from it, reorder it, and add artists of your own."
- **Large model alone** and **large model with Qloo:** GPT-6 Astra, same two prompts.
Replies are asked for as a JSON list of names; nothing else differs between a model's two arms.

## Measure

An opener is found at a cut-off if a returned name within it matches by their rule. For each tour, recall is the
share of its counted openers found. Mean over tours and 95% interval from 2,000 bootstrap resamples of tours
(seed 0), at 100 names (primary) and at 10 and 25 (reported). Total hits out of all counted openers are reported
beside their published figures.

## Readings and the sentence for each (fixed). "Above" means the lower bound of the difference's interval is above 0.

- **Small model with Qloo above small model alone.** "On 115 real tours, a small model found more of the acts that
  really opened when it could see Qloo's candidates." Otherwise: "Qloo's candidates did not help a small model."
- **Large model with Qloo above large model alone.** "The same held for a frontier model." Otherwise: "For a
  frontier model, Qloo's candidates made no measurable difference."
- **Small model with Qloo against large model alone,** reported with its interval. If its lower bound is above
  -0.03: "With Qloo, the small model found about as many real openers as the frontier model alone."
- **Replication:** whether Qloo alone is above the small model alone at 100 names, as "advance" reports for its
  model. Stated as reproduced or not reproduced, with our counts beside theirs.

## Limitations, stated before the result

These tours are on Wikipedia, so either model may have read who opened; that favours the models, not Qloo. The
tour list is another team's and was not checked against Wikipedia by us. Openers Qloo cannot resolve are left out,
which favours Qloo. Supports are often label-mates or friends, so recall is low for every arm. The small model is
not the one "advance" used. Model arms run on whichever host has credit; the host is recorded.
