# Test 17: does Qloo know which cities an artist should play? Pre-registered protocol

Registered 2026-10-12, before any Test 17 code or comparison. The git commit adding this file is the timestamp.

## Why

The team is looking for uses where Qloo genuinely helps, on its home ground of entertainment. Test 15 found its
artist-to-artist links strong against real tour bills. Tour routing is the next question a promoter or agent asks:
which markets will turn out for this act. About twenty entries in this hackathon route tours from Qloo; the ones
that checked found raw affinity mostly follows popularity. The record of what really happens is public: the cities
an act is booked to play.

## What had been seen before this file

Qloo's scores for six hand-picked artists in five cities (Nashville, Miami, Boston, Los Angeles, Oklahoma City).
The highest-scored artists matched what a music fan would expect in each. No artist's real tour stops had been
compared with any Qloo score.

## Sample

- Markets: 40 large US metros, fixed in the code with a centre point and an approximate 2020 metro population.
- Shows: US Music events on Ticketmaster that went on sale 2026-08-15 to 2026-10-12 (the daily windows already
  fetched for Test 16). A show counts for a market if its venue is within 60 km of that market's centre (nearest
  market wins).
- Artists: every named act in those shows, with the markets it has a show in. An artist is eligible if it has shows
  in at least 5 and at most 30 of the 40 markets, so that both "plays" and "skips" exist. Eligible artists are
  sorted by name, shuffled with seed 17, and taken until 60 resolve in Qloo (first artist hit, same name after
  normalising) or all have been tried.

## Scorers: each an AUC per artist over the 40 markets (markets it plays are the positives)

- **Qloo affinity** of the artist among people in each market: /v2/insights for artists with the market's point
  and a 25 km radius as the location signal, filter.results.entities for the sampled artists. A market that
  returns no score for the artist counts lowest.
- **Market size:** the metro's population. Bigger markets get more shows, so this is the baseline to beat.
- **Language model:** GPT-6 Astra, given the artist's name and the 40 markets in shuffled order (seed 17), scores
  each from 0 to 100 for how likely the artist is to play there on its current US tour.
Mean over artists, 95% interval by bootstrap over artists (seed 0), and the same for each gain of Qloo over a
baseline.

## Outcomes and the sentence for each (fixed)

"Above" means the lower bound of the gain's interval is above 0. Qloo's own AUC must have its lower bound above 0.5
in every case but the last.

- **Above market size and the language model.** "Qloo's location signal picked the cities artists really play
  better than city size and better than a language model's own knowledge."
- **Above market size, not above the language model.** "Qloo knows where an artist's fans are, beyond city size.
  A language model alone did as well or better, so we make no claim that Qloo beats it."
- **Not above market size.** "Qloo's city scores did no better than city size at picking where artists play."
- **Qloo's AUC not above 0.5.** "Not shown."

## Amendment 1 (2026-10-12, before any result existed)

The first run was stopped while it was still fetching listings; it had scored nothing. A reviewer (DeepSeek)
raised circularity: Qloo's city scores may reflect where acts have played, and some cities host more tours than
their size suggests. The sample already uses only upcoming shows. One baseline is added to deal with the rest.

- **Market draw:** for each artist, a market's score is the share of the other sampled artists that have a show
  there. It needs no Qloo call. It stands for "this is a busy tour stop", whoever the act is.
- The outcomes change in one way: wherever they say "market size", read "market size and market draw". Qloo must
  be above both for the second and first outcomes; if it is above market size and not above market draw, the
  sentence is: "Qloo's city scores did no better than knowing which cities are busy tour stops."

Not controlled, and said so: an act may have played these cities on earlier tours, and Qloo may know that. For a
promoter that is a fair signal, but it means a pass shows Qloo knows where an act draws, not that it can find a
market the act has never tried.

## Limitations, stated before the result

Routing follows venue availability, distance between stops and promoter deals as much as demand, so no demand
signal can score near 1. Only shows on sale in a two-month window are seen, so "skips" include cities announced
earlier or later. The model may know announced tours. Qloo's scores may themselves reflect where the artist has
played. Populations are approximate. A pass shows the signal is real, not that a routing product is useful.
