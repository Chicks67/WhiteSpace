"""Blind comparison: GPT-6 Astra positioning briefs with vs without Qloo evidence.

Same model, same instructions, same output shape; only the evidence differs.
Writes a shuffled rating sheet (blind_sheet.md) and a hidden key (blind_key.json).
"""
import json
import random

import llm
import qloo

CASES = [
    ("Korean cafe", "korean", "Flushing, Queens", "POINT(-73.8303 40.7590)"),
    ("Korean cafe", "korean", "Williamsburg, Brooklyn", "POINT(-73.9586 40.7140)"),
    ("Mexican taqueria", "mexican", "Jackson Heights, Queens", "POINT(-73.8830 40.7480)"),
    ("Coffee shop", "coffee_shop", "Astoria, Queens", "POINT(-73.9180 40.7650)"),
    ("Caribbean restaurant", "caribbean", "Flatbush, Brooklyn", "POINT(-73.9590 40.6409)"),
    ("Bakery", "bakery", "Park Slope, Brooklyn", "POINT(-73.9796 40.6710)"),
    ("Ramen shop", "japanese", "East Village, Manhattan", "POINT(-73.9850 40.7265)"),
    ("Pizzeria", "pizza", "Bushwick, Brooklyn", "POINT(-73.9215 40.6943)"),
    ("Middle Eastern restaurant", "middle_eastern", "Bay Ridge, Brooklyn", "POINT(-74.0285 40.6262)"),
    ("Latin American restaurant", "latin_american", "Washington Heights, Manhattan", "POINT(-73.9396 40.8417)"),
]
NYC = "New York City"
BLOCK = {"nigga", "nigger"}  # offensive names seen in Qloo results


def lifted(ft, point, extra=None, field="entities", take=40):
    """Entities or tags an area over-indexes on, ranked by lift over an NYC baseline."""
    sig = {"filter.type": ft, "take": take, **(extra or {})}
    if ft != "urn:tag":
        sig["filter.popularity.max"] = 0.9
    here = qloo.results(qloo.get("/v2/insights", **sig, **{"signal.location": point}), field)
    key = "entity_id" if field == "entities" else "tag_id"
    ids = ",".join(x[key] for x in here if x.get(key))
    filt = "filter.results.entities" if field == "entities" else "filter.results.tags"
    base = qloo.results(qloo.get("/v2/insights", **sig, **{"signal.location.query": NYC, filt: ids}), field)
    bmap = {x[key]: x.get("query", {}).get("affinity", 0) for x in base}
    rows = [(x.get("query", {}).get("affinity", 0) - bmap.get(x[key], 0), x["name"]) for x in here]
    return [n for _, n in sorted(rows, reverse=True) if not any(b in n.lower() for b in BLOCK)]


SENSITIVE = {"race", "religion", "ethnicity"}


def raw_evidence(tag_slug, point):
    tag = f"urn:tag:genre:place:restaurant:{tag_slug}"
    return {
        "tags": lifted("urn:tag", point, field="tags")[:20],
        "brands": lifted("urn:entity:brand", point)[:20],
        "concept_brands": lifted("urn:entity:brand", point, {"signal.interests.tags": tag})[:20],
    }


def evidence_all(cases):
    """Keep only distinctive items: drop anything present in half or more of the areas.

    Findings recorded while building this (2026-10-10): Qloo location results repeat generic
    NYC entities (New York Yankees, Ample Hills Creamery, Urbanspace) across areas; one area's tags
    included "Race"; urn:demographics for every cuisine skewed female and 55+ almost identically,
    so demographics are left out as uninformative.
    """
    raw = [raw_evidence(c[1], c[3]) for c in cases]
    out = []
    for r in raw:
        def keep(field):
            seen = lambda n: sum(n in x[field] for x in raw)
            return [n for n in r[field] if seen(n) < len(cases) / 2
                    and n.lower() not in SENSITIVE][:8]
        out.append("\n".join([
            f"E1. Taste and vibe tags this area over-indexes on versus all of NYC: {', '.join(keep('tags'))}.",
            f"E2. Brands this area over-indexes on versus all of NYC: {', '.join(keep('brands'))}.",
            f"E3. Brands that people near this address who like this cuisine over-index on: {', '.join(keep('concept_brands'))}.",
        ]))
    return out


INSTRUCTIONS = (
    "You are a restaurant brand strategist advising an independent founder in New York City. "
    "Write a concise positioning brief (about 180 words) with exactly these headings: "
    "Audience, Brand voice, Menu emphasis, Music and decor, Launch partners. "
    "Be specific and practical; name real local partner types or brands where you can justify them. "
    "Do not invent statistics. Plain text, no markdown symbols, no evidence codes. "
    "Write as a strategist's recommendations: do not mention data sources, evidence, research, "
    "affinities, signals or any disclaimer about data."
)
LEAK = ("qloo", "affinit", "evidence", "data show", "signal", "over-index", "aggregate", "supplied")


def leaks(text):
    t = text.lower()
    return [w for w in LEAK if w in t]


CACHE = "blind_cache_v2.json"


def brief(concept, area, ev=None):
    import os
    store = json.load(open(CACHE)) if os.path.exists(CACHE) else {}
    k = f"{concept}|{area}|{'qloo' if ev else 'plain'}"
    if k in store:
        return store[k]["text"], store[k]["meta"]
    text, meta = _brief(concept, area, ev)
    store[k] = {"text": text, "meta": meta}
    json.dump(store, open(CACHE, "w"), indent=1)
    return text, meta


def _brief(concept, area, ev=None):
    prompt = f"Concept: {concept}. Location: {area}."
    if ev:
        prompt += ("\n\nBackground on this neighbourhood's audience (use it where relevant, "
                   "ignore items that look irrelevant, never refer to it):\n" + ev)
    for attempt in range(3):
        text, meta = llm.complete(INSTRUCTIONS, prompt, effort="medium", max_output=1500)
        found = leaks(text)
        meta["leak_retries"] = attempt
        if not found:
            return text.strip(), meta
    raise RuntimeError(f"brief still leaks after 3 attempts: {found}")


HEADER = """# Blind brief comparison: rating sheet

## How to rate (please read this first)

**What this is.** Imagine an independent founder about to open a restaurant or cafe in New York City.
For each of the 10 cases below, two positioning briefs (Brief A and Brief B) were written for the same
concept in the same neighbourhood. They were made in different ways, and the order was shuffled at
random, so A is not always the same method. Your job is to judge which brief would help that founder
more, and to score each one.

**Time.** About 30 minutes. Please do it in one sitting if you can.

**Ground rules.**
1. Rate on your own. Please don't discuss the briefs with anyone (including the other team member) until you have
   sent your ratings.
2. Judge only what is written. Don't search the web, and don't try to work out how each brief was made.
3. Use what you already know about NYC. If a brief names a place or brand you know is wrong for that
   area, mark it down on plausibility. If you don't recognise a name, don't penalise it for that alone.
4. Length is roughly equal by design, so don't reward a brief for being longer.

**For each case, give four things.**

1. **Preference: A, B or tie.** Which brief would you rather hand to that founder? Use tie only if you
   genuinely cannot choose.
2. **Specificity** (score each brief 1 to 5): is it written for *this* neighbourhood?
   - 1 = could be pasted onto any neighbourhood in NYC
   - 3 = some real local detail, but much of it is generic
   - 5 = clearly about this neighbourhood; most of it would not fit elsewhere
3. **Plausibility** (1 to 5): does it sound true and workable for this area?
   - 1 = contains claims, names or advice that seem wrong or made up
   - 3 = mostly believable, with a few doubtful points
   - 5 = everything sounds credible for this place and concept
4. **Usefulness** (1 to 5): could the founder act on it?
   - 1 = nothing they could act on
   - 3 = some useful ideas, but they would still need to work most of it out
   - 5 = concrete enough to act on this week (who to target, what to put on the menu, who to call)

Use the whole 1 to 5 range; 2 and 4 are fine for in-between.

**How to reply.** Reply to the email this came in, with one line per case, in this exact format:

`case: preference, A specificity/plausibility/usefulness, B specificity/plausibility/usefulness`

Example: `1: B, A 3/4/3, B 4/4/5` means case 1, you prefer B; Brief A scored 3 for specificity,
4 for plausibility, 3 for usefulness; Brief B scored 4, 4, 5. You can add a short comment after a `#`
if you want, for example `1: B, A 3/4/3, B 4/4/5  # B's partner ideas were much more concrete`.

Copy and fill in this template:

```
1:
2:
3:
4:
5:
6:
7:
8:
9:
10:
```

Thank you!

---
"""


def main():
    random.seed(7)
    sheet, key, spent = [HEADER], {}, 0
    evs = evidence_all(CASES)
    for i, (concept, slug, area, point) in enumerate(CASES, 1):
        ev = evs[i - 1]
        plain, m1 = brief(concept, area)
        grounded, m2 = brief(concept, area, ev)
        spent += (m1["credits"] or 0) + (m2["credits"] or 0)
        pair = [("plain", plain), ("qloo", grounded)]
        random.shuffle(pair)
        key[str(i)] = {"A": pair[0][0], "B": pair[1][0], "evidence": ev}
        sheet += [f"\n## Case {i}: {concept} in {area}\n", "### Brief A\n", pair[0][1], "\n### Brief B\n", pair[1][1], ""]
        print(f"case {i} done ({m1['seconds']}s, {m2['seconds']}s)", flush=True)
    open("blind_sheet.md", "w").write("\n".join(sheet))
    json.dump(key, open("blind_key.json", "w"), indent=2)
    print("credits spent:", round(spent, 2))


if __name__ == "__main__":
    main()
