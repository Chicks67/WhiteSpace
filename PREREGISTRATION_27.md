# Test 27: on small artists, does Qloo know a real listener's taste better than a model? Pre-registered protocol

Registered 2026-10-20, before any code for this test was written and before any artist in it was looked up in Qloo or
shown to a model. The git commit adding this file is the timestamp.

## Why

The candidate product "Point" (read every name on a festival poster or a street, light up the ones for you) rests on
one claim: where little has been written about an act, Qloo's behaviour-based graph knows more than a model that
reasons from text. Tests 21 and 25 could not test small acts. ListenBrainz's API is now behind a browser check. This
test uses an open research dataset of real listening instead.

## What had been seen before this file

The dataset's file list and counts: 1,892 users, 17,632 artists, 92,834 user-artist rows; 1,855 users with 30 or more
artists; 16,230 artists with 10 or fewer listeners in the data. No artist was looked up and no result computed.

## Data

GroupLens HetRec 2011 Last.fm dataset (`user_artists.dat`: each user's 50 most played artists with play counts;
`artists.dat`: names). Collected around 2011.

- **Small artist:** 10 or fewer listeners among the dataset's 1,892 users.
- **Users:** those with 30 or more artists, shuffled (seed 27).
- **For a user:** favourites are their 5 most played artists that Qloo's artist search returns under the same name.
  Positives: up to 5 small artists from the user's own list, outside their 20 most played, that Qloo returns under
  the same name, drawn at random (seeded by user). A user with fewer than 3 positives is skipped.
- **Negatives:** 30 small artists the user did not listen to, found in Qloo under the same name, drawn (seeded) from a
  shared pool built the same way from the small artists of skipped and kept users alike.
- Stop at 40 users kept or 120 tried. Fewer than 20 kept: "too few to say".

## Arms

Each scores every artist on the user's shortlist (positives and negatives, shuffled); the measure is the AUC of the
positives over the negatives, per user.

- **Qloo:** affinity with the 5 favourites together as the signal (`signal.interests.entities`), the shortlist in
  `filter.results.entities`. No score ranks last.
- **Fame:** Qloo popularity.
- **Model alone** (gemini-3.8-flash on Google's API; CometAPI is out of credit): "Here are the five artists a person
  listens to most. For each artist in the numbered list, score from 0 to 100 how likely this person is to listen to it
  too. Use the whole range. If you do not know an artist, give your best guess."
- **Model with Qloo:** the same, with each artist's Qloo score shown ("taste-database fit 0 to 1, or none").

## Analysis and readings (fixed)

Means over users with 95% intervals from 2,000 bootstrap resamples of users (seed 0).
1. Qloo minus model alone, lower bound above 0: "on small artists, Qloo knew a real listener's taste better than the
   model". Upper bound below 0: "the model knew better". Otherwise "no different".
2. Model with Qloo minus model alone: above, below or no different.
3. Qloo minus fame: above or not.
Also reported: each arm's mean AUC, the share of shortlist artists with a Qloo score, and how many artists the model
said it did not know (counted only if it says so in a "note" field; the score still counts).

## Limitations, stated before the result

The data is from about 2011 and lists only each user's top 50 artists, so a small artist missing from a list may still
be one the user liked. Qloo may have been built partly from Last.fm data, which would favour Qloo. A model may have
read about some of these artists in the fifteen years since. "Small" is measured inside this dataset of 1,892 people,
not in the world. Name matching leaves out artists Qloo does not hold, which favours Qloo. One model, on Google's API.

## Amendment 1 (2026-10-20, before any model call and before any result)

The model is GPT-6 Astra through Kie instead of gemini-3.8-flash, now that the team has funded it. The run under the
first wording stopped after selecting 5 users and before any model call; its Qloo lookups are cached and reused.

## Amendment 2 (2026-10-26, before any outcome was computed)

Kie flagged the team's accounts, so the remaining GPT-6 Astra calls go through CometAPI. Same model and prompts;
answers already made through Kie are kept. No outcome had been computed.
