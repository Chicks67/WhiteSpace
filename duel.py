"""The Test 20 duel, live: ask the model when a real place closes on Friday, alone and with Qloo's record.

Same instructions as Test 20 (PREREGISTRATION_20.md, test20.py). In that test, with Google Maps as the reference,
GPT-6 Astra was right for 0 of 30 places alone and 29 of 30 with Qloo's record. Here the page shows both answers
next to Qloo's record for a place the founder picks; no live answer is checked against Google.
"""
import threading

import backtest10 as b10
import engine
import llm
import scene
import test9_dev as t9

# Test 20's wording, unchanged
ALONE = ("You are asked about one restaurant in New York City. Answer with the time it closes on Friday, in 24-hour "
         'HH:MM. If you do not know, say so: do not guess. Reply as {"closes": "HH:MM"} or {"closes": null}.')
WITH = ALONE.replace("If you do not know", "A place-data record is given; use it if it helps. If you do not know")
_cache, _lock = {}, threading.Lock()


class NoRecord(ValueError):
    """Qloo has no place, or no Friday hours, for the name given (a message for the visitor)."""


def _check(o):
    t = o.get("closes") if isinstance(o, dict) else "missing"
    if t is not None and not (isinstance(t, str) and len(t) == 5 and t[2] == ":" and t.replace(":", "").isdigit()):
        raise ValueError('reply as {"closes": "HH:MM"} or {"closes": null}')


def _ask(instructions, prompt):
    """(answer, credits). Answers are kept for the life of the server, so a repeated duel costs nothing."""
    key = (instructions, prompt)
    with _lock:
        if key in _cache:
            return _cache[key], 0.0
    o, meta = llm.complete_json(instructions, prompt, check=_check, timeout=60)
    with _lock:
        _cache[key] = o["closes"]
    return o["closes"], float(meta.get("credits") or 0)


def resolve(name, lat, lon):
    """Qloo's record for a named place within 2 km, closest match by name (as the place_hours tool does)."""
    hits = [h for h in scene.search(name, lat, lon, take=8, radius_km=2) if b10.same_name(h.get("name", ""), name)]
    hit = min(hits, key=lambda h: engine.metres(lat, lon, float(h["location"]["lat"]), float(h["location"]["lon"])), default=None)
    if not hit:
        raise NoRecord(f"Qloo has no place named {name!r} near this storefront")
    p = hit.get("properties") or {}
    closes = t9.closes(p)
    if not closes:
        raise NoRecord(f"Qloo has no Friday closing time for {hit['name']}")
    return {"name": hit["name"], "address": p.get("address") or "New York, NY", "qloo_closes_friday": closes}


def run(name, lat, lon):
    """Returns (result, credits)."""
    rec = resolve(name, lat, lon)
    prompt = f"Restaurant: {rec['name']}\nAddress: {rec['address']}\nQuestion: What time does it close on Friday?"
    out, errors = {}, []

    def arm(key, instructions, text):
        try:
            out[key] = _ask(instructions, text)
        except Exception as e:  # noqa: BLE001  (re-raised below, so the visitor gets the real reason)
            errors.append(e)
    threads = [threading.Thread(target=arm, args=("alone", ALONE, prompt)),
               threading.Thread(target=arm, args=("with_qloo", WITH, prompt + f"\n\nPlace-data record for this "
                                                  f"restaurant: Friday closing time {rec['qloo_closes_friday']}."))]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    if errors:
        raise errors[0]
    if set(out) != {"alone", "with_qloo"}:
        raise llm.LLMError("the model did not answer both questions")
    return ({**rec, "model": llm.MODEL, "alone": out["alone"][0], "with_qloo": out["with_qloo"][0],
             "test20": {"alone_right": 0, "with_qloo_right": 29, "of": 30}},
            out["alone"][1] + out["with_qloo"][1])
