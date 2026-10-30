"""Idea screen as registered in PREREGISTRATION_13.md: seven uses of Qloo's entity graph, the same five checks
for each. Exploratory: a pass earns an idea its own registered test and nothing else.
Aggregates go to screen13_results.json; names to screen13_detail.json (not committed: Qloo names).
python screen13.py"""
import itertools
import json
import random
from collections import Counter

import numpy as np

import engine
import positioning
import qloo
import scene
import test9_dev as t9

TOP, SEEDS, PAIRS, MAX_SEARCHES = 10, 30, 15, 120
RESTAURANT = "urn:tag:genre:place:restaurant"
MARKS = {"coverage": 0.7, "generic": 0.2, "specificity": 0.15, "baseline": 0.3}


def insights(ft, seed=None, field="entities", **extra):
    """Top rows for one query. With no seed, the same query is made for the city as a whole (Qloo needs a signal)."""
    sig = {"signal.interests.entities": seed} if seed else {"signal.location.query": "New York City"}
    d = qloo.get("/v2/insights", **{"filter.type": ft, "take": 30, **sig, **extra})
    return qloo.results(d, field)


def ids(rows, seed=None, keep=lambda x: True):
    key = lambda x: x.get("entity_id") or x.get("tag_id")
    out = [(key(x), x.get("name")) for x in rows if key(x) and key(x) != seed and keep(x)]
    return list(dict.fromkeys(out))[:TOP]


NYC = {"filter.location.query": "New York City"}
IDEAS = {
    "1 partners": lambda s: ids(insights("urn:entity:place", s, **NYC, **{"filter.exclude.tags": RESTAURANT}), s, lambda x: not t9.food(x)),
    "2 scene": lambda s: ids(insights("urn:entity:place", s, **NYC, **{"filter.tags": RESTAURANT}), s),
    "3 sound": lambda s: ids(insights("urn:entity:artist", s), s),
    "4 brands": lambda s: ids(insights("urn:entity:brand", s), s),
    "5 screen taste": lambda s: (ids(insights("urn:entity:tv_show", s), s)[:5] + ids(insights("urn:entity:movie", s), s)[:5]),
    "6 words": lambda s: ids(insights("urn:tag", s, field="tags"), s),
    "7 twin city": lambda s: ids(insights("urn:entity:place", s, **{"filter.location.query": "Chicago"}), s),
}


def jac(a, b):
    a, b = {x[0] for x in a}, {x[0] for x in b}
    return len(a & b) / len(a | b) if a | b else 0.0


def restaurants():
    """Test 11's restaurants whose scene was not the generic landmark list, as (name, entity id)."""
    detail = json.load(open("test11_detail.json", encoding="utf-8"))
    common = Counter(tuple(sorted(s["scene"])) for b in detail for s in b["seeds"]).most_common(1)[0][0]
    city, rows = engine.city(), []
    for b in detail:
        for s in b["seeds"]:
            if tuple(sorted(s["scene"])) == common:
                continue
            r = next(r for r in city.by_cell[b["cell"]] if r["dba"] == s["city"])
            hit = scene.resolve_at(r["dba"].title(), r["lat"], r["lon"])
            if hit:
                rows.append((hit["name"], hit["entity_id"]))
    rows = sorted(set(rows))
    random.Random(13).shuffle(rows)
    return rows[:SEEDS]


def siblings():
    city = engine.city()
    by = {}
    for r in city.rest:
        by.setdefault(positioning._norm(r["dba"]), []).append(r)
    names = sorted(k for k, v in by.items() if 2 <= len(v) <= 4 and len(k) >= 4)
    random.Random(13).shuffle(names)
    pairs, used = [], 0
    for n in names:
        if len(pairs) == PAIRS or used >= MAX_SEARCHES:
            break
        hits = []
        for r in by[n][:2]:
            used += 1
            h = scene.resolve_at(r["dba"].title(), r["lat"], r["lon"])
            if not h:
                break
            hits.append(h)
        if len(hits) == 2 and hits[0]["entity_id"] != hits[1]["entity_id"]:
            pairs.append(((hits[0]["name"], hits[0]["entity_id"]), (hits[1]["name"], hits[1]["entity_id"])))
    return pairs, used


def main():
    seeds, (pairs, used) = restaurants(), siblings()
    print(f"{len(seeds)} seeds, {len(pairs)} sibling pairs ({used} searches)", flush=True)
    out, detail = {"seeds": len(seeds), "sibling_pairs": len(pairs), "pass_marks": MARKS, "ideas": {}}, {}
    for name, fn in IDEAS.items():
        tops = {sid: fn(sid) for _, sid in seeds}
        base = fn(None)
        lists = list(tops.values())
        common = Counter(tuple(x[0] for x in t) for t in lists if t).most_common(1)
        cross = [jac(a, b) for a, b in itertools.combinations(lists, 2)]
        sib = np.array([jac(fn(a[1]), fn(b[1])) for a, b in pairs])
        rng = np.random.default_rng(0)
        unrelated = float(np.mean(cross))
        boots = [float(np.mean(rng.choice(sib, len(sib)))) - unrelated for _ in range(2000)] if len(sib) else [0.0]
        r = {"coverage": round(float(np.mean([len(t) >= 5 for t in lists])), 3),
             "generic": round(sum(tuple(x[0] for x in t) == common[0][0] for t in lists) / len(lists), 3) if common and common[0][1] > 1 else 0.0,
             "specificity": round(unrelated, 3),
             "baseline": round(float(np.mean([jac(t, base) for t in lists])), 3), "baseline_items": len(base),
             "sibling_overlap": round(float(sib.mean()), 3) if len(sib) else None,
             "consistency": {"mean": round(float(sib.mean()) - unrelated, 3) if len(sib) else None,
                             "ci95": [round(float(v), 3) for v in np.percentile(boots, [2.5, 97.5])]}}
        r["checks"] = {"coverage": r["coverage"] >= MARKS["coverage"], "generic": r["generic"] <= MARKS["generic"],
                       "specificity": r["specificity"] <= MARKS["specificity"], "baseline": r["baseline"] <= MARKS["baseline"],
                       "consistency": r["consistency"]["ci95"][0] > 0}
        r["pass"] = all(r["checks"].values())
        out["ideas"][name] = r
        detail[name] = {"baseline": [x[1] for x in base], "examples": {n: [x[1] for x in tops[sid]] for n, sid in seeds[:6]}}
        print(name, json.dumps(r), flush=True)
    json.dump(out, open("screen13_results.json", "w"), indent=1)
    json.dump(detail, open("screen13_detail.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print("passed:", [k for k, v in out["ideas"].items() if v["pass"]], "| quota:", qloo.QUOTA["remaining"])


if __name__ == "__main__":
    main()
