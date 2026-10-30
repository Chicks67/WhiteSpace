# Test 23: does Qloo know which comedians share a crowd? Pre-registered protocol

Registered 2026-10-14, before any code for this test was written and before any bill in its sample was scored.
The git commit adding this file is the timestamp.

## Why

A candidate product ("Kings", IDEAS.md): find groups of acts whose fans are the same people and that nobody has put
on one bill, as the package comedy tours and themed festivals did by instinct. It rests on one thing: that Qloo's
score between two comedians says something true about who shares a crowd. This test checks that against two outside
records: who is on a bill together today, and who toured together in the famous packages.

## What had been seen before this file

- A probe on Oct 14 (IDEAS.md): 21 well-known comics in three groups we named ourselves; a same-group pair
  outscored another pair 0.865 of the time. That probe included three of the four Original Kings of Comedy and
  two comics from other tours in Part B below, so Part B is not blind for those pairs; it is reported with and
  without them.
- A count of Ticketmaster comedy events (weekly windows from July 1): 69 headliners with a bill of 2 to 4 named
  acts, many of them venues or festivals listed as acts. No Qloo call was made for any of them.

## Part A: current bills (Ticketmaster)

**Sample.** US events, classification "comedy", on sale 2026-07-01 to 2026-10-13, fetched in daily windows; events
with 2 to 4 named attractions; the first is the headliner, the rest are bill-mates. Headliners are shuffled (seed
23). A headliner is kept when Qloo's person search returns it under the same name, Qloo returns similar people for
it, and at least one bill-mate is found in Qloo under the same name. Stop at 40 kept or 200 tried. Fewer than 20
kept: "too few comedy bills to say", and no reading below is used.

**Task.** As in Test 15. For each headliner a shortlist: its real bill-mates plus up to 40 others drawn (seeded by
headliner) from the bill-mates of the other kept headliners, shuffled. Each arm scores every act on the shortlist;
the measure is the AUC of real bill-mates over the others, per headliner.

**Arms.**
- Qloo: its person-to-person affinity from the headliner (an act with no score ranks last).
- Fame: Qloo's popularity of the act.
- Model alone (GPT-6 Astra, CometAPI): "You know stand-up comedy touring in the United States. For one headliner
  you get a numbered list of other acts. Score each from 0 to 100 for how likely it is to be on the same bill as
  that headliner, as support, opener or co-headliner. Use the whole range."
- Model with Qloo: the same, plus "Beside each act is its fan-overlap score with the headliner from a taste
  database (0 to 1, or 'none' if the database has no score); use it as you see fit."

**Analysis.** Means over headliners with 95% intervals from 2,000 bootstrap resamples of headliners (seed 0).

**Readings (fixed).**
1. Qloo's AUC has a lower bound above 0.5 and Qloo minus fame has a lower bound above 0: "Qloo's score ranks the
   comics who really share a bill above others, and it is not just fame." Otherwise: "not shown".
2. Model with Qloo minus model alone: lower bound above 0, "the model picked real bill-mates better with Qloo's
   scores"; upper bound below 0, "worse"; otherwise "no different".
3. Qloo minus model alone, read the same way, reported beside the others.

## Part B: the famous package tours

**Tours and members (fixed here, from public record).**
- The Original Kings of Comedy: Steve Harvey, D.L. Hughley, Cedric the Entertainer, Bernie Mac.
- The Queens of Comedy: Laura Hayes, Adele Givens, Sommore, Mo'Nique.
- Blue Collar Comedy Tour: Jeff Foxworthy, Bill Engvall, Ron White, Larry the Cable Guy.
- The Original Latin Kings of Comedy: Paul Rodriguez, Cheech Marin, George Lopez, Joey Medina, Alex Reymundo.
- Axis of Evil Comedy Tour: Ahmed Ahmed, Maz Jobrani, Aron Kader, Dean Obeidallah.
- The Comedians of Comedy: Patton Oswalt, Brian Posehn, Maria Bamford, Zach Galifianakis.
- The Kims of Comedy: Bobby Lee, Ken Jeong, Kevin Shea, Steve Byrne.
- Wild West Comedy Show: John Caparulo, Bret Ernst, Sebastian Maniscalco (Ahmed Ahmed also toured with it and is
  counted in both).

**Measure.** Every comic found in Qloo's person search under the same name; Qloo's score for every pair (mean of
the two directions). The chance that a pair who toured together outscores a pair who did not (an AUC over pairs),
with a 95% interval from 2,000 bootstrap resamples of comics (seed 0). Reported for all pairs and again leaving out
pairs among the comics in the Oct 14 probe.

**Reading (fixed).** Lower bound above 0.5 on the pairs not in the probe: "with no labels, Qloo's scores put real
tour-mates together". Otherwise "not shown".

## Limitations, stated before the result

A bill is a booking decision: agents, managers and price matter as much as shared fans. The other acts on a
shortlist are bill-mates from other comedy bills, so the task is choosing among working comics, not among all
people. Both sides of a pair must be in Qloo by name, which leaves out the comics Qloo does not hold and favours
Qloo. The model has read about every tour in Part B, so Part B has no model arm: it shows what the graph holds, not
that Qloo knows more than a model. The package tours were built around audiences defined by background, so labels
such as ethnicity or region would also recover them; Part B cannot tell Qloo's score from those labels. Neither part
tests whether a group nobody has toured would sell tickets.
