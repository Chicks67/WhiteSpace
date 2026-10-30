"""Test 16 as registered in PREREGISTRATION_16.md: starting from no shortlist, does GPT-6 Astra find more real
tour openers when it can see Qloo's candidates than on its own? Fresh headliners (from the 57th in Test 15's order).
Aggregates go to backtest16_results.json; names to test16_detail.json (not committed).
python backtest16.py"""
import json
import os

import numpy as np

import backtest14 as b14
import backtest15 as b15
import llm
import positioning
import qloo

HEADLINERS, SKIP, MAX_TRIED, K = 100, 56, 400, 50
ALONE = ("You know live music touring in the United States. Name the {k} acts most likely to be the support "
         "(opening) act on the headliner's current US tour, most likely first. "
         'Reply as {{"acts": ["name", ...]}} with exactly {k} names.')
WITH = ("You know live music touring in the United States. Name the {k} acts most likely to be the support "
        "(opening) act on the headliner's current US tour, most likely first. You also get a list of artists whose "
        "fans overlap most with the headliner's, from a taste database, each with an affinity score and a popularity "
        "score from 0 to 1. Use it as you see fit: pick from it, reorder it, and add acts of your own. "
        'Reply as {{"acts": ["name", ...]}} with exactly {k} names.')


def cached(tag, hid, fn):
    name = os.path.join(qloo.CACHE, f"llm16_{tag}_{hid}.json")
    if os.path.exists(name):
        return json.load(open(name, encoding="utf-8"))
    out = fn()
    json.dump(out, open(name, "w", encoding="utf-8"), ensure_ascii=False)
    return out


def ask(instructions, prompt):
    def check(o):
        if not isinstance(o.get("acts"), list) or len(o["acts"]) < K // 2 or not all(isinstance(x, str) for x in o["acts"]):
            raise ValueError(f"reply with a list of {K} act names")
    o, _ = llm.complete_json(instructions.format(k=K), prompt, check=check, timeout=180)
    return o["acts"][:K]


def similar(eid, take):
    """Qloo's highest-affinity artists, in pages of 50 (the API's limit)."""
    out = []
    for page in range(1, take // 50 + 1):
        d = qloo.get("/v2/insights", **{"filter.type": "urn:entity:artist", "signal.interests.entities": eid, "take": 50, "page": page})
        if "error" in d:
            return None
        out += [{"name": x["name"], "affinity": round(x.get("query", {}).get("affinity", 0), 3), "popularity": round(x.get("popularity") or 0, 2)}
                for x in qloo.results(d, "entities") if x.get("entity_id") != eid]
    return out


def bills():
    """Amendment 1: Test 15's events fetched in daily on-sale windows, minus the headliners Test 15 tried."""
    import random
    from datetime import datetime, timedelta
    used = {h["name"] for h, _ in b15.bills()[:SKIP]}
    out, day = [], datetime(2026, 8, 15)
    while day < datetime(2026, 10, 13):
        nxt = day + timedelta(days=1)
        for page in range(5):
            d = b14.tm("events.json", countryCode="US", classificationName="music", size=200, page=page,
                       onsaleStartDateTime=day.strftime("%Y-%m-%dT00:00:00Z"), onsaleEndDateTime=nxt.strftime("%Y-%m-%dT00:00:00Z"))
            for ev in d.get("_embedded", {}).get("events", []):
                acts = list(dict.fromkeys(a["name"] for a in ev.get("_embedded", {}).get("attractions", []) if a.get("name")))
                if 2 <= len(acts) <= 4 and acts[0] not in used:
                    out.append(({"name": acts[0], "genre": None, "onsale": ""}, [{"name": n} for n in acts[1:]], ev["id"]))
            if d.get("page", {}).get("number", 0) + 1 >= d.get("page", {}).get("totalPages", 0):
                break
        day = nxt
    out.sort(key=lambda x: x[2])
    random.Random(16).shuffle(out)
    seen, one = set(), []
    for h, s, _ in out:
        if h["name"] not in seen:
            seen.add(h["name"]); one.append((h, s))
    return one


def recall(names, truth, k):
    got = {positioning._norm(n) for n in names[:k]}
    return sum(positioning._norm(t) in got for t in truth) / len(truth)


def interval(vals):
    vals = np.array(vals, dtype=float)
    rng = np.random.default_rng(0)
    boots = [float(np.mean(rng.choice(vals, len(vals)))) for _ in range(2000)]
    return {"mean": round(float(vals.mean()), 3), "ci95": [round(float(v), 3) for v in np.percentile(boots, [2.5, 97.5])]}


def main():
    rows, tried = [], 0
    for h, supports in bills():
        if len(rows) == HEADLINERS or tried == MAX_TRIED:
            break
        tried += 1
        hq = b14.qloo_act(h)
        cand = similar(hq["id"], 100) if hq else None
        if not cand or len(cand) < 20:
            continue
        truth = [s["name"] for s in supports]
        alone = cached("alone", hq["id"], lambda: ask(ALONE, f"Headliner: {hq['name']}."))
        listing = "\n".join(f"{c['name']} (affinity {c['affinity']}, popularity {c['popularity']})" for c in cand)
        both = cached("with", hq["id"], lambda: ask(WITH, f"Headliner: {hq['name']}.\n\nTaste database candidates:\n{listing}"))
        arms = {"model_alone": alone, "qloo_alone": [c["name"] for c in cand[:K]], "model_with_qloo": both}
        qn = {positioning._norm(c["name"]) for c in cand}
        found = [t for t in truth if positioning._norm(t) in {positioning._norm(n) for n in both}]
        rows.append({"headliner": hq["name"], "supports": truth, "lists": arms,
                     **{f"{a}_at{k}": recall(v, truth, k) for a, v in arms.items() for k in (K, 10)},
                     "found_with": len(found), "found_with_from_qloo_list": sum(positioning._norm(t) in qn for t in found)})
        print(len(rows), "headliners", flush=True)
    arms = ("model_alone", "qloo_alone", "model_with_qloo")
    diff = lambda a, b, k: interval([r[f"{a}_at{k}"] - r[f"{b}_at{k}"] for r in rows])
    out = {"headliners": len(rows), "headliners_tried": tried, "real_supports": sum(len(r["supports"]) for r in rows),
           "recall_at_50": {a: interval([r[f"{a}_at{K}"] for r in rows]) for a in arms},
           "recall_at_10": {a: interval([r[f"{a}_at10"] for r in rows]) for a in arms},
           "headliners_with_a_support_found_at_50": {a: sum(r[f"{a}_at{K}"] > 0 for r in rows) for a in arms},
           "with_qloo_minus_alone_at_50": diff("model_with_qloo", "model_alone", K),
           "with_qloo_minus_alone_at_10": diff("model_with_qloo", "model_alone", 10),
           "qloo_alone_minus_model_alone_at_50": diff("qloo_alone", "model_alone", K),
           "supports_found_by_model_with_qloo": sum(r["found_with"] for r in rows),
           "of_which_were_in_qloo_list": sum(r["found_with_from_qloo_list"] for r in rows)}
    lo, hi = out["with_qloo_minus_alone_at_50"]["ci95"]
    out["outcome"] = "model with Qloo above model alone" if lo > 0 else "model with Qloo below model alone" if hi < 0 else "not shown"
    json.dump(out, open("backtest16_results.json", "w"), indent=1)
    json.dump(rows, open("test16_detail.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
