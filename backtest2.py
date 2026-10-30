"""Test 2 (PREREGISTRATION_2.md): audience music heatmaps, mechanism and usefulness."""
import json

import numpy as np
from scipy.stats import binomtest
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupKFold

import backtest as B

AUDIENCE = {
    "Korean": ["korean", "k_pop"], "Indian": ["indian", "bollywood"],
    "Japanese": ["j_pop", "anime"], "Mexican": ["mexican", "regional_mexican"],
    "Caribbean": ["reggae", "soca"], "Chinese": ["c_pop"], "Thai": ["thai"],
    "Middle Eastern": ["arabic", "middle_eastern"], "Latin American": ["latin", "reggaeton"],
    "Italian": ["italian", "italian_pop"], "Mediterranean": ["greek"],
}


def distances(heat, places):
    """Distance in metres from each geohash-7 sub-cell to the nearest place."""
    out = {}
    for gh, (_, lat, lon) in heat.items():
        out[gh] = min((B.metres(lat, lon, p, q) for p, q in places
                       if abs(p - lat) < 0.012 and abs(q - lon) < 0.016), default=1e9)
    return out


def cell_signal(heats, places, radius):
    """Per geohash-6 cell: mean over tags of the tag's mean affinity on sub-cells farther than radius."""
    per_tag = []
    for h in heats:
        d = distances(h, places)
        agg = {}
        for gh, (a, _, _) in h.items():
            if d[gh] > radius:
                agg.setdefault(gh[:6], []).append(a)
        per_tag.append({k: np.mean(v) for k, v in agg.items()})
    cells = set().union(*per_tag)
    return {c: float(np.mean([t[c] for t in per_tag if c in t])) for c in cells}


def presence_auc(sig, background, has):
    cells = [c for c in background if c in sig]
    y = [int(c in has) for c in cells]
    return roc_auc_score(y, [sig[c] for c in cells]) if 0 < sum(y) < len(y) else float("nan")


def retention(a0, a500):
    return (a500 - 0.5) / (a0 - 0.5)


def oof(rows, feats):
    X = np.array([[r[f] for f in feats] for r in rows])
    y = np.array([r["y"] for r in rows])
    out = np.zeros(len(y))
    for tr, te in GroupKFold(5).split(X, y, [r["block"] for r in rows]):
        out[te] = LogisticRegression(max_iter=1000).fit(X[tr], y[tr]).predict_proba(X[te])[:, 1]
    return out


def main():
    rest, pre, is_new, density, background, heat, mean_aff = B.build()
    report, mech, pooled = {"per_cuisine": {}}, [], {"y": [], "base": [], "full": [], "alone": [], "B1": [], "block": []}
    for c, tags in AUDIENCE.items():
        aud_heats = [h for h in (B.heatmap(f"urn:tag:genre:music:{t}") for t in tags) if h]
        places = [(r["lat"], r["lon"]) for r in pre if r["cuisine"] == c]
        has = {B.g6(lat, lon) for lat, lon in places}

        # A: mechanism
        aud = {r: presence_auc(cell_signal(aud_heats, places, r), background, has) for r in (0, 500)}
        cui = {r: presence_auc(cell_signal([heat[c]], places, r), background, has) for r in (0, 500)}
        tie = aud[0] <= 0.55 or cui[0] <= 0.55
        ret_a, ret_c = retention(aud[0], aud[500]), retention(cui[0], cui[500])
        mech.append((ret_a, ret_c, tie))

        # B: usefulness on the Test 1 H1 sample
        sig = cell_signal(aud_heats, places, 0)
        rows, _ = B.h1_rows(c, rest, pre, is_new, density, background, mean_aff)
        rows = [r for r in rows if r["cell"] in sig]
        for r in rows:
            r["AUD"] = sig[r["cell"]]
        y = np.array([r["y"] for r in rows])
        base, full = oof(rows, ["B1", "B2"]), oof(rows, ["B1", "B2", "AUD"])
        alone, b1 = np.array([r["AUD"] for r in rows]), np.array([r["B1"] for r in rows])
        d, se, p = B.delong(y, alone, b1)
        for k, v in (("y", y), ("base", base), ("full", full), ("alone", alone), ("B1", b1)):
            pooled[k] += list(v)
        pooled["block"] += [r["block"] for r in rows]

        report["per_cuisine"][c] = {
            "tags_used": len(aud_heats), "h1_cells": len(rows), "first_openings": int(y.sum()),
            "A_presence_auc": {"audience": {str(k): round(v, 3) for k, v in aud.items()},
                               "cuisine": {str(k): round(v, 3) for k, v in cui.items()}},
            "A_retention": {"audience": round(ret_a, 3), "cuisine": round(ret_c, 3), "tie": tie},
            "B_auc": {"base": round(roc_auc_score(y, base), 3), "full": round(roc_auc_score(y, full), 3),
                      "audience_alone": round(roc_auc_score(y, alone), 3), "B1": round(roc_auc_score(y, b1), 3)},
            "B_delong_alone_vs_B1": {"diff": round(d, 3), "p": round(p, 4)},
            "B_precision@20": {"full": round(B.precision_at(y, full, 20), 2), "base": round(B.precision_at(y, base, 20), 2)},
            "B_boyce": {"full": round(B.boyce(y, full), 2), "base": round(B.boyce(y, base), 2)},
        }
        print(f"{c:15s} A: aud {aud[0]:.3f}->{aud[500]:.3f} (ret {ret_a:+.2f}) | cui {cui[0]:.3f}->{cui[500]:.3f} "
              f"(ret {ret_c:+.2f}){' TIE' if tie else ''} || B: base {roc_auc_score(y, base):.3f} "
              f"full {roc_auc_score(y, full):.3f} alone {roc_auc_score(y, alone):.3f} B1 {roc_auc_score(y, b1):.3f}", flush=True)

    counted = [(a, c) for a, c, t in mech if not t]
    wins = sum(a > c for a, c in counted)
    A = {"median_retention_audience": round(float(np.median([m[0] for m in mech])), 3),
         "median_retention_cuisine": round(float(np.median([m[1] for m in mech])), 3),
         "sign_test": {"audience_wins": wins, "counted": len(counted),
                       "p_one_sided": round(binomtest(wins, len(counted), 0.5, alternative="greater").pvalue, 4) if counted else None}}
    A["supported"] = bool(A["median_retention_audience"] > A["median_retention_cuisine"]
                          and A["sign_test"]["p_one_sided"] is not None and A["sign_test"]["p_one_sided"] < 0.05)

    y = np.array(pooled["y"])
    arr = {k: np.array(pooled[k]) for k in ("base", "full", "alone", "B1")}
    lo, hi = B.block_bootstrap(y, arr["full"], arr["base"], pooled["block"])
    lo2, hi2 = B.block_bootstrap(y, arr["alone"], arr["B1"], pooled["block"])
    Bres = {"pooled_auc": {k: round(roc_auc_score(y, v), 3) for k, v in arr.items()},
            "full_minus_base": {"diff": round(roc_auc_score(y, arr["full"]) - roc_auc_score(y, arr["base"]), 3),
                                "ci95": [round(lo, 3), round(hi, 3)]},
            "alone_minus_B1": {"diff": round(roc_auc_score(y, arr["alone"]) - roc_auc_score(y, arr["B1"]), 3),
                               "ci95": [round(lo2, 3), round(hi2, 3)]},
            "rows": len(y), "positives": int(y.sum())}
    Bres["supported"] = bool(lo > 0)
    report["A_mechanism"], report["B_usefulness"] = A, Bres
    with open("backtest2_results.json", "w") as f:
        json.dump(report, f, indent=2)
    print("\nA", json.dumps(A, indent=1), "\nB", json.dumps(Bres, indent=1))


if __name__ == "__main__":
    main()
