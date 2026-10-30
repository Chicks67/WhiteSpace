"""Test 5 as registered in PREREGISTRATION_5.md: do restaurants on high-scoring blocks survive?"""
import csv
import io
import json
import math
import os
import urllib.request
import zipfile
from datetime import datetime

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupKFold

import engine

SNAP = os.path.join(os.path.dirname(__file__), "data", "snapshots", "kaggle_2022_shivanielakurthy.zip")
S_DATE = datetime(2021, 10, 15)
COHORT_FROM = datetime(2018, 10, 15)
BOROS = {"BROOKLYN": "Brooklyn", "QUEENS": "Queens", "MANHATTAN": "Manhattan", "BRONX": "Bronx"}
DOHMH_TO_CONCEPT = {v[0]: k for k, v in engine.CONCEPTS.items()}
MIN_CLASS, BOOT = 15, 2000
rng = np.random.default_rng(0)


def snapshot():
    """One record per CAMIS from the snapshot: borough, cuisine, coordinates, earliest real inspection."""
    z = zipfile.ZipFile(SNAP)
    name = [n for n in z.namelist() if n.endswith(".csv")][0]
    out = {}
    for row in csv.DictReader(io.TextIOWrapper(z.open(name), encoding="utf-8", errors="replace")):
        c = row["CAMIS"]
        rec = out.setdefault(c, {"boro": BOROS.get(row["BORO"].upper()), "cuisine": row["CUISINE DESCRIPTION"],
                                 "lat": None, "lon": None, "first": None})
        try:
            lat, lon = float(row["Latitude"]), float(row["Longitude"])
            if lat > 1:
                rec["lat"], rec["lon"] = lat, lon
        except (TypeError, ValueError):
            pass
        try:
            d = datetime.strptime(row["INSPECTION DATE"][:10], "%m/%d/%Y")
        except ValueError:
            continue
        if d.year > 1900 and (rec["first"] is None or d < rec["first"]):
            rec["first"] = d
    return out


def camis_today():
    """Every CAMIS in today's dataset, with no filters."""
    path = os.path.join(os.path.dirname(__file__), "data", "camis_today.json")
    if not os.path.exists(path):
        url = "https://data.cityofnewyork.us/resource/43nn-pn8j.json?$select=distinct%20camis&$limit=200000"
        rows = json.load(urllib.request.urlopen(url, timeout=300))
        json.dump([r["camis"] for r in rows], open(path, "w"))
    return set(json.load(open(path)))


def build():
    snap = snapshot()
    located = {c: r for c, r in snap.items() if r["boro"] and r["lat"] is not None}
    by_cell, by_cell_cuisine, members = {}, {}, {}
    for c, r in located.items():
        cell = engine.g6(r["lat"], r["lon"])
        by_cell[cell] = by_cell.get(cell, 0) + 1
        by_cell_cuisine[(cell, r["cuisine"])] = by_cell_cuisine.get((cell, r["cuisine"]), 0) + 1
        members.setdefault(cell, []).append(c)
    today = camis_today()
    heat = {concept: engine._heat(engine.CONCEPTS[concept][1]) for concept in engine.CONCEPTS}
    rows = []
    for c, r in located.items():
        concept = DOHMH_TO_CONCEPT.get(r["cuisine"])
        if not concept or r["first"] is None or not (COHORT_FROM <= r["first"] <= S_DATE):
            continue
        cell = engine.g6(r["lat"], r["lon"])
        same = sum(by_cell_cuisine.get((n, r["cuisine"]), 0) for n in engine.neighbours(cell) | {cell}) - 1
        m = engine.MODEL[concept]
        D, S = math.log1p(by_cell[cell]), math.log1p(same)
        near400 = sum(1 for n in engine.neighbours(cell) | {cell} for o in members.get(n, [])
                      if o != c and located[o]["cuisine"] == r["cuisine"]
                      and engine.metres(r["lat"], r["lon"], located[o]["lat"], located[o]["lon"]) <= 400)
        rows.append({"camis": c, "concept": concept, "block": cell[:5], "cell6": cell, "y": int(c in today), "D": D, "S": S,
                     "lease": m["intercept"] + m["D"] * D + m["S"] * S, "qloo": heat[concept].get(cell),
                     "near400": near400})
    return rows, {"snapshot_restaurants": len(snap), "located_in_4_boroughs": len(located), "today_camis": len(today)}


def oof(X, y, groups):
    out = np.zeros(len(y))
    for tr, te in GroupKFold(5).split(X, y, groups):
        out[te] = LogisticRegression().fit(X[tr], y[tr]).predict_proba(X[te])[:, 1]
    return out


def main():
    rows, meta = build()
    per, data = {}, {}
    for concept in engine.CONCEPTS:
        rs = [r for r in rows if r["concept"] == concept]
        y = np.array([r["y"] for r in rs])
        n_surv, n_closed = int(y.sum()), int(len(y) - y.sum())
        entry = {"cohort": len(rs), "survived": n_surv, "closed": n_closed,
                 "survival_rate": round(n_surv / len(rs), 3) if rs else None}
        if n_surv >= MIN_CLASS and n_closed >= MIN_CLASS:
            q = [r for r in rs if r["qloo"] is not None]
            yq = np.array([r["y"] for r in q])
            g = [r["block"] for r in q]
            Xb = np.array([[r["D"], r["S"]] for r in q]); Xq = np.array([[r["D"], r["S"], r["qloo"]] for r in q])
            base, full = oof(Xb, yq, g), oof(Xq, yq, g)
            sc = {k: np.array([r[k] for r in rs]) for k in ("lease", "D", "S", "near400")}
            entry["auc"] = {k: round(roc_auc_score(y, v), 3) for k, v in sc.items()}
            entry["auc"]["qloo_alone"] = round(roc_auc_score(yq, [r["qloo"] for r in q]), 3)
            entry["auc"]["DS_oof"], entry["auc"]["DSQ_oof"] = round(roc_auc_score(yq, base), 3), round(roc_auc_score(yq, full), 3)
            data[concept] = {"y": y, "lease": sc["lease"], "blocks": [r["block"] for r in rs],
                             "yq": yq, "base": base, "full": full, "qblocks": g}
        per[concept] = entry
    used = list(data)
    q1 = float(np.mean([per[c]["auc"]["lease"] for c in used]))
    q2 = float(np.mean([per[c]["auc"]["DSQ_oof"] - per[c]["auc"]["DS_oof"] for c in used]))
    blocks = sorted({b for c in used for b in data[c]["blocks"]})
    idx = {c: {} for c in used}
    qidx = {c: {} for c in used}
    for c in used:
        for i, b in enumerate(data[c]["blocks"]):
            idx[c].setdefault(b, []).append(i)
        for i, b in enumerate(data[c]["qblocks"]):
            qidx[c].setdefault(b, []).append(i)
    b1, b2 = [], []
    for _ in range(BOOT):
        chosen = [blocks[k] for k in rng.integers(0, len(blocks), len(blocks))]
        a1, a2, ok = [], [], True
        for c in used:
            ii = np.array([i for b in chosen for i in idx[c].get(b, [])], int)
            jj = np.array([i for b in chosen for i in qidx[c].get(b, [])], int)
            d = data[c]
            if len(ii) == 0 or not (0 < d["y"][ii].sum() < len(ii)) or len(jj) == 0 or not (0 < d["yq"][jj].sum() < len(jj)):
                ok = False
                break
            a1.append(roc_auc_score(d["y"][ii], d["lease"][ii]))
            a2.append(roc_auc_score(d["yq"][jj], d["full"][jj]) - roc_auc_score(d["yq"][jj], d["base"][jj]))
        if ok:
            b1.append(np.mean(a1)); b2.append(np.mean(a2))
    ci1 = [round(float(x), 4) for x in np.percentile(b1, [2.5, 97.5])]
    ci2 = [round(float(x), 4) for x in np.percentile(b2, [2.5, 97.5])]
    out = {
        "meta": meta, "cohort_total": len(rows), "survival_rate_total": round(np.mean([r["y"] for r in rows]), 3),
        "cuisines_used": used, "per_cuisine": per, "resamples_used": len(b1),
        "q1_mean_auc_lease_score": round(q1, 4), "q1_ci95": ci1,
        "q1_outcome": "supported" if ci1[0] > 0.5 else "reversed" if ci1[1] < 0.5 else "no evidence either way",
        "q2_mean_auc_gain_qloo": round(q2, 4), "q2_ci95": ci2, "q2_supported": bool(ci2[0] > 0),
    }
    json.dump(out, open("backtest5_results.json", "w"), indent=1)
    print(json.dumps({k: v for k, v in out.items() if k != "per_cuisine"}, indent=1))


if __name__ == "__main__":
    main()
