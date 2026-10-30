# Handoff: context from the first build conversation (Oct 9 to 12, 2026)

Read with CLAUDE.md (rules, state) and PROJECT_LOG.md (full record). This file holds what only the chat had.

## How the team wants to work

- Agent quality first; the write-up stays light until the end (the team said so explicitly). Wording polish later.
- Credits are the team's call; do not lecture about them. One funded CometAPI account is the working setup.
- Be honest and direct; disagree with reasons; credit good results plainly. No em or en dashes in any text.
- Reviews from another model (DeepSeek) are pasted in often. Treat them as input: act on valid points, push back
  with reasons on the rest. Several of its claims were wrong or unverified (see below).
- Both team members use one Claude account.

## Decisions and why

- Each data source only where a pre-registered test says it works. City records rank locations (Test 4, median
  within-cuisine AUC 0.851). Census says who lives or works somewhere (Qloo audience tags matched census for only
  2 of 7, Test 6). Qloo was kept for positioning text; Test 8 now says a nearby-business list does better.
- Scout mode (founder describes a plan) is the headline path; "my addresses" and "search an area" are secondary.
- Cuisine fit (lease-score percentile) guards against reading "no competitors" as an opening when it means no
  demand (the seniors/Caribbean/City Island failure). Weak-fit picks are sent back once in code.
- Test 4b extended the lease score to 11 more cuisines (25 total), coverage 50% to 83% of active restaurants.
- Saved runs and the Qloo cache never go in a public repo (Qloo Support on Discord). Public redacted replays and
  SHA256SUMS in fixtures/replays; /api/golden/<id>/sha256 lets a judge check a live replay.
- Staten Island stops in code: the city publishes its data but our tests did not cover it and we did not load it.
- "Not measured here" notes (rent, hours, nightlife, neighbourhood change) sit below a "Measured for every pick"
  list on scout shortlists.
- Option chosen for direction (Oct 11): "what should open here" headline was proposed, gated on Test 8. Test 8
  failed for Qloo, so no rebuild. Open decision: what the brief uses, after Test 3's human verdict.

## Things tried and rejected

- AgentRouter: its firewall serves a JavaScript bot check to any server request; bypassing it was declined. Its
  keys work only from personal machines for coding tools.
- OmniRush: no API key found; chat-only credits cannot run the agent. Earlier listed as unverified.
- Vercel AI Gateway: valid key but needs a card on the account.
- Kie: works but stalls 1 to 4 minutes on about a third of turns; now a fallback only.
- Azure gpt-5-mini fallback: wired (hedged duplicate goes to Azure if AZURE_* settings exist), never configured.
- Reviewer suggestions not taken: obscure-entity music/film test (ground truth = the LLM's own training data);
  ancestry-vs-Qloo test (Qloo reflects active taste including visitors, not residents); abort turns at 30 s;
  running evals on a cheaper model; committing full replays to git (violates Qloo's rule).

## Lessons from running things

- CometAPI reserves a request's maximum output cost before running it: a tiny test call can pass while real runs
  fail on "pre-consume quota failed". Test with max_output_tokens 3000 before trusting a key.
- Several CometAPI keys shared near-empty balances; a new key does not add credit, the account does.
- Gemini free tier limits by tokens: short prompts pass while long judge prompts get 429. CometAPI also serves
  gemini-3.8-flash.
- Running six live runs at once hit provider concurrency; run eval batches one at a time.
- Do not use `pkill -f` with patterns that match your own shell command; it kills the shell (exit 144).
- Never print per-case results from a blind test's progress log (two Test 8 rankings were seen this way).

## Open items (also in CLAUDE.md)

1. Test 3: two human raters on blind_sheet.md, then the Gemini judge and the reveal. It is the human check on
   Test 8 and decides how the brief uses Qloo.
2. Product decision on the brief and the framing of the seven-test audit in the write-up.
3. GitHub (the team's repository, private until near the deadline), Render deploy with the private disk, restart test.
4. Three or four real NYC founders or brokers trying it, quotes with permission.
5. Write-up in the kit's six-item format (check docs/SUBMISSION.md in qloo-hackathon-kit); the team writes the
   opening paragraph.
6. The "busy, try again" error path has never been triggered live.
