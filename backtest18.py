"""Test 18 as registered in PREREGISTRATION_18.md: from five films a real person loved (MovieLens), does Qloo
tell their other loved films from their disliked ones, against average rating, popularity, genre and the language
model with and without Qloo's scores? State in test18_state.json (not committed).
python backtest18.py prepare   (MovieLens and Qloo only; computes no result)
python backtest18.py score     (language model arms, then the analysis; writes backtest18_results.json)"""
import csv
import io
import json
import os
import random
import re
import sys
import unicodedata
import zipfile

import backtest14 as b14
import llm
import positioning
import qloo

ZIP, STATE, PEOPLE = os.path.join("data", "movielens", "ml-latest-small.zip"), "test18_state.json", 50
ARTICLE = re.compile(r"^(.*), (The|A|An|Les|La|Le|Il|Das|Der|Die|El|L')$")
ALONE = ("A person loved the five films listed first. For each numbered candidate film, score from 0 to 100 how much "
         'this person would like it. Use the whole range. Reply as {"scores": {"1": n, "2": n, ...}} with every number.')
WITH = ALONE.replace("Use the whole range.", "Each candidate shows a taste-database affinity score between 0 and 1 for people "
                     "who like those five films; use it as you see fit. Use the whole range.")


def table(z, name):
    return list(csv.DictReader(io.TextIOWrapper(z.open(f"ml-latest-small/{name}.csv"), encoding="utf-8")))


def norm(s):
    return positioning._norm(unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode())


def title_year(t):
    m = re.match(r"^(.*)\((\d{4})\)\s*$", t.strip())
    if not m:
        return None, None
    name = re.sub(r"\s*\([^)]*\)", "", m.group(1)).strip()  # drop "(a.k.a. ...)" and other bracketed alternates
    a = ARTICLE.match(name)
    return (f"{a.group(2)} {a.group(1)}" if a else name), int(m.group(2))


def resolver():
    seen = {}

    def resolve(movie):
        if movie["movieId"] not in seen:
            name, year = title_year(movie["title"])
            hit = None
            for h in (qloo.get("/search", query=name, types="urn:entity:movie", take=5).get("results") or []) if name else []:
                y = (h.get("properties") or {}).get("release_year")
                if y and abs(int(y) - year) <= 1 and norm(h.get("name", "")) == norm(name):
                    hit = h["entity_id"]
                    break
            seen[movie["movieId"]] = hit
        return seen[movie["movieId"]]
    return resolve


def prepare():
    with zipfile.ZipFile(ZIP) as z:
        movies = {m["movieId"]: m for m in table(z, "movies")}
        ratings = table(z, "ratings")
    total, count, by = {}, {}, {}
    for r in ratings:
        v = float(r["rating"])
        total[r["movieId"]] = total.get(r["movieId"], 0) + v
        count[r["movieId"]] = count.get(r["movieId"], 0) + 1
        by.setdefault(r["userId"], []).append((r["movieId"], v))
    ok = sorted((u for u, rs in by.items() if sum(v >= 4.5 for _, v in rs) >= 13 and sum(v <= 2.5 for _, v in rs) >= 8), key=int)
    random.Random(18).shuffle(ok)
    resolve, people = resolver(), []
    for u in ok:
        if len(people) == PEOPLE:
            break
        rng = random.Random(f"18-{u}")
        loved, disliked = [m for m, v in by[u] if v >= 4.5], [m for m, v in by[u] if v <= 2.5]
        rng.shuffle(loved); rng.shuffle(disliked)
        own = dict(by[u])

        def usable(ms, n):
            out = []
            for m in ms:
                if len(out) == n:
                    break
                q = resolve(movies[m])
                if q and q not in [x["qloo"] for x in out]:
                    name, year = title_year(movies[m]["title"])
                    others = count[m] - 1
                    out.append({"movie": m, "qloo": q, "title": f"{name} ({year})", "genres": movies[m]["genres"].split("|"),
                                "avg_rating": (total[m] - own[m]) / others if others else 0.0, "ratings": others})
            return out
        l = usable(loved, 13)
        signal, pos, neg = l[:5], l[5:], usable(disliked, 8)
        if len(signal) < 5 or len(pos) < 6 or len(neg) < 6:
            continue
        cand = pos + neg
        d = qloo.get("/v2/insights", **{"filter.type": "urn:entity:movie", "signal.interests.entities": ",".join(x["qloo"] for x in signal),
                                        "filter.results.entities": ",".join(x["qloo"] for x in cand), "take": 50})
        aff = {x["entity_id"]: x.get("query", {}).get("affinity", 0.0) for x in qloo.results(d, "entities")}
        for x in cand:
            x["affinity"] = aff.get(x["qloo"])
        people.append({"user": u, "signal": signal, "pos": pos, "neg": neg})
        print(len(people), "people prepared", flush=True)
    json.dump({"eligible": len(ok), "people": people}, open(STATE, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print("eligible people:", len(ok), "| prepared:", len(people), "| qloo quota:", qloo.QUOTA["remaining"])


SMALL = "gemini-3.8-flash"
_GKEY = {"i": 0}  # which Gemini key is in use


def small_json(instructions, prompt, check):
    """One JSON reply from the small model on CometAPI (Amendment 1), with the same prompts as the large model."""
    import time
    import urllib.error
    import urllib.request
    google = os.environ.get("SMALL_HOST") == "google"  # the same model on Google's own API, as test8.gemini_google does
    kie = os.environ.get("SMALL_HOST") == "kie"        # the same model on Kie: the model is in the path, content is in parts
    if kie:
        part = lambda t: [{"type": "text", "text": t}]
        body = {"messages": [{"role": "system", "content": part(instructions + "\nReply with JSON only.")},
                             {"role": "user", "content": part(prompt)}], "stream": False, "reasoning_effort": "low"}
        req = urllib.request.Request("https://api.kie.ai/gemini-3-8-flash-openai/v1/chat/completions", data=json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json", "Authorization": "Bearer " + llm._env()["KIE_API_KEY"]})
    elif google:
        env = llm._env()
        body = {"systemInstruction": {"parts": [{"text": instructions + "\nReply with JSON only."}]}, "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"responseMimeType": "application/json"}}
        req = urllib.request.Request(f"https://generativelanguage.googleapis.com/v1beta/models/{SMALL}:generateContent",
                                     data=json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json", "x-goog-api-key": env.get("GEMINI_API_KEY_3") or env["GEMINI_API_KEY"]})
    else:
        body = {"model": SMALL, "response_format": {"type": "json_object"},
                "messages": [{"role": "system", "content": instructions + "\nReply with JSON only."}, {"role": "user", "content": prompt}]}
        req = urllib.request.Request("https://api.cometapi.com/v1/chat/completions", data=json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json", "Authorization": "Bearer " + llm._env()["COMET_API_KEY"]})
    # Google: every key in .env named GEMINI_API_KEY* is used in turn; a key that is out of quota or busy hands on
    # to the next. The team's keys are separate projects on one Google account.
    gkeys = [v for k, v in sorted(llm._env().items()) if k.startswith("GEMINI_API_KEY") and v] if google else []
    tries = max(6, 3 * len(gkeys))
    for attempt in range(tries):
        if google:
            req.add_header("x-goog-api-key", gkeys[_GKEY["i"] % len(gkeys)])
        try:
            d = json.load(urllib.request.urlopen(req, timeout=90 if google else 180))
            if kie and d.get("code") not in (None, 200):  # Kie reports errors inside an HTTP 200 reply
                if d["code"] in (401, 402):
                    raise llm.LLMError(f"provider error {d['code']}: {str(d.get('msg'))[:120]}")
                raise ConnectionError(f"Kie {d['code']}: {str(d.get('msg'))[:80]}")
            txt = d["candidates"][0]["content"]["parts"][0]["text"] if google else d["choices"][0]["message"]["content"]
            o = json.loads(txt[txt.find("{"):txt.rfind("}") + 1])
            check(o)
            return o
        except urllib.error.HTTPError as e:
            if (e.code in (401, 402, 403) and not google) or attempt == tries - 1:
                raise llm.LLMError(f"HTTP {e.code}: {e.read()[:200].decode(errors='replace')}") from None
            _GKEY["i"] += 1  # next key (Google); elsewhere this only counts
            time.sleep(4 if google else 15 * (attempt + 1))
        except (TimeoutError, urllib.error.URLError, ConnectionError, ValueError, KeyError):
            if attempt == tries - 1:
                raise
            _GKEY["i"] += 1
            time.sleep(5 if google else 5 * (attempt + 1))


def model(p, with_qloo, small=False):
    name = os.path.join(qloo.CACHE, f"llm18_{'small_' if small else ''}{'with' if with_qloo else 'alone'}_{p['user']}.json")
    if os.path.exists(name):
        return json.load(open(name))
    cand = p["pos"] + p["neg"]
    order = list(range(len(cand)))
    random.Random(f"18-{p['user']}").shuffle(order)
    show = lambda x: x["title"] + (f" (affinity {x['affinity']:.3f})" if with_qloo and x["affinity"] is not None else
                                   " (affinity: none)" if with_qloo else "")
    prompt = ("Loved:\n" + "\n".join(x["title"] for x in p["signal"]) + "\n\nCandidates:\n"
              + "\n".join(f"{n}. {show(cand[i])}" for n, i in enumerate(order, 1)))

    def check(o):
        if not isinstance(o.get("scores"), dict) or any(str(n) not in o["scores"] for n in range(1, len(order) + 1)):
            raise ValueError("give a score for every number")
    o = small_json(WITH if with_qloo else ALONE, prompt, check) if small else \
        llm.complete_json(WITH if with_qloo else ALONE, prompt, check=check, timeout=180)[0]
    out = {str(i): float(o["scores"][str(n)]) for n, i in enumerate(order, 1)}
    json.dump(out, open(name, "w"))
    return out


def score():
    s = json.load(open(STATE, encoding="utf-8"))
    rows = []
    for p in s["people"]:
        cand = p["pos"] + p["neg"]
        y = [True] * len(p["pos"]) + [False] * len(p["neg"])
        mine = {g for x in p["signal"] for g in x["genres"]}
        alone, both = model(p, False), model(p, True)
        s_alone, s_both = model(p, False, small=True), model(p, True, small=True)
        rows.append({"qloo": b14.auc(y, [-1.0 if x["affinity"] is None else x["affinity"] for x in cand]),
                     "small_alone": b14.auc(y, [s_alone[str(i)] for i in range(len(cand))]),
                     "small_with_qloo": b14.auc(y, [s_both[str(i)] for i in range(len(cand))]),
                     "avg_rating": b14.auc(y, [x["avg_rating"] for x in cand]),
                     "popularity": b14.auc(y, [x["ratings"] for x in cand]),
                     "genre": b14.auc(y, [sum(g in mine for g in x["genres"]) / len(x["genres"]) for x in cand]),
                     "model_alone": b14.auc(y, [alone[str(i)] for i in range(len(cand))]),
                     "model_with_qloo": b14.auc(y, [both[str(i)] for i in range(len(cand))]),
                     "candidates_scored_by_qloo": sum(x["affinity"] is not None for x in cand), "candidates": len(cand)})
        print(len(rows), "scored", flush=True)
    gain = lambda a, b: b14.interval([r[a] - r[b] for r in rows])
    out = {"people": len(rows), "eligible_people": s["eligible"],
           "auc": {k: b14.interval([r[k] for r in rows]) for k in ("qloo", "avg_rating", "popularity", "genre", "model_alone", "model_with_qloo",
                                                                    "small_alone", "small_with_qloo")},
           "small_with_qloo_minus_small_alone": gain("small_with_qloo", "small_alone"),
           "small_with_qloo_minus_large_alone": gain("small_with_qloo", "model_alone"),
           "qloo_minus_avg_rating": gain("qloo", "avg_rating"), "qloo_minus_popularity": gain("qloo", "popularity"),
           "qloo_minus_genre": gain("qloo", "genre"), "model_with_qloo_minus_model_alone": gain("model_with_qloo", "model_alone"),
           "model_alone_minus_qloo": gain("model_alone", "qloo"),
           "share_of_candidates_scored_by_qloo": round(sum(r["candidates_scored_by_qloo"] for r in rows) / sum(r["candidates"] for r in rows), 3),
           "per_person": rows}
    up = lambda k: out[k]["ci95"][0] > 0
    out["outcome"] = ("model with Qloo above model alone" if up("model_with_qloo_minus_model_alone")
                      else "Qloo's AUC not above 0.5" if out["auc"]["qloo"]["ci95"][0] <= 0.5
                      else "Qloo not above average rating" if not up("qloo_minus_avg_rating")
                      else "Qloo above average rating, popularity and genre; model with Qloo not above model alone"
                      if up("qloo_minus_popularity") and up("qloo_minus_genre") else "Qloo above average rating only")
    out["small_model_reading"] = [s for s, ok in (
        ("small model with Qloo above small model alone", up("small_with_qloo_minus_small_alone")),
        ("small model with Qloo not below the large model alone", out["small_with_qloo_minus_large_alone"]["ci95"][0] > -0.03)) if ok] \
        or ["Qloo's scores did not help a small model either"]
    json.dump(out, open("backtest18_results.json", "w"), indent=1)
    print(json.dumps({k: v for k, v in out.items() if k != "per_person"}, indent=1))


def small():
    """Only the small-model arms, saved for `score` to use. No result is computed here."""
    import time
    people = json.load(open(STATE, encoding="utf-8"))["people"]
    for n, p in enumerate(people, 1):
        for with_qloo in (False, True):
            fresh = not os.path.exists(os.path.join(qloo.CACHE, f"llm18_small_{'with' if with_qloo else 'alone'}_{p['user']}.json"))
            model(p, with_qloo, small=True)
            if fresh:
                time.sleep(4)
        print(n, "people done (small model)", flush=True)


def large():
    """Only the large-model arms, saved for `score` to use, retrying through provider errors. No result is computed."""
    import time
    people = json.load(open(STATE, encoding="utf-8"))["people"]
    todo = [(p, w) for p in people for w in (False, True)]
    done, fails = 0, 0
    for p, w in todo:
        while True:
            try:
                model(p, w)
                done += 1
                print(done, "of", len(todo), "large-model answers saved", flush=True)
                break
            except Exception as e:
                fails += 1
                msg = str(e)[:90]
                print("retry after:", msg, flush=True)
                if fails > 120 or any(x in msg for x in ("401", "402", "insufficient", "credit")):
                    raise
                time.sleep(20)


if __name__ == "__main__":
    {"prepare": prepare, "score": score, "small": small, "large": large}[sys.argv[1]]()
