"""Rank whitespace: blocks where locals' taste for a concept is high but no such place exists."""
import sys

import numpy as np
from sklearn.linear_model import LogisticRegression

import qloo
from experiment import LOC, RESTAURANT, cell_scores, heatmap, supply

tag = sys.argv[1] if len(sys.argv) > 1 else "urn:tag:genre:place:restaurant:korean"
blocks, n = supply(tag)
density = cell_scores(heatmap(**{"signal.interests.tags": RESTAURANT}), blocks)
taste = cell_scores(heatmap(**{"signal.interests.tags": tag}), blocks)
cells = sorted(set(density) & set(taste))
y = np.array([any(b[:6] == c for b in blocks) for c in cells], dtype=int)
X = np.array([[density[c], taste[c]] for c in cells])
p = LogisticRegression().fit(X, y).predict_proba(X)[:, 1]

gaps = sorted((pr, c) for pr, c, has in zip(p, cells, y) if not has)[::-1][:5]
print(f"{n} existing places. Top whitespace cells (no existing place):")
for pr, c in gaps:
    e = qloo.results(qloo.get("/v2/insights", **{"filter.type": "urn:entity:place",
                     "filter.tags": RESTAURANT, "filter.location.geohash": c, "take": 5}), "entities")
    hood = next((x["properties"].get("geocode", {}).get("name") for x in e if x.get("properties")), "?")
    print(f"  {c}  fit {pr:.2f}  taste {taste[c]:.2f}  density {density[c]:.2f}  near {hood}")
