"""Test 9, Part A (PREREGISTRATION_9.md): development of new Qloo backgrounds on Test 8's 30 cases. Exploratory:
nothing printed here is a test result. Reuses Test 8's B and C briefs, brief call and judge unchanged.
State in test9_dev_state.json (not committed: it holds Qloo-derived text).
python test9_dev.py briefs ARM [first-last] | judge ARM | analyse ARM | show ARM CASE"""
import json
import os
import random
import sys
import threading
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

import re

import numpy as np

import backtest10 as b10
import blind_test as bt
import engine
import llm
import positioning
import qloo
import test8 as t8

STATE = "test9_dev_state.json"
LOCK = threading.Lock()
JUNK = {"cashier", "bathroom", "name", "wait time", "rude barista", "polite staff", "friendly workers", "cleanliness",
        "online orders", "app ordering", "security", "crowd", "respectful staff", "free water", "clean bathrooms",
        "staff", "service", "prices", "price", "food", "place", "order", "delivery", "manager", "parking"}


def load():
    return json.load(open(STATE, encoding="utf-8")) if os.path.exists(STATE) else {}


def save(s):
    with open(STATE, "w", encoding="utf-8") as f:
        json.dump(s, f, indent=1, ensure_ascii=False)


def places(point, take, radius, **params):
    d = qloo.get("/v2/insights", **{"filter.type": "urn:entity:place", "take": take, "filter.location": point,
                                    "filter.location.radius": radius, **params})
    return [x for x in qloo.results(d, "entities") if not x.get("properties", {}).get("is_closed")]


def food(x):
    """A place to eat or drink (the SoHo search returned Chanel)."""
    ids = [t.get("id", "") for t in x.get("tags") or []]
    return any(i.startswith("urn:tag:genre:place:restaurant") or i.rsplit(":", 1)[-1] in ("bar", "night_club", "cafe")
               for i in ids)


def closes(p, day="friday"):
    """Friday closing time as 'HH:MM', or None. A close before 06:00 is after midnight."""
    slots = [s for s in (p.get("hours") or {}).get(day, []) if not s.get("closed") and s.get("closes")]
    return slots[-1]["closes"].lstrip("T")[:5] if slots else None


def late(t):
    return t is not None and (t >= "23:00" or t < "06:00")


def line(x):
    p = x.get("properties", {})
    facts = ["$" * p["price_level"]] if p.get("price_level") else []
    if p.get("business_rating"):
        facts.append(f"rated {p['business_rating']:.1f}")
    if closes(p):
        facts.append(f"closes {closes(p)} Fri")
    kw = [k["name"] for k in p.get("keywords") or [] if k.get("name", "").lower() not in JUNK][:5]
    desc = (p.get("short_description") or "").strip().rstrip(".")
    out = x["name"] + (f" [{', '.join(facts)}]" if facts else "")
    if desc:
        out += f": {desc}."
    if kw:
        out += f" Reviewers mention {', '.join(kw)}."
    return out


def mix(rows):
    """Counted facts the model should not have to work out: price mix and who is open late on Friday."""
    prices = Counter(x["properties"]["price_level"] for x in rows if x.get("properties", {}).get("price_level"))
    out = []
    if prices:
        out.append("Price levels: " + ", ".join(f"{n} at {'$' * k}" for k, n in sorted(prices.items())) + ".")
    known = [x for x in rows if closes(x.get("properties", {}))]
    if known:
        names = [x["name"] for x in known if late(closes(x["properties"]))]
        out.append(f"Open at 23:00 or later on Friday: {', '.join(names) if names else 'none'} (of {len(known)} with hours).")
    return " ".join(out)


def arm_D(c):
    """Place intelligence: same-cuisine competitors within 1.5 km and the places within 800 m that fans of the
    cuisine rate highest, each with price, rating, Friday closing time, description and review keywords."""
    point = f"POINT({c['lon']:.4f} {c['lat']:.4f})"
    tag = f"urn:tag:genre:place:restaurant:{c['slug']}"
    comp = places(point, 12, 1500, **{"filter.tags": tag})
    loved = [x for x in places(point, 20, 800, **{"signal.interests.tags": tag})
             if x["entity_id"] not in {y["entity_id"] for y in comp} and food(x)][:12]
    parts = [f"{c['concept']} places within 1.5 km ({len(comp)} found)" + (":" if comp else ".")]
    parts += ["- " + line(x) for x in comp]
    if comp:
        parts.append(mix(comp))
    parts.append(f"\nOther places within 800 m that people who like {c['concept']} food rate highest:")
    parts += ["- " + line(x) for x in loved]
    if loved:
        parts.append(mix(loved))
    return "\n".join(p for p in parts if p)


def known_for(rows, top=8):
    """Review keywords summed over places, most mentioned first."""
    n = Counter()
    for x in rows:
        for k in x.get("properties", {}).get("keywords") or []:
            if k.get("name", "").lower() not in JUNK:
                n[k["name"].lower()] += k.get("count") or 1
    return [k for k, _ in n.most_common(top)]


def latest(rows):
    """'22:00 (Hado, Saka)': the latest Friday closing among places with hours, and who closes then."""
    t = {x["name"]: closes(x.get("properties", {})) for x in rows}
    t = {k: v for k, v in t.items() if v}
    if not t:
        return None
    key = lambda v: ("1" if v < "06:00" else "0") + v
    last = max(t.values(), key=key)
    return f"{last} ({', '.join(k for k, v in t.items() if v == last)})", len(t)


def short(x):
    p = x.get("properties", {})
    bits = ["$" * p["price_level"]] if p.get("price_level") else []
    if closes(p):
        bits.append("closes " + closes(p))
    kw = [k["name"] for k in p.get("keywords") or [] if k.get("name", "").lower() not in JUNK][:3]
    return x["name"] + (f" ({', '.join(bits)})" if bits else "") + (": " + ", ".join(kw) if kw else "")


def genre(x):
    g = (x.get("properties", {}).get("primary_genre") or {})
    return g.get("name") or g.get("id", "").rsplit(":", 1)[-1].replace("_", " ")


def bare(x):
    return x["name"] + (f" ({genre(x)})" if genre(x) else "")


def arm_En(c):
    """Ablation: E's Qloo-selected places with names and cuisine only. No price, hours, rating or keywords."""
    point = f"POINT({c['lon']:.4f} {c['lat']:.4f})"
    tag = f"urn:tag:genre:place:restaurant:{c['slug']}"
    comp = places(point, 12, 1500, **{"filter.tags": tag})
    loved = [x for x in places(point, 20, 800, **{"signal.interests.tags": tag})
             if x["entity_id"] not in {y["entity_id"] for y in comp} and food(x)][:10]
    out = [LEAD, "", (f"Competitors: {len(comp)} {c['concept']} places within 1.5 km: " + "; ".join(bare(x) for x in comp) + "."
                      if comp else f"Competitors: no {c['concept']} place within 1.5 km.")]
    if loved:
        out += ["", f"Neighbours within 800 m that people who like {c['concept']} food rate highest: "
                + "; ".join(bare(x) for x in loved) + "."]
    return "\n".join(out)


def arm_Em(c):
    """Ablation: E's metadata, with neighbours taken in Qloo's default order (no taste signal)."""
    return arm_E(c, affinity=False)


def arm_E(c, affinity=True):
    """D's data as stated findings: named competitors, what they are known for in aggregate, price mix,
    latest closing; then what sells at the places nearby that the cuisine's fans rate highest."""
    point = f"POINT({c['lon']:.4f} {c['lat']:.4f})"
    tag = f"urn:tag:genre:place:restaurant:{c['slug']}"
    comp = places(point, 12, 1500, **{"filter.tags": tag})
    loved = [x for x in places(point, 20, 800, **({"signal.interests.tags": tag} if affinity else {}))
             if x["entity_id"] not in {y["entity_id"] for y in comp} and food(x)][:10]
    out = [LEAD, ""]
    if comp:
        out.append(f"Competitors: {len(comp)} {c['concept']} places within 1.5 km: " + "; ".join(short(x) for x in comp) + ".")
        prices = Counter(x["properties"]["price_level"] for x in comp if x.get("properties", {}).get("price_level"))
        if prices:
            out.append("Their price levels: " + ", ".join(f"{n} at {'$' * k}" for k, n in sorted(prices.items())) + ".")
        if known_for(comp):
            out.append("What their reviewers mention most: " + ", ".join(known_for(comp)) + ".")
        if latest(comp):
            out.append(f"Latest Friday closing among the {latest(comp)[1]} with hours: {latest(comp)[0]}.")
    else:
        out.append(f"Competitors: no {c['concept']} place within 1.5 km.")
    if loved:
        out += ["", (f"Neighbours within 800 m that people who like {c['concept']} food rate highest: " if affinity
                     else "Places to eat and drink within 800 m: ") + "; ".join(short(x) for x in loved) + "."]
        if known_for(loved):
            out.append("What sells there, by reviewer mentions: " + ", ".join(known_for(loved)) + ".")
        names = [x["name"] for x in loved if late(closes(x.get("properties", {})))]
        out.append("Open at 23:00 or later on Friday: " + (", ".join(names) if names else "none of them") + ".")
    return "\n".join(out)


LEAD = ("These are facts about real businesses around the address. State them plainly in the brief and name the "
        "businesses where it helps the founder: competitors to differ from, neighbours to work with.")


def arm_Cp(c):
    """Control for E's opening line: Test 8's city-records list (arm C) under the same line. No Qloo."""
    return LEAD + "\n\nActive restaurants within 500 m, nearest first, from city inspection records:\n" + t8.city_background(c)


LEAD_Q = (LEAD + " Details are known for only some of the competitors, so never say that no competitor does "
          "something, and never say what the competitors without details serve, charge or when they close.")


def pair(left, right):
    """Test 10's matching rule, returning {left index: right index}."""
    pairs = sorted((engine.metres(a["lat"], a["lon"], b["lat"], b["lon"]), i, j)
                   for i, a in enumerate(left) for j, b in enumerate(right)
                   if abs(a["lat"] - b["lat"]) < 0.003 and b10.same_name(a["name"], b["name"]))
    out, used = {}, set()
    for d, i, j in pairs:
        if d <= b10.PAIR and i not in out and j not in used:
            out[i] = j; used.add(j)
    return out


def located(rows):
    return [{"name": x["name"], "lat": float(x["location"]["lat"]), "lon": float(x["location"]["lon"]), "raw": x}
            for x in rows if (x.get("location") or {}).get("lat") is not None]


def arm_Q(c, take=15, attrs=True, affinity=True):
    """E made to comply with Test 10's bands (coverage under 50%, existence under 90%): city inspection records
    define the competitor set, Qloo adds detail to the ones it holds, no absence claims, and a neighbour is
    named as operating only if it has an active city record."""
    point = f"POINT({c['lon']:.4f} {c['lat']:.4f})"
    tag = f"urn:tag:genre:place:restaurant:{c['slug']}"
    cat = engine.CONCEPTS[c["concept"]][0]
    city_all = b10.city_list(c)
    city_cat = sorted((x for x in city_all if x["cuisine"] == cat and x["metres"] <= b10.NEAR), key=lambda x: x["metres"])
    q = []
    for page in range(1, 5):  # Test 10's Qloo list, with the full records
        rows = qloo.results(qloo.get("/v2/insights", **{"filter.type": "urn:entity:place", "filter.tags": tag, "filter.location": point,
                                                        "filter.location.radius": b10.WIDE, "take": 50, "page": page}), "entities")
        q += [x for x in rows if not x.get("properties", {}).get("is_closed")]
        if len(rows) < 50:
            break
    q = located(q)
    near = city_cat[:take]
    m = pair(near, q)
    known = [q[j]["raw"] for j in m.values()]
    name = lambda x: re.sub(r"(?<=\w)'S\b", "'s", x["name"].title())
    one = short if attrs else bare
    out = [LEAD_Q if attrs else LEAD, ""]
    if near:
        out.append(f"Competitors: city inspection records list {len(city_cat)} {c['concept']} restaurants within 1.5 km. "
                   f"The {len(near)} nearest: " + "; ".join(name(x) if not attrs else short(q[m[i]]["raw"]) if i in m
                                                            else name(x) + " (no details)" for i, x in enumerate(near)) + ".")
        if known and attrs:
            prices = Counter(x["properties"]["price_level"] for x in known if x.get("properties", {}).get("price_level"))
            out.append(f"Among the {len(known)} with details: " + "; ".join(filter(None, [
                "price levels " + ", ".join(f"{n} at {'$' * k}" for k, n in sorted(prices.items())) if prices else "",
                "reviewers mention most " + ", ".join(known_for(known)) if known_for(known) else "",
                f"latest Friday closing {latest(known)[0]}" if latest(known) else ""])) + ".")
    else:
        out.append(f"Competitors: city inspection records list no {c['concept']} restaurant within 1.5 km.")
    # the union: Qloo's same-cuisine places the city files under another category, if the city has them at all
    rest = [x for j, x in enumerate(q) if j not in m.values()
            and engine.metres(c["lat"], c["lon"], x["lat"], x["lon"]) <= b10.NEAR]
    alive = pair(rest, city_all)
    extra = [x["raw"] for i, x in enumerate(rest) if i in alive][:8]
    if extra:
        out.append(f"Also tagged {c['concept']} by Qloo, with an active city record under another category: "
                   + "; ".join(one(x) for x in extra) + ".")
    taken = {x["entity_id"] for x in known} | {x["raw"]["entity_id"] for x in q}
    loved = located([x for x in places(point, 20, 800, **({"signal.interests.tags": tag} if affinity else {}))
                     if x["entity_id"] not in taken and food(x)])
    ok = pair(loved, city_all)
    sure = [x["raw"] for i, x in enumerate(loved) if i in ok][:10]
    if sure:
        out += ["", (f"Neighbours within 800 m that people who like {c['concept']} food rate highest" if affinity
                     else "Places to eat and drink within 800 m") + ", each with an active city inspection record: "
                + "; ".join(one(x) for x in sure) + "."]
        if attrs and known_for(sure):
            out.append("What sells there, by reviewer mentions: " + ", ".join(known_for(sure)) + ".")
        names = [x["name"] for x in sure if attrs and late(closes(x.get("properties", {})))]
        if names:
            out.append("Of these, open at 23:00 or later on Friday: " + ", ".join(names) + ".")
    unsure = [x["name"] for i, x in enumerate(loved) if i not in ok][:5]
    if unsure:
        out.append("Listed by Qloo but not found in city records, so do not name them as operating: " + ", ".join(unsure) + ".")
    return "\n".join(out)


def arm_Q0(c, take=15):
    """Control for Q (Amendment 2): Q's city-record content with nothing from Qloo."""
    cat = engine.CONCEPTS[c["concept"]][0]
    city_all = sorted(b10.city_list(c), key=lambda x: x["metres"])
    city_cat = [x for x in city_all if x["cuisine"] == cat and x["metres"] <= b10.NEAR]
    name = lambda x: re.sub(r"(?<=\w)'S\b", "'s", x["name"].title())
    out = [LEAD, "", (f"Competitors: city inspection records list {len(city_cat)} {c['concept']} restaurants within 1.5 km. "
                      f"The {len(city_cat[:take])} nearest: " + "; ".join(name(x) for x in city_cat[:take]) + "." if city_cat
                      else f"Competitors: city inspection records list no {c['concept']} restaurant within 1.5 km.")]
    others = [x for x in city_all if x["cuisine"] != cat and x["metres"] <= 800][:10]
    if others:
        out += ["", "Nearest other places to eat and drink within 800 m, from city inspection records: "
                + "; ".join(f"{name(x)} ({x['cuisine']})" for x in others) + "."]
    return "\n".join(out)


def arm_Qn(c):
    """Ablation of Q: Qloo chooses which places are listed, but only names and categories are given."""
    return arm_Q(c, attrs=False)


def arm_Qm(c):
    """Ablation of Q: Q's attributes, neighbours in Qloo's default order (no taste signal)."""
    return arm_Q(c, affinity=False)


ARMS = {"D": arm_D, "E": arm_E, "Cp": arm_Cp, "En": arm_En, "Em": arm_Em, "Q": arm_Q, "Q0": arm_Q0, "Qn": arm_Qn, "Qm": arm_Qm}


def _cases(s8, span):
    lo, hi = (map(int, span.split("-")) if span else (1, 30))
    return [c for c in s8["cases"] if lo <= c["id"] <= hi]


def briefs(arm, span=None):
    s, s8 = load(), t8.load()

    def one(c):
        b = s.setdefault("arms", {}).setdefault(arm, {}).setdefault(str(c["id"]), {})
        if "brief" in b or "dropped" in b:
            return
        try:
            bg = ARMS[arm](c)
            text = bt._brief(c["concept"], c["area"], bg)[0]
            # an empty or cut-off reply is a provider failure, not a brief: leave the case to be rerun
            if any(h not in positioning.sections(text) for h in positioning.HEADINGS):
                print(c["id"], "empty or cut-off reply, not saved", flush=True)
                return
            with LOCK:
                b.update(background=bg, brief=text); save(s)
        except RuntimeError as e:
            with LOCK:
                b["dropped"] = str(e); save(s)
        print(c["id"], "done", flush=True)
    with ThreadPoolExecutor(3) as ex:
        list(ex.map(one, _cases(s8, span)))
    print("spent usd:", round(llm.SPEND["usd"], 2), "| qloo quota:", qloo.QUOTA["remaining"])


def judge(arm, vs=None):
    """X = this arm, against Test 8's B and C. With vs, the C slot holds that development arm's brief instead
    (judgements kept under 'ARM_vs_VS')."""
    s, s8 = load(), t8.load()
    key = f"{arm}_vs_{vs}" if vs else arm

    def one(c):
        cid = str(c["id"])
        x = s["arms"][arm].get(cid, {})
        other = s["arms"][vs].get(cid, {}).get("brief") if vs else s8["briefs"][cid]["C"]
        if "brief" not in x or not other:
            return
        texts = {"X": x["brief"], "B": s8["briefs"][cid]["B"], "C": other}
        order = ["X", "B", "C"]; random.Random(f"{key}-{cid}").shuffle(order)
        done = s.setdefault("judgements", {}).setdefault(key, {}).setdefault(cid, {})
        for k, o in (("j1", order), ("j2", order[::-1])):
            if k in done:
                continue
            prompt = f"Concept: {c['concept']}. Location: {c['area']}.\n\n" + "\n\n".join(
                f"Brief {i + 1}:\n{texts[a]}" for i, a in enumerate(o))
            r = t8.gemini(prompt)
            with LOCK:
                done[k] = {"host": os.environ.get("JUDGE_HOST", "google"), "order": o, "ranking": [o[int(v) - 1] for v in r["ranking"]],
                           "scores": {o[int(i) - 1]: v for i, v in r["scores"].items()}}
                save(s)
        print(cid, "judged", flush=True)
    with ThreadPoolExecutor(3) as ex:
        list(ex.map(one, s8["cases"]))


def analyse(arm):
    js = {k: v for k, v in load()["judgements"][arm].items() if len(v) == 2}

    def stat(x, y):
        vals = [np.mean([t8.above(j["ranking"], x, y) for j in v.values()]) for v in js.values()]
        rng = np.random.default_rng(0)
        boots = [np.mean(rng.choice(vals, len(vals))) for _ in range(2000)]
        return round(float(np.mean(vals)), 3), [round(float(b), 3) for b in np.percentile(boots, [2.5, 97.5])]
    flat = [j for v in js.values() for j in v.values()]
    print(f"EXPLORATORY, arm {arm}, {len(js)} cases")
    print(" X over C:", *stat("X", "C"), "| X over B:", *stat("X", "B"))
    print(" ranked first:", dict(Counter(j["ranking"][0] for j in flat)), "| last:", dict(Counter(j["ranking"][-1] for j in flat)))
    for a in "XBC":
        print(f" {a}:", {k: round(float(np.mean([j["scores"][a][k] for j in flat])), 2) for k in t8.RUBRIC})
    print(" per case, X over C:", {k: float(np.mean([t8.above(j["ranking"], "X", "C") for j in v.values()])) for k, v in js.items()})


def show(arm, cid):
    x = load()["arms"][arm][cid]
    print(x["background"], "\n\n-----\n", x.get("brief") or x.get("dropped"))


if __name__ == "__main__":
    {"briefs": briefs, "judge": judge, "analyse": analyse, "show": show}[sys.argv[1]](*sys.argv[2:])
