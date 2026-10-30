# Whitespace: submission text

**Live demo:** https://whitespace-nyc.vercel.app
**Code:** this repository (MIT licence, see `LICENSE`)

## In one line

An agent that helps an independent restaurant founder in New York City pick a storefront and size up every rival
around it, grounded in Qloo's record of real places: when each competitor closes, what its reviewers rave about, and
where its fans also go.

## The problem

Opening a restaurant is a bet on one block. A founder needs to know who is already there, when they close, what their
customers love, and what a new place could do differently. A general chatbot cannot answer that. Asked when 30 real
New York restaurants close on Friday, GPT-6 Astra alone got **0** right (it declined every time) and Gemini 3.8 Flash
got **3**, with 6 confident wrong times. It is the "culturally blind agent" the challenge describes, on the one block
that matters.

## What it does

1. **Scouts storefronts from a plain-language plan.** "College students on a budget, anywhere in Manhattan or
   Brooklyn, not next to other Korean places." A tool-calling agent picks neighbourhoods from census data, searches
   NYC's Storefront Registry for vacant storefronts, checks competition, cuisine fit and subway traffic, and submits a
   shortlist that code then checks (every address from this run's searches, every number from a tool result).
2. **Ranks the leases** with a score built on NYC inspection records (where operators of the cuisine actually opened).
3. **Sizes up every rival with Qloo.** For the top pick, the nearest competitors come from city records and Qloo adds
   each one's Friday closing time and what its reviewers mention, on a closing-time timeline. It also shows places
   Qloo tags with the cuisine that the city files elsewhere, and the neighbours that fans of the cuisine rate highest.
4. **Writes a positioning brief** from Qloo's evidence for the area, compared against a 10-area New York baseline so
   only what is distinctive about this neighbourhood is used. Every business the brief names is traced to Qloo or to
   city records, or marked unverified and repaired.
5. **Answers follow-up questions with twelve tools**, two of them Qloo tools for hours (`competitor_hours`,
   `place_hours`). The agent is told never to state opening hours from memory; numbers in an answer that appear in no
   tool result are flagged on the page.
6. **Scene explorer:** name up to three places your customers love; Qloo returns where their fans also go, and the
   music and brands that crowd follows.

7. **See the Qloo difference yourself.** A table of all 30 recorded answers behind Test 20 (Google Maps, each model
   alone, each model with Qloo), and a live "ask the model" duel beside every rival: one click asks GPT-6 Astra when the
   place closes on Friday, alone and with Qloo's record, side by side.

Every step and every Qloo call is shown live in an agent trace. Saved runs replay instantly with no API calls.

## What makes it Qloo-powered

Qloo is what lets the agent know real places. We measured it before building on it; each test's rules were committed
before its result:

| Question | Without Qloo | With Qloo |
|---|---|---|
| When does this NYC restaurant close on Friday? (30 places, Google Maps as truth) | GPT-6 Astra 0 of 30; Gemini 3.8 Flash 3 of 30 | 29 of 30 for both |
| Are Qloo's closing times right? (40 places checked by a person) | | 29 of 30 within 30 minutes |
| Which small artists does a real listener play? (40 listeners) | popularity: AUC 0.516 | Qloo: AUC 0.841 |
| A festival timetable that keeps shared fans apart | popularity: 0.043 of the possible gain | Qloo: 0.663 |

Without Qloo, the competition panel, the closing-time timeline, the hours answers, the brief's local evidence and the
scene explorer would all be empty or guessed. With it, the agent answers the questions a founder actually asks about
the block.

## How it is built

- Python FastAPI server; the agent loop uses GPT-6 Astra (OpenAI Responses-compatible API via CometAPI) with function
  calling, hedged requests and an Azure fallback.
- Qloo Insights API through a cached client with a monthly quota guard; a private warm cache ships with the server.
- NYC Open Data (restaurant inspections, Storefront Registry, business improvement districts, subway ridership),
  US Census ACS and LODES jobs data.
- Plain HTML, CSS and JavaScript page with a Leaflet map, dark and light modes, streamed over server-sent events.
- Hosted on Vercel. Keys stay on the server; live runs are rate limited per visitor with a daily model budget.
- 28 pre-registered tests, a reliability suite, and a full decision log in the repository.

## Results

Status of every test: PROGRESS.md. An external Kaggle results table, checked row by row against our
recorded tests: KAGGLE_RESULTS.md.

## Try it

1. Open https://whitespace-nyc.vercel.app and click a saved run: it replays a recorded live run in seconds.
2. Scroll to "What is around": the Friday closing-time timeline loads from Qloo.
3. Click "ask the model" beside a rival to see the model alone against the model with Qloo, live.
4. Under "Why Qloo", open "See all 30 answers".
5. Ask a follow-up such as "When do the competitors near the top lease close on Friday?"
6. Or run your own plan live (about a minute).
