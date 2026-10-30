"""Find vacant storefronts from NYC's Storefront Registry (Local Law 157, dataset 92iy-9c3n) and score them.

Owners of ground-floor and second-floor commercial space report each year whether it was vacant. We keep
the latest report per storefront: 2025 filings (vacant on June 30, 2025, partial year so far) and 2024
filings (vacant on Dec 31, 2024). A storefront reported vacant may since have been leased; the age of the
report is shown with every result. Each storefront's block is scored with the Test 4 lease score.
"""
import json
import os
import re
import urllib.parse
import urllib.request
from functools import lru_cache

import engine

URL = "https://data.cityofnewyork.us/resource/92iy-9c3n.json?"
PATH = os.path.join(os.path.dirname(__file__), "data", "storefronts_vacant.json")
BOROUGHS = {b.upper(): b for b in engine.BOROUGHS}


def _get(**p):
    return json.load(urllib.request.urlopen(URL + urllib.parse.urlencode(p), timeout=300))


def _download():
    sel = ("reporting_year, borough, nbhd, property_street_address_or, primary_business_activity, "
           "latitude, longitude, bbl, vacant_on_12_31, vacant_6_30_or_date_sold")
    rows = []
    for where in ("reporting_year='2025' AND (vacant_on_12_31='YES' OR vacant_6_30_or_date_sold='YES')",
                  "reporting_year='2024' AND vacant_on_12_31 in ('YES','Y')",
                  "reporting_year='2024' AND vacant_on_12_31 not in ('YES','Y')"):
        rows += _get(**{"$select": sel, "$where": where + " AND latitude IS NOT NULL", "$limit": 100000})
    latest = {}
    for r in rows:  # keep the newest report per storefront
        k = (r.get("bbl"), r.get("property_street_address_or"))
        if k not in latest or r["reporting_year"] > latest[k]["reporting_year"]:
            latest[k] = r
    out = []
    for r in latest.values():
        vacant = (r.get("vacant_on_12_31") in ("YES", "Y") or r.get("vacant_6_30_or_date_sold") == "YES")
        if not vacant or r.get("borough") not in BOROUGHS:
            continue
        use = (r.get("primary_business_activity") or "").title()
        addr = re.sub(r"(\d)(St|Nd|Rd|Th)\b", lambda m: m.group(1) + m.group(2).lower(),
                      r["property_street_address_or"].title())
        addr = re.sub(r"\s+(Coml|Comm|Store|Str)\b\.?$", "", addr)  # registry suffixes for the commercial unit
        out.append({
            "address": addr, "borough": BOROUGHS[r["borough"]],
            "neighbourhood": r.get("nbhd"), "lat": float(r["latitude"]), "lon": float(r["longitude"]),
            "reported": "June 30, 2025" if r["reporting_year"] == "2025" else "Dec 31, 2024",
            "last_use": None if use.startswith("No Business") or not use else use,
            "bbl": r.get("bbl"),
        })
    os.makedirs(os.path.dirname(PATH), exist_ok=True)
    json.dump(out, open(PATH, "w"))


_TYPE = (r"(?:Street|St|Avenue|Ave|Av|Road|Rd|Boulevard|Blvd|Place|Pl|Parkway|Pkwy|Drive|Dr|Lane|Ln|Broadway|"
         r"Concourse|Plaza|Terrace|Turnpike|Highway|Square|Court|Ct|Way|Bowery|Expressway|Americas)")
_KEEP_TAIL = re.compile(r"(?:North|South|East|West|Extension|Of The Americas)", re.I)


def _ordinal(n):
    n = int(n)
    return f"{n}{'th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"


def clean_address(a):
    """Registry addresses as people write them: '37 -53 Junction Blvd' -> '37-53 Junction Blvd',
    '358 East 51th Street' -> '358 East 51st Street', '229 East 2 Street' -> '229 East 2nd Street',
    '151 East 58 Street Retl1' -> '151 East 58th Street' (unit codes after the street name are dropped).
    Directions, 'Avenue Of The Americas' and Avenue A to Z (Brooklyn) are kept."""
    a = re.sub(r"^(\d+) ?- ?(\d+)", r"\1-\2", a.strip())
    a = re.sub(r"\bOf The Amer(?:icas)?\b", "Of The Americas", a)
    a = re.sub(r"\.?,\s*(?:[A-Za-z .#]+,\s*)*Ny\b.*$", "", a)  # ', New York, Ny 10022'
    a = re.sub(r"\s+(?:New York|Brooklyn|Bronx|Queens|Ny)\s*,?\s*Ny\b.*$", "", a)  # ' Ny, Ny 10027'
    a = re.sub(r"\bExpre$", "Expressway", a)
    a = re.sub(r"\b(\d+)(?:st|nd|rd|th)\b", lambda m: _ordinal(m.group(1)), a, flags=re.I)
    ms = list(re.finditer(r"\b" + _TYPE + r"\b", a))
    if ms:
        last, tail = ms[-1], a[ms[-1].end():].strip(" ,.")
        avenue_letter = last.group(0) in ("Avenue", "Ave", "Av") and re.fullmatch(r"[A-Z]", tail)
        if tail and not avenue_letter and not _KEEP_TAIL.fullmatch(tail) and len(tail.split()) <= 3:
            a = a[:last.end()]
    a = a.rstrip(" .,")
    # bare street numbers: any number after the house number that is followed by a street type
    a = re.sub(r"(?<=\s)(\d+)(?=\s+" + _TYPE + r"\b)", lambda m: _ordinal(m.group(1)), a)
    return re.sub(r"\s{2,}", " ", a).strip()


PLUTO_PATH = os.path.join(os.path.dirname(__file__), "data", "pluto_lot_addresses.json")


def _pluto_queens(records):
    """The registry drops the hyphenated part of many Queens addresses ('30 Steinway Street' for
    '30-60 Steinway Street'). PLUTO (64uk-42ks) has each lot's address; fetched once by BBL and cached."""
    if os.path.exists(PLUTO_PATH):
        return json.load(open(PLUTO_PATH))
    bbls = sorted({r["bbl"] for r in records if r.get("bbl") and (r["borough"] == "Queens" or not _numbered(r["address"]))})
    out = {}
    for i in range(0, len(bbls), 150):
        part = bbls[i:i + 150]
        rows = json.load(urllib.request.urlopen("https://data.cityofnewyork.us/resource/64uk-42ks.json?" + urllib.parse.urlencode(
            {"$select": "bbl,address", "$where": "bbl in (" + ",".join(f"'{b}'" for b in part) + ")", "$limit": 1000}), timeout=120))
        out.update({str(int(float(r["bbl"]))): r["address"] for r in rows if r.get("address")})
    json.dump(out, open(PLUTO_PATH, "w"))
    return out


def _numbered(a):
    return bool(re.match(r"^\d", a.strip()))


def _street(a):
    return " ".join(_norm(re.sub(r"^[\d\- ]+", "", clean_address(a.title()))))


def _queens_fix(s, pluto):
    lot = pluto.get(s.get("bbl") or "")
    if lot and not _numbered(s["address"]) and _numbered(lot):  # no house number in the report: use the lot's
        return clean_address(lot.title())
    if s["borough"] != "Queens" or re.match(r"^\d+[A-Z]?-\d+", s["address"]):
        return s["address"]
    if lot and _street(lot) == _street(s["address"]) and re.match(r"^\d+-\d+ ", lot):
        return lot.split(" ", 1)[0] + " " + re.sub(r"^[\d\- ]+", "", s["address"])
    return s["address"]


@lru_cache(maxsize=1)
def vacant():
    if not os.path.exists(PATH):
        _download()
    raw = json.load(open(PATH))
    try:
        pluto = _pluto_queens(raw)
    except Exception:  # noqa: BLE001 - the registry address still works without the repair
        pluto = {}
    out = [{**s, "address": clean_address(s["address"])} for s in raw]
    out = [{**s, "address": _queens_fix(s, pluto)} for s in out]
    # a few reports give only a unit number or only a street name; a founder cannot act on those
    # 55 reports carry coordinates of (0, 0); a storefront we cannot place cannot be scored
    return [s for s in out if re.search(r"[A-Za-z]{3,}", s["address"]) and _numbered(s["address"])
            and 40.49 <= s["lat"] <= 40.92 and -74.27 <= s["lon"] <= -73.68
            and not re.search(r"\s(st|nd|rd|th)\s", s["address"])]  # '132-07 th Avenue': street number lost


def _norm(s):
    return re.sub(r"[^a-z ]", " ", (s or "").lower()).split()


@lru_cache(maxsize=1)
def areas():
    """Neighbourhood names used in the registry, with their borough."""
    out = {}
    for s in vacant():
        if s["neighbourhood"]:
            out.setdefault((s["neighbourhood"], s["borough"]), 0)
            out[(s["neighbourhood"], s["borough"])] += 1
    return out


def _parts(name):
    """'Astoria (North)-Ditmars-Steinway' -> {'astoria', 'ditmars', 'steinway'}"""
    return {" ".join(_norm(re.sub(r"\(.*?\)", "", p))) for p in name.split("-")} - {""}


def match_area(text):
    """Neighbourhoods named in the text, matched in code against registry names (NTA 2020 names).
    Returns a list of (neighbourhood, borough); [("*", borough)] for a whole borough."""
    exact = [(n, b) for (n, b) in areas() if n.lower() == text.strip().lower()
             or f"{n}, {b}".lower() == text.strip().lower()]
    if exact:
        return exact
    words = " " + " ".join(_norm(text)) + " "
    boro = next((b for b in engine.BOROUGHS if f" {b.lower()} " in words or f" the {b.lower()} " in words), None)
    hits = [(n, b) for (n, b) in areas() if (boro is None or b == boro)
            and any(f" {p} " in words for p in _parts(n))]
    if not hits and boro:
        return [("*", boro)]
    return sorted(hits)


def find(concept, places, top=5, per_block=1):
    """Best-scoring vacant storefronts in the given areas [(neighbourhood or "*", borough)]: one per block,
    Test 4 score first; within a block, last used for food services first, then the newer report."""
    if concept not in engine.CONCEPTS:
        raise engine.LeaseError(f"concept must be one of: {', '.join(engine.CONCEPTS)}")
    want = set(places)
    pool = [s for s in vacant() if (s["neighbourhood"], s["borough"]) in want or ("*", s["borough"]) in want]
    if not pool:
        raise engine.LeaseError("no vacant storefronts reported in " + ", ".join(f"{n}, {b}" for n, b in places))
    city = engine.city()
    scored = {}
    for s in pool:
        cell = engine.g6(s["lat"], s["lon"])
        if cell not in scored:
            scored[cell] = city.score(concept, s["lat"], s["lon"])["score"]
        s = {**s, "block": cell, "score": scored[cell], "food": s["last_use"] == "Food Services"}
        scored.setdefault(("list", cell), []).append(s)
    blocks = sorted({k for k in scored if isinstance(k, str)}, key=lambda c: -scored[c])
    out = []
    for cell in blocks:
        cands = sorted(scored[("list", cell)], key=lambda s: (not s["food"], s["reported"] != "June 30, 2025"))
        out += cands[:per_block]
        if len(out) >= top:
            break
    return out, {"storefronts_in_area": len(pool), "blocks_in_area": len(blocks)}


if __name__ == "__main__":
    v = vacant()
    print(len(v), "vacant storefronts;", sum(s["last_use"] == "Food Services" for s in v), "last used for food services")
    for q in ["Astoria", "Flushing, Queens", "Park Slope", "Bushwick Brooklyn", "the Bronx", "Williamsburg", "Jackson Heights", "Crown Heights"]:
        print(q, "->", match_area(q))
    res, info = find("Korean", match_area("Astoria"))
    print(info)
    for s in res:
        print(s["score"], s["address"], s["reported"], s["last_use"])


_HYPHENATED = ("Bedford-Stuyvesant", "Co-op City", "Prospect-Lefferts", "Stuyvesant Town-Peter Cooper Village")


def short_name(nta):
    """'Astoria (North)-Ditmars-Steinway' -> 'Astoria'; names that contain a hyphen stay whole
    ('Co-op City', 'Bedford-Stuyvesant (East)' -> 'Bedford-Stuyvesant')."""
    n = re.sub(r"\s*\(.*?\)", "", nta or "").strip()
    keep = next((h for h in _HYPHENATED if n.startswith(h)), None)
    return keep or n.split("-")[0].strip() or None


def as_leases(found):
    return [{"address": f"{s['address']}, {s['borough']}", "lat": s["lat"], "lon": s["lon"], "borough": s["borough"],
             "neighbourhood": short_name(s["neighbourhood"]),
             "storefront": {"reported": s["reported"], "last_use": s["last_use"], "area": s["neighbourhood"],
                            "bbl": s.get("bbl")}}
            for s in found]


def near_place(concept, lat, lon, radius=600, top=6):
    """Vacant storefronts within `radius` metres of a point, one per block, best lease score first; each with
    its distance to the point."""
    if concept not in engine.CONCEPTS:
        raise engine.LeaseError(f"concept must be one of: {', '.join(engine.CONCEPTS)}")
    city, scores, best = engine.city(), {}, {}
    for s in vacant():
        d = engine.metres(lat, lon, s["lat"], s["lon"])
        if d > radius:
            continue
        cell = engine.g6(s["lat"], s["lon"])
        if cell not in scores:
            scores[cell] = city.score(concept, s["lat"], s["lon"])["score"]
        s = {**s, "metres_to_place": round(d), "score": scores[cell]}
        if cell not in best or (s["last_use"] == "Food Services", -d) > (best[cell]["last_use"] == "Food Services", -best[cell]["metres_to_place"]):
            best[cell] = s
    found = sorted(best.values(), key=lambda s: -s["score"])[:top]
    return found, {"storefronts_within_radius": sum(1 for s in vacant() if engine.metres(lat, lon, s["lat"], s["lon"]) <= radius),
                   "blocks_within_radius": len(best)}
