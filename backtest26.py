"""Test 26 as registered in PREREGISTRATION_26.md: do MLB theme nights whose theme suits the city's taste draw more
people than the team's usual crowd for that day?
Aggregates go to backtest26_results.json; games and names to test26_detail.json (not committed).
python backtest26.py"""
import concurrent.futures
import hashlib
import json
import math
import os
import urllib.request

import numpy as np

import backtest18 as b18
import llm
import positioning
import qloo

API = "https://statsapi.mlb.com/api/v1"
TYPES = ["movie", "tv_show", "artist", "videogame", "book", "brand"]
EXTRACT = ("You read ballpark promotion names. For each one: if it is themed on a named film, TV show, artist or band, video "
           "game, book, character franchise or brand, give that name as it is usually written; otherwise null. Heritage, "
           "faith, team, school, charity, holiday, food deal, ticket deal and sport themes are null. "
           'Reply as {"names": {"1": "name or null", "2": ...}} with every number.')
PULL = ("For each line you get a named film, show, artist, game, book, franchise or brand and a US city. Score how strong "
        "the fan following for it is in that city compared with other US cities, from 0 to 100. Use the whole range.")
PULL_WITH = PULL + (" Each line also shows a taste database's affinity of that city for it (0 to 1, or 'none'); use it as "
                    "you see fit.")
SCORES = ' Reply as {"scores": {"1": n, "2": n, ...}} with every number.'


def ask(instructions, prompt, check):
    """Amendment 2: GPT-6 Astra through Kie."""
    return llm.complete_json(instructions, prompt, check=check, timeout=180)[0]


def get(url):
    path = os.path.join(qloo.CACHE, "mlb_" + hashlib.md5(url.encode()).hexdigest() + ".json")
    if os.path.exists(path):
        return json.load(open(path, encoding="utf-8"))
    for attempt in range(5):
        try:
            d = json.load(urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "whitespace-test/1.0"}), timeout=60))
            json.dump(d, open(path, "w", encoding="utf-8"))
            return d
        except Exception:
            if attempt == 4:
                raise


def games():
    teams = {t["id"]: t for t in get(f"{API}/teams?sportId=1&season=2026")["teams"]}
    out = []
    for tid, t in sorted(teams.items()):
        for m in range(3, 11):
            d = get(f"{API}/schedule?sportId=1&teamId={tid}&season=2026&gameType=R&startDate=2026-{m:02d}-01&endDate=2026-{m:02d}-{__import__('calendar').monthrange(2026, m)[1]}"
                    f"&hydrate=game(promotions)")
            for x in d.get("dates", []):
                for g in x["games"]:
                    if g["teams"]["home"]["team"]["id"] == tid and g["status"].get("abstractGameState") == "Final":
                        out.append({"pk": g["gamePk"], "team": tid, "city": t.get("locationName") or t.get("franchiseName"),
                                    "date": g["officialDate"], "promos": [p.get("name") for p in g.get("promotions") or [] if p.get("name")]})
    seen, one = set(), []
    for g in out:
        if g["pk"] not in seen:
            seen.add(g["pk"]); one.append(g)

    def att(g):
        for i in get(f"{API}/game/{g['pk']}/boxscore").get("info", []):
            if i.get("label") == "Att":
                return int("".join(ch for ch in i.get("value", "") if ch.isdigit()) or 0) or None
        return None
    with concurrent.futures.ThreadPoolExecutor(8) as ex:
        for g, a in zip(one, ex.map(att, one)):
            g["attendance"] = a
    return [g for g in one if g["attendance"]]


def themes(names):
    path = os.path.join(qloo.CACHE, "llm26k_extract.json")
    done = json.load(open(path, encoding="utf-8")) if os.path.exists(path) else {}
    todo = [n for n in names if n not in done]
    for i in range(0, len(todo), 50):
        batch = todo[i:i + 50]

        def check(o):
            if not isinstance(o.get("names"), dict) or any(str(k) not in o["names"] for k in range(1, len(batch) + 1)):
                raise ValueError("answer for every number")
        o = ask(EXTRACT, "\n".join(f"{k}. {n}" for k, n in enumerate(batch, 1)), check)
        for k, n in enumerate(batch, 1):
            v = o["names"][str(k)]
            done[n] = v if isinstance(v, str) and v.strip() and v.strip().lower() != "null" else None
        json.dump(done, open(path, "w", encoding="utf-8"), ensure_ascii=False)
    return done


def resolve(name):
    for t in TYPES:
        for h in qloo.get("/search", query=name, types="urn:entity:" + t, take=3).get("results") or []:
            if positioning._norm(h.get("name", "")) == positioning._norm(name):
                return {"id": h["entity_id"], "name": h["name"], "type": t, "popularity": h.get("popularity") or 0.0}
    return None


def affinity(city, ents):
    out = {}
    for t in {e["type"] for e in ents}:
        ids = [e["id"] for e in ents if e["type"] == t]
        for i in range(0, len(ids), 40):
            d = qloo.get("/v2/insights", **{"filter.type": "urn:entity:" + t, "signal.location.query": city,
                                            "filter.results.entities": ",".join(ids[i:i + 40]), "take": 50})
            out.update({x["entity_id"]: x.get("query", {}).get("affinity") for x in qloo.results(d, "entities")})
    return out


def pull(tag, rows):
    path = os.path.join(qloo.CACHE, f"llm26k_{tag}.json")
    done = json.load(open(path, encoding="utf-8")) if os.path.exists(path) else {}
    key = lambda r: f"{r['theme']['name']}|{r['city']}"
    todo = list(dict.fromkeys(key(r) for r in rows if key(r) not in done))
    aff = {key(r): r["qloo"] for r in rows}
    for i in range(0, len(todo), 25):
        batch = todo[i:i + 25]
        line = lambda k, x: f"{k}. {x.split('|')[0]}, {x.split('|')[1]}" + (
            f" (affinity {aff[x]:.2f})" if tag == "with" and aff[x] is not None else " (affinity none)" if tag == "with" else "")

        def check(o):
            if not isinstance(o.get("scores"), dict) or any(str(k) not in o["scores"] for k in range(1, len(batch) + 1)):
                raise ValueError("score every number")
        o = ask((PULL_WITH if tag == "with" else PULL) + SCORES, "\n".join(line(k, x) for k, x in enumerate(batch, 1)), check)
        for k, x in enumerate(batch, 1):
            done[x] = float(o["scores"][str(k)])
        json.dump(done, open(path, "w", encoding="utf-8"), ensure_ascii=False)
    return [done[key(r)] for r in rows]


def spearman(a, b):
    def rank(x):
        x = np.asarray(x, dtype=float)
        r = np.empty(len(x)); r[np.argsort(x, kind="mergesort")] = np.arange(len(x))
        for v in np.unique(x):
            r[x == v] = r[x == v].mean()
        return r
    return float(np.corrcoef(rank(a), rank(b))[0, 1])


def boot(rows, f):
    rng = np.random.default_rng(0)
    point, bs = f(rows), []
    for _ in range(2000):
        s = [rows[i] for i in rng.integers(0, len(rows), len(rows))]
        v = f(s)
        if not math.isnan(v):
            bs.append(v)
    return {"value": round(point, 3), "ci95": [round(float(x), 3) for x in np.percentile(bs, [2.5, 97.5])], "n": len(rows)}


def main():
    gs = games()
    print("final home games with attendance:", len(gs), flush=True)
    day = lambda d: {4: "fri", 5: "sat", 6: "sun"}.get(__import__("datetime").date.fromisoformat(d).weekday(), "mon-thu")
    for g in gs:
        g["day"] = day(g["date"])
    top = {}
    for g in gs:
        top[g["team"]] = max(top.get(g["team"], 0), g["attendance"])
    names = sorted({p for g in gs for p in g["promos"]})
    ex = themes(names)
    cache, rows = {}, []
    for g in gs:
        for p in g["promos"]:
            n = ex.get(p)
            if not n:
                continue
            if n not in cache:
                cache[n] = resolve(n)
            if cache[n]:
                peers = [math.log(x["attendance"]) for x in gs if x["team"] == g["team"] and x["day"] == g["day"] and x["pk"] != g["pk"]]
                rows.append({"pk": g["pk"], "team": g["team"], "city": g["city"], "date": g["date"], "promo": p, "theme": cache[n],
                             "outcome": math.log(g["attendance"]) - float(np.mean(peers)), "near_sellout": g["attendance"] >= 0.98 * top[g["team"]]})
                break  # one theme per game: the first themed promotion listed
    print("theme nights:", len(rows), flush=True)
    out = {"games": len(gs), "promotion_names": len(names), "themed_names": sum(1 for v in ex.values() if v), "theme_nights": len(rows)}
    if len(rows) < 40:
        out["reading"] = "too few theme nights to say"
    else:
        for city in sorted({r["city"] for r in rows}):
            aff = affinity(city, [r["theme"] for r in rows if r["city"] == city])
            for r in rows:
                if r["city"] == city:
                    r["qloo"] = aff.get(r["theme"]["id"])
        alone, both = pull("alone", rows), pull("with", rows)
        for r, a, b in zip(rows, alone, both):
            r["model_alone"], r["model_with"], r["fame"] = a, b, r["theme"]["popularity"]

        def block(rs):
            q = lambda s: spearman([r["qloo"] if r["qloo"] is not None else -1 for r in s], [r["outcome"] for r in s])
            c = lambda k: (lambda s: spearman([r[k] for r in s], [r["outcome"] for r in s]))
            return {"qloo": boot(rs, q), "fame": boot(rs, c("fame")), "model_alone": boot(rs, c("model_alone")),
                    "model_with_qloo": boot(rs, c("model_with")),
                    "qloo_minus_fame": boot(rs, lambda s: q(s) - c("fame")(s)),
                    "with_minus_alone": boot(rs, lambda s: c("model_with")(s) - c("model_alone")(s)),
                    "qloo_minus_model_alone": boot(rs, lambda s: q(s) - c("model_alone")(s)),
                    "share_with_qloo_affinity": round(sum(r["qloo"] is not None for r in rs) / len(rs), 3),
                    "mean_outcome": round(float(np.mean([r["outcome"] for r in rs])), 3)}
        out["all_theme_nights"] = block(rows)
        out["without_near_sellouts"] = block([r for r in rows if not r["near_sellout"]])
        m = out["all_theme_nights"]
        three = lambda g: "above" if g["ci95"][0] > 0 else "below" if g["ci95"][1] < 0 else "no different"
        out["reading_1"] = ("theme nights that suit the city's taste in Qloo drew more people than the team's usual crowd for that day"
                            if m["qloo"]["ci95"][0] > 0 else "not shown")
        out["reading_2_beyond_fame"] = m["qloo_minus_fame"]["ci95"][0] > 0
        out["reading_3_model_with_qloo_against_alone"] = three(m["with_minus_alone"])
        out["reading_3_qloo_against_model_alone"] = three(m["qloo_minus_model_alone"])
    json.dump(out, open("backtest26_results.json", "w"), indent=1)
    json.dump(rows, open("test26_detail.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
