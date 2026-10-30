"""Test 7 as registered in PREREGISTRATION_7.md: given a block where a restaurant opened, does Qloo taste rank
the cuisine that opened above the others, beyond city records? Writes backtest7_results.json."""
import json
import math

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupKFold

import backtest as bt

CUISINES = list(bt.CUISINES)


def build():
    rest, pre, is_new, density, background, heat, mean_aff = bt.build()
    share = {c: sum(r["cuisine"] == c for r in pre) / len(pre) for c in CUISINES}
    pre_c = {c: {} for c in CUISINES}
    for r in pre:
        if r["cuisine"] in pre_c:
            k = bt.g6(r["lat"], r["lon"]); pre_c[r["cuisine"]][k] = pre_c[r["cuisine"]].get(k, 0) + 1
    opened = {}
    for r in rest:
        if is_new(r) and r["cuisine"] in pre_c:
            opened.setdefault(bt.g6(r["lat"], r["lon"]), set()).add(r["cuisine"])

    def ring(c, b):
        vals = [mean_aff[c][n] for n in bt.neighbours(b) if n in mean_aff[c]]
        return float(np.mean(vals)) if vals else None
    blocks = []
    for b in opened:
        if not all(b in mean_aff[c] for c in CUISINES):
            continue
        rq = {c: ring(c, b) for c in CUISINES}
        if any(v is None for v in rq.values()):
            continue
        blocks.append((b, rq))
    # z-score Q within cuisine across the sample's blocks
    def z(vals):
        a = np.array(vals); return (a - a.mean()) / (a.std() or 1)
    zr = {c: dict(zip([b for b, _ in blocks], z([rq[c] for _, rq in blocks]))) for c in CUISINES}
    zo = {c: dict(zip([b for b, _ in blocks], z([mean_aff[c][b] for b, _ in blocks]))) for c in CUISINES}
    rows = []
    for b, _ in blocks:
        for c in CUISINES:
            s = pre_c[c].get(b, 0) + sum(pre_c[c].get(n, 0) for n in bt.neighbours(b))
            p = share[c]
            rows.append({"block": b, "group": b[:5], "cuisine": c, "y": int(c in opened[b]),
                         "P": math.log(p / (1 - p)), "S": math.log1p(s), "Qr": zr[c][b], "Qo": zo[c][b]})
    return rows


def oof(X, y, g):
    out = np.zeros(len(y))
    for tr, te in GroupKFold(5).split(X, y, g):
        out[te] = LogisticRegression(max_iter=1000).fit(X[tr], y[tr]).predict_proba(X[te])[:, 1]
    return out


def block_aucs(rows, pred):
    by = {}
    for r, p in zip(rows, pred):
        by.setdefault(r["block"], ([], []))
        by[r["block"]][0].append(r["y"]); by[r["block"]][1].append(p)
    return {b: roc_auc_score(y, p) for b, (y, p) in by.items() if 0 < sum(y) < len(y)}


def top3(rows, pred):
    by = {}
    for r, p in zip(rows, pred):
        by.setdefault(r["block"], []).append((p, r["y"]))
    return float(np.mean([any(y for _, y in sorted(v, reverse=True)[:3]) for v in by.values()]))


def main():
    rows = build()
    y = np.array([r["y"] for r in rows]); g = np.array([r["group"] for r in rows])
    F = {k: np.array([r[k] for r in rows]) for k in ("P", "S", "Qr", "Qo")}
    preds = {"CITY": oof(np.c_[F["P"], F["S"]], y, g),
             "CITY+Q": oof(np.c_[F["P"], F["S"], F["Qr"]], y, g),
             "CITY+Qown": oof(np.c_[F["P"], F["S"], F["Qo"]], y, g),
             "Q_alone": oof(np.c_[F["P"], F["Qr"]], y, g)}
    aucs = {k: block_aucs(rows, v) for k, v in preds.items()}
    blocks = sorted(aucs["CITY"])
    diff = np.array([aucs["CITY+Q"][b] - aucs["CITY"][b] for b in blocks])
    point = float(diff.mean())
    grp = np.array([b[:5] for b in blocks]); ug = np.unique(grp); idx = {u: np.where(grp == u)[0] for u in ug}
    rng = np.random.default_rng(0)
    boots = [diff[np.concatenate([idx[u] for u in rng.choice(ug, len(ug))])].mean() for _ in range(2000)]
    lo, hi = (float(x) for x in np.percentile(boots, [2.5, 97.5]))
    # permutation: shuffle Q_ring across blocks within each cuisine, refit out-of-fold
    rng = np.random.default_rng(0)
    by_c = {}
    for i, r in enumerate(rows):
        by_c.setdefault(r["cuisine"], []).append(i)
    perm = []
    for _ in range(200):
        q = F["Qr"].copy()
        for c, ii in by_c.items():
            ii = np.array(ii); q[ii] = q[rng.permutation(ii)]
        a = block_aucs(rows, oof(np.c_[F["P"], F["S"], q], y, g))
        perm.append(float(np.mean([a[b] - aucs["CITY"][b] for b in blocks])))
    p_perm = float(np.mean([d >= point for d in perm]))
    out = {"blocks": len(blocks), "rows": len(rows),
           "mean_block_auc": {k: round(float(np.mean([v[b] for b in blocks])), 4) for k, v in aucs.items()},
           "top3_hit_rate": {k: round(top3(rows, v), 3) for k, v in preds.items()},
           "primary_diff": round(point, 4), "ci95": [round(lo, 4), round(hi, 4)],
           "permutation_p": round(p_perm, 3), "permutation_mean": round(float(np.mean(perm)), 4),
           "supported": bool(lo > 0 and p_perm < 0.05)}
    print(json.dumps(out, indent=1))
    json.dump(out, open("backtest7_results.json", "w"), indent=1)


if __name__ == "__main__":
    main()
