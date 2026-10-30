"""Scout mode: the founder describes the plan in plain words; the agent finds and shortlists storefronts.

A function-calling loop (GPT-6 Astra on Kie). The model plans which neighbourhoods to consider (by census
measures of the founder's target customers), searches vacant storefronts in several of them, checks
competition, and submits a shortlist. Code runs every tool, and checks the shortlist: every storefront must
have come from a search in this run, and every number in the reasons must appear in a tool result.
"""
import json
import re
import time

import census
import engine
import followup
import llm
import storefronts

MAX_CALLS = 12
TARGET_KEYS = list(census.TARGETS)

INSTRUCTIONS = (
    "You are Whitespace's scout, helping an independent restaurant founder in New York City find a lease. "
    "Work like a careful site-selection analyst:\n"
    "1. Read the founder's plan: cuisine, target customers, places they want or want to avoid, any constraint "
    "(competition, subway access, quiet or busy streets, budget).\n"
    "2. Call list_neighbourhoods for the boroughs they named (all four if none) with the census measure that "
    "matches the target customers ('residents' if none), usually with rank_by 'balanced', which also weighs "
    "cuisine fit. Census data answers who lives or works somewhere; Qloo does not (only 2 of its 7 audience "
    "tags matched census data in our test), so never use Qloo for who is there.\n"
    "3. Pick 3 or 4 neighbourhoods and call find_storefronts in each, in one turn. If the founder names a place to "
    "be near (a campus, station, landmark), call storefronts_near_place for it instead or as well, and check the "
    "matched place is the one they meant. Every storefront found after that carries metres_to_named_places; give "
    "that distance in the reason of every pick.\n"
    "4. Judge each storefront on: fit with the target customers (the neighbourhood's census measure); cuisine fit "
    "(lease_score_percentile_nyc: how closely the block resembles blocks where operators of this cuisine chose to "
    "open recently, our best-tested signal); competition (same-cuisine counts); foot traffic (subway entries "
    "within 500 m, and busier_than_pct_of_blocks for how busy the street is).\n"
    "   Whitespace means few same-cuisine restaurants AND a good cuisine fit. Few same-cuisine restaurants with a "
    "low cuisine fit (below about the 40th percentile) usually means little demand for the cuisine there, not an "
    "opening. Do not shortlist a storefront below the 25th percentile unless the founder's constraints leave "
    "nothing better, and then say so plainly.\n"
    "5. Optionally check competitors with nearby_restaurants, or taste with area_profile (the brands and venues "
    "an area's people over-index on). Storefronts already carry subway entries; call foot_traffic only to name "
    "the nearest stations for a finalist.\n"
    "6. Finish with submit_shortlist: 3 to 5 storefronts, best first, from at least 2 neighbourhoods when "
    "possible. Use only addresses returned by find_storefronts. Quote numbers exactly as the tools give them; do "
    "not compute new ones (no differences, sums or inverted percentages). The lease score shows where operators "
    "chose to open, not where restaurants survive; never claim survival or success. Be decisive, and say what "
    "trade-off each pick makes.\n"
    "No tool here measures rent, opening hours, nightlife, or whether an area is up-and-coming; never claim them, "
    "and say plainly when the founder's plan depends on one. Staten Island is not covered.\n"
    "Cuisines we tested: " + ", ".join(engine.CONCEPTS) + "."
)

S = {"type": "string"}
CUISINE = {"type": "string", "enum": list(engine.CONCEPTS)}
BOROUGHS = {"type": "array", "items": {"type": "string", "enum": engine.BOROUGHS},
            "description": "boroughs the founder will consider; all four if they gave none"}
EFFORT = "low"  # medium spent 60 to 120 s silent per turn on Kie (no reasoning events stream) and cost ~3x
TOOLS = [
    followup._fn("list_neighbourhoods", "Rank NYC neighbourhoods by a census or jobs measure of the target customers, "
                 "with population, vacant storefronts reported, same-cuisine restaurants, and cuisine fit (median and best "
                 "lease-score percentile of the vacant storefronts for this cuisine). rank_by 'balanced' averages the "
                 "target percentile with the median cuisine fit. Measures: "
                 + "; ".join(f"{k} = {v[1]}" for k, v in census.TARGETS.items()) + ".",
                 {"cuisine": CUISINE, "target": {"type": "string", "enum": TARGET_KEYS}, "boroughs": BOROUGHS,
                  "min_vacant_storefronts": {"type": "integer", "description": "0 to 50"},
                  "rank_by": {"type": "string", "enum": ["target", "balanced"]},
                  "top": {"type": "integer", "description": "1 to 15"}},
                 ["cuisine", "target", "boroughs", "min_vacant_storefronts", "rank_by", "top"]),
    followup._fn("neighbourhood_profile", "Every census and jobs measure for one neighbourhood, with NYC percentiles.",
                 {"name": S}, ["name"]),
] + [t for t in followup.TOOLS if t["name"] in ("find_storefronts", "storefronts_near_place", "nearby_restaurants", "area_profile",
                                                   "foot_traffic", "local_partners")] + [
    followup._fn("submit_shortlist", "Finish: the shortlist of storefronts to recommend, best first.",
                 {"summary": {**S, "description": "under 50 words: the approach and the main trade-off"},
                  "picks": {"type": "array", "items": {"type": "object", "additionalProperties": False,
                            "properties": {"address": S, "neighbourhood": S,
                                           "reason": {**S, "description": "under 35 words: why it fits the plan and "
                                                      "its main trade-off. The page already shows each storefront's "
                                                      "numbers, so cite at most two."}},
                            "required": ["address", "neighbourhood", "reason"]}}},
                 ["summary", "picks"]),
]


def _vacant_by_area():
    out = {}
    for s in storefronts.vacant():
        out.setdefault(s["neighbourhood"], []).append(s)
    return out


def _fit(cuisine, stores, city, cache):
    """Lease-score percentiles (this cuisine) of a neighbourhood's vacant storefronts: median and best."""
    pcts = []
    for st in stores:
        cell = engine.g6(st["lat"], st["lon"])
        if cell not in cache:
            cache[cell] = city.score(cuisine, st["lat"], st["lon"])["score_percentile"]
        pcts.append(cache[cell])
    pcts.sort()
    return (pcts[len(pcts) // 2], pcts[-1]) if pcts else (None, None)


def list_neighbourhoods(cuisine, target, boroughs, min_vacant, top, rank_by="target"):
    key, label = census.TARGETS[target]
    lower_first = target == "budget"
    prof, vac = census.profiles(), _vacant_by_area()
    dohmh = engine.CONCEPTS[cuisine][0]
    city, cache = engine.city(), {}
    rows = []
    for name, p in prof.items():
        if boroughs and p["borough"] not in boroughs:
            continue
        stores = vac.get(name, [])
        if p[key] is None or len(stores) < max(1, min_vacant):
            continue
        share = key.endswith("_share")
        med, best = _fit(cuisine, stores, city, cache)
        target_pct = 100 - p[key + "_pct"] if lower_first else p[key + "_pct"]
        rows.append({"neighbourhood": name, "borough": p["borough"], "measure": label + (" (%)" if share else ""),
                     "value": round(100 * p[key], 1) if share else p[key], "nyc_percentile": p[key + "_pct"],
                     "population": p["population"], "vacant_storefronts": len(stores),
                     "cuisine_fit_median_percentile": med, "cuisine_fit_best_percentile": best,
                     "_sort": (target_pct + med) / 2 if rank_by == "balanced" else (-p[key] if lower_first else p[key])})
    rows.sort(key=lambda r: r["_sort"], reverse=True)
    rows = rows[:max(1, min(15, top))]
    for r in rows:  # same-cuisine supply: restaurants of this cuisine at the area's vacant storefront blocks
        cells = {engine.g6(st["lat"], st["lon"]) for st in vac.get(r["neighbourhood"], [])}
        r["same_cuisine_restaurants_near_vacancies"] = sum(
            1 for c in cells for x in city.by_cell.get(c, []) if x["cuisine"] == dohmh)
        del r["_sort"]
    ranked = label + (" (lowest first)" if lower_first and "lower first" not in label else "")
    return {"target": target, "ranked_by": ranked if rank_by != "balanced" else f"average of {ranked} percentile "
            "and median cuisine-fit percentile", "neighbourhoods": rows}


def run_tool(name, args, found, places=None):
    """places: [(label, lat, lon)] matched by storefronts_near_place in this run. Once the founder's place is
    known, every storefront any search returns carries its distance to it, so a pick from an area search can
    still say how far it is from the campus or landmark."""
    places = [] if places is None else places
    out = _run_tool(name, args, found)
    if name == "storefronts_near_place" and "matched_point" in out:
        lab = out["matched_place"].split(",")[0].title()
        if lab not in [p[0] for p in places]:
            places.append((lab, *out["matched_point"]))
    if name in ("find_storefronts", "storefronts_near_place") and places:
        for st in out.get("storefronts", []):
            l = found.get(st["address"])
            if l:
                st["metres_to_named_places"] = {p[0]: round(engine.metres(l["lat"], l["lon"], p[1], p[2])) for p in places}
    return out


def _run_tool(name, args, found):
    if name == "list_neighbourhoods":
        return list_neighbourhoods(args["cuisine"], args["target"], args.get("boroughs") or [],
                                   max(0, min(50, args["min_vacant_storefronts"])), args["top"], args.get("rank_by", "target"))
    if name == "neighbourhood_profile":
        p = census.profiles().get(args["name"])
        if not p:
            close = [n for n in census.profiles() if args["name"].lower().split()[0] in n.lower()][:5]
            return {"error": f"no neighbourhood named {args['name']!r}", "did_you_mean": close}
        return {k: (round(100 * v, 1) if k.endswith("_share") and v is not None else v) for k, v in p.items()} | {
            "note": "values ending in _share are percentages; _pct fields are NYC percentiles among 181 neighbourhoods"}
    if name in ("find_storefronts", "storefronts_near_place"):
        out, ranked = (followup.find_storefronts if name == "find_storefronts" else followup.storefronts_near_place)(args)
        for l in ranked:
            found[l["address"]] = l
        return out
    return followup.run_tool(name, args)


WEAK_FIT, GOOD_FIT = 25, 40


def check_shortlist(args, found, seen, warned):
    """Problems with a submitted shortlist, checked in code. `warned` is a set this run keeps: a weak-fit pick
    is sent back once, and accepted on resubmission only if its reason names the weak cuisine fit."""
    picks = args.get("picks") or []
    problems = []
    strong = sum(1 for l in found.values() if (l.get("score_percentile") or 0) >= GOOD_FIT)
    for p in picks:
        pct = (found.get(p["address"]) or {}).get("score_percentile")
        if pct is None or pct >= WEAK_FIT or strong < 3:
            continue
        if p["address"] not in warned:
            warned.add(p["address"])
            problems.append(f"{p['address']} is at the {pct}th percentile for cuisine fit while {strong} storefronts "
                            f"you found are at the {GOOD_FIT}th or above; replace it, or keep it only if the founder's "
                            "constraints require it and say in its reason that its cuisine fit is weak")
        elif "fit" not in p["reason"].lower():
            problems.append(f"say in the reason for {p['address']} that its cuisine fit is weak")
    if not 1 <= len(picks) <= 5:
        problems.append("give 1 to 5 picks")
    for p in picks:
        if p["address"] not in found:
            problems.append(f"{p['address']!r} was not returned by find_storefronts; use an exact address from it")
    text = args.get("summary", "") + " ".join(p["reason"] for p in picks)
    loose = sorted(followup._numbers(text) - followup._numbers(seen))
    if loose:
        problems.append(f"these numbers appear in no tool result: {', '.join(loose)}")
    if re.search(r"\b(surviv|will succeed|guarantee)", text, re.I):
        problems.append("do not claim survival or success")
    return problems


def run(goal, cuisine, emit):
    """Returns (shortlist, summary, credits). Emits scout tool events."""
    inp = [{"role": "user", "content": f"Cuisine: {cuisine}.\nThe founder's plan: {goal}"}]
    found, seen, credits, calls, warned, places = {}, goal, 0.0, 0, set(), []
    for turn in range(1, MAX_CALLS + 4):
        emit({"type": "scout_think", "n": turn})
        t0 = time.time()
        body = {"model": llm.MODEL, "instructions": INSTRUCTIONS, "input": inp, "tools": TOOLS,
                "tool_choice": "required", "reasoning": {"effort": EFFORT}, "max_output_tokens": 3000}
        d = llm.hedged_response(body, on_hedge=lambda k: emit({"type": "scout_hedge", "n": turn, "attempt": k}))
        retried = d["attempts"] > 1 and f"answered by attempt {d['attempt']} of {d['attempts']}"
        credits += (d.get("credits") or 0) * d["kie_attempts"]  # every duplicate is billed
        fcs = [o for o in d.get("output", []) if o.get("type") == "function_call"]
        emit({"type": "scout_turn", "n": turn, "seconds": round(time.time() - t0, 1), "retried": retried,
              "calls": [f["name"] for f in fcs], "credits": d.get("credits"), "model": d.get("model")})
        if not fcs:
            inp.append({"role": "user", "content": "Use the tools, then finish with submit_shortlist."})
            continue
        for fc in fcs:
            args = json.loads(fc["arguments"] or "{}")
            if fc["name"] == "submit_shortlist":
                problems = check_shortlist(args, found, seen, warned)
                emit({"type": "scout", "status": "error" if problems else "done", "name": "submit_shortlist",
                      "summary": "; ".join(problems) if problems else f"{len(args['picks'])} storefronts shortlisted"})
                if not problems:
                    return [found[p["address"]] | {"reason": p["reason"], "picked_neighbourhood": p["neighbourhood"]}
                            for p in args["picks"]], args["summary"], credits
                out = {"error": "shortlist rejected: " + "; ".join(problems)}
            else:
                calls += 1
                if calls > MAX_CALLS:
                    out = {"error": "tool budget used up; submit the shortlist now"}
                else:
                    emit({"type": "scout", "status": "running", "name": fc["name"], "args": args, "n": calls})
                    t1 = time.time()
                    try:
                        out = run_tool(fc["name"], args, found, places)
                    except Exception as e:
                        out = {"error": str(e)[:200]}
                    seen += json.dumps(out)
                    emit({"type": "scout", "status": "error" if "error" in out else "done", "name": fc["name"],
                          "args": args, "n": calls, "seconds": round(time.time() - t1, 1),
                          "summary": followup.safe_summary(fc["name"], out, _summary)})
            inp += [{"type": "function_call", "call_id": fc["call_id"], "name": fc["name"], "arguments": fc["arguments"]},
                    {"type": "function_call_output", "call_id": fc["call_id"], "output": json.dumps(out)[:12000]}]
    raise llm.LLMError("scout did not finish a shortlist")


def _summary(name, out):
    if "error" in out:
        return out["error"]
    if name == "list_neighbourhoods":
        top = out["neighbourhoods"][:3]
        return f"ranked by {out['ranked_by']}: " + ", ".join(f"{r['neighbourhood']} ({r['value']})" for r in top)
    if name == "neighbourhood_profile":
        return f"profile of {out['name']}"
    return followup._summary(name, out)


def as_leases(shortlist):
    return [{"address": s["address"], "lat": s["lat"], "lon": s["lon"], "borough": s["borough"],
             "neighbourhood": s.get("neighbourhood"), "storefront": s.get("storefront"), "reason": s["reason"]}
            for s in shortlist]
