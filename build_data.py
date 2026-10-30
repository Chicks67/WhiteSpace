"""Build step for a fresh server: download public city data and warm the Qloo cache the app needs.

Run once at deploy (needs QLOO_API_KEY). Downloads NYC inspection records, neighbourhood boundaries and the
Storefront Registry; fetches the Qloo cuisine heatmaps used by the comparison toggle and the evidence for the
10 reference areas used by the distinctiveness filter. Qloo responses stay in the server's local cache only;
nothing from Qloo is written to the repository.
"""
import time

import engine
import nyc
import positioning
import storefronts
import transit
import census
import bids

t = time.time()
print("restaurants", len(nyc.restaurants()))
print("neighbourhoods", len(nyc.ntas()))
print("vacant storefronts", len(storefronts.vacant()))
for concept in engine.CONCEPTS:
    print("taste map", concept, len(engine._heat(engine.CONCEPTS[concept][1])))
print("reference areas", len(positioning.reference()))
print("subway stations", len(transit.stations()))
print("business improvement districts", len(bids._index()[2]))
print("neighbourhood profiles", len(census.profiles()), "(needs CENSUS_API_KEY)")
print("lease score percentiles", [engine.city().percentile(c, 0) for c in list(engine.CONCEPTS)[:1]])
print(f"done in {time.time() - t:.0f} s")
