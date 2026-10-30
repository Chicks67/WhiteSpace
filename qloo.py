import hashlib
import json
import threading
import os
import time
import urllib.error
import urllib.parse
import urllib.request

BASE = "https://hackathon.api.qloo.com"
CACHE = (os.environ.get("QLOO_CACHE_DIR")  # private server storage only
         or ("/tmp/qloo-cache" if os.environ.get("VERCEL") else os.path.join(os.path.dirname(__file__), "cache")))  # Vercel: only /tmp is writable
# Hackathon keys allow 10,000 requests a month (X-Month-RateLimit-*). Keep a reserve so a busy judging day
# cannot use the month up: below it, uncached calls stop and live runs say so; cached and saved runs still work.
RESERVE = int(os.environ.get("QLOO_RESERVE", "300"))
QUOTA = {"remaining": None}
# Read-only copy of the responses every server needs (reference areas, cuisine heatmaps, saved runs' top picks),
# shipped inside the private server deployment so a fresh instance does not spend quota on them. Git-ignored:
# Qloo data never goes in the public repo. Built by warm_cache.py.
WARM = os.path.join(os.path.dirname(__file__), "qloo_warm")
USED = set()  # cache files read or written by this process (warm_cache.py collects them)


class QuotaLow(RuntimeError):
    pass
on_call = None  # optional callback(path, params, status, cached) for the agent trace
_local = threading.local()


def set_trace(cb):
    """Per-thread trace callback, so concurrent runs do not mix their traces."""
    _local.cb = cb


def _status(data):
    if "error" in data:
        return "error"
    res = data.get("results", {})
    if isinstance(res, list):  # /search returns a plain list
        return "ok" if res else "empty"
    return "ok" if any(res.get(k) for k in ("entities", "tags", "heatmap", "demographics")) else "empty"


def _report(path, params, data, cached):
    cb = getattr(_local, "cb", None) or on_call
    if cb:
        cb(path, params, _status(data), cached)


def _key():
    key = os.environ.get("QLOO_API_KEY")
    if key:
        return key
    path = os.path.join(os.path.dirname(__file__), ".env")
    if not os.path.exists(path):
        raise RuntimeError("QLOO_API_KEY is not set")
    with open(path) as f:
        for line in f:
            if line.startswith("QLOO_API_KEY="):
                return line.strip().split("=", 1)[1]


def get(path, **params):
    """GET a Qloo endpoint, cached on disk so repeat runs cost no API calls."""
    url = BASE + path + "?" + urllib.parse.urlencode(params)
    base = hashlib.md5(url.encode()).hexdigest() + ".json"
    name = os.path.join(CACHE, base)
    for hit in (name, os.path.join(WARM, base)):
        if os.path.exists(hit):
            with open(hit) as f:
                data = json.load(f)
            USED.add(base)
            _report(path, params, data, True)
            return data
    if QUOTA["remaining"] is not None and QUOTA["remaining"] < RESERVE:
        raise QuotaLow(f"Qloo monthly quota low ({QUOTA['remaining']} requests left); live runs are paused")
    req = urllib.request.Request(url, headers={"X-Api-Key": _key()})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=90) as r:
                left = r.headers.get("X-Month-RateLimit-Remaining")
                if left is not None:
                    QUOTA["remaining"] = int(float(left))
                data = json.load(r)
            break
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503) and attempt < 3:
                time.sleep(2 ** attempt)
                continue
            data = {"error": e.code, "body": e.read()[:300].decode()}
            _report(path, params, data, False)
            return data
        except (TimeoutError, urllib.error.URLError, ConnectionError, json.JSONDecodeError):  # dropped or cut-off reply
            if attempt == 3:
                data = {"error": "timeout"}
                _report(path, params, data, False)
                return data
            time.sleep(2 ** attempt)
    os.makedirs(CACHE, exist_ok=True)
    tmp = f"{name}.{os.getpid()}.{threading.get_ident()}.tmp"
    with open(tmp, "w") as f:  # write then rename, so a parallel reader never sees half a file
        json.dump(data, f)
    os.replace(tmp, name)
    USED.add(base)
    _report(path, params, data, False)
    return data


def results(data, field):
    return data.get("results", {}).get(field, [])
