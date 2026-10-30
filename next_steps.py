"""Next steps for a lease: the city's opening requirements, plus what applies to this address.

General steps are taken from NYC Business (nyc-business.nyc.gov) pages, cited per item. Address-specific
items come from public records: landmark status (LPC, ncre-qhxs), the business improvement district, and
the storefront's last reported use.
"""
import json
import os
import urllib.request
from functools import lru_cache

import bids

DATA = os.path.join(os.path.dirname(__file__), "data")
FSE = "https://nyc-business.nyc.gov/nycbusiness/description/food-service-establishment-permit"
INDUSTRY = "https://nyc-business.nyc.gov/nycbusiness/resources-by-industry/bar"

GENERAL = [
    ("Confirm the space has a Certificate of Occupancy for a restaurant use (NYC Department of Buildings). "
     "No place may be used until one is issued.", FSE),
    ("Register as a sales tax vendor and get a Certificate of Authority (NYS Department of Taxation and Finance); "
     "its address must match the restaurant's.", FSE),
    ("Get workers' compensation and disability insurance, with the Health Department listed as certificate holder.", FSE),
    ("A supervising manager passes the Food Protection Course (NYC Health Academy) and is on site at all times.", FSE),
    ("Apply for the Food Service Establishment Permit online at nyc.gov/dohmhpermits ($280 for most restaurants). "
     "You may open 22 days after applying; a pre-permit inspection follows, then an unannounced visit after opening.", FSE),
    ("If you will serve alcohol, apply for a new liquor license from the State Liquor Authority (licenses cannot be "
     "transferred).", INDUSTRY),
    ("Signs nailed or screwed into the building, or lit, need Department of Buildings approval; FDNY fire permits "
     "may apply to cooking equipment.", INDUSTRY),
]


@lru_cache(maxsize=1)
def _landmarks():
    path = os.path.join(DATA, "landmarks.json")
    if not os.path.exists(path):
        url = ("https://data.cityofnewyork.us/resource/ncre-qhxs.json?$select=bbl,lm_type,hist_distr,lm_name"
               "&$where=status='DESIGNATED'&$limit=60000")
        open(path, "wb").write(urllib.request.urlopen(url, timeout=120).read())
    out = {}
    for r in json.load(open(path)):
        if r.get("bbl"):
            out[r["bbl"].split(".")[0]] = r
    return out


def landmark(bbl):
    r = _landmarks().get(str(bbl or "").split(".")[0])
    if not r:
        return None
    dist = (r.get("hist_distr") or "").replace("Yes, ", "").replace("Yes. ", "")
    if r.get("lm_type") == "Historic District":
        return f"in the {dist} historic district" if dist and dist not in ("Yes", "No") else "in a historic district"
    return f"an individual landmark ({r.get('lm_name')})"


def for_lease(lease):
    """Address-specific items first, then the general requirements, each with its source."""
    items = []
    sf = lease.get("storefront") or {}
    lm = landmark(sf.get("bbl"))
    if lm:
        items.append({"step": f"This building is {lm}: storefront or sign changes need Landmarks Preservation "
                              "Commission approval before work starts.", "source": INDUSTRY, "specific": True})
    bid = lease.get("bid") or bids.bid_for(lease["lat"], lease["lon"])
    if bid:
        contact = ", ".join(x for x in (bid.get("phone"), bid.get("email")) if x)
        items.append({"step": f"Call the {bid['bid']} business improvement district: ask about the space, local foot "
                              "traffic and opening events" + (f". Contact: {contact}." if contact else "."),
                      "source": bid.get("website"), "specific": True})
    near = lease.get("partners") or {}
    if not bid and near.get("bids"):
        b = near["bids"][0]
        contact = ", ".join(x for x in (b.get("phone"), b.get("email")) if x)
        items.append({"step": f"The nearest business improvement district, {b['bid']}, is about {b['metres']} m away. "
                              "Its staff know the street and run local events" + (f"; contact {contact}." if contact else "."),
                      "source": b.get("website"), "specific": True})
    if near.get("complements"):
        names = "; ".join(f"{c['name']} ({c['kind']}, {c['metres']} m)" for c in near["complements"])
        items.append({"step": "Introduce yourself to independent neighbours that serve your customers at another moment, "
                              f"for cross-promotion at opening: {names}.", "source": near.get("source"), "specific": True})
    if sf.get("last_use") == "Food Services":
        items.append({"step": "The last reported use was food service. Ask the landlord what kitchen equipment, venting "
                              "and grease trap remain, and check the Certificate of Occupancy covers your use.",
                      "source": "https://data.cityofnewyork.us/d/92iy-9c3n", "specific": True})
    items += [{"step": s, "source": src, "specific": False} for s, src in GENERAL]
    return items


if __name__ == "__main__":
    import engine
    L = engine.rank("Korean", [{"address": "136-20 38th Ave, Queens"}, {"address": "300 Atlantic Ave, Brooklyn"}])
    for l in L:
        print(l["address"], l["storefront"])
        for i in for_lease(l)[:3]:
            print("  -", i["step"][:140])
