"""Idea screen, Amendment 1's secondary analysis (PREREGISTRATION_13.md): for every idea, how much two unlike
restaurants on one block share (location effect), how much more two of the same category share (category effect,
reported only), and for place ideas how much of a top 10 lies within 1,500 m of the seed (nearby share).
Adds a "secondary" block to screen13_results.json.
python screen13b.py"""
import json
import random
from collections import Counter

import numpy as np

import engine
import qloo
import scene
import screen13 as s13

PLACE_IDEAS = {"1 partners": {"filter.exclude.tags": s13.RESTAURANT}, "2 scene": {"filter.tags": s13.RESTAURANT}}


def blocks():
    """Test 11 blocks as [(A1, A2, B)], each a dict with entity id and coordinates; and which hold signal throughout."""
    detail = json.load(open("test11_detail.json", encoding="utf-8"))
    common = Counter(tuple(sorted(s["scene"])) for b in detail for s in b["seeds"]).most_common(1)[0][0]
    city, out, flat = engine.city(), [], []
    for b in detail:
        three = []
        for s in b["seeds"]:
            r = next(r for r in city.by_cell[b["cell"]] if r["dba"] == s["city"])
            hit = scene.resolve_at(r["dba"].title(), r["lat"], r["lon"])
            three.append({"id": hit["entity_id"], "name": hit["name"], "lat": r["lat"], "lon": r["lon"],
                          "signal": tuple(sorted(s["scene"])) != common} if hit else None)
        flat += [x for x in three if x and x["signal"]]
        if all(x and x["signal"] for x in three):
            out.append(three)
    return out, flat


def nearby(idea, seeds):
    shares = []
    for s in seeds:
        rows = s13.insights("urn:entity:place", s["id"], **s13.NYC, **PLACE_IDEAS[idea])
        rows = [x for x in rows if x.get("entity_id") != s["id"] and (idea != "1 partners" or not s13.t9.food(x))
                and (x.get("location") or {}).get("lat") is not None][:s13.TOP]
        if rows:
            shares.append(np.mean([engine.metres(s["lat"], s["lon"], float(x["location"]["lat"]), float(x["location"]["lon"])) <= 1500
                                   for x in rows]))
    return round(float(np.mean(shares)), 3), len(shares)


def main():
    res = json.load(open("screen13_results.json"))
    full, flat = blocks()
    by_name = sorted({(x["name"], x["id"]): x for x in flat}.items())
    random.Random(13).shuffle(by_name)
    seeds = [v for _, v in by_name[:s13.SEEDS]]  # the screen's 30 seeds, with their coordinates
    print(len(full), "blocks with signal for all three;", len(seeds), "seeds", flush=True)
    out = {"blocks": len(full)}
    for idea, fn in s13.IDEAS.items():
        tops = [[fn(x["id"]) for x in three] for three in full]
        diff = np.array([(s13.jac(t[0], t[2]) + s13.jac(t[1], t[2])) / 2 for t in tops])
        same = np.array([s13.jac(t[0], t[1]) for t in tops])
        rng = np.random.default_rng(0)
        d = same - diff
        boots = [float(np.mean(rng.choice(d, len(d)))) for _ in range(2000)]
        loc = float(diff.mean()) - res["ideas"][idea]["specificity"]
        r = {"same_block_unlike_overlap": round(float(diff.mean()), 3), "location_effect": round(loc, 3),
             "category_effect": {"mean": round(float(d.mean()), 3), "ci95": [round(float(v), 3) for v in np.percentile(boots, [2.5, 97.5])]}}
        if idea in PLACE_IDEAS:
            r["nearby_share"], r["nearby_seeds"] = nearby(idea, seeds)
        r["mostly_location"] = r["location_effect"] > 0.3 or r.get("nearby_share", 0) > 0.5
        out[idea] = r
        print(idea, json.dumps(r), flush=True)
    res["secondary"] = out
    json.dump(res, open("screen13_results.json", "w"), indent=1)
    print("quota:", qloo.QUOTA["remaining"])


if __name__ == "__main__":
    main()
