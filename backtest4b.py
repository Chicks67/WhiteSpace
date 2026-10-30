"""Test 4b as registered in PREREGISTRATION_6.md: the city-records lease score (DS) on untested cuisine
categories, on all background blocks (no Qloo feature). Writes backtest4b_results.json."""
import json
import math

import numpy as np
from sklearn.metrics import roc_auc_score

import backtest as bt
import backtest4 as b4

CANDIDATES = ["American", "Chicken", "Juice, Smoothies, Fruit Salads", "Donuts", "Hamburgers", "Asian/Asian Fusion",
              "Spanish", "Sandwiches", "Frozen Desserts", "Jewish/Kosher", "Tex-Mex", "French", "Seafood",
              "Bagels/Pretzels", "New American", "Irish", "Sandwiches/Salads/Mixed Buffet", "Greek",
              "Eastern European", "Salads", "Southeast Asian", "Fusion", "Steakhouse", "Peruvian"]
RULE = {"min_positives": 50, "min_auc": 0.75, "min_lower": 0.70}


def rows_all(c, rest, pre, is_new, density, background):
    pre_c = {}
    for r in pre:
        if r["cuisine"] == c:
            k = bt.g6(r["lat"], r["lon"])
            pre_c[k] = pre_c.get(k, 0) + 1
    opened = {bt.g6(r["lat"], r["lon"]) for r in rest if r["cuisine"] == c and is_new(r)}
    return [{"block": cell[:5], "y": int(cell in opened), "D": math.log1p(density[cell]),
             "S": math.log1p(pre_c.get(cell, 0) + sum(pre_c.get(n, 0) for n in bt.neighbours(cell)))}
            for cell in background]


def score(rows, resamples=2000):
    y = np.array([r["y"] for r in rows]); g = np.array([r["block"] for r in rows])
    D, S = np.array([r["D"] for r in rows]), np.array([r["S"] for r in rows])
    DS = b4.oof(np.c_[D, S], y, g)
    rng = np.random.default_rng(0)
    blocks = np.unique(g); idx = {b: np.where(g == b)[0] for b in blocks}
    boots = []
    for _ in range(resamples):
        take = np.concatenate([idx[b] for b in rng.choice(blocks, len(blocks))])
        if 0 < y[take].sum() < len(take):
            boots.append(roc_auc_score(y[take], DS[take]))
    lo, hi = np.percentile(boots, [2.5, 97.5])
    return {"blocks": len(rows), "positives": int(y.sum()), "auc_DS": round(roc_auc_score(y, DS), 3),
            "ci95": [round(float(lo), 3), round(float(hi), 3)], "auc_D": round(roc_auc_score(y, D), 3)}


def main():
    rest, pre, is_new, density, background, heat, mean_aff = bt.build()
    out = {"rule": RULE, "candidates": {}, "tested_14_on_all_blocks": {}}
    for c in CANDIDATES:
        r = score(rows_all(c, rest, pre, is_new, density, background))
        r["passes"] = bool(r["positives"] >= RULE["min_positives"] and r["auc_DS"] >= RULE["min_auc"]
                       and r["ci95"][0] >= RULE["min_lower"])
        out["candidates"][c] = r
        print(f"{c:32} {r}", flush=True)
    for c in bt.CUISINES:
        out["tested_14_on_all_blocks"][c] = score(rows_all(c, rest, pre, is_new, density, background), 500)
        print(f"  tested {c:24} {out['tested_14_on_all_blocks'][c]}", flush=True)
    json.dump(out, open("backtest4b_results.json", "w"), indent=1)


if __name__ == "__main__":
    main()
