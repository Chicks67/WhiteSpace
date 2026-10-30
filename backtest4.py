"""Test 4 as registered in PREREGISTRATION_3.md: lease ranking on all blocks, and whether Qloo taste adds to it."""
import json
import math
import statistics

import numpy as np
from scipy.stats import binomtest
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupKFold

import backtest as bt

rng = np.random.default_rng(0)


def rows_for(c, rest, pre, is_new, density, background, mean_aff, exclude_replacements=False):
    pre_c = {}
    for r in pre:
        if r["cuisine"] == c:
            k = bt.g6(r["lat"], r["lon"])
            pre_c[k] = pre_c.get(k, 0) + 1
    new_c = [r for r in rest if r["cuisine"] == c and is_new(r)]
    if exclude_replacements:
        old = {}
        for r in pre:
            old.setdefault(bt.g6(r["lat"], r["lon"]), []).append(r)
        new_c = [r for r in new_c if not any(bt.metres(r["lat"], r["lon"], o["lat"], o["lon"]) <= 5
                                             for o in old.get(bt.g6(r["lat"], r["lon"]), []))]
    opened = {bt.g6(r["lat"], r["lon"]) for r in new_c}
    rows = []
    for cell in background:
        if cell not in mean_aff[c]:
            continue
        s = pre_c.get(cell, 0) + sum(pre_c.get(n, 0) for n in bt.neighbours(cell))
        rows.append({"cell": cell, "block": cell[:5], "y": int(cell in opened),
                     "D": math.log1p(density[cell]), "S": math.log1p(s), "M1": mean_aff[c][cell]})
    return rows


def oof(X, y, groups):
    out = np.zeros(len(y))
    for tr, te in GroupKFold(5).split(X, y, groups):
        out[te] = LogisticRegression().fit(X[tr], y[tr]).predict_proba(X[te])[:, 1]
    return out


def analyse(per_rows):
    res, data = {}, {}
    for c, rows in per_rows.items():
        y = np.array([r["y"] for r in rows])
        g = [r["block"] for r in rows]
        D, S, M1 = (np.array([r[k] for r in rows]) for k in ("D", "S", "M1"))
        DS = oof(np.c_[D, S], y, g)
        DSQ = oof(np.c_[D, S, M1], y, g)
        sc = {"D": D, "S": S, "DS": DS, "DSQ": DSQ, "M1": M1}
        res[c] = {"blocks": len(rows), "positives": int(y.sum()),
                  "auc": {k: round(roc_auc_score(y, v), 3) for k, v in sc.items()},
                  "delong_DSQ_vs_DS": dict(zip(("diff", "se", "p"), (round(x, 4) for x in bt.delong(y, DSQ, DS))))}
        data[c] = (y, sc, np.array(g))
    cuisines = list(res)
    med = {k: round(statistics.median(res[c]["auc"][k] for c in cuisines), 3) for k in ("D", "S", "DS", "DSQ", "M1")}
    winner = max(("D", "S", "DS"), key=lambda k: med[k])
    signs = {}
    for other in ("D", "S", "DS"):
        if other == winner:
            continue
        wins = sum(res[c]["auc"][winner] > res[c]["auc"][other] for c in cuisines)
        losses = sum(res[c]["auc"][winner] < res[c]["auc"][other] for c in cuisines)
        signs[other] = {"wins": wins, "losses": losses,
                        "p_two_sided": round(binomtest(wins, wins + losses).pvalue, 4) if wins + losses else None}
    point = float(np.mean([res[c]["auc"]["DSQ"] - res[c]["auc"]["DS"] for c in cuisines]))
    # block bootstrap: resample geohash-5 blocks, shared across cuisines
    blocks = sorted({b for c in cuisines for b in data[c][2]})
    idx = {c: {} for c in cuisines}
    for c in cuisines:
        for i, b in enumerate(data[c][2]):
            idx[c].setdefault(b, []).append(i)
    diffs = []
    for _ in range(bt.BOOT):
        pick = rng.integers(0, len(blocks), len(blocks))
        chosen = [blocks[k] for k in pick]
        ds = []
        for c in cuisines:
            ii = np.concatenate([idx[c][b] for b in chosen if b in idx[c]] or [np.array([], int)]).astype(int)
            y, sc, _ = data[c]
            if len(ii) and 0 < y[ii].sum() < len(ii):
                ds.append(roc_auc_score(y[ii], sc["DSQ"][ii]) - roc_auc_score(y[ii], sc["DS"][ii]))
        if len(ds) == len(cuisines):
            diffs.append(np.mean(ds))
    ci = [round(float(x), 4) for x in np.percentile(diffs, [2.5, 97.5])]
    return {"per_cuisine": res, "median_auc": med, "q1_winner": winner, "q1_sign_tests": signs,
            "q2_mean_DSQ_minus_DS": round(point, 4), "q2_ci95": ci, "q2_resamples_used": len(diffs),
            "q2_supported": bool(ci[0] > 0)}


def main():
    rest, pre, is_new, density, background, heat, mean_aff = bt.build()
    out = {}
    for name, excl in (("primary", False), ("secondary_excluding_replacements", True)):
        per = {c: rows_for(c, rest, pre, is_new, density, background, mean_aff, excl) for c in bt.CUISINES}
        out[name] = analyse(per)
        print(name, out[name]["median_auc"], out[name]["q1_winner"], out[name]["q2_mean_DSQ_minus_DS"], out[name]["q2_ci95"], flush=True)
    json.dump(out, open("backtest4_results.json", "w"), indent=1)


if __name__ == "__main__":
    main()
