# Test 9: can a different use of Qloo improve the brief? Development plan, then a confirmatory test

Registered 2026-10-12, before any Test 9 code, brief or judgement. The git commit adding this file is the timestamp.
Tests 3 and 8 are unchanged. Test 3 is still pending and nothing here reads its key.

## Why

Test 8 found that briefs written with Qloo evidence lost to briefs written with a list of nearby businesses and to
briefs with no background. Every Qloo call in the product and in Tests 1 to 8 used a location signal (heatmaps, or
what a map point over-indexes on). Two parts of Qloo have never been tested here: entity-to-entity affinity, and
the attributes Qloo holds for each place (price level, rating, opening hours, review keywords, descriptions).

The team wants to find out whether some other use of Qloo makes the brief better. Trying several variants and
reporting the best one on the same cases would be a forking-paths error. So the work is split in two parts.

## What was seen before this file (exploratory, no claims)

- Oct 12: 24 Qloo calls on five seed restaurants (Thai Diner, Win Son, Peppa's Jerk Chicken, Lucali, Jackson
  Diner; none is a Test 3 or Test 8 case). Entity search resolved all five. Places with affinity to a destination
  restaurant looked like a recognisable scene; for neighbourhood spots they were mostly whatever is nearby, chains
  included. Artists and brands differed clearly between seeds.
- Oct 12: finished Test 8 data read back. The Qloo arm was ranked last in 44 of 60 judgements. Its evidence for
  Jamaica, Queens included Weightwatchers, Montauk Brewing Co., NYC Ferry and StreetEasy; several of the same
  brands recurred for Midtown.
- Oct 12: three place queries around Test 8 case 3 (Japanese, Jamaica). Place records carry price level, rating,
  hours, review keywords with counts and written descriptions.

## Part A: development (exploratory)

- Cases: the 30 Test 8 cases only (test8_cases.json). Their results are already known, so nothing found on them
  is evidence.
- Arms: any new way of building background from Qloo may be tried, changed and dropped. Existing Test 8 briefs
  for arms B (nothing) and C (nearby businesses from city records) are reused as they are.
- Brief call: blind_test._brief, unchanged (same instructions, model, effort, length, leak rule). Only the
  background text differs between arms.
- Judge: Test 8's judge, unchanged (same prompt, gemini-3.8-flash, three briefs, two orders).
- Reporting: every variant tried is listed in PROJECT_LOG.md with its numbers, including the ones dropped. All of
  it is labelled exploratory. No Part A number is ever presented as a test result.
- Stop: when one variant is chosen to freeze, or when the team decides none is worth confirming.

## Part B: confirmatory test (run once)

Fixed now:

- Cases are fresh: vacant storefronts sampled with seed 9, one per block, excluding any block within 1,000 m of a
  Test 3 location or a Test 8 case. No Qloo call, brief or judgement is made for any Part B case until Part B's
  details are committed.
- One frozen Qloo arm (Q), chosen in Part A, against B (nothing) and C (nearby businesses from city records).
  Same brief call and same judge as Test 8.
- Statistic as in Test 8: for each case, the share of the two judgements ranking Q above the other arm; mean over
  cases; 95% interval from 2,000 bootstrap resamples of cases (seed 0).
- Decision rule: "Qloo improves the brief" is claimed only if the lower bound is above 0.5 against C and against
  B. If either interval contains 0.5, no improvement is claimed. If either upper bound is below 0.5, Q is reported
  as worse than that arm.
- It runs once. No second sample, no change of arm after the first Part B judgement.

Fixed later, in a separate commit made before any Part B case is sampled: the exact definition of arm Q (queries,
filters, background wording), the number of cases, and anything else the frozen arm needs.

## Amendment 1 (2026-10-12, afternoon)

Committed before any result for arms C+, En or Em was read, and before any Part B case was sampled.

What had been seen when this was written (exploratory, 14 cases): variant D (Qloo place data offered as a list)
0.429 over C and 0.464 over B; variant E (the same data as stated findings, under an opening line telling the
writer to state the facts and name the businesses) 0.964 over C and 0.929 over B. D and E use the same data, so
the jump is a wording effect until shown otherwise. A reviewer (DeepSeek) asked for the points below.

1. Control arm C+: Test 8's city-records list (arm C) under E's opening line, word for word. No Qloo.
2. Part B's comparator changes from C to C+. The decision rule becomes: "Qloo improves the brief" is claimed only
   if the lower bound is above 0.5 against C+ and against B. Plain C is not a Part B arm. This is stricter than
   the first version.
3. Two ablations of E on the 30 development cases, same opening line:
   - En: E's Qloo-selected places with name and cuisine only. No price, hours, rating or review keywords.
   - Em: E's place attributes, with the neighbours within 800 m taken in Qloo's default order, without the
     taste signal (signal.interests.tags).
   Each is judged against B and C+ with the usual statistic. "Above C+" means the lower bound of the 95%
   interval is above 0.5; anything else is "not shown above".
4. How En and Em will be read, fixed now:
   - En above C+, Em not: the taste-graph selection is what helps.
   - Em above C+, En not: the place attributes are what help; the taste graph adds little.
   - Both above C+: both contribute.
   - Neither above C+: E's gain is the opening line; Qloo data adds nothing shown.
   If E itself is not above C+, the same conclusion as the last line holds whatever En and Em show.
5. Not done: a control giving C+ hours, prices and ratings from a source other than Qloo. Without it, En and Em
   separate selection from attributes only as far as Qloo's own data allows, and any write-up says so.
6. These readings are still Part A: exploratory, on cases with known earlier results. Only Part B is a test.

## Amendment 2 (2026-10-12, evening)

Committed before any brief exists for arms Q, Q0, Qn or Qm, and before any Part B case was sampled.

What had been seen when this was written: Amendment 1's numbers; E over C 0.891 and over B 0.87 on 23 cases; one
case of E against C+ (0.5), from the run that stopped when the model account ran out of credit; no En or Em
brief; Test 10's result (PROJECT_LOG.md, section 25).

1. Test 10 put Qloo's competitor list under 50% coverage and under 90% existence. Variant E states absence
   claims and names places from Qloo's list alone, so it cannot ship. E is retired. En and Em, its ablations, are
   not run.
2. The candidate is Q (test9_dev.arm_Q): city inspection records define the competitor set (the 15 nearest
   same-category restaurants within 1.5 km), Qloo price, Friday closing time and review keywords are attached
   where a place matches by Test 10's rule, Qloo-tagged places the city files under another category are added,
   aggregates are worded "among the N with details", the opening line forbids absence claims, and a neighbour
   within 800 m is named only if it has an active city record.
3. Q holds more city-record content than C+ (same-category competitors to 1.5 km against any restaurant within
   500 m), so C+ alone cannot isolate Qloo. New control Q0: Q's city-record competitor line with names only, and
   the 10 nearest other restaurants within 800 m from city records with their inspection category. No Qloo call
   contributes to it. C+ stays as registered.
4. Ablations of Q, same opening line as Q0:
   - Qn: Qloo decides which places are listed (the extra Qloo-tagged competitors and the taste-ranked neighbours),
     but only names and categories are given. No price, hours or review keywords.
   - Qm: Q's attributes, with the neighbours taken in Qloo's default order, without the taste signal.
5. Part A readings, on the 30 development cases, each arm judged with B and one control, two orders. "Above"
   means the lower bound of the 95% interval is above 0.5.
   - Go or stop: Part B runs only if Q is above C+ and above Q0. Otherwise the work stops here, the conclusion is
     "Qloo is not shown to improve the brief over city records", and it is reported with the numbers. Compliance
     with Test 10 is not offered as a reason; a brief that needed false claims to win did not win.
   - Qn above Q0, Qm not: Qloo's choice of places is what helps.
   - Qm above Q0, Qn not: the place attributes are what help; the taste graph adds little.
   - Both above Q0: both contribute. Neither above Q0 while Q is: the gain needs both together.
6. Part B, if it runs: arms Q, Q0, C+ and B on the fresh cases. Each case is judged as two triples, (Q, B, C+) and
   (Q, B, Q0), two orders each. "Qloo improves the brief" is claimed only if the lower bound is above 0.5 against
   C+, against Q0 and against B (B from the first triple). If any interval contains 0.5, no improvement is
   claimed. If any upper bound is below 0.5, Q is reported as worse than that arm.
7. Optional human check, only if two raters from outside the team are found before Part B's judgements are read:
   the first 10 Part B cases by case number, Q against Q0, one question (which brief would you hand the founder),
   order shuffled with seed 9. Reported beside the LLM judge and never pooled with it. Team members do not rate.
8. Still Part A until Part B's remaining details (number of cases) are committed. Only Part B is a test.

## Amendment 3 (2026-10-12, night): wording of the Part A outcomes

Committed before any Q, Qn or Qm judgement was read. All 30 Q against C+ judgements and 29 of 30 Q against Q0
judgements existed in the state file, unread. Amendment 2's rules are unchanged; this fixes the sentences the
write-up will use, so they are not softened or hardened by the numbers. A reviewer (DeepSeek) drafted them; three
were corrected to match Amendment 2 before commit.

- **Q above C+ and above Q0.** "On 30 development cases, a blind LLM judge preferred briefs built with Qloo's place
  data over both controls. The gain holds when the city-record content is the same (Q against Q0), so it comes
  from Qloo and not from a longer competitor list. These are development cases with known earlier results, so
  this is not evidence yet. Part B tests it once on fresh storefronts, and nothing is claimed beyond what Part B
  shows."
- **Q above Q0 only.** "Against the same city-record content, the judge preferred the brief with Qloo's data. It
  did not prefer it to the plain city list under the same instructions. By the rule we fixed, Qloo is not shown
  to improve the brief over city records, and Part B did not run. We report both numbers."
- **Q above C+ only.** "The judge preferred the Qloo brief to the plain city list, but not to the same brief with
  Qloo removed. So the gain over the city list is not shown to come from Qloo; it may come from the fuller
  competitor list. By the rule we fixed, Qloo is not shown to improve the brief over city records, and Part B did
  not run."
- **Neither.** "Neither comparison shows a gain from Qloo. The brief ships written from city records. The Qloo
  panels stay as labelled descriptions, each under the result of its own test."

No sentence counts this as "the ninth null" or similar: the earlier tests asked different questions (Tests 6, 10
and 11 were not about beating an alternative), and the write-up lists each with its own result.

## Limitations

An LLM judge, not founders. The judge and the brief writer are both language models and may share tastes. Part A
uses cases whose earlier results are known. Qloo data is a 2026 snapshot.
