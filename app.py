"""Whitespace web server: static page, live agent runs over SSE, golden-run replays, evidence panel.

Keys stay in server environment variables. Live runs are rate limited per visitor and capped by a
daily LLM spend; saved runs replay with zero API calls.
"""
import asyncio
import functools
import json
import os
import threading
import time
from contextlib import asynccontextmanager
from datetime import date

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, model_validator
from sse_starlette.sse import EventSourceResponse

import agent
import around
import duel
import engine
import evidence
import followup
import llm
import qloo
import scene

ROOT = os.path.dirname(__file__)
GOLDEN = os.environ.get("GOLDEN_DIR") or os.path.join(ROOT, "golden")  # private: Qloo-derived, never in the public repo
FIXTURES = os.path.join(ROOT, "fixtures", "replays")  # public, redacted copies: used when no full saved runs are here
RUNS_PER_HOUR = int(os.environ.get("RUNS_PER_HOUR", "4"))
ASKS_PER_HOUR = int(os.environ.get("ASKS_PER_HOUR", "15"))
LOOKUPS_PER_HOUR = int(os.environ.get("LOOKUPS_PER_HOUR", "30"))
DUELS_PER_HOUR = int(os.environ.get("DUELS_PER_HOUR", "10"))
DAILY_CREDITS = float(os.environ.get("DAILY_CREDITS", "300"))
MAX_CONCURRENT = int(os.environ.get("MAX_CONCURRENT", "3"))

SITE = os.environ.get("SITE_URL", "https://whitespace-nyc.vercel.app").rstrip("/")


@asynccontextmanager
async def lifespan(_app):
    threading.Thread(target=engine.city, daemon=True).start()  # build the city index before the first visitor needs it
    yield


# No public API explorer: the page is the interface, and the docs would only advertise the paid endpoints.
app = FastAPI(title="Whitespace", lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
app.mount("/static", StaticFiles(directory=os.path.join(ROOT, "static")), name="static")
_lock = threading.Lock()
_hits, _spend = {}, {"day": str(date.today()), "credits": 0.0}
_slots = threading.BoundedSemaphore(MAX_CONCURRENT)
_ask_slots = threading.BoundedSemaphore(2 * MAX_CONCURRENT)

CSP = ("default-src 'self'; script-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com; "
       "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdnjs.cloudflare.com; "
       "font-src https://fonts.gstatic.com; img-src 'self' data: https://tile.openstreetmap.org https://*.tile.openstreetmap.org https://cdnjs.cloudflare.com; "
       "connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'; object-src 'none'")


@app.middleware("http")
async def headers(request: Request, call_next):
    response = await call_next(request)
    h = response.headers
    h.setdefault("Content-Security-Policy", CSP)
    h.setdefault("X-Content-Type-Options", "nosniff")
    h.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    h.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
    if request.url.path.startswith("/static/") and response.status_code == 200:
        # asset URLs carry a ?v= version, so browsers and the CDN may keep them; unversioned ones revalidate daily
        h["Cache-Control"] = "public, max-age=31536000, immutable" if request.url.query else "public, max-age=86400"
    return response


class Cancelled(Exception):
    """The visitor closed the page: stop the run instead of spending on it."""


def _emitter(loop, queue, gone):
    def emit(e):
        if gone.is_set() and e is not None:
            raise Cancelled()
        loop.call_soon_threadsafe(queue.put_nowait, e)
    return emit


async def _drain(queue, gone):
    try:
        while True:
            e = await queue.get()
            if e is None:
                break
            yield {"data": json.dumps(e)}
    finally:
        gone.set()


def _friendly(e):
    """What a visitor may see of an error: messages written for them, else a plain line. Details go to the log."""
    msg = str(e)
    if llm.busy(msg):
        return "the language model is busy right now; please try again in a minute (the saved runs work meanwhile)"
    if llm.out_of_budget(msg):
        return "the language model is out of budget or busy right now; the saved answers still work"
    if isinstance(e, (engine.LeaseError, qloo.QuotaLow)) or type(e) is ValueError:
        return msg[:200]
    print("ask failed:", repr(e)[:500], flush=True)
    return "something went wrong on our side; please try again"


class Lease(BaseModel):
    address: str = Field(min_length=3, max_length=120)


class RunRequest(BaseModel):
    concept: str = Field(min_length=2, max_length=60)
    cuisine: str | None = None
    leases: list[Lease] | None = Field(default=None, min_length=2, max_length=5)
    area: str | None = Field(default=None, min_length=2, max_length=80)
    goal: str | None = Field(default=None, min_length=5, max_length=400)

    @model_validator(mode="after")
    def one_of(self):
        if not self.leases and not self.area and not self.goal:
            raise ValueError("describe your plan, name an area to search, or give two to five addresses")
        if sum(bool(x) for x in (self.leases, self.area, self.goal)) > 1:
            raise ValueError("choose one: describe your plan, name an area, or give addresses")
        return self


def _visitor(request):
    """The visitor's address. Vercel sets x-vercel-forwarded-for and x-real-ip itself, so they cannot be spoofed
    there; x-forwarded-for is the fallback for other hosts. IPv6 visitors are grouped by their /64 network."""
    h = request.headers
    ip = (h.get("x-vercel-forwarded-for") or h.get("x-real-ip") or h.get("x-forwarded-for", "")).split(",")[0].strip()
    ip = ip or (request.client.host if request.client else "unknown")
    return ":".join(ip.split(":")[:4]) if ":" in ip else ip


class Turn(BaseModel):
    q: str = Field(max_length=300)
    a: str = Field(max_length=2000)


class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=300)
    context: dict
    history: list[Turn] = Field(default_factory=list, max_length=4)


def _admit(ip, kind="run", per_hour=None, spend=True):
    """Rate limit and spend cap. Returns None if admitted, else the reason. Lookups make no model call, so the
    spend cap does not apply to them (spend=False)."""
    per_hour = per_hour or RUNS_PER_HOUR
    ip = f"{kind}:{ip}"
    now = time.time()
    with _lock:
        if _spend["day"] != str(date.today()):
            _spend.update(day=str(date.today()), credits=0.0)
        if spend and _spend["credits"] >= DAILY_CREDITS:
            return "Today's live-run budget is used up. The saved runs still work."
        if len(_hits) > 5000:  # forget visitors with nothing in the last hour
            for k in [k for k, v in _hits.items() if not v or now - v[-1] >= 3600]:
                del _hits[k]
        recent = [t for t in _hits.get(ip, []) if now - t < 3600]
        if len(recent) >= per_hour:
            return f"Live {kind}s are limited to {per_hour} per hour per visitor. The saved runs still work."
        _hits[ip] = recent + [now]
    return None


def _saved():
    """Where saved runs come from: the private full runs if this server has any, else the public redacted copies."""
    if os.path.isdir(GOLDEN) and any(n.endswith(".json") for n in os.listdir(GOLDEN)):
        return GOLDEN, False
    return FIXTURES, True


def _live():
    """Whether this server holds the keys a live run needs. Reports yes or no only, never a key."""
    return bool(llm.ENV.get("QLOO_API_KEY") and llm.ENV.get(llm.KEY_NAME))


@app.api_route("/", methods=["GET", "HEAD"])
def index():
    return FileResponse(os.path.join(ROOT, "static", "index.html"), headers={"Cache-Control": "no-cache"})


@app.get("/robots.txt")
def robots():
    return PlainTextResponse(f"User-agent: *\nAllow: /\nDisallow: /api/\nSitemap: {SITE}/sitemap.xml\n")


@app.get("/sitemap.xml")
def sitemap():
    xml = (f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
           f"<url><loc>{SITE}/</loc></url><url><loc>{SITE}/llms.txt</loc></url></urlset>\n")
    return Response(xml, media_type="application/xml")


@app.get("/favicon.ico")
def favicon():
    return FileResponse(os.path.join(ROOT, "static", "favicon.svg"), media_type="image/svg+xml",
                        headers={"Cache-Control": "public, max-age=86400"})


@app.get("/llms.txt")
def llms_txt():
    """A plain-text guide to the site for language models (llmstxt.org)."""
    return FileResponse(os.path.join(ROOT, "static", "llms.txt"), media_type="text/plain; charset=utf-8")


@app.get("/health")
def health():
    return {"ok": True, "spend_today": round(_spend["credits"], 2), "cap": DAILY_CREDITS, "live": _live()}


@app.get("/api/stats")
def stats():
    """Counts of the city data behind the page, for the header."""
    import nyc
    import storefronts
    out = {"cuisines": len(engine.CONCEPTS)}
    for key, fn in (("restaurants", nyc.restaurants), ("neighbourhoods", nyc.ntas), ("storefronts", storefronts.vacant)):
        try:
            out[key] = len(fn())
        except Exception:
            out[key] = None
    try:  # restaurants first inspected in the last full year that are still operating: a floor on yearly openings
        year = str(date.today().year - 1)
        city = engine.city()
        out["opened_last_year"] = {"year": year, "count": sum(1 for r in city.rest if (r["opened"] or "").startswith(year)),
                                   "active_four_boroughs": len(city.rest)}
    except Exception:
        out["opened_last_year"] = None
    return out


@app.get("/api/concepts")
def concepts():
    return {"cuisines": list(engine.CONCEPTS)}


@app.get("/api/evidence")
def evidence_panel():
    return evidence.panel()


@app.get("/api/golden")
def golden_list():
    out = []
    folder, redacted = _saved()
    for name in sorted(os.listdir(folder)) if os.path.isdir(folder) else []:
        if name.endswith(".json"):
            with open(os.path.join(folder, name)) as f:
                g = json.load(f)
            out.append({"id": name[:-5], "title": g["title"], "request": g["request"], "recorded": g["recorded"],
                        "order": g.get("order", 99)})
    return {"runs": sorted(out, key=lambda r: (r["order"], "goal" not in r["request"], r["id"])), "redacted": redacted}


@app.get("/api/golden/{run_id}/sha256")
def golden_hash(run_id: str):
    """Hash of the full saved run the server replays; compare with fixtures/replays/SHA256SUMS in the repo."""
    import hashlib
    path = os.path.join(GOLDEN, os.path.basename(run_id) + ".json")
    if not os.path.exists(path):
        raise HTTPException(404, "no such saved run")
    with open(path, "rb") as f:
        return {"run": run_id, "sha256": hashlib.sha256(f.read()).hexdigest()}


@app.get("/api/golden/{run_id}")
async def golden(run_id: str):
    path = os.path.join(_saved()[0], os.path.basename(run_id) + ".json")
    if not os.path.exists(path):
        raise HTTPException(404, "no such saved run")
    with open(path) as f:
        g = json.load(f)

    async def replay():
        last = None
        for t, e in g["events"]:
            if last is not None:
                await asyncio.sleep(min(t - last, 0.6))  # keep the real order, compress the waits
            last = t
            yield {"data": json.dumps({**e, "replay": True})}
        if g.get("followups"):
            yield {"data": json.dumps({"type": "saved_followups", "data": g["followups"]})}
    return EventSourceResponse(replay())


class SceneRequest(BaseModel):
    anchors: list[str] = Field(min_length=1, max_length=3)


def _lookup(request, fn):
    """A Qloo-only lookup (no model call): rate limited per visitor, and stopped by the Qloo quota guard."""
    reason = _admit(_visitor(request), "lookup", LOOKUPS_PER_HOUR, spend=False)
    if reason:
        return JSONResponse({"error": reason}, status_code=429)
    try:
        return fn()
    except qloo.QuotaLow:
        return JSONResponse({"error": "Live Qloo lookups are paused to protect this month's quota. The saved runs still work."},
                            status_code=503)


@app.post("/api/scene")
def scene_lookup(req: SceneRequest, request: Request):
    names = [a.strip()[:80] for a in req.anchors if len(a.strip()) >= 2]
    if not names:
        raise HTTPException(422, "name one to three places")
    return _lookup(request, lambda: scene.for_anchors(names))


@app.get("/api/around")
def around_lookup(concept: str, lat: float, lon: float, request: Request):
    if concept not in engine.CONCEPTS or not (40.45 <= lat <= 40.95 and -74.3 <= lon <= -73.65):
        raise HTTPException(422, "give a tested cuisine and a point in New York City")
    lat, lon = round(lat, 3), round(lon, 3)  # about 100 m: nearby requests share one cached Qloo lookup
    return _lookup(request, lambda: around.for_point(concept, lat, lon))


PINS_PER_HOUR = int(os.environ.get("PINS_PER_HOUR", "300"))
CITY_BOX = (40.54, -74.04, 40.915, -73.70)   # south, west, north, east: the four boroughs we cover


@functools.lru_cache(maxsize=1)
def _city_map():
    """Every active restaurant and every vacant storefront as 16-bit grid positions inside CITY_BOX, packed to
    base64, with one cuisine index per restaurant. Public city records only; built once per process."""
    import base64
    import struct
    import storefronts
    s, w, n, e = CITY_BOX
    q = lambda lat, lon: (round((lon - w) / (e - w) * 65535), round((n - lat) / (n - s) * 65535))
    inside = lambda r: s <= r["lat"] <= n and w <= r["lon"] <= e
    rest = [r for r in engine.city().rest if inside(r)]
    cuisines = sorted({c for c, _ in engine.CONCEPTS.values()})
    code = {c: i + 1 for i, c in enumerate(cuisines)}
    shop = [v for v in storefronts.vacant() if v.get("lat") and inside(v)]
    pack = lambda pts: base64.b64encode(b"".join(struct.pack("<HH", *q(p["lat"], p["lon"])) for p in pts)).decode()
    return {"box": CITY_BOX, "restaurants": pack(rest), "storefronts": pack(shop),
            "cuisine": base64.b64encode(bytes(code.get(r["cuisine"], 0) for r in rest)).decode(),
            "cuisines": cuisines, "concepts": {k: v[0] for k, v in engine.CONCEPTS.items()},
            "counts": {"restaurants": len(rest), "storefronts": len(shop)}}


@app.get("/api/citymap")
def city_map():
    return JSONResponse(_city_map(), headers={"Cache-Control": "public, max-age=86400"})


@app.get("/api/pin")
def pin_score(concept: str, lat: float, lon: float, request: Request):
    """The lease score for any point, from city records only: no Qloo call and no model call."""
    if concept not in engine.CONCEPTS or not (40.45 <= lat <= 40.95 and -74.3 <= lon <= -73.65):
        raise HTTPException(422, "give a tested cuisine and a point in New York City")
    reason = _admit(_visitor(request), "pin", PINS_PER_HOUR, spend=False)
    if reason:
        return JSONResponse({"error": reason}, status_code=429)
    s = engine.city().score(concept, round(lat, 5), round(lon, 5))
    return {**s, "concept": concept, "lat": lat, "lon": lon,
            "same_cuisine_400m": s["same_cuisine_400m"][:12], "openings_800m": s["openings_800m"][:12],
            "same_cuisine_400m_count": len(s["same_cuisine_400m"]), "openings_800m_count": len(s["openings_800m"])}


@app.get("/api/whatif")
def what_if(concept: str, density: int = Query(ge=0, le=200), same: int = Query(ge=0, le=200)):
    """The lease score percentile for a block with this many restaurants and this much of the cuisine around it."""
    if concept not in engine.CONCEPTS:
        raise HTTPException(422, "give a tested cuisine")
    m = engine.MODEL[concept]
    score = m["intercept"] + m["D"] * engine.math.log1p(density) + m["S"] * engine.math.log1p(same)
    c = engine.city()
    return {"score": round(score, 3), "score_percentile": c.percentile(concept, score),
            "density_percentile": c.density_percentile(density)}


@app.get("/api/test20")
def test20_answers():
    """Every recorded answer behind Test 20's result, for the page's table (built privately by warm_cache.py)."""
    path = os.path.join(qloo.WARM, "test20_answers.json")
    if not os.path.exists(path):
        raise HTTPException(404, "not available on this server")
    with open(path) as f:
        return json.load(f)


class DuelRequest(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    lat: float = Field(ge=40.45, le=40.95)
    lon: float = Field(ge=-74.3, le=-73.65)


@app.post("/api/duel")
def duel_lookup(req: DuelRequest, request: Request):
    """Test 20, live: the model alone against the model with Qloo's record, for one real place. Two short model calls."""
    reason = _admit(_visitor(request), "duel", DUELS_PER_HOUR)
    if reason:
        return JSONResponse({"error": reason}, status_code=429)
    try:
        out, spent = duel.run(req.name.strip(), req.lat, req.lon)
    except qloo.QuotaLow:
        return JSONResponse({"error": "Live Qloo lookups are paused to protect this month's quota."}, status_code=503)
    except duel.NoRecord as e:
        return JSONResponse({"error": str(e)}, status_code=404)
    except Exception as e:
        msg = _friendly(e)
        return JSONResponse({"error": msg[:1].upper() + msg[1:]}, status_code=502)
    with _lock:
        _spend["credits"] += spent
    return out


@app.post("/api/run")
async def run(req: RunRequest, request: Request):
    reason = _admit(_visitor(request))
    if reason:
        return JSONResponse({"error": reason}, status_code=429)
    loop, queue, gone = asyncio.get_running_loop(), asyncio.Queue(), threading.Event()
    emit = _emitter(loop, queue, gone)

    def work():
        if not _slots.acquire(timeout=60):
            emit({"type": "error", "message": "Server busy, try a saved run or retry shortly."})
            emit(None)
            return
        try:
            spent = agent.run(req.model_dump(exclude_none=True), emit)
            with _lock:
                _spend["credits"] += spent
        except Cancelled:
            pass
        finally:
            _slots.release()
            emit(None)
    threading.Thread(target=work, daemon=True).start()
    return EventSourceResponse(_drain(queue, gone))


@app.post("/api/ask")
async def ask(req: AskRequest, request: Request):
    if len(json.dumps(req.context)) > 20000:
        return JSONResponse({"error": "Run context too large."}, status_code=413)
    reason = _admit(_visitor(request), "question", ASKS_PER_HOUR)
    if reason:
        return JSONResponse({"error": reason}, status_code=429)
    loop, queue, gone = asyncio.get_running_loop(), asyncio.Queue(), threading.Event()
    emit = _emitter(loop, queue, gone)
    history = [t.model_dump() for t in req.history]

    def work():
        if not _ask_slots.acquire(timeout=30):
            emit({"type": "error", "message": "The agent is busy with other questions; please ask again shortly."})
            emit(None)
            return
        try:
            spent = followup.ask(req.question, req.context, history, emit)
            with _lock:
                _spend["credits"] += spent
        except Cancelled:
            pass
        except Exception as e:
            emit({"type": "error", "message": f"The agent could not answer: {_friendly(e)}"})
        finally:
            _ask_slots.release()
            emit(None)
    threading.Thread(target=work, daemon=True).start()
    return EventSourceResponse(_drain(queue, gone))
