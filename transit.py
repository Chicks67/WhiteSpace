"""Foot-traffic proxy: average weekday subway entries at stations near a point (MTA open data).

Descriptive only: not tested as a predictor of openings or survival.
"""
import json
import os
import urllib.parse
import urllib.request
from functools import lru_cache

import engine

PATH = os.path.join(os.path.dirname(__file__), "data", "subway_ridership.json")
DAYS = ["2025-09-16", "2025-09-17", "2025-09-18"]  # Tue to Thu of a typical school-term week


def build():
    base = "https://data.ny.gov/resource/5wq4-mkjj.json?"
    tot = {}
    for day in DAYS:
        q = {"$select": "station_complex_id, station_complex, borough, avg(latitude) as lat, avg(longitude) as lon, "
                        "sum(ridership) as riders",
             "$where": f"transit_timestamp between '{day}T00:00:00' and '{day}T23:59:59'",
             "$group": "station_complex_id, station_complex, borough", "$limit": 1000}
        for r in json.load(urllib.request.urlopen(base + urllib.parse.urlencode(q), timeout=200)):
            t = tot.setdefault(r["station_complex_id"], {**r, "riders": 0.0})
            t["riders"] += float(r["riders"])
    st = [{**r, "daily_riders": round(r["riders"] / len(DAYS)), "lat": float(r["lat"]), "lon": float(r["lon"])}
          for r in tot.values()]
    json.dump({"period": "weekday average, " + ", ".join(DAYS),
               "source": "MTA Subway Hourly Ridership: Beginning 2025 (5wq4-mkjj)", "stations": st}, open(PATH, "w"))


@lru_cache(maxsize=1)
def stations():
    if not os.path.exists(PATH):
        build()
    return json.load(open(PATH))["stations"]


def near(lat, lon, radius=500):
    hits = []
    for s in stations():
        d = engine.metres(lat, lon, s["lat"], s["lon"])
        if d <= radius:
            hits.append({"station": s["station_complex"], "metres": round(d), "weekday_entries": s["daily_riders"]})
    hits.sort(key=lambda h: h["metres"])
    return {"subway_entries_within_500m": sum(h["weekday_entries"] for h in hits), "stations": hits[:4]}


if __name__ == "__main__":
    print(near(40.7590, -73.8303))
