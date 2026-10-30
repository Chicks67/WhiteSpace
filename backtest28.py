"""Test 28 as registered in PREREGISTRATION_28.md: does a festival timetable built on Qloo's fan-overlap scores make
fewer real fans choose? Truth: GroupLens HetRec 2011 Last.fm (data/lastfm, not committed).
Aggregates go to backtest28_results.json; names to test28_detail.json (not committed).
LLM_PROVIDER=comet python backtest28.py (frontier model: GPT-6 Astra through CometAPI; small model on Google's API)"""
import collections
import itertools
import json
import os
import random

import sys
import types

import numpy as np

# Windows Application Control now blocks scikit-learn's compiled files; backtest14 imports it only for an AUC this
# test does not use, so a stand-in module lets the import through.
sys.modules.setdefault("sklearn", types.ModuleType("sklearn"))
sys.modules.setdefault("sklearn.metrics", types.SimpleNamespace(roc_auc_score=None))

import backtest14 as b14
import backtest18 as b18
import backtest24 as b24
import llm
import qloo

BILLS, GENRES, PER, ACTS, ELIGIBLE, STAGES, SLOTS = 10, 8, 10, 30, 40, 3, 10
ALONE = ("Here are the acts on a festival bill. For every pair, estimate from 0 to 100 how much the two acts' fans are "
         "the same people. Use the whole range.")
WITH = ALONE + " Beside each pair is its overlap from a taste database (0 to 1, or none); use it as you see fit."
FORMAT = (' Reply as {"pairs": {"1-2": n, "1-3": n, ...}} with every pair i-j where i < j, for all '
          f"{ACTS * (ACTS - 1) // 2} pairs.")
PAIRS = list(itertools.combinations(range(ACTS), 2))


def load():
    names = {}
    for line in list(open(os.path.join("data", "lastfm", "artists.dat"), encoding="utf-8"))[1:]:
        p = line.rstrip("\n").split("\t")
        names[p[0]] = p[1]
    fans = collections.defaultdict(set)
    for line in list(open(os.path.join("data", "lastfm", "user_artists.dat"), encoding="utf-8"))[1:]:
        u, a, _ = line.split("\t")
        fans[a].add(u)
    tags = {}
    for line in list(open(os.path.join("data", "lastfm", "tags.dat"), encoding="latin-1"))[1:]:
        t, v = line.rstrip("\n").split("\t")
        tags[t] = v
    tagged = collections.defaultdict(set)
    for line in list(open(os.path.join("data", "lastfm", "user_taggedartists.dat"), encoding="utf-8"))[1:]:
        _, a, t = line.split("\t")[:3]
        tagged[t].add(a)
    return names, fans, tags, tagged


def rank(v):
    v = np.asarray(v, dtype=float)
    o = np.argsort(v, kind="mergesort")
    r = np.empty(len(v))
    r[o] = np.arange(len(v))
    for x in np.unique(v):  # ties share the mean rank
        m = v == x
        r[m] = r[m].mean()
    return r


def spearman(a, b):
    ra, rb = rank(a), rank(b)
    if ra.std() == 0 or rb.std() == 0:
        return 0.0
    return float(np.corrcoef(ra, rb)[0, 1])


def clash(m, sched):
    """Sum of pair scores over acts that share a slot. sched[i] = slot of act i."""
    s = np.asarray(sched)
    same = s[:, None] == s[None, :]
    return float(np.triu(m * same, 1).sum())


def optimise(m, tag):
    best, best_v = None, None
    for start in range(20):
        sched = [k // STAGES for k in range(ACTS)]
        random.Random(f"28-opt-{tag}-{start}").shuffle(sched)
        v = clash(m, sched)
        improved = True
        while improved:
            improved = False
            for i, j in PAIRS:
                if sched[i] == sched[j]:
                    continue
                sched[i], sched[j] = sched[j], sched[i]
                w = clash(m, sched)
                if w < v - 1e-12:
                    v, improved = w, True
                else:
                    sched[i], sched[j] = sched[j], sched[i]
        if best_v is None or v < best_v:
            best, best_v = list(sched), v
    return best


def matrix(scores):
    m = np.zeros((ACTS, ACTS))
    for (i, j), x in zip(PAIRS, scores):
        m[i, j] = m[j, i] = x
    return m


def model(tag, b, acts, qpairs, small, run=1):
    path = os.path.join(qloo.CACHE, f"llm28_{'small' if small else 'big'}_{tag}_{run}_{b}.json")
    if os.path.exists(path):
        return json.load(open(path))
    listing = "\n".join(f"{i}. {a['name']}" for i, a in enumerate(acts, 1))
    if tag == "with":
        listing += "\n\nTaste-database overlap per pair:\n" + "\n".join(
            f"{i + 1}-{j + 1}: {'none' if qpairs[k] is None else f'{qpairs[k]:.2f}'}" for k, (i, j) in enumerate(PAIRS))

    def check(o):
        p = o.get("pairs")
        if not isinstance(p, dict) or any(f"{i + 1}-{j + 1}" not in p for i, j in PAIRS):
            raise ValueError("give a score for every pair i-j with i < j")
    instr = (WITH if tag == "with" else ALONE) + FORMAT
    prompt = "Acts:\n" + listing
    o = b18.small_json(instr, prompt, check) if small else llm.complete_json(instr, prompt, check=check, timeout=300)[0]
    out = [float(o["pairs"][f"{i + 1}-{j + 1}"]) for i, j in PAIRS]
    json.dump(out, open(path, "w"))
    return out


def interval(v):
    v = np.array(v, dtype=float)
    rng = np.random.default_rng(0)
    b = [float(np.mean(rng.choice(v, len(v)))) for _ in range(2000)]
    return {"mean": round(float(v.mean()), 3), "ci95": [round(float(x), 3) for x in np.percentile(b, [2.5, 97.5])], "n": len(v)}


def main():
    os.environ.pop("SMALL_HOST", None)  # Amendment 2: the small model through CometAPI
    names, fans, tags, tagged = load()
    eligible = {a for a, f in fans.items() if len(f) >= ELIGIBLE}
    count = {t: len(s & eligible) for t, s in tagged.items()}
    top = sorted(count, key=lambda t: (-count[t], int(t)))[:GENRES]
    found = {}

    def q(a):
        if a not in found:
            found[a] = b24.artist(names[a])
        return found[a]
    rng = random.Random(28)
    rows, detail, aside = [], [], []
    for b in range(2 * BILLS):  # Amendment 1: refused bills are set aside; at most 20 drawn
        if len(rows) == BILLS:
            break
        genres = rng.sample(top, 3)
        acts, ids = [], []
        for g in genres:
            cand = sorted(tagged[g] & eligible, key=int)
            random.Random(f"28-{b}-{g}").shuffle(cand)
            n = 0
            for a in cand:
                if n == PER:
                    break
                if a in ids:
                    continue
                x = q(a)
                if x and x["id"] not in {y["id"] for y in acts}:
                    acts.append(x); ids.append(a); n += 1
        assert len(acts) == ACTS, f"bill {b}: only {len(acts)} acts"
        truth = [len(fans[ids[i]] & fans[ids[j]]) / min(len(fans[ids[i]]), len(fans[ids[j]])) for i, j in PAIRS]
        qid = [a["id"] for a in acts]
        aff = [b14.affinities(qid[i], [x for x in qid if x != qid[i]]) for i in range(ACTS)]
        qpairs = []
        for i, j in PAIRS:
            two = [d[o] for d, o in ((aff[i], qid[j]), (aff[j], qid[i])) if o in d]
            qpairs.append(float(np.mean(two)) if two else None)
        try:
            arms = {"qloo": [x or 0.0 for x in qpairs],
                    "fame": [acts[i]["popularity"] * acts[j]["popularity"] for i, j in PAIRS],
                    "frontier_alone": model("alone", b, acts, qpairs, False),
                    "frontier_with_qloo": model("with", b, acts, qpairs, False),
                    "small_alone": model("alone", b, acts, qpairs, True),
                    "small_with_qloo": model("with", b, acts, qpairs, True)}
            repeat = model("alone", b, acts, qpairs, False, run=2)
        except (llm.LLMError, KeyError) as e:  # KeyError: Google returned no candidate (a blocked prompt)
            if isinstance(e, llm.LLMError) and not any(w in str(e).lower() for w in ("flagged", "invalid_prompt", "safety")):
                raise
            aside.append({"bill": b, "reason": str(e)[:160]})
            print("bill", b + 1, "set aside (provider refused the prompt)", flush=True)
            continue
        tm = matrix(truth)
        rand = float(np.mean([clash(tm, random.Random(f"28-rand-{b}-{k}").sample([s // STAGES for s in range(ACTS)], ACTS))
                              for k in range(200)]))
        best = clash(tm, optimise(tm, f"truth-{b}"))
        r = {"bill": b, "pairs_scored_by_qloo": round(sum(x is not None for x in qpairs) / len(PAIRS), 3),
             "stability_frontier": spearman(arms["frontier_alone"], repeat)}
        for k, v in arms.items():
            r[f"pair_{k}"] = spearman(v, truth)
            r[f"gain_{k}"] = (rand - clash(tm, optimise(matrix(v), f"{k}-{b}"))) / (rand - best)
        rows.append(r)
        detail.append({"bill": b, "genres": [tags[g] for g in genres], "acts": [a["name"] for a in acts], **r})
        print("bill", b + 1, "done", flush=True)
    out = {"bills": len(rows), "bills_set_aside": len(aside), "set_aside_reasons": [a["reason"] for a in aside],
           "genres": [tags[g] for g in top],
           "pairs_scored_by_qloo": interval([r["pairs_scored_by_qloo"] for r in rows]),
           "stability_frontier": interval([r["stability_frontier"] for r in rows])}
    for lvl in ("pair", "gain"):
        out[lvl] = {k: interval([r[f"{lvl}_{k}"] for r in rows]) for k in
                    ("qloo", "fame", "frontier_alone", "frontier_with_qloo", "small_alone", "small_with_qloo")}
        d = lambda a, c: interval([r[f"{lvl}_{a}"] - r[f"{lvl}_{c}"] for r in rows])
        out[f"{lvl}_differences"] = {"qloo_minus_fame": d("qloo", "fame"), "qloo_minus_frontier_alone": d("qloo", "frontier_alone"),
                                     "frontier_with_minus_alone": d("frontier_with_qloo", "frontier_alone"),
                                     "small_with_minus_alone": d("small_with_qloo", "small_alone"),
                                     "small_with_qloo_minus_frontier_alone": d("small_with_qloo", "frontier_alone")}
    three = lambda x: "above" if x["ci95"][0] > 0 else "below" if x["ci95"][1] < 0 else "no different"
    out["reading_1"] = ("a timetable built on Qloo's scores made fewer real fans choose than a random one"
                        if out["gain"]["qloo"]["ci95"][0] > 0 else "not shown")
    out["readings"] = {f"{lvl}_{k}": three(v) for lvl in ("pair", "gain") for k, v in out[f"{lvl}_differences"].items()}
    json.dump(detail, open("test28_detail.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    json.dump(out, open("backtest28_results.json", "w"), indent=1)
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
