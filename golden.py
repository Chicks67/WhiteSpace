"""Record a live agent run so the site can replay it with zero API calls: python3 golden.py <id>"""
import json
import sys
import time
from datetime import date

import agent

RUNS = {
    "korean-cafe-queens": ("Korean cafe in Queens", {"concept": "Korean cafe", "leases": [
        {"address": "136-20 38th Ave, Queens"}, {"address": "35-01 Union St, Queens"}, {"address": "41-08 Bell Blvd, Queens"}]}),
    "ramen-brooklyn": ("Ramen shop in Brooklyn", {"concept": "Ramen shop", "leases": [
        {"address": "700 Manhattan Ave, Brooklyn"}, {"address": "1000 Fulton St, Brooklyn"}, {"address": "620 Vanderbilt Ave, Brooklyn"}]}),
    "caribbean-brooklyn-bronx": ("Caribbean restaurant, Brooklyn or Bronx", {"concept": "Caribbean restaurant", "leases": [
        {"address": "600 Nostrand Ave, Brooklyn"}, {"address": "2000 Grand Concourse, Bronx"}, {"address": "3000 White Plains Rd, Bronx"}]}),
}

if __name__ == "__main__":
    rid = sys.argv[1]
    title, req = RUNS[rid]
    t0, events = time.time(), []
    agent.run(req, lambda e: events.append([round(time.time() - t0, 2), e]))
    kinds = [e["type"] for _, e in events]
    if "error" in kinds or "brief" not in kinds:
        sys.exit(f"run failed, not saved: {[e for _, e in events if e['type'] == 'error']}")
    json.dump({"title": title, "order": list(RUNS).index(rid), "request": req, "recorded": str(date.today()), "events": events},
              open(f"golden/{rid}.json", "w"), indent=1)
    print(rid, "saved", len(events), "events,", events[-1][0], "s")
