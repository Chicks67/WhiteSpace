"""Follow-up questions after a run: a tool-using loop (GPT-6 Astra function calling on Kie).

The model chooses which tools to call and in what order; code runs them on city records, the Storefront
Registry, Qloo and our committed test results. At most MAX_CALLS tool calls per question. Every number in
the final answer is checked against the tool outputs and the run context; unmatched numbers are flagged.
"""
import json
import re
import time

import census
import engine
import partners
import evidence
import llm
import positioning
import storefronts
import transit
import bids

MAX_CALLS = 6
KIE = "https://api.kie.ai/codex/v1/responses"

INSTRUCTIONS = (
    "You are Whitespace, an assistant for an independent restaurant founder choosing a lease in New York City. "
    "Answer the founder's follow-up question using the tools. Rules: take every number and every business name "
    "from tool results or the run context, never from memory; lease rankings come only from city records; "
    "rank_in_this_set compares only the leases in one result, so compare leases from different results or areas "
    "with lease_score_percentile_nyc (share of NYC restaurant blocks scoring lower for this cuisine); Qloo describes an area's audience and is never evidence of where to open; if the tools cannot "
    "answer, say so plainly. For who lives or works somewhere use neighbourhood_profile (census), never Qloo; for "
    "partners or cross-promotion use local_partners. Keep answers short (under 150 words), plain text, no markdown tables. "
    "Cuisines we tested: " + ", ".join(engine.CONCEPTS) + "."
)


def _fn(name, desc, props, req):
    return {"type": "function", "name": name, "description": desc, "strict": True,
            "parameters": {"type": "object", "properties": props, "required": req, "additionalProperties": False}}


S = {"type": "string"}
CUISINE = {"type": "string", "enum": list(engine.CONCEPTS)}
TOOLS = [
    _fn("find_storefronts", "Vacant storefronts reported in NYC's Storefront Registry in a neighbourhood or borough, "
        "best city-records lease score first (one per block).",
        {"cuisine": CUISINE, "area": {**S, "description": "neighbourhood or borough, e.g. 'Astoria' or 'the Bronx'"},
         "top": {"type": "integer", "description": "how many, 1 to 8"}}, ["cuisine", "area", "top"]),
    _fn("rank_addresses", "Score and rank 1 to 5 street addresses for a cuisine with the city-records lease score.",
        {"cuisine": CUISINE, "addresses": {"type": "array", "items": S}}, ["cuisine", "addresses"]),
    _fn("nearby_restaurants", "Restaurants of a cuisine near an address from NYC inspection records, with distance "
        "and opening date; use for competitors.",
        {"cuisine": CUISINE, "address": S, "radius_m": {"type": "integer", "description": "100 to 1500"}},
        ["cuisine", "address", "radius_m"]),
    _fn("area_profile", "Qloo: tags and brands the area around an address over-indexes on versus all of NYC, "
        "with items common to most neighbourhoods removed. Descriptive only.",
        {"cuisine": CUISINE, "address": S}, ["cuisine", "address"]),
    _fn("foot_traffic", "Average weekday subway entries at stations within 500 m of an address (MTA counts, "
        "September 2025): a proxy for foot traffic. Descriptive, not tested as a predictor.",
        {"address": S}, ["address"]),
    _fn("storefronts_near_place", "Vacant storefronts within a radius of a named place (a campus, station, park, "
        "landmark or address), best city-records lease score first, each with its walking-line distance to the place. "
        "Check matched_place: the geocoder can pick the wrong campus (e.g. NYU's Brooklyn campus); if so, call again "
        "with a more specific name such as 'Washington Square Park'.",
        {"place": S, "cuisine": CUISINE, "radius_m": {"type": "integer", "description": "200 to 1500"},
         "top": {"type": "integer", "description": "1 to 8"}}, ["place", "cuisine", "radius_m", "top"]),
    _fn("local_partners", "Real local businesses to approach near an address, from NYC Open Data: the nearest "
        "business improvement districts (with phone, email, website, distance) and independent complementary "
        "neighbours within 400 m (coffee, bakery, dessert, juice, bagels; kinds that would compete with the concept "
        "are left out). Use this for partnership or cross-promotion questions.",
        {"address": S, "cuisine": CUISINE, "concept": {**S, "description": "the founder's concept, e.g. 'Korean cafe'"}},
        ["address", "cuisine", "concept"]),
    _fn("neighbourhood_profile", "Census and jobs measures for one NYC neighbourhood (2020 NTA name, e.g. "
        "'Morningside Heights'), with NYC percentiles: residents, students, households with children, seniors, "
        "young adults, income, jobs density, visitors. Use this for who lives or works somewhere.",
        {"name": S}, ["name"]),
    _fn("lookup_business", "Check whether a named business appears in NYC inspection records near an address "
        "(within 2 km) or elsewhere in NYC.",
        {"name": S, "near_address": S}, ["name", "near_address"]),
    _fn("test_results", "Our pre-registered test results: how leases are ranked, whether Qloo taste predicts "
        "openings, where supply data comes from, how the brief uses Qloo. Give a cuisine to also get that "
        "cuisine's own numbers, which can differ from the median.",
        {"topic": {"type": "string", "enum": ["lease", "test1", "test2", "supply", "positioning"]},
         "cuisine": {"type": "string", "enum": ["all"] + list(engine.CONCEPTS)}}, ["topic", "cuisine"]),
]


def _point(address):
    label, boro, lat, lon, hood = engine.geocode(address)
    if boro and boro not in engine.BOROUGHS:
        raise engine.LeaseError(f"{label} is in {boro}, which our tests did not cover")
    return label, boro, lat, lon, hood


def _lease_view(l):
    return {"rank_in_this_set": l["rank"], "lease_score_percentile_nyc": l.get("score_percentile"), "address": l["address"], "restaurants_in_block": l["density"],
            "busier_than_pct_of_blocks": l["density_percentile"], "same_cuisine_in_and_around_block": l["same_cuisine_area"],
            "same_cuisine_within_400m": len(l["same_cuisine_400m"]), "opened_within_800m_since_2024": len(l["openings_800m"]),
            "subway_weekday_entries_within_500m": transit.near(l["lat"], l["lon"])["subway_entries_within_500m"],
            "business_improvement_district": (bids.bid_for(l["lat"], l["lon"]) or {}).get("bid"),
            **({"storefront": l["storefront"]} if l.get("storefront") else {})}


def storefronts_near_place(args):
    """Returns (tool output, ranked leases)."""
    cands = engine.places(args["place"])
    if not cands:
        return {"error": f"no place found for {args['place']!r}"}, []
    label, boro, lat, lon, _ = cands[0]
    r = max(200, min(1500, args["radius_m"]))
    found, info = storefronts.near_place(args["cuisine"], lat, lon, r, max(1, min(8, args["top"])))
    if not found:
        return {"matched_place": f"{label} ({boro})", "error": f"no vacant storefronts reported within {r} m"}, []
    dist = {f"{s['address']}, {s['borough']}": s["metres_to_place"] for s in found}
    ranked = engine.rank(args["cuisine"], storefronts.as_leases(found))
    return ({"matched_place": f"{label} ({boro})", "matched_point": [round(lat, 6), round(lon, 6)],
             "other_matches": [f"{c[0]} ({c[1]})" for c in cands[1:]],
             "radius_m": r, **info,
             "storefronts": [{**_lease_view(l), "metres_to_place": dist.get(l["address"])} for l in ranked]}, ranked)


def find_storefronts(args):
    """Returns (tool output, ranked leases with coordinates)."""
    places = storefronts.match_area(args["area"])
    if not places:
        return {"error": f"no neighbourhood matched '{args['area']}'"}, []
    found, info = storefronts.find(args["cuisine"], places, top=max(1, min(8, args["top"])))
    ranked = engine.rank(args["cuisine"], storefronts.as_leases(found))
    return ({"areas": [("all of " + b) if n == "*" else n for n, b in places], **info,
             "storefronts": [_lease_view(l) for l in ranked]}, ranked)


def run_tool(name, args):
    if name == "find_storefronts":
        return find_storefronts(args)[0]
    if name == "storefronts_near_place":
        return storefronts_near_place(args)[0]
    if name == "rank_addresses":
        ranked = engine.rank(args["cuisine"], [{"address": a} for a in args["addresses"][:5]])
        return {"leases": [_lease_view(l) for l in ranked]}
    if name == "nearby_restaurants":
        label, _, lat, lon, _ = _point(args["address"])
        r = max(100, min(1500, args["radius_m"]))
        near = engine.city().nearby(lat, lon, r, engine.CONCEPTS[args["cuisine"]][0])
        return {"address": label, "radius_m": r, "count": len(near),
                "restaurants": [{"name": x["name"], "metres": x["metres"], "first_inspected_as_new": x["opened"]} for x in near[:15]]}
    if name == "area_profile":
        label, boro, lat, lon, hood = _point(args["address"])
        _, items = positioning.evidence(engine.CONCEPTS[args["cuisine"]][1], lat, lon)
        groups = {}
        for x in items:
            groups.setdefault(x["group"], []).append(x["name"])
        return {"address": label, "area": positioning.area_name(lat, lon, boro, hood), "source": "Qloo, descriptive", **groups}
    if name == "foot_traffic":
        label, _, lat, lon, _ = _point(args["address"])
        return {"address": label, **transit.near(lat, lon)}
    if name == "local_partners":
        label, _, lat, lon, _ = _point(args["address"])
        near = partners.for_lease(args["cuisine"], lat, lon, args.get("concept", ""))
        return {"address": label, "business_improvement_districts": near["bids"],
                "complementary_neighbours": near["complements"], "source": "NYC Open Data (BIDs, restaurant inspections)"}
    if name == "neighbourhood_profile":
        prof = census.profiles()
        p = prof.get(args["name"]) or next((v for k, v in prof.items() if args["name"].lower() in k.lower()), None)
        if not p:
            return {"error": f"no neighbourhood named {args['name']!r}",
                    "did_you_mean": [k for k in prof if args["name"].lower().split()[0] in k.lower()][:5]}
        return {k: (round(100 * v, 1) if k.endswith("_share") and v is not None else v) for k, v in p.items()} | {
            "note": "values ending in _share are percentages; _pct fields are NYC percentiles among 181 neighbourhoods"}
    if name == "lookup_business":
        label, _, lat, lon, _ = _point(args["near_address"])
        where, hit = positioning.city_lookup(args["name"], lat, lon)
        return {"name": args["name"], "found": where or "not found in NYC inspection records", **({"match": hit} if hit else {})}
    if name == "test_results":
        p = evidence.panel()
        e = next(x for x in p["entries"] if x["id"] == args["topic"])
        out = {k: e[k] for k in ("title", "claim", "result", "caveat", "confidence")}
        c = args.get("cuisine", "all")
        if c in engine.CONCEPTS:
            dohmh = engine.CONCEPTS[c][0]
            t1 = next((r for r in p["per_cuisine"] if r["cuisine"] == dohmh), None)
            t4 = next((r for r in p["chart"] if r["cuisine"] == dohmh), None)
            out["this_cuisine"] = {
                "cuisine": c,
                "test1_blocks_without_the_cuisine_auc": t1 and {"restaurant_count": t1["B1"], "nearby_same_cuisine_supply": t1["B2"],
                                                              "qloo_raw_taste": t1["M1"], "qloo_peer_lift_taste": t1["M2"]},
                "test4_all_blocks_auc": t4 and {"city_records_lease_score": t4["city"], "restaurant_count_alone": t4["D"],
                                               "qloo_raw_taste": t4["qloo"], "lease_score_plus_qloo": t4["DSQ"]},
                "note": "AUC within this cuisine; 0.5 is a coin flip. Test 4's decision used the mean over all 14 cuisines.",
            }
        return out
    return {"error": f"unknown tool {name}"}


def _canon(x):
    """'0.860' and '0.86' are the same number; '13' stays '13'."""
    return x.rstrip("0").rstrip(".") if "." in x else (x.lstrip("0") or "0")


def _numbers(s):
    return {_canon(x) for x in re.findall(r"\d+(?:\.\d+)?", s.replace(",", ""))}


def ask(question, context, history, emit):
    """context: compact JSON of the current run; history: [{"q":..., "a":...}] of earlier follow-ups."""
    inp = [{"role": "user", "content": "Run context:\n" + json.dumps(context)}]
    for h in history[-4:]:
        inp += [{"role": "user", "content": h["q"]}, {"role": "assistant", "content": h["a"]}]
    inp.append({"role": "user", "content": question})
    seen, credits, calls = json.dumps(context) + json.dumps(history[-4:]), 0.0, 0
    for _ in range(MAX_CALLS + 1):
        body = {"model": llm.MODEL, "instructions": INSTRUCTIONS, "input": inp, "tools": TOOLS,
                "tool_choice": "auto" if calls < MAX_CALLS else "none", "stream": False,
                "reasoning": {"effort": "low"}, "max_output_tokens": 1500}
        d = llm.hedged_response(body)  # a duplicate starts if Kie stalls; the first to finish wins
        credits += (d.get("credits") or 0) * d["kie_attempts"]
        fcs = [o for o in d.get("output", []) if o.get("type") == "function_call"]
        if not fcs:
            answer = llm._text(d).strip()
            if not answer:
                if calls >= MAX_CALLS or _ == MAX_CALLS:
                    raise llm.LLMError("the model returned no answer")
                inp.append({"role": "user", "content": "Please answer the question now in plain text."})
                continue
            loose = sorted(_numbers(answer) - _numbers(seen) - _numbers(question), key=float)
            emit({"type": "answer", "text": answer, "unchecked_numbers": loose, "tool_calls": calls,
                  "credits": round(credits, 2)})
            return credits
        for fc in fcs:
            calls += 1
            args = json.loads(fc["arguments"] or "{}")
            emit({"type": "tool", "status": "running", "name": fc["name"], "args": args, "n": calls})
            t1 = time.time()
            try:
                out = run_tool(fc["name"], args)
            except Exception as e:
                out = {"error": str(e)[:200]}
            seen += json.dumps(out)
            emit({"type": "tool", "status": "error" if "error" in out else "done", "name": fc["name"], "args": args,
                  "n": calls, "seconds": round(time.time() - t1, 1), "summary": safe_summary(fc["name"], out)})
            inp += [{"type": "function_call", "call_id": fc["call_id"], "name": fc["name"], "arguments": fc["arguments"]},
                    {"type": "function_call_output", "call_id": fc["call_id"], "output": json.dumps(out)[:12000]}]
    raise llm.LLMError("tool loop did not finish")


def safe_summary(name, out, fn=None):
    """A one-line trace summary; never lets a formatting slip end the run."""
    try:
        return (fn or _summary)(name, out)
    except Exception:  # noqa: BLE001
        return ""


def _summary(name, out):
    if "error" in out:
        return out["error"]
    if name == "storefronts_near_place":
        return f"{out['storefronts_within_radius']} vacant storefronts within {out['radius_m']} m of {out['matched_place']}; best: " + \
               ", ".join(s["address"] for s in out["storefronts"][:3])
    if name == "find_storefronts":
        return f"{out['storefronts_in_area']} vacant storefronts in {', '.join(out['areas'])}; best: " + \
               ", ".join(s["address"] for s in out["storefronts"][:3])
    if name == "rank_addresses":
        return "; ".join(f"{l['rank']}. {l['address']}" for l in out["leases"])
    if name == "nearby_restaurants":
        return f"{out['count']} within {out['radius_m']} m of {out['address']}"
    if name == "area_profile":
        return f"Qloo profile for {out['area']}"
    if name == "lookup_business":
        return f"{out['name']}: {out['found']}"
    if name == "foot_traffic":
        return f"{out['subway_entries_within_500m']} weekday subway entries within 500 m of {out['address']}"
    if name == "test_results":
        return out["title"]
    return ""


def compact_context(events):
    """Build the run context the client sends back with each follow-up from the run's events."""
    ctx = {}
    for e in events:
        if e.get("type") == "scout_result":
            ctx["order"] = ("the scout's shortlist order: it weighs the founder's plan (target customers, competition, "
                            "subway, street) as well as the lease score, so it need not follow lease_score_percentile_nyc")
            ctx["scout_summary"] = e["data"].get("summary")
        if e.get("type") == "concept":
            ctx["concept"] = e["data"]["label"]; ctx["cuisine"] = e["data"]["cuisine"]
        if e.get("type") == "leases":
            ctx["leases"] = [_lease_view(l) for l in e["data"]]
        if e.get("type") == "brief":
            ctx["brief_area"] = e["data"]["area"]; ctx["brief"] = e["data"]["text"][:2500]
    return ctx


if __name__ == "__main__":
    g = json.load(open("golden/korean-cafe-queens.json"))
    ctx = compact_context([e for _, e in g["events"]])
    for q in ["Who are the Korean competitors within 300 m of the top lease?",
              "Would Astoria be a better area? Find me vacant storefronts there."]:
        print("Q:", q)
        ask(q, ctx, [], lambda e: print("  ", e["text"] if e["type"] == "answer" else json.dumps(e)[:200], e.get("unchecked_numbers", "")))
