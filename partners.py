"""Real local businesses a founder could approach, found in code from city data (no model, no credits).

- Business improvement districts (BIDs) around the storefront, by distance to the district boundary.
- Complementary neighbours: independent food businesses within 400 m that serve the same people at another
  moment (coffee, bakery, dessert, juice) rather than competing for the same meal; categories the concept's own
  name overlaps with are left out (coffee for a "Korean cafe"). Independent = fewer than 5 locations in NYC
  inspection records. Nearest first.

Every name comes from NYC Open Data, so the brief's name check can trace it.
"""
import collections
import math
import re
from functools import lru_cache

import numpy as np
import shapely
from shapely.geometry import Point

import bids
import engine

COMPLEMENTS = {"Coffee/Tea": r"caf|coffee|tea|espresso|boba", "Bakery Products/Desserts": r"bak|dessert|pastr|sweet|cake",
               "Frozen Desserts": r"ice cream|gelato|dessert|frozen", "Juice, Smoothies, Fruit Salads": r"juice|smoothie",
               "Bagels/Pretzels": r"bagel", "Donuts": r"donut|doughnut"}  # DOHMH category: words in a concept that compete
KIND = {"Coffee/Tea": "coffee or tea", "Bakery Products/Desserts": "bakery", "Frozen Desserts": "dessert",
        "Juice, Smoothies, Fruit Salads": "juice bar", "Bagels/Pretzels": "bagels", "Donuts": "donuts"}
INSPECTIONS = "https://data.cityofnewyork.us/d/43nn-pn8j"


def _title(name):
    return re.sub(r"(?<=\w)'S\b", "'s", name.strip().title())


def _to_metres(lat):
    k = np.array([111320 * math.cos(math.radians(lat)), 110540])
    return lambda g: shapely.transform(g, lambda xy: xy * k)


def bids_near(lat, lon, radius=800):
    """BIDs whose boundary is within `radius` metres, nearest first; 0 m means the storefront is inside."""
    tree, polys, info = bids._index()
    f = _to_metres(lat)
    p = f(Point(lon, lat))
    out = []
    for i in tree.query(Point(lon, lat).buffer(radius / 80000)):
        d = f(polys[i]).distance(p)
        if d <= radius:
            out.append({**info[i], "metres": round(d)})
    return sorted(out, key=lambda b: b["metres"])


@lru_cache(maxsize=1)
def _locations():
    city = engine.city()
    return collections.Counter(r["dba"].strip().lower() for v in city.by_cell.values() for r in v)


def complements(concept, lat, lon, label="", radius=400, top=5):
    own = engine.CONCEPTS[concept][0]
    kinds = {k for k, words in COMPLEMENTS.items() if k != own and not re.search(words, (label or "").lower())}
    city, counts = engine.city(), _locations()
    found = []
    for c in {engine.g6(lat, lon)} | engine.neighbours(engine.g6(lat, lon)):
        for r in city.by_cell.get(c, []):
            if r["cuisine"] not in kinds or counts[r["dba"].strip().lower()] >= 5:
                continue
            d = engine.metres(lat, lon, r["lat"], r["lon"])
            if d <= radius:
                found.append({"name": _title(r["dba"]), "kind": KIND[r["cuisine"]], "metres": round(d)})
    seen, by_kind = set(), {}
    for x in sorted(found, key=lambda x: x["metres"]):
        if x["name"].lower() not in seen:
            seen.add(x["name"].lower())
            by_kind.setdefault(x["kind"], []).append(x)
    out = []  # nearest of each kind first, so a list is not five bakeries
    while len(out) < top and any(by_kind.values()):
        out += [v.pop(0) for v in sorted(by_kind.values(), key=lambda v: v[0]["metres"] if v else 1e9) if v]
    return sorted(out[:top], key=lambda x: x["metres"])


def for_lease(concept, lat, lon, label=""):
    return {"bids": bids_near(lat, lon)[:2], "complements": complements(concept, lat, lon, label), "source": INSPECTIONS}


if __name__ == "__main__":
    for addr in ["555 Waverly Avenue, Brooklyn", "136-20 38th Ave, Queens", "1054 Allerton Avenue, Bronx"]:
        g = engine.geocode(addr)
        print(addr, for_lease("Korean", g[2], g[3], "Korean cafe"))
