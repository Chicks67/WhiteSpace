"""Test 23 as registered in PREREGISTRATION_23.md: does Qloo know which comedians share a crowd?
Part A: current Ticketmaster comedy bills, Qloo against fame and the model. Part B: the famous package tours.
Aggregates go to backtest23_results.json; names and scores to test23_detail.json (not committed).
python backtest23.py"""
import itertools
import json
import os
import random
from datetime import datetime, timedelta

import numpy as np

import backtest14 as b14
import llm
import positioning
import qloo

HEADLINERS, MAX_TRIED, NEGATIVES, MIN_KEPT = 40, 200, 40, 20
ALONE = ("You know stand-up comedy touring in the United States. For one headliner you get a numbered list of other "
         "acts. Score each from 0 to 100 for how likely it is to be on the same bill as that headliner, as support, "
         "opener or co-headliner. Use the whole range.")
WITH = ALONE + (" Beside each act is its fan-overlap score with the headliner from a taste database (0 to 1, or 'none' "
                "if the database has no score); use it as you see fit.")
FORMAT = ' Reply as {"scores": {"1": n, "2": n, ...}} with every number in the list.'
TOURS = {"kings": ["Steve Harvey", "D.L. Hughley", "Cedric the Entertainer", "Bernie Mac"],
         "queens": ["Laura Hayes", "Adele Givens", "Sommore", "Mo'Nique"],
         "blue collar": ["Jeff Foxworthy", "Bill Engvall", "Ron White", "Larry the Cable Guy"],
         "latin kings": ["Paul Rodriguez", "Cheech Marin", "George Lopez", "Joey Medina", "Alex Reymundo"],
         "axis of evil": ["Ahmed Ahmed", "Maz Jobrani", "Aron Kader", "Dean Obeidallah"],
         "comedians of comedy": ["Patton Oswalt", "Brian Posehn", "Maria Bamford", "Zach Galifianakis"],
         "kims": ["Bobby Lee", "Ken Jeong", "Kevin Shea", "Steve Byrne"],
         "wild west": ["John Caparulo", "Bret Ernst", "Sebastian Maniscalco", "Ahmed Ahmed"]}
PROBED = {"Steve Harvey", "D.L. Hughley", "Cedric the Entertainer", "Bernie Mac", "Sebastian Maniscalco"}


def bills():
    out, day = [], datetime(2026, 7, 1)
    while day < datetime(2026, 10, 14):
        nxt = day + timedelta(days=1)
        for page in range(5):
            d = b14.tm("events.json", countryCode="US", classificationName="comedy", size=200, page=page,
                       onsaleStartDateTime=day.strftime("%Y-%m-%dT00:00:00Z"), onsaleEndDateTime=nxt.strftime("%Y-%m-%dT00:00:00Z"))
            for ev in d.get("_embedded", {}).get("events", []):
                acts = list(dict.fromkeys(a["name"] for a in ev.get("_embedded", {}).get("attractions", []) if a.get("name")))
                if 2 <= len(acts) <= 4:
                    out.append((acts[0], acts[1:], ev["id"]))
            if d.get("page", {}).get("number", 0) + 1 >= d.get("page", {}).get("totalPages", 0):
                break
        day = nxt
    out.sort(key=lambda x: x[2])
    random.Random(23).shuffle(out)
    seen, one = set(), []
    for h, s, _ in out:
        if h not in seen:
            seen.add(h); one.append((h, s))
    return one


def person(name):
    h = (qloo.get("/search", query=name, types="urn:entity:person", take=3).get("results") or [None])[0]
    if h and positioning._norm(h.get("name", "")) == positioning._norm(name):
        return {"name": h["name"], "id": h["entity_id"], "popularity": h.get("popularity") or 0.0}
    return None


def scores(pid, ids):
    out = {}
    for i in range(0, len(ids), 40):
        d = qloo.get("/v2/insights", **{"filter.type": "urn:entity:person", "signal.interests.entities": pid,
                                        "filter.results.entities": ",".join(ids[i:i + 40]), "take": 50})
        for x in qloo.results(d, "entities"):
            out[x["entity_id"]] = x.get("query", {}).get("affinity", 0.0)
    return out


def similar_ok(pid):
    d = qloo.get("/v2/insights", **{"filter.type": "urn:entity:person", "signal.interests.entities": pid, "take": 5})
    return "error" not in d and bool(qloo.results(d, "entities"))


def model(tag, h, short, pool, aff):
    name = os.path.join(qloo.CACHE, f"llm23_{tag}_{h['id']}.json")
    if os.path.exists(name):
        return json.load(open(name))
    show = lambda x: f" (fan overlap {aff[x]:.2f})" if x in aff else " (fan overlap none)"
    listing = "\n".join(f"{i}. {pool[x]['name']}{show(x) if tag == 'with' else ''}" for i, x in enumerate(short, 1))

    def check(o):
        if not isinstance(o.get("scores"), dict) or any(str(i) not in o["scores"] for i in range(1, len(short) + 1)):
            raise ValueError("give a score for every number in the list")
    o, _ = llm.complete_json((WITH if tag == "with" else ALONE) + FORMAT, f"Headliner: {h['name']}.\n\nActs:\n{listing}", check=check, timeout=180)
    out = {x: float(o["scores"][str(i)]) for i, x in enumerate(short, 1)}
    json.dump(out, open(name, "w"))
    return out


def part_a():
    rows, tried, why = [], 0, {"headliner_not_in_qloo": 0, "no_bill_mate_in_qloo": 0}
    for h, mates in bills():
        if len(rows) == HEADLINERS or tried == MAX_TRIED:
            break
        tried += 1
        hq = person(h)
        if not hq or not similar_ok(hq["id"]):
            why["headliner_not_in_qloo"] += 1; continue
        kept = [a for a in (person(m) for m in mates) if a and a["id"] != hq["id"]]
        if not kept:
            why["no_bill_mate_in_qloo"] += 1; continue
        rows.append({"headliner": hq, "mates": kept})
        print(len(rows), "headliners kept of", tried, "tried", flush=True)
    if len(rows) < MIN_KEPT:
        return {"headliners": len(rows), "headliners_tried": tried, "skipped": why, "reading": "too few comedy bills to say"}, []
    pool = {a["id"]: a for r in rows for a in r["mates"]}
    ids, res, detail = sorted(pool), [], []
    for r in rows:
        h, own = r["headliner"], {a["id"] for a in r["mates"]}
        cand = [i for i in ids if i != h["id"]]
        rng = random.Random(f"23-{h['id']}")
        others = [i for i in cand if i not in own]
        short = sorted(own) + rng.sample(others, min(NEGATIVES, len(others)))
        rng.shuffle(short)
        aff = scores(h["id"], short)
        y = [i in own for i in short]
        alone, both = model("alone", h, short, pool, aff), model("with", h, short, pool, aff)
        out = {"qloo": b14.auc(y, [aff.get(i, -1.0) for i in short]), "fame": b14.auc(y, [pool[i]["popularity"] for i in short]),
               "model_alone": b14.auc(y, [alone[i] for i in short]), "model_with_qloo": b14.auc(y, [both[i] for i in short]),
               "headliner_popularity": round(h["popularity"], 2), "mates": len(own), "shortlist": len(short),
               "share_with_no_qloo_score": round(sum(i not in aff for i in short) / len(short), 3)}
        res.append(out)
        detail.append({"headliner": h["name"], "mates": [a["name"] for a in r["mates"]], **out})
        print(len(res), "scored", flush=True)
    res = [r for r in res if r["qloo"] is not None]
    gain = lambda a, b: b14.interval([r[a] - r[b] for r in res])
    out = {"headliners": len(res), "headliners_tried": tried, "skipped": why, "pool_acts": len(ids),
           "auc": {k: b14.interval([r[k] for r in res]) for k in ("qloo", "fame", "model_alone", "model_with_qloo")},
           "qloo_minus_fame": gain("qloo", "fame"), "with_qloo_minus_alone": gain("model_with_qloo", "model_alone"),
           "qloo_minus_model_alone": gain("qloo", "model_alone"),
           "headliner_popularity_quartiles": [round(float(v), 2) for v in np.percentile([r["headliner_popularity"] for r in res], [25, 50, 75])],
           "mean_share_with_no_qloo_score": round(float(np.mean([r["share_with_no_qloo_score"] for r in res])), 3)}
    three = lambda g: "above" if g["ci95"][0] > 0 else "below" if g["ci95"][1] < 0 else "no different"
    out["reading_1"] = ("Qloo's score ranks the comics who really share a bill above others, and it is not just fame"
                        if out["auc"]["qloo"]["ci95"][0] > 0.5 and out["qloo_minus_fame"]["ci95"][0] > 0 else "not shown")
    out["reading_2_model_with_qloo_against_alone"] = three(out["with_qloo_minus_alone"])
    out["reading_3_qloo_against_model_alone"] = three(out["qloo_minus_model_alone"])
    return out, detail


def pair_auc(comics, score, together, skip=lambda a, b: False):
    pos, neg = [], []
    for a, b in itertools.combinations(comics, 2):
        if a == b or skip(a, b) or score(a, b) is None:
            continue
        (pos if together(a, b) else neg).append(score(a, b))
    if not pos or not neg:
        return None
    pos, neg = np.array(pos)[:, None], np.array(neg)[None, :]
    return float(np.mean((pos > neg) + 0.5 * (pos == neg)))


def part_b():
    names = list(dict.fromkeys(n for t in TOURS.values() for n in t))
    found = {n: p for n in names if (p := person(n))}
    ids = {n: p["id"] for n, p in found.items()}
    M = {n: scores(ids[n], [ids[m] for m in found if m != n]) for n in found}

    def score(a, b):
        v = [x for x in (M[a].get(ids[b]), M[b].get(ids[a])) if x is not None]
        return float(np.mean(v)) if v else None
    together = lambda a, b: any(a in t and b in t for t in TOURS.values())
    probed = lambda a, b: a in PROBED and b in PROBED
    comics = list(found)

    def boot(skip):
        point = pair_auc(comics, score, together, skip)
        rng, bs = np.random.default_rng(0), []
        for _ in range(2000):
            v = pair_auc(list(rng.choice(comics, len(comics))), score, together, skip)
            if v is not None:
                bs.append(v)
        return {"auc": None if point is None else round(point, 3), "ci95": [round(float(x), 3) for x in np.percentile(bs, [2.5, 97.5])]}
    pairs = list(itertools.combinations(comics, 2))
    out = {"comics_named": len(names), "comics_found": len(found), "not_found": [n for n in names if n not in found],
           "pairs": len(pairs), "pairs_with_a_score": sum(score(a, b) is not None for a, b in pairs),
           "toured_together_pairs": sum(together(a, b) for a, b in pairs),
           "all_pairs": boot(lambda a, b: False), "pairs_not_in_the_probe": boot(probed)}
    out["reading"] = ("with no labels, Qloo's scores put real tour-mates together"
                      if out["pairs_not_in_the_probe"]["ci95"][0] > 0.5 else "not shown")
    return out, {f"{a} / {b}": score(a, b) for a, b in pairs}


def main():
    b, bd = part_b()
    print(json.dumps(b, indent=1), flush=True)
    a, ad = part_a()
    out = {"part_a_current_bills": a, "part_b_package_tours": b}
    json.dump(out, open("backtest23_results.json", "w"), indent=1)
    json.dump({"part_a": ad, "part_b": bd}, open("test23_detail.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
