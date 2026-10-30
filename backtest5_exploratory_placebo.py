"""Exploratory, not pre-registered: is Qloo's survival gain a proxy for today's supply?
Placebo feature T = log(1 + same-cuisine restaurants in the block and 8 neighbours TODAY, excluding the
restaurant itself). If adding T gains as much as adding Qloo, Qloo's gain likely reflects today's map
counting survivors (leakage), not foresight."""
import sys, math, json
sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.abspath(__file__)))
import numpy as np
from sklearn.metrics import roc_auc_score
import backtest5 as b5, engine
rows, _ = b5.build()
city = engine.city()
cnt = {}
for r in city.rest:
    k = (engine.g6(r["lat"], r["lon"]), r["cuisine"]); cnt[k] = cnt.get(k, 0) + 1
conc2dohmh = {k: v[0] for k, v in engine.CONCEPTS.items()}
gq, gt = [], []
for concept in engine.CONCEPTS:
    rs = [r for r in rows if r["concept"] == concept and r["qloo"] is not None]
    y = np.array([r["y"] for r in rs])
    if y.sum() < 15 or len(y) - y.sum() < 15:
        continue
    cell = lambda r: r["camis"]
    T = []
    for r in rs:
        c6 = r["block"]  # geohash-5 here; need geohash-6
    # rebuild geohash-6 cells from the snapshot rows
    snap = {r["camis"]: r for r in rows}
    T = np.array([math.log1p(max(sum(cnt.get((n, conc2dohmh[concept]), 0) for n in engine.neighbours(r["cell6"]) | {r["cell6"]}) - r["y"], 0)) for r in rs]) if rs and "cell6" in rs[0] else None
    if T is None:
        break
    g = [r["block"] for r in rs]
    Xb = np.array([[r["D"], r["S"]] for r in rs])
    base = b5.oof(Xb, y, g)
    q = b5.oof(np.c_[Xb, [r["qloo"] for r in rs]], y, g)
    t = b5.oof(np.c_[Xb, T], y, g)
    gq.append(roc_auc_score(y, q) - roc_auc_score(y, base)); gt.append(roc_auc_score(y, t) - roc_auc_score(y, base))
    print(f"{concept:15s} qloo gain {gq[-1]:+.3f}  today-supply gain {gt[-1]:+.3f}  today-supply alone {roc_auc_score(y, T):.3f}")
print("mean gain: qloo", round(float(np.mean(gq)), 4), "today's supply", round(float(np.mean(gt)), 4))
