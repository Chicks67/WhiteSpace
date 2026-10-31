"""NYC open data: restaurant inspections (ground-truth supply and opening dates) and NTA boundaries."""
import json
import os
import time
import urllib.parse
import urllib.request

from shapely.geometry import Point, shape
from shapely.strtree import STRtree

DATA = os.path.join(os.path.dirname(__file__), "data")


def _socrata(url, **params):
    full = url + "?" + urllib.parse.urlencode(params)
    for attempt in range(5):
        try:
            return json.load(urllib.request.urlopen(full, timeout=300))
        except Exception:
            if attempt == 4:
                raise
            time.sleep(5 * 2 ** attempt)


def restaurants():
    """One row per restaurant (CAMIS): name, borough, cuisine, coordinates, first inspection date."""
    path = os.path.join(DATA, "dohmh_restaurants.json")
    if not os.path.exists(path):
        os.makedirs(DATA, exist_ok=True)
        rows = _socrata(
            "https://data.cityofnewyork.us/resource/43nn-pn8j.json",
            **{"$select": "camis, dba, boro, cuisine_description, latitude, longitude, "
                          "min(inspection_date) as first_inspection",
               "$where": "inspection_date > '1901-01-01' AND latitude > 1",
               "$group": "camis, dba, boro, cuisine_description, latitude, longitude",
               "$limit": 100000})
        # A pre-permit operational inspection is the city's check on a new food permit:
        # the closest public proxy for an opening date.
        opened = _socrata(
            "https://data.cityofnewyork.us/resource/43nn-pn8j.json",
            **{"$select": "camis, min(inspection_date) as opened",
               "$where": "inspection_type like 'Pre-permit (Operational)%'",
               "$group": "camis", "$limit": 100000})
        opened = {o["camis"]: o["opened"][:10] for o in opened}
        for r in rows:
            r["opened"] = opened.get(r["camis"])
        with open(path, "w") as f:
            json.dump(rows, f)
    with open(path) as f:
        rows = json.load(f)
    for r in rows:
        r["lat"], r["lon"] = float(r.pop("latitude")), float(r.pop("longitude"))
        r["first_inspection"] = r["first_inspection"][:10]
        r["cuisine"] = r.pop("cuisine_description", None)
    return rows


def ntas():
    """2020 Neighborhood Tabulation Areas as (name, borough, polygon)."""
    path = os.path.join(DATA, "nta2020.geojson")
    if not os.path.exists(path):
        os.makedirs(DATA, exist_ok=True)
        urllib.request.urlretrieve(
            "https://data.cityofnewyork.us/resource/9nt8-h7nd.geojson?$limit=1000", path)
    with open(path) as f:
        feats = json.load(f)["features"]
    return [(x["properties"]["ntaname"], x["properties"]["boroname"], shape(x["geometry"])) for x in feats]


class NTALookup:
    def __init__(self):
        self.areas = ntas()
        self.tree = STRtree([a[2] for a in self.areas])

    def borough(self, lat, lon):
        p = Point(lon, lat)
        for i in self.tree.query(p):
            if self.areas[i][2].contains(p):
                return self.areas[i][1]
        return None

    def name(self, lat, lon):
        p = Point(lon, lat)
        for i in self.tree.query(p):
            if self.areas[i][2].contains(p):
                return self.areas[i][0]
        return None
