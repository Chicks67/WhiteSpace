"""Test 6 as registered in PREREGISTRATION_4.md: do Qloo's audience tags describe who is in an area?"""
import csv
import gzip
import io
import json
import math
import os
import urllib.parse
import urllib.request

import numpy as np
from scipy.stats import spearmanr
from shapely.geometry import Point, shape

import llm
import nyc
import qloo

DATA = os.path.join(os.path.dirname(__file__), "data")
BOROS = {"Brooklyn": "047", "Queens": "081", "Manhattan": "061", "Bronx": "005"}
TAGS = {
    "affluent": "urn:tag:customer_identity:qloo:affluent_diners",
    "young_adults": "urn:tag:customer_identity:qloo:young_adults",
    "college": "urn:tag:customer_identity:qloo:college_students",
    "families": "urn:tag:customer_identity:qloo:families",
    "seniors": "urn:tag:customer_identity:qloo:seniors",
    "business": "urn:tag:customer_identity:qloo:business_professionals",
    "tourists": "urn:tag:customer_identity:qloo:tourists",
}
BOOT, rng = 2000, np.random.default_rng(0)
SQFT_TO_KM2 = 0.09290304 / 1e6


def _get(url):
    return urllib.request.urlopen(url, timeout=300).read()


def _cached(name, fetch):
    path = os.path.join(DATA, name)
    if not os.path.exists(path):
        os.makedirs(DATA, exist_ok=True)
        open(path, "wb").write(fetch())
    return open(path, "rb").read()


# ---------- units ----------
def ntas():
    feats = json.load(open(os.path.join(DATA, "nta2020.geojson")))["features"]
    out = {}
    for f in feats:
        p = f["properties"]
        if p["boroname"] in BOROS and p["ntatype"] == "0":
            poly = shape(f["geometry"])
            out[p["nta2020"]] = {"name": p["ntaname"], "boro": p["boroname"], "cdta": p["cdta2020"], "poly": poly,
                                 "point": poly.representative_point(), "km2": float(p["shape_area"]) * SQFT_TO_KM2}
    return out


def tract_to_nta():
    raw = _cached("tract_nta_2020.json", lambda: _get(
        "https://data.cityofnewyork.us/resource/hm78-6dwm.json?$limit=5000"))
    rows = json.loads(raw)
    out = {}
    for r in rows:
        geoid = r.get("geoid") or r.get("geoid20") or r.get("ct2020_geoid")
        nta = r.get("nta2020") or r.get("ntacode")
        if geoid and nta:
            out[geoid[-11:]] = nta
    return out, sorted(rows[0].keys()) if rows else []


# ---------- independent measures ----------
ACS_VARS = (["B19013_001E", "B11001_001E", "B14001_001E", "B14001_008E", "B14001_009E", "B11005_001E", "B11005_002E",
             "B01001_001E"] + [f"B01001_{i:03d}E" for i in list(range(8, 13)) + list(range(32, 37))]
            + [f"B01001_{i:03d}E" for i in list(range(20, 26)) + list(range(44, 50))])


def acs():
    key = llm.ENV["CENSUS_API_KEY"]
    rows = []
    for county in BOROS.values():
        url = ("https://api.census.gov/data/2023/acs/acs5?" + urllib.parse.urlencode(
            {"get": ",".join(ACS_VARS), "for": "tract:*", "in": f"state:36 county:{county}", "key": key}))
        data = json.loads(_cached(f"acs2023_{county}.json", lambda u=url: _get(u)))
        head = data[0]
        rows += [dict(zip(head, r)) for r in data[1:]]
    return rows


def lodes_jobs_by_tract():
    raw = _cached("ny_wac_S000_JT00_2023.csv.gz", lambda: _get(
        "https://lehd.ces.census.gov/data/lodes/LODES8/ny/wac/ny_wac_S000_JT00_2023.csv.gz"))
    jobs = {}
    for r in csv.DictReader(io.StringIO(gzip.decompress(raw).decode())):
        tract = r["w_geocode"][:11]
        jobs[tract] = jobs.get(tract, 0) + int(r["C000"])
    return jobs


def hotels():
    raw = _cached("hotels_tjus-cn27.json", lambda: _get(
        "https://data.cityofnewyork.us/resource/tjus-cn27.json?$limit=50000"))
    latest = {}  # one point per hotel parcel (the dataset repeats parcels across tax years)
    for r in json.loads(raw):
        k = r.get("bbl") or r.get("parid")
        if k and (k not in latest or (r.get("taxyear") or "") > (latest[k].get("taxyear") or "")):
            latest[k] = r
    pts = []
    for r in latest.values():
        try:
            pts.append(Point(float(r["longitude"]), float(r["latitude"])))
        except (KeyError, TypeError, ValueError):
            continue
    return pts


def measures(units):
    t2n, cols = tract_to_nta()
    agg = {k: {"pop": 0, "hh": 0, "inc_w": 0.0, "inc_hh": 0, "enr_base": 0, "college": 0, "hh5": 0, "kids": 0,
               "young": 0, "old": 0, "jobs": 0} for k in units}
    num = lambda r, v: max(float(r.get(v) or 0), 0)
    for r in acs():
        nta = t2n.get(r["state"] + r["county"] + r["tract"])
        if nta not in agg:
            continue
        a = agg[nta]
        a["pop"] += num(r, "B01001_001E")
        if float(r["B19013_001E"] or -1) > 0:
            a["inc_w"] += float(r["B19013_001E"]) * num(r, "B11001_001E")
            a["inc_hh"] += num(r, "B11001_001E")
        a["enr_base"] += num(r, "B14001_001E")
        a["college"] += num(r, "B14001_008E") + num(r, "B14001_009E")
        a["hh5"] += num(r, "B11005_001E")
        a["kids"] += num(r, "B11005_002E")
        a["young"] += sum(num(r, f"B01001_{i:03d}E") for i in list(range(8, 13)) + list(range(32, 37)))
        a["old"] += sum(num(r, f"B01001_{i:03d}E") for i in list(range(20, 26)) + list(range(44, 50)))
    for tract, j in lodes_jobs_by_tract().items():
        nta = t2n.get(tract)
        if nta in agg:
            agg[nta]["jobs"] += j
    hp = hotels()
    out = {}
    for k, u in units.items():
        a = agg[k]
        if a["pop"] < 1000:
            continue
        n_hotels = sum(1 for p in hp if u["poly"].contains(p))
        out[k] = {
            "affluent": a["inc_w"] / a["inc_hh"] if a["inc_hh"] else None,
            "young_adults": a["young"] / a["pop"],
            "college": a["college"] / a["enr_base"] if a["enr_base"] else None,
            "families": a["kids"] / a["hh5"] if a["hh5"] else None,
            "seniors": a["old"] / a["pop"],
            "business": math.log(max(a["jobs"], 1) / u["km2"]),
            "tourists": math.log1p(n_hotels / u["km2"]),
            "pop": a["pop"],
        }
    return out, cols


# ---------- Qloo ----------
def qloo_affinity(units):
    ids = ",".join(TAGS.values())
    out = {}
    for k, u in units.items():
        p = u["point"]
        d = qloo.get("/v2/insights", **{"filter.type": "urn:tag", "take": 20, "filter.results.tags": ids,
                                        "signal.location": f"POINT({p.x:.5f} {p.y:.5f})"})
        got = {x.get("tag_id"): x.get("query", {}).get("affinity") for x in qloo.results(d, "tags")}
        out[k] = {name: got.get(tid) for name, tid in TAGS.items()}
    return out


# ---------- statistics ----------
def boot_ci(x, y, clusters):
    ids = {}
    for i, c in enumerate(clusters):
        ids.setdefault(c, []).append(i)
    groups = list(ids.values())
    vals = []
    for _ in range(BOOT):
        idx = np.concatenate([groups[g] for g in rng.integers(0, len(groups), len(groups))])
        if len(set(x[idx])) > 1 and len(set(y[idx])) > 1:
            vals.append(spearmanr(x[idx], y[idx]).statistic)
    return [round(float(v), 3) for v in np.percentile(vals, [2.5, 97.5])]


def main():
    units = ntas()
    meas, cols = measures(units)
    aff = qloo_affinity({k: units[k] for k in meas})
    res, matrix = {}, {}
    for tag in TAGS:
        keep = [k for k in meas if aff[k][tag] is not None and meas[k][tag] is not None]
        x = np.array([aff[k][tag] for k in keep]); y = np.array([meas[k][tag] for k in keep])
        rho = spearmanr(x, y).statistic
        ci = boot_ci(x, y, [units[k]["cdta"] for k in keep])
        res[tag] = {"n": len(keep), "rho": round(float(rho), 3), "ci95": ci,
                    "validated": bool(rho >= 0.30 and ci[0] > 0)}
        matrix[tag] = {}
        for m in TAGS:
            kk = [k for k in meas if aff[k][tag] is not None and meas[k][m] is not None]
            matrix[tag][m] = round(float(spearmanr([aff[k][tag] for k in kk], [meas[k][m] for k in kk]).statistic), 3)
    for m in TAGS:  # discriminant: rank of the matched tag among all tags for this measure
        order = sorted(TAGS, key=lambda t: -matrix[t][m])
        res[m]["own_tag_rank"] = order.index(m) + 1
    n_valid = sum(r["validated"] for r in res.values())
    out = {"units": len(meas), "pairs": res, "rho_matrix_tag_by_measure": matrix, "validated": n_valid,
           "band": "5+ validated" if n_valid >= 5 else "2 to 4 validated" if n_valid >= 2 else "1 or none",
           "tract_equivalency_columns": cols}
    json.dump(out, open("backtest6_results.json", "w"), indent=1)
    print(json.dumps({k: v for k, v in out.items() if k != "rho_matrix_tag_by_measure"}, indent=1))


if __name__ == "__main__":
    main()
