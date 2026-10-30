"""Test 19 as registered in PREREGISTRATION_19.md: on the 115 real tours published by another entry
(github.com/bisale24-ops/advance, data/tours.json), does Qloo's top-100 list lift a small model and a large one at
naming the acts that really opened? State in test19_state.json (not committed).
python backtest19.py prepare   (Qloo only; computes no result)
python backtest19.py small | large   (model answers, saved; no result)
python backtest19.py score     (the analysis; writes backtest19_results.json)"""
import json
import os
import sys
import time

import backtest14 as b14
import backtest18 as b18
import llm
import qloo

TOURS, STATE, K, CUTS = os.path.join("data", "advance", "tours.json"), "test19_state.json", 100, (10, 25, 100)
ALONE = ("List 100 different artists who would be good opening acts for a {name} concert tour, best fit first. "
         'Reply as {{"acts": ["name", ...]}} with 100 names.')
WITH = ("List 100 different artists who would be good opening acts for a {name} concert tour, best fit first. "
        "Below is a list of artists whose fans overlap most with the headliner's, from a taste database, each with an "
        "affinity score and a popularity score from 0 to 1. Use this list as you see fit: pick from it, reorder it, "
        'and add artists of your own. Reply as {{"acts": ["name", ...]}} with 100 names.')


def norm(name):  # advance's rule: lower case, "&" as "and", single spaces
    return " ".join(name.casefold().replace("&", "and").split())


def find(name):
    h = (qloo.get("/search", query=name, types="urn:entity:artist", take=3).get("results") or [None])[0]
    return {"id": h["entity_id"], "name": h["name"]} if h and norm(h.get("name", "")) == norm(name) else None


def top100(eid):
    out = []
    for page in (1, 2):
        d = qloo.get("/v2/insights", **{"filter.type": "urn:entity:artist", "signal.interests.entities": eid, "take": 50, "page": page})
        if "error" in d:
            return None
        out += [{"id": x["entity_id"], "name": x["name"], "affinity": round(x.get("query", {}).get("affinity", 0), 3),
                 "popularity": round(x.get("popularity") or 0, 2)} for x in qloo.results(d, "entities") if x.get("entity_id") != eid]
    return out[:K]


def prepare():
    tours, rows, skipped = json.load(open(TOURS, encoding="utf-8")), [], 0
    for t in tours:
        h = find(t["headliner"])
        cand = top100(h["id"]) if h else None
        if not cand or len(cand) < K:
            skipped += 1
            continue
        known = [o for o in (find(s) for s in t["support"]) if o and o["id"] != h["id"]]
        rows.append({"tour": t["tour"], "headliner": h, "named": len(t["support"]), "openers": known, "qloo": cand})
        print(len(rows), "tours prepared", flush=True)
    json.dump({"tours_in_file": len(tours), "skipped": skipped, "tours": rows}, open(STATE, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print("tours:", len(rows), "| skipped:", skipped, "| openers named:", sum(r["named"] for r in rows),
          "| openers Qloo knows:", sum(len(r["openers"]) for r in rows), "| qloo quota:", qloo.QUOTA["remaining"])


def answer(r, with_qloo, small):
    name = os.path.join(qloo.CACHE, f"llm19_{'small' if small else 'large'}_{'with' if with_qloo else 'alone'}_{r['headliner']['id']}.json")
    if os.path.exists(name):
        return json.load(open(name, encoding="utf-8"))
    instructions = (WITH if with_qloo else ALONE).format(name=r["headliner"]["name"])
    prompt = f"Headliner: {r['headliner']['name']}."
    if with_qloo:
        prompt += "\n\nTaste database list:\n" + "\n".join(f"{c['name']} (affinity {c['affinity']}, popularity {c['popularity']})" for c in r["qloo"])

    def check(o):
        if not isinstance(o.get("acts"), list) or len(o["acts"]) < 40 or not all(isinstance(x, str) for x in o["acts"]):
            raise ValueError("reply with a list of 100 act names")
    o = b18.small_json(instructions, prompt, check) if small else llm.complete_json(instructions, prompt, check=check, timeout=240)[0]
    out = {"host": (os.environ.get("SMALL_HOST") or "comet") if small else llm.PROVIDER, "acts": o["acts"][:K]}
    json.dump(out, open(name, "w", encoding="utf-8"), ensure_ascii=False)
    return out


def collect(small, reverse=False):
    """One model's two arms for every tour, retrying through provider errors. No result is computed.
    With reverse, the tours are taken from the end, so a second worker can run beside the first."""
    tours = json.load(open(STATE, encoding="utf-8"))["tours"]
    tours = tours[::-1] if reverse else tours
    done = fails = 0
    for r in tours:
        for w in (False, True):
            while True:
                try:
                    answer(r, w, small)
                    done += 1
                    print(done, "of", 2 * len(tours), "answers saved", flush=True)
                    break
                except Exception as e:
                    fails += 1
                    msg = str(e)[:90]
                    print("retry after:", msg, flush=True)
                    if fails > 150 or any(x in msg for x in ("401", "402", "403", "insufficient", "exceeded your current quota")):
                        raise
                    time.sleep(20)


def score():
    s = json.load(open(STATE, encoding="utf-8"))
    arms = {"qloo_alone": lambda r: [c["name"] for c in r["qloo"]],
            "small_alone": lambda r: answer(r, False, True)["acts"], "small_with_qloo": lambda r: answer(r, True, True)["acts"],
            "large_alone": lambda r: answer(r, False, False)["acts"], "large_with_qloo": lambda r: answer(r, True, False)["acts"]}
    rows, hits = [], {a: {c: 0 for c in CUTS} for a in arms}
    for r in [t for t in s["tours"] if t["openers"]]:
        row = {}
        for a, fn in arms.items():
            names = [norm(n) for n in fn(r)]
            for c in CUTS:
                got = sum(norm(o["name"]) in names[:c] for o in r["openers"])
                hits[a][c] += got
                row[f"{a}_{c}"] = got / len(r["openers"])
        rows.append(row)
    gain = lambda a, b, c=100: b14.interval([r[f"{a}_{c}"] - r[f"{b}_{c}"] for r in rows])
    out = {"tours": len(rows), "tours_skipped": s["skipped"], "openers_counted": sum(len(t["openers"]) for t in s["tours"]),
           "hits": hits, "advance_published_hits": {"qloo": {"10": 26, "25": 48, "100": 109}, "their_model_alone": {"10": 21, "25": 32, "100": 37},
                                                     "openers_counted": 619},
           "recall_at_100": {a: b14.interval([r[f"{a}_100"] for r in rows]) for a in arms},
           "small_with_minus_alone": gain("small_with_qloo", "small_alone"), "large_with_minus_alone": gain("large_with_qloo", "large_alone"),
           "small_with_minus_large_alone": gain("small_with_qloo", "large_alone"), "qloo_alone_minus_small_alone": gain("qloo_alone", "small_alone"),
           "qloo_alone_minus_large_alone": gain("qloo_alone", "large_alone"),
           "at_25": {"small_with_minus_alone": gain("small_with_qloo", "small_alone", 25), "large_with_minus_alone": gain("large_with_qloo", "large_alone", 25)},
           "at_10": {"small_with_minus_alone": gain("small_with_qloo", "small_alone", 10), "large_with_minus_alone": gain("large_with_qloo", "large_alone", 10)}}
    up = lambda k: out[k]["ci95"][0] > 0
    out["readings"] = {"small model with Qloo above small model alone": up("small_with_minus_alone"),
                       "large model with Qloo above large model alone": up("large_with_minus_alone"),
                       "small model with Qloo about as good as large model alone": out["small_with_minus_large_alone"]["ci95"][0] > -0.03,
                       "replication: Qloo alone above small model alone": up("qloo_alone_minus_small_alone")}
    json.dump(out, open("backtest19_results.json", "w"), indent=1)
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    back = "reverse" in sys.argv[2:]
    {"prepare": prepare, "small": lambda: collect(True, back), "large": lambda: collect(False, back), "score": score}[sys.argv[1]]()
