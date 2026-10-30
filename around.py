"""What is around a storefront. City inspection records define who the competitors are; Qloo adds price level,
Friday closing time and review keywords to the ones it holds, and ranks the neighbours for fans of the cuisine.
The wording follows Test 10's bands (PREREGISTRATION_10.md): Qloo's list holds under half of the city's
competitors, so no absence claim is made, and a Qloo place is named only if it has an active city record.
Same data as Test 9's arm Q, as structured fields for the page. No model call.
"""
import re

import backtest10 as b10
import engine
import qloo
import test9_dev as t9

NOTES = [
    "Competitors come from city inspection records. In our Test 10, Qloo's same-cuisine list held 37% of them, so "
    "details appear only where a place matches, and nothing here says what the other competitors serve, charge or "
    "when they close.",
    "Closing times are Qloo's. In our Test 12 a person looked up 40 of these places on Google Maps: Qloo's Friday "
    "closing time matched Google's for 29 of the 30 places used for the decision, and 2 of the 40 were marked "
    "permanently closed on Google.",
    "Price levels are not shown. In the same test Qloo's level equalled the price band Google shows for 17 of 27 "
    "places, under our bar of 70%, though it was never more than one level away.",
    "Review mentions are Qloo's too. We have not checked those against another source.",
    "A place Qloo lists is named here only if city inspection records also hold it.",
]


def _detail(x):
    p = x.get("properties", {})
    return {"qloo_name": x["name"], "address": p.get("address"), "closes_friday": t9.closes(p),
            "open_late_friday": t9.late(t9.closes(p)), "kind": t9.genre(x),
            "mentions": [k["name"] for k in p.get("keywords") or [] if k.get("name", "").lower() not in t9.JUNK][:5],
            "description": (p.get("short_description") or "").strip() or None}


def for_point(concept, lat, lon, take=15):
    c = {"concept": concept, "slug": engine.CONCEPTS[concept][1], "lat": round(lat, 4), "lon": round(lon, 4)}
    point = f"POINT({c['lon']:.4f} {c['lat']:.4f})"
    tag = f"urn:tag:genre:place:restaurant:{c['slug']}"
    cat = engine.CONCEPTS[concept][0]
    city_all = b10.city_list(c)
    city_cat = sorted((x for x in city_all if x["cuisine"] == cat and x["metres"] <= b10.NEAR), key=lambda x: x["metres"])
    q = []
    for page in range(1, 5):
        rows = qloo.results(qloo.get("/v2/insights", **{"filter.type": "urn:entity:place", "filter.tags": tag, "filter.location": point,
                                                        "filter.location.radius": b10.WIDE, "take": 50, "page": page}), "entities")
        q += [x for x in rows if not x.get("properties", {}).get("is_closed")]
        if len(rows) < 50:
            break
    q = t9.located(q)
    near = city_cat[:take]
    m = t9.pair(near, q)
    name = lambda x: re.sub(r"(?<=\w)'S\b", "'s", x["name"].title())
    known = [q[j]["raw"] for j in m.values()]
    last = t9.latest(known)
    rest = [x for j, x in enumerate(q) if j not in m.values() and engine.metres(c["lat"], c["lon"], x["lat"], x["lon"]) <= b10.NEAR]
    alive = t9.pair(rest, city_all)
    taken = {x["raw"]["entity_id"] for x in q}
    loved = t9.located([x for x in t9.places(point, 20, 800, **{"signal.interests.tags": tag})
                        if x["entity_id"] not in taken and t9.food(x)])
    ok = t9.pair(loved, city_all)
    return {
        "concept": concept, "lat": c["lat"], "lon": c["lon"],
        "competitors_in_city_records": len(city_cat),
        "competitors": [{"name": name(x), "metres": round(x["metres"]), "lat": x["lat"], "lon": x["lon"],
                         "qloo": _detail(q[m[i]]["raw"]) if i in m else None} for i, x in enumerate(near)],
        "with_details": len(known),
        "among_details": {"mentions": t9.known_for(known),
                          "latest_friday_close": last[0] if last else None, "with_hours": last[1] if last else 0},
        "also_tagged": [{"name": x["name"], "lat": x["lat"], "lon": x["lon"], **_detail(x["raw"])}
                        for i, x in enumerate(rest) if i in alive][:8],
        "neighbours": [{"name": x["name"], "lat": x["lat"], "lon": x["lon"], **_detail(x["raw"])}
                       for i, x in enumerate(loved) if i in ok][:10],
        "unconfirmed": [x["name"] for i, x in enumerate(loved) if i not in ok][:5],
        "notes": NOTES,
    }
