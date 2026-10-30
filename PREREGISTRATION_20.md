# Test 20: does a model know when a restaurant closes, with and without Qloo? Pre-registered protocol

Registered 2026-10-13, before any Test 20 code or model answer. The git commit adding this file is the timestamp.

## Why

The team's question throughout has been a use where a model with Qloo does better than the same model alone.
Tests 16 and 18 asked that for taste and found ties. Test 12 found Qloo's Friday closing times agree with Google
Maps for 29 of 30 places. A language model has no live opening hours. So the direct question is whether a model
answers "when does this place close on Friday?" correctly more often with Qloo's record than without it.

## What had been seen before this file

All of Test 12: Qloo's closing time against Google's for every sampled place (29 of 30 within 30 minutes on the
decision sample). So the "with Qloo" arm's score is essentially known already; it is run for completeness. No
model had been asked for any closing time.

## Sample and reference

Test 12's sampled places that are still operating and have Friday hours on Google Maps (36). The reference is the
Friday closing time a team member read off Google Maps on 2026-10-13. As in Test 12, the decision uses the places
whose Qloo values had not been shown in the working session (30); all 36 are reported beside it.

## Arms

Each arm gets the place's name and address and the question "What time does it close on Friday?", and replies with
a time or says it does not know.
- **Large model alone:** GPT-6 Astra, no tools, no background.
- **Large model with Qloo:** the same, with Qloo's opening hours for that place in the prompt.
- **Small model alone** and **small model with Qloo:** gemini-3.8-flash, same two prompts.

## Measures

- **Correct:** the answer is within 30 minutes of Google's Friday closing time. "Does not know" is not correct.
- Reported: how often each arm declines to answer, and how often it gives a time that is wrong by more than 30
  minutes (a confident wrong answer).
Share of places correct per arm; 95% interval from 2,000 bootstrap resamples of places (seed 0); the same for the
difference between a model's two arms.

## Readings and the sentence for each (fixed). "Above" means the lower bound of the difference is above 0.

- **Model with Qloo above model alone.** "Asked when a real New York restaurant closes on Friday, the model was
  right for X of N places with Qloo's record and Y of N without it. This is a job the agent cannot do the same
  without Qloo's place data."
- **Not above.** "The model alone answered closing times about as well as with Qloo's record."
The reading is given for each model.

## What a pass does and does not show, stated before the result

Qloo's hours matched Google's to the minute in Test 12, so they very likely share a source. A pass therefore shows
that live place data reaching the agent through Qloo's API does something the model cannot, with Google Maps as the
yardstick. It does not show Qloo is the only source of such data, and it is not a result about taste. The sample is
40 places drawn for Test 12, mostly small independents, which is where a model's knowledge is thinnest.
