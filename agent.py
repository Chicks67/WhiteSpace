"""The Whitespace agent: a fixed workflow with bounded agency.

Steps: resolve concept (LLM) -> rank leases (code, city records) -> fetch Qloo evidence (code)
-> recover thin evidence (LLM picks a wider radius, at most 3 tries) -> write brief (LLM)
-> verify (code; one rewrite on failure). Every step and every Qloo call is emitted as an event.
"""
import re
import time

import blind_test as bt
import engine
import llm
import positioning
import qloo
import scout
import bids
import next_steps
import partners
import storefronts
import transit

RESOLVE_INSTRUCTIONS = (
    "You map a restaurant founder's concept to the closest cuisine category in a fixed list. "
    f"Allowed cuisines: {', '.join(engine.CONCEPTS)}. "
    "If none is a reasonable match, use null. Also return a short clean concept label (at most 5 words) "
    'and one short sentence explaining the match. Reply as {"cuisine": "...", "label": "...", "reason": "..."}.'
)
RECOVER_INSTRUCTIONS = (
    "You are checking whether neighbourhood taste evidence is rich enough to write a positioning brief. "
    "Each group should have at least 3 items. You may widen the search radius around the address. "
    'Reply as {"action": "accept"} or {"action": "widen", "metres": 800 or 1500 or 3000, "reason": "..."}. '
    "Prefer the smallest radius likely to fill the thin groups; accept if widening already failed."
)
MAX_RECOVER = 3
MAX_REPAIR = 2
AREA_INSTRUCTIONS = (
    "You map a founder's description of where they want to open to neighbourhood names from a fixed list "
    "(NYC 2020 Neighborhood Tabulation Areas in Brooklyn, Queens, Manhattan and the Bronx). Handle nicknames and "
    "abbreviations (for example LIC, Bed-Stuy, UES). Pick at most 4 names, exactly as written in the list, "
    'or an empty list if nothing matches. Reply as {"areas": ["..."], "reason": "..."}.'
)
# Unambiguous words resolve in code; anything else goes to the model.
ALIASES = {
    "korean": "Korean", "mexican": "Mexican", "taqueria": "Mexican", "taco": "Mexican",
    "japanese": "Japanese", "ramen": "Japanese", "sushi": "Japanese", "izakaya": "Japanese",
    "thai": "Thai", "indian": "Indian", "caribbean": "Caribbean", "jamaican": "Caribbean",
    "trinidadian": "Caribbean", "chinese": "Chinese", "dim sum": "Chinese", "pizza": "Pizza",
    "pizzeria": "Pizza", "italian": "Italian", "mediterranean": "Mediterranean", "greek": "Mediterranean",
    "latin american": "Latin American", "middle eastern": "Middle Eastern", "lebanese": "Middle Eastern",
    "bakery": "Bakery", "patisserie": "Bakery", "coffee": "Coffee shop", "cafe": "Coffee shop",
    # dishes and styles founders type (checked against a list of 66 realistic phrasings, Oct 11)
    "bibimbap": "Korean", "bulgogi": "Korean", "kimbap": "Korean",
    "burrito": "Mexican", "tamale": "Mexican", "birria": "Mexican",
    "omakase": "Japanese", "udon": "Japanese", "soba": "Japanese", "yakitori": "Japanese", "tempura": "Japanese",
    "dosa": "Indian", "biryani": "Indian", "tandoor": "Indian", "chaat": "Indian", "masala": "Indian",
    "haitian": "Caribbean", "guyanese": "Caribbean", "west indian": "Caribbean", "jerk": "Caribbean",
    "cantonese": "Chinese", "sichuan": "Chinese", "szechuan": "Chinese", "hot pot": "Chinese",
    "hand-pulled": "Chinese", "dumpling": "Chinese", "xiao long bao": "Chinese",
    "slice shop": "Pizza", "pasta": "Italian", "trattoria": "Italian", "osteria": "Italian",
    "falafel": "Middle Eastern", "shawarma": "Middle Eastern",
    "dominican": "Latin American", "colombian": "Latin American", "puerto rican": "Latin American",
    "salvadoran": "Latin American", "pupusa": "Latin American", "arepa": "Latin American",
    "empanada": "Latin American", "venezuelan": "Latin American", "ecuadorian": "Latin American",
    "cuban": "Latin American", "espresso": "Coffee shop", "boba": "Coffee shop", "bubble tea": "Coffee shop",
    "pastry": "Bakery", "croissant": "Bakery",
    # Test 4b cuisines (PREREGISTRATION_6.md)
    "american": "American", "diner": "American", "bbq": "American", "barbecue": "American", "brunch": "American",
    "new american": "New American", "farm-to-table": "New American",
    "chicken": "Chicken", "wings": "Chicken", "burger": "Burgers", "sandwich": "Sandwich shop", "deli": "Sandwich shop",
    "hero shop": "Sandwich shop", "seafood": "Seafood", "oyster": "Seafood", "fish market": "Seafood",
    "spanish": "Spanish", "tapas": "Spanish", "paella": "Spanish", "asian fusion": "Asian fusion",
    "juice": "Juice bar", "smoothie": "Juice bar", "acai": "Juice bar",
    "ice cream": "Ice cream and frozen desserts", "gelato": "Ice cream and frozen desserts",
    "frozen yogurt": "Ice cream and frozen desserts", "froyo": "Ice cream and frozen desserts",
    "bagel": "Bagel shop",
}
# Inspection-record categories we did not test: stop at once with a clear message, no model call.
UNTESTED = {"vietnamese": "Vietnamese", "pho": "Vietnamese", "banh mi": "Vietnamese", "ethiopian": "Ethiopian",
            "filipino": "Filipino", "steakhouse": "steakhouse", "donut": "donut", "doughnut": "donut",
            "peruvian": "Peruvian", "turkish": "Turkish", "kebab": "Turkish", "french": "French", "bistro": "French",
            "greek": "Greek", "kosher": "Kosher", "tex-mex": "Tex-Mex"}
# Broad words: a specific cuisine in the same text wins ("Korean cafe" is Korean, "Korean fried chicken" is
# Korean, "Latin American" is Latin American, "Japanese seafood" is Japanese, "New American" is New American)
GENERIC = {"Coffee shop", "Bakery", "American", "Chicken", "Sandwich shop", "Seafood", "Juice bar",
           "Ice cream and frozen desserts", "Burgers"}


def match_rule(text):
    t = " " + text.lower().replace("caf\u00e9", "cafe") + " "
    hits = {c for w, c in ALIASES.items() if f" {w}" in t}
    specific = hits - GENERIC
    if len(specific) == 1:
        return specific.pop()
    if not specific and len(hits) == 1:
        return hits.pop()
    return None


def _check_resolve(o):
    if o.get("cuisine") is not None and o["cuisine"] not in engine.CONCEPTS:
        raise ValueError(f"cuisine must be one of the allowed list or null, got {o['cuisine']!r}")
    if not isinstance(o.get("label"), str) or not o["label"].strip():
        raise ValueError("label missing")


def _check_recover(o):
    if o.get("action") == "accept":
        return
    if o.get("action") != "widen" or o.get("metres") not in (800, 1500, 3000):
        raise ValueError("action must be accept, or widen with metres 800, 1500 or 3000")


class Run:
    def __init__(self, emit):
        self.emit, self.credits = emit, 0.0

    def step(self, sid, label, fn, detail=None):
        t = time.time()
        self.emit({"type": "step", "id": sid, "label": label, "status": "running"})
        try:
            out, info = fn()
        except Exception as e:
            self.emit({"type": "step", "id": sid, "label": label, "status": "error", "detail": str(e)[:300]})
            raise
        self.emit({"type": "step", "id": sid, "label": label, "status": "done",
                   "seconds": round(time.time() - t, 1), "detail": info})
        return out

    def llm_json(self, instructions, prompt, check, effort="low"):
        obj, meta = llm.complete_json(instructions, prompt, check=check, effort=effort)
        self.credits += meta.get("credits") or 0
        return obj, meta


GAPS = [  # what a founder may ask for that no data here measures; shown on the page with every shortlist
    (r"rent|cheap|afford|lease cost|low cost|budget-friendly",
     "Rent: we have no rent data. The shortlist ranks by cuisine fit, competition, target customers and foot traffic "
     "only; get a rent quote from a broker for each address."),
    (r"late[- ]night|nightlife|\bbars?\b|after hours|open late|hours",
     "Late-night demand: we have no opening-hours or nightlife data, so late-night trade is not measured."),
    (r"up[- ]and[- ]coming|gentrif|emerging|trending|growing",
     "Neighbourhood change: we do not measure whether an area is up-and-coming."),
    (r"parking|delivery|ghost kitchen|catering",
     "Parking and delivery demand are not measured."),
]


def not_measured(goal):
    return [msg for pat, msg in GAPS if re.search(pat, goal, re.I)]


def run(req, emit):
    """req: {"concept": str, "cuisine": optional str, "leases": [{"address"...}]}"""
    r = Run(emit)
    qloo.set_trace(lambda path, params, status, cached: emit({
        "type": "qloo", "path": path, "status": status, "cached": cached,
        "params": {k: v for k, v in params.items() if k != "filter.results.entities" and k != "filter.results.tags"}}))
    try:
        concept_text = req["concept"].strip()[:60]

        def resolve():
            if req.get("cuisine") in engine.CONCEPTS:
                return {"cuisine": req["cuisine"], "label": concept_text, "reason": "chosen by the user"}, "user choice"
            rule = match_rule(concept_text)
            low = " " + concept_text.lower() + " "
            untested = next((v for k, v in UNTESTED.items() if f" {k}" in low), None)
            if untested and not rule:
                raise ValueError(f"'{concept_text}' does not match any of the {len(engine.CONCEPTS)} cuisines we tested ({untested} "
                                 f"was not one of them): {', '.join(engine.CONCEPTS)}")
            if rule:
                return {"cuisine": rule, "label": concept_text, "reason": f"matched by keyword to {rule}"}, "keyword match"
            o, m = r.llm_json(RESOLVE_INSTRUCTIONS, f"Concept: {concept_text}", _check_resolve)
            if o["cuisine"] is None:
                raise ValueError(f"'{concept_text}' does not match any of the {len(engine.CONCEPTS)} cuisines we tested")
            return o, o["reason"]
        concept = r.step("resolve", "Match concept to a tested cuisine", resolve)
        emit({"type": "concept", "data": concept})
        cuisine, label = concept["cuisine"], concept["label"]

        if req.get("goal") and not req.get("leases"):
            goal = req["goal"].strip()[:400]
            boros = [b for b in engine.BOROUGHS if re.search(r"\b" + b + r"\b", goal, re.I)]
            if re.search(r"staten\s+island", goal, re.I) and not boros:
                raise ValueError("Staten Island is not covered: the city publishes data for it, but our pre-registered "
                                 "tests ran only on Brooklyn, Queens, Manhattan and the Bronx, so we did not load it and "
                                 "will not rank storefronts there")
            gaps = not_measured(goal)

            def scouting():
                picks, summary, spent = scout.run(goal + ("\n\nNot measured by any tool here: " + " ".join(gaps)
                                                          if gaps else ""), cuisine, emit)
                r.credits += spent
                return (picks, summary), f"{len(picks)} storefronts shortlisted"
            picks, summary = r.step("scout", "Scout neighbourhoods and storefronts for your plan", scouting)
            emit({"type": "scout_result", "data": {"summary": summary, "not_measured": gaps,
                  "picks": [{"address": p["address"], "neighbourhood": p.get("picked_neighbourhood"), "reason": p["reason"]}
                            for p in picks]}})
            req = {**req, "leases": scout.as_leases(picks)}
        elif not req.get("leases"):
            area_text = req["area"].strip()[:80]

            def where():
                places = storefronts.match_area(area_text)
                how = "name match"
                if not places:
                    names = sorted({f"{n} ({b})" for n, b in storefronts.areas()})
                    known = {f"{n} ({b})": (n, b) for n, b in storefronts.areas()}
                    def check(o):
                        if not isinstance(o.get("areas"), list) or any(x not in known for x in o["areas"]):
                            raise ValueError("areas must be names copied exactly from the list")
                    o, _ = r.llm_json(AREA_INSTRUCTIONS, f"Founder wrote: {area_text}\n\nList:\n" + "\n".join(names), check)
                    places, how = [known[x] for x in o["areas"]], "model match: " + o.get("reason", "")
                if not places:
                    raise ValueError(f"could not match '{area_text}' to a neighbourhood in Brooklyn, Queens, Manhattan or the Bronx")
                return places, f"{how}: " + ", ".join(("all of " + b) if n == "*" else n for n, b in places)
            places = r.step("area", "Match the area to city neighbourhoods", where)

            def find():
                found, info = storefronts.find(cuisine, places, top=req.get("top", 5))
                return found, (f"{info['storefronts_in_area']} vacant storefronts reported across {info['blocks_in_area']} "
                               f"blocks; kept the best-scoring one per block")
            found = r.step("find", "Find vacant storefronts in NYC's Storefront Registry", find)
            emit({"type": "storefronts", "data": {"area": area_text, "places": places}})
            req = {**req, "leases": storefronts.as_leases(found)}

        leases = r.step("rank", "Rank leases on city inspection records",
                        lambda: (lambda L: (L, f"{len(L)} leases scored"))(
                            engine.rank(cuisine, req["leases"], keep_order=bool(req.get("goal")))))
        for l in leases:
            l["subway"] = transit.near(l["lat"], l["lon"])
            l["bid"] = bids.bid_for(l["lat"], l["lon"])
            l["partners"] = partners.for_lease(cuisine, l["lat"], l["lon"], req.get("concept", ""))
            l["next_steps"] = next_steps.for_lease(l)
        emit({"type": "leases", "data": leases})
        emit({"type": "taste", "data": engine.taste(cuisine, leases)})

        top = leases[0]
        slug = engine.CONCEPTS[cuisine][1]
        area = positioning.area_name(top["lat"], top["lon"], top["borough"], top.get("neighbourhood"))

        def fetch():
            point, items = positioning.evidence(slug, top["lat"], top["lon"])
            return (point, items), _counts(items)
        point, items = r.step("evidence", f"Fetch Qloo audience evidence for {area}", fetch)

        for attempt in range(MAX_RECOVER):
            counts = _counts(items)
            if all(n >= 3 for n in counts.values()):
                break
            def recover():
                o, _ = r.llm_json(RECOVER_INSTRUCTIONS, f"Group sizes: {counts}. Attempt {attempt + 1} of {MAX_RECOVER}.",
                                  _check_recover)
                if o["action"] == "accept":
                    return None, "accepted thin evidence"
                _, new = positioning.evidence(slug, top["lat"], top["lon"], radius=o["metres"])
                return new, f"widened to {o['metres']} m: {_counts(new)}"
            new = r.step(f"recover{attempt + 1}", "Evidence is thin: decide whether to widen", recover)
            if new is None:
                break
            items = new
        emit({"type": "evidence", "data": {"area": area, "point": point, "items": items}})

        def write():
            buf, last = [], [0.0]

            def on_delta(d):
                if d is None:
                    buf.clear(); emit({"type": "brief_delta", "reset": True}); return
                buf.append(d)
                if time.time() - last[0] > 0.3:  # coalesce deltas so the stream stays light
                    emit({"type": "brief_delta", "text": "".join(buf)}); buf.clear(); last[0] = time.time()
            text, meta = positioning.write_brief(label, area, items, on_delta)
            if buf:
                emit({"type": "brief_delta", "text": "".join(buf)})
            r.credits += meta.get("credits") or 0
            via = f", attempt {meta['attempt']}" if meta.get("attempt", 1) > 1 else ""
            return text, f"{meta['seconds']} s{via}"
        text = r.step("write", "Write positioning brief (GPT-6 Astra)", write)

        def verify():
            out = positioning.verify(text, items, top["lat"], top["lon"], req.get("goal", ""))
            r.credits += out.pop("credits", 0)
            return out, ("passed" if not out["problems"] else "problems: " + ", ".join(out["problems"]))
        result = r.step("verify", "Verify brief", verify)
        if result["problems"]:
            text = r.step("rewrite", "Rewrite once after failed check", write)
            result = r.step("verify2", "Verify rewrite", verify)
        result["unverified_before_repair"] = list(result["unverified_names"])
        for attempt in range(MAX_REPAIR):
            if not result["unverified_names"]:
                break
            bad = result["unverified_names"]

            def fix():
                new, meta = positioning.repair(text, bad, items)
                r.credits += meta.get("credits") or 0
                return new, f"replaced {', '.join(bad)}"
            try:
                text = r.step(f"repair{attempt + 1}", "Replace names no source backs up", fix)
            except Exception:  # the model's repair failed its checks: drop those sentences in code instead
                text = r.step(f"drop{attempt + 1}", "Remove sentences naming businesses no source backs up",
                              lambda: (positioning.drop_unverified(text, bad), f"removed sentences naming {', '.join(bad)}"))
            before = result["unverified_before_repair"]
            result = r.step(f"verify_repair{attempt + 1}", "Verify repaired brief", verify)
            result["unverified_before_repair"] = before
        emit({"type": "brief", "data": {"area": area, "concept": label, "lease": top["address"], **result}})
        # credits are token-based estimates in Kie units; on CometAPI ($8 / $40 per M tokens) 1 unit is about $0.0142
        emit({"type": "done", "credits": round(r.credits, 2), "provider": llm.PROVIDER,
              **({"usd": round(r.credits * 0.0142, 2)} if llm.PROVIDER == "comet" else {})})
    except Exception as e:
        msg = str(e)
        detail = msg[:300]
        if llm.busy(msg):
            msg = "The language model is busy with other runs right now. Please try again in a minute; the saved runs work meanwhile."
        elif llm.out_of_budget(msg):
            msg = "Live runs are paused right now (the language model's budget for the demo is used up). The saved runs still work."
        emit({"type": "error", "message": msg[:300], "detail": detail})
    finally:
        qloo.set_trace(None)
    return r.credits


def _counts(items):
    return {g: sum(1 for x in items if x["id"].startswith(p)) for g, p in
            (("tags", "T"), ("brands", "B"), ("concept_brands", "C"))}


if __name__ == "__main__":
    import json
    run({"concept": "Korean cafe", "leases": [{"address": "136-20 38th Ave, Queens"},
                                              {"address": "41-08 Bell Blvd, Queens"}]},
        lambda e: print(json.dumps(e)[:300]) if e["type"] != "qloo" else None)
