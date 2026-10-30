"""Who-and-how layer: Qloo-grounded positioning brief for one lease. Descriptive, never predictive.

This is the configuration tested blind in Test 3 (blind_test.py): same instructions, same evidence
builder, same distinctiveness filter, same model settings. Only additions: evidence IDs, linking named
items in the brief back to the evidence, and a second call that lists every named business so the
UI can mark names that did not come from Qloo as unverified model suggestions.
"""
import re
from functools import lru_cache

import blind_test as bt
import llm
import nyc

HEADINGS = ["Audience", "Brand voice", "Menu emphasis", "Music and decor", "Launch partners"]
FIELDS = [("tags", "T", "Taste and vibe tags this area over-indexes on versus all of NYC"),
          ("brands", "B", "Brands this area over-indexes on versus all of NYC"),
          ("concept_brands", "C", "Brands that people near this address who like this cuisine over-index on")]


@lru_cache(maxsize=1)
def reference():
    """Raw evidence for the 10 Test 3 reference areas; the filter drops items common to half of them."""
    return [bt.raw_evidence(c[1], c[3]) for c in bt.CASES]


@lru_cache(maxsize=1)
def nta():
    return nyc.NTALookup()


def area_name(lat, lon, borough, neighbourhood=None):
    """Plain neighbourhood name as in Test 3 ("Flushing, Queens"); NTA name only as a fallback."""
    import storefronts
    n = neighbourhood or storefronts.short_name(nta().name(lat, lon) or "")
    return f"{n}, {borough}" if n else borough


def raw_evidence(slug, point, radius=None):
    """Test 3's evidence builder. With a radius, only the area query is widened; the NYC baseline is unchanged."""
    if radius is None:
        return bt.raw_evidence(slug, point)
    tag = f"urn:tag:genre:place:restaurant:{slug}"
    wide = {"signal.location.radius": radius}
    return {
        "tags": lifted("urn:tag", point, wide, field="tags")[:20],
        "brands": lifted("urn:entity:brand", point, wide)[:20],
        "concept_brands": lifted("urn:entity:brand", point, wide, {"signal.interests.tags": tag})[:20],
    }


def lifted(ft, point, here_extra, extra=None, field="entities", take=40):
    """bt.lifted with extra parameters on the area query only."""
    sig = {"filter.type": ft, "take": take, **(extra or {})}
    if ft != "urn:tag":
        sig["filter.popularity.max"] = 0.9
    here = bt.qloo.results(bt.qloo.get("/v2/insights", **sig, **here_extra, **{"signal.location": point}), field)
    key = "entity_id" if field == "entities" else "tag_id"
    ids = ",".join(x[key] for x in here if x.get(key))
    filt = "filter.results.entities" if field == "entities" else "filter.results.tags"
    base = bt.qloo.results(bt.qloo.get("/v2/insights", **sig, **{"signal.location.query": bt.NYC, filt: ids}), field)
    bmap = {x[key]: x.get("query", {}).get("affinity", 0) for x in base}
    rows = [(x.get("query", {}).get("affinity", 0) - bmap.get(x[key], 0), x["name"]) for x in here]
    return [n for _, n in sorted(rows, reverse=True) if not any(b in n.lower() for b in bt.BLOCK)]


def evidence(slug, lat, lon, radius=None):
    """Distinctive Qloo items near the lease, each with an evidence ID."""
    point = f"POINT({lon:.4f} {lat:.4f})"
    raw, ref = raw_evidence(slug, point, radius), reference()
    items = []
    for field, prefix, label in FIELDS:
        kept = [n for n in raw[field] if sum(n in r[field] for r in ref) < len(ref) / 2
                and n.lower() not in bt.SENSITIVE][:8]
        items += [{"id": f"{prefix}{i}", "group": label, "name": n} for i, n in enumerate(kept, 1)]
    return point, items


def evidence_text(items):
    lines = []
    for i, (_, prefix, label) in enumerate(FIELDS, 1):
        names = [x["name"] for x in items if x["id"].startswith(prefix)]
        lines.append(f"E{i}. {label}: {', '.join(names)}.")
    return "\n".join(lines)


def sections(text):
    pat = re.compile(r"^\s*(" + "|".join(map(re.escape, HEADINGS)) + r")\s*:?\s*", re.I | re.M)
    marks = list(pat.finditer(text))
    out = {}
    for i, m in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(text)
        name = next(h for h in HEADINGS if h.lower() == m.group(1).lower())
        out[name] = text[m.end():end].strip()
    return out


NAMES_INSTRUCTIONS = (
    "List every named business, brand, venue, publication, organisation or event series mentioned in the text. "
    "Exclude generic types (for example 'a local bakery'), neighbourhood and street names, and dish names. "
    'Reply as {"names": ["..."]}.'
)


def check_names(obj):
    if not isinstance(obj.get("names"), list) or not all(isinstance(n, str) for n in obj["names"]):
        raise ValueError("names must be a list of strings")


def _norm(name):
    n = re.sub(r"[^a-z0-9& ]", " ", name.lower().replace("\u2019", "'").replace("'", ""))
    n = re.sub(r"\s+", " ", n.replace("&", " and ")).strip()
    n = n[4:] if n.startswith("the ") else n
    return re.sub(r"( (co|company|inc|llc|corp|nyc|ny))+$", "", n)


@lru_cache(maxsize=1)
def _city_names():
    import engine
    idx = {}
    for r in engine.city().rest:
        idx.setdefault(_norm(r["dba"]), []).append((r["lat"], r["lon"], r["dba"]))
    return idx


def city_lookup(name, lat, lon, near=2000):
    """Find a named business in NYC inspection records: 'near' (within 2 km of the lease), 'nyc', or None."""
    import engine
    n, idx = _norm(name), _city_names()
    if len(n) < 4:
        return None, None
    hits = idx.get(n, []) + [h for k, v in idx.items() if k.startswith(n + " ") for h in v]
    if not hits:
        return None, None
    best = min(hits, key=lambda h: engine.metres(lat, lon, h[0], h[1]))
    d = engine.metres(lat, lon, best[0], best[1])
    return ("near" if d <= near else "nyc"), {"dba": best[2].title(), "metres": round(d)}


def bid_lookup(name, lat, lon, near=2000):
    """A business improvement district named in the brief, within 2 km of the lease (NYC Open Data)."""
    import bids
    import partners
    n = bids._norm(name)
    if len(n) < 4:
        return None, None
    for b in partners.bids_near(lat, lon, near):
        k, nt = set(bids._norm(b["bid"]).split()), set(n.split())
        if k and (k <= nt or (nt <= k and len(nt) >= 2)):  # whole words: 'Park' alone matches no district
            return "near", {"dba": b["bid"], "metres": b["metres"], "kind": "business improvement district"}
    return None, None


def verify(text, items, lat=None, lon=None, founder_text=""):
    """Code checks on a brief: headings present, no figures, no data-source talk; every named business is
    traced to Qloo, to NYC inspection records, or marked unverified."""
    secs = sections(text)
    problems = [f"missing heading {h}" for h in HEADINGS if h not in secs]
    if re.search(r"\d+\s*%|\b\d{2,}\b", text):
        problems.append("contains figures")
    if bt.leaks(text):
        problems.append("mentions data sources")
    try:
        names, meta = llm.complete_json(NAMES_INSTRUCTIONS, text, check=check_names)
    except llm.LLMError as e:  # the brief stands; only the name check is missing, and the page says so
        names, meta = {"names": []}, {"credits": 0}
        problems_soft = f"name check unavailable ({str(e)[:60]})"
    else:
        problems_soft = None
    linked = [x["id"] for x in items if _has(x["name"], text)]
    q = [x["name"].lower() for x in items]
    sources = []
    for n in dict.fromkeys(names["names"]):
        from_qloo = any(n.lower() in s or s in n.lower() for s in q)
        where, hit = city_lookup(n, lat, lon) if lat is not None else (None, None)
        if where is None and lat is not None:
            where, hit = bid_lookup(n, lat, lon)
        if where is None and founder_text and _has(n, founder_text):  # the founder named it in their own plan
            where, hit = "founder", {"dba": n, "metres": None, "kind": "named in your plan"}
        sources.append({"name": n, "qloo": from_qloo, "city": where, "city_match": hit})
    unverified = [s["name"] for s in sources if not s["qloo"] and s["city"] is None]
    return {"sections": secs, "text": text, "evidence": items, "linked": linked, "names": sources,
            "unverified_names": unverified, "problems": problems, "credits": meta.get("credits") or 0,
            "name_check": problems_soft or "done"}


def brief(concept, slug, lat, lon, borough, neighbourhood=None):
    area = area_name(lat, lon, borough, neighbourhood)
    point, items = evidence(slug, lat, lon)
    text, meta = bt._brief(concept, area, evidence_text(items))
    return {"area": area, "point": point, "concept": concept, **verify(text, items, lat, lon), "meta": meta}


if __name__ == "__main__":
    import json
    import qloo
    qloo.on_call = lambda p, params, s, c: print("qloo", s, "cached" if c else "live")
    r = brief("Korean cafe", "korean", 40.7607, -73.8297, "Queens", "Flushing")
    print(json.dumps({k: v for k, v in r.items() if k not in ("text", "evidence", "sections")}, indent=1))


REPAIR_INSTRUCTIONS = (
    "You edit a restaurant positioning brief. Some named businesses in it could not be traced to any source we hold. "
    "Rewrite ONLY the sentences that contain those names: replace each name either with a generic description of "
    "that kind of partner or place (for example 'a nearby craft brewery'), or with one of the allowed names if it "
    "fits naturally. Do not add any other business names. Keep every other sentence exactly as it is, keep the "
    "headings Audience, Brand voice, Menu emphasis, Music and decor, Launch partners, plain text, no markdown. "
    "Return the full brief."
)


def repair(text, unverified, items):
    """One repair pass: returns (new_text, meta) or raises if the edit breaks the brief."""
    allowed = [x["name"] for x in items if not x["id"].startswith("T")]
    prompt = (f"Names to replace: {'; '.join(unverified)}\n"
              f"Allowed names: {'; '.join(allowed) or 'none'}\n\nBrief:\n{text}")
    new, meta = llm.complete(REPAIR_INSTRUCTIONS, prompt, effort="low", max_output=1500, timeout=60)
    new = new.strip()
    secs = sections(new)
    if any(h not in secs for h in HEADINGS):
        raise ValueError("repair dropped a heading")
    if not 0.75 <= len(new) / max(len(text), 1) <= 1.25:
        raise ValueError("repair changed the length too much")
    left = [n for n in unverified if _has(n, new)]
    if left:
        raise ValueError(f"repair kept {left}")
    touched = unchanged_except(text, new, unverified)
    if touched is None:
        raise ValueError("repair changed sentences that named no flagged business")
    meta["sentences_changed"] = touched
    return new, meta


def drop_unverified(text, names):
    """Code fallback when the repair call fails: remove each sentence that names an unverified business. A
    section that would be left empty keeps its sentences with the name replaced by 'a local partner'."""
    out = []
    for h, body in sections(text).items():
        sents = [x for x in _sentences(body)]
        kept = [x for x in sents if not any(_has(n, x) for n in names)]
        if not kept:
            kept = sents
            for n in names:
                kept = [re.sub(r"(?<!\w)" + re.escape(n) + r"(?!\w)", "a local partner", x, flags=re.I) for x in kept]
        out.append(h + "\n\n" + " ".join(kept))
    return "\n\n".join(out)


def _has(name, text):
    """Whole-name match that also works for names ending in punctuation ("Ale Co.")."""
    return re.search(r"(?<!\w)" + re.escape(name) + r"(?!\w)", text, re.I) is not None


def _sentences(text):
    # split at sentence ends followed by a capital letter or a quote, and at line breaks; "Co. for" stays whole
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+(?=[A-Z\"\u201c])|\n+", text) if s.strip()]


def unchanged_except(old, new, names):
    """Every sentence of `old` that names none of `names` must appear verbatim in `new`.
    Returns how many sentences changed, or None if any other sentence was altered."""
    new_set = set(_sentences(new))
    flagged = lambda s: any(_has(n, s) for n in names)
    changed = 0
    for s in _sentences(old):
        if flagged(s):
            changed += 1
        elif s not in new_set:
            return None
    return changed


def write_brief(concept, area, items, on_delta, attempts=3):
    """Test 3's brief call (same instructions, prompt, effort and length as blind_test._brief), streamed.
    Retries on a data-source leak (as in Test 3) or on a provider error/timeout."""
    prompt = f"Concept: {concept}. Location: {area}."
    prompt += ("\n\nBackground on this neighbourhood's audience (use it where relevant, "
               "ignore items that look irrelevant, never refer to it):\n" + evidence_text(items))
    last = None
    for attempt in range(attempts):
        on_delta(None)  # reset the visible draft
        try:
            text, meta = llm.stream_complete(bt.INSTRUCTIONS, prompt, on_delta, effort="medium", max_output=1500)
        except llm.LLMError as e:
            last = e
            continue
        meta["attempt"] = attempt + 1
        if not bt.leaks(text):
            return text.strip(), meta
        last = llm.LLMError(f"brief mentions data sources: {bt.leaks(text)}")
    raise last
