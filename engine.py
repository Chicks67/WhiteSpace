"""Where layer: rank candidate lease addresses for one concept using NYC inspection records.

Score: Test 4's registered winner DS (PREREGISTRATION_3.md), a per-cuisine logistic regression on
D = log(1 + restaurants in the block) and S = log(1 + same-cuisine restaurants in the block and its 8
neighbours). On all blocks, 2024 to 2026, it found where a cuisine opened next at median within-cuisine
AUC 0.851, beating D alone in 12 of 14 cuisines; adding Qloo taste changed it by +0.0015 (interval
spans zero), so Qloo is not used for the lease decision. Coefficients: lease_model.json.
"""
import json
import math
import re
import os
import urllib.parse
import urllib.request
from functools import lru_cache

import pygeohash as pgh

import nyc

BOROUGHS = ["Brooklyn", "Queens", "Manhattan", "Bronx"]
SINCE = "2024-01-01"

# concept label -> (DOHMH cuisine, Qloo restaurant tag slug)
CONCEPTS = {
    "Korean": ("Korean", "korean"),
    "Mexican": ("Mexican", "mexican"),
    "Japanese": ("Japanese", "japanese"),
    "Thai": ("Thai", "thai"),
    "Indian": ("Indian", "indian"),
    "Caribbean": ("Caribbean", "caribbean"),
    "Coffee shop": ("Coffee/Tea", "coffee_shop"),
    "Bakery": ("Bakery Products/Desserts", "bakery"),
    "Chinese": ("Chinese", "chinese"),
    "Pizza": ("Pizza", "pizza"),
    "Italian": ("Italian", "italian"),
    "Mediterranean": ("Mediterranean", "mediterranean"),
    "Latin American": ("Latin American", "latin_american"),
    "Middle Eastern": ("Middle Eastern", "middle_eastern"),
}
# Added by Test 4b (PREREGISTRATION_6.md): inspection categories where the city-records lease score passed the
# pre-registered rule on all blocks. Their lease models are fitted on all blocks (no Qloo feature involved).
CONCEPTS_4B = {
    "American": ("American", "american"),
    "New American": ("New American", "new_american"),
    "Chicken": ("Chicken", "chicken"),
    "Burgers": ("Hamburgers", "burgers"),
    "Sandwich shop": ("Sandwiches", "sandwich_shop"),
    "Seafood": ("Seafood", "seafood"),
    "Spanish": ("Spanish", "spanish"),
    "Asian fusion": ("Asian/Asian Fusion", "asian_fusion"),
    "Juice bar": ("Juice, Smoothies, Fruit Salads", "juice_shop"),
    "Ice cream and frozen desserts": ("Frozen Desserts", "ice_cream_shop"),
    "Bagel shop": ("Bagels/Pretzels", "bagel_shop"),
}
CONCEPTS = {**CONCEPTS, **CONCEPTS_4B}


def g6(lat, lon):
    return pgh.encode(lat, lon, 6)


def neighbours(cell):
    lat, lon, dlat, dlon = pgh.decode_exactly(cell)
    return {pgh.encode(lat + i * 2 * dlat, lon + j * 2 * dlon, 6)
            for i in (-1, 0, 1) for j in (-1, 0, 1) if (i, j) != (0, 0)}


def metres(lat1, lon1, lat2, lon2):
    x = math.radians(lon2 - lon1) * math.cos(math.radians((lat1 + lat2) / 2))
    return 6371000 * math.hypot(x, math.radians(lat2 - lat1))


with open(os.path.join(os.path.dirname(__file__), "lease_model.json")) as _f:
    MODEL = json.load(_f)


class LeaseError(Exception):
    pass


_GENERIC = {"st", "street", "ave", "av", "avenue", "rd", "road", "blvd", "boulevard", "pl", "place", "dr", "drive",
            "ln", "lane", "pkwy", "parkway", "e", "w", "n", "s", "east", "west", "north", "south", "ny", "new", "york",
            "nyc", "usa", "apt", "unit", "suite", "ste", "fl", "floor", "the", "of", "and", "at"}
_BORO_WORDS = {"Brooklyn": ["brooklyn", "bklyn"], "Queens": ["queens"] + "flushing astoria jamaica bayside woodside "
               "sunnyside corona elmhurst ridgewood woodhaven".split(), "Manhattan": ["manhattan"],
               "Bronx": ["bronx"], "Staten Island": ["staten island"]}


def _tokens(text):
    t = re.sub(r"\b(\d+)(st|nd|rd|th)\b", r"\1", text.lower())
    return set(re.findall(r"[a-z]+|\d+", t))


def _street_ok(asked, label):
    """The street the founder typed must appear in the match: '123 Fake Street' must not become '123 West 123 Street'."""
    a = re.sub(r"^\s*[\d-]+\s+", "", asked.split(",")[0])  # drop the house number
    want = {w for w in _tokens(a) if w not in _GENERIC and not any(w in v for v in _BORO_WORDS.values())}
    return not want or bool(want & _tokens(label.split(",")[0]))


def _named_borough(text):
    t = " " + text.lower() + " "
    hits = {b for b, words in _BORO_WORDS.items() if any(f" {w}" in t for w in words)}
    return hits.pop() if len(hits) == 1 else None


@lru_cache(maxsize=512)
def _geosearch(address):
    url = "https://geosearch.planninglabs.nyc/v2/search?" + urllib.parse.urlencode({"text": address, "size": 5})
    try:
        feats = json.load(urllib.request.urlopen(url, timeout=20)).get("features", [])
    except Exception as e:
        raise LeaseError(f"geocoder unavailable: {e}")
    if not feats:
        raise LeaseError(f"address not found: {address}")
    boro = _named_borough(address)
    ok = [f for f in feats if _street_ok(address, f["properties"].get("label", ""))]
    if not ok:
        raise LeaseError(f"address not found: {address} (closest match was {feats[0]['properties'].get('label')}, "
                         "a different street)")
    if boro:
        inb = [f for f in ok if f["properties"].get("borough") == boro]
        if not inb:
            raise LeaseError(f"address not found in {boro}: {address} (the closest match is "
                             f"{ok[0]['properties'].get('label')}, in {ok[0]['properties'].get('borough')})")
        return inb[0]
    return ok[0]


def places(text, n=3):
    """Named places (venues first) from NYC GeoSearch: [(label, borough, lat, lon, layer)]."""
    url = "https://geosearch.planninglabs.nyc/v2/search?" + urllib.parse.urlencode({"text": text, "size": n})
    try:
        feats = json.load(urllib.request.urlopen(url, timeout=20)).get("features", [])
    except Exception as e:
        raise LeaseError(f"geocoder unavailable: {e}")
    out = [(f["properties"].get("label"), f["properties"].get("borough"), f["geometry"]["coordinates"][1],
            f["geometry"]["coordinates"][0], f["properties"].get("layer")) for f in feats]
    return sorted(out, key=lambda x: x[4] != "venue")


def geocode(address):
    """NYC Planning Labs GeoSearch: (label, borough, lat, lon, neighbourhood)."""
    f = _geosearch(address)
    p, (lon, lat) = f["properties"], f["geometry"]["coordinates"]
    return p.get("label", address), p.get("borough"), lat, lon, p.get("neighbourhood")


def bbl(address):
    """Tax lot (borough-block-lot) of an address, or None."""
    try:
        return (_geosearch(address)["properties"].get("addendum") or {}).get("pad", {}).get("bbl")
    except LeaseError:
        return None


class City:
    """Restaurant records indexed by geohash-6 block. Built once per process."""

    def __init__(self):
        self.rest = [r for r in nyc.restaurants() if r["boro"] in BOROUGHS]
        self.by_cell = {}
        for r in self.rest:
            self.by_cell.setdefault(g6(r["lat"], r["lon"]), []).append(r)
        counts = sorted(len(v) for v in self.by_cell.values())
        self.counts = counts

    def density_percentile(self, n):
        """Share of restaurant blocks with fewer restaurants than n."""
        lo = sum(1 for c in self.counts if c < n)
        return round(100 * lo / len(self.counts))

    def nearby(self, lat, lon, radius, cuisine=None, since=None):
        cell = g6(lat, lon)
        cells = {cell} | neighbours(cell)
        out = []
        for c in cells:
            for r in self.by_cell.get(c, []):
                if cuisine and r["cuisine"] != cuisine:
                    continue
                if since and not (r["opened"] and r["opened"] >= since):
                    continue
                d = metres(lat, lon, r["lat"], r["lon"])
                if d <= radius:
                    out.append({"name": re.sub(r"(?<=\w)'S\b", "'s", r["dba"].title()), "cuisine": r["cuisine"], "metres": round(d),
                                "opened": r["opened"], "lat": r["lat"], "lon": r["lon"]})
        return sorted(out, key=lambda x: x["metres"])

    def percentile(self, concept, score):
        """Share of NYC restaurant blocks (four boroughs) whose lease score for this concept is below `score`."""
        if not hasattr(self, "_dist"):
            self._dist = {}
        if concept not in self._dist:
            m, cuisine = MODEL[concept], CONCEPTS[concept][0]
            cnt = {c: sum(1 for r in v if r["cuisine"] == cuisine) for c, v in self.by_cell.items()}
            self._dist[concept] = sorted(
                m["intercept"] + m["D"] * math.log1p(len(v)) + m["S"] * math.log1p(cnt[c] + sum(cnt.get(n, 0) for n in neighbours(c)))
                for c, v in self.by_cell.items())
        d = self._dist[concept]
        return round(100 * sum(1 for x in d if x < score) / len(d))

    def score(self, concept, lat, lon):
        cuisine = CONCEPTS[concept][0]
        cell = g6(lat, lon)
        here = self.by_cell.get(cell, [])
        n = len(here)
        same_here = sum(1 for r in here if r["cuisine"] == cuisine)
        same_area = same_here + sum(1 for c in neighbours(cell) for r in self.by_cell.get(c, []) if r["cuisine"] == cuisine)
        m = MODEL[concept]
        return {
            "block": cell,
            "density": n,
            "density_percentile": self.density_percentile(n),
            "same_cuisine_in_block": same_here,
            "same_cuisine_area": same_area,   # this block and its 8 neighbours
            "score": round(m["intercept"] + m["D"] * math.log1p(n) + m["S"] * math.log1p(same_area), 3),
            "score_percentile": self.percentile(concept, m["intercept"] + m["D"] * math.log1p(n) + m["S"] * math.log1p(same_area)),
            "same_cuisine_400m": self.nearby(lat, lon, 400, cuisine),
            "openings_800m": self.nearby(lat, lon, 800, cuisine, SINCE),
            "all_400m": len(self.nearby(lat, lon, 400)),
        }


@lru_cache(maxsize=16)
def _heat(slug):
    import backtest  # Qloo cuisine heatmaps by borough, exactly as in Test 1
    agg = {}
    for gh, (a, _, _) in backtest.heatmap(f"urn:tag:genre:place:restaurant:{slug}").items():
        agg.setdefault(gh[:6], []).append(a)
    return {k: sum(v) / len(v) for k, v in agg.items()}


def taste(concept, leases):
    """Qloo taste score (Test 1 M1: mean cuisine heatmap affinity in the block), for the comparison toggle only."""
    heat = _heat(CONCEPTS[concept][1])
    out = [{"address": l["address"], "taste": round(heat[l["block"]], 3) if l["block"] in heat else None} for l in leases]
    for x in out:
        x["rank"] = 1 + sum(1 for y in out if (y["taste"] or -1) > (x["taste"] or -1))
    return out


@lru_cache(maxsize=1)
def city():
    return City()


def rank(concept, leases, keep_order=False):
    """leases: list of dicts with 'address' and optional 'lat'/'lon'. Returns scored leases, best first.

    Equal scores share a rank (for example two leases in the same block): the data cannot separate them.
    """
    if concept not in CONCEPTS:
        raise LeaseError(f"concept must be one of: {', '.join(CONCEPTS)}")
    out = []
    for l in leases:
        if "lat" in l and "lon" in l:
            label, boro, lat, lon, hood = l["address"], l.get("borough"), l["lat"], l["lon"], l.get("neighbourhood")
        else:
            label, boro, lat, lon, hood = geocode(l["address"])
            l = {**l, "storefront": l.get("storefront") or {"bbl": bbl(l["address"])}}
        if boro and boro not in BOROUGHS:
            raise LeaseError(f"{label}: {boro} was not covered by our tests (Brooklyn, Queens, Manhattan, Bronx only)")
        out.append({"address": label, "borough": boro, "neighbourhood": hood, "lat": lat, "lon": lon,
                    "storefront": l.get("storefront"), **city().score(concept, lat, lon)})
    if keep_order:  # scout mode: the agent's order (it weighs the founder's constraints); scores shown alongside
        for i, x in enumerate(out):
            x["rank"] = i + 1
        return out
    out.sort(key=lambda x: -x["score"])
    for x in out:
        x["rank"] = 1 + sum(1 for y in out if y["score"] > x["score"])
    return out


if __name__ == "__main__":
    for x in rank("Korean", [{"address": "136-20 38th Ave, Queens"},
                             {"address": "41-08 Bell Blvd, Queens"},
                             {"address": "35-01 Union St, Queens"}]):
        print(x["rank"], x["address"], x["score"], x["density"], x["same_cuisine_area"],
              len(x["same_cuisine_400m"]), len(x["openings_800m"]))
