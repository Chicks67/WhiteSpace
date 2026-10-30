# Product spec (working name: Whitespace)

## One line
For an independent restaurant founder in NYC choosing between lease addresses: city records rank
the leases by where the concept is already proving itself, and Qloo grounds how to position the
concept for the people around the chosen lease. Each source is used only where our tests say it works.

## User and job
An independent founder (or the SBDC / BID advisor helping them) with a concept chosen and two to
five candidate addresses. Decisions: which lease to sign; how to position the concept there
(brand voice, menu emphasis, music, décor cues, launch partners).

## The 30-second judge path
1. Landing page shows one prefilled brief: "Korean café, Queens, three lease addresses." No login.
2. Click Run. Within about 15 seconds (instant on a golden run) the page shows:
   - a map with the three addresses, existing same-cuisine restaurants and recent openings;
   - the lease ranking with its evidence label (Test 4, pre-registered: median within-cuisine AUC 0.851);
   - the positioning brief for the top lease, every line linked to its Qloo evidence;
   - the agent trace (each step, each Qloo status).
3. A toggle "Qloo taste" re-sorts the leases and explains: in Test 4 raw taste reached 0.760 vs 0.851
   for the city-records score, and adding it changed the score by +0.0015 (interval spans zero).

## Inputs
- Concept: one of the 14 tested cuisines (list in PREREGISTRATION.md), resolved to a Qloo tag
  with `qloo exec find_tags` and shown to the user for confirmation.
- Borough and 2 to 5 addresses, geocoded (NYC GeoSearch if reachable, else coordinates).

## Where layer (city data; this is the lease decision)
- Correction (Oct 10): the earlier "B2, pooled AUC 0.725" was pooled across cuisines and flattered B2;
  within a cuisine, density beat it in 11 of 14. Test 4 (PREREGISTRATION_3.md) then tested all blocks,
  including those that already have the cuisine (most real leases).
- Per address: its geohash-6 block. Score = Test 4 winner DS, per-cuisine logistic regression on
  D = log(1 + restaurants in block) and S = log(1 + same-cuisine restaurants in block and 8 neighbours),
  coefficients in lease_model.json. Median within-cuisine AUC 0.851 (D alone 0.822). Ties stay ties.
- Description shown per lease (not part of the score): named same-cuisine restaurants within
  400 m, openings of the concept since 2024 within 800 m, total restaurants in the cell.
- Mandatory caveats on screen: openings follow clusters; an opening is not success; records
  cover active restaurants only.

## Who-and-how layer (Qloo; this is the positioning decision)
Labelled descriptive, never predictive. For the top lease (or each lease, on request):
- Area over-index profile: tags, artists, brands, films for a POINT at the lease, each ranked by
  lift against the same query for an NYC-wide baseline. Raw top entities are generic (tested), so
  only lift is shown. Must be validated first (see Open checks).
- Concept audience: `urn:demographics` for the concept tag (six age bands, gender).
- Concept vs area: where the concept's typical audience and the area's audience differ, which
  drives what to lean into and what to downplay.
- Output: a positioning brief (audience, voice, menu emphasis, music, décor cues, partner
  brands), each line citing evidence IDs.

## Agent design
Fixed workflow with bounded agency (Anthropic "workflows before agents"):
1. Plan (LLM, one call): resolve concept, confirm tag, list the calls needed.
2. Fetch (code, parallel): city lookups, Qloo calls via a cached client; each response stored
   with an evidence ID, its request and its status.
3. Recover (LLM, capped loop of 3): only for `empty`, `partial` or ambiguous tag results.
4. Compute (code): lease scores, lift profiles, comparisons. No arithmetic in the LLM.
5. Write (LLM, structured output): brief lines reference evidence IDs and numbers by placeholder;
   code fills the values.
6. Verify (code): every placeholder resolves, no free-typed digits, superlatives match the
   computed ranking; failures trigger one rewrite.
Trace events stream to the UI over SSE.

## Evidence panel
Entries, in order:
1. Test 1 (cuisine heatmaps predict first openings): refuted. Protocol, results, mechanism.
2. Test 2 (music-audience heatmaps): refuted on mechanism and usefulness.
3. Supply source: Qloo lists 72 Korean places in Queens vs 198 in city records, so supply comes
   from city records.
4. Lease ranking: Test 4, DS 0.851 vs D 0.822; Qloo adds +0.0015 [-0.0003, 0.0037].
5. Point profiles: near-identical within 1.5 km, so they describe areas, not single leases.
Each entry: claim, result, caveat, confidence, links to protocol, code commit and raw responses.

## Reliability
- Golden runs: three prefilled briefs replay from stored responses with zero API calls.
- Cache every Qloo and city response; per-IP rate limit; global daily spend cap on the LLM.
- Health check endpoint; uptime monitoring through Nov 23.

## Stack
FastAPI backend (Python) with SSE; static frontend (one page, map via Leaflet); Docker image with
Node 22 and `@qloo/qloo-harness` for `find_tags`; hosted on a container platform (Render, Railway
or Fly). Keys only in server environment variables.

## Open checks before building (plumbing, not screening)
1. Area lift profile: is POINT-vs-NYC lift specific and different between areas about 5 km apart?
2. Geocoder reachable from the host.
3. `/v2/insights/compare` and `urn:demographics` outputs usable for concept vs area.

## Non-goals
No claim that Qloo predicts where to open. No second city. No Jensen term. No MCP server.

## Write-up (Devpost, in criterion order)
Technological implementation; design; potential impact; quality of the idea (two pre-registered
refutations, the mechanism, the architecture that follows from them); known limitations.
