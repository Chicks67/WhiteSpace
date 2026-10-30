"""Test 14 as registered in PREREGISTRATION_14.md with Amendment 1: does Qloo's venue-to-artist affinity rank
the acts a venue booked (Ticketmaster upcoming shows) above acts booked at other sampled venues, and does it
beat fame, genre and the language model's own knowledge?
Aggregates go to backtest14_results.json; names to test14_detail.json (not committed).
python backtest14.py"""
import hashlib
import json
import os
import random
import time
import urllib.error
import urllib.parse
import urllib.request

import numpy as np
from sklearn.metrics import roc_auc_score

import backtest10 as b10
import engine
import llm
import positioning
import qloo
import scene

TM = "https://app.ticketmaster.com/discovery/v2/"
CENTRE, VENUES, MAX_TRIED, MIN_ACTS, KEEP_ACTS, MIN_KEPT, NEAR = "40.73,-73.95", 40, 400, 6, 10, 5, 300
RECENT = "2026-08-13"  # 60 days before the run date, 2026-10-12
NO_GENRE = {None, "Other", "Undefined"}
LLM_INSTRUCTIONS = (
    "You know live music in New York City. For one venue you get a numbered list of music acts. Score each act "
    "from 0 to 100 for how likely it is to be booked to play at that venue. Use the whole range. "
    'Reply as {"scores": {"1": n, "2": n, ...}} with every number in the list.')


def tm(path, **q):
    """Ticketmaster Discovery GET, cached on disk beside the Qloo cache (private)."""
    url = TM + path + "?" + urllib.parse.urlencode(sorted(q.items()))
    name = os.path.join(qloo.CACHE, "tm_" + hashlib.md5(url.encode()).hexdigest() + ".json")
    if os.path.exists(name):
        return json.load(open(name, encoding="utf-8"))
    for attempt in range(10):  # a dropped connection gets several minutes to come back before the run gives up
        try:
            with urllib.request.urlopen(url + "&apikey=" + llm._env()["TICKETMASTER_API_KEY"], timeout=60) as r:
                data = json.load(r)
            break
        except urllib.error.HTTPError as e:
            if e.code != 429 or attempt == 9:
                raise RuntimeError(f"Ticketmaster HTTP {e.code}") from None
            time.sleep(2 * (attempt + 1))
        except (TimeoutError, urllib.error.URLError, ConnectionError):
            if attempt == 9:
                raise
            time.sleep(10 * (attempt + 1))
    time.sleep(0.25)  # the key allows 5 calls a second
    json.dump(data, open(name, "w", encoding="utf-8"))
    return data


def music_venues():
    """Venues in the upcoming Music events within 15 km. The API pages to 1,000 events, so six 30-day windows
    from the run date are fetched (Amendment 2)."""
    from datetime import datetime, timedelta
    seen, start = {}, datetime(2026, 10, 12)
    for w in range(6):
        a, b = start + timedelta(days=30 * w), start + timedelta(days=30 * (w + 1))
        for page in range(5):
            d = tm("events.json", latlong=CENTRE, radius=15, unit="km", classificationName="music", size=200, page=page, sort="date,asc",
                   startDateTime=a.strftime("%Y-%m-%dT00:00:00Z"), endDateTime=b.strftime("%Y-%m-%dT00:00:00Z"))
            for ev in d.get("_embedded", {}).get("events", []):
                for v in ev.get("_embedded", {}).get("venues", []):
                    loc = v.get("location") or {}
                    if v.get("id") and loc.get("latitude"):
                        seen[v["id"]] = {"id": v["id"], "name": v["name"], "lat": float(loc["latitude"]), "lon": float(loc["longitude"])}
            if d.get("page", {}).get("number", 0) + 1 >= d.get("page", {}).get("totalPages", 0):
                break
    rows = [seen[k] for k in sorted(seen)]
    random.Random(14).shuffle(rows)
    return rows


def acts_at(v):
    """Named acts in show-date order, each with its Ticketmaster genre and the date its show went on sale."""
    d = tm("events.json", venueId=v["id"], classificationName="music", size=100, sort="date,asc")
    out = {}
    for ev in d.get("_embedded", {}).get("events", []):
        onsale = ((ev.get("sales") or {}).get("public") or {}).get("startDateTime", "")[:10]
        for a in ev.get("_embedded", {}).get("attractions", []):
            if a.get("name") and a["name"] not in out:
                c = (a.get("classifications") or [{}])[0]
                out[a["name"]] = {"name": a["name"], "genre": (c.get("genre") or {}).get("name"), "onsale": onsale}
    return list(out.values())


def qloo_venue(v):
    for h in scene.search(v["name"], v["lat"], v["lon"]):
        if b10.same_name(h.get("name", ""), v["name"]) and \
                engine.metres(v["lat"], v["lon"], float(h["location"]["lat"]), float(h["location"]["lon"])) <= NEAR:
            d = qloo.get("/v2/insights", **{"filter.type": "urn:entity:artist", "signal.interests.entities": h["entity_id"], "take": 5})
            return h["entity_id"] if "error" not in d and qloo.results(d, "entities") else None
    return None


def qloo_act(act):
    h = (qloo.get("/search", query=act["name"], types="urn:entity:artist", take=3).get("results") or [None])[0]
    if h and positioning._norm(h.get("name", "")) == positioning._norm(act["name"]):
        return {**act, "id": h["entity_id"], "popularity": h.get("popularity") or 0.0}
    return None


def affinities(vid, ids):
    out = {}
    for i in range(0, len(ids), 40):
        d = qloo.get("/v2/insights", **{"filter.type": "urn:entity:artist", "signal.interests.entities": vid,
                                        "filter.results.entities": ",".join(ids[i:i + 40]), "take": 50})
        for x in qloo.results(d, "entities"):
            out[x["entity_id"]] = x.get("query", {}).get("affinity", 0.0)
    return out


def model_scores(v, ids, pool):
    """The language model's score for each act in `ids` at this venue; cached privately so a rerun costs nothing."""
    name = os.path.join(qloo.CACHE, f"llm14_{v['id']}.json")
    if os.path.exists(name):
        return json.load(open(name))
    listing = "\n".join(f"{i}. {pool[x]['name']}" for i, x in enumerate(ids, 1))

    def check(o):
        if not isinstance(o.get("scores"), dict) or any(str(i) not in o["scores"] for i in range(1, len(ids) + 1)):
            raise ValueError("give a score for every number in the list")
    o, _ = llm.complete_json(LLM_INSTRUCTIONS, f"Venue: {v['name']}, New York City.\n\nActs:\n{listing}", check=check, timeout=180)
    out = {x: float(o["scores"][str(i)]) for i, x in enumerate(ids, 1)}
    json.dump(out, open(name, "w"))
    return out


def auc(y, s):
    return float(roc_auc_score(y, s)) if 0 < sum(y) < len(y) else None


def interval(vals):
    vals = np.array([v for v in vals if v is not None], dtype=float)
    rng = np.random.default_rng(0)
    boots = [float(np.mean(rng.choice(vals, len(vals)))) for _ in range(2000)]
    return {"mean": round(float(vals.mean()), 3), "ci95": [round(float(v), 3) for v in np.percentile(boots, [2.5, 97.5])], "venues": len(vals)}


def main():
    venues, tried, why = [], 0, {"too_few_acts": 0, "not_in_qloo": 0, "too_few_acts_in_qloo": 0}
    for v in music_venues():
        if len(venues) == VENUES or tried == MAX_TRIED:
            break
        tried += 1
        acts = acts_at(v)
        if len(acts) < MIN_ACTS:
            why["too_few_acts"] += 1; continue
        vid = qloo_venue(v)
        if not vid:
            why["not_in_qloo"] += 1; continue
        kept = [a for a in (qloo_act(x) for x in acts[:KEEP_ACTS]) if a]
        if len(kept) < MIN_KEPT:
            why["too_few_acts_in_qloo"] += 1; continue
        venues.append({**v, "qloo": vid, "acts": kept})
        print(len(venues), "venues", flush=True)
    pool = {a["id"]: a for v in venues for a in v["acts"]}
    ids = sorted(pool)
    shared = {i for i in ids if sum(i in {a["id"] for a in v["acts"]} for v in venues) > 1}
    rows = []
    for v in venues:
        aff = affinities(v["qloo"], ids)
        own = {a["id"]: a for a in v["acts"]}

        def genre(i):
            g = pool[i]["genre"]
            others = [a for k, a in own.items() if k != i]
            return 0.0 if g in NO_GENRE or not others else sum(a["genre"] == g for a in others) / len(others)
        score = {"affinity": lambda i: aff.get(i, -1.0), "fame": lambda i: pool[i]["popularity"], "genre": genre}
        y = [i in own for i in ids]
        r = {k: auc(y, [f(i) for i in ids]) for k, f in score.items()}
        solo = [i for i in ids if i not in shared]
        r["affinity_unshared"] = auc([i in own for i in solo], [score["affinity"](i) for i in solo])
        for label, keep in (("affinity_recent_onsale", lambda a: a["onsale"] >= RECENT), ("affinity_older_onsale", lambda a: a["onsale"] < RECENT)):
            sub = [i for i in ids if i not in own or keep(own[i])]
            r[label] = auc([i in own for i in sub], [score["affinity"](i) for i in sub])
        rng = random.Random(f"14-{v['id']}")
        short = sorted(own) + rng.sample([i for i in ids if i not in own], 40)
        rng.shuffle(short)
        model = model_scores(v, short, pool)
        ys = [i in own for i in short]
        r.update({"model_s": auc(ys, [model[i] for i in short]), **{k + "_s": auc(ys, [f(i) for i in short]) for k, f in score.items()}})
        rows.append({k: None if x is None else round(x, 3) for k, x in r.items()} | {"acts": len(own)})
        print(len(rows), "scored", flush=True)
    gain = lambda a, b: interval([r[a] - r[b] for r in rows])
    out = {"venues": len(venues), "venues_tried": tried, "skipped": why, "pool_acts": len(ids), "acts_at_two_or_more_venues": len(shared),
           "auc": {k: interval([r[k] for r in rows]) for k in ("affinity", "fame", "genre", "affinity_unshared",
                                                                 "affinity_recent_onsale", "affinity_older_onsale")},
           "auc_on_the_model_list": {k: interval([r[k + "_s"] for r in rows]) for k in ("affinity", "fame", "genre", "model")},
           "gain_over_fame": gain("affinity", "fame"), "gain_over_genre": gain("affinity", "genre"),
           "gain_over_model": gain("affinity_s", "model_s"), "per_venue": rows}
    a, f, g, m = out["auc"]["affinity"]["ci95"][0] > 0.5, out["gain_over_fame"]["ci95"][0] > 0, \
        out["gain_over_genre"]["ci95"][0] > 0, out["gain_over_model"]["ci95"][0] > 0
    out["outcome"] = ("affinity AUC not above 0.5" if not a else "not above fame" if not f else "above fame, not above genre" if not g
                      else "above fame and genre, not above the language model" if not m else "above fame, genre and the language model")
    json.dump(out, open("backtest14_results.json", "w"), indent=1)
    json.dump([{"venue": v["name"], "acts": [x["name"] for x in v["acts"]], **r} for v, r in zip(venues, rows)],
              open("test14_detail.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print(json.dumps({k: v for k, v in out.items() if k != "per_venue"}, indent=1))


if __name__ == "__main__":
    main()
