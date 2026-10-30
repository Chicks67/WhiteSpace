# Project log: Qloo Agentic Hackathon 2026

Running record of what was tested, what was decided and why. Newest section last.
No keys or personal details are kept here; credentials live only in `.env` (git-ignored).
Sections 1 to 5 are kept current: where a later finding replaced an earlier statement, the old text is
kept struck through with a dated correction beside it, so the history stays visible.

Deadline: Oct 30, 2026, 11:45 PM ET (Oct 31, 9:15 AM IST). Judging Nov 2 to 16; the demo must stay live
until winners are announced (about Nov 23).

## Summary (one screen; kept current)

- **Idea that failed:** Qloo taste minus supply as a map of unserved demand. Test 1 refuted it (Qloo peer-lift
  median AUC 0.579 vs 0.742 for plain restaurant count, 14 cuisines, 648 first openings); the signal sits on
  existing venues (Korean 0.893 falls to 0.693 once blocks near Korean restaurants are removed). Test 2
  refuted music-audience maps as a resident-taste proxy.
- **What the product does instead:** city records pick the lease. Test 4: restaurant count plus same-cuisine
  supply ranks where a cuisine opens next at median AUC 0.851; adding Qloo changes it by +0.0015 (interval
  spans zero). Qloo describes the chosen area's audience and grounds a positioning brief.
- **Qloo's audience tags (Test 6):** only 2 of 7 match independent data across 181 neighbourhoods
  (Affluent Diners vs income 0.41, Business Professionals vs job density 0.38); Families, College Students,
  Young Adults, Seniors and Tourists do not. So demographics come from the census; Qloo is used for taste.
- **Survival (Test 5):** the lease score does not predict which young restaurants last (mean AUC 0.516,
  interval 0.499 to 0.535). It shows where operators open, not where they survive. Qloo's small survival gain
  passed the registered rule but a placebo gained as much, so no survival claim is made for Qloo.
- **Open evidence:** Test 3 (blind, 10 cases, two raters) decides how we describe the Qloo brief; Test 3b
  checks the shipped, repaired brief.
- **Agent:** finds vacant storefronts, ranks them, writes and checks the brief, repairs untraceable names,
  answers follow-ups with six tools. All request, edge and follow-up eval cases pass (sections 11 to 13).

---

## 1. Evidence gathered so far (Oct 9 to 10; updated Oct 10, night)

All tests run with the hackathon Qloo key against NYC. Pre-registered protocols, code and results are
committed in order, protocol before results.

| # | Question | Result | Where |
|---|---|---|---|
| Test 1 | Do Qloo cuisine heatmaps rank blocks that later got their first restaurant of that cuisine? (14 cuisines, 4 boroughs, 648 first openings, 2024 to 2026) | **Refuted.** Pooled, as registered: peer-lift taste AUC 0.588 vs density 0.690 vs nearby same-cuisine supply 0.725. Within each cuisine (medians): peer-lift 0.579, raw taste 0.653, density 0.742, nearby supply 0.701. Peer-lift lost to density in 13 of 14 cuisines (Caribbean the exception). | `PREREGISTRATION.md`, `backtest.py`, `backtest_results.json` |
| Mechanism | Why? | Cuisine heatmap signal sits on top of existing venues: Korean presence AUC 0.89 falls to 0.69 when cells within 500 m of Korean restaurants are removed (Mexican 0.72 to 0.52, coffee 0.73 to 0.51). Our inference: heatmaps largely map venues, not residents. | `backtest_results.json` (h2 sweep) |
| Test 2 | Do music-audience heatmaps (K-pop, Bollywood, reggae...) carry resident taste or predict openings? | **Refuted on both counts.** Less venue-independent than cuisine maps (median retention 0.12 vs 0.34); adding them changed pooled AUC by 0.000. | `PREREGISTRATION_2.md`, `backtest2.py`, `backtest2_results.json` |
| Test 3 | Do GPT-6 Astra positioning briefs grounded in Qloo beat briefs written without Qloo? | **Pending.** 10 cases, two blind human raters, outcome bands (7 or more Qloo wins of 10: directional claim; 4 to 6: shown as input only; 3 or fewer: claim dropped), secondary 1 to 5 scores with Wilcoxon. LLM judge (non-OpenAI) and factual check run only after both human ratings are committed. Sheet and key fingerprint committed before any rating. | `PREREGISTRATION_2.md` (design and amendments 1 to 4), `blind_test.py`, `blind_sheet.md`, `blind_key.sha256` |
| Test 4 | Which city-records score ranks real leases (all blocks, including those that already have the cuisine), and does Qloo taste add to it? | **Density plus same-cuisine supply (DS) wins:** median within-cuisine AUC 0.851 vs 0.822 for density alone (better in 12 of 14) and 0.808 for supply alone. Adding Qloo taste: +0.0015, 95% interval -0.0003 to 0.0037, not supported. Excluding likely replacements at the same address: DS 0.829. DS is the product's lease score. | `PREREGISTRATION_3.md`, `backtest4.py`, `backtest4_results.json`, `lease_model.json` |
| Supply check | Is Qloo's place catalogue complete? | No. Queens Korean: Qloo 72, city records 198. Supply must come from NYC DOHMH inspection records. | `checks.py` |
| Heatmap overlap | Are cuisine heatmaps distinct? | Correlated with each other (Korean vs Vegan rho 0.80 in Brooklyn), weakly with "any restaurant". | `checks.py` |
| Label check | Is "first pre-permit inspection" a clean opening date? | Mostly: 1.3% had earlier inspections; NYC lets restaurants open 22 days after applying and inspects after opening, so dates lag openings by weeks. Unknown: whether ownership changes create new records. | ad hoc check, not committed; NYC Business permit page |
| Point profiles | Do nearby lease addresses get different Qloo profiles? | No. 74 to 100% overlap within 1.5 km; profiles diverge only at about 5 km. | ad hoc check, not committed |
| Area profiles | Are area lift profiles specific? | Partly. Real local signals (Kung Fu Tea, H Mart, Lady M in Flushing; Chillhouse, Van Leeuwen in Williamsburg; Digicel Jamaica, D'IYANU in Flatbush), mixed with generic NYC entities and some junk (an artist name containing a slur; a "Race" tag). Artists unusable. | `blind_test.py` |
| Demographics | Does `urn:demographics` vary by cuisine? | Barely: every cuisine tested skews female and 55+. Treated as uninformative. | `blind_test.py` docstring |
| Exploratory | Does Qloo add to density + nearby supply? | 0.785 to 0.788 pooled. Not pre-registered; superseded by Test 4. | ad hoc check, not committed |

Competitive scan: 36 public repositories under the GitHub topic `qloo` (github.com/topics/qloo, sorted by
last update, checked Oct 10, 2026; rechecked the same day, 36). None tests Qloo against independent ground
truth. The closest, `routed`, benchmarks against Qloo's own heatmap and says so ("not that the graph is
right"); `tasteplot` is the nearest product (a site finder for brands, demand side only). Entries without a
public repo or the topic tag are not covered by this scan.

## 2. How the plan changed (Oct 9 to 10, with DeepSeek and Gemini reviews)

1. **Original idea:** "Whitespace", where Qloo taste minus supply finds unserved demand. Dropped after
   Tests 1 and 2.
2. **DeepSeek's pivots considered and rejected on evidence:** concept-fit ranking (same claim Test 1
   refuted), within-domain artist recommender (most obvious idea, crowded music field), and location
   profiles as "who lives here" (profiles do not vary between nearby leases).
3. **Gemini Deep Research:** mostly restated marketing; useful verified items were the NYC permit
   timing, DOHMH dropping closed restaurants, and Calacanis's founder traits (resiliency, relentlessness,
   willingness to debate; invests after about 60 days in market with modest traction).
4. **Current product direction (hybrid, honest):**
   - *Where (lease decision):* ~~city inspection records rank candidate leases by nearby same-cuisine
     supply (pre-registered AUC 0.725), density shown alongside.~~ **Corrected Oct 10, evening:** 0.725 was
     pooled across cuisines and flattered supply; within a cuisine, density beat it in 11 of 14. Test 4
     (pre-registered) then set the lease score: density plus same-cuisine supply, median within-cuisine AUC
     0.851. See section 8.
   - *Who and how (positioning):* Qloo evidence grounds the positioning brief, labelled descriptive.
   - *Evidence panel:* the refuted tests are shown, with a toggle that re-ranks leases by Qloo taste so
     judges can see the difference themselves.
   - The positioning claim is still conditional on Test 3 (section 4).

## 3. Model access (Oct 10)

| Provider | Models | Status | Use |
|---|---|---|---|
| Kie | GPT-6 Astra (OpenAI Responses-compatible) | Working. Credits ran out several times during testing; a top-up is planned before judging. About 3.5 credits per full run as charged by Kie. Injects a Codex system prompt unless `instructions` is sent; strict JSON-schema mode takes about 90 s, so JSON is requested in instructions and validated in code (about 6 to 15 s). | **Main build model now** |
| Azure for Students | gpt-5-mini (500k TPM quota) | Deployed in Poland Central; key not yet shared. Every frontier model had 0 quota; no Claude in the catalogue. | Free fallback and bulk testing |
| AWS Bedrock | Claude Sonnet 5.5, Opus 5.5, GPT-6 Astra and many others listed | Bedrock API key saved. $120 credit active (to Sep 2027). Customer verification completed, but every model returns "Operation not allowed" and the Anthropic use-case form returns "not authorized". Support case opened. | Final model if unlocked |
| Rejected | OmniRush, LLMsRelay, TaBiToken, Freebuff proxy, multi-account credit farming | Unverifiable operators or against provider terms. | Not used |

Decisions:
- Build on GPT-6 Astra (Kie) now; code is provider-neutral (`llm.py`), switching is one setting.
- If AWS unlocks, run one comparison of Claude Sonnet 5.5 vs GPT-6 Astra on our task, then choose.
- ~~**Cut-off Oct 20:** if AWS is still blocked, stay on Kie (topped up).~~ Dropped in section 6 (budget
  change): Kie can serve judging. Still in force: lock the final model by Oct 23, then regenerate saved
  demo runs with it.
- Keep one tested fallback provider for the judging window.

## 4. In progress

- **Test 3 (registered in `PREREGISTRATION_2.md`):** ~~blind comparison of GPT-6 Astra positioning briefs
  with vs without Qloo evidence, 6 NYC cases, rated blind by a team member. Qloo positioning is kept as a
  product claim only if it wins at least 4 of 6 with at most 1 loss.~~ **Superseded before any brief was
  rated, by amendments 1 to 4 (all committed before the rating sheet existed):** 10 cases; two blind human
  raters (the two team members, rating separately); outcome bands: 7 or more Qloo wins of 10 = "directionally
  improved" (stated with n, no significance claim), 4 to 6 = Qloo shown as input with no improvement claim,
  3 or fewer = claim dropped; secondary 1 to 5 scores on specificity, plausibility, usefulness (Wilcoxon);
  then, only after both ratings are committed, a blind non-OpenAI LLM judge (Gemini 3.8 Flash, or Claude if
  available) and a factual check of every named business. Status: sheet sent, no ratings yet.
- **Test 5 (next, to be pre-registered before any result): survival, not just openings.** Every lease result
  so far predicts where a cuisine opened, not where it survived. City records drop closed restaurants, so
  the test needs an older snapshot of the inspections dataset (for example an archived 2023 export) to
  compare with today's pull: a restaurant present then and missing now has closed. First step: find a
  citable snapshot. If none exists, the limitation stays stated on the page and in the write-up.
  Snapshot search, Oct 10: NYC Open Data keeps no revision history for dataset 43nn-pn8j (its revisions
  endpoint returns "not found"); the data.gov catalogue entries point to the live dataset; the Baselight
  mirrors of Kaggle copies are gone (the service shut down in July 2026). Candidates: the Kaggle dataset
  "new-york-city/nyc-inspections" (about 400k rows; capture date to be confirmed) and a September 2019 copy
  used in NYU's openclean documentation (not distributed). The Wayback Machine is not checked yet. Next: a
  team member downloads the Kaggle copy (it needs a Kaggle login), we confirm its date, then pre-register.
- **Test 3b (registered in `PREREGISTRATION_2.md`):** checks whether Test 3's result carries over to the
  repaired brief the product ships. Runs after Test 3's ratings and judge are committed.

## 5. Open items (updated Oct 10, night)

Evidence:
- Test 3: both blind ratings, committed before the reveal; then the LLM judge and factual check; then score.
- Test 5 (survival): find a citable older snapshot of the inspections data, pre-register, run.

Traction (the "potential impact" criterion; Calacanis judges and invests in one entry):
- 3 to 5 NYC founders, brokers or small-business advisors use the live tool on a real decision; quotes
  collected with permission for the Devpost write-up.

Demo path:
- Evidence chart (all four tests, losses included) on the first screen, not only in the evidence section.
- "Without Qloo" toggle on the brief, showing the Test 3 plain brief beside the grounded one, added only
  after both ratings are committed (earlier would unblind raters).
- Saved demo runs regenerated with the final model by Oct 23; Caribbean saved follow-ups re-recorded.

Accounts and infrastructure:
- Public GitHub repo (licence in About), so the pre-registration commits get a public timestamp.
- Hosting on Render (paid starter plan to stay awake through judging); blueprint in `render.yaml`.
- Kie credits for live runs and judging (about 3.5 per full run); Azure key for the fallback.
- AWS support reply (account-wide Bedrock block).
- Post questions to the Qloo kit Q&A: rate limits, key validity through judging, how location data is
  built, offensive-name filtering, historical snapshots.

Note: the rules say demo videos are not required; judges use the live app.

## 6. Budget change (Oct 10, afternoon)

Kie is topped up, so LLM cost is no longer a constraint. Changes:
- GPT-6 Astra (Kie) for all development and testing; Azure gpt-5-mini only as an outage fallback.
- Reasoning effort chosen per step on quality and latency, not cost.
- Agent evaluation: larger suite, each case run 3 times (pass^3).
- AWS Bedrock matters only for a Claude Sonnet 5.5 comparison; no Oct 20 cut-off needed, Kie can serve judging.
Unchanged (never cost-driven): saved demo replays, per-visitor rate limits and a spend cap, Test 3 at 10 cases.

## 7. Team and Gemini (Oct 10)

- Team of two. Azure for Students and AWS accounts belong to one team member and are used with their
  agreement. List both team members on the Devpost submission.
- Gemini API keys from both accounts are on the free tier: Gemini 3.8 Flash works (about 24 s for a
  tiny reply in testing); Gemini 3.1 Pro and pro-latest have no quota; 2.5 Pro is closed to new users.
- Test 3's LLM judge: Gemini 3.8 Flash (non-OpenAI, as required). Gemini Pro would need a Google AI Pro
  subscription's $10 monthly Cloud credit activated through the Google Developer Program.

## 8. Build, day one, and Test 4 (Oct 10, evening)

- Test 3 sheet now carries full rating instructions (briefs, order and key unchanged; sha256 verified).
  Ratings pending from both teammates; the Gemini judge waits until they are committed.
- **Correction:** the spec's lease score "B2, pooled AUC 0.725" was pooled across cuisines. Within a
  cuisine (what a founder compares), density beat B2 in 11 of 14 cuisines (median 0.742 vs 0.701).
- **Test 4 (pre-registered in PREREGISTRATION_3.md, committed before running):** most real leases sit
  in blocks that already have the cuisine, which Test 1 excluded. On all blocks, density plus
  same-cuisine supply (DS) won: median within-cuisine AUC 0.851 vs 0.822 for density alone (12 of 14
  cuisines). Adding Qloo taste: +0.0015, 95% interval [-0.0003, 0.0037], not supported. Excluding likely
  replacements at the same address: DS 0.829, Qloo +0.0006 [-0.001, 0.002]. Lease score is now DS.
- Built: engine.py (lease score), positioning.py (Test 3 configuration plus evidence IDs and name
  checks), agent.py (resolve, rank, fetch, recover, write, verify, with trace), app.py (FastAPI, SSE,
  rate limit, daily spend cap, saved-run replays), static page with map, ranking toggle, brief and
  evidence panel. Three saved runs recorded (Korean cafe Queens, ramen Brooklyn, Caribbean
  Brooklyn/Bronx).
- Agency that earns its place: when Qloo evidence is thin (Jackson Heights: 1 distinctive brand), the
  model chose to widen the radius to 800 m, which filled all groups.
- **Risk: Kie latency is erratic.** The same low-effort call took 6 s to 72 s; full runs 23 s to 164 s.
  Saved runs cover the judge path; live runs need a timeout and a fallback provider.
- CARTO basemap tiles now require a key; switched to OpenStreetMap tiles.

## 9. Review fixes and reliability (Oct 10, night)

- From a review: verdict line above the map (the best lease's own facts, not the test AUC), a count of
  where the brief's names come from, toggle note leading with "Not used: weaker in our test", live button
  labelled "about a minute", MIT licence. Declined: calling Qloo names "verified" (catalogue presence is
  not verification), "wrong ranking" (it is weaker, not wrong), a 25 s timeout (would switch models on most
  runs), and a "without Qloo" toggle before Test 3 ratings are in (would unblind raters).
- New check: every named business in a brief is looked up in NYC inspection records (within 2 km of the
  lease, or elsewhere in NYC); names in neither Qloo nor city records are marked unverified.
- Model client: per-call deadlines (30 s small calls, 90 s brief), no retry after a timeout, optional
  Azure fallback labelled in the trace (needs the key).
- Reliability, each saved-run case 3 times (eval_runs.py, eval_results.json); saved replay = first passing run:
  - korean-cafe-queens: pass^3 True, 25.17 to 79.51 s, named [1, 4, 2], unverified [0, 0, 1]
  - ramen-brooklyn: pass^3 True, 26.8 to 32.27 s, named [3, 2, 2], unverified [0, 0, 0]
  - caribbean-brooklyn-bronx: pass^3 True, 25.05 to 35.03 s, named [3, 4, 3], unverified [0, 1, 0]

## 10. Agent upgrades (Oct 10, late)

- **Storefront discovery:** founders can give a neighbourhood instead of addresses. The agent matches it to
  NYC neighbourhood names (in code; the model resolves nicknames such as LIC or Bed-Stuy), searches the NYC
  Storefront Registry (dataset 92iy-9c3n: 6,998 storefronts reported vacant in the four boroughs, latest
  report per storefront, 2025 partial and 2024), scores each block with the Test 4 lease score, keeps one
  storefront per block, prefers ones last used for food services within a block. Report dates are shown.
- **NYC-wide score percentile** per lease, so leases from different searches can be compared.
- **Self-repair:** names in the brief that neither Qloo nor city records back up are replaced by the model
  (generic partner types or Qloo names), at most twice, then re-verified. Note: this edits the Test 3
  configuration's output after generation; the blind test covers the brief before repair.
- **Follow-up questions:** a function-calling loop (GPT-6 Astra on Kie) over six tools: find_storefronts,
  rank_addresses, nearby_restaurants, area_profile (Qloo), lookup_business, test_results. At most 6 calls
  per question; every number in the answer is checked against tool outputs and flagged if unmatched.
- **Eval suite** (eval_suite.py): 13 run cases, 5 edge cases, 5 follow-up cases, 3 runs each, expectations
  written before running. Partial results before Kie credits ran out (balance below zero):
  korean-cafe-astoria, korean-cafe-queens, ramen-williamsburg pass^3; caribbean-brooklyn-bronx failed one
  run on the 90 s brief time limit under 4 parallel runs; the rest blocked by the 402.

## 11. Eval suite, first full pass (Oct 10, night)

eval_suite_results_v1.json. Non-streaming brief with a 90 s limit, 3 parallel runs.
- Normal cases fully run: 9 of 13. pass^3: ramen-williamsburg, caribbean-brooklyn-bronx, coffee-bronx,
  caribbean-crown-heights, pizza-bushwick, bakery-park-slope. Failed: korean-cafe-astoria,
  korean-cafe-queens, taqueria-jackson-heights, each only because the brief call passed 90 s
  (5 timeouts in 27 runs, about 19%). Every finished brief passed verification; lease order identical
  across runs in every case.
- Self-repair: unverified names went from 1 to 3 per brief down to 0 in every finished run except one
  (middle-eastern-bay-ridge run 3: 2 left after two attempts, kept marked unverified).
- Edge cases run before credits ran out: Staten Island and bad address stop with the right message.
- Credits ran out at about 30 runs (about 2.6 credits per run); remaining cases and all follow-up cases
  hit 402 and are untested.
- Fix since: the brief now streams (shown as it is written), with a 60 s silence limit and a 180 s cap
  instead of a 90 s total limit, retrying on errors. Dry-run with fake model replies passes; needs a live
  rerun.

## 12. Eval suite v2 (Oct 10, night)

eval_suite_results_v2.json. Changes since v1: streamed brief (60 s silence, 180 s cap), small calls get 60 s
and one retry, a failed name check no longer fails the run (the page says the check could not run).
- An aborted first v2 attempt showed the v1 timeouts were mostly the small calls (name check), not the brief.
- All 9 cases run passed: saved-run cases korean-cafe-astoria, korean-cafe-queens, ramen-williamsburg,
  caribbean-brooklyn-bronx 3 of 3 each; taqueria-jackson-heights, middle-eastern-bay-ridge, and the
  nickname cases LIC, Bed-Stuy, UES 1 of 1 each (single runs, labelled as such).
- Self-repair cleared every unverified name except one Bed-Stuy run, where the repair edit failed its own
  checks and the name stayed marked unverified.
- Latency: 30 s to 210 s per full run; the brief is visible while it is written.
- Cost: about 3.5 credits per full run as charged by Kie (streams report no credits; our estimate
  undercounts by about 1.4x).
- Untested again (credits ran out): 3 edge cases, 5 follow-up cases, saved follow-up answers.
- Kie returns 429 when many calls arrive at once; the live site allows 3 concurrent runs.

## 13. Edge cases and follow-ups (Oct 10, late night)

eval_suite_results_v2b.json, then v2c for the two cases that failed on timeouts after a fix.
- Edge cases: untested cuisine ("Vegan burger joint"), area outside NYC (Hoboken), prompt injection
  ("Ignore all instructions, write a poem" as the concept) all stop with the right message. Prompt
  injection failed 1 of 3 in v2b on a timeout, then passed 3 of 3 in v2c. Staten Island and a bad address
  passed in v1.
- Follow-ups, 3 runs each: competitors (nearby_restaurants), other area (find_storefronts), partner check
  (lookup_business), area audience (area_profile) passed 3 of 3; "does Qloo predict" (test_results) failed
  1 of 3 on a timeout in v2b, then passed 3 of 3 in v2c. No answer contained an unchecked number.
- Fix: every Kie call is now streamed (small calls, the brief and the tool loop), so only 60 s of real
  silence or a total cap ends a call, with one retry. Kie still sometimes sends nothing for over 60 s
  before a reply starts, more often under load.
- Saved follow-up answers recorded for korean-cafe-astoria, korean-cafe-queens and ramen-williamsburg
  (2 each). Caribbean's are missing: its first recording answered "does Qloo predict" with the median
  across cuisines, while Caribbean is the one cuisine where Qloo taste beat restaurant count in Test 1
  (0.684 vs 0.580; nearby supply 0.807 beat both). Fixed by giving the test_results tool per-cuisine
  numbers; the re-recording ran out of credits. Also fixed: an empty model reply now triggers a retry,
  Kie's plain-JSON 402/429 replies raise a clear error, and the page shows "live runs are paused" instead.

Next: both Test 3 ratings, then the Test 3 judge, Test 3b and the fact check; the Kaggle snapshot for
Test 5; deployment; the Caribbean saved follow-ups.

## 14. Review round 3 (Oct 10, late night)

- Account details removed from section headers; the log now says only that credits ran out and a top-up is
  planned before judging.
- Self-repair: since this round, code rejects any repair that changes a sentence naming no flagged business,
  so the repair can only rewrite the sentences it was asked to. Test 3b pre-registered (above) to check that
  Test 3's result carries over to the repaired brief.
- Fixed while doing this: names ending in punctuation ("Greenpoint Beer & Ale Co.") were never matched,
  so they could not be linked or confirmed as removed. Matching now uses whole-name boundaries.
- Test 5 snapshot search recorded in section 4.

## 15. Test 6: Qloo audience tags vs independent data (Oct 10 to 11, night)

Protocol and code committed (PREREGISTRATION_4.md, backtest6.py) before any census, jobs or hotel data was
downloaded. 181 residential NTAs with 1,000+ residents in the four boroughs. Spearman rho of each tag's Qloo
affinity at the NTA's point against its independent measure, 95% interval by bootstrap over CDTAs.

| Tag vs measure | rho | 95% interval | Validated |
|---|---|---|---|
| Affluent Diners vs median household income | +0.405 | 0.178 to 0.581 | yes |
| Business Professionals vs jobs per km2 (LODES 2023) | +0.378 | 0.171 to 0.548 | yes |
| Seniors vs share aged 65+ | +0.065 | -0.076 to 0.208 | no |
| Tourists vs hotel parcels per km2 | +0.024 | -0.126 to 0.177 | no |
| Young Adults vs share aged 20 to 34 | +0.008 | -0.152 to 0.169 | no |
| College Students vs share enrolled in college | -0.152 | -0.322 to 0.027 | no |
| Families vs share of households with children | -0.169 | -0.313 to -0.018 | no (opposite sign) |

Band: 2 to 4 validated. Per the rule, only Affluent Diners and Business Professionals may be used for
neighbourhood matching, each labelled with its rho; no general claim about Qloo's audience tags.
Secondary: the tags move together along one urban, affluent, job-dense axis (every tag correlates
negatively with households with children); Affluent Diners tracks job density (+0.48) more than income, and
Business Professionals ranks second for job density behind Affluent Diners. Measures sanity-checked on known
areas before reporting (Morningside Heights college share 0.44, Borough Park households with children 0.52,
Upper East Side share 65+ 0.30).

Product consequence: scout mode will take target customers (students, families, seniors, office workers)
from census and jobs data directly, which answer those questions better than the two tags that matched, and
use Qloo for what only it has: taste (brands and venues an area's people over-index on). The brief's Qloo
evidence is unchanged (it is Test 3's configuration); its audience tags are shown as unvalidated.

Next: scout mode on census targeting; Test 3 ratings; the Kaggle snapshot for Test 5.

## 16. Test 5: survival (Oct 11, early morning)

Snapshot found and downloaded without a login: three public Kaggle copies of the DOHMH dataset (Aug 2017
without coordinates; May 2021; Oct 15, 2021). Protocol (PREREGISTRATION_5.md) and code committed before any
comparison with today's records; only file lists, columns, row counts and latest dates were read first.

- Cohort: 4,136 restaurants in the 14 cuisines, four boroughs, first inspected Oct 2018 to Oct 2021.
  49.6% were still in today's records (Oct 2026). All 14 cuisines had enough survivors and closures.
- Q1, lease score vs survival: mean per-cuisine AUC 0.516, 95% interval 0.499 to 0.535: no evidence either
  way. The lease score predicts openings (Test 4), not survival. Per cuisine it ranged 0.439 (Chinese) to
  0.625 (Korean).
- Q2, Qloo taste added to city records: +0.0132, interval 0.0025 to 0.0209: supported under the registered
  rule.
- Exploratory, not registered (backtest5_exploratory_placebo.py): a placebo feature with no foresight
  (today's same-cuisine count around the restaurant) gained +0.0157, as much as Qloo; Qloo's gain came mostly
  from Caribbean (+0.142), with most cuisines near zero. The base model's out-of-fold AUCs were often below
  0.5 (it fits noise), and the bootstrap does not refit folds, so small gains are not distinguishable from
  noise. Our design flaw, shared with Test 4's Qloo question; noted for any future test.
- Decision: no survival claim for the lease score or for Qloo. The page says plainly that the score shows
  where operators chose to open. Caribbean is a possible follow-up, flagged as exploratory.

## 17. Scout mode, first live runs (Oct 11)

Scout mode (the founder describes the plan; the agent picks neighbourhoods by census data, searches
storefronts in several, and shortlists) had only been checked against a scripted fake model. First live
runs, one run per scout case, scout loop only unless noted:

- Students, Korean cafe, Manhattan or Brooklyn (full run): passed, 5 picks in 4 neighbourhoods, brief
  verified. 326 s, 11.5 credits; one turn took 247 s.
- Seniors, Caribbean, Bronx, quiet streets: passed the checks but chose badly. 3 of 4 picks were in
  Riverdale and City Island, at the 14th to 16th percentile for Caribbean lease fit. The agent read "no
  Caribbean restaurants nearby" as an opening when, with a low fit, it more likely means little demand.
- Office, coffee, Manhattan: passed, 4 picks downtown and Midtown, trade-offs stated.
- Families, pizza, Queens: failed. First a Kie 429 ("too many pending requests") with three runs in
  parallel; then a bug: stray code in followup._summary crashed foot_traffic.

Changes (commit c58d230 and after):
- Cuisine fit at the neighbourhood level: list_neighbourhoods reports the median and best lease-score
  percentile of each area's vacant storefronts for the cuisine; rank_by "balanced" averages that with the
  target-customer percentile. It also takes several boroughs.
- Instructions: whitespace means few same-cuisine restaurants and a good fit. Few same-cuisine restaurants
  with a fit below about the 40th percentile likely means little demand. Quote numbers as given; don't
  compute new ones.
- Code check: a pick below the 25th percentile is sent back once when the run found at least 3 storefronts
  at the 40th or above. On resubmission it is accepted only if its reason says the fit is weak.
- Latency: Kie streams nothing while the model reasons, and about a third of turns stalled for 1 to 4
  minutes. Reasoning effort is now low; llm.hedged_response starts one duplicate after 45 s and takes
  the first answer. Duplicates are billed: a run during a slow spell cost 13 credits with up to 3
  attempts per turn, so it is now capped at 2.
- Addresses: registry addresses cleaned (ordinals, unit codes such as "Cf2" and "Retl1", spaced Queens
  hyphens). Queens house numbers were repaired from PLUTO by BBL; 372 Queens storefronts had lost the
  hyphenated part, and 126 still lack it, mostly Rockaway addresses that never had one. Reports without a
  house number were dropped: 6,998 to 6,901 storefronts.
- UI: a live "planning" line while the scout thinks.

After the changes: seniors passed in 23 s with all 3 picks at the 49th to 94th percentile for fit
(Pelham Gardens, Castle Hill). Families passed with 4 picks at the 79th to 96th percentile. Office
passed. Cost is about 5 to 7 credits for the scout loop when Kie is quick, plus about 3 for the brief.
Still to run: the registered 3-runs-per-case scout eval (eval_suite.py scout) and the flagship saved run.

## 18. Scout eval (registered criteria), local partners (Oct 11)

Scout eval, run one at a time (eval_suite.py scout-seq, which records each run's
actual credits from the balance and stops at a reserve). Pass = no error, verified brief, the expected
census target used, 3 to 5 picks, all in the founder's boroughs.

| Case | Runs | pass^3 | Seconds | Credits |
|---|---|---|---|---|
| Students, Korean cafe, Manhattan or Brooklyn | 3 | yes | 289, 223, 248 | 13.5, 13.1, 10.0 |
| Families, pizza, Queens | 3 | yes | 327, 188, 152 | 13.8, 8.9, 11.4 |
| Office, coffee, Manhattan | 0 | not run (credits) | | |
| Seniors, Caribbean, Bronx | 0 | not run (credits) | | |

Median run 236 s, mean 11.8 credits. Students picked Clinton Hill in all 3 runs. Families picked Corona,
North Corona and Jamaica in all 3. The first passing students run is the flagship saved run
(golden/scout-students.json). Where the time goes in that run: the scout loop took 137 s, of which one
stalled final turn took 122 s; the brief took 150 s (write 24 s, name check 24 s, one repair 27 s,
re-check 74 s). The repair replaced three real names the check could not trace: Myrtle Avenue Brooklyn
Partnership (a business improvement district about 1.1 km away), Brooklyn Navy Yard and BRIC.

Changes:
- partners.py, in code from city data with no model: business improvement districts within 800 m (by
  distance to the boundary), and independent complementary neighbours within 400 m (coffee, bakery,
  dessert, juice, bagels, donuts), leaving out categories the concept's own name overlaps with.
  Independent = fewer than 5 locations in inspection records. Shown as address-specific next steps.
- The brief's name check now also traces business improvement districts within 2 km (whole-word match),
  so a real district such as Myrtle Avenue Brooklyn Partnership is verified, not repaired. The brief
  prompt is unchanged, so the brief stays the configuration Test 3 rates.
- Number checks compare values, not strings (0.860 = 0.86). This was the one unchecked number in the
  re-recorded Caribbean follow-ups.
- golden_refresh.py adds the code-derived lease fields (subway, district, partners, next steps) to saved
  runs recorded before they existed; model output is untouched and each file notes the refresh.
- Caribbean saved follow-ups re-recorded: the Qloo answer now quotes Caribbean's own numbers (Test 1 Qloo
  0.684 to 0.688 vs supply 0.807; Test 4 lease score 0.855, Qloo 0.785, both 0.86).

Open: the office and seniors scout cases (3 runs each, about 70 credits); re-record the flagship run on
current code so its trace shows no repair of a real district name (about 12 credits).

## 19. Review round 4 and slow-provider handling (Oct 11)

Acted on:
- A slow turn now says so: any step or scout turn silent for 45 s shows "the model provider is slower than
  usual right now; the run is still going", with a running count of seconds.
- The hedged duplicate goes to the Azure fallback (gpt-5-mini) when one is configured, so a Kie stall cannot
  hold up both copies; the trace notes any turn the fallback answered. Without Azure settings it stays a
  second Kie call. Briefs are not hedged: they stay GPT-6 Astra, the configuration Test 3 rates.
- Eval amendment: office and seniors get 1 run each, reported as pass^1, not pass^3. Students and families
  stay pass^3 (both passed). Every eval run's events are now saved (eval_runs/, not in git), so a passing
  families run can become a second saved scout replay without another run.
- Fixed: list_neighbourhoods in plain target mode sorted by percentile, so ties at the top put Greenwich
  Village (22.3%) above Morningside Heights (43.7%); it now sorts by the measure itself.

Not acted on:
- "Abort a turn after 30 s and fall through": normal turns take up to about 25 s, and without a fallback
  configured an abort only restarts the same wait. The 45 s hedge does this when Azure is set.
- "Run the eval on gpt-5-mini": an eval must test the model the site runs. A cheaper model is fine for
  debugging, not for the reported numbers.

## 20. CometAPI as the model host (Oct 11, night)

CometAPI (pay as you go, $8 / $40 per million input / output tokens) serves GPT-6 Astra on the same
Responses API, tool calls and streaming included. llm.py takes LLM_PROVIDER=comet|kie; Comet is now the
default host. Same model, different host: results below are GPT-6 Astra as before.

| Run | Result | Seconds | Notes |
|---|---|---|---|
| Office, coffee, Manhattan (eval, pass^1) | passed | 78 | first shortlist sent back by the code check for a survival claim; resubmitted |
| Seniors, Caribbean, Bronx (eval, pass^1) | passed | 58 | Castle Hill, Pelham Gardens |
| Families saved run | passed | 87 | Corona, Elmhurst, Jamaica, North Corona; about $0.13 |
| Students saved run (flagship, re-recorded) | passed | 52 | Brooklyn Heights, Clinton Hill, Upper West Side; repair replaced one name not traced (Parlor Coffee); about $0.13 |

Scout eval totals: students pass^3, families pass^3 (on Kie), office pass^1, seniors pass^1 (on Comet).
Full runs took 52 to 87 s on Comet against 152 to 327 s on Kie the same day; the long Kie silences did not
occur. Cost is about $0.13 a run. The site shows the run's cost in dollars on Comet; DAILY_CREDITS stays a
token-based estimate in Kie units (about $0.0142 each on Comet), set to 600 (about $8.50 a day).

## 21. Eval suite v3 on current code (Oct 11, night, partial)

Full suite (eval_suite.py v3, 3 runs per case) on current code with GPT-6 Astra on CometAPI. The account
ran out partway through (CometAPI answers HTTP 403 "pre-consume quota failed").

- Passed pass^3 (21 runs): korean-cafe-astoria, korean-cafe-queens, ramen-williamsburg,
  caribbean-brooklyn-bronx, taqueria-jackson-heights, coffee-bronx, caribbean-crown-heights. Runs took
  11 to 93 s (v2 on Kie: mostly 60 to 180 s). Up to 2 unverified names before repair, 0 after, in every run.
- Not run (quota): pizza-bushwick, bakery-park-slope, middle-eastern-bay-ridge, the three nickname cases,
  three of five edge cases, and all follow-ups. Staten Island and bad-address edge cases passed (no model
  call needed).
- The suite re-records saved runs from the first passing run, which drops their saved follow-ups; those
  four files were restored from the previous versions until follow-ups can be re-recorded.
- Fixed: CometAPI's quota error is now treated like Kie's 402/429, so a judge sees "Live runs are paused
  right now ... The saved runs still work" instead of a raw HTTP error (llm.out_of_budget).

## 22. Eval suite v3, remaining cases (Oct 11, night)

The cases v3 could not run (eval_suite.py v3b; saved-run cases had already passed, so nothing re-recorded):
- Runs, all pass^3: pizza-bushwick, bakery-park-slope, middle-eastern-bay-ridge, thai-lic-nickname
  ("LIC"), indian-bedstuy-nickname ("Bed-Stuy"), italian-ues-nickname ("UES"). 16 to 83 s per run.
- Edge cases, all pass^3: untested cuisine, Hoboken, prompt injection.
- Follow-ups pass^3: competitors, other-area, qloo-predicts; every number in every answer traced.
  partner-check passed 2 of 2 before the account's quota ran out; area-audience not run.
- One weak spot: in Bay Ridge run 3 the repair step itself failed, so the brief kept 2 names no source
  backs up. The run still counts as passed under the suite's rule (no error, brief checks pass), and the
  page marks those names dotted as unverified, but it is the only run where unverified names reached the
  page.

v3 total on current code: 13 of 13 run cases pass^3 (39 runs), 5 of 5 edge cases, 3 of 5 follow-ups
pass^3 plus partner-check 2 of 2.

## 23. Qloo data stays private (Oct 11)

Qloo Support on Discord: live calls from a public demo with per-visitor limits are fine, private server-side
caching is fine with no time limit, and storing Qloo response data in a public repo is not approved. Keys
stay active through Nov 16; the monthly limit (10,000 requests, 5 per second) resets on the 1st.

- Saved runs (golden/) contain Qloo responses, so they were removed from git and from all of its history
  before the repo was ever pushed, and golden/ is ignored. Commit hashes changed; the one cited here
  was updated.
- Saved runs and the Qloo cache are read from GOLDEN_DIR and QLOO_CACHE_DIR; on Render both sit on a
  private persistent disk (render.yaml). The rating sheet holds only model-written briefs and stays.
- Qloo quota guard: below QLOO_RESERVE (300) remaining requests, uncached calls stop and live runs say so.

## 24. Test 9 registered; development variants (Oct 12)

Work moved to Claude Code on a team machine. Everything in this section is exploratory unless it says otherwise.

- Why Test 8's Qloo arm lost: read back from finished Test 8 data, arm A was ranked last in 44 of 60 judgements.
  Its evidence (area brand lift) was noise: for a Japanese concept in Jamaica, Queens it gave Weightwatchers,
  Montauk Brewing Co., NYC Ferry, Northwell Health and StreetEasy, and several of the same brands came back for
  Midtown.
- Not tested before today: every Qloo call in the product and in Tests 1 to 8 used a location signal. Entity
  affinity and the attributes on place records (price level, rating, hours, review keywords, descriptions) were
  unused.
- Probes before registration: 24 calls on five seed restaurants (Thai Diner, Win Son, Peppa's Jerk Chicken,
  Lucali, Jackson Diner); 3 place queries around Test 8 case 3. Listed in PREREGISTRATION_9.md.
- PREREGISTRATION_9.md committed (9f9d3e3) before any Test 9 code: Part A development on Test 8's 30 cases,
  Part B one confirmatory run on fresh storefronts. Amendment 1 the same day, before any C+, En or Em result was
  read: Part B's comparator is C+ (the city list under E's opening line), and the reading of the two ablations
  is fixed in advance.
- Variants tried so far (test9_dev.py), 14 cases each, same brief call and judge as Test 8:
  - D: same-cuisine places within 1.5 km and the places within 800 m that the cuisine's fans rate highest, each
    with price, rating, Friday closing time, description and review keywords, as a list. D over C 0.429
    (0.214 to 0.714), D over B 0.464 (0.25 to 0.714). Parity.
  - E: the same data as stated findings (named competitors, what their reviewers mention most, price mix, latest
    closing time) under an opening line telling the writer to state the facts and name the businesses. E over C
    0.964 (0.893 to 1.0), E over B 0.929 (0.786 to 1.0). Confounded with the opening line, which C never had.
  - Running or queued: E on all 30 cases; C+ (control for the opening line); En and Em (ablations).
- Known weaknesses: the judge cannot check facts; Qloo's place catalogue is incomplete (section 1, supply
  check), so a gap claim from Qloo's list alone can be wrong; Qloo's hours, prices and keywords have not been
  checked against any independent source.
- Deviation to record for Test 3: its two raters are the team members. During this session the chat showed two
  Test 8 arm A briefs with their Qloo evidence, and named brands that recur in Qloo's area lists (StreetEasy,
  Dream Hotels, DŌ, Wölffer Estate Vineyard, Montauk Brewing Co.). Test 3's Qloo arm is built the same way, so a
  team member who read the session may recognise it by those names even with the key sealed. Test 3's key and
  sheet were not opened. Ratings by anyone who read this session must be reported as possibly unblinded, or the
  rating should go to people outside the team.

## 25. Test 10: Qloo's competitor list against city records (Oct 12)

Registered in PREREGISTRATION_10.md (70f670b) before any code or comparison; backtest10.py, backtest10_results.json.
30 storefronts (Test 8's cases), same-cuisine places within 1,500 m.

| Measure | Result | 95% interval | Band |
|---|---|---|---|
| Coverage: city-record competitors found in Qloo's same-cuisine list | 37.2% (519 of 1,396) | 32.3% to 44.3% | under 50% |
| Existence: Qloo same-cuisine places with an active city record | 81.1% (813 of 1,002) | 78.4% to 83.7% | under 90% |

- Per the registered rules: the competitor set is the union of both lists with city-only places marked as having
  no Qloo detail; no absence claim ("no competitor opens late") is made at all; a Qloo place is named as operating
  only if it has an active city record.
- /search sample: of 40 unmatched city restaurants, Qloo holds 22 under another cuisine tag. So much of the
  coverage gap is the two taxonomies, not a missing catalogue; the list variant E used still misses about six
  competitors in ten.
- Existence is a lower bound: unmatched Qloo places include ones plainly operating (Starbucks, Paris Baguette,
  The Halal Guys), so name matching and carts or kiosks explain part of it. The 40 sampled names are in
  test10_detail.json (not committed) for a hand check, which would be unblinded.
- Per cuisine, coverage ran from 16.7% (Caribbean) to 58.6% (Thai). 1,349 of the 1,396 city competitors are
  in Manhattan, where the density is; the outer-borough counts are too small to read.
- Exploratory, not registered: two cases (both Midtown coffee) reached the protocol's 200-place cap. Without them
  coverage is 42.6% (39.0% to 46.7%) and existence 80.1%: the same bands.
- What it did to Test 9: variant E's Jamaica brief said the three Japanese competitors close by 22:00. City
  records list three Japanese restaurants within 1.5 km there (Sarku Japan, Teriyaki R Us, New Sarkura Japan), and
  none of them is in Qloo's list; Qloo's three are filed by the city under other categories or not at all. E's
  "Open at 23:00 or later: none" lines are not allowed under the bands.
- Variant Q built in test9_dev.py to comply (no briefs written yet; the model account has no credit): city
  records define the competitor set (nearest 15), Qloo detail is attached where the place matches, Qloo-tagged
  places the city files under another category are added, aggregates are worded "among the N with details", the
  opening line forbids absence claims, and neighbours are named only with an active city record. Median
  background 450 words. Q, not E, is the candidate to freeze for Part B once C+, En and Em have run.

## 26. Test 9 Amendment 2: candidate Q, control Q0, ablations rebased (Oct 12, evening)

Amendment 2 (56bc069) was committed before any brief existed for Q, Q0, Qn or Qm. After a reviewer round (DeepSeek):

- E is retired because Test 10 forbids its absence claims and its Qloo-only competitor list. En and Em are not run.
- Q is the candidate. Q0 is Q with nothing from Qloo: it exists because Q holds more city-record content than C+
  (same-category competitors to 1.5 km against any restaurant within 500 m), so a win over C+ alone could come
  from the better city list. Qn (Qloo chooses the places, names only) and Qm (Qloo attributes, no taste signal)
  are read against Q0.
- Go or stop: Part B runs only if Q is above both C+ and Q0 on the development cases. Part B then needs Q above
  C+, Q0 and B.
- Known imbalance: Q's background is far longer than its controls (median words over the 30 cases: Q 450, Qm 445,
  Qn 205, C+ 183, Q0 127). Brief length is fixed at about 180 words for every arm, but the writer has more to
  choose from in Q. That is what adding Qloo means here; it is stated, not corrected.
- Reviewer points taken: the reading of a Q loss is fixed in advance and compliance is not an excuse; the human
  subsample is one preference question; the write-up says the competitor panel is city records with Qloo detail
  where places match. Not taken: "Q not above C+ means the taste graph adds nothing" (Q tests all of Qloo's
  contribution, and "not shown" is not "nothing"); "a clean Test 3 would validate positioning" (Test 3 rates the
  area-brand-lift evidence that Test 8 showed loses, so it says nothing about Q).
- Open with the team: whether Test 3 is reported as not run. No decision is recorded yet.
- Status: no Q, Q0, Qn, Qm briefs exist; C+ has 1 of 30. Waiting on model credit.

## 27. Test 11: is a Qloo scene about the restaurant or its location? (Oct 12)

Registered in PREREGISTRATION_11.md (0954928) before any code; backtest11.py, backtest11_results.json. 40 blocks
(52 tried), three resolved restaurants per block: two of the block's main inspection category and one of another.
A scene is the first 30 NYC places with affinity to a restaurant.

| Measure | Result |
|---|---|
| Location share: scene overlap of two unlike restaurants on one block | 0.225 |
| Same-category overlap | 0.24 |
| Category effect (same minus different) | 0.015, 95% interval -0.074 to 0.115 |
| Share of a scene within 1,500 m of its restaurant | mean 0.18, median 0.10 |
| Empty scenes | 0 of 120 |

Band, as registered: **specific, not validated.** Scenes differ between restaurants on the same block, so a scene
is not just its location; but nothing independent backs it, since same-category pairs share no more than
different-category pairs. Per the rule the feature may show a scene labelled "Qloo's list, not validated" and may
not use it to choose neighbourhoods. The plan to steer the scout's neighbourhood search by scene is dropped.

Exploratory, not registered:
- 46 of the 120 restaurants (in 28 of the 40 blocks) returned one identical list: city landmarks (Central Park,
  Empire State Building, LaGuardia Airport, Barclays Center, Katz's Delicatessen and so on). That is Qloo's answer
  when it holds no signal for a place. It explains the overlaps of exactly 1.0 and 0.5 in the per-block results
  and inflates the location share. So for a restaurant drawn at random from city records, Qloo has no scene about
  four times in ten.
- In the 12 blocks where no restaurant got that list: location share 0.044, same-category overlap 0.094, category
  effect 0.05 (-0.055 to 0.159). Scenes are then almost entirely specific to the restaurant, and still not shown
  to follow category. Twelve blocks is too few to read more into.
- Product consequence already coded (scene.py): a scene that is mostly not food and drink is treated as "no
  signal" and the founder is asked for a better-known place.

Limitations as registered: inspection category is coarse; seeds are restaurants Qloo can resolve.

## 28. Two Qloo lookups on the page; Test 12 registered (Oct 12, night)

- Built, no model call (a589f3d): "What is around the top pick" (around.py, /api/around) and a scene explorer
  (scene.py, /api/scene). The first is arm Q's data as fields: city records define competitors, Qloo adds price
  level, Friday closing time and review mentions where a place matches; worded by Test 10. The second is labelled
  by Test 11 and is not used to choose neighbourhoods. Both endpoints were tested and the page loads in a headless
  browser with its script running; the two new buttons have not been clicked in a real browser yet.
- Scene explorer, exploratory check on five unlike seeds (Thai Diner, Win Son, Peppa's Jerk Chicken, Lucali,
  Jackson Diner), top 8 names each, mean pairwise overlap: artists 0.02, brands 0.17 (Eater, Milk Bar, Oddfellows
  and The Infatuation came back for three or more seeds), podcasts 0.28 (seven shows came back for three or more).
  Podcasts are dropped from the panel. Brands stay, with a line saying New York food media turn up often.
- Test 12 registered (PREREGISTRATION_12.md, a4d6bd5) before the sample was drawn: Qloo's Friday closing times and
  price levels against Google Maps and restaurants' own sites. Bars: 80% of closing times within 30 minutes, 70%
  of price levels equal; an attribute that fails is removed from the panel and from any shipped brief. The sample
  is drawn (test12.py sheet): 400 eligible places, 40 taken (Bronx 8, Brooklyn 11, Manhattan 11, Queens 10). The
  sheet shows name and address only; Qloo's values sit in a key file the checker does not open. Borough is the
  borough of the storefront a place was drawn for. Waiting for a person to fill the sheet.
- Reviewer round (DeepSeek), corrections it accepted: descriptions can be wrong (Test 6), so the panels carry
  their test's label; Tests 8, 10 and 11 were not prediction tests; "E beat C+" was never measured; if Q loses
  Part A, nothing is shown to move brief quality and the panel is then a capability resting on unchecked data,
  which is why Test 12 exists.

## 29. Test 9 Part A: two failed briefs found before any Q number was read (Oct 12, late)

The Q against Q0 comparison stayed at 29 of 30 judged. The cause was not the judge: the Q0 brief for case 17 was an
empty model reply that had been saved as a brief. Checking every arm then found:
- Empty replies saved as briefs: Q0 case 17, Qm case 3.
- A reply cut off after two of the five headings (54 words): Q0 case 6. This one had been judged, in Q against Q0
  and in Qn against Q0, with a control brief less than a third of the normal length.
No Q, Qn or Qm number had been read when this was found. Rule applied, and now enforced in test9_dev.py: a reply
missing any of the five headings is a provider failure, not a brief; it is not saved, and the case is rerun. The
three bad entries were removed, with the two judgements of case 6 that used the cut-off brief. Test 8's B briefs
(used in every triple) all have five headings. This is recorded as a deviation: two judgements were discarded and
will be redone, for a reason fixed without sight of any result.
State after this: Q 30 briefs, C+ 30, Q0 28; Q against C+ 30 of 30 judged; Q against Q0 28 of 30. The go or stop
decision now needs two Q0 briefs rewritten and two cases judged. Model credit is still at zero.

## 30. Test 9 Part A result: stop. Qloo is not shown to improve the brief (Oct 12, late)

All four comparisons have 30 cases, complete briefs, two judgements each, one judge host (gemini-3.8-flash on
CometAPI). Read once, in the order fixed beforehand. Numbers in test9_partA_results.json. "Above" means the lower
bound of the 95% interval is above 0.5 (Amendment 2).

| Comparison | Share of judgements preferring the first arm | 95% interval | Above? |
|---|---|---|---|
| Q against C+ | 0.633 | 0.483 to 0.80 | no |
| Q against Q0 | 0.60 | 0.433 to 0.767 | no |
| Qn against Q0 | 0.333 | 0.20 to 0.483 | no; Qn is below Q0 |
| Qm against Q0 | 0.617 | 0.483 to 0.75 | no |

- Rule (Amendment 2): Part B runs only if Q is above both C+ and Q0. It is above neither. **Part B does not run.**
  No Part B case was sampled. A Part B harness had been written while the run finished; it was never run or
  committed and has been deleted.
- Wording fixed in Amendment 3 for this outcome: "Neither comparison shows a gain from Qloo. The brief ships
  written from city records. The Qloo panels stay as labelled descriptions, each under the result of its own
  test."
- What the numbers do and do not say. Q's point estimates are above 0.5 against both controls, and the intervals
  include 0.5: with 30 cases this is "not shown", not "shown to be equal". It is also Part A, on cases with
  known earlier results. We do not run more cases to chase it; the rule was fixed and it says stop.
- Ablations. Neither is above Q0. Qn's upper bound is below 0.5: letting Qloo choose which places to list, with
  names only, made the brief worse than listing the nearest restaurants from city records. Qm (Qloo attributes,
  no taste signal) scored about the same as Q. So nothing here suggests the taste graph helps the brief, and the
  taste-ranked choice of neighbours may hurt it.
- A finding that is not about Qloo (exploratory). Every arm with the opening line beat the no-background brief:
  C+ over B 0.817 (0.683 to 0.933), Q0 over B 0.783 (0.65 to 0.90), Q over B 0.80 (0.667 to 0.933). In Test 8 the
  same city list without that line tied with no background (C over B 0.483). So the gain seen in variant E this
  morning came from telling the writer to state facts and name businesses, as the reviewer suspected, and it
  works on city records alone. This is a candidate change to the shipped brief; it would need its own registered
  test on fresh cases before any claim.
- Deviations: two Q0 briefs and one Qm brief were provider failures and were rewritten, and two judgements made
  against a cut-off brief were redone (section 29); cut-off replies for Qn case 30 and one Qm case were refused by
  the harness and rerun. Four CometAPI keys were used over the day; the model and judge were the same throughout.
- Consequence for the product: the positioning brief has no tested reason to use Qloo. Qloo remains in the two
  lookups (what is around an address; scenes), each labelled by its own test, with Test 12 still to decide
  whether closing times and prices stay.

## 31. Test 14: Qloo venue-to-artist affinity against Ticketmaster bookings (Oct 12, late)

Registered in PREREGISTRATION_14.md (d1c9712) before any code; Amendment 1 (genre and language-model baselines,
outcomes fixed) and Amendment 2 (frame widened) were both committed before any result was read. backtest14.py,
backtest14_results.json. The first run's result files and a stopped second run were deleted unread; only progress
lines were read to check health.

Sample: 105 venues with upcoming music events within 15 km over six months (the widened frame added 12 venues to
the 93 found at first, so the target of 40 could not be met). 19 qualified: 55 had fewer than 6 named acts, 27 did
not resolve in Qloo or returned no artist list, 4 had too few acts that resolved. Pool: 106 acts, 14 of them
booked at two or more sampled venues. For each venue, each scorer ranks the pool; the acts that venue booked are
the positives. AUC per venue, mean over venues, 95% interval by bootstrap over venues.

| Scorer | AUC | 95% interval |
|---|---|---|
| Qloo affinity | 0.589 | 0.518 to 0.668 |
| Fame (Qloo popularity of the act) | 0.485 | 0.403 to 0.573 |
| Genre (share of the venue's other acts with the same Ticketmaster genre) | 0.533 | 0.462 to 0.607 |
| GPT-6 Astra with the venue's name only, on its list of own acts plus 40 others | 0.814 | 0.768 to 0.862 |
| Qloo affinity on that same list | 0.592 | 0.52 to 0.672 |

Gains of Qloo affinity: over fame +0.104 (0.003 to 0.212); over genre +0.056 (-0.025 to 0.138); over the language
model -0.223 (-0.281 to -0.16).

- Outcome, by the rules fixed in Amendment 1: **above fame, not above genre.** Sentence fixed beforehand: "Qloo's
  affinity knows what kind of music a room books, not which acts. A feature built on it may describe a room's
  sound and may not suggest specific acts as a fit."
- The language model beat Qloo by a wide margin on the same lists. For these venues, what a model already knows
  ranks real bookings far better than Qloo's affinity does. A booking or sound feature for known venues would work
  better without Qloo than with it. Caution on the model's score: shows that went on sale before the model's
  training date could be remembered rather than inferred; that was not separated.
- Reported with no reading attached: affinity AUC 0.61 (0.531 to 0.693, 17 venues) on acts whose show went on sale
  more than 60 days ago, and 0.451 (0.295 to 0.61, 8 venues) on acts on sale within 60 days. Leaving out the 14
  shared acts: 0.576 (0.455 to 0.691, 15 venues).
- Limits as registered: 19 venues; venues are not restaurants; Ticketmaster lists ticketed rooms only.

## 32. Idea screen, primary checks (Oct 12, late)

PREREGISTRATION_13.md (de9b5c9; Amendment 1 before any result). screen13.py, screen13_results.json. 30 restaurants
with Qloo signal, 15 sibling pairs. Exploratory by registration: a pass earns an idea a real test, nothing more.

| Idea | Coverage | Specificity (overlap between unlike seeds) | Sibling overlap | Consistency (siblings minus unrelated) | Screen |
|---|---|---|---|---|---|
| 1 Partners (non-restaurant places) | 1.00 | 0.034 | 0.364 | +0.33 (0.115 to 0.565) | pass |
| 2 Scene (restaurants) | 1.00 | 0.004 | 0.27 | +0.267 (0.067 to 0.53) | pass |
| 3 Sound (artists) | 0.70 | 0.026 | 0.032 | +0.006 (-0.026 to 0.067) | fail: consistency |
| 4 Brands | 0.60 | 0.041 | 0.091 | +0.05 (-0.041 to 0.209) | fail: coverage, consistency |
| 5 Screen taste (TV and film) | 0.57 | 0.026 | 0.04 | +0.015 (-0.026 to 0.084) | fail: coverage, consistency |
| 6 Words (tags) | 0.97 | 0.114 | 0.079 | -0.035 (-0.079 to 0.01) | fail: consistency |
| 7 Twin city (Chicago places) | 1.00 | 0.058 | 0.335 | +0.276 (0.076 to 0.508) | pass |

No idea returned a generic list, and none overlapped with the no-seed baseline (0.011 at most).
- The three ideas whose answers are places passed. The four whose answers come from another field (artists,
  brands, TV and film, tags) failed: their lists differ between restaurants, but two branches of the same
  restaurant get lists no more alike than two strangers'. A list that changes this much between branches of one
  restaurant is not describing that restaurant's crowd in any stable way.
- With Test 14, the sound idea has failed twice: unstable for restaurants here, and worse than a language model
  for venues.
- Open until the secondary analysis finishes (screen13b.py): whether the three passes are mostly about where a
  restaurant stands. Sibling branches may also share a name, which the screen cannot separate from a shared crowd.

## 33. Idea screen, secondary analysis; Test 15 registered (Oct 12, late)

- Secondary analysis as registered in Amendment 1 (screen13b.py; 12 blocks where all three restaurants hold
  signal; 30 seeds for nearby share). No idea is "mostly about where the restaurant is".

| Idea | Location effect | Nearby share | Category effect (reported only) |
|---|---|---|---|
| 1 Partners | +0.092 | 0.261 | +0.055 (-0.101 to 0.23) |
| 2 Scene | +0.008 | 0.39 | +0.062 (-0.011 to 0.181) |
| 3 Sound | -0.005 | n/a | -0.021 (-0.051 to 0.0) |
| 4 Brands | -0.034 | n/a | +0.077 (-0.016 to 0.25) |
| 5 Screen taste | +0.009 | n/a | +0.038 (-0.037 to 0.119) |
| 6 Words | -0.003 | n/a | +0.136 (0.058 to 0.216) |
| 7 Twin city | +0.059 | n/a | +0.119 (-0.049 to 0.332) |

  So the three ideas that passed (partners, scene, twin city) are not explained by location: about a quarter of
  a partner list and four tenths of a scene lie within 1.5 km, and two unlike restaurants on one block share
  little. The category effect is on 12 blocks and carries no reading; tags ("words") are the one idea where it is
  above zero, which fits tags describing cuisine. Still open: whether branch consistency is a shared name.
- Web research the same evening (no Qloo data involved): the 2025 Qloo hackathon was won by "GeoTaste: Your
  Business Consultant Agent" (location to business insights from Qloo's business data), with Alloy, Resonance AI
  and Zesty as honorable mentions. Qloo's own site sells enrichment, agent grounding in real places,
  recommendations from combined interests, and locality. Public 2026 entries seen: Tasteplot (site finder on
  heatmaps, validation not run), Transplant, House-programme, SponsorFit; none checks Qloo against ground truth.
- The team asked for completely new ideas outside restaurants. Test 15 registered (PREREGISTRATION_15.md,
  b1000a4): does Qloo's artist-to-artist affinity pick the act that really opened for a headliner, against fame,
  genre and a language model, on US bills that went on sale since Aug 15. A reviewer suggested a caveat that
  compressed affinity scores could produce a null; not added, because AUC depends on order only, so compression
  cannot lower it. Ties would be reported if common.

## 34. Test 15: Qloo artist-to-artist affinity against real tour bills (Oct 12, night)

Registered in PREREGISTRATION_15.md (b1000a4) before any code. backtest15.py, backtest15_results.json. The run
stopped once at 26 of 40 on a network dropout and was resumed from its caches; no result was read in between.

Sample: US music events on Ticketmaster that went on sale Aug 15 to Oct 12, 2026, with 2 to 4 named acts; one bill
per headliner. 56 headliners tried, 40 qualified (8 headliners and 8 bills' supports did not resolve in Qloo). Pool:
58 support acts. For each headliner, its own supports are the positives and the other pool acts the negatives.

| Scorer | AUC | 95% interval |
|---|---|---|
| Qloo affinity | 0.875 | 0.795 to 0.941 |
| Fame | 0.473 | 0.388 to 0.561 |
| Genre (same Ticketmaster genre as the headliner) | 0.714 | 0.635 to 0.788 |
| GPT-6 Astra with the headliner's name only, on its supports plus 40 others | 0.976 | 0.958 to 0.99 |
| Qloo affinity on that same list | 0.883 | 0.804 to 0.948 |

Gains of Qloo affinity: over fame +0.401 (0.296 to 0.508); over genre +0.161 (0.063 to 0.253); over the language
model -0.093 (-0.171 to -0.029).

- Outcome by the registered rules: **above fame and genre, not above the language model.** Sentence fixed
  beforehand: "Qloo's affinity carries real information about who tours with whom, beyond fame and genre. A
  language model alone did as well, so we make no claim that Qloo beats it." The model did more than as well: the
  interval of the difference lies below zero, so on these lists the model ranked real openers better than Qloo.
- This is the first test in the project where Qloo shows a strong signal against ground truth outside Qloo: 0.875,
  well above genre. Its artist-to-artist links are real, unlike its links from restaurants or venues.
- It is still not a use that works better with Qloo than without. As registered, the model may know some of these
  tours or the acts' past tours together; a near-perfect 0.976 fits either memory or strong knowledge of music
  scenes. Either way a promoter asking the model directly would do at least as well on a shortlist like this.
- Not tested here: finding candidates from a whole catalogue (the model cannot enumerate acts it has never heard
  of; Qloo can search millions), acts too obscure for the model, and the model given Qloo's scores as an input.
  Another entrant's README reports Qloo finding more real openers in a top 100 than a model alone; not verified.

## 35. Test 17: Qloo city scores against the markets artists really play (Oct 13)

Registered in PREREGISTRATION_17.md (1b631eb); Amendment 1 (market draw baseline) before any result. backtest17.py,
backtest17_results.json. The run stopped twice with no result read: once on a network dropout while fetching
listings, once when the CometAPI balance ran out after 4 of 60 model calls; it resumed from its caches on a new key.

Sample: US music shows on sale Aug 15 to Oct 12, 2026; 677 acts had a show in one of 40 large metros; 132 had shows
in 5 to 30 of them; 60 resolved in Qloo. They play 7.7 of the 40 markets on average. Qloo returned a score for an
artist in 32 of 40 markets on average. AUC per artist over the 40 markets, mean and bootstrap over artists.

| Scorer | AUC | 95% interval |
|---|---|---|
| Qloo affinity of the artist among people in the market | 0.63 | 0.593 to 0.67 |
| Market size (metro population) | 0.66 | 0.611 to 0.707 |
| Market draw (share of the other sampled acts playing there) | 0.693 | 0.653 to 0.731 |
| GPT-6 Astra with the artist's name only | 0.739 | 0.702 to 0.777 |

Qloo minus market size -0.03 (-0.081 to 0.022); minus market draw -0.063 (-0.109 to -0.018); minus the language
model -0.109 (-0.144 to -0.075).

- Outcome by the registered rules: **not above market size.** Sentence fixed beforehand: "Qloo's city scores did
  no better than city size at picking where artists play." They were also below simply knowing which cities are
  busy tour stops, and below the language model.
- Qloo's scores are better than chance (0.63), so they hold some information about where an act draws, but less
  than a population table. The hand-picked probe (Morgan Wallen in Nashville, Bad Bunny in Miami) was real and
  unrepresentative: a few artists with strong regional identities, not the typical touring act.
- This matches what other entrants reported about routing from Qloo's location data, and Tests 1 and 2 here.
- Limits as registered: routing follows venues, distance and deals as much as demand; only a two-month on-sale
  window is seen; populations are approximate.

## 36. Test 16: the model with Qloo against the model alone, finding real openers from scratch (Oct 13)

Registered in PREREGISTRATION_16.md (ebd5dba); Amendment 1 before any comparison (the first run made no data: the
harness asked Qloo for 100 artists in one call and the limit is 50). backtest16.py, backtest16_results.json.
Deviations: the frame held only 62 fresh headliners, so 46 qualified instead of the 100 aimed for; the model calls
for the first 25 headliners went through CometAPI and the rest through Kie (same model, GPT-6 Astra) after the
CometAPI balance ran out; the run was restarted many times through network dropouts and Kie server errors, always
from saved answers, and no result was read before it finished.

46 headliners, 67 real support acts. Each arm returns up to 50 names for a headliner with no shortlist given.

| Arm | Share of real supports found in 50 names | 95% interval | Headliners with at least one found |
|---|---|---|---|
| GPT-6 Astra alone | 0.319 | 0.199 to 0.449 | 17 |
| Qloo alone (50 highest-affinity artists) | 0.159 | 0.076 to 0.254 | 11 |
| GPT-6 Astra with Qloo's 100 candidates and scores | 0.312 | 0.199 to 0.438 | 19 |

Model with Qloo minus model alone: -0.007 (-0.112 to 0.098) at 50 names; -0.04 (-0.138 to 0.054) at 10. Qloo alone
minus model alone: -0.159 (-0.275 to -0.054).

- Outcome by the registered rules: **not shown.** Sentence fixed beforehand: "Not shown. With Qloo the model found
  about as many real openers as without."
- Qloo alone found half as many real openers as the model alone, and that difference is clear. So the idea that
  Qloo's reach across its catalogue makes up for the model's limits did not hold here. Another entrant's README
  reports the opposite at 100 names; this test does not reproduce it at 50.
- Of the 22 supports the model found with Qloo's list in front of it, 11 were on Qloo's list. Seeing the list
  changed which openers it found, not how many.
- Limits as registered: few real supports per headliner, often chosen for business reasons; 46 headliners is a
  small sample and the intervals are wide; the model may know some tours.

## 37. Test 18: from five films a real person loved, what else will they love? (Oct 13)

Registered in PREREGISTRATION_18.md (a3349ee); Amendment 1 (small-model arms) before any model call. backtest18.py,
backtest18_results.json. Data: MovieLens ml-latest-small. 233 people were eligible; 50 were used, each with 5 loved
films as the signal and 8 other loved films against 8 disliked ones as candidates (800 candidates; Qloo returned a
score for 99.6%). Deviations: the large-model answers came from three hosts as credit ran out (CometAPI, Kie,
CometAPI; all GPT-6 Astra); the small-model answers (gemini-3.8-flash) came from Google's own API on several of
the team's keys and, for the last 16, from CometAPI; Kie lists that model but both of its endpoints returned
server errors. No answer was scored until all 400 were saved.

| Scorer | AUC (loved against disliked) | 95% interval |
|---|---|---|
| Qloo affinity from the five films | 0.758 | 0.717 to 0.796 |
| Average rating by everyone else | 0.815 | 0.777 to 0.852 |
| Popularity (number of ratings) | 0.687 | 0.642 to 0.73 |
| Genre overlap with the five films | 0.578 | 0.532 to 0.625 |
| GPT-6 Astra alone | 0.821 | 0.781 to 0.862 |
| GPT-6 Astra with Qloo's scores | 0.82 | 0.782 to 0.856 |
| gemini-3.8-flash alone | 0.84 | 0.806 to 0.873 |
| gemini-3.8-flash with Qloo's scores | 0.837 | 0.802 to 0.872 |

Differences: Qloo minus average rating -0.057 (-0.109 to -0.008); minus popularity +0.071 (0.018 to 0.122); minus
genre +0.179 (0.124 to 0.23). Large model with Qloo minus alone -0.001 (-0.019 to 0.016). Small model with Qloo
minus alone -0.003 (-0.017 to 0.01). Large model alone minus Qloo +0.063 (0.026 to 0.108).

- Outcome by the registered rules: **Qloo not above average rating.** Sentence fixed beforehand: "Qloo's scores did
  no better than knowing which films are generally well liked." They did worse: the interval is below zero.
- Qloo's scores are real information (0.758, clearly above popularity and genre). They added nothing to either
  model: both differences are within two hundredths of zero.
- Small-model readings: "small model with Qloo above small model alone" does not hold. "Small model with Qloo not
  below the large model alone" holds by the registered margin (+0.016, -0.002 to 0.033), but not because of Qloo:
  the small model alone already scored as high as the large one. It is not evidence that Qloo lifts a small model.
- What the numbers suggest about the task (exploratory): average rating, both models and the with-Qloo arms all
  land between 0.815 and 0.84. Telling a person's loved films from their disliked ones is mostly a matter of which
  films are good; little room is left for personal taste to show. A test with disliked films matched on average
  rating would ask a sharper question. That is a design note for a future test, not a reason to discount this one.
- Limits as registered: well-known films up to 2018; film enthusiasts; one domain.

## 38. Test 12: the sub-agent lookups failed the spot check and were discarded (Oct 13)

Amendments 2 and 3 to PREREGISTRATION_12.md (1408983, 1608528) allowed language-model lookups under a human spot
check. Four fresh sub-agents with web search, given names and addresses only, filled the sheet: a Friday closing
time for 29 of 40 (9 from the restaurant's own site, 27 from another listing site, none from Google's listing,
which they could not open) and a price for 18. Nothing was scored. A team member then looked up spot-check rows on
Google Maps. Of the first six, two disagreed with the agents' sheet by more than 30 minutes: Juicy King Crab
Express (Google 22:20, sheet 23:00 from a listing site that calls itself unverified) and Nacho Macho Taco (Google
23:00, sheet 18:00 from an ordering page showing the same hours for every branch). More than one disagreement
voids the sheet, so it was discarded unscored and kept aside as test12_sheet_agents_discarded.csv (not committed).
The six Google Maps lookups by the team member start a clean sheet; the remaining rows are to be looked up the
same way. Lesson: listing aggregators and ordering pages are not a usable reference for opening hours.

## 39. Test 12 result: Qloo's Friday closing times against Google Maps (Oct 13)

Registered in PREREGISTRATION_12.md (a4d6bd5) before the sample was drawn; Amendments 1 to 3 before any entry.
test12.py, test12_results.json. After the sub-agent lookups were discarded (section 38), a team member looked up
all 40 sampled places on Google Maps on 2026-10-13 and sent the Friday hours; the assistant entered them in the
sheet. The team member did not open the key file. Seven rows had Qloo values shown in the working session earlier
(Amendment 1), so the decision uses the other 33.

| | Decision sample (33 places) | All 40 |
|---|---|---|
| Places with Friday hours on Google and still operating | 30 | 36 |
| Qloo's Friday closing time within 30 minutes of Google's | 29 of 30 (96.7%; 90.0% to 100%) | 35 of 36 (97.2%; 91.7% to 100%) |
| Exactly equal | 29 of 30 | 35 of 36 |
| Marked permanently closed on Google | 1 | 2 |
| No hours on Google, or temporarily closed | 2 | 2 |

- Decision by the registered rule (80% or more within 30 minutes): **closing times are shown**, with this result
  beside them. This is the first test in the project that Qloo's data passes against a source outside Qloo.
- Price levels: **not assessed.** No price was recorded from Google during the lookups, so the 70% rule could not
  be applied. Price levels stay on the panel labelled as not checked.
- Permanently closed: 2 of 40 (5%), under the 10% that would require a warning. One more was marked temporarily
  closed. All three are places Qloo lists as operating and that matched an active city inspection record.
- What agreement means, stated plainly: 29 of 30 are exact matches to the minute, including unusual times. That
  is what one would expect if Qloo's hours come from Google's listings or the same feed. So this shows Qloo's
  closing times are as current as Google Maps, not that two independent sources confirm each other. The registered
  limitation already said agreement is not truth.
- Deviations: lookups were not blind to the day's work in the sense that the same team member had seen seven
  rows' Qloo values (handled by Amendment 1); the team member pasted Google's hours into the chat and the
  assistant transcribed them, matching unnumbered lines to rows by list order, which the team member could
  correct; the restaurant's own site was not consulted, so every reference is Google's listing; one sampled place
  is a chain outlet (Domino's) that the no-chains filter missed.
- Panel text updated (around.py) to state the checked result for closing times and that prices are not checked.

## 40. Test 12, price levels: a partial sample (Oct 13)

The team member sent Google's price for the first 17 sampled places (rows 1 to 17, matched by list order; a note
on the sixteenth confirmed the order there) and then asked whether the rest were needed. The lookups were stopped
there, before any price had been compared with Qloo's, to save the team member's time. That is a deviation: the
protocol planned all 40. 12 of the 17 showed a price on Google, all as per-person ranges, converted by the
registered rule (top of the range up to $20 is level 1, up to $50 level 2, up to $100 level 3).

| | Decision sample | All rows with a price |
|---|---|---|
| Places with a Google price | 10 | 12 |
| Qloo's level equals Google's | 7 of 10 (70%; 40% to 100%) | 9 of 12 (75%; 50% to 100%) |
| Within one level | 10 of 10 | 12 of 12 |

- By the registered rule (70% or more equal), price levels are **shown**. This is at the bar exactly, on ten
  places, with an interval from 40% to 100%, so it is a weak pass and is described as such: the panel now says a
  price level is a rough guide and gives the count.
- All three disagreements are the same case: Google shows $20 to $30 per person, which the registered conversion
  puts at level 2, and Qloo gives level 1. No place was more than one level apart. Whether that band belongs at
  level 1 or 2 is a matter of where the conversion draws its line, which was fixed before any data and is not
  changed now.
- Not checked: review mentions.

Interim look, recorded before any further price was received (Oct 13): the 7 of 10 above was seen, and the team
judged it not decisive. The remaining 21 sampled places (rows 18 to 27, 29 to 36, 38 to 40) will all be looked up,
with no stopping partway, and the price decision will be taken once on the full registered sample. The partial
figure above is superseded by that result whichever way it goes.

## 41. Test 12, price levels on the full sample: removed (Oct 13)

After the interim look (section 40) the team member looked up Google's price for all remaining sampled places, as
committed beforehand. 38 places were looked up (2 are permanently closed); 32 showed a price, all as per-person
ranges, converted by the registered rule. Lines sent without row numbers were matched by list order and confirmed
by the team member's notes on rows 16 and 32 and a correction on rows 38 to 40.

| | Decision sample | All rows with a price |
|---|---|---|
| Places with a Google price | 27 | 32 |
| Qloo's level equals Google's | 17 of 27 (63.0%; 44.4% to 81.5%) | 21 of 32 (65.6%; 50.0% to 81.2%) |
| Within one level | 27 of 27 | 32 of 32 |

- Decision by the registered rule (70% or more equal): **price levels are removed** from the panel, the scene
  explorer and any brief the product ships. This replaces the weak pass on the first ten places. The panel now says
  why, with the count.
- What the misses look like: Qloo was never more than one level away. Google's bands put 12 of the 32 places at
  level 2; Qloo put 3 there, and gave most places level 1 or 3. Seven of the eleven misses are Google bands whose
  top is $30 to $50 against Qloo's level 1. So the two scales draw their lines in different places; under the
  conversion fixed in advance that is a fail, and the conversion is not changed after the fact.
- Test 12 in full: Friday closing times pass strongly (29 of 30 within 30 minutes of Google Maps) and stay; price
  levels fail and are removed; 2 of 40 places Qloo lists as operating are permanently closed on Google; review
  mentions are unchecked and labelled so.

## 42. Test 20: asked when a restaurant closes, is a model right more often with Qloo? (Oct 13)

Registered in PREREGISTRATION_20.md (562d587) before any code or model answer. test20.py, test20_results.json.
Reference: the Friday closing times a team member read off Google Maps for Test 12. 36 places still operating with
hours on Google; the decision uses the 30 whose Qloo values had not been shown in session. Deviations: the two
models' arms were collected at different times as credit allowed (each model is read on its own, as registered);
small-model answers came from CometAPI and, for a few, Google's own API; the "with Qloo" prompt carried Qloo's
Friday closing time, the only hours field kept in Test 12's key, not the whole week.

| Arm | Right within 30 minutes (decision sample) | Said it did not know | Gave a wrong time |
|---|---|---|---|
| GPT-6 Astra alone | 0 of 30 | 30 | 0 |
| GPT-6 Astra with Qloo's record | 29 of 30 (96.7%; 90% to 100%) | 0 | 1 |
| gemini-3.8-flash alone | 3 of 30 (10%; 0% to 23%) | 21 | 6 |
| gemini-3.8-flash with Qloo's record | 29 of 30 (96.7%; 90% to 100%) | 0 | 1 |

Differences, with Qloo minus alone: large model +0.967 (0.90 to 1.0); small model +0.867 (0.70 to 1.0). On all 36
places: 0, 35, 4 and 35 right; small model alone gave 8 wrong times.

- Reading by the registered rule, for both models: **with Qloo above alone.** Sentence fixed beforehand: "Asked when
  a real New York restaurant closes on Friday, the model was right for 29 of 30 places with Qloo's record and 0 of
  30 without it [large model; 3 of 30 for the small model]. This is a job the agent cannot do the same without
  Qloo's place data."
- This is the first test in the project in which a model with Qloo beats the same model alone, against a
  reference outside Qloo, and the difference is as large as it can be.
- What the two models did alone differs in a way that matters: the large model declined every time, as told
  ("do not guess"); the small model answered 9 of 30 anyway and was wrong on 6. So without the record the choice
  is between no answer and a wrong one.
- What it does not show, as registered: the "with Qloo" arm repeats a fact it was handed, so its score is Test
  12's agreement between Qloo and Google (the one miss is the same place). Qloo's hours very likely share
  Google's source. The result is that live place data reaching the agent through Qloo's API answers a question
  the model cannot; any live place-data source would serve, and it says nothing about taste.
- Sample: 40 places drawn for Test 12, mostly small independents, where a model's knowledge is thinnest.

## 43. Test 21: is Qloo ahead of the model on lesser-known headliners? (Oct 13)

Registered in PREREGISTRATION_21.md (adb06b2) before any split by fame was computed. backtest21.py,
backtest21_results.json. No model call: Test 15's and Test 16's saved per-headliner results, split at the median of
the headliner's Qloo popularity.

| | Lesser-known half | Better-known half |
|---|---|---|
| Test 15: Qloo's AUC minus the model's | -0.098 (-0.224 to -0.009), n 20 | -0.088 (-0.207 to -0.015), n 20 |
| Test 16: recall with Qloo minus alone | +0.014 (-0.196 to 0.232), n 23 | -0.029 (-0.072 to 0.0), n 23 |

Trend over Test 15's 40 headliners (popularity against Qloo minus model): Spearman -0.115 (-0.402 to 0.19).

- Reading by the registered rule: **Qloo was not ahead of the model on lesser-known headliners either.** The
  secondary is not shown.
- The split did not reach obscure acts, and this limits what the result says. The median popularity in Test 15's
  sample is 0.99, and its "lesser-known" half runs from 0.72 to 0.99: by Qloo's own score nearly every headliner
  is well known, because a Ticketmaster bill with named supports that Qloo resolves is already a notable act. So
  the question "does Qloo beat a model on acts the model has barely read about" is not answered by this data.
  Test 16's lesser-known half does reach down to 0.02, and there the difference is +0.014 with an interval from
  -0.196 to 0.232: nothing shown, on 23 headliners.

## 44. A test on truly obscure headliners: planned, not registered (Oct 13)

Test 21 left "does Qloo beat a model on acts the model has barely read about" open. The plan was a Test 22 on
headliners with Qloo popularity below 0.5, with a "model with Qloo's scores" arm. Before registering, the popularity
of the headliners already looked up for Tests 15 and 16 was counted (cached searches; no opener result read):

- Of 95 resolved headliners, 2 are below 0.5, 3 below 0.7, 11 below 0.9. The median is 0.99.
- Tests 15 and 16 between them tried every bill the Ticketmaster windows returned (106 and 62 headliners).

So a sample of 20 or more obscure headliners cannot be drawn from this source, and the protocol was not committed.
What this says on its own: an act with a Ticketmaster bill naming its supports is almost always one Qloo rates as
very well known, so tour bills are the wrong ground truth for the long tail. Model hosts on this date: CometAPI
answers for GPT-6 Astra and gemini-3.8-flash; Kie is out of credit.

## 45. Test 22 (screen): model-written NYC plans against Qloo's hours (Oct 13)

Registered in PREREGISTRATION_22.md (306f914) before any plan was made. test22.py, test22_results.json. Idea being
screened: an agent that checks and repairs a chatbot's plan for places that are shut at the planned hour.

| | GPT-6 Astra | gemini-3.8-flash |
|---|---|---|
| Stops Qloo holds hours for (bar 1: 0.70) | 0.992 (0.975 to 1.0) | 0.967 (0.933 to 0.992) |
| Plans with a stop Qloo flags (bar 2: 0.25) | 0.567 (0.40 to 0.733) | 0.633 (0.467 to 0.80) |
| Checkable stops flagged | 24 of 119 | 29 of 116 |

Bars 1 and 2 hold. Bar 3 (a person confirms the flags on Google Maps) has not been run, and two things changed
before it could be:

- Deviation: before making the sheet I opened the flagged rows to look for a fault in the code. 16 of GPT-6 Astra's
  24 flags are "closed that day", from records whose hours for that day are a single entry marked closed. Several
  are well-known places that are widely known to open every day. So many flags are probably Qloo's record being
  wrong or empty for that day, not the plan being wrong. This is an impression from reading rows, not a measurement;
  the sheet (test22_sheet.csv, 40 rows, blind) exists if the team wants the number.
- The team dropped the idea for a reason outside the test: one closing time is a Google search, Qloo's hours seem
  to share Google's source (Test 12), and any team could build the same check on Google's Places data.

What stands from this: Qloo's search found 119 of 120 places a strong model named, so name lookup is not the weak
point. And "closed" entries in Qloo's hours cannot be trusted without a second source: Test 12's 29 of 30 was on
places that had a Friday closing time, which left out records like these.

## 46. Gallery read, new ideas, and Test 23 on comedy (Oct 13 to 14)

**Gallery.** The Devpost gallery opened with 117 projects; all pages were read (kept privately in
research_notes/gallery_oct13). About 80 are recommenders. Crowded: group picks (16), tour routing and openers (13),
concierges (12), moving city (9). Five do "where to launch" from Qloo heatmaps, the approach Tests 1, 4 and 7
rejected; none uses vacant storefronts. Several teams test themselves honestly (Roomtone found 0 of 149 touring acts
in Qloo's read of the venue they played; Taste Day Japan found a model did not invent places). Most "beats the model"
claims score themselves with Qloo's own numbers. Advance's "3x more real openers" compares Qloo alone with a much
weaker model, with no model-plus-Qloo arm.

**Ideas and probes.** IDEAS.md holds the candidates and the probes behind them. Probes are feasibility checks with
expectations written first, not registered tests. What they showed about Qloo on our key: artist-to-artist overlap
is complete and sensible, including "bridge" acts between two crowds; comedians score against each other; film
overlap is sensible but matched only 3 of 6 known release-date cases; age and gender skew exists but is coarse and
male-skewed for every film; books and podcasts are thin; scoring named artists for an age band and city breaks
down; the progressive and conservative audiences return one identical score for everything; trends return nothing.

**Test 23** (PREREGISTRATION_23.md, edc23a1; backtest23.py, backtest23_results.json). Does Qloo know which
comedians share a crowd?

- Part B, famous package tours: 31 of 32 comics found, 444 of 465 pairs scored. A pair who toured together outscored
  a pair who did not 0.612 of the time (0.464 to 0.797); on pairs outside the earlier probe 0.616 (0.45 to 0.811).
  Reading: **not shown**. The probe's 0.865 on comics we grouped ourselves did not carry over to real tours.
- Part A, current Ticketmaster comedy bills: only 70 headliners had a bill of 2 to 4 named acts, and 18 survived
  (34 headliners not in Qloo under the same name, many of them venues or show titles; 18 with no bill-mate in Qloo).
  The protocol needs 20. Reading: **too few comedy bills to say**. The model arms were not run.

So the comedy version of "Kings" has no support, and Ticketmaster cannot supply enough comedy bills to test it.

## 47. Test 24: does Qloo's age skew find older acts young people took up? (Oct 14)

Registered in PREREGISTRATION_24.md (cb25d02). backtest24.py, backtest24_results.json. Outside record: three
published week-by-week lists of songs that trended on TikTok (2022 to 2024), 188 acts; 89 older by MusicBrainz;
60 found in Qloo; 52 sets of one trended act and its two closest same-era peers by fan overlap. One deviation: the
first run stopped on a dropped connection during the model step and was rerun from its cache.

| | All 52 sets | 48 sets without the earlier probe's acts |
|---|---|---|
| Trended act's under-25 score minus its peers' | +0.024 (-0.058 to 0.107) | +0.057 (-0.021 to 0.141) |
| Trended act has the youngest score of three (chance 0.333) | 0.346 (0.231 to 0.481) | 0.375 (0.25 to 0.50) |
| Trended act is the most popular of three | 0.50 (0.365 to 0.635) | 0.521 |
| Model alone scores the trended act highest | 0.663 (0.529 to 0.788) | 0.677 |
| Model with Qloo's age scores | 0.558 (0.423 to 0.692) | 0.604 |
| With Qloo minus alone | -0.106 (-0.26 to 0.058) | see results file |

- Reading 1: **not shown**. Qloo's age skew did not separate older acts that trended with young people from their
  peers; it was at chance. The probe's 0.792 on our own lists did not carry over.
- Reading 3: model with Qloo against alone, **no different**, with the point estimate lower.
- The model alone picked the trended act about twice as often as chance. It has read about these trends, so this
  is not a fair forecast, but it is the same pattern as Tests 14 to 18: on taste, the model alone does better than
  Qloo, and Qloo's numbers pull it down slightly.

So "Comeback" has no support from Qloo's age data.

## 48. Test 25: Qloo on its home ground (Oct 14 to 20)

Registered in PREREGISTRATION_25.md (d7f06d6). backtest25.py; results in backtest25_a/b/c_results.json. Deviations:
scipy's Spearman was replaced by an equivalent numpy one (a Windows policy blocked a scipy file); street addresses
for Part B came from NYC Open Data because our local copy has none; runs were resumed from cache after a CometAPI
credit stop (new key from the team) and two dropped connections.

- **A, small acts against ListenBrainz co-listening: too few small acts to say.** 279 of 300 artists real listeners
  play had Qloo popularity 0.5 or more; 4 seeds of the 15 needed. With Test 21 (2 of 95), Qloo's popularity scale
  puts almost every act people actually play in its top half.
- **B, 120 NYC restaurants opened after 2026-04-01: not shown.** Qloo held 66 (55%), 28 with a description or
  keywords. Cuisine right: model alone 0.683, with Qloo 0.658; difference -0.025 (-0.075 to 0.025). On the 66 found,
  0.682 alone and 0.667 with Qloo. Qloo knows about half of new places and adds nothing the name does not already say.
- **C, steadiness:** the model scoring the same 20 Test 15 lists twice agreed at Spearman 0.97 (0.956 to 0.981),
  AUC change 0.009; Qloo returned identical scores on 5 of 5 repeated requests. Both are steady; no case for Qloo
  on steadiness.

## 49. Test 27: small artists, real listeners (Oct 20 to 26)

Registered in PREREGISTRATION_27.md (d244ef8) with amendments (GPT-6 Astra through Kie, then CometAPI after Kie
flagged the team's accounts; same model throughout). backtest27.py, backtest27_results.json. GroupLens HetRec 2011
Last.fm data: 40 listeners, each with 3 to 5 small artists they really played (10 or fewer listeners in the data) hidden
among 30 small artists they did not.

| AUC | Mean (95% interval) |
|---|---|
| Qloo | 0.841 (0.80 to 0.879) |
| Fame | 0.516 (0.456 to 0.58) |
| GPT-6 Astra alone | 0.865 (0.827 to 0.901) |
| GPT-6 Astra with Qloo | 0.874 (0.84 to 0.906) |

- Qloo minus model alone: -0.024 (-0.052 to 0.006): **no different**. With Qloo minus alone: +0.010 (-0.001 to
  0.022): **no different**, just short of the bar. Qloo minus fame: +0.324: above.
- Qloo scored 99.3% of shortlist artists. The model said it did not know about 2.5 of 35 artists per list.
- The hidden artists had Qloo popularity 0.953 on average: small in this 2011 dataset, but well known by Qloo's
  scale, so "obscure" is again not reached. Qloo's real taste signal is strong (far above fame); a top model is as good.

## 50. Test 26: MLB theme nights against real attendance (Oct 20 to 26)

Registered in PREREGISTRATION_26.md (b39be0d) with amendments (model host changes only; GPT-6 Astra for every model
step). backtest26.py, backtest26_results.json. 2,425 home games of the 2026 MLB season; 336 theme nights (a promotion
named for a film, show, artist, game, book, franchise or brand). Outcome: log attendance against the same team's
other home games on the same kind of day.

| Spearman with the attendance lift (95% interval) | All 336 | Without near sellouts (322) |
|---|---|---|
| Qloo city affinity | 0.051 (-0.055 to 0.156) | 0.045 |
| Fame | -0.031 | -0.02 |
| GPT-6 Astra alone | 0.099 (-0.002 to 0.205) | 0.103 |
| GPT-6 Astra with Qloo | 0.08 | 0.089 |

- Reading: **not shown**; with Qloo against alone, **no different** (-0.019, -0.078 to 0.038). Qloo had an affinity
  for only 35% of the theme nights. Theme nights drew about 4% more than the team's usual crowd for that day
  (mean log lift 0.039), but how well the theme suits the city did not predict which drew more.

## 51 onward

From section 51 (Oct 28, 2026) the team built a new entry, Clash Court, in its own folder (clash-court/). Its log
continues there. Test 28's code (backtest28.py) runs from this folder; its protocol and result are copied there too.

## Oct 31: external Kaggle results table

A results table from a Kaggle run was added as KAGGLE_RESULTS.md without re-running it. 14 rows match recorded
tests. 10 rows (S3, S4/S4b, S8, S10, S12, S16, S17, S18, S21) contradict recorded results; the recorded results
stand because their data, code and protocol are committed. 6 rows have no matching test and are unverified.
PROGRESS.md added as a one-page status.
