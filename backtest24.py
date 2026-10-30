"""Test 24 as registered in PREREGISTRATION_24.md: do older acts that trended with young people show a younger
crowd in Qloo than their fan-overlap peers of the same era?
Aggregates go to backtest24_results.json; names and scores to test24_detail.json (not committed).
python backtest24.py"""
import hashlib
import json
import os
import random
import re
import time
import urllib.parse
import urllib.request

import numpy as np

import llm
import positioning
import qloo

SOURCES = [os.path.join("research_notes", "test24_sources", f"ud{y}.json") for y in (2022, 2023, 2024)]
ACTS, PEERS, CHECKED, SPAN, MIN_SETS = 60, 2, 15, 10, 20
PROBED = {positioning._norm(n) for n in (
    "Deftones", "Kate Bush", "Fleetwood Mac", "Sade", "Cocteau Twins", "Slowdive", "Mazzy Star", "The Smiths", "Radiohead", "Korn",
    "System of a Down", "Duster", "Hootie & the Blowfish", "Matchbox Twenty", "Counting Crows", "Live", "Third Eye Blind",
    "Goo Goo Dolls", "Collective Soul", "Candlebox", "Staind", "Puddle of Mudd", "Dire Straits", "Simply Red")}
ALONE = "You know popular music and who listens to it. For each act give a score from 0 to 100 for how much of its audience today is under 25."
WITH = ALONE + (" Beside each act are age scores from a taste database: positive means that age group is over-represented among "
                "its fans, negative under-represented. Use them as you see fit.")
FORMAT = ' Reply as {"scores": {"1": n, "2": n, "3": n}}.'


def listed():
    """First-named artist of every 'artist, dash, song' heading in the three source pages, in page order."""
    out = []
    for path in SOURCES:
        text = re.sub(r"!\[.*?\]\(.*?\)", "", json.load(open(path, encoding="utf-8"))["data"]["content"])
        for h in re.findall(r"^#{2,4}\s*(.+)$", text, re.M):
            m = re.match(r"\s*(.+?)\s*[–—‒-]\s*\S", h)
            if m:
                act = re.split(r"\s+(?:&|feat\.?|ft\.?|x)\s+|,", m.group(1), flags=re.I)[0].strip(" *_[]")
                if act:
                    out.append(act)
    return list(dict.fromkeys(out))


def mb(name):
    """(kind, start year) from MusicBrainz for an artist of this name among its first three results, or None."""
    url = "https://musicbrainz.org/ws/2/artist/?" + urllib.parse.urlencode({"query": f'artist:"{name}"', "fmt": "json", "limit": 3})
    path = os.path.join(qloo.CACHE, "mb_" + hashlib.md5(url.encode()).hexdigest() + ".json")
    if os.path.exists(path):
        d = json.load(open(path, encoding="utf-8"))
    else:
        d = None
        for attempt in range(6):
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "whitespace-hackathon-test/1.0"})
                d = json.load(urllib.request.urlopen(req, timeout=40))
                break
            except Exception:
                time.sleep(3 * (attempt + 1))
        if d is None:
            return None
        json.dump(d, open(path, "w", encoding="utf-8"))
        time.sleep(1.1)  # MusicBrainz asks for at most one call a second
    for a in d.get("artists", []):
        year = ((a.get("life-span") or {}).get("begin") or "")[:4]
        if positioning._norm(a.get("name", "")) == positioning._norm(name) and a.get("type") in ("Group", "Person") and year.isdigit():
            return a["type"], int(year)
    return None


def older(info):
    return bool(info) and ((info[0] == "Group" and info[1] <= 2000) or (info[0] == "Person" and info[1] <= 1980))


def artist(name):
    h = (qloo.get("/search", query=name, types="urn:entity:artist", take=3).get("results") or [None])[0]
    if h and positioning._norm(h.get("name", "")) == positioning._norm(name):
        return {"name": h["name"], "id": h["entity_id"], "popularity": h.get("popularity") or 0.0}
    return None


def similar(aid):
    d = qloo.get("/v2/insights", **{"filter.type": "urn:entity:artist", "signal.interests.entities": aid, "take": 50})
    return [{"name": x["name"], "id": x["entity_id"], "popularity": x.get("popularity") or 0.0} for x in qloo.results(d, "entities") if x["entity_id"] != aid]


def ages(ids):
    out = {}
    for i in range(0, len(ids), 8):
        d = qloo.get("/v2/insights", **{"filter.type": "urn:demographics", "signal.interests.entities": ",".join(ids[i:i + 8])})
        for x in d.get("results", {}).get("demographics", []):
            out[x["entity_id"]] = x.get("query", {}).get("age", {})
    return out


def model(tag, key, names, age):
    path = os.path.join(qloo.CACHE, f"llm24_{tag}_{key}.json")
    if os.path.exists(path):
        return json.load(open(path))
    line = lambda i, n: f"{i}. {n}" + (f" (age scores: {json.dumps(age[n])})" if tag == "with" else "")

    def check(o):
        if not isinstance(o.get("scores"), dict) or any(str(i) not in o["scores"] for i in (1, 2, 3)):
            raise ValueError("give a score for 1, 2 and 3")
    o, _ = llm.complete_json((WITH if tag == "with" else ALONE) + FORMAT, "\n".join(line(i, n) for i, n in enumerate(names, 1)), check=check, timeout=120)
    out = [float(o["scores"][str(i)]) for i in (1, 2, 3)]
    json.dump(out, open(path, "w"))
    return out


def interval(v):
    v = np.array(v, dtype=float)
    rng = np.random.default_rng(0)
    b = [float(np.mean(rng.choice(v, len(v)))) for _ in range(2000)]
    return {"mean": round(float(v.mean()), 3), "ci95": [round(float(x), 3) for x in np.percentile(b, [2.5, 97.5])], "n": len(v)}


def top(vals):
    """1 if the first (trended) value is strictly highest, a share if tied for highest, else 0."""
    best = max(vals)
    return (1.0 / sum(x == best for x in vals)) if vals[0] == best else 0.0


def summarise(sets):
    out = {"sets": len(sets),
           "under_25_score_trended_minus_peers": interval([s["young"][0] - np.mean(s["young"][1:]) for s in sets]),
           "trended_is_youngest_of_three": interval([top(s["young"]) for s in sets]),
           "popularity_trended_minus_peers": interval([s["pop"][0] - np.mean(s["pop"][1:]) for s in sets]),
           "trended_is_most_popular_of_three": interval([top(s["pop"]) for s in sets])}
    if all("alone" in s for s in sets):
        out["model_alone_picks_trended"] = interval([top(s["alone"]) for s in sets])
        out["model_with_qloo_picks_trended"] = interval([top(s["with"]) for s in sets])
        out["with_qloo_minus_alone"] = interval([top(s["with"]) - top(s["alone"]) for s in sets])
    return out


def main():
    names = listed()
    named = {positioning._norm(n) for n in names}
    trended, why = [], {"not_older_or_not_in_musicbrainz": 0, "not_in_qloo": 0, "fewer_than_two_peers": 0}
    pool = [n for n in names if older(mb(n))]
    why["not_older_or_not_in_musicbrainz"] = len(names) - len(pool)
    random.Random(24).shuffle(pool)
    for n in pool:
        if len(trended) == ACTS:
            break
        a = artist(n)
        if not a:
            why["not_in_qloo"] += 1; continue
        trended.append({**a, "era": mb(n)})
    print("listed", len(names), "| older", len(pool), "| in Qloo", len(trended), flush=True)
    sets = []
    for t in trended:
        peers = []
        for c in similar(t["id"])[:CHECKED]:
            if len(peers) == PEERS:
                break
            info = mb(c["name"])
            if positioning._norm(c["name"]) not in named and older(info) and info[0] == t["era"][0] and abs(info[1] - t["era"][1]) <= SPAN:
                peers.append({**c, "era": info})
        if len(peers) < PEERS:
            why["fewer_than_two_peers"] += 1; continue
        sets.append({"acts": [t] + peers})
        print(len(sets), "sets", flush=True)
    age = ages([a["id"] for s in sets for a in s["acts"]])
    sets = [s for s in sets if all(a["id"] in age and age[a["id"]].get("24_and_younger") is not None for a in s["acts"])]
    out = {"acts_listed": len(names), "older_acts": len(pool), "trended_in_qloo": len(trended), "dropped": why, "sets": len(sets)}
    if len(sets) < MIN_SETS:
        out["reading"] = "too few to say"
    else:
        for s in sets:
            s["young"] = [age[a["id"]]["24_and_younger"] for a in s["acts"]]
            s["pop"] = [a["popularity"] for a in s["acts"]]
            order = [0, 1, 2]
            random.Random(f"24-{s['acts'][0]['id']}").shuffle(order)
            shown = [s["acts"][i]["name"] for i in order]
            by_name = {a["name"]: age[a["id"]] for a in s["acts"]}
            for tag in ("alone", "with"):
                got = model(tag, s["acts"][0]["id"], shown, by_name)
                s[tag] = [got[order.index(i)] for i in (0, 1, 2)]
            print("scored", s["acts"][0]["name"].encode("ascii", "replace").decode(), flush=True)
        probed = lambda s: any(positioning._norm(a["name"]) in PROBED for a in s["acts"])
        out["all_sets"] = summarise(sets)
        out["sets_without_probe_acts"] = summarise([s for s in sets if not probed(s)])
        m = out["all_sets"]
        out["reading_1"] = ("older acts that trended with young people show a younger crowd in Qloo than their closest peers of the same era"
                            if m["under_25_score_trended_minus_peers"]["ci95"][0] > 0 else "not shown")
        out["reading_2_also_more_famous"] = m["popularity_trended_minus_peers"]["ci95"][0] > 0
        g = m["with_qloo_minus_alone"]["ci95"]
        out["reading_3_model_with_qloo_against_alone"] = "above" if g[0] > 0 else "below" if g[1] < 0 else "no different"
    json.dump(out, open("backtest24_results.json", "w"), indent=1)
    json.dump([{"acts": [(a["name"], a["era"], round(a["popularity"], 2)) for a in s["acts"]], **{k: s.get(k) for k in ("young", "alone", "with")}} for s in sets],
              open("test24_detail.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
