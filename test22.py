"""Test 22 (screen) as registered in PREREGISTRATION_22.md: do model-written NYC plans send people to closed
places, and does Qloo hold hours for enough of the stops to check them?
python test22.py collect [large|small]   (plans, saved; no result)
python test22.py score                   (bars 1 and 2; writes test22_results.json and test22_detail.json)
python test22.py sheet                   (only if bars 1 and 2 hold: test22_sheet.csv for a person, test22_key.json)
python test22.py confirm                 (bar 3 from the filled sheet)"""
import csv
import json
import os
import random
import re
import sys
import time

import numpy as np

import backtest10 as b10
import backtest18 as b18
import llm
import qloo
import scene
import test12 as t12

PLACES = ["Williamsburg", "Astoria", "East Village", "Harlem", "Park Slope", "Long Island City", "Lower East Side",
          "Bushwick", "Jackson Heights", "Upper West Side"]
OCCASIONS = [("a Friday night out, 7 pm to 1 am", "friday"), ("a Sunday, 10 am to 4 pm", "sunday"),
             ("a Monday evening, 6 pm to 11 pm", "monday")]
REQUESTS = [(p, o, d) for p in PLACES for o, d in OCCASIONS]
ASK = ("Plan {occasion} for two people in {place}, New York City. Give exactly 4 stops at real places to eat or drink, "
       "in order. For each stop give the place's name, its street address, and the time we arrive and the time we "
       "leave, in 24-hour HH:MM.")
FORMAT = 'Reply as {"stops": [{"name": "...", "address": "...", "arrive": "HH:MM", "leave": "HH:MM"}, ...]}.'
GRACE, SHEET, KEY = 15, "test22_sheet.csv", "test22_key.json"


def plan(model, i):
    name = os.path.join(qloo.CACHE, f"llm22_{model}_{i}.json")
    if os.path.exists(name):
        return json.load(open(name, encoding="utf-8"))
    place, occasion, _ = REQUESTS[i]

    def check(o):
        s = o.get("stops")
        if not isinstance(s, list) or len(s) != 4 or any(
                not isinstance(x, dict) or not x.get("name") or t12.minutes(str(x.get("arrive"))) is None
                or t12.minutes(str(x.get("leave"))) is None for x in s):
            raise ValueError("give exactly 4 stops, each with name, address, arrive and leave as HH:MM")
    prompt = ASK.format(occasion=occasion, place=place)
    o = b18.small_json(FORMAT, prompt, check) if model == "small" else llm.complete_json(FORMAT, prompt, check=check, timeout=120)[0]
    out = {"stops": o["stops"], "host": "comet" if model == "small" else llm.PROVIDER}
    json.dump(out, open(name, "w", encoding="utf-8"), ensure_ascii=False)
    return out


def collect(only=None):
    fails = 0
    for model in [m for m in ("large", "small") if only in (None, m)]:
        for i in range(len(REQUESTS)):
            while True:
                try:
                    plan(model, i)
                    break
                except Exception as e:
                    fails += 1
                    msg = str(e)[:90]
                    print("retry after:", msg, flush=True)
                    if fails > 40 or any(x in msg for x in ("401", "402", "403", "insufficient", "exceeded your current quota")):
                        raise
                    time.sleep(15)
        print(model, "plans done", flush=True)


def clock(t):
    """Minutes on the plan's day; a time before 06:00 is after midnight."""
    m = t12.minutes(str(t).lstrip("T")[:5])
    return None if m is None else m + 1440 if m < 360 else m


def find(stop):
    hits = [h for h in scene.search(stop["name"]) if b10.same_name(h.get("name", ""), stop["name"])]
    num = re.match(r"\s*(\d+)", str(stop.get("address") or ""))
    same = [h for h in hits if num and re.match(rf"\s*{num.group(1)}\b", str(h.get("properties", {}).get("address") or ""))]
    return (same or hits or [None])[0]


def flag(h, stop, day):
    """(checkable, reason or None) for a found record."""
    p = h.get("properties", {})
    if p.get("is_closed"):
        return True, "marked closed for good"
    slots = (p.get("hours") or {}).get(day)
    if not slots:
        return False, None
    a, l = clock(stop["arrive"]), clock(stop["leave"])
    spans = []
    for s in slots:
        if s.get("closed") or not s.get("opens") or not s.get("closes"):
            continue
        o, c = t12.minutes(s["opens"].lstrip("T")[:5]), t12.minutes(s["closes"].lstrip("T")[:5])
        spans.append((o, c + 1440 if c <= o or c < 360 else c))
    if not spans:
        return True, "closed that day"
    if any(a >= o and l <= c + GRACE for o, c in spans):
        return True, None
    return True, "arrives before it opens" if all(a < o for o, _ in spans) else "leaves after it closes"


def stops(model):
    out = []
    for i, (place, occasion, day) in enumerate(REQUESTS):
        for j, s in enumerate(plan(model, i)["stops"]):
            h = find(s)
            checkable, reason = flag(h, s, day) if h else (False, None)
            out.append({"plan": i, "stop": j, "day": day, "neighbourhood": place, "name": s["name"], "address": s.get("address"),
                        "arrive": s["arrive"], "leave": s["leave"], "found": bool(h), "checkable": checkable, "reason": reason,
                        "qloo_hours": (h.get("properties", {}).get("hours") or {}).get(day) if h else None})
    return out


def interval(per_plan):
    v = np.array(per_plan, dtype=float)
    rng = np.random.default_rng(0)
    b = [float(np.mean(rng.choice(v, len(v)))) for _ in range(2000)]
    return {"share": round(float(v.mean()), 3), "ci95": [round(float(x), 3) for x in np.percentile(b, [2.5, 97.5])], "n": len(v)}


def measures(rows):
    plans = sorted({r["plan"] for r in rows})
    by = lambda i: [r for r in rows if r["plan"] == i]
    checkable = [r for r in rows if r["checkable"]]
    return {"stops": len(rows), "found": sum(r["found"] for r in rows),
            "coverage": interval([np.mean([r["checkable"] for r in by(i)]) for i in plans]),
            "plans_with_a_flagged_stop": interval([any(r["reason"] for r in by(i)) for i in plans]),
            "checkable_stops_flagged": {"share": round(sum(bool(r["reason"]) for r in checkable) / max(1, len(checkable)), 3),
                                        "count": sum(bool(r["reason"]) for r in checkable), "n": len(checkable)},
            "reasons": {k: sum(r["reason"] == k for r in rows) for k in sorted({r["reason"] for r in rows if r["reason"]})}}


def score():
    out, detail = {}, {}
    for model in ("large", "small"):
        if not all(os.path.exists(os.path.join(qloo.CACHE, f"llm22_{model}_{i}.json")) for i in range(len(REQUESTS))):
            continue
        rows = stops(model)
        detail[model] = rows
        out[model] = {**measures(rows), "by_occasion": {d: measures([r for r in rows if r["day"] == d]) for _, d in OCCASIONS}}
    if "large" in out:
        c, p = out["large"]["coverage"]["share"] >= 0.70, out["large"]["plans_with_a_flagged_stop"]["share"] >= 0.25
        out["bar_1_coverage"], out["bar_2_plans_flagged"] = c, p
        out["reading"] = ("bars 1 and 2 hold: make the sheet for bar 3" if c and p else
                          "Qloo holds hours for too few of the places models put in plans to check them" if not c else
                          "Plans from a strong model rarely send people to a closed place: no problem to solve")
    json.dump(out, open("test22_results.json", "w"), indent=1)
    json.dump(detail, open("test22_detail.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print(json.dumps(out, indent=1))


def sheet():
    rows = json.load(open("test22_detail.json", encoding="utf-8"))["large"]
    rng = random.Random(22)
    flagged = [r for r in rows if r["reason"]]
    clear = [r for r in rows if r["checkable"] and not r["reason"]]
    if len(flagged) > 20:
        flagged = rng.sample(flagged, 20)
    clear = rng.sample(clear, min(len(flagged), len(clear)))
    pick = flagged + clear
    rng.shuffle(pick)
    json.dump({str(i): {"flagged": bool(r["reason"]), "reason": r["reason"], "plan": r["plan"], "stop": r["stop"]} for i, r in enumerate(pick, 1)},
              open(KEY, "w"), indent=1)
    with open(SHEET, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["id", "name", "address", "day", "planned_arrive", "planned_leave", "google_opens", "google_closes",
                    "closed_that_day_or_permanently (write: day / permanent / blank)"])
        for i, r in enumerate(pick, 1):
            w.writerow([i, r["name"], r["address"], r["day"].title(), r["arrive"], r["leave"], "", "", ""])
    print(len(pick), "rows written to", SHEET)


def confirm():
    key = json.load(open(KEY))
    wrong = {True: [], False: []}
    for r in csv.DictReader(open(SHEET, encoding="utf-8-sig")):
        note = list(r.values())[8].strip().lower()
        o, c = t12.minutes(r["google_opens"]), t12.minutes(r["google_closes"])
        if not note and (o is None or c is None):
            continue
        if note:
            bad = True
        else:
            c = c + 1440 if c <= o or c < 360 else c
            bad = not (clock(r["planned_arrive"]) >= o and clock(r["planned_leave"]) <= c + GRACE)
        wrong[key[r["id"]]["flagged"]].append(bad)
    res = json.load(open("test22_results.json"))
    share = lambda v: {"share": round(float(np.mean(v)), 3) if v else None, "count": int(sum(v)), "n": len(v)}
    res["precision_flagged_confirmed_wrong"], res["miss_rate_unflagged_wrong"] = share(wrong[True]), share(wrong[False])
    ok = bool(wrong[True]) and res["precision_flagged_confirmed_wrong"]["share"] >= 0.70
    res["bar_3_precision"] = ok
    res["reading"] = "all three bars hold: worth building" if ok else "Qloo's flags are too often wrong to act on"
    json.dump(res, open("test22_results.json", "w"), indent=1)
    print(json.dumps({k: res[k] for k in ("precision_flagged_confirmed_wrong", "miss_rate_unflagged_wrong", "bar_3_precision", "reading")}, indent=1))


if __name__ == "__main__":
    {"collect": lambda: collect(*sys.argv[2:3]), "score": score, "sheet": sheet, "confirm": confirm}[sys.argv[1]]()
