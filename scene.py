"""Taste anchors: a founder names places their customers already love; Qloo returns each place's scene (the
places its fans also go). Entity-to-entity affinity, not a location signal. Whether a scene may be shown as
taste is set by Test 11 (PREREGISTRATION_11.md); the lease ranking stays the city-records score.
"""
import backtest10 as b10
import engine
import qloo

NYC = "40.7128,-74.0060"
NEAR = 1500
# How a scene may be described is set by Test 11's band (backtest11_results.json); see PREREGISTRATION_11.md.
LABELS = {
    "specific and follows category": ("Places these restaurants' fans also go", True),
    "specific, not validated": ("Qloo's list of related places, not validated", False),
    "mostly location": ("Popular near these places", False),
}


def band():
    import json
    import os
    path = os.path.join(os.path.dirname(__file__), "backtest11_results.json")
    return json.load(open(path))["band"] if os.path.exists(path) else "specific, not validated"


def search(name, lat=None, lon=None, take=5):
    """Qloo place search by name, near a point if given, else across the city."""
    where = {"filter.location": f"{lat:.5f},{lon:.5f}", "filter.radius": 1} if lat is not None else \
            {"filter.location": NYC, "filter.radius": 30}
    d = qloo.get("/search", query=name, types="urn:entity:place", take=take, **where)
    return [h for h in d.get("results") or [] if (h.get("location") or {}).get("lat") is not None]


def resolve_at(name, lat, lon):
    """The Qloo place for a known restaurant: Test 10's rule (same name, within 200 m)."""
    for h in search(name, lat, lon):
        if b10.same_name(h.get("name", ""), name) and \
                engine.metres(lat, lon, float(h["location"]["lat"]), float(h["location"]["lon"])) <= b10.PAIR:
            return h
    return None


def scene(entity_ids, take=30, skip=()):
    """Places across NYC with the highest affinity to these entities, best first."""
    d = qloo.get("/v2/insights", **{"filter.type": "urn:entity:place", "signal.interests.entities": ",".join(entity_ids),
                                    "filter.location.query": "New York City", "take": take + len(skip) + len(entity_ids)})
    out = []
    for x in qloo.results(d, "entities"):
        loc = x.get("location") or {}
        if x["entity_id"] in skip or x["entity_id"] in entity_ids or loc.get("lat") is None:
            continue
        p = x.get("properties", {})
        out.append({"id": x["entity_id"], "name": x["name"], "lat": float(loc["lat"]), "lon": float(loc["lon"]),
                    "affinity": round(x.get("query", {}).get("affinity", 0), 3), "address": p.get("address"), "raw": x})
    return out[:take]


def taste(entity_ids, kind, take=8):
    """Names from another domain (artist, brand, podcast, tv_show) with the highest affinity to these entities."""
    import blind_test as bt
    d = qloo.get("/v2/insights", **{"filter.type": f"urn:entity:{kind}", "signal.interests.entities": ",".join(entity_ids),
                                    "take": take + 4})
    names = [x["name"] for x in qloo.results(d, "entities") if not any(b in x["name"].lower() for b in bt.BLOCK)]
    return list(dict.fromkeys(names))[:take]


def for_anchors(names, take=40):
    """The feature's whole answer for up to 3 places a founder names. No model call.
    Each scene place carries its neighbourhood and whether city inspection records hold it (Test 10's rule for
    naming a place as operating)."""
    import positioning
    import test9_dev
    found, missing = [], []
    for n in names[:3]:
        hits = search(n)
        best = next((h for h in hits if b10.same_name(h.get("name", ""), n)), hits[0] if hits else None)
        if best:
            found.append({"asked": n, "id": best["entity_id"], "name": best["name"], "address": best.get("properties", {}).get("address"),
                          "lat": float(best["location"]["lat"]), "lon": float(best["location"]["lon"])})
        else:
            missing.append(n)
    label, for_areas = LABELS[band()]
    out = {"anchors": found, "not_found": missing, "label": label, "band": band(), "may_choose_neighbourhoods": for_areas,
           "places": [], "neighbourhoods": [], "taste": {}}
    if not found:
        return out
    ids = [a["id"] for a in found]
    sc = scene(ids, take)
    city, nta = engine.city(), positioning.nta()
    for x in sc:
        d = min(engine.metres(a["lat"], a["lon"], x["lat"], x["lon"]) for a in found)
        near = [{"name": r["dba"], "lat": r["lat"], "lon": r["lon"]} for r in city.by_cell.get(engine.g6(x["lat"], x["lon"]), [])]
        near += [{"name": r["dba"], "lat": r["lat"], "lon": r["lon"]} for c in engine.neighbours(engine.g6(x["lat"], x["lon"]))
                 for r in city.by_cell.get(c, [])]
        p = x["raw"].get("properties", {})
        out["places"].append({"name": x["name"], "lat": x["lat"], "lon": x["lon"], "address": x["address"], "affinity": x["affinity"],
                              "metres_from_nearest_anchor": round(d), "neighbourhood": nta.name(x["lat"], x["lon"]),
                              "in_city_records": bool(test9_dev.pair([x], near)), "kind": test9_dev.genre(x["raw"])})
    out["share_within_1500m_of_an_anchor"] = round(sum(p["metres_from_nearest_anchor"] <= NEAR for p in out["places"])
                                                   / max(len(out["places"]), 1), 2)
    # Test 11: 46 of 120 sampled restaurants got one and the same list of city landmarks (parks, airports, arenas):
    # Qloo's answer when it holds no signal for a place. A scene that is mostly not food and drink is that list.
    if sum(test9_dev.food(x["raw"]) for x in sc) < len(sc) / 2:
        out.update(places=[], no_signal=True, note="Qloo holds too little about these places to say where their fans "
                   "also go. Try a better-known place your customers love.")
        return out
    if for_areas:  # only a validated scene may point at neighbourhoods (Test 11's rule)
        count = {}
        for p in out["places"]:
            if p["neighbourhood"]:
                count[p["neighbourhood"]] = count.get(p["neighbourhood"], 0) + 1
        out["neighbourhoods"] = [{"neighbourhood": k, "scene_places": v} for k, v in sorted(count.items(), key=lambda kv: -kv[1])]
    # Podcasts are left out: across five unlike seeds the same seven shows came back for three or more of them
    # (mean pairwise overlap 0.28, against 0.02 for artists and 0.17 for brands; exploratory, Oct 12).
    out["taste"] = {k: taste(ids, k) for k in ("artist", "brand")}
    return out
