"""Build qloo_warm/: the Qloo responses every fresh server needs, copied from the local cache.

A new server instance (Vercel starts several) would otherwise spend Qloo quota on the same calls before its first
answer: the 10 reference areas the brief's distinctiveness filter compares against, the cuisine heatmaps behind
the "Qloo taste" toggle, the "what is around" lookups for each saved run's top pick, and the scene explorer's
example. qloo_warm/ is git-ignored (Qloo data never goes in the public repo) and ships only inside the private
server deployment. Run before deploying: python warm_cache.py
"""
import json
import os
import shutil

import around
import backtest
import engine
import positioning
import qloo
import scene

ROOT = os.path.dirname(__file__)
GOLDEN = os.environ.get("GOLDEN_DIR") or os.path.join(ROOT, "golden")


def top_picks():
    """(cuisine, lat, lon) of each saved run's top pick, rounded as /api/around rounds them."""
    out = set()
    for name in sorted(os.listdir(GOLDEN)) if os.path.isdir(GOLDEN) else []:
        if not name.endswith(".json"):
            continue
        with open(os.path.join(GOLDEN, name)) as f:
            events = [e for _, e in json.load(f)["events"]]
        cuisine = next((e["data"]["cuisine"] for e in events if e["type"] == "concept"), None)
        leases = next((e["data"] for e in events if e["type"] == "leases"), [])
        top = next((l for l in leases if l.get("rank") == 1), leases[0] if leases else None)
        if cuisine and top:
            out.add((cuisine, round(top["lat"], 3), round(top["lon"], 3)))
    return sorted(out)


def test20_answers():
    """Test 20's recorded answers for its 30 decision places, scored by the test's own rule (within 30 minutes of
    Google Maps), for the page's "see every answer" table. Recorded answers only: no new model call."""
    import test12 as t12
    import test20 as t20
    rows = []
    for p in [p for p in t20.places() if not p["shown"]]:
        r = {"name": p["name"], "address": p["address"], "google": f"{p['google'] // 60 % 24:02d}:{p['google'] % 60:02d}",
             "qloo": p["qloo"]}
        for arm, small, with_qloo in t20.ARMS:
            a = t20.answer(p, arm, small, with_qloo)["closes"]
            m = None if a is None else t12.minutes(str(a))
            d = None if m is None else min(abs(m - p["google"]), 1440 - abs(m - p["google"]))
            r[arm] = {"said": a, "right": d is not None and d <= 30}
        rows.append(r)
    out = {"rows": rows, "rule": "right means within 30 minutes of Google Maps' Friday closing time",
           "totals": {arm: sum(r[arm]["right"] for r in rows) for arm, *_ in t20.ARMS}}
    with open(os.path.join(qloo.WARM, "test20_answers.json"), "w") as f:
        json.dump(out, f)
    return out


def main():
    print("reference areas", len(positioning.reference()))
    for concept, (_, slug) in engine.CONCEPTS.items():
        backtest.heatmap(f"urn:tag:genre:place:restaurant:{slug}")
    print("heatmaps", len(engine.CONCEPTS))
    for cuisine, lat, lon in top_picks():
        around.for_point(cuisine, lat, lon)
        print("around", cuisine, lat, lon)
    scene.for_anchors(["Thai Diner"])
    print("scene example")
    os.makedirs(qloo.WARM, exist_ok=True)
    for base in sorted(qloo.USED):
        src = os.path.join(qloo.CACHE, base)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(qloo.WARM, base))
    print("test20 answers", test20_answers()["totals"])
    size = sum(os.path.getsize(os.path.join(qloo.WARM, n)) for n in os.listdir(qloo.WARM))
    print(f"{len(os.listdir(qloo.WARM))} responses in qloo_warm/, {size / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
