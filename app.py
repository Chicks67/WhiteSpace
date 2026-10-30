"""Whitespace web server: static page, live agent runs over SSE, golden-run replays, evidence panel.

Keys stay in server environment variables. Live runs are rate limited per visitor and capped by a
daily LLM spend; saved runs replay with zero API calls.
"""
import asyncio
import json
import os
import threading
import time
from datetime import date

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, model_validator
from sse_starlette.sse import EventSourceResponse

import agent
import around
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
DAILY_CREDITS = float(os.environ.get("DAILY_CREDITS", "300"))
MAX_CONCURRENT = int(os.environ.get("MAX_CONCURRENT", "3"))

app = FastAPI(title="Whitespace")
app.mount("/static", StaticFiles(directory=os.path.join(ROOT, "static")), name="static")
_lock = threading.Lock()
_hits, _spend = {}, {"day": str(date.today()), "credits": 0.0}
_slots = threading.BoundedSemaphore(MAX_CONCURRENT)


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
        return self


def _visitor(request):
    fwd = request.headers.get("x-forwarded-for", "")
    return fwd.split(",")[0].strip() or (request.client.host if request.client else "unknown")


class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=300)
    context: dict
    history: list[dict] = Field(default_factory=list, max_length=10)


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


@app.on_event("startup")
def warm():
    threading.Thread(target=engine.city, daemon=True).start()


@app.get("/")
def index():
    return FileResponse(os.path.join(ROOT, "static", "index.html"), headers={"Cache-Control": "no-cache"})


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
            g = json.load(open(os.path.join(folder, name)))
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
    return {"run": run_id, "sha256": hashlib.sha256(open(path, "rb").read()).hexdigest()}


@app.get("/api/golden/{run_id}")
async def golden(run_id: str):
    path = os.path.join(_saved()[0], os.path.basename(run_id) + ".json")
    if not os.path.exists(path):
        raise HTTPException(404, "no such saved run")
    g = json.load(open(path))

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
    return _lookup(request, lambda: around.for_point(concept, lat, lon))


@app.post("/api/run")
async def run(req: RunRequest, request: Request):
    reason = _admit(_visitor(request))
    if reason:
        return JSONResponse({"error": reason}, status_code=429)
    loop, queue = asyncio.get_running_loop(), asyncio.Queue()
    emit = lambda e: loop.call_soon_threadsafe(queue.put_nowait, e)

    def work():
        if not _slots.acquire(timeout=60):
            emit({"type": "error", "message": "Server busy, try a saved run or retry shortly."})
            emit(None)
            return
        try:
            spent = agent.run(req.model_dump(exclude_none=True), emit)
            with _lock:
                _spend["credits"] += spent
        finally:
            _slots.release()
            emit(None)
    threading.Thread(target=work, daemon=True).start()

    async def stream():
        while True:
            e = await queue.get()
            if e is None:
                break
            yield {"data": json.dumps(e)}
    return EventSourceResponse(stream())


@app.post("/api/ask")
async def ask(req: AskRequest, request: Request):
    if len(json.dumps(req.context)) > 20000:
        return JSONResponse({"error": "Run context too large."}, status_code=413)
    reason = _admit(_visitor(request), "question", ASKS_PER_HOUR)
    if reason:
        return JSONResponse({"error": reason}, status_code=429)
    loop, queue = asyncio.get_running_loop(), asyncio.Queue()
    emit = lambda e: loop.call_soon_threadsafe(queue.put_nowait, e)

    def work():
        try:
            spent = followup.ask(req.question, req.context, req.history, emit)
            with _lock:
                _spend["credits"] += spent
        except Exception as e:
            msg = str(e)
            if llm.out_of_budget(msg):
                msg = "the language model is out of budget or busy right now; the saved answers still work"
            emit({"type": "error", "message": f"The agent could not answer: {msg[:200]}"})
        finally:
            emit(None)
    threading.Thread(target=work, daemon=True).start()

    async def stream():
        while True:
            e = await queue.get()
            if e is None:
                break
            yield {"data": json.dumps(e)}
    return EventSourceResponse(stream())
