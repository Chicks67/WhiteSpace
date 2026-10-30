# Test 25: a stress test of Qloo on its home ground. Pre-registered protocol

Registered 2026-10-14, before any code for this test was written and before any item in its samples was looked up.
The git commit adding this file is the timestamp.

## Why

Tests 14 to 18, 23 and 24 put Qloo against a strong model on famous, much-written-about things, where a model is
strongest. Qloo's paying customers use it where a model is weak: small acts nobody has written about, things newer
than the model, and scoring at scale. This test checks those three, each tied to a product idea, each against an
outside record. The challenge brief asks for an agent that outperforms LLM-only approaches because of Qloo, so the
model alone is a rival in every part.

## What had been seen before this file

ListenBrainz's similar-artists reply for one artist (to learn its shape). The count of NYC restaurant openings by
month in our city data (1,627 since 2026-04-01). No item below was looked up in Qloo or shown to a model.

## Part A: small acts (idea: a scout for the acts nobody has written about)

- **Outside record:** ListenBrainz (open listening data) "similar artists", built from what real people play in the
  same sessions. Algorithm string as fixed in the code.
- **Starter acts (fixed):** Japanese Breakfast, Turnstile, Khruangbin, Alvvays, Black Country New Road, Snail Mail,
  Mdou Moctar, Floating Points, Wednesday, Tyler Childers, Arooj Aftab, Jockstrap. Their MusicBrainz ids come from
  MusicBrainz search (first result of the same name).
- **Seeds:** all acts in the starters' ListenBrainz lists, shuffled (seed 25). A seed is kept when Qloo's artist
  search returns it under the same name **with Qloo popularity below 0.5**, and Qloo returns similar artists for it.
  Stop at 30 seeds or 300 tried; fewer than 15: "too few small acts to say".
- **Truth for a seed:** its own ListenBrainz list in order; the first 8 found in Qloo under the same name (at most 12
  checked). A seed with fewer than 3 is dropped.
- **Shortlist:** the seed's truth acts plus 30 others drawn (seeded) from the truth acts of the other seeds, shuffled.
- **Arms**, AUC of truth acts over the others, per seed: Qloo's artist-to-artist affinity from the seed (no score
  ranks last); fame (Qloo popularity); GPT-6 Astra alone ("You know music and who listens to it. For one artist you
  get a numbered list of other artists. Score each from 0 to 100 for how likely a fan of that artist is to also
  listen to it. Use the whole range."); GPT-6 Astra with Qloo (the same, plus each act's fan-overlap score shown).
- **Readings:** (1) Qloo's AUC lower bound above 0.5 and Qloo minus fame lower bound above 0: "Qloo knows the
  neighbours of small acts, beyond fame". (2) Model with Qloo minus alone: above, below, or no different. (3) Qloo
  minus model alone: the same. Intervals: 2,000 bootstrap resamples of seeds (seed 0).

## Part B: new places (idea: a radar of what opened near a site, or near you)

- **Sample:** NYC restaurants whose first city inspection is on or after 2026-04-01, from our city data; leaving out
  names that appear 3 or more times in the city data (chains), and cuisines recorded as "Other", "Not Listed/Not
  Applicable" or blank. Shuffled (seed 25); the first 120.
- **Found in Qloo:** a place of the same name within 200 m (Test 10's rule, as in scene.resolve_at).
- **Task with an outside answer:** "Which cuisine does this restaurant serve?", the model choosing one from the fixed
  list of cuisine names in the sample. Truth: the city's recorded cuisine. Alone: name, address and borough. With
  Qloo: the same, plus Qloo's record where found (description, up to 8 keywords, up to 8 tag names, price level);
  where not found, the prompt says no record was found.
- **Measures:** share found; share found with a description or keywords; share correct alone and with Qloo, and
  the difference, on all 120 and on the found ones. GPT-6 Astra.
- **Reading:** difference on all 120 with lower bound above 0: "with Qloo, the agent knew more about places opened
  after the model was trained". Otherwise "not shown". Intervals over restaurants.

## Part C: scale and steadiness (idea: why an agent should call Qloo rather than ask the model each time)

- 20 headliners from Test 15 (its first 20 in saved order). The model alone scores the same shortlist again with
  Test 15's exact prompt. Measure: Spearman correlation between the two runs per headliner, and the change in AUC.
- Qloo: the same 5 affinity requests sent twice live, bypassing our cache. Measure: identical or not.
- **Reading:** descriptive only. No claim is made about which is "better".

## Budget

At most about 900 Qloo calls in all (4,500 were left this month; the live demo needs the rest).

## Limitations, stated before the result

ListenBrainz users are a small, enthusiast crowd, so its "similar" lists reflect their taste, not everyone's. "Below
0.5 popularity" is Qloo's own measure of small. In Part B the name often reveals the cuisine, which helps the model
alone; and the cuisine list is the city's, which is coarse. Part B tests knowledge of new places, which is a fact
task like Test 20, not a taste task. Part C shows steadiness, not accuracy. The model may know some small acts.
