"""Test 8 as registered in PREREGISTRATION_8.md. Stages, resumable (state in test8_state.json, not committed
because briefs contain Qloo-derived text): cases -> briefs -> judge -> analyse.
python3 test8.py cases | briefs | judge | analyse"""
import json
import os
import random
import re
import sys
import urllib.error
import urllib.request

import numpy as np

import blind_test as bt
import engine
import llm
import positioning
import storefronts

STATE = "test8_state.json"
ORIGINAL = list(engine.CONCEPTS)[:14]
RUBRIC = ["specificity", "grounding", "distinctiveness", "actionability"]


def load():
    return json.load(open(STATE)) if os.path.exists(STATE) else {}


def save(s):
    json.dump(s, open(STATE, "w"), indent=1)


def test3_points():
    out = []
    for *_, pt in bt.CASES:
        lon, lat = map(float, re.findall(r"-?\d+\.\d+", pt))
        out.append((lat, lon))
    return out


def cases():
    s = load()
    rng = random.Random(8)
    far = [v for v in storefronts.vacant()
           if all(engine.metres(v["lat"], v["lon"], a, b) > 1000 for a, b in test3_points())]
    pool = rng.sample(far, len(far))
    picked, used_blocks = [], set()
    for v in pool:
        if len(picked) == 30:
            break
        cell = engine.g6(v["lat"], v["lon"])
        if cell in used_blocks:
            continue
        used_blocks.add(cell)
        concept = ORIGINAL[len(picked) % 14]
        picked.append({"id": len(picked) + 1, "concept": concept, "slug": engine.CONCEPTS[concept][1],
                       "address": f"{v['address']}, {v['borough']}", "lat": v["lat"], "lon": v["lon"],
                       "area": positioning.area_name(v["lat"], v["lon"], v["borough"], storefronts.short_name(v["neighbourhood"]))})
    s["cases"] = picked
    save(s)
    for c in picked:
        print(c["id"], c["concept"], "|", c["area"], "|", c["address"])


def city_background(c):
    near = engine.city().nearby(c["lat"], c["lon"], 500)[:40]
    return "\n".join(f"{x['name']} ({x['cuisine']})" for x in near)


def briefs():
    s = load()
    for c in s["cases"]:
        b = s.setdefault("briefs", {}).setdefault(str(c["id"]), {})
        if len(b) == 3:
            continue
        try:
            if "A" not in b:
                _, items = positioning.evidence(c["slug"], c["lat"], c["lon"])
                b["A"] = bt._brief(c["concept"], c["area"], positioning.evidence_text(items))[0]
            if "B" not in b:
                b["B"] = bt._brief(c["concept"], c["area"])[0]
            if "C" not in b:
                b["C"] = bt._brief(c["concept"], c["area"], city_background(c))[0]
        except RuntimeError as e:  # still leaks after three attempts: case dropped, as registered
            b["dropped"] = str(e)
        save(s)
        print(c["id"], sorted(b), flush=True)


JUDGE = ("You judge restaurant positioning briefs for an independent founder about to open in New York City. "
         "You will see one concept, one location and three briefs labelled 1, 2 and 3. Rank them from most to least "
         "helpful to this founder, and score each from 1 to 5 on: specificity (names real brands, artists, venues or "
         "aesthetics rather than generic claims), grounding (what it says about the people fits this particular "
         "place), distinctiveness (a different neighbourhood would get a different brief), actionability (a founder "
         "could act on it). Reply only with JSON: {\"ranking\": [best, middle, worst], \"scores\": {\"1\": "
         "{\"specificity\": n, \"grounding\": n, \"distinctiveness\": n, \"actionability\": n}, \"2\": {...}, \"3\": {...}}}")


def gemini(prompt):
    if os.environ.get("JUDGE_HOST") == "comet":  # same model (gemini-3.8-flash) on CometAPI when the free tier is out
        return gemini_comet(prompt)
    return gemini_google(prompt)


def gemini_comet(prompt):
    import time
    body = {"model": "gemini-3.8-flash", "response_format": {"type": "json_object"},
            "messages": [{"role": "system", "content": JUDGE}, {"role": "user", "content": prompt}]}
    req = urllib.request.Request("https://api.cometapi.com/v1/chat/completions", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json", "Authorization": "Bearer " + llm.ENV["COMET_API_KEY"]})
    for attempt in range(6):
        try:
            d = json.load(urllib.request.urlopen(req, timeout=300))
            txt = d["choices"][0]["message"]["content"].strip()
            return json.loads(txt[txt.find("{"):txt.rfind("}") + 1])
        except (urllib.error.HTTPError, TimeoutError, urllib.error.URLError, ConnectionError, OSError, ValueError, KeyError):
            if attempt == 5:
                raise
            time.sleep(10 * (attempt + 1))


def gemini_google(prompt):
    key = llm.ENV.get(os.environ.get("JUDGE_KEY", "GEMINI_API_KEY_3")) or llm.ENV["GEMINI_API_KEY"]
    body = {"systemInstruction": {"parts": [{"text": JUDGE}]}, "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"responseMimeType": "application/json"}}
    req = urllib.request.Request("https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent",
                                 data=json.dumps(body).encode(), headers={"Content-Type": "application/json", "x-goog-api-key": key})
    import time
    for attempt in range(6):  # Gemini answers 503 / 429 when busy: back off and retry
        try:
            d = json.load(urllib.request.urlopen(req, timeout=300))
            return json.loads(d["candidates"][0]["content"]["parts"][0]["text"])
        except urllib.error.HTTPError as e:
            if e.code not in (429, 500, 503) or attempt == 5:
                raise
            time.sleep(10 * (attempt + 1))
        except (TimeoutError, urllib.error.URLError, ConnectionError, OSError):
            if attempt == 5:
                raise
            time.sleep(5)


def judge():
    s = load()
    rng = random.Random(8)
    for c in s["cases"]:
        b = s["briefs"].get(str(c["id"]), {})
        order = ["A", "B", "C"]; rng.shuffle(order)
        if "dropped" in b or len(b) < 3:
            continue
        for k, o in (("j1", order), ("j2", order[::-1])):
            done = s.setdefault("judgements", {}).setdefault(str(c["id"]), {})
            if k in done:
                continue
            prompt = f"Concept: {c['concept']}. Location: {c['area']}.\n\n" + "\n\n".join(
                f"Brief {i + 1}:\n{b[arm]}" for i, arm in enumerate(o))
            r = gemini(prompt)
            done[k] = {"host": os.environ.get("JUDGE_HOST", "google"), "order": o, "ranking": [o[int(x) - 1] for x in r["ranking"]],
                       "scores": {o[int(i) - 1]: v for i, v in r["scores"].items()}}
            save(s)
        print(c["id"], "judged", flush=True)  # rankings are not printed: no peeking before the analysis


def above(rank, x, y):
    return rank.index(x) < rank.index(y)


def stat(s, x, y):
    vals = [np.mean([above(j["ranking"], x, y) for j in js.values()]) for js in s["judgements"].values() if len(js) == 2]
    rng = np.random.default_rng(0)
    boots = [np.mean(rng.choice(vals, len(vals))) for _ in range(2000)]
    return {"mean": round(float(np.mean(vals)), 3), "ci95": [round(float(v), 3) for v in np.percentile(boots, [2.5, 97.5])],
            "cases": len(vals)}


def analyse():
    s = load()
    ac = stat(s, "A", "C")
    band = "A beats C" if ac["ci95"][0] > 0.5 else "C beats A" if ac["ci95"][1] < 0.5 else "no difference shown"
    js = [j for v in s["judgements"].values() for j in v.values()]
    scores = {arm: {k: round(float(np.mean([j["scores"][arm][k] for j in js])), 2) for k in RUBRIC} for arm in "ABC"}
    disagree = float(np.mean([v["j1"]["ranking"][0] != v["j2"]["ranking"][0] for v in s["judgements"].values() if len(v) == 2]))
    out = {"primary_A_over_C": ac, "band": band, "A_over_B": stat(s, "A", "B"), "C_over_B": stat(s, "C", "B"),
           "rubric_means": scores, "top_choice_disagreement_between_orders": round(disagree, 3),
           "dropped_cases": [k for k, v in s["briefs"].items() if "dropped" in v]}
    print(json.dumps(out, indent=1))
    json.dump(out, open("test8_results.json", "w"), indent=1)


if __name__ == "__main__":
    {"cases": cases, "briefs": briefs, "judge": judge, "analyse": analyse}[sys.argv[1]]()
