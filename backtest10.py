"""Test 10 as registered in PREREGISTRATION_10.md: is Qloo's same-cuisine list around a storefront complete
(coverage against city inspection records) and current (existence in city records)?
Aggregates go to backtest10_results.json; per-place detail to test10_detail.json (not committed: Qloo names).
python backtest10.py"""
import json
import random
import re

import numpy as np

import engine
import positioning
import qloo

NEAR, WIDE, PAIR = 1500, 1800, 200
DROP = {"restaurant", "cafe", "kitchen", "bar", "grill", "cuisine", "house", "shop", "food", "foods"}


def words(name):
    return [w for w in positioning._norm(name).split() if w not in DROP]


def same_name(a, b):
    wa, wb = words(a), words(b)
    if not wa or not wb:
        return False
    short, long_ = sorted((wa, wb), key=len)
    if long_[:len(short)] == short:  # equal, or one name's words open the other
        return True
    sa, sb = set(wa), set(wb)
    return len(sa & sb) / len(sa | sb) >= 0.5


def qloo_list(c):
    point = f"POINT({c['lon']:.4f} {c['lat']:.4f})"
    out, seen = [], set()
    for page in range(1, 5):
        rows = qloo.results(qloo.get("/v2/insights", **{
            "filter.type": "urn:entity:place", "filter.tags": f"urn:tag:genre:place:restaurant:{c['slug']}",
            "filter.location": point, "filter.location.radius": WIDE, "take": 50, "page": page}), "entities")
        for x in rows:
            loc = x.get("location") or {}
            if x["entity_id"] in seen or x.get("properties", {}).get("is_closed") or loc.get("lat") is None:
                continue
            seen.add(x["entity_id"])
            out.append({"name": x["name"], "lat": float(loc["lat"]), "lon": float(loc["lon"]),
                        "metres": engine.metres(c["lat"], c["lon"], float(loc["lat"]), float(loc["lon"]))})
        if len(rows) < 50:
            break
    return [x for x in out if x["metres"] <= WIDE]


def city_list(c, category=None):
    out = []
    for r in engine.city().rest:
        if category and r["cuisine"] != category:
            continue
        d = engine.metres(c["lat"], c["lon"], r["lat"], r["lon"])
        if d <= WIDE:
            out.append({"name": r["dba"], "lat": r["lat"], "lon": r["lon"], "metres": d, "cuisine": r["cuisine"]})
    return out


def match(left, right):
    """Indices of `left` matched one-to-one to `right`: nearest name-matching pair first."""
    pairs = sorted((engine.metres(a["lat"], a["lon"], b["lat"], b["lon"]), i, j)
                   for i, a in enumerate(left) for j, b in enumerate(right)
                   if abs(a["lat"] - b["lat"]) < 0.003 and same_name(a["name"], b["name"]))
    done_l, done_r = set(), set()
    for d, i, j in pairs:
        if d <= PAIR and i not in done_l and j not in done_r:
            done_l.add(i); done_r.add(j)
    return done_l


def pooled(rows, num, den):
    rng = np.random.default_rng(0)
    n = len(rows)
    boots = []
    for _ in range(2000):
        pick = [rows[i] for i in rng.integers(0, n, n)]
        d = sum(r[den] for r in pick)
        boots.append(sum(r[num] for r in pick) / d if d else np.nan)
    d = sum(r[den] for r in rows)
    return {"share": round(sum(r[num] for r in rows) / d, 3) if d else None, "matched": sum(r[num] for r in rows), "of": d,
            "ci95": [round(float(v), 3) for v in np.nanpercentile(boots, [2.5, 97.5])]}


def search_has(r):
    """One /search by name near a city record: does Qloo hold the place at all (any tag)?"""
    d = qloo.get("/search", query=r["name"].title(), types="urn:entity:place", take=5,
                 **{"filter.location": f"{r['lat']:.5f},{r['lon']:.5f}", "filter.radius": 1})
    for h in d.get("results") or []:
        loc = h.get("location") or {}
        if loc.get("lat") is not None and same_name(h.get("name", ""), r["name"]) and \
                engine.metres(r["lat"], r["lon"], float(loc["lat"]), float(loc["lon"])) <= PAIR:
            return True
    return False


def main():
    cases = json.load(open("test8_cases.json"))
    rows, detail = [], {"unmatched_city": [], "unmatched_qloo": []}
    for c in cases:
        cat = engine.CONCEPTS[c["concept"]][0]
        q, city_cat, city_all = qloo_list(c), city_list(c, cat), city_list(c)
        cc = [x for x in city_cat if x["metres"] <= NEAR]
        qq = [x for x in q if x["metres"] <= NEAR]
        cov, exi = match(cc, q), match(qq, city_all)
        rows.append({"id": c["id"], "concept": c["concept"], "borough": c["address"].rsplit(", ", 1)[-1],
                     "city": len(cc), "city_matched": len(cov), "qloo": len(qq), "qloo_matched": len(exi)})
        detail["unmatched_city"] += [{"case": c["id"], **x} for i, x in enumerate(cc) if i not in cov]
        detail["unmatched_qloo"] += [{"case": c["id"], **x} for i, x in enumerate(qq) if i not in exi]
        print(rows[-1], flush=True)

    def by(key):
        return {k: {"coverage": pooled([r for r in rows if r[key] == k], "city_matched", "city")["share"],
                    "existence": pooled([r for r in rows if r[key] == k], "qloo_matched", "qloo")["share"],
                    "city": sum(r["city"] for r in rows if r[key] == k), "qloo": sum(r["qloo"] for r in rows if r[key] == k)}
                for k in sorted({r[key] for r in rows})}
    cov, exi = pooled(rows, "city_matched", "city"), pooled(rows, "qloo_matched", "qloo")
    rng = random.Random(10)
    sample = rng.sample(detail["unmatched_city"], min(40, len(detail["unmatched_city"])))
    for r in sample:
        r["qloo_has_it"] = search_has(r)
    detail["search_sample"] = sample
    detail["hand_check"] = random.Random(10).sample(detail["unmatched_qloo"], min(40, len(detail["unmatched_qloo"])))
    out = {"cases": len(rows), "coverage": cov, "existence": exi,
           "coverage_band": "80% or more" if cov["share"] >= 0.8 else "50% to under 80%" if cov["share"] >= 0.5 else "under 50%",
           "existence_band": "90% or more" if exi["share"] >= 0.9 else "under 90%",
           "search_sample": {"unmatched_city_sampled": len(sample), "qloo_has_it_under_another_tag": sum(r["qloo_has_it"] for r in sample)},
           "by_cuisine": by("concept"), "by_borough": by("borough"), "per_case": rows}
    json.dump(out, open("backtest10_results.json", "w"), indent=1)
    json.dump(detail, open("test10_detail.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print(json.dumps({k: v for k, v in out.items() if k != "per_case"}, indent=1))
    print("qloo quota:", qloo.QUOTA["remaining"])


if __name__ == "__main__":
    main()
