"""Pre-registered NYC whitespace backtest. See PREREGISTRATION.md; this file implements it as written."""
import json
import math

import numpy as np
import pygeohash as pgh
from scipy.stats import binomtest, norm, spearmanr
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupKFold

import nyc
import qloo

T = "2024-01-01"
BOROUGHS = ["Brooklyn", "Queens", "Manhattan", "Bronx"]
CUISINES = {
    "Korean": "korean", "Mexican": "mexican", "Japanese": "japanese", "Thai": "thai",
    "Indian": "indian", "Caribbean": "caribbean", "Coffee/Tea": "coffee_shop",
    "Bakery Products/Desserts": "bakery", "Chinese": "chinese", "Pizza": "pizza",
    "Italian": "italian", "Mediterranean": "mediterranean", "Latin American": "latin_american",
    "Middle Eastern": "middle_eastern",
}
BOOT = 2000
rng = np.random.default_rng(0)


# ---------- data ----------
def heatmap(tag):
    """Qloo affinity per geohash-7 cell with its coordinates, merged over the four boroughs."""
    out = {}
    for b in BOROUGHS:
        cells = qloo.results(qloo.get("/v2/insights", **{
            "filter.type": "urn:heatmap", "signal.interests.tags": tag,
            "filter.location.query": b, "filter.location.radius": 0}), "heatmap")
        for c in cells:
            loc = c["location"]
            out[loc["geohash"][:7]] = (c["query"]["affinity"], loc["latitude"], loc["longitude"])
    return out


def g6(lat, lon):
    return pgh.encode(lat, lon, 6)


def neighbours(cell):
    lat, lon, dlat, dlon = pgh.decode_exactly(cell)
    return {pgh.encode(lat + i * 2 * dlat, lon + j * 2 * dlon, 6)
            for i in (-1, 0, 1) for j in (-1, 0, 1) if (i, j) != (0, 0)}


def metres(lat1, lon1, lat2, lon2):
    x = math.radians(lon2 - lon1) * math.cos(math.radians((lat1 + lat2) / 2))
    return 6371000 * math.hypot(x, math.radians(lat2 - lat1))


# ---------- statistics ----------
def delong(y, a, b):
    """Paired DeLong test: AUC(a) - AUC(b), its standard error and two-sided p-value."""
    pos, neg = y == 1, y == 0
    def comps(s):
        sp, sn = s[pos], s[neg]
        v10 = np.array([((x > sn).sum() + 0.5 * (x == sn).sum()) / len(sn) for x in sp])
        v01 = np.array([((sp > x).sum() + 0.5 * (sp == x).sum()) / len(sp) for x in sn])
        return v10.mean(), v10, v01
    auc_a, a10, a01 = comps(a)
    auc_b, b10, b01 = comps(b)
    s10, s01 = np.cov(np.vstack([a10, b10])), np.cov(np.vstack([a01, b01]))
    var = (s10[0, 0] + s10[1, 1] - 2 * s10[0, 1]) / len(a10) + (s01[0, 0] + s01[1, 1] - 2 * s01[0, 1]) / len(a01)
    se = math.sqrt(max(var, 1e-12))
    return auc_a - auc_b, se, 2 * norm.sf(abs(auc_a - auc_b) / se)


def precision_at(y, s, k):
    return y[np.argsort(-s, kind="stable")[:k]].mean()


def boyce(y, s):
    """Boyce index over score deciles: Spearman of decile vs predicted/expected positive ratio."""
    edges = np.quantile(s, np.linspace(0, 1, 11))
    bins = np.clip(np.searchsorted(edges, s, side="right") - 1, 0, 9)
    ratio = [(y[bins == i].sum() / y.sum()) / max((bins == i).mean(), 1e-9) for i in range(10)]
    return spearmanr(range(10), ratio).statistic


def block_bootstrap(y, a, b, blocks):
    """95% interval for AUC(a) - AUC(b), resampling geohash-5 blocks with replacement."""
    ids = {}
    for i, blk in enumerate(blocks):
        ids.setdefault(blk, []).append(i)
    groups = list(ids.values())
    diffs = []
    for _ in range(BOOT):
        idx = np.concatenate([groups[k] for k in rng.integers(0, len(groups), len(groups))])
        if 0 < y[idx].sum() < len(idx):
            diffs.append(roc_auc_score(y[idx], a[idx]) - roc_auc_score(y[idx], b[idx]))
    return np.percentile(diffs, [2.5, 97.5])


# ---------- build ----------
def build():
    rest = [r for r in nyc.restaurants() if r["boro"] in BOROUGHS]
    is_new = lambda r: bool(r["opened"]) and r["opened"] >= T
    pre = [r for r in rest if not is_new(r)]

    density = {}
    for r in pre:
        density[g6(r["lat"], r["lon"])] = density.get(g6(r["lat"], r["lon"]), 0) + 1
    background = sorted(density)

    heat = {c: heatmap(f"urn:tag:genre:place:restaurant:{t}") for c, t in CUISINES.items()}
    mean_aff = {}
    for c, h in heat.items():
        agg = {}
        for gh, (a, _, _) in h.items():
            agg.setdefault(gh[:6], []).append(a)
        mean_aff[c] = {k: float(np.mean(v)) for k, v in agg.items()}
    return rest, pre, is_new, density, background, heat, mean_aff


def h1_rows(c, rest, pre, is_new, density, background, mean_aff):
    had = {g6(r["lat"], r["lon"]) for r in pre if r["cuisine"] == c}
    opened = {g6(r["lat"], r["lon"]) for r in rest if r["cuisine"] == c and is_new(r)}
    others = [o for o in CUISINES if o != c]
    rows = []
    for cell in background:
        if cell in had or cell not in mean_aff[c]:
            continue
        peers = [mean_aff[o][cell] for o in others if cell in mean_aff[o]]
        A = mean_aff[c][cell]
        rows.append({
            "cell": cell, "block": cell[:5], "y": int(cell in opened),
            "M1": A, "M2": A - float(np.mean(peers)) if peers else 0.0,
            "B1": math.log1p(density[cell]),
            "B2": float(sum(1 for n in neighbours(cell) if n in had)),
        })
    eligible = sum(1 for cell in background if cell not in had)
    return rows, eligible


def m3_scores(rows):
    X = np.array([[r["B1"], r["B2"], r["M2"]] for r in rows])
    y = np.array([r["y"] for r in rows])
    groups = [r["block"] for r in rows]
    out, fold_auc = np.zeros(len(rows)), []
    for tr, te in GroupKFold(5).split(X, y, groups):
        if y[tr].sum() == 0:
            continue
        out[te] = LogisticRegression().fit(X[tr], y[tr]).predict_proba(X[te])[:, 1]
        if 0 < y[te].sum() < len(te):
            fold_auc.append(roc_auc_score(y[te], out[te]))
    return out, float(np.mean(fold_auc)) if fold_auc else float("nan")


def h2_sweep(c, pre, background, heat):
    """Presence AUC of raw taste after dropping sub-cells within r metres of a c restaurant."""
    places = [(r["lat"], r["lon"]) for r in pre if r["cuisine"] == c]
    has = {g6(lat, lon) for lat, lon in places}
    near = {}
    for gh, (a, lat, lon) in heat[c].items():
        d = min((metres(lat, lon, p, q) for p, q in places if abs(p - lat) < 0.012 and abs(q - lon) < 0.016),
                default=1e9)
        near.setdefault(gh[:6], []).append((a, d))
    out = {}
    for r in (0, 250, 500, 1000):
        cells, y, s = [], [], []
        for cell in background:
            vals = [a for a, d in near.get(cell, []) if d > r]
            if vals:
                y.append(int(cell in has))
                s.append(np.mean(vals))
        out[r] = round(roc_auc_score(y, s), 3) if 0 < sum(y) < len(y) else None
    return out


def main():
    rest, pre, is_new, density, background, heat, mean_aff = build()
    report = {"background_cells": len(background), "cutoff": T, "per_cuisine": {}}
    pooled = []
    for c in CUISINES:
        rows, eligible = h1_rows(c, rest, pre, is_new, density, background, mean_aff)
        y = np.array([r["y"] for r in rows])
        s = {k: np.array([r[k] for r in rows]) for k in ("M1", "M2", "B1", "B2")}
        s["M3"], m3_fold = m3_scores(rows)
        d, se, p = delong(y, s["M2"], s["B1"])
        report["per_cuisine"][c] = {
            "cells": len(rows), "coverage": round(len(rows) / max(eligible, 1), 3),
            "first_openings": int(y.sum()),
            "auc": {k: round(roc_auc_score(y, v), 3) for k, v in s.items()},
            "auc_M3_fold_mean": round(m3_fold, 3),
            "delong_M2_vs_B1": {"diff": round(d, 3), "se": round(se, 3), "p": round(p, 4)},
            "precision@10": {k: round(precision_at(y, v, 10), 2) for k, v in s.items()},
            "precision@20": {k: round(precision_at(y, v, 20), 2) for k, v in s.items()},
            "base_rate": round(y.mean(), 3),
            "boyce": {k: round(boyce(y, v), 2) for k, v in s.items()},
            "h2_presence_exclusion_sweep": h2_sweep(c, pre, background, heat),
        }
        pooled += rows
        print(f"{c:26s} n={len(rows):4d} first openings={int(y.sum()):3d} "
              + " ".join(f"{k}={roc_auc_score(y, v):.3f}" for k, v in s.items())
              + f" | M2-B1 {d:+.3f} p={p:.3f}", flush=True)

    y = np.array([r["y"] for r in pooled])
    blocks = [r["block"] for r in pooled]
    s = {k: np.array([r[k] for r in pooled]) for k in ("M1", "M2", "B1", "B2")}
    primary = {}
    for base in ("B1", "B2", "M1"):
        lo, hi = block_bootstrap(y, s["M2"], s[base], blocks)
        primary[f"M2_vs_{base}"] = {"diff": round(roc_auc_score(y, s["M2"]) - roc_auc_score(y, s[base]), 3),
                                    "ci95": [round(lo, 3), round(hi, 3)]}
    wins = sum(v["auc"]["M2"] > v["auc"]["B1"] for v in report["per_cuisine"].values())
    report["pooled"] = {
        "rows": len(pooled), "positives": int(y.sum()),
        "auc": {k: round(roc_auc_score(y, v), 3) for k, v in s.items()},
        "primary_tests": primary,
        "H1_supported": bool(primary["M2_vs_B1"]["ci95"][0] > 0),
        "sign_test_M2_beats_B1": {"wins": wins, "of": len(CUISINES),
                                  "p": round(binomtest(wins, len(CUISINES), 0.5).pvalue, 4)},
    }
    with open("backtest_results.json", "w") as f:
        json.dump(report, f, indent=2)
    print("\nPOOLED", json.dumps(report["pooled"], indent=2))


if __name__ == "__main__":
    main()
