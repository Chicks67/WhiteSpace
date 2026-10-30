"""Public, redacted copies of the saved runs, plus a hash of each full file.

The full saved runs contain Qloo responses. Qloo allows private server-side caching but not Qloo data in a
public repo, so the full files live only on the private server (GOLDEN_DIR). This writes what can be public:
the agent's steps, tool calls, the city-data rankings, verification results and timings, with Qloo content
removed. SHA256SUMS lets anyone with the live site check that a replay matches the recording:
GET /api/golden/<id>/sha256 returns the hash of the file the server replays.
"""
import glob
import hashlib
import json
import os

SRC = os.environ.get("GOLDEN_DIR") or "golden"
OUT = "fixtures/replays"
DROP = {"qloo", "evidence", "taste", "brief_delta"}  # Qloo responses, or text written from them
QLOO_TOOLS = {"area_profile"}


def redact(g):
    events = []
    for t, e in g["events"]:
        if e["type"] in DROP:
            continue
        if e["type"] == "brief":
            d = e["data"]
            e = {"type": "brief", "data": {
                "lease": d.get("lease"), "area": d.get("area"), "problems": d.get("problems"),
                "name_check": d.get("name_check"),
                "names_traced_to_city_records": [n["name"] for n in d.get("names", []) if not n["qloo"] and n["city"]],
                "names_traced_to_qloo": sum(1 for n in d.get("names", []) if n["qloo"]),
                "replaced_unverified_names": d.get("unverified_before_repair"),
                "unverified_names_left": d.get("unverified_names"),
                "text": "[brief written from Qloo evidence; on the live site only]"}}
        events.append([t, e])
    out = {k: g[k] for k in ("title", "request", "recorded") if k in g} | {"events": events}
    if g.get("followups"):
        out["followups"] = []
        for f in g["followups"]:
            tools = [e["name"] for _, e in f["events"] if e["type"] == "tool" and e["status"] == "done"]
            ans = next(e for _, e in f["events"] if e["type"] == "answer")
            out["followups"].append({"q": f["q"], "tools": tools, "unchecked_numbers": ans["unchecked_numbers"],
                                     "answer": "[drew on Qloo data; on the live site only]" if QLOO_TOOLS & set(tools)
                                     else ans["text"]})
    return out


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    sums = []
    for p in sorted(glob.glob(os.path.join(SRC, "*.json"))):
        rid = os.path.basename(p)[:-5]
        sums.append(f"{hashlib.sha256(open(p, 'rb').read()).hexdigest()}  {rid}.json")
        json.dump(redact(json.load(open(p))), open(os.path.join(OUT, rid + ".json"), "w"), indent=1)
    open(os.path.join(OUT, "SHA256SUMS"), "w").write("\n".join(sums) + "\n")
    print("\n".join(sums))
