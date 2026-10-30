"""Add the code-derived lease fields (subway, business improvement district, local partners, next steps) to
saved runs recorded before those fields existed. Nothing the model wrote is touched: the shortlist, brief and
follow-up answers stay as recorded. Each refreshed file notes the date and the fields added."""
import json
import sys
from datetime import date

import bids
import next_steps
import partners
import transit

FIELDS = ["subway", "bid", "partners", "next_steps"]


def refresh(path):
    g = json.load(open(path))
    concept = g["request"]["concept"]
    cuisine = next((e["data"]["cuisine"] for _, e in g["events"] if e["type"] == "concept"), None)
    for _, e in g["events"]:
        if e["type"] != "leases":
            continue
        for l in e["data"]:
            l["subway"] = transit.near(l["lat"], l["lon"])
            l["bid"] = bids.bid_for(l["lat"], l["lon"])
            l["partners"] = partners.for_lease(cuisine, l["lat"], l["lon"], concept)
            l["next_steps"] = next_steps.for_lease(l)
    g["refreshed"] = {"date": str(date.today()), "fields": FIELDS,
                      "note": "computed in code from city data after recording; model output unchanged"}
    json.dump(g, open(path, "w"), indent=1)
    return cuisine


if __name__ == "__main__":
    for p in sys.argv[1:]:
        print(p, refresh(p))
