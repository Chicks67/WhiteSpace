"""Business Improvement Districts: which BID a storefront sits in, with the BID's public contact details.

A BID is the local merchants' organisation, a natural first call for a founder (vacancies, foot traffic
counts, events). Boundaries: NYC Open Data 7jdm-inj8; directory: qpm9-j523.
"""
import json
import os
import re
import urllib.request
from functools import lru_cache

from shapely.geometry import Point, shape
from shapely.strtree import STRtree

DATA = os.path.join(os.path.dirname(__file__), "data")


def _get(name, url):
    path = os.path.join(DATA, name)
    if not os.path.exists(path):
        os.makedirs(DATA, exist_ok=True)
        open(path, "wb").write(urllib.request.urlopen(url, timeout=120).read())
    return json.load(open(path))


def _norm(s):
    s = re.sub(r"[^a-z0-9 ]", " ", (s or "").lower())
    s = re.sub(r"\b(bid|business improvement district|partnership|district|management|association|alliance|inc)\b", " ", s)
    return " ".join(s.split())


@lru_cache(maxsize=1)
def _index():
    bounds = _get("bids.json", "https://data.cityofnewyork.us/resource/7jdm-inj8.json?$limit=500")
    directory = _get("bid_directory.json", "https://data.cityofnewyork.us/resource/qpm9-j523.json?$limit=500")
    by_name = {_norm(d.get("org_name")): d for d in directory}
    polys, info = [], []
    for b in bounds:
        if not b.get("the_geom"):
            continue
        name = b.get("f_all_bi_2")
        d = by_name.get(_norm(name)) or next((v for k, v in by_name.items() if k and (k in _norm(name) or _norm(name) in k)), {})
        polys.append(shape(b["the_geom"]))
        phone = d.get("org_phone") or ""
        info.append({"bid": name, "website": b.get("f_all_bi_4") or d.get("org_website"),
                     "phone": f"({phone[:3]}) {phone[3:6]}-{phone[6:]}" if len(phone) == 10 else phone or None,
                     "email": d.get("org_email"), "boundary": d.get("org_boundary")})
    return STRtree(polys), polys, info


def bid_for(lat, lon):
    tree, polys, info = _index()
    p = Point(lon, lat)
    for i in tree.query(p):
        if polys[i].contains(p):
            return info[i]
    return None


if __name__ == "__main__":
    for lat, lon in [(40.7590, -73.8303), (40.7556, -73.9231), (40.8065, -73.9655), (40.7477, -73.8856)]:
        print(lat, lon, bid_for(lat, lon))
