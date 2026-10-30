"""Test 27 as registered in PREREGISTRATION_27.md: on small artists, does Qloo know a real listener's taste better
than a model? Data: GroupLens HetRec 2011 Last.fm (data/lastfm, not committed).
Aggregates go to backtest27_results.json; names to test27_detail.json (not committed).
LLM_PROVIDER=kie python backtest27.py (Amendment 1: GPT-6 Astra through Kie)"""
import collections
import json
import os
import random

import numpy as np

import backtest14 as b14
import backtest24 as b24
import llm
import qloo

KEEP, TRY, POS, NEG, SMALL, CANDS = 40, 120, 5, 30, 10, 8
FLOOR = 2500  # stop before Qloo's monthly quota falls below what the live demo needs
ALONE = ("Here are the five artists a person listens to most. For each artist in the numbered list, score from 0 to 100 "
         "how likely this person is to listen to it too. Use the whole range. If you do not know an artist, give your "
         "best guess.")
WITH = ALONE + " Beside each artist is its fit with this person from a taste database (0 to 1, or none); use it as you see fit."
FORMAT = (' Reply as {"scores": {"1": n, "2": n, ...}, "unknown": [numbers of artists you do not know]} with every '
          "number in the list.")


def load():
    names = {}
    for line in list(open(os.path.join("data", "lastfm", "artists.dat"), encoding="utf-8"))[1:]:
        p = line.rstrip("\n").split("\t")
        names[p[0]] = p[1]
    plays = collections.defaultdict(list)
    for line in list(open(os.path.join("data", "lastfm", "user_artists.dat"), encoding="utf-8"))[1:]:
        u, a, w = line.split("\t")
        plays[u].append((int(w), a))
    listeners = collections.Counter(a for v in plays.values() for _, a in v)
    return names, {u: [a for _, a in sorted(v, reverse=True)] for u, v in plays.items()}, listeners


def model(tag, uid, favs, names, extra):
    path = os.path.join(qloo.CACHE, f"llm27_{tag}_{uid}.json")
    if os.path.exists(path):
        return json.load(open(path))
    listing = "\n".join(f"{i}. {n}" + (f" (fit {extra[i - 1]})" if tag == "with" else "") for i, n in enumerate(names, 1))

    def check(o):
        if not isinstance(o.get("scores"), dict) or any(str(i) not in o["scores"] for i in range(1, len(names) + 1)):
            raise ValueError("score every number in the list")
    o = llm.complete_json((WITH if tag == "with" else ALONE) + FORMAT, f"Most played: {', '.join(favs)}.\n\nArtists:\n{listing}",
                          check=check, timeout=180)[0]
    out = {"scores": [float(o["scores"][str(i)]) for i in range(1, len(names) + 1)], "unknown": len(o.get("unknown") or [])}
    json.dump(out, open(path, "w"))
    return out


def interval(v):
    v = np.array([x for x in v if x is not None], dtype=float)
    rng = np.random.default_rng(0)
    b = [float(np.mean(rng.choice(v, len(v)))) for _ in range(2000)]
    return {"mean": round(float(v.mean()), 3), "ci95": [round(float(x), 3) for x in np.percentile(b, [2.5, 97.5])], "n": len(v)}


def main():
    names, lists, listeners = load()
    users = sorted(u for u, v in lists.items() if len(v) >= 30)
    random.Random(27).shuffle(users)
    found, pool, kept, tried, stopped = {}, {}, [], 0, None

    def q(aid):
        if aid not in found:
            found[aid] = b24.artist(names[aid])
        return found[aid]
    for u in users:
        if len(kept) == KEEP or tried == TRY:
            break
        if qloo.QUOTA["remaining"] is not None and qloo.QUOTA["remaining"] < FLOOR:
            stopped = "Qloo quota floor"; break
        tried += 1
        favs = [x for x in (q(a) for a in lists[u][:12]) if x][:5]
        rng = random.Random(f"27-{u}")
        small = [a for a in lists[u][20:] if listeners[a] <= SMALL]
        rng.shuffle(small)
        pos = []
        for a in small[:CANDS]:
            x = q(a)
            if x:
                pool[x["id"]] = x
                if len(pos) < POS:
                    pos.append(x)
        if len(favs) < 5 or len(pos) < 3:
            continue
        kept.append({"user": u, "favs": favs, "pos": pos})
        print(len(kept), "users of", tried, "tried", flush=True)
    out = {"users_tried": tried, "users_kept": len(kept), "pool": len(pool), "stopped": stopped}
    if len(kept) < 20:
        out["reading"] = "too few to say"
    else:
        rows, detail = [], []
        for k in kept:
            heard = {q(a)["id"] for a in lists[k["user"]] if found.get(a)}
            rng = random.Random(f"27n-{k['user']}")
            others = [i for i in sorted(pool) if i not in heard]
            short = [p["id"] for p in k["pos"]] + rng.sample(others, min(NEG, len(others)))
            rng.shuffle(short)
            own = {p["id"] for p in k["pos"]}
            aff = b14.affinities(",".join(f["id"] for f in k["favs"]), short)
            y = [i in own for i in short]
            nm = [pool[i]["name"] for i in short]
            favn = [f["name"] for f in k["favs"]]
            alone = model("alone", k["user"], favn, nm, None)
            both = model("with", k["user"], favn, nm, [f"{aff[i]:.2f}" if i in aff else "none" for i in short])
            r = {"qloo": b14.auc(y, [aff.get(i, -1.0) for i in short]), "fame": b14.auc(y, [pool[i]["popularity"] for i in short]),
                 "model_alone": b14.auc(y, alone["scores"]), "model_with_qloo": b14.auc(y, both["scores"]),
                 "scored_by_qloo": round(sum(i in aff for i in short) / len(short), 3), "unknown_to_model": alone["unknown"],
                 "positive_popularity": round(float(np.mean([pool[i]["popularity"] for i in own])), 3)}
            rows.append(r)
            detail.append({"user": k["user"], "favourites": favn, "positives": [pool[i]["name"] for i in own], **r})
            print(len(rows), "scored", flush=True)
        g = lambda a, b: interval([r[a] - r[b] for r in rows])
        out.update({"auc": {k: interval([r[k] for r in rows]) for k in ("qloo", "fame", "model_alone", "model_with_qloo")},
                    "qloo_minus_model_alone": g("qloo", "model_alone"), "with_qloo_minus_alone": g("model_with_qloo", "model_alone"),
                    "qloo_minus_fame": g("qloo", "fame"), "share_scored_by_qloo": interval([r["scored_by_qloo"] for r in rows]),
                    "artists_model_said_unknown_per_user": interval([r["unknown_to_model"] for r in rows]),
                    "positive_popularity": interval([r["positive_popularity"] for r in rows])})
        three = lambda x: "above" if x["ci95"][0] > 0 else "below" if x["ci95"][1] < 0 else "no different"
        d = out["qloo_minus_model_alone"]
        out["reading_1"] = ("on small artists, Qloo knew a real listener's taste better than the model" if d["ci95"][0] > 0 else
                            "the model knew better" if d["ci95"][1] < 0 else "no different")
        out["reading_2_model_with_qloo_against_alone"] = three(out["with_qloo_minus_alone"])
        out["reading_3_qloo_against_fame"] = three(out["qloo_minus_fame"])
        json.dump(detail, open("test27_detail.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    json.dump(out, open("backtest27_results.json", "w"), indent=1)
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
