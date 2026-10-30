"""Test 21 as registered in PREREGISTRATION_21.md: split Test 15's and Test 16's saved per-headliner results at
the median of the headliner's Qloo popularity. No model call. Writes backtest21_results.json.
python backtest21.py"""
import json

import numpy as np
from scipy.stats import spearmanr

import qloo


def popularity(name):
    """Qloo's popularity for a headliner, from the search already made (cached)."""
    h = (qloo.get("/search", query=name, types="urn:entity:artist", take=3).get("results") or [None])[0]
    return float(h.get("popularity") or 0.0) if h else None


def interval(v):
    v = np.array(v, dtype=float)
    rng = np.random.default_rng(0)
    b = [float(np.mean(rng.choice(v, len(v)))) for _ in range(2000)]
    return {"mean": round(float(v.mean()), 3), "ci95": [round(float(x), 3) for x in np.percentile(b, [2.5, 97.5])], "n": len(v)}


def split(rows, diff):
    rows = [r for r in rows if r["pop"] is not None]
    med = float(np.median([r["pop"] for r in rows]))
    low, high = [r for r in rows if r["pop"] <= med], [r for r in rows if r["pop"] > med]
    rng = lambda g: [round(min(r["pop"] for r in g), 2), round(max(r["pop"] for r in g), 2)] if g else None
    return rows, {"median_popularity": round(med, 3),
                  "lesser_known": {**interval([diff(r) for r in low]), "popularity_range": rng(low)},
                  "better_known": {**interval([diff(r) for r in high]), "popularity_range": rng(high)} if high else None}


def main():
    t15 = [{**r, "pop": popularity(r["headliner"])} for r in json.load(open("test15_detail.json", encoding="utf-8"))]
    t16 = [{**r, "pop": popularity(r["headliner"])} for r in json.load(open("test16_detail.json", encoding="utf-8"))]
    d15 = lambda r: r["affinity_s"] - r["model_s"]
    d16 = lambda r: r["model_with_qloo_at50"] - r["model_alone_at50"]
    rows15, primary = split(t15, d15)
    _, secondary = split(t16, d16)
    pops, diffs = np.array([r["pop"] for r in rows15]), np.array([d15(r) for r in rows15])
    rho = float(spearmanr(pops, diffs).statistic)
    rng = np.random.default_rng(0)
    boots = []
    for _ in range(2000):
        i = rng.integers(0, len(pops), len(pops))
        s = spearmanr(pops[i], diffs[i]).statistic
        if not np.isnan(s):
            boots.append(float(s))
    trend = {"spearman": round(rho, 3), "ci95": [round(float(x), 3) for x in np.percentile(boots, [2.5, 97.5])], "n": len(pops)}
    lo, hi = primary["lesser_known"]["ci95"]
    reading = ("Qloo ahead of the model on lesser-known headliners" if lo > 0 else
               "Qloo closes the gap as fame falls, without overtaking" if trend["ci95"][1] < 0 else
               "Qloo not ahead of the model on lesser-known headliners either")
    s_lo = secondary["lesser_known"]["ci95"][0]
    out = {"primary_test15_qloo_auc_minus_model_auc": primary, "trend_test15": trend, "reading": reading,
           "secondary_test16_recall_with_qloo_minus_alone": secondary,
           "secondary_reading": "model found more real openers with Qloo for lesser-known headliners" if s_lo > 0 else "not shown",
           "test15_means": {k: round(float(np.mean([r[k] for r in rows15 if r["pop"] <= primary["median_popularity"]])), 3) for k in ("affinity_s", "model_s")}}
    json.dump(out, open("backtest21_results.json", "w"), indent=1)
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
