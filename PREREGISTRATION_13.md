# Idea screen: which uses of Qloo's entity graph are worth a real test? Pre-registered protocol

Registered 2026-10-12, before any screen code or result. The git commit adding this file is the timestamp.

## Why

Tests 1 to 11 found that Qloo does not help the product's location questions, and Test 9 found it is not shown to
improve the brief. The team wants to try several different uses of Qloo's taste graph, keep the ones that work,
and combine them. Trying many ideas and reporting the ones that look good is a forking-paths error. So every idea
goes through one screen with pass marks fixed here, and an idea that passes earns its own registered test against
ground truth or people. A screen pass is not a result and is never reported as one.

## What had been seen before this file

Artists, brands and podcasts for five hand-picked restaurants (mean pairwise overlap 0.02, 0.17 and 0.28). Scenes
for the 120 Test 11 restaurants; 46 of them got Qloo's generic landmark list. A probe of other place categories
for two restaurants was started and not yet read.

## Ideas

The user in every idea is an independent restaurant owner or founder. Each idea starts from a restaurant (or
several) that Qloo holds and asks the graph a question whose answer is a decision.

| # | Idea | The owner's question | Qloo output screened |
|---|---|---|---|
| 1 | Partners | Which other local businesses share my customers? | NYC places that are not restaurants, by affinity |
| 2 | Scene | Which restaurants are my crowd's other favourites? | NYC restaurants, by affinity |
| 3 | Sound | What should the room sound like, and who could play here? | Music artists, by affinity |
| 4 | Brands | What should I stock or co-brand with? | Brands, by affinity |
| 5 | Screen taste | What do they watch (for look, references, tone)? | TV shows and films, by affinity |
| 6 | Words | What do they care about (for menu and voice)? | Tags, by affinity |
| 7 | Twin city | If I open in another city, which places there share my crowd? | Chicago places, by affinity |

Ideas that need data from outside Qloo and are not in this screen, but may follow from it: event booking checked
against who actually played at a venue (needs a ticketing or listings source); sound checked against restaurants'
own published playlists (needs a music service).

## Seeds

- Restaurants: the Test 11 restaurants whose scene was not the generic landmark list, sorted by name, shuffled
  with seed 13, first 30. They were drawn at random from city records in Test 11.
- Sibling pairs: names with 2 to 4 locations in city records (not chains), shuffled with seed 13, each location
  resolved in Qloo by Test 10's rule; a pair counts when two locations resolve to different Qloo entities. Taken
  until 15 pairs exist or 120 searches are used.

## Checks, the same for every idea (top 10 items per seed)

- **Coverage:** share of the 30 seeds that get at least 5 items.
- **Generic list:** share of seeds whose top 10 equals the most common top 10 among the seeds.
- **Specificity:** mean overlap (Jaccard) of the top 10 between pairs of different seeds.
- **Baseline:** mean overlap of a seed's top 10 with the top 10 of the same query made with no seed.
- **Consistency:** mean overlap between the two locations of a sibling pair, minus the mean overlap between
  unrelated seeds; 95% interval from 2,000 bootstrap resamples of sibling pairs (seed 0). Two branches of one
  restaurant should share more of a crowd than two unrelated restaurants.

## Pass marks (fixed)

An idea passes the screen only if all hold: coverage at least 0.7; generic list at most 0.2; specificity at most
0.15; baseline at most 0.3; consistency interval's lower bound above 0.

- **Pass:** the idea gets its own pre-registered test against ground truth outside Qloo or against real owners.
  Nothing is claimed for it before that test.
- **Fail:** the idea is dropped, or shown only with the failing check stated beside it.
- All seven results are reported, passes and fails alike.

## Amendment 1 (2026-10-12, while the screen was running, before any screen result was read)

A reviewer (DeepSeek) pointed out that sibling consistency can come from a shared name. Separately, a two-restaurant
probe of other place categories (read after this protocol was first committed) gave lists that could be explained
by where each restaurant stands: a Crown Heights restaurant got Planet Fitness and T.J. Maxx, a Nolita one got
Barry's and Aritzia. So a secondary analysis is added. The pass marks above are unchanged and still decide the
screen; this is reported beside them and is weighed when choosing which passing idea to test first.

For every idea, using the Test 11 blocks in which all three restaurants (two of the block's main inspection
category, one of another) hold signal:
- **Location effect:** mean top-10 overlap between two restaurants of different categories on the same block,
  minus the mean overlap between unrelated seeds.
- **Nearby share** (ideas whose items are places): mean share of a seed's top 10 within 1,500 m of the seed, over
  all 30 seeds.
- **Category effect, reported only:** mean overlap between the two same-category restaurants on a block, minus the
  overlap between different-category restaurants on that block, with a bootstrap interval over blocks (seed 0).
  Only about 12 blocks qualify, so this cannot show much either way and no reading is attached to it. It does not
  settle whether sibling consistency reflects a shared name or a shared crowd; that stays open.

Reading, fixed now: an idea whose location effect is above 0.3, or whose nearby share is above 0.5, is described as
"mostly about where the restaurant is", and any later test of it must include a control for distance. The two
cut-offs are our choice, fixed before any result.

Revised the same hour, still before any screen result was read: the category effect was first written as a check
with the same standing as the other two, and was demoted when the count of usable blocks was worked out.

## Limitations

The screen asks whether an output is specific and self-consistent, not whether it is true or useful. Consistency
between siblings can come from a shared name or brand rather than shared taste. Seeds are restaurants Qloo holds
signal for, about six in ten of those drawn. One city.
