"""Test 20 as registered in PREREGISTRATION_20.md: asked when a real restaurant closes on Friday, is a model right
more often with Qloo's record than alone? Reference: the Google Maps lookups made for Test 12.
python test20.py collect   (model answers, saved; no result)
python test20.py score     (writes test20_results.json)"""
import csv
import json
import os
import sys
import time

import numpy as np

import backtest18 as b18
import llm
import qloo
import test12 as t12

ALONE = ("You are asked about one restaurant in New York City. Answer with the time it closes on Friday, in 24-hour "
         'HH:MM. If you do not know, say so: do not guess. Reply as {"closes": "HH:MM"} or {"closes": null}.')
WITH = ALONE.replace("If you do not know", "A place-data record is given; use it if it helps. If you do not know")
ARMS = [("large_alone", False, False), ("large_with_qloo", False, True), ("small_alone", True, False), ("small_with_qloo", True, True)]


def places():
    key = json.load(open(t12.KEY, encoding="utf-8"))
    out = []
    for r in csv.DictReader(open(t12.SHEET, encoding="utf-8-sig")):
        if r["google_friday_close"].strip() and not r[t12.COLS[6]].strip().lower().startswith("y"):
            out.append({"id": r["id"], "name": r["name"], "address": r["address"], "google": t12.minutes(r["google_friday_close"]),
                        "qloo": key[r["id"]]["closes_friday"], "shown": r["id"] in t12.SHOWN})
    return out


def answer(p, arm, small, with_qloo):
    name = os.path.join(qloo.CACHE, f"llm20_{arm}_{p['id']}.json")
    if os.path.exists(name):
        return json.load(open(name))
    prompt = f"Restaurant: {p['name']}\nAddress: {p['address']}\nQuestion: What time does it close on Friday?"
    if with_qloo:
        prompt += f"\n\nPlace-data record for this restaurant: Friday closing time {p['qloo']}."

    def check(o):
        if "closes" not in o or (o["closes"] is not None and t12.minutes(str(o["closes"])) is None):
            raise ValueError('reply as {"closes": "HH:MM"} or {"closes": null}')
    o = b18.small_json(WITH if with_qloo else ALONE, prompt, check) if small else \
        llm.complete_json(WITH if with_qloo else ALONE, prompt, check=check, timeout=120)[0]
    out = {"closes": o["closes"], "host": (os.environ.get("SMALL_HOST") or "comet") if small else llm.PROVIDER}
    json.dump(out, open(name, "w"))
    return out


def collect(only=None):
    """only = 'small' or 'large' collects that model's two arms (they run on different credit)."""
    ps, done, fails = places(), 0, 0
    for arm, small, with_qloo in [a for a in ARMS if only is None or a[0].startswith(only)]:
        for p in ps:
            while True:
                try:
                    answer(p, arm, small, with_qloo)
                    done += 1
                    break
                except Exception as e:
                    fails += 1
                    msg = str(e)[:90]
                    print("retry after:", msg, flush=True)
                    if fails > 60 or any(x in msg for x in ("401", "402", "403", "insufficient", "exceeded your current quota")):
                        raise
                    time.sleep(15)
        print(arm, "done:", done, "of", len(ps) * len(ARMS), flush=True)


def share(vals):
    v = np.array(vals, dtype=float)
    rng = np.random.default_rng(0)
    boots = [float(np.mean(rng.choice(v, len(v)))) for _ in range(2000)]
    return {"share": round(float(v.mean()), 3), "count": int(v.sum()), "n": len(v), "ci95": [round(float(x), 3) for x in np.percentile(boots, [2.5, 97.5])]}


def _score(ps, models):
    res, right = {}, {}
    for arm, small, with_qloo in [a for a in ARMS if a[0].split("_")[0] in models]:
        ok, declined, wrong = [], 0, 0
        for p in ps:
            a = answer(p, arm, small, with_qloo)["closes"]
            m = None if a is None else t12.minutes(str(a))
            if m is None:
                declined += 1; ok.append(False); continue
            d = abs(m - p["google"]); d = min(d, 1440 - d)
            ok.append(d <= 30); wrong += d > 30
        right[arm] = ok
        res[arm] = {"correct": share(ok), "declined": declined, "confident_wrong": wrong}
    for m in models:
        res[f"{m}_with_minus_alone"] = share([float(a) - float(b) for a, b in zip(right[f"{m}_with_qloo"], right[f"{m}_alone"])])
        res[f"{m}_reading"] = "with Qloo above alone" if res[f"{m}_with_minus_alone"]["ci95"][0] > 0 else "not above"
    return res


def score():
    """Each model is read on its own (the protocol gives a reading per model), so one can be scored when its two
    arms are complete even if the other is still waiting on credit."""
    ps = places()
    have = lambda arm: all(os.path.exists(os.path.join(qloo.CACHE, f"llm20_{arm}_{p['id']}.json")) for p in ps)
    models = [m for m in ("large", "small") if have(f"{m}_alone") and have(f"{m}_with_qloo")]
    out = {"models_scored": models, "decision_sample": _score([p for p in ps if not p["shown"]], models), "all_places": _score(ps, models)}
    json.dump(out, open("test20_results.json", "w"), indent=1)
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    {"collect": lambda: collect(*sys.argv[2:3]), "score": score}[sys.argv[1]]()
