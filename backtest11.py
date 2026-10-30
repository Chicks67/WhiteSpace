"""Test 11 as registered in PREREGISTRATION_11.md: do two restaurants on the same block get different Qloo
scenes, and do same-category pairs share more of their scene than different-category pairs?
Aggregates go to backtest11_results.json; names to test11_detail.json (not committed: Qloo names).
python backtest11.py"""
import json
import random
from collections import Counter

import numpy as np

import engine
import positioning
import scene

BLOCKS, MAX_TRIED, MAX_SEARCHES, MIN_RESTAURANTS, CHAIN = 40, 200, 10, 6, 5


def jaccard(a, b):
    a, b = {x["id"] for x in a}, {x["id"] for x in b}
    return len(a & b) / len(a | b) if a | b else 0.0


def seeds_for(rows, chains, rng):
    """(A1, A2, B, searches used) for one block, or None."""
    rows = [r for r in sorted(rows, key=lambda r: r["camis"]) if chains[positioning._norm(r["dba"])] < CHAIN]
    rng.shuffle(rows)
    if not rows:
        return None
    count = Counter(r["cuisine"] for r in rows)
    main = min(count, key=lambda k: (-count[k], k))
    a, b, used = [], None, 0
    for r in rows:
        want_a = r["cuisine"] == main and len(a) < 2 and positioning._norm(r["dba"]) not in {positioning._norm(x[0]["dba"]) for x in a}
        want_b = r["cuisine"] != main and b is None
        if not (want_a or want_b):
            continue
        if used == MAX_SEARCHES:
            return None
        used += 1
        hit = scene.resolve_at(r["dba"].title(), r["lat"], r["lon"])
        if hit and hit["entity_id"] not in {x[1]["entity_id"] for x in a + ([b] if b else [])}:
            if want_a:
                a.append((r, hit))
            else:
                b = (r, hit)
        if len(a) == 2 and b:
            return a[0], a[1], b, used
    return None


def main():
    city = engine.city()
    chains = Counter(positioning._norm(r["dba"]) for r in city.rest)
    cells = sorted(c for c, v in city.by_cell.items() if len(v) >= MIN_RESTAURANTS)
    random.Random(11).shuffle(cells)
    rows, detail, tried, searches = [], [], 0, 0
    for cell in cells:
        if len(rows) == BLOCKS or tried == MAX_TRIED:
            break
        tried += 1
        got = seeds_for(city.by_cell[cell], chains, random.Random(f"11-{cell}"))
        if not got:
            continue
        *three, used = got
        searches += used
        ids = [h["entity_id"] for _, h in three]
        sc = [scene.scene([i], 30, skip=ids) for i in ids]
        near = [float(np.mean([engine.metres(r["lat"], r["lon"], x["lat"], x["lon"]) <= 1500 for x in s])) if s else None
                for (r, _), s in zip(three, sc)]
        same, diff = jaccard(sc[0], sc[1]), (jaccard(sc[0], sc[2]) + jaccard(sc[1], sc[2])) / 2
        rows.append({"block": len(rows) + 1, "borough": three[0][0]["boro"], "same": round(same, 3), "different": round(diff, 3),
                     "sizes": [len(s) for s in sc], "within_1500m": [None if n is None else round(n, 3) for n in near]})
        detail.append({"block": len(rows), "cell": cell, "seeds": [{"city": r["dba"], "category": r["cuisine"], "qloo": h["name"],
                       "scene": [x["name"] for x in s]} for (r, h), s in zip(three, sc)]})
        print(rows[-1], flush=True)
    d = np.array([r["same"] - r["different"] for r in rows])
    rng = np.random.default_rng(0)
    boots = [float(np.mean(rng.choice(d, len(d)))) for _ in range(2000)]
    loc = float(np.mean([r["different"] for r in rows]))
    lo, hi = np.percentile(boots, [2.5, 97.5])
    near = [n for r in rows for n in r["within_1500m"] if n is not None]
    sizes = [n for r in rows for n in r["sizes"]]
    band = ("mostly location" if loc >= 0.5 else "specific and follows category" if lo > 0 else "specific, not validated")
    out = {"blocks": len(rows), "blocks_tried": tried, "searches_in_completed_blocks": searches,
           "location_share": round(loc, 3), "same_category_overlap": round(float(np.mean([r["same"] for r in rows])), 3),
           "category_effect": {"mean": round(float(d.mean()), 3), "ci95": [round(float(lo), 3), round(float(hi), 3)]},
           "band": band, "scene_within_1500m_of_seed": {"mean": round(float(np.mean(near)), 3), "median": round(float(np.median(near)), 3)},
           "empty_scenes": sum(n == 0 for n in sizes), "seeds": len(sizes),
           "by_borough": {b: {"blocks": sum(r["borough"] == b for r in rows),
                              "location_share": round(float(np.mean([r["different"] for r in rows if r["borough"] == b])), 3),
                              "same": round(float(np.mean([r["same"] for r in rows if r["borough"] == b])), 3)}
                          for b in sorted({r["borough"] for r in rows})},
           "per_block": rows}
    json.dump(out, open("backtest11_results.json", "w"), indent=1)
    json.dump(detail, open("test11_detail.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print(json.dumps({k: v for k, v in out.items() if k != "per_block"}, indent=1))


if __name__ == "__main__":
    main()
