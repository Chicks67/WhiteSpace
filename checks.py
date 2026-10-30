"""Trust checks: Qloo supply vs NYC inspection records, and whether cuisine heatmaps differ."""
import itertools

import numpy as np
import pygeohash as pgh

import nyc
import qloo

CUISINES = {  # Qloo tag, DOHMH cuisine labels
    "Korean": ("urn:tag:genre:place:restaurant:korean", {"Korean"}),
    "Vegan": ("urn:tag:genre:place:restaurant:vegan", {"Vegan", "Vegetarian"}),
    "Mexican": ("urn:tag:genre:place:restaurant:mexican", {"Mexican", "Tex-Mex"}),
}
BORO = {"Brooklyn": "Brooklyn", "Queens": "Queens"}


def qloo_supply(tag, area):
    out = []
    for page in range(1, 41):
        e = qloo.results(qloo.get("/v2/insights", **{
            "filter.type": "urn:entity:place", "filter.tags": tag, "take": 50, "page": page,
            "filter.location.query": area, "filter.location.radius": 0}), "entities")
        out += [p for p in e if p.get("location")]
        if len(e) < 50:
            break
    return out


def heat(tag, area):
    cells = qloo.results(qloo.get("/v2/insights", **{
        "filter.type": "urn:heatmap", "signal.interests.tags": tag,
        "filter.location.query": area, "filter.location.radius": 0}), "heatmap")
    return {c["location"]["geohash"][:7]: c["query"]["affinity"] for c in cells}


R = nyc.restaurants()
for area in BORO:
    print(f"\n== {area}: supply, Qloo vs city inspection records")
    for name, (tag, labels) in CUISINES.items():
        q = qloo_supply(tag, area)
        city = [r for r in R if r["boro"] == BORO[area] and r["cuisine"] in labels]
        qc = {pgh.encode(p["location"]["lat"], p["location"]["lon"], 6) for p in q}
        cc = {pgh.encode(r["lat"], r["lon"], 6) for r in city}
        print(f"  {name:8s} Qloo {len(q):4d} places in {len(qc):3d} cells | city {len(city):4d} in {len(cc):3d} cells"
              f" | city cells Qloo also marks: {len(qc & cc) / max(1, len(cc)):.0%}")

    print(f"== {area}: are cuisine heatmaps distinct? (Spearman over shared cells)")
    maps = {n: heat(t, area) for n, (t, _) in CUISINES.items()}
    maps["Any restaurant"] = heat("urn:tag:genre:place:restaurant", area)
    for a, b in itertools.combinations(maps, 2):
        keys = sorted(set(maps[a]) & set(maps[b]))
        ra = np.argsort(np.argsort([maps[a][k] for k in keys]))
        rb = np.argsort(np.argsort([maps[b][k] for k in keys]))
        print(f"  {a:15s} vs {b:15s} rho {np.corrcoef(ra, rb)[0, 1]:+.2f}  ({len(keys)} cells)")
