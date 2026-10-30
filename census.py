"""Neighbourhood profiles from public data: who lives and works in each NYC neighbourhood (2020 NTAs).

Built with Test 6's code (backtest6.py): ACS 2019 to 2023 5-year estimates, LEHD LODES 2023 jobs and the
city's hotel parcels. Test 6 found that these answer "who is here" directly, while only 2 of Qloo's 7
audience tags matched them, so scout mode targets customers with these measures and uses Qloo for taste.
"""
import json
import math
import os
from functools import lru_cache

import backtest6

PATH = os.path.join(os.path.dirname(__file__), "data", "nta_profiles.json")

# What a founder may target, and the measure that answers it (direction: +1 = more is better)
TARGETS = {
    "students": ("college_share", "share of residents enrolled in college or graduate school"),
    "families": ("kids_share", "share of households with children"),
    "seniors": ("senior_share", "share of residents aged 65+"),
    "young_adults": ("young_share", "share of residents aged 20 to 34"),
    "office_workers": ("jobs_per_km2", "jobs located in the neighbourhood per square km"),
    "affluent": ("median_income", "median household income"),
    "budget": ("median_income", "median household income (lower first)"),
    "residents": ("pop_per_km2", "residents per square km"),
    "visitors": ("hotels_per_km2", "hotel properties per square km"),
}


def build():
    units = backtest6.ntas()
    meas, _ = backtest6.measures(units)
    out = []
    for code, m in meas.items():
        u = units[code]
        out.append({
            "code": code, "name": u["name"], "borough": u["boro"], "km2": round(u["km2"], 3),
            "population": int(m["pop"]), "pop_per_km2": round(m["pop"] / u["km2"]),
            "median_income": round(m["affluent"]) if m["affluent"] else None,
            "college_share": round(m["college"], 3) if m["college"] is not None else None,
            "kids_share": round(m["families"], 3) if m["families"] is not None else None,
            "senior_share": round(m["seniors"], 3), "young_share": round(m["young_adults"], 3),
            "jobs_per_km2": round(math.exp(m["business"])),
            "hotels_per_km2": round(math.expm1(m["tourists"]), 2),
        })
    os.makedirs(os.path.dirname(PATH), exist_ok=True)
    json.dump(out, open(PATH, "w"), indent=0)
    return out


@lru_cache(maxsize=1)
def profiles():
    rows = json.load(open(PATH)) if os.path.exists(PATH) else build()
    # NYC percentile of every measure, so the agent can say "higher than 90% of neighbourhoods"
    for key in ("median_income", "college_share", "kids_share", "senior_share", "young_share", "jobs_per_km2",
                "hotels_per_km2", "pop_per_km2"):
        vals = sorted(r[key] for r in rows if r[key] is not None)
        for r in rows:
            r[key + "_pct"] = None if r[key] is None else round(100 * sum(v < r[key] for v in vals) / len(vals))
    return {r["name"]: r for r in rows}


if __name__ == "__main__":
    p = profiles()
    print(len(p), "neighbourhoods")
    for n in ["Morningside Heights", "Astoria (Central)", "Borough Park", "Sunnyside"]:
        print(n, {k: v for k, v in p.get(n, {}).items() if not k.endswith("_pct")})
