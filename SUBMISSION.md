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

7. **See the Qloo difference yourself.** A table of all 30 recorded answers behind the closing-time check (Google Maps, each model
   alone, each model with Qloo), and a live "ask the model" duel beside every rival: one click asks GPT-6 Astra when the
   place closes on Friday, alone and with Qloo's record, side by side.

8. **Play with the city itself.** The page opens on a dot map of all 26,043 active restaurants and 6,767 vacant
   storefronts in the four boroughs: click any block to score it. Drop up to three pins on a street map (or type an
   address), compare them, and move what-if sliders to see how the score responds.
9. **Two games on real results.** Guess when a real restaurant closes on Friday against GPT-6 Astra alone and with
   Qloo's record, then "Qloo or the baseline?", eight rounds over the tests where Qloo won.

Every step and every Qloo call is shown live in an agent radar and trace. Finished runs play back instantly with no API
calls, and if a live run cannot run, the page shows the finished run closest to the plan, labelled as such.

## The business

About 3,000 new restaurants open in the four boroughs each year (3,034 that opened in 2025 are still operating, from
city inspection records), and 6,767 storefronts are reported vacant. A site report for founders and paid listings for
landlords are the two revenue lines; the page carries an estimate whose shares and prices the visitor sets.

## What makes it Qloo-powered

Qloo is what lets the agent know real places. We measured it before building on it; each test's rules were committed
before its result:

| Question | Without Qloo | With Qloo |
|---|---|---|
| When does this NYC restaurant close on Friday? (30 places, Google Maps as truth) | GPT-6 Astra 0 of 30; Gemini 3.8 Flash 3 of 30 | 29 of 30 for both |
| Are Qloo's closing times right? (30 places checked by a person against Google Maps) | | 29 of 30 within 30 minutes, all 29 exact |
| Does Qloo find the real competitors? | | 92.4% of them |
| Do raters prefer the brief written with Qloo? (blind) | | 78% of the time |
| Which storefront block gets the next opening of a cuisine? (AUC) | city records alone: 0.851 | with Qloo: 0.893 |

Without Qloo, the competition panel, the closing-time timeline, the hours answers, the brief's local evidence and the
scene explorer would all be empty or guessed. With it, the agent answers the questions a founder actually asks about
the block.

## How it is built

- Python FastAPI server; the agent loop uses GPT-6 Astra (OpenAI Responses-compatible API via Kie, with CometAPI as an alternative provider) with function
  calling, hedged requests and an Azure fallback.
- Qloo Insights API through a cached client with a monthly quota guard; a private warm cache ships with the server.
- NYC Open Data (restaurant inspections, Storefront Registry, business improvement districts, subway ridership),
  US Census ACS and LODES jobs data.
- Plain HTML, CSS and JavaScript page: a canvas dot map of the city, a Leaflet pin map, charts in SVG, day and night
  themes, runs streamed over server-sent events. No build step.
- Hosted on Vercel. Keys stay on the server; live runs are rate limited per visitor with a daily model budget.
- 13 pre-registered tests, a reliability suite, and a full decision log in the repository.

## Results

Every test, its question and its result: README "What we tested", and on the page under Results and How we know.
Status notes: [PROGRESS.md](PROGRESS.md).

## Try it

1. Open https://whitespace-nyc.vercel.app and click any block on the city map to score it.
2. Click a finished run: it plays back a recorded live run in seconds.
3. Scroll to "What is around": the Friday closing-time timeline loads from Qloo.
4. Click "ask the model" beside a rival to see the model alone against the model with Qloo, live.
5. Under "Why Qloo", see the four pie charts and open "See all 30 answers"; then play both games.
6. Ask a follow-up such as "When do the competitors near the top lease close on Friday?"
7. Or scout your own plan live (about a minute).
