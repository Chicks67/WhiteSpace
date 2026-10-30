# Test 18: given five films a real person loves, does Qloo know what else they will love? Pre-registered protocol

Registered 2026-10-12, before any Test 18 code or comparison. The git commit adding this file is the timestamp.

## Why

Research into Qloo's customers found one pattern: the customer brings people and a few things they like, and Qloo
predicts what else they will like. That is the product's core job, and none of Tests 1 to 17 has tested it. Real
ground truth exists: public datasets of what real people rated. If Qloo cannot tell a person's loved films from
their disliked ones better than simple baselines, a taste concierge built on it has nothing to stand on; if it can,
and adds to a language model, that is the use the hackathon describes.

## What had been seen before this file

Qloo /search results for three film titles (The Matrix, Toy Story, Amelie), to learn the field names. The file
list of the dataset. No rating had been compared with any Qloo score.

## Data

MovieLens "ml-latest-small" (GroupLens, University of Minnesota): 100,836 ratings by 610 people of about 9,700
films, on a scale of 0.5 to 5, collected up to September 2018.

## Sample

- A film is loved by a person if they rated it 4.5 or 5, and disliked if they rated it 2.5 or lower.
- A person is eligible with at least 13 loved and at least 8 disliked films. Eligible people are sorted by id and
  shuffled with seed 18.
- For each person, their loved and disliked films are each shuffled (seed 18 with the person's id). A film is
  usable if Qloo resolves it: first /search hit of type movie whose release year is within one year of
  MovieLens's and whose name matches after normalising (leading-article forms such as "Matrix, The" are put back
  in order first). The first 5 usable loved films are the person's signal; the next 8 usable loved films are the
  positives; the first 8 usable disliked films are the negatives. A person with fewer than 5, 6 and 6 of these is
  skipped. People are taken until 50 qualify or all have been tried.

## Scorers: each an AUC per person (positives against negatives), mean over people, 95% interval by bootstrap over
people (seed 0)

- **Qloo affinity:** /v2/insights for movies with the five signal films as signal.interests.entities and the
  candidates as filter.results.entities. No score returned counts lowest.
- **Average rating:** the film's mean rating by everyone else in MovieLens. Good films are liked by most people,
  so this is the main baseline to beat.
- **Popularity:** how many people in MovieLens rated the film.
- **Genre:** the share of the film's MovieLens genres that appear among the five signal films' genres.
- **Language model:** GPT-6 Astra, given the five signal titles with years and the candidates in shuffled order
  (seed 18), scores each from 0 to 100 for how much this person would like it.
- **Language model with Qloo:** the same, with Qloo's affinity for each candidate shown beside its title.

## Outcomes and the sentence for each (fixed)

"Above" means the lower bound of the 95% interval of the difference is above 0. Qloo's own AUC must have its lower
bound above 0.5 in every case but the last two.

- **Model with Qloo above model alone.** "Given five films a real person loved, a language model predicted what
  else they loved better when it could see Qloo's scores. It does not work the same without Qloo."
- **Qloo above average rating, popularity and genre; model with Qloo not above model alone.** "Qloo's taste scores
  carry real information about what a person will like, beyond a film's quality, fame and genre. A language model
  did as well without them."
- **Qloo not above average rating.** "Qloo's scores did no better than knowing which films are generally well
  liked."
- **Qloo's AUC not above 0.5.** "Not shown."
Whether the model alone is above Qloo alone is reported with its interval and decides nothing.

## Amendment 1 (2026-10-13, before any model call or result for this test)

The Qloo half was still being prepared and no score had been computed. Tests 14, 15 and 17 compared Qloo with
GPT-6 Astra, one of the strongest models available, and it won each time. A product does not have to run on the
most expensive model. So two arms are added with a small, cheap model (gemini-3.8-flash), given exactly the same
prompts as the large model:
- **Small model alone.**
- **Small model with Qloo.**
All the earlier arms and outcomes stay. Two readings are added, each by the lower bound of the 95% interval of the
difference in AUC:
- **Small model with Qloo above small model alone.** "Qloo's scores made a small, cheap model better at
  predicting what a real person loved."
- **Small model with Qloo not below the large model alone** (the interval of small-with-Qloo minus large-alone has
  its lower bound above -0.03). "With Qloo's scores, a small model predicted a real person's taste about as well as
  a much larger one did on its own." The margin of 0.03 is our choice, fixed here.
If neither holds, the sentence is: "Qloo's scores did not help a small model either."
The large model stays in every comparison; a win over the small model alone is never described as beating a
language model in general.

## Limitations, stated before the result

These are well-known films up to 2018, which suits a language model. MovieLens users are film enthusiasts. People
rate films they chose to watch, so "disliked" films are still films they picked. Qloo's own training data may
include similar ratings. One domain; it says nothing about restaurants, music or travel. Title matching can pick
the wrong film for all scorers alike.
