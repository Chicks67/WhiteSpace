"""Test 17 as registered in PREREGISTRATION_17.md: does Qloo's city-level artist affinity pick the markets an
artist really plays (Ticketmaster shows on sale 2026-08-15 to 2026-10-12), against market size and the language
model? Aggregates go to backtest17_results.json; names to test17_detail.json (not committed).
python backtest17.py"""
import json
import os
import random
from datetime import datetime, timedelta

import backtest14 as b14
import engine
import llm
import qloo

ARTISTS, MIN_MKT, MAX_MKT, REACH_KM = 60, 5, 30, 60
# 40 large US metros: (name, lat, lon, approximate 2020 metro population in millions). Fixed before any result.
MARKETS = [("New York", 40.71, -74.01, 20.1), ("Los Angeles", 34.05, -118.24, 13.2), ("Chicago", 41.88, -87.63, 9.6),
           ("Dallas", 32.78, -96.80, 7.6), ("Houston", 29.76, -95.37, 7.1), ("Washington", 38.91, -77.04, 6.4),
           ("Philadelphia", 39.95, -75.17, 6.2), ("Miami", 25.76, -80.19, 6.1), ("Atlanta", 33.75, -84.39, 6.1),
           ("Boston", 42.36, -71.06, 4.9), ("Phoenix", 33.45, -112.07, 4.8), ("San Francisco", 37.77, -122.42, 4.7),
           ("Detroit", 42.33, -83.05, 4.4), ("Seattle", 47.61, -122.33, 4.0), ("Minneapolis", 44.98, -93.27, 3.7),
           ("San Diego", 32.72, -117.16, 3.3), ("Tampa", 27.95, -82.46, 3.2), ("Denver", 39.74, -104.99, 3.0),
           ("Baltimore", 39.29, -76.61, 2.8), ("St. Louis", 38.63, -90.20, 2.8), ("Orlando", 28.54, -81.38, 2.7),
           ("Charlotte", 35.23, -80.84, 2.7), ("San Antonio", 29.42, -98.49, 2.6), ("Portland", 45.52, -122.68, 2.5),
           ("Sacramento", 38.58, -121.49, 2.4), ("Pittsburgh", 40.44, -80.00, 2.4), ("Austin", 30.27, -97.74, 2.3),
           ("Las Vegas", 36.17, -115.14, 2.3), ("Cincinnati", 39.10, -84.51, 2.3), ("Kansas City", 39.10, -94.58, 2.2),
           ("Columbus", 39.96, -83.00, 2.1), ("Indianapolis", 39.77, -86.16, 2.1), ("Cleveland", 41.50, -81.69, 2.1),
           ("Nashville", 36.16, -86.78, 2.0), ("Jacksonville", 30.33, -81.66, 1.6), ("Oklahoma City", 35.47, -97.52, 1.4),
           ("Raleigh", 35.78, -78.64, 1.4), ("Memphis", 35.15, -90.05, 1.3), ("Louisville", 38.25, -85.76, 1.3),
           ("Salt Lake City", 40.76, -111.89, 1.3)]
LLM_INSTRUCTIONS = (
    "You know live music touring in the United States. For one act you get a numbered list of US metro areas. "
    "Score each from 0 to 100 for how likely the act is to play a show there on its current US tour. Use the whole "
    'range. Reply as {"scores": {"1": n, "2": n, ...}} with every number in the list.')


def market_of(lat, lon):
    d, i = min((engine.metres(lat, lon, m[1], m[2]), i) for i, m in enumerate(MARKETS))
    return i if d <= REACH_KM * 1000 else None


def tours():
    """{act name: set of market indexes} from the daily on-sale windows Test 16 fetched."""
    out, day = {}, datetime(2026, 8, 15)
    while day < datetime(2026, 10, 13):
        nxt = day + timedelta(days=1)
        for page in range(5):
            d = b14.tm("events.json", countryCode="US", classificationName="music", size=200, page=page,
                       onsaleStartDateTime=day.strftime("%Y-%m-%dT00:00:00Z"), onsaleEndDateTime=nxt.strftime("%Y-%m-%dT00:00:00Z"))
            for ev in d.get("_embedded", {}).get("events", []):
                loc = ((ev.get("_embedded", {}).get("venues") or [{}])[0].get("location") or {})
                if not loc.get("latitude"):
                    continue
                m = market_of(float(loc["latitude"]), float(loc["longitude"]))
                if m is not None:
                    for a in ev.get("_embedded", {}).get("attractions", []):
                        if a.get("name"):
                            out.setdefault(a["name"], set()).add(m)
            if d.get("page", {}).get("number", 0) + 1 >= d.get("page", {}).get("totalPages", 0):
                break
        day = nxt
    return out


def city_scores(ids):
    """{market index: {artist id: affinity}} with the market's point and a 25 km radius as the location signal."""
    out = {}
    for i, (_, lat, lon, _) in enumerate(MARKETS):
        out[i] = {}
        for j in range(0, len(ids), 40):
            d = qloo.get("/v2/insights", **{"filter.type": "urn:entity:artist", "signal.location": f"POINT({lon:.4f} {lat:.4f})",
                                            "signal.location.radius": 25000, "filter.results.entities": ",".join(ids[j:j + 40]), "take": 50})
            for x in qloo.results(d, "entities"):
                out[i][x["entity_id"]] = x.get("query", {}).get("affinity", 0.0)
    return out


def model_scores(act):
    name = os.path.join(qloo.CACHE, f"llm17_{act['id']}.json")
    if os.path.exists(name):
        return json.load(open(name))
    order = list(range(len(MARKETS)))
    random.Random(f"17-{act['id']}").shuffle(order)
    listing = "\n".join(f"{n}. {MARKETS[i][0]}" for n, i in enumerate(order, 1))

    def check(o):
        if not isinstance(o.get("scores"), dict) or any(str(n) not in o["scores"] for n in range(1, len(order) + 1)):
            raise ValueError("give a score for every number in the list")
    o, _ = llm.complete_json(LLM_INSTRUCTIONS, f"Act: {act['name']}.\n\nMetro areas:\n{listing}", check=check, timeout=180)
    out = {str(i): float(o["scores"][str(n)]) for n, i in enumerate(order, 1)}
    json.dump(out, open(name, "w"))
    return out


def main():
    t = tours()
    eligible = sorted(n for n, m in t.items() if MIN_MKT <= len(m) <= MAX_MKT)
    random.Random(17).shuffle(eligible)
    acts = []
    for n in eligible:
        if len(acts) == ARTISTS:
            break
        a = b14.qloo_act({"name": n, "genre": None, "onsale": ""})
        if a and a["id"] not in {x["id"] for x in acts}:
            acts.append({**a, "markets": sorted(t[n])})
    print(len(t), "acts with a show in a market;", len(eligible), "eligible;", len(acts), "resolved", flush=True)
    scores = city_scores([a["id"] for a in acts])
    rows = []
    for a in acts:
        y = [i in a["markets"] for i in range(len(MARKETS))]
        model = model_scores(a)
        others = [x for x in acts if x["id"] != a["id"]]  # market draw: how many of the other acts play each market
        rows.append({"qloo": b14.auc(y, [scores[i].get(a["id"], -1.0) for i in range(len(MARKETS))]),
                     "size": b14.auc(y, [m[3] for m in MARKETS]),
                     "draw": b14.auc(y, [sum(i in x["markets"] for x in others) / len(others) for i in range(len(MARKETS))]),
                     "model": b14.auc(y, [model[str(i)] for i in range(len(MARKETS))]),
                     "markets_played": len(a["markets"]), "markets_scored_by_qloo": sum(a["id"] in scores[i] for i in range(len(MARKETS)))})
        print(len(rows), "scored", flush=True)
    gain = lambda b: b14.interval([r["qloo"] - r[b] for r in rows])
    out = {"artists": len(rows), "eligible_artists": len(eligible),
           "auc": {k: b14.interval([r[k] for r in rows]) for k in ("qloo", "size", "draw", "model")},
           "gain_over_size": gain("size"), "gain_over_draw": gain("draw"), "gain_over_model": gain("model"),
           "mean_markets_played": round(sum(r["markets_played"] for r in rows) / len(rows), 1),
           "mean_markets_scored_by_qloo": round(sum(r["markets_scored_by_qloo"] for r in rows) / len(rows), 1), "per_artist": rows}
    a, s, m = out["auc"]["qloo"]["ci95"][0] > 0.5, out["gain_over_size"]["ci95"][0] > 0, out["gain_over_model"]["ci95"][0] > 0
    dr = out["gain_over_draw"]["ci95"][0] > 0
    out["outcome"] = ("Qloo's AUC not above 0.5" if not a else "not above market size" if not s
                      else "above market size, not above market draw" if not dr
                      else "above market size and market draw, not above the language model" if not m
                      else "above market size, market draw and the language model")
    json.dump(out, open("backtest17_results.json", "w"), indent=1)
    json.dump([{"artist": a["name"], "markets": [MARKETS[i][0] for i in a["markets"]], **r} for a, r in zip(acts, rows)],
              open("test17_detail.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print(json.dumps({k: v for k, v in out.items() if k != "per_artist"}, indent=1))


if __name__ == "__main__":
    main()
