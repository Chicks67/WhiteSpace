"""Test 25 as registered in PREREGISTRATION_25.md: Qloo on its home ground.
python backtest25.py a   (small acts against ListenBrainz co-listening)
python backtest25.py b   (restaurants opened after 2026-04-01)
python backtest25.py c   (steadiness of model scores and Qloo scores)
Each part writes its own section of backtest25_results.json; names go to test25_detail.json (not committed)."""
import collections
import hashlib
import json
import os
import random
import sys
import time
import urllib.parse
import urllib.request

import numpy as np

import backtest14 as b14
import backtest15 as b15
import backtest24 as b24
import llm
import positioning
import qloo
import scene

STARTERS = ["Japanese Breakfast", "Turnstile", "Khruangbin", "Alvvays", "Black Country New Road", "Snail Mail", "Mdou Moctar",
            "Floating Points", "Wednesday", "Tyler Childers", "Arooj Aftab", "Jockstrap"]
LB_ALGO = "session_based_days_7500_session_300_contribution_5_threshold_10_limit_100_filter_True_skip_30"
UA = {"User-Agent": "whitespace-hackathon-test/1.0"}
A_ALONE = ("You know music and who listens to it. For one artist you get a numbered list of other artists. Score each from 0 "
           "to 100 for how likely a fan of that artist is to also listen to it. Use the whole range.")
A_WITH = A_ALONE + " Beside each artist is its fan-overlap score with the first artist from a taste database (0 to 1, or 'none'); use it as you see fit."
SCORES = ' Reply as {"scores": {"1": n, "2": n, ...}} with every number in the list.'


def fetch(url, tag, pause=1.1):
    path = os.path.join(qloo.CACHE, f"{tag}_" + hashlib.md5(url.encode()).hexdigest() + ".json")
    if os.path.exists(path):
        return json.load(open(path, encoding="utf-8"))
    for attempt in range(6):
        try:
            d = json.load(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60))
            json.dump(d, open(path, "w", encoding="utf-8"))
            time.sleep(pause)
            return d
        except Exception:
            time.sleep(4 * (attempt + 1))
    return None


def mbid(name):
    url = "https://musicbrainz.org/ws/2/artist/?" + urllib.parse.urlencode({"query": f'artist:"{name}"', "fmt": "json", "limit": 1})
    a = ((fetch(url, "mb") or {}).get("artists") or [None])[0]
    return a["id"] if a and positioning._norm(a.get("name", "")) == positioning._norm(name) else None


def lb(mid):
    d = fetch(f"https://labs.api.listenbrainz.org/similar-artists/json?artist_mbids={mid}&algorithm={LB_ALGO}", "lb", pause=0.5)
    return [x for x in (d or []) if isinstance(x, dict) and x.get("artist_mbid") and x.get("name")]


def spearman(a, b):
    """Spearman correlation with tied values given their average rank (no scipy: a Windows policy blocked one of its files)."""
    def rank(x):
        x = np.asarray(x, dtype=float)
        order = np.argsort(x, kind="mergesort")
        r = np.empty(len(x))
        r[order] = np.arange(len(x))
        for v in np.unique(x):
            r[x == v] = r[x == v].mean()
        return r
    return float(np.corrcoef(rank(a), rank(b))[0, 1])


def interval(v):
    v = np.array([x for x in v if x is not None], dtype=float)
    rng = np.random.default_rng(0)
    b = [float(np.mean(rng.choice(v, len(v)))) for _ in range(2000)]
    return {"mean": round(float(v.mean()), 3), "ci95": [round(float(x), 3) for x in np.percentile(b, [2.5, 97.5])], "n": len(v)}


def three(g):
    return "above" if g["ci95"][0] > 0 else "below" if g["ci95"][1] < 0 else "no different"


def save(part, out, detail):
    """Each part has its own files, so the three parts can run at the same time."""
    json.dump(out, open(f"backtest25_{part}_results.json", "w"), indent=1)
    json.dump(detail, open(f"test25_{part}_detail.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print(json.dumps(out, indent=1))


def scored(tag, key, instr, head, names, extra=None, sep="\n\n"):
    path = os.path.join(qloo.CACHE, f"llm25{tag}_{key}.json")
    if os.path.exists(path):
        return json.load(open(path))
    listing = "\n".join(f"{i}. {n}" + (f" ({extra[i - 1]})" if extra else "") for i, n in enumerate(names, 1))

    def check(o):
        if not isinstance(o.get("scores"), dict) or any(str(i) not in o["scores"] for i in range(1, len(names) + 1)):
            raise ValueError("give a score for every number in the list")
    o, _ = llm.complete_json(instr + SCORES, f"{head}{sep}{listing}", check=check, timeout=180)
    out = [float(o["scores"][str(i)]) for i in range(1, len(names) + 1)]
    json.dump(out, open(path, "w"))
    return out


def part_a():
    cands = []
    for s in STARTERS:
        m = mbid(s)
        cands += [(x["name"], x["artist_mbid"]) for x in lb(m)] if m else []
    cands = list(dict.fromkeys(cands))
    starters = {positioning._norm(s) for s in STARTERS}
    cands = [c for c in cands if positioning._norm(c[0]) not in starters]
    random.Random(25).shuffle(cands)
    seeds, tried, why = [], 0, {"not_in_qloo": 0, "popularity_0.5_or_more": 0, "no_similar_in_qloo": 0, "fewer_than_3_truth": 0}
    for name, mid in cands:
        if len(seeds) == 30 or tried == 300:
            break
        tried += 1
        a = b24.artist(name)
        if not a:
            why["not_in_qloo"] += 1; continue
        if a["popularity"] >= 0.5:
            why["popularity_0.5_or_more"] += 1; continue
        if not b15.similar_ok(a["id"]):
            why["no_similar_in_qloo"] += 1; continue
        truth = []
        for x in lb(mid)[:12]:
            if len(truth) == 8:
                break
            t = b24.artist(x["name"])
            if t and t["id"] != a["id"]:
                truth.append(t)
        if len(truth) < 3:
            why["fewer_than_3_truth"] += 1; continue
        seeds.append({"seed": a, "truth": truth})
        print(len(seeds), "seeds of", tried, "tried", flush=True)
    out = {"candidates": len(cands), "tried": tried, "seeds": len(seeds), "dropped": why}
    if len(seeds) < 15:
        out["reading"] = "too few small acts to say"
        return save("a", out, [])
    pool = {t["id"]: t for s in seeds for t in s["truth"]}
    rows, detail = [], []
    for s in seeds:
        a, own = s["seed"], {t["id"] for t in s["truth"]}
        rng = random.Random(f"25-{a['id']}")
        others = [i for i in sorted(pool) if i not in own and i != a["id"]]
        short = sorted(own) + rng.sample(others, min(30, len(others)))
        rng.shuffle(short)
        aff = b14.affinities(a["id"], short)
        y = [i in own for i in short]
        names = [pool[i]["name"] for i in short]
        alone = scored("a_alone", a["id"], A_ALONE, f"Artist: {a['name']}.", names)
        both = scored("a_with", a["id"], A_WITH, f"Artist: {a['name']}.", names, [f"fan overlap {aff[i]:.2f}" if i in aff else "fan overlap none" for i in short])
        r = {"qloo": b14.auc(y, [aff.get(i, -1.0) for i in short]), "fame": b14.auc(y, [pool[i]["popularity"] for i in short]),
             "model_alone": b14.auc(y, alone), "model_with_qloo": b14.auc(y, both), "seed_popularity": round(a["popularity"], 2)}
        rows.append(r)
        detail.append({"seed": a["name"], "truth": [t["name"] for t in s["truth"]], **r})
    g = lambda x, z: interval([r[x] - r[z] for r in rows])
    out.update({"auc": {k: interval([r[k] for r in rows]) for k in ("qloo", "fame", "model_alone", "model_with_qloo")},
                "qloo_minus_fame": g("qloo", "fame"), "with_qloo_minus_alone": g("model_with_qloo", "model_alone"),
                "qloo_minus_model_alone": g("qloo", "model_alone"),
                "seed_popularity_quartiles": [round(float(v), 2) for v in np.percentile([r["seed_popularity"] for r in rows], [25, 50, 75])]})
    out["reading_1"] = ("Qloo knows the neighbours of small acts, beyond fame"
                        if out["auc"]["qloo"]["ci95"][0] > 0.5 and out["qloo_minus_fame"]["ci95"][0] > 0 else "not shown")
    out["reading_2_model_with_qloo_against_alone"] = three(out["with_qloo_minus_alone"])
    out["reading_3_qloo_against_model_alone"] = three(out["qloo_minus_model_alone"])
    save("a", out, detail)


def part_b():
    data = json.load(open(os.path.join("data", "dohmh_restaurants.json"), encoding="utf-8"))
    count = collections.Counter(positioning._norm(r.get("dba") or "") for r in data)
    bad = {"other", "not listed/not applicable", ""}
    pool = [r for r in data if (r.get("opened") or "") >= "2026-04-01" and count[positioning._norm(r.get("dba") or "")] < 3
            and (r.get("cuisine_description") or "").strip().lower() not in bad]
    pool.sort(key=lambda r: r["camis"])
    random.Random(25).shuffle(pool)
    sample = pool[:120]
    cuisines = sorted({r["cuisine_description"] for r in sample})
    where = "camis in (" + ",".join(f"'{r['camis']}'" for r in sample) + ")"
    url = "https://data.cityofnewyork.us/resource/43nn-pn8j.json?" + urllib.parse.urlencode(
        {"$select": "camis,building,street", "$where": where, "$group": "camis,building,street", "$limit": 1000})
    addr = {x["camis"]: f"{x.get('building', '')} {x.get('street', '')}".strip() for x in fetch(url, "nycod", pause=0.2) or []}
    instr = ("You are asked about one restaurant in New York City. Say which cuisine it serves, choosing exactly one name "
             "from this list: " + "; ".join(cuisines) + '. Reply as {"cuisine": "name from the list"}.')
    rows = []
    for r in sample:
        try:
            lat, lon = float(r["latitude"]), float(r["longitude"])
        except (TypeError, ValueError, KeyError):
            lat = lon = None
        h = scene.resolve_at(r["dba"], lat, lon) if lat and lon and abs(lat) > 1 else None
        p = (h or {}).get("properties", {})
        desc = (p.get("description") or p.get("short_description") or "").strip()
        kw = [k.get("name") for k in (p.get("keywords") or []) if k.get("name")][:8]
        tags = [t.get("name") for t in (h or {}).get("tags") or [] if t.get("name")][:8]
        record = (f"Description: {desc}\nKeywords: {', '.join(kw)}\nTags: {', '.join(tags)}\nPrice level: {p.get('price_level')}"
                  if h else "No record was found for this restaurant.")
        base = f"Restaurant: {r['dba']}\nAddress: {addr.get(r['camis'], '')}, {r['boro']}".replace("Address: , ", "Address: ")

        def ask(tag, prompt):
            path = os.path.join(qloo.CACHE, f"llm25b_{tag}_{r['camis']}.json")
            if os.path.exists(path):
                return json.load(open(path))["cuisine"]

            def check(o):
                if o.get("cuisine") not in cuisines:
                    raise ValueError("choose exactly one name from the list")
            o, _ = llm.complete_json(instr, prompt, check=check, timeout=120)
            json.dump(o, open(path, "w"))
            return o["cuisine"]
        alone = ask("alone", base)
        both = ask("with", base + "\n\nPlace-data record:\n" + record)
        rows.append({"name": r["dba"], "truth": r["cuisine_description"], "found": bool(h), "detail": bool(desc or kw),
                     "alone": alone, "with": both, "ok_alone": alone == r["cuisine_description"], "ok_with": both == r["cuisine_description"]})
        print(len(rows), "restaurants", flush=True)
    f = [x for x in rows if x["found"]]
    out = {"sample": len(rows), "found_in_qloo": len(f), "found_with_description_or_keywords": sum(x["detail"] for x in rows),
           "correct_alone": interval([x["ok_alone"] for x in rows]), "correct_with_qloo": interval([x["ok_with"] for x in rows]),
           "with_minus_alone": interval([float(x["ok_with"]) - float(x["ok_alone"]) for x in rows]),
           "found_only": {"correct_alone": interval([x["ok_alone"] for x in f]) if f else None,
                          "correct_with_qloo": interval([x["ok_with"] for x in f]) if f else None}}
    out["reading"] = ("with Qloo, the agent knew more about places opened after the model was trained"
                      if out["with_minus_alone"]["ci95"][0] > 0 else "not shown")
    save("b", out, rows)


def part_c():
    rows, tried = [], 0
    for h, supports in b15.bills():
        if len(rows) == b15.HEADLINERS or tried == b15.MAX_TRIED:
            break
        tried += 1
        hq = b14.qloo_act(h)
        if not hq or not b15.similar_ok(hq["id"]):
            continue
        kept = [a for a in (b14.qloo_act(s) for s in supports) if a and a["id"] != hq["id"]]
        if kept:
            rows.append({"headliner": hq, "supports": kept})
    pool = {a["id"]: a for r in rows for a in r["supports"]}
    ids = sorted(pool)
    out_rows = []
    for r in rows[:20]:
        h, own = r["headliner"], {a["id"] for a in r["supports"]}
        cand = [i for i in ids if i != h["id"]]
        rng = random.Random(f"15-{h['id']}")
        short = sorted(own) + rng.sample([i for i in cand if i not in own], min(b15.NEGATIVES, len(cand) - len(own)))
        rng.shuffle(short)
        first = json.load(open(os.path.join(qloo.CACHE, f"llm15_{h['id']}.json")))
        again = scored("c", h["id"], b15.LLM_INSTRUCTIONS.split(' Reply as')[0], f"Headliner: {h['name']}.\n\nActs:",
                       [pool[x]["name"] for x in short], sep="\n")
        a1, a2 = [first[x] for x in short], again
        y = [i in own for i in short]
        out_rows.append({"spearman": spearman(a1, a2), "auc_first": b14.auc(y, a1), "auc_again": b14.auc(y, a2)})
    same = []
    for r in rows[:5]:
        h = r["headliner"]
        ids5 = ",".join(sorted(pool)[:40])
        url = qloo.BASE + "/v2/insights?" + urllib.parse.urlencode({"filter.type": "urn:entity:artist", "signal.interests.entities": h["id"],
                                                                   "filter.results.entities": ids5, "take": 50})
        got = []
        for _ in range(2):
            d = json.load(urllib.request.urlopen(urllib.request.Request(url, headers={"X-Api-Key": qloo._key()}), timeout=90))
            got.append({x["entity_id"]: x.get("query", {}).get("affinity") for x in d.get("results", {}).get("entities", [])})
        same.append(got[0] == got[1])
    out = {"headliners": len(out_rows), "model_run_to_run_spearman": interval([x["spearman"] for x in out_rows]),
           "model_auc_change_abs": interval([abs(x["auc_first"] - x["auc_again"]) for x in out_rows]),
           "model_auc_first": interval([x["auc_first"] for x in out_rows]), "model_auc_again": interval([x["auc_again"] for x in out_rows]),
           "qloo_identical_on_repeat": f"{sum(same)} of {len(same)}"}
    save("c", out, out_rows)


if __name__ == "__main__":
    {"a": part_a, "b": part_b, "c": part_c}[sys.argv[1]]()
