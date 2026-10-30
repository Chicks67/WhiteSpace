"""Reliability check: run each saved-run case 3 times (pass^3). A run passes if it finishes without error,
the brief passes verification, and the lease order matches the other runs. The first passing run of each
case is saved as its replay."""
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date

import agent
import golden

N = 3


def one(rid):
    t0, events = time.time(), []
    agent.run(golden.RUNS[rid][1], lambda e: events.append([round(time.time() - t0, 2), e]))
    by = {e["type"]: e for _, e in events}
    brief = by.get("brief", {}).get("data", {})
    steps = {e["id"]: e for _, e in events if e["type"] == "step" and e["status"] == "done"}
    return {
        "events": events,
        "error": by.get("error", {}).get("message"),
        "order": [l["address"] for l in by.get("leases", {}).get("data", [])],
        "problems": brief.get("problems"),
        "names": len(brief.get("names", [])),
        "qloo_names": sum(1 for s in brief.get("names", []) if s["qloo"]),
        "city_names": sum(1 for s in brief.get("names", []) if not s["qloo"] and s["city"] == "near"),
        "unverified": len(brief.get("unverified_names", [])),
        "rewrite": "rewrite" in steps,
        "recovered": [k for k in steps if k.startswith("recover")],
        "seconds": events[-1][0] if events else None,
        "credits": by.get("done", {}).get("credits"),
        "fallback": "fallback" in str(steps.get("write", {}).get("detail", "")),
    }


if __name__ == "__main__":
    ids = sys.argv[1:] or list(golden.RUNS)
    with ThreadPoolExecutor(3) as ex:
        res = {rid: list(ex.map(one, [rid] * N)) for rid in ids}
    summary = {}
    for rid, runs in res.items():
        orders = {tuple(r["order"]) for r in runs}
        for r in runs:
            r["passed"] = not r["error"] and r["problems"] == [] and len(orders) == 1
        summary[rid] = {"pass^3": all(r["passed"] for r in runs),
                        "runs": [{k: v for k, v in r.items() if k != "events"} for r in runs]}
        good = next((r for r in runs if r["passed"]), None)
        if good:
            title, req = golden.RUNS[rid]
            json.dump({"title": title, "order": list(golden.RUNS).index(rid), "request": req,
                       "recorded": str(date.today()), "events": good["events"]},
                      open(f"golden/{rid}.json", "w"), indent=1)
        print(rid, json.dumps(summary[rid]["pass^3"]), [(r["seconds"], r["names"], r["qloo_names"], r["city_names"],
                                                         r["unverified"], r["error"]) for r in runs], flush=True)
    json.dump(summary, open("eval_results.json", "w"), indent=1)
