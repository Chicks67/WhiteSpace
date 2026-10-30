# Test 8: does Qloo add anything a list of nearby businesses does not? Pre-registered protocol

Registered 2026-10-11, before any Test 8 code, brief or judgement. The git commit adding this file is the timestamp.
Test 3 (PREREGISTRATION_2.md) is unchanged and still pending; Test 8 is a separate test.

## Why

Five tests found Qloo does not help decide where a cuisine opens or which cuisine opens. Qloo's remaining role is
describing the taste of the people around a place, to position a concept. Test 3 compares a brief written with
Qloo evidence against one written with nothing. That leaves open whether Qloo adds anything beyond what city
records already give: a model told which businesses are nearby might position a concept as well. Test 8 adds
that arm. Its result decides whether the product is rebuilt around "what should open here, and how to position
it" with Qloo at the centre.

## Cases

30 vacant storefronts from the Storefront Registry, sampled with seed 8 after excluding Test 3's 10 locations,
one concept per storefront assigned in turn over the 14 original cuisines (the ones Test 3 used; concept label =
the product's label, e.g. "Korean"). Location text = the product's area name for the storefront.

## Arms (same model, prompt, effort and length as Test 3: blind_test._brief, GPT-6 Astra)

- **A (Qloo):** background = Qloo evidence for the storefront's area, built exactly as in the product
  (positioning.evidence).
- **B (nothing):** no background.
- **C (city records):** background = the 40 nearest active restaurants from NYC inspection records within 500 m of
  the storefront, as "name (inspection category)", in the same background wording.

A brief that still mentions data sources after Test 3's three attempts drops its case from all comparisons; the
count is reported.

## Judge (primary)

Gemini 3.8 Flash (not an OpenAI model), blind to arms. Each case is judged twice with the three briefs in
different orders (a random order with seed 8, then the reverse). The judge sees the concept, the location and the
three briefs labelled 1 to 3, and returns JSON: a ranking best to worst for "which would help this founder more",
and 1 to 5 scores on four criteria:
- Specificity: names real brands, artists, venues or aesthetics rather than generic claims ("young professionals
  like coffee").
- Grounding: what it says about the people fits this particular place.
- Distinctiveness: a different neighbourhood would get a different brief.
- Actionability: a founder could act on it.

## Primary statistic and decision bands

For each case, a = share of the two judgements ranking A above C (0, 0.5 or 1). Statistic: mean of a over cases;
95% interval from 2,000 bootstrap resamples of cases (seed 0).
- **Lower bound above 0.5: A beats C.** Qloo adds something city records do not; the rebuild goes ahead with Qloo
  at the centre.
- **Interval contains 0.5: no difference shown.** Qloo is not shown to add beyond city records; no rebuild; the
  product stays the honest hybrid.
- **Upper bound below 0.5: C beats A.** A model given nearby businesses positions better than one given Qloo; this
  goes at the top of the audit.

## Reported, not decisive

A vs B and C vs B on the same statistic; mean rubric scores per arm; how often the two orders disagree (position
bias); named businesses per brief and how many trace to a source (positioning.verify).

## Limitations

An LLM judge, not founders. 30 cases. Arm C's list includes the concept's own competitors, which a real founder
would also know. Qloo evidence is a 2026 snapshot.
