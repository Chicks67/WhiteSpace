"""Test 12 as registered in PREREGISTRATION_12.md: Qloo's Friday closing times and price levels against Google
Maps and restaurants' own sites. The sheet hides Qloo's values; the key holds them. Neither is committed.
python test12.py sheet   (draws the sample; writes test12_sheet.csv and test12_key.json)
python test12.py score   (after a person has filled the sheet; writes test12_results.json)"""
import csv
import json
import random
import re
import sys
from collections import Counter

import numpy as np

import around
import engine
import positioning

SHEET, KEY, N = "test12_sheet.csv", "test12_key.json", 40
BOROUGHS = ["Bronx", "Brooklyn", "Manhattan", "Queens"]
COLS = ["id", "name", "address", "borough", "google_friday_close", "google_price", "google_permanently_closed (y/n)",
        "own_site_friday_close", "notes"]


def sheet():
    # Ran once, on 2026-10-12. around.py dropped price levels afterwards (this test's outcome), so this step
    # cannot be rerun as written; the drawn sample is in test12_sheet.csv and test12_key.json.
    chains = Counter(positioning._norm(r["dba"]) for r in engine.city().rest)
    pool = {}
    for c in json.load(open("test8_cases.json")):
        a = around.for_point(c["concept"], c["lat"], c["lon"])
        rows = [x["qloo"] for x in a["competitors"] if x["qloo"]] + a["also_tagged"] + a["neighbours"]
        for q in rows:
            name = q.get("qloo_name") or q["name"]
            if q["closes_friday"] and q["price_level"] and q.get("address") and chains[positioning._norm(name)] < 5:
                # borough = the borough of the storefront the place was drawn for (it lies within 1.5 km of it)
                pool.setdefault((positioning._norm(name), q["address"]), {
                    "name": name, "address": q["address"], "borough": c["address"].rsplit(", ", 1)[-1],
                    "closes_friday": q["closes_friday"], "price_level": q["price_level"]})
    places = sorted(pool.values(), key=lambda p: (p["name"], p["address"]))
    random.Random(12).shuffle(places)
    by = {b: [p for p in places if p["borough"] == b] for b in BOROUGHS}
    picked = []
    while len(picked) < N and any(by.values()):
        for b in BOROUGHS:
            if by[b] and len(picked) < N:
                picked.append(by[b].pop(0))
    with open(SHEET, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(COLS)
        for i, p in enumerate(picked, 1):
            w.writerow([i, p["name"], p["address"], p["borough"], "", "", "", "", ""])
    json.dump({str(i): p for i, p in enumerate(picked, 1)}, open(KEY, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print(f"pool {len(places)} places; drew {len(picked)}:", dict(Counter(p["borough"] for p in picked)))


def minutes(text):
    """'23:00', '11 PM', '11:30pm', '2 am' -> minutes after midnight, or None."""
    text = text.lower().replace("midnight", "12 am").replace("noon", "12 pm")
    m = re.match(r"^\s*(\d{1,2})(?::(\d{2}))?\s*([ap])?\.?m?\.?\s*$", text.strip())
    if not m:
        return None
    h, mi, ap = int(m.group(1)), int(m.group(2) or 0), m.group(3)
    if ap:
        h = h % 12 + (12 if ap == "p" else 0)
    return (h * 60 + mi) % 1440


def level(text):
    """'$$' -> 2; '$20-30' -> 2 (upper bound up to 20, 50, 100, more); '$100+' -> 4."""
    t = text.strip().replace("–", "-")
    if re.fullmatch(r"\$+", t):
        return len(t)
    nums = [int(n) for n in re.findall(r"\d+", t)]
    if not nums:
        return None
    if "+" in t:
        return 4 if nums[-1] >= 100 else None
    return 1 if nums[-1] <= 20 else 2 if nums[-1] <= 50 else 3 if nums[-1] <= 100 else 4


def share(vals):
    if not vals:  # nothing to compare (for example no price was recorded)
        return {"share": None, "n": 0, "ci95": [None, None]}
    vals = np.array(vals, dtype=float)
    rng = np.random.default_rng(0)
    boots = [float(np.mean(rng.choice(vals, len(vals)))) for _ in range(2000)]
    return {"share": round(float(vals.mean()), 3), "n": len(vals), "ci95": [round(float(v), 3) for v in np.percentile(boots, [2.5, 97.5])]}


SHOWN = {"3", "4", "15", "20", "24", "28", "34"}  # Amendment 1: Qloo values for these were seen before the check


def score():
    """Decision on the 33 places not shown (Amendment 1); all 40 reported beside it."""
    rows = list(csv.DictReader(open(SHEET, encoding="utf-8-sig")))
    out = {"decision_sample_33": _score([r for r in rows if r["id"] not in SHOWN]), "all_40": _score(rows)}
    json.dump(out, open("test12_results.json", "w"), indent=1)
    print(json.dumps(out, indent=1))


def _score(rows):
    key = json.load(open(KEY, encoding="utf-8"))
    closed = sum(r[COLS[6]].strip().lower().startswith("y") for r in rows)
    near, exact, price, price1, own, skipped, by_kind = [], [], [], [], 0, 0, {}
    for r in rows:
        k = key[r["id"]]
        if r[COLS[6]].strip().lower().startswith("y"):
            continue
        # Amendment 3: own site first, then Google's listing, then one other named listing site
        ref, kind = None, None
        for col, label in (("own_site_friday_close", "own site"), ("google_friday_close", "Google"), ("other_friday_close", "other listing")):
            if ref is None and (r.get(col) or "").strip():
                ref, kind = minutes(r[col]), label
        own += kind == "own site"
        if ref is None:
            skipped += 1
        else:
            d = abs(minutes(k["closes_friday"]) - ref)
            d = min(d, 1440 - d)
            near.append(d <= 30); exact.append(d == 0)
            by_kind.setdefault(kind, []).append(d <= 30)
        g = level(r["google_price"]) if r["google_price"].strip() else None
        if g is not None:
            price.append(g == k["price_level"]); price1.append(abs(g - k["price_level"]) <= 1)
    out = {"places": len(rows), "permanently_closed": closed, "no_reference_hours": skipped, "reference_from_own_site": own,
           "closing_within_30_min": share(near), "closing_exact": share(exact), "price_equal": share(price),
           "price_within_one_level": share(price1)}
    out["closing_within_30_min_by_reference"] = {k: {"share": round(sum(v) / len(v), 3), "n": len(v)} for k, v in by_kind.items()}
    out["closing_times"] = "shown" if out["closing_within_30_min"]["share"] >= 0.8 else "removed"
    out["price_levels"] = ("not assessed (no reference price recorded)" if out["price_equal"]["share"] is None
                           else "shown" if out["price_equal"]["share"] >= 0.7 else "removed")
    out["closed_note_needed"] = closed / len(rows) > 0.1
    return out


if __name__ == "__main__":
    {"sheet": sheet, "score": score}[sys.argv[1]]()
