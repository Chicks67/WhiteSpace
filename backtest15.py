"""Test 15 as registered in PREREGISTRATION_15.md: does Qloo's artist-to-artist affinity rank the act that
really opened for a headliner (Ticketmaster bills on sale since 2026-08-15) above acts that opened for others,
and does it beat fame, genre and the language model?
Aggregates go to backtest15_results.json; names to test15_detail.json (not committed).
python backtest15.py"""
import json
import os
import random
from datetime import datetime, timedelta

import numpy as np

import backtest14 as b14
import llm
import qloo

HEADLINERS, MAX_TRIED, NEGATIVES = 40, 400, 40
LLM_INSTRUCTIONS = (
    "You know live music touring in the United States. For one headlining act you get a numbered list of other "
    "acts. Score each from 0 to 100 for how likely it is to be the support (opening) act on that headliner's tour. "
    'Use the whole range. Reply as {"scores": {"1": n, "2": n, ...}} with every number in the list.')


def bills():
    """(headliner, supports, event id) for US music events on sale 2026-08-15 to 2026-10-12 with 2 to 4 named acts."""
    out, start = [], datetime(2026, 8, 15)
    while start < datetime(2026, 10, 13):
        end = min(start + timedelta(days=7), datetime(2026, 10, 13))
        for page in range(5):
            d = b14.tm("events.json", countryCode="US", classificationName="music", size=200, page=page,
                       onsaleStartDateTime=start.strftime("%Y-%m-%dT00:00:00Z"), onsaleEndDateTime=end.strftime("%Y-%m-%dT00:00:00Z"))
            for ev in d.get("_embedded", {}).get("events", []):
                acts = []
                for a in ev.get("_embedded", {}).get("attractions", []):
                    c = (a.get("classifications") or [{}])[0]
                    if a.get("name") and a["name"] not in [x["name"] for x in acts]:
                        acts.append({"name": a["name"], "genre": (c.get("genre") or {}).get("name"), "onsale": ""})
                if 2 <= len(acts) <= 4:
                    out.append((acts[0], acts[1:], ev["id"]))
            if d.get("page", {}).get("number", 0) + 1 >= d.get("page", {}).get("totalPages", 0):
                break
        start = end
    out.sort(key=lambda x: x[2])
    random.Random(15).shuffle(out)
    seen, one = set(), []
    for h, s, _ in out:
        if h["name"] not in seen:
            seen.add(h["name"]); one.append((h, s))
    return one


def similar_ok(eid):
    d = qloo.get("/v2/insights", **{"filter.type": "urn:entity:artist", "signal.interests.entities": eid, "take": 5})
    return "error" not in d and bool(qloo.results(d, "entities"))


def model_scores(h, ids, pool):
    name = os.path.join(qloo.CACHE, f"llm15_{h['id']}.json")
    if os.path.exists(name):
        return json.load(open(name))
    listing = "\n".join(f"{i}. {pool[x]['name']}" for i, x in enumerate(ids, 1))

    def check(o):
        if not isinstance(o.get("scores"), dict) or any(str(i) not in o["scores"] for i in range(1, len(ids) + 1)):
            raise ValueError("give a score for every number in the list")
    o, _ = llm.complete_json(LLM_INSTRUCTIONS, f"Headliner: {h['name']}.\n\nActs:\n{listing}", check=check, timeout=180)
    out = {x: float(o["scores"][str(i)]) for i, x in enumerate(ids, 1)}
    json.dump(out, open(name, "w"))
    return out


def main():
    rows, tried, why = [], 0, {"headliner_not_in_qloo": 0, "no_support_in_qloo": 0}
    for h, supports in bills():
        if len(rows) == HEADLINERS or tried == MAX_TRIED:
            break
        tried += 1
        hq = b14.qloo_act(h)
        if not hq or not similar_ok(hq["id"]):
            why["headliner_not_in_qloo"] += 1; continue
        kept = [a for a in (b14.qloo_act(s) for s in supports) if a and a["id"] != hq["id"]]
        if not kept:
            why["no_support_in_qloo"] += 1; continue
        rows.append({"headliner": hq, "supports": kept})
        print(len(rows), "headliners", flush=True)
    pool = {a["id"]: a for r in rows for a in r["supports"]}
    ids = sorted(pool)
    res = []
    for r in rows:
        h, own = r["headliner"], {a["id"] for a in r["supports"]}
        cand = [i for i in ids if i != h["id"]]
        aff = b14.affinities(h["id"], cand)
        score = {"affinity": lambda i: aff.get(i, -1.0), "fame": lambda i: pool[i]["popularity"],
                 "genre": lambda i: float(h["genre"] not in b14.NO_GENRE and pool[i]["genre"] == h["genre"])}
        y = [i in own for i in cand]
        out = {k: b14.auc(y, [f(i) for i in cand]) for k, f in score.items()}
        rng = random.Random(f"15-{h['id']}")
        short = sorted(own) + rng.sample([i for i in cand if i not in own], min(NEGATIVES, len(cand) - len(own)))
        rng.shuffle(short)
        model = model_scores(h, short, pool)
        ys = [i in own for i in short]
        out.update({"model_s": b14.auc(ys, [model[i] for i in short]), **{k + "_s": b14.auc(ys, [f(i) for i in short]) for k, f in score.items()}})
        res.append({k: None if v is None else round(v, 3) for k, v in out.items()} | {"supports": len(own)})
        print(len(res), "scored", flush=True)
    gain = lambda a, b: b14.interval([r[a] - r[b] for r in res])
    out = {"headliners": len(res), "headliners_tried": tried, "skipped": why, "pool_acts": len(ids),
           "auc": {k: b14.interval([r[k] for r in res]) for k in ("affinity", "fame", "genre")},
           "auc_on_the_model_list": {k: b14.interval([r[k + "_s"] for r in res]) for k in ("affinity", "fame", "genre", "model")},
           "gain_over_fame": gain("affinity", "fame"), "gain_over_genre": gain("affinity", "genre"),
           "gain_over_model": gain("affinity_s", "model_s"), "per_headliner": res}
    a, f, g, m = out["auc"]["affinity"]["ci95"][0] > 0.5, out["gain_over_fame"]["ci95"][0] > 0, \
        out["gain_over_genre"]["ci95"][0] > 0, out["gain_over_model"]["ci95"][0] > 0
    out["outcome"] = ("affinity AUC not above 0.5" if not a else "not above fame" if not f else "above fame, not above genre" if not g
                      else "above fame and genre, not above the language model" if not m else "above fame, genre and the language model")
    json.dump(out, open("backtest15_results.json", "w"), indent=1)
    json.dump([{"headliner": r["headliner"]["name"], "supports": [a["name"] for a in r["supports"]], **x} for r, x in zip(rows, res)],
              open("test15_detail.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print(json.dumps({k: v for k, v in out.items() if k != "per_headliner"}, indent=1))


if __name__ == "__main__":
    main()
