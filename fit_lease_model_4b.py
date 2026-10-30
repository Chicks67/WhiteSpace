"""Lease models for the Test 4b cuisines (PREREGISTRATION_6.md): same DS logistic regression as
fit_lease_model.py, fitted on all background blocks. Adds them to lease_model.json; the original 14 are untouched."""
import json

import numpy as np
from sklearn.linear_model import LogisticRegression

import backtest as bt
import backtest4b as b4b
import engine

rest, pre, is_new, density, background, heat, mean_aff = bt.build()
model = json.load(open("lease_model.json"))
for concept, (cuisine, _) in engine.CONCEPTS_4B.items():
    rows = b4b.rows_all(cuisine, rest, pre, is_new, density, background)
    X = np.array([[r["D"], r["S"]] for r in rows]); y = np.array([r["y"] for r in rows])
    m = LogisticRegression().fit(X, y)
    model[concept] = {"intercept": float(m.intercept_[0]), "D": float(m.coef_[0][0]), "S": float(m.coef_[0][1]),
                      "rows": len(rows), "positives": int(y.sum()), "test": "4b"}
    print(concept, {k: round(v, 3) if isinstance(v, float) else v for k, v in model[concept].items()})
json.dump(model, open("lease_model.json", "w"), indent=1)
