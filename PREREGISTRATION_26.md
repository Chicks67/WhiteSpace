# Test 26: do theme nights that suit a city's taste draw more people? Pre-registered protocol

Registered 2026-10-20, before any code for this test was written and before any attendance or promotion was read for
analysis. The git commit adding this file is the timestamp.

## Why

A candidate product: a promotions agent for sports teams that picks theme nights a city's own fans will turn out
for. One entry in the gallery (Theme Night GM) builds this and scores itself with Qloo's numbers. No one has checked
it against tickets. Attendance is public, so this test can.

## What had been seen before this file

That MLB's public API returns attendance per game (one Dodgers game) and a promotion list per game (White Sox, June
2026: promotions at 24 of 26 games, names such as "All-You-Can-Eat" and "Family Section"). Nothing else.

## Data

- All 30 MLB teams, 2026 regular season home games with a final status, from MLB's public API: attendance from each
  game's box score; promotions from the schedule with `hydrate=game(promotions)`.
- **Theme night:** a game with a promotion naming a cultural property: a film, TV show, artist, band, video game,
  book or character franchise, or brand (for example "Star Wars Night", "Bluey Day"). The model reads each distinct
  promotion name once (GPT-6 Astra; "If this ballpark promotion is themed on a named film, show, artist, game, book,
  character franchise or brand, give that name; otherwise null"), and Qloo's search must find that name among films,
  TV shows, artists, games, books or brands under the same name. Heritage, faith, team, school, charity, holiday and
  sport themes count only if the model returns such a named property, which it should not.
- **Outcome for a game:** log attendance minus the mean log attendance of the same team's other home games on the
  same day of the week (Mon to Thu pooled, Fri, Sat, Sun). Games at or above 98% of the team's highest attendance
  of the season are flagged as near sellouts and analysed with and without.

## Predictors

For each theme night, the property's pull in that team's city:
- **Qloo:** affinity of the property for the team's city (`signal.location.query` = the team's city, the property in
  `filter.results.entities`, same entity type).
- **Fame:** Qloo popularity of the property.
- **Model alone (GPT-6 Astra):** "How strong is the fan following for this in this city, compared with other US
  cities? 0 to 100." Given the property name and the city.
- **Model with Qloo:** the same, with Qloo's affinity for that city shown.

## Analysis (fixed)

Over theme nights: Spearman correlation between each predictor and the outcome, 95% interval from 2,000 bootstrap
resamples of theme nights (seed 0). Differences between predictors' correlations, same bootstrap.

Fewer than 40 theme nights: "too few theme nights to say".

## Readings (fixed)

1. Qloo's correlation lower bound above 0: "theme nights that suit the city's taste in Qloo drew more people than
   the team's usual crowd for that day". Otherwise "not shown".
2. Qloo minus fame above 0 (lower bound): "beyond the theme's fame".
3. Model with Qloo minus model alone: above, below or no different. Qloo minus model alone: the same.

## Limitations, stated before the result

Many theme nights sell a special ticket package to a small group, so most of the crowd may not be there for the
theme. Giveaways, fireworks, opponents, weather and pennant races move attendance more than any theme, and are not
controlled beyond day of week. Popular teams sell out, which caps the outcome. Teams choose themes they already
expect to sell, so the sample is not random. The model has general knowledge of where fandoms are strong. One
season, one league.

## Amendment 1 (2026-10-20, before any model call and before any outcome was computed)

CometAPI ran out of credit after the attendance data was downloaded, and the Vercel gateway needs a card on file.
All model steps (reading promotion names, model alone, model with Qloo) run on gemini-3.8-flash through Google's API
on the team's keys instead of GPT-6 Astra. Nothing else changes. No model answer had been produced for this test.

## Amendment 2 (2026-10-20, before any outcome was computed)

The team funded GPT-6 Astra on Kie, so the model steps return to GPT-6 Astra (through Kie), as first registered.
Gemini had read about 550 promotion names under Amendment 1; those readings are discarded and every name is read
again by GPT-6 Astra, so one model does every step. No theme-night list, Qloo score or outcome had been computed.

## Amendment 3 (2026-10-26, before any outcome was computed)

Kie flagged the team's accounts, so the remaining GPT-6 Astra calls go through CometAPI. Same model and prompts;
answers already made through Kie are kept. No outcome had been computed.
