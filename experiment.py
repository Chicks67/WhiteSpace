"""Hold-out test: does cross-domain taste demand predict where a concept's places exist?

Grid: geohash-6 cells (about 1.2 km x 0.6 km) inside a borough.
Label: a cell is positive if it contains at least one place of the concept.
Spatial hold-out: a cell's score is averaged only over its geohash-7 sub-blocks that
contain NO place of the concept, so a restaurant cannot vouch for itself.
"""
import json
import sys

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold, cross_val_predict

import qloo

AREA = sys.argv[1] if len(sys.argv) > 1 else "Brooklyn"
CONCEPTS = {
    "Korean": "urn:tag:genre:place:restaurant:korean",
    "Vegan": "urn:tag:genre:place:restaurant:vegan",
    "Mexican": "urn:tag:genre:place:restaurant:mexican",
}
RESTAURANT = "urn:tag:genre:place:restaurant"
LOC = {"filter.location.query": AREA, "filter.location.radius": 0}


def supply(tag):
    places = []
    for page in range(1, 41):
        e = qloo.results(qloo.get("/v2/insights", **{"filter.type": "urn:entity:place",
                         "filter.tags": tag, "take": 50, "page": page, **LOC}), "entities")
        places += e
        if len(e) < 50:
            break
    return {p["location"]["geohash"][:7] for p in places if p.get("location")}, len(places)


def heatmap(**signal):
    cells = qloo.results(qloo.get("/v2/insights", **{"filter.type": "urn:heatmap", **signal, **LOC}), "heatmap")
    return {c["location"]["geohash"][:7]: c["query"]["affinity"] for c in cells}


def audience(tag):
    """The concept's cross-domain audience: brands, artists and films its fans over-index on."""
    ids, names = [], []
    for ft in ["urn:entity:brand", "urn:entity:artist", "urn:entity:movie"]:
        e = qloo.results(qloo.get("/v2/insights", **{"filter.type": ft, "signal.interests.tags": tag,
                         "filter.popularity.min": 0.6, "take": 8}), "entities")
        ids += [x["entity_id"] for x in e]
        names += [f"{x['name']} ({ft.split(':')[-1]})" for x in e]
    return ids, names


def cell_scores(heat, held_out):
    curr = {}
    for gh, a in heat.items():
        if gh not in held_out:
            curr.setdefault(gh[:6], []).append(a)
    return {g: np.mean(v) for g, v in curr.items()}


def run(name, tag):
    blocks, n_places = supply(tag)
    ids, names = audience(tag)
    signals = {
        "restaurant density (baseline)": heatmap(**{"signal.interests.tags": RESTAURANT}),
        "concept taste, held out (ours)": heatmap(**{"signal.interests.tags": tag}),
        "cross-domain audience brands": heatmap(**{"signal.interests.entities": ",".join(ids)}),
    }
    scores = {k: cell_scores(v, blocks) for k, v in signals.items()}
    cells = sorted(set.intersection(*(set(s) for s in scores.values())))
    y = np.array([any(b[:6] == c for b in blocks) for c in cells], dtype=int)
    arr = {k: np.array([s[c] for c in cells]) for k, s in scores.items()}

    out = {"concept": name, "area": AREA, "places": n_places, "cells": len(cells),
           "positive_cells": int(y.sum()), "audience": names, "auc": {}}
    for k, x in arr.items():
        out["auc"][k] = round(roc_auc_score(y, x), 3)

    # Does audience demand add signal beyond "where restaurants are"? 5-fold CV logistic.
    cv = StratifiedKFold(5, shuffle=True, random_state=0)
    base = arr["restaurant density (baseline)"].reshape(-1, 1)
    taste = np.column_stack([base, arr["concept taste, held out (ours)"]])
    allx = np.column_stack([taste, arr["cross-domain audience brands"]])
    for label, X in [("density only (CV)", base), ("density + concept taste (CV)", taste),
                     ("density + taste + audience (CV)", allx)]:
        p = cross_val_predict(LogisticRegression(), X, y, cv=cv, method="predict_proba")[:, 1]
        out["auc"][label] = round(roc_auc_score(y, p), 3)
    return out


if __name__ == "__main__":
    report = [run(n, t) for n, t in CONCEPTS.items()]
    with open(f"results_{AREA.lower().replace(' ', '_')}.json", "w") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    for r in report:
        print(f"\n{r['concept']} in {r['area']}: {r['places']} places, "
              f"{r['positive_cells']}/{r['cells']} cells positive")
        print("  audience:", ", ".join(r["audience"][:8]))
        for k, v in r["auc"].items():
            print(f"  AUC {v:.3f}  {k}")
