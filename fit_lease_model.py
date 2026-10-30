"""Fit the lease score registered as the Test 4 winner (DS): per-cuisine logistic regression on
D = log(1 + restaurants in block) and S = log(1 + same-cuisine restaurants in block and 8 neighbours),
trained on all blocks with pre-2024 features and 2024 to 2026 first openings. Writes lease_model.json."""
import json

import numpy as np
from sklearn.linear_model import LogisticRegression

import backtest as bt
import backtest4 as b4
import engine

rest, pre, is_new, density, background, heat, mean_aff = bt.build()
out = {}
for concept, (cuisine, _) in engine.CONCEPTS.items():
    rows = b4.rows_for(cuisine, rest, pre, is_new, density, background, mean_aff)
    X = np.array([[r["D"], r["S"]] for r in rows]); y = np.array([r["y"] for r in rows])
    m = LogisticRegression().fit(X, y)
    out[concept] = {"intercept": float(m.intercept_[0]), "D": float(m.coef_[0][0]), "S": float(m.coef_[0][1]),
                    "rows": len(rows), "positives": int(y.sum())}
    print(concept, {k: round(v, 3) for k, v in out[concept].items()})
json.dump(out, open("lease_model.json", "w"), indent=1)
