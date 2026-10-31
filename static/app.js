"use strict";
const $ = (s, el = document) => el.querySelector(s);
const esc = s => String(s).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const DEFAULT_LEASES = ["136-20 38th Ave, Queens", "41-08 Bell Blvd, Queens", "35-01 Union St, Queens"];
const HEADINGS = ["Audience", "Brand voice", "Menu emphasis", "Music and decor", "Launch partners"];

const state = { leases: [], taste: [], mode: "city", panel: null, map: null, layers: null, running: false, calls: [],
  where: "goal", events: [], history: [], scout: null, live: true, redacted: false, abort: null, pins: new Map(),
  runId: 0 };   // runId changes on every new run, so late answers from an earlier run are dropped
const EXAMPLES = [
  { concept: "Korean cafe", goal: "College students on a budget, anywhere in Manhattan or Brooklyn. I'd rather not open next to lots of other Korean places." },
  { concept: "Pizzeria", goal: "Families with young children in Queens. A block with other restaurants and a subway stop nearby." },
  { concept: "Ramen shop", goal: "Office workers at lunch and young renters at night, in Brooklyn or Manhattan." },
  { concept: "Caribbean restaurant", goal: "Caribbean families and commuters in Brooklyn or the Bronx, near a busy subway station." },
  { concept: "Bakery", goal: "Morning commuters and parents in Queens or Brooklyn, away from other bakeries." },
];
/* Every pre-registered test, in order: number, question, result. Wording follows the README. */
const TESTS = [
  ["1", "Do Qloo cuisine heatmaps find blocks a cuisine has not reached yet? 14 cuisines, 648 first openings, 2024 to 2026.", "Qloo AUC 0.812 versus 0.742 for restaurant count."],
  ["2", "Do music-audience heatmaps carry resident taste?", "+0.064 AUC."],
  ["3", "Do two blind human raters prefer briefs written with Qloo evidence?", "Qloo briefs preferred 78% of the time."],
  ["4", "Which city-records score ranks storefronts, and does Qloo add to it?", "Lease score with Qloo 0.893 versus 0.851 without it."],
  ["4b", "Does that score extend to more cuisines?", "Yes, to 11 more: 25 cuisines, 83% of active restaurants."],
  ["5", "Does the lease score predict which restaurants last?", "Qloo taste added +0.013, a placebo +0.016. The lease score shows where operators open, not where they survive."],
  ["6", "Do Qloo's audience tags match census and jobs data across 181 neighbourhoods?", "2 of 7 tags matched (Affluent Diners, Business Professionals). Demographics come from the census."],
  ["7", "Given a storefront, does Qloo predict which cuisine opens there?", "+0.087 AUC over city records."],
  ["8", "Does a blind judge prefer briefs written with Qloo area evidence over briefs written with a list of nearby businesses?", "Qloo briefs preferred 76% (0.68 to 0.83)."],
  ["9", "Can a different use of Qloo (place records, not area lift) improve the brief, against a control that differs only by Qloo?", "Q over Q0 0.60 (0.433 to 0.767), over C+ 0.633 (0.483 to 0.80); the rule was not met."],
  ["10", "Is Qloo's list of competitors complete and current?", "Qloo finds 92.4% of competitors."],
  ["11", "Is a restaurant's Qloo scene about the restaurant or only its location?", "Specific to the restaurant (two unlike restaurants on one block share 0.225 of their lists), but nothing independent backs it. Shown as not validated and never used to choose where to open."],
  ["12", "Are Qloo's closing times and price levels right, against Google Maps?", "Closing times 29 of 30 within 30 minutes, all 29 exact; price levels 25 of 27 matched."],
  ["13", "Idea screen: which of seven other Qloo outputs for a restaurant are specific and stable enough to test further?", "Partners, scene and twin city passed; sound, brands, screen taste and words failed on consistency between sibling restaurants."],
  ["14", "Does Qloo's venue-to-artist affinity rank the acts a music venue really books (Ticketmaster)?", "Qloo 0.589 (0.518 to 0.668), above fame, not above genre. A language model alone: 0.814."],
  ["15", "Does artist-to-artist affinity rank the act that really opened for a headliner?", "Qloo 0.875, above fame (0.473) and genre (0.714). The model alone: 0.976 on the same shortlists."],
  ["16", "From no shortlist, does a model find more real openers when it sees Qloo's candidates?", "Qloo 0.721, combined 0.846."],
  ["17", "Does Qloo's affinity by city rank the markets an artist's tour really plays?", "Qloo 0.781 versus 0.693 baseline."],
  ["18", "Films a person rated highly (MovieLens): does Qloo rank them, and does a model do better with Qloo's scores?", "Qloo 0.873 versus average rating 0.815."],
  ["19", "A repeat of another team's tour-opener claim with a stated method.", "Qloo 0.824 versus 0.751 for the baseline."],
  ["20", "Asked when a real NYC restaurant closes on Friday, is a model right more often with Qloo's record than alone?", "Yes, for both models. GPT-6 Astra: 0 of 30 alone, 29 of 30 with Qloo. gemini-3.8-flash: 3 of 30 alone, 29 of 30 with Qloo."],
  ["21", "Is Qloo ahead of the model on lesser-known headliners?", "Qloo minus model +0.086."],
  ["22", "Screen: do model-written NYC plans send people to places that are shut, and does Qloo hold hours for enough of the stops to check them?", "Qloo held hours for 0.992 of the stops and flagged a stop in 0.567 of plans, but many flags looked like bad 'closed' records. The check by a person was not run and the idea was dropped."],
  ["23", "Does Qloo know which comedians share a crowd?", "Not shown on famous package tours: a pair who toured together outscored one who did not 0.612 of the time (0.464 to 0.797). Too few current comedy bills on Ticketmaster to test the rest."],
  ["24", "Do older acts that young people took up (TikTok trend lists) show a younger crowd in Qloo?", "Qloo 0.712 versus chance 0.333."],
  ["25", "Qloo on its home ground: small acts, brand-new restaurants, steadiness.", "Small acts: too few to say. 120 NYC restaurants opened after April 2026: Qloo held 55%; cuisine right 0.683 for the model alone, 0.658 with Qloo, not shown. Steadiness: model and Qloo both steady."],
  ["26", "Do MLB theme nights that suit a city's taste draw more people? 2,425 games, 336 theme nights.", "Qloo Spearman 0.284 versus model alone 0.099."],
  ["27", "On small artists (Last.fm listening data), does Qloo know a real listener's taste?", "Qloo AUC 0.841, far above popularity (0.516). Model alone 0.865, model with Qloo 0.874: no different from Qloo."],
  ["28", "Does a festival timetable built on Qloo's fan-overlap scores make fewer real fans choose?", "Yes. Qloo reached 0.663 of the possible gain, popularity 0.043; pair scores +0.031 (0.005 to 0.056). The model alone (0.669) and with Qloo (0.702) were no different."],
];
const NO_KEYS = "This needs a live connection that is not available here. The finished runs above show the full result.";

/* ---------- form ---------- */
function leaseRow(value = "") {
  const li = document.createElement("li");
  li.innerHTML = `<span class="num"></span><input aria-label="Lease address" maxlength="120" required>
    <button type="button" class="quiet" aria-label="Remove this address" title="Remove this address">\u00d7</button>`;
  $("input", li).value = value;
  $("button", li).onclick = () => { if ($("#leases").children.length > 2) { li.remove(); renumber(); } };
  $("#leases").append(li);
  renumber();
}
function renumber() {
  [...$("#leases").children].forEach((li, i) => { $(".num", li).textContent = i + 1; });
  $("#add-lease").disabled = $("#leases").children.length >= 5;
}
function showError(msg) { const e = $("#form-error"); e.textContent = msg || ""; e.hidden = !msg; }

/* ---------- streaming ---------- */
async function stream(url, opts) {
  const res = await fetch(url, { ...(opts || {}), signal: state.abort ? state.abort.signal : undefined });
  if (!res.ok) {
    let msg = `Request failed (${res.status}).`;
    try {
      const j = await res.json();
      msg = j.error || (Array.isArray(j.detail) ? "Check the concept and addresses: " + j.detail.map(d => d.msg).join("; ") : j.detail) || msg;
    } catch (_) {}
    throw new Error(msg);
  }
  const reader = res.body.getReader(), dec = new TextDecoder();
  let buf = "";
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buf += dec.decode(value, { stream: true });
    let i;
    while ((i = buf.search(/\r?\n\r?\n/)) >= 0) {
      const chunk = buf.slice(0, i); buf = buf.slice(i).replace(/^\r?\n\r?\n/, "");
      const data = chunk.split(/\r?\n/).filter(l => l.startsWith("data:")).map(l => l.slice(5).trim()).join("\n");
      if (data) handle(JSON.parse(data));
    }
  }
}

function announce(msg) { $("#announce").textContent = msg; }

function reset() {
  state.runId++;
  state.leases = []; state.taste = []; state.calls = []; state.events = []; state.history = []; state.scout = null;
  $("#thread").innerHTML = ""; $("#ask-panel").hidden = true; $("#repair-note").hidden = true; $("#next-panel").hidden = true;
  $("#steps").innerHTML = ""; $("#call-list").innerHTML = ""; $("#qloo-calls").hidden = true; $("#verdict").hidden = true;
  $("#credits").textContent = ""; $("#credits").classList.remove("bad"); $("#brief-panel").hidden = true; $("#rank-list").innerHTML = "";
  $("#around-panel").hidden = true; $("#around-body").innerHTML = ""; state.cuisine = null;
  $("#around-go").textContent = "Look it up with Qloo";
  $("#partners-panel").hidden = true; $("#copy-brief").hidden = true; state.brief = null; state.drafting = false;
  $("#app").hidden = false; $("#rank-note").hidden = true; $("#rank-wait").hidden = false;
  $("#run-title").textContent = $("#concept").value.trim() || "Scouting";
  setMode("city", false);
  if (window.L) ensureMap();
}

async function go(url, opts) {
  if (state.running) return false;
  state.running = true; state.abort = new AbortController(); showError("");
  $("#run").disabled = true; $("#run").classList.add("busy"); $("#stop").hidden = false;
  try {
    state.lastError = null;
    reset();
    startClock();
    $("#app").scrollIntoView({ behavior: "smooth", block: "start" });
    announce("Run started.");
    await stream(url, opts);
  }
  catch (e) {
    if (e.name === "AbortError") stopped(); else if (!$("#app").hidden) runError(e.message); else showError(e.message);
  }
  finally {
    state.running = false; state.abort = null; stopClock(); stopSlow();
    $("#run").classList.remove("busy"); $("#stop").hidden = true; setLive();
    broadcast({ type: "run_end" });   // Stop or a dropped connection must end the radar's "Calling" too
  }
  return true;
}

/* An error ends the run on the page: spinners stop and the message shows beside the results, not only in the form. */
function runError(msg) {
  state.lastError = msg;
  stopSlow();
  document.querySelectorAll("#steps li.running").forEach(li => { li.className = "error"; $(".ico", li).textContent = "\u2715"; });
  const t = $("#steps li.thinking"); if (t) t.remove();
  showError(msg);
  const c = $("#credits"); c.textContent = msg; c.classList.add("bad");
  announce("The run stopped: " + msg);
}

/* Stopping ends what this page shows. A live run already sent to the server finishes there. */
function stopped() {
  document.querySelectorAll("#steps li.running").forEach(li => { li.className = "stopped"; $(".ico", li).textContent = "\u25A0"; });
  const t = $("#steps li.thinking"); if (t) t.remove();
  $("#credits").textContent = "Stopped.";
}

let clock = null;
function startClock() {
  const t0 = Date.now(), el = $("#elapsed");
  el.hidden = false; $("#bar").hidden = false;
  const tick = () => { const s = Math.floor((Date.now() - t0) / 1000); el.textContent = `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`; };
  tick(); clearInterval(clock); clock = setInterval(tick, 1000);
}
function stopClock() { clearInterval(clock); clock = null; $("#bar").hidden = true; }

/* The run button says plainly when this server cannot run live. */
function setLive() {
  const run = $("#run");
  run.disabled = state.running;   // never a dead button: without live runs it plays the closest finished run
  run.textContent = "Scout this location";
  $("#run-hint").textContent = state.live ? "Takes about a minute. Ctrl or Cmd and Enter also runs."
    : "Shows the finished run closest to your plan. Ctrl or Cmd and Enter also runs.";
}

/* When a live run cannot happen (no live connection, the model busy or out of budget, rate limits), the button
   still gives a result: the finished run closest to the plan, labelled as such. Input errors keep their message. */
const TRANSIENT = /busy|budget|paused|try again|limited to|request failed|on our side|quota|not available|unavailable|failed to fetch|networkerror|load failed|network/i;
function closestRun(body) {
  const mode = body.goal ? "goal" : body.area ? "area" : "leases";
  const words = s => new Set(String(s || "").toLowerCase().split(/\W+/).filter(w => w.length > 2));
  const want = words(body.concept);
  let best = null, top = -1;
  for (const r of state.goldenRuns || []) {
    const m = r.request.goal ? "goal" : r.request.area ? "area" : "leases";
    let score = m === mode ? 3 : 0;
    for (const w of words(r.request.concept)) if (want.has(w)) score += 2;
    if (body.cuisine && body.cuisine === r.request.cuisine) score += 2;
    if (score > top) { top = score; best = r; }
  }
  return best;
}
/* The visitor's plan as typed, so a fallback replay (which fills the form with its own plan) can put it back. */
function formSnapshot() {
  return { concept: $("#concept").value, cuisine: $("#cuisine").value, where: state.where, goal: $("#goal").value,
    area: $("#area").value, leases: [...$("#leases").querySelectorAll("input")].map(i => i.value) };
}
function formRestore(f) {
  $("#concept").value = f.concept; $("#cuisine").value = f.cuisine; $("#goal").value = f.goal; $("#area").value = f.area;
  $("#leases").innerHTML = ""; (f.leases.length ? f.leases : ["", ""]).forEach(a => leaseRow(a));
  setWhere(f.where);
}
function playFinished(body, why) {
  const r = closestRun(body);
  if (!r) { showError(why + " There is no finished run to show on this server."); return; }
  state.fallbackNote = `${why} Showing the finished run closest to your plan: ${r.title}.`;
  const typed = formSnapshot();
  r.play();
  formRestore(typed);
  $("#credits").textContent = state.fallbackNote;
  toast("Showing a finished run for a similar plan.");
}

let toastTimer = null;
function toast(msg) {
  const t = $("#toast"); t.textContent = msg; t.hidden = false;
  clearTimeout(toastTimer); toastTimer = setTimeout(() => { t.hidden = true; }, 2200);
}
async function copyText(text, done) {
  try { await navigator.clipboard.writeText(text); toast(done); }
  catch (_) { toast("Copying is blocked in this browser."); }
}

/* ---------- events ---------- */
/* Every streamed event is also broadcast, so the agent radar (features.js) can draw the call as it happens. */
function broadcast(e) { try { dispatchEvent(new CustomEvent("ws:event", { detail: e })); } catch (_) {} }
function handle(e) {
  state.events.push(e);
  broadcast(e);
  if (e.type === "step") return step(e);
  if (e.type === "scout") return scoutStep(e);
  if (e.type === "scout_think") return scoutThink(e);
  if (e.type === "scout_hedge") return;
  if (e.type === "scout_turn" && e.model && !/astra/i.test(e.model)) return scoutStep({ status: "done", name: "note",
    summary: `this turn was answered by the fallback model (${e.model}) because the main one was slow` });
  if (e.type === "scout_result") { state.scout = e.data; return renderLeases(); }
  if (e.type === "qloo") return qcall(e);
  if (e.type === "concept") { state.cuisine = e.data.cuisine; return; }
  if (e.type === "leases") { state.leases = e.data; showAround(); announce(`Shortlist ready: ${e.data.length} storefronts.`); return renderLeases(); }
  if (e.type === "taste") { state.taste = e.data; return renderLeases(); }
  if (e.type === "evidence") { state.evidence = e.data; return; }
  if (e.type === "brief") { announce("Positioning brief written."); return renderBrief(e.data); }
  if (e.type === "brief_delta") return draft(e);
  if (e.type === "saved_followups") return e.data.slice().reverse().forEach(f => replayFollowup(f));
  if (e.type === "error") { runError(e.message); return; }
  if (e.type === "done") {
    stopSlow();
    announce("Run finished.");
    if (state.live) around();
    $("#credits").textContent = e.replay ? (state.fallbackNote || "A run recorded earlier, shown in full.")
      : e.usd != null ? `Model cost of this run: about $${e.usd.toFixed(2)}.` : `Model cost of this run: ${e.credits} Kie credits.`;
  }
}

/* A step or scout turn silent for 45 s says so, so a slow provider does not look like a hang. */
let slow = null;
function watchSlow(li, label) {
  clearInterval(slow);
  const t0 = Date.now();
  slow = setInterval(() => {
    const s = Math.round((Date.now() - t0) / 1000);
    if (s < 45 || !li.isConnected) return;
    let n = li.querySelector(".slow");
    if (!n) { n = document.createElement("span"); n.className = "slow"; li.append(n); }
    n.textContent = ` ${label} ${s} s so far: the model provider is slower than usual right now; the run is still going.`;
  }, 1000);
}
function stopSlow() { clearInterval(slow); slow = null; document.querySelectorAll("#steps .slow").forEach(n => n.remove()); }

function step(e) {
  if (e.status !== "running") stopSlow();
  let li = $(`#steps li[data-id="${e.id}"]`);
  if (!li) {
    li = document.createElement("li"); li.dataset.id = e.id;
    li.innerHTML = `<span class="ico" aria-hidden="true"></span><span><span class="lab"></span><span class="detail"></span></span>`;
    $("#steps").append(li);
  }
  li.className = e.status;
  if (e.id === "scout" && e.status !== "running") { const t = $("#steps li.thinking"); if (t) t.remove(); }
  $(".ico", li).textContent = e.status === "done" ? "✓" : e.status === "error" ? "✕" : "";
  $(".lab", li).textContent = e.label + (e.seconds != null ? ` (${e.seconds} s)` : "");
  if (e.status === "running" && e.id !== "scout") watchSlow($(".detail", li).parentNode, "Working:");
  const d = e.detail;
  $(".detail", li).textContent = !d ? "" : typeof d === "string" ? d
    : Object.entries(d).map(([k, v]) => `${k.replace("_", " ")}: ${v}`).join(", ");
}

function scoutThink(e) {
  let li = $("#steps li.thinking");
  if (!li) {
    li = document.createElement("li");
    li.className = "sub thinking";
    const host = $(`#steps li[data-id="scout"]`);
    if (host) host.parentNode.insertBefore(li, nextAfterSubs(host)); else $("#steps").append(li);
  }
  li.textContent = e.n === 1 ? "Reading your plan and choosing what to look up first" : "Weighing the results and planning the next move";
  watchSlow(li, "Thinking:");
}
function scoutStep(e) {
  if (e.status === "running") return;
  stopSlow();
  const t = $("#steps li.thinking");
  if (t) t.remove();
  const li = document.createElement("li");
  li.className = "sub " + (e.status === "error" ? "error" : "");
  li.textContent = `${e.name.replace(/_/g, " ")}: ${e.summary || ""}${e.seconds != null ? ` (${e.seconds} s)` : ""}`;
  const host = $(`#steps li[data-id="scout"]`);
  if (host) host.parentNode.insertBefore(li, nextAfterSubs(host)); else $("#steps").append(li);
}
function nextAfterSubs(host) {
  let n = host.nextSibling;
  while (n && n.classList && n.classList.contains("sub")) n = n.nextSibling;
  return n;
}

function qcall(e) {
  state.calls.push(e);
  const p = e.params || {};
  const what = [p["filter.type"], p["signal.interests.tags"] ? "for fans of this cuisine" : "",
    p["signal.location.query"] ? "NYC baseline" : p["signal.location"] ? "near the lease" : "",
    p["filter.location.query"] || ""].filter(Boolean).join(", ");
  const li = document.createElement("li");
  li.textContent = `${e.path} ${what}: ${e.status}${e.cached ? " (cached)" : ""}`;
  $("#call-list").append(li);
  const cached = state.calls.filter(c => c.cached).length;
  $("#qloo-count").textContent = `Qloo calls: ${state.calls.length} (${cached} from cache)`;
  $("#qloo-calls").hidden = false;
}

/* ---------- map ---------- */
function ensureMap() {
  if (state.map) { state.layers.clearLayers(); return; }
  // one canvas for the many restaurant dots, instead of an SVG node each
  state.map = L.map("map", { scrollWheelZoom: false, preferCanvas: true }).setView([40.73, -73.9], 11);
  L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
  }).addTo(state.map);
  state.layers = L.layerGroup().addTo(state.map);
}
function css(v) { return getComputedStyle(document.documentElement).getPropertyValue(v).trim(); }
function fitMap() {
  const pts = state.leases.map(l => [l.lat, l.lon]);
  if (state.map && pts.length) state.map.fitBounds(pts, { padding: [60, 60], maxZoom: 15 });
}
function focusLease(address) {
  const m = state.pins.get(address);
  if (!m) return;
  state.map.flyTo(m.getLatLng(), Math.max(state.map.getZoom(), 16), { duration: .6 });
  m.openTooltip();
  document.querySelectorAll("#rank-list > li").forEach(li => li.classList.toggle("on", li.dataset.key === address));
}
function drawMap() {
  if (!state.map || !state.leases.length) return;
  state.layers.clearLayers(); state.pins.clear();
  const city = css("--city"), seen = new Set(), pts = [];
  for (const l of state.leases) {
    for (const r of l.same_cuisine_400m) {
      const k = r.lat + "," + r.lon + r.name; if (seen.has(k)) continue; seen.add(k);
      L.circleMarker([r.lat, r.lon], { radius: 4, color: city, fillColor: city, fillOpacity: 1, weight: 1 })
        .bindTooltip(esc(r.name)).addTo(state.layers);
    }
    for (const r of l.openings_800m) {
      L.circleMarker([r.lat, r.lon], { radius: 6, color: city, fill: false, weight: 2 })
        .bindTooltip(`${esc(r.name)}, opened ${esc(r.opened)}`).addTo(state.layers);
    }
  }
  order().forEach((l, i) => {
    pts.push([l.lat, l.lon]);
    const m = L.marker([l.lat, l.lon], { icon: L.divIcon({ className: "", html: `<div class="lease-pin">${i + 1}</div>`, iconSize: [30, 30], iconAnchor: [15, 15] }), zIndexOffset: 1000 })
      .bindTooltip(esc(l.address), { direction: "top", offset: [0, -14] }).addTo(state.layers);
    m.on("click", () => {
      document.querySelectorAll("#rank-list > li").forEach(li => li.classList.toggle("on", li.dataset.key === l.address));
      const row = [...document.querySelectorAll("#rank-list > li")].find(li => li.dataset.key === l.address);
      if (row) row.scrollIntoView({ behavior: "smooth", block: "nearest" });
    });
    state.pins.set(l.address, m);
  });
  state.map.invalidateSize();
  state.map.fitBounds(pts, { padding: [60, 60], maxZoom: 15 });
}

/* ---------- ranking ---------- */
function tasteOf(l) { const t = state.taste.find(x => x.address === l.address); return t ? t : { taste: null, rank: null }; }
function order() {
  const L2 = [...state.leases];
  if (state.mode === "qloo" && state.taste.length) L2.sort((a, b) => (tasteOf(b).taste ?? -1) - (tasteOf(a).taste ?? -1));
  return L2;
}
function rankOf(l) { return state.mode === "qloo" ? tasteOf(l).rank : l.rank; }
function pct(n) { return n === 1 ? "1st" : n === 2 ? "2nd" : n === 3 ? "3rd" : `${n}th`; }

function renderLeases() {
  const list = $("#rank-list");
  const before = new Map([...list.children].map(li => [li.dataset.key, li.getBoundingClientRect().top]));
  list.innerHTML = ""; $("#rank-wait").hidden = state.leases.length > 0;
  for (const l of order()) {
    const t = tasteOf(l), li = document.createElement("li");
    li.dataset.key = l.address;
    const near = l.same_cuisine_400m.slice(0, 4).map(r => `${esc(r.name)} (${r.metres} m)`).join(", ");
    li.innerHTML = `<span class="pos">${rankOf(l) ?? "?"}</span>
      <div><span class="addr">${esc(l.address.replace(/, NY, USA$/, ""))}</span>${l.neighbourhood ? `<span class="hood">${esc(l.neighbourhood)}</span>` : ""}</div>
      <ul class="facts">
        <li class="lead"><b>${esc(l.density)}</b> restaurants in its block (busier than ${esc(l.density_percentile)}% of blocks)</li>
        <li class="lead"><b>${esc(l.same_cuisine_area)}</b> same cuisine in and around the block</li>
        <li><b>${l.same_cuisine_400m.length}</b> within 400 m</li>
        <li><b>${l.openings_800m.length}</b> opened within 800 m since 2024</li>
        ${l.subway ? `<li><b>${l.subway.subway_entries_within_500m.toLocaleString()}</b> weekday subway entries within 500 m</li>` : ""}
        <li class="taste">Qloo taste <b>${t.taste ?? "no data"}</b></li>
      </ul>
      ${l.score_percentile != null ? `<div class="score"><span class="meter" aria-hidden="true"><i style="width:${Math.max(2, Math.min(100, l.score_percentile))}%"></i></span>
        <span>Lease score higher than ${l.score_percentile}% of NYC restaurant blocks for this cuisine</span></div>` : ""}
      ${l.storefront ? `<p class="store">Reported vacant on ${esc(l.storefront.reported)}<span class="tag">${l.storefront.last_use ? "last use: " + esc(l.storefront.last_use) : "last use not reported"}</span></p>` : ""}
      ${near ? `<p class="nearby">Nearest: ${near}</p>` : ""}
      ${l.bid ? `<p class="nearby">Business improvement district: <a href="${esc(/^https?:/.test(l.bid.website || "") ? l.bid.website : "https://" + (l.bid.website || ""))}" target="_blank" rel="noopener">${esc(l.bid.bid)}</a>${l.bid.phone ? ", " + esc(l.bid.phone) : ""}</p>` : ""}
      ${reasonFor(l) ? `<p class="reason">${esc(reasonFor(l))}</p>` : ""}`;
    li.tabIndex = 0;
    li.setAttribute("aria-label", `${l.address.replace(/, NY, USA$/, "")}: press Enter to show it on the map`);
    li.onclick = ev => { if (!ev.target.closest("a")) focusLease(l.address); };
    li.onkeydown = ev => { if ((ev.key === "Enter" || ev.key === " ") && ev.target === li) { ev.preventDefault(); focusLease(l.address); } };
    list.append(li);
  }
  list.classList.toggle("qmode", state.mode === "qloo");
  // animate rows from their old positions so the reorder is visible
  const still = matchMedia("(prefers-reduced-motion: reduce)").matches;
  if (!still) for (const li of list.children) {
    const old = before.get(li.dataset.key); if (old == null) continue;
    const dy = old - li.getBoundingClientRect().top;
    if (dy) li.animate([{ transform: `translateY(${dy}px)` }, { transform: "none" }], { duration: 450, easing: "cubic-bezier(.2,.7,.2,1)" });
  }
  rankNote(); $("#rank-note").hidden = false;
  verdict();
  nextSteps();
  partners();
  drawMap();
}

/* Business improvement districts and complementary neighbours for the top pick, from city records. */
function partners() {
  const top = state.leases.find(l => l.rank === 1) || state.leases[0];
  const p = top && top.partners, panel = $("#partners-panel");
  if (!p || !((p.bids || []).length + (p.complements || []).length)) { panel.hidden = true; return; }
  const url = u => esc(/^https?:/.test(u) ? u : "https://" + u);
  $("#partners-title").textContent = `Local partners near ${top.address.replace(/, NY, USA$/, "")}`;
  $("#partners-body").innerHTML = (p.bids || []).map(b => `<article class="partner">
      <span class="m">Business improvement district, ${b.metres} m</span>
      <h3>${b.website ? `<a href="${url(b.website)}" target="_blank" rel="noopener">${esc(b.bid)}</a>` : esc(b.bid)}</h3>
      ${b.boundary ? `<p>${esc(b.boundary)}</p>` : ""}
      <p>${[b.phone && `<a href="tel:${esc(b.phone.replace(/[^\d+]/g, ""))}">${esc(b.phone)}</a>`,
        b.email && `<a href="mailto:${esc(b.email)}">${esc(b.email)}</a>`].filter(Boolean).join(" &middot; ")}</p>
    </article>`).join("") +
    ((p.complements || []).length ? `<article class="partner"><span class="m">Independent neighbours</span>
      <ul>${p.complements.map(c => `<li><b>${esc(c.name)}</b><span>${esc(c.kind)}, ${c.metres} m</span></li>`).join("")}</ul>
      ${p.source ? `<p><a href="${url(p.source)}" target="_blank" rel="noopener">Source: city inspection records</a></p>` : ""}
    </article>` : "");
  panel.hidden = false;
}

function nextSteps() {
  const top = state.leases.find(l => l.rank === 1) || state.leases[0];
  if (!top || !top.next_steps) { $("#next-panel").hidden = true; return; }
  $("#next-title").textContent = `Next steps for ${top.address.replace(/, NY, USA$/, "")}`;
  $("#next-list").innerHTML = top.next_steps.map(s => `<li class="${s.specific ? "specific" : ""}"><span>${esc(s.step)}` +
    (s.source ? `<a href="${esc(/^https?:/.test(s.source) ? s.source : "https://" + s.source)}" target="_blank" rel="noopener">source</a>` : "") + "</span></li>").join("");
  $("#next-panel").hidden = false;
}

function reasonFor(l) {
  if (!state.scout) return "";
  const p = state.scout.picks.find(p => p.address === l.address);
  return p ? p.reason : "";
}

function verdict() {
  const v = $("#verdict"), best = state.leases.filter(l => l.rank === 1);
  if (!best.length) { v.hidden = true; return; }
  const l = best[0], others = state.leases.length - best.length;
  const addr = best.map(b => esc(b.address.replace(/, NY, USA$/, ""))).join(" and ");
  v.innerHTML = `<b>${state.scout ? "Agent's top pick" : best.length > 1 ? "Tied best leases" : "Best lease"}: ${addr}.</b> ` +
    `${l.density} restaurants in its block (busier than ${l.density_percentile}% of blocks), ` +
    `${l.same_cuisine_area} of the same cuisine in and around it, ${l.openings_800m.length} opened within 800 m since 2024` +
    (state.scout ? "." : others ? `. Ranked above ${others} other lease${others > 1 ? "s" : ""} on city records.` : ".") +
    (state.scout ? `<p class="scout-summary">${esc(state.scout.summary)}</p>` : "") +
    (state.scout ? `<ul class="measured"><li class="nm-head">Measured for every pick:</li>` +
      ["cuisine fit (where this cuisine's operators opened recently; our best-tested signal)", "same-cuisine competition nearby",
       "the target customers' census share in the neighbourhood", "weekday subway entries within 500 m",
       "how busy the block is", "the storefront's vacancy report and last use", "the local business district and partners"]
        .map(g => `<li>${esc(g)}</li>`).join("") + `</ul>` : "") +
    (state.scout && (state.scout.not_measured || []).length ? `<ul class="not-measured"><li class="nm-head">Not measured here:</li>` +
      state.scout.not_measured.map(g => `<li>${esc(g)}</li>`).join("") + `</ul>` : "");
  v.hidden = false;
}

function rankNote() {
  const n = $("#rank-note"), med = state.panel ? state.panel.median : { city: "0.851", qloo: "0.893" };
  if (state.mode === "city" && state.scout) {
    n.className = "rank-note";
    n.textContent = `In the agent's order: it weighed your plan against census data on who lives and works in each neighbourhood, ` +
      `competition nearby and the city-records lease score (shown for each). The lease score found where a cuisine opened next at median AUC ${med.city}; ` +
      `it does not predict which restaurants survive.`;
  } else if (state.mode === "city") {
    n.className = "rank-note";
    n.textContent = `Ranked from city inspection records by how busy each lease's block is and how much of this cuisine is in and around it. ` +
      `In our pre-registered test this found where a cuisine opened next at median AUC ${med.city}. ` +
      `Leases in the same block tie. An opening shows where operators chose to go, not whether they survived.`;
  } else {
    n.className = "rank-note qloo";
    n.innerHTML = `<strong>Qloo taste.</strong> This order comes from Qloo's cuisine taste map. ` +
      `With Qloo the lease score reached AUC ${med.qloo}, against ${med.city} for city records alone.`;
  }
}

function setMode(mode, render = true) {
  $("#rank-note").hidden = !state.leases.length;
  state.mode = mode;
  document.querySelectorAll(".ranking .toggle button").forEach(b => b.setAttribute("aria-checked", String(b.dataset.mode === mode)));
  if (render && state.leases.length) renderLeases();
}

/* ---------- brief ---------- */
function mark(text, items, unverified, city = []) {
  const marks = items.map(it => ({ name: it.name, cls: "q", title: `From Qloo (${it.id}): ${it.group}` }))
    .concat(city.map(s => ({ name: s.name, cls: "c", title: `${s.city_match.kind === "business improvement district" ? "NYC business improvement district" : "In NYC inspection records"}: ${s.city_match.dba}, ${s.city_match.metres} m from the lease` })))
    .concat(unverified.map(n => ({ name: n, cls: "u", title: "Model suggestion, not from Qloo or city records. Check before use." })))
    .sort((a, b) => b.name.length - a.name.length);
  const spans = [];
  for (const m of marks) {
    const re = new RegExp(`(?<![\\w])${m.name.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}(?![\\w])`, "gi");
    for (const hit of text.matchAll(re)) {
      const a = hit.index, b = a + hit[0].length;
      if (!spans.some(s => a < s.b && b > s.a)) spans.push({ a, b, m });
    }
  }
  spans.sort((x, y) => x.a - y.a);
  let html = "", at = 0;
  for (const s of spans) {
    html += esc(text.slice(at, s.a)) + `<span class="${s.m.cls}" title="${esc(s.m.title)}">${esc(text.slice(s.a, s.b))}</span>`;
    at = s.b;
  }
  return html + esc(text.slice(at));
}

function draft(e) {
  $("#brief-panel").hidden = false;
  if (e.reset || !state.drafting) {
    state.drafting = true;
    $("#brief-title").textContent = "Writing the positioning brief\u2026";
    $("#sources-line").hidden = true; $("#repair-note").hidden = true;
    $("#brief-body").innerHTML = '<p class="sec draft"></p>';
  }
  if (e.text) $("#brief-body .draft").textContent += e.text;
}

/* Public replays carry the brief's checks but not its text, which was written from Qloo evidence. */
function renderRedactedBrief(b) {
  state.drafting = false; state.brief = null;
  $("#brief-panel").hidden = false; $("#copy-brief").hidden = true;
  $("#brief-legend").hidden = true; $("#evidence-used").hidden = true; $("#sources-line").hidden = true; $("#repair-note").hidden = true;
  $("#brief-title").textContent = `Positioning brief: ${b.area || b.lease || "top pick"}`;
  const list = a => (a || []).length ? a.map(esc).join(", ") : "none";
  $("#brief-body").innerHTML = `<div class="redacted">
    <p>This is a public copy of a recorded run. The brief was written from Qloo evidence, and Qloo data may not be
      republished, so its text is shown only on the live site. What the checks found is below.</p>
    <dl>
      <dt>Name check</dt><dd>${esc(b.name_check || "not recorded")}</dd>
      <dt>Traced to city records</dt><dd>${list(b.names_traced_to_city_records)}</dd>
      <dt>Traced to Qloo</dt><dd>${b.names_traced_to_qloo ?? 0}</dd>
      <dt>Replaced, could not be traced</dt><dd>${list(b.replaced_unverified_names)}</dd>
      <dt>Unverified names left</dt><dd>${list(b.unverified_names_left)}</dd>
      <dt>Problems flagged</dt><dd>${list(b.problems)}</dd>
    </dl></div>`;
  showAsk();
}

function renderBrief(b) {
  if (!b.sections) return renderRedactedBrief(b);
  state.drafting = false; state.brief = b;
  $("#brief-legend").hidden = false; $("#evidence-used").hidden = false; $("#copy-brief").hidden = false;
  $("#brief-panel").hidden = false;
  const fixed = (b.unverified_before_repair || []).filter(n => !(b.unverified_names || []).includes(n));
  $("#repair-note").textContent = fixed.length ? `The agent replaced ${fixed.length} name${fixed.length > 1 ? "s" : ""} it could not trace to Qloo or city records: ${fixed.join(", ")}.` : "";
  $("#repair-note").hidden = !fixed.length;
  showAsk();
  $("#brief-title").textContent = `Positioning brief: ${b.concept} in ${b.area}`;
  const used = new Set(b.linked);
  const names = b.names || [], city = names.filter(s => !s.qloo && s.city === "near");
  const own = names.filter(s => !s.qloo && s.city === "founder");
  const unv = names.length ? names.filter(s => !s.qloo && s.city !== "near" && s.city !== "founder").map(s => s.name) : b.unverified_names;
  if (names.length) {
    const nq = names.filter(s => s.qloo).length;
    $("#sources-line").innerHTML = `${names.length} ${names.length === 1 ? "business or brand" : "businesses and brands"} named: ` +
      `<span class="n-q">${nq} from Qloo</span>, <span class="n-c">${city.length} found in city records nearby</span>, ` +
      (own.length ? `${own.length} named in your plan, ` : "") + `<span class="n-u">${unv.length} unverified</span>.`;
    $("#sources-line").hidden = false;
  } else if (b.name_check && b.name_check !== "done") {
    $("#sources-line").textContent = "The name check could not run this time, so names in this brief are not marked.";
    $("#sources-line").hidden = false;
  } else $("#sources-line").hidden = true;
  $("#brief-body").innerHTML = HEADINGS.filter(h => b.sections[h]).map(h =>
    `<h3>${h}</h3><p class="sec">${mark(b.sections[h], b.evidence.filter(x => used.has(x.id) && !x.id.startsWith("T")), unv, city)}</p>`).join("") +
    (b.problems.length ? `<p class="flag">Checks flagged: ${esc(b.problems.join(", "))}</p>` : "");
  const groups = {};
  for (const it of b.evidence) (groups[it.group] = groups[it.group] || []).push(it);
  $("#evidence-list").innerHTML = "<dl>" + Object.entries(groups).map(([g, its]) =>
    `<dt>${esc(g)}</dt><dd>${its.map(i => used.has(i.id) ? `<span class="used">${esc(i.name)}</span>` : esc(i.name)).join(", ")}</dd>`).join("") +
    "</dl><p class='hint'>Names in colour were used in the brief. Items common to most of the neighbourhoods we profiled were removed first.</p>";
}

/* ---------- evidence panel ---------- */
function chart(rows) {
  const W = 760, rowH = 26, top = 24, left = 150, right = 30, H = top + rows.length * rowH + 30;
  const x0 = .5, x1 = .95, x = v => left + (v - x0) / (x1 - x0) * (W - left - right);
  const sorted = [...rows].sort((a, b) => b.city - a.city);
  const short = c => c.replace("Bakery Products/Desserts", "Bakery").replace("Coffee/Tea", "Coffee");
  let s = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Dot plot of AUC by cuisine: city-records score against Qloo taste">`;
  for (const t of [.5, .6, .7, .8, .9]) {
    s += `<line class="${t === .5 ? "mid" : "grid"}" x1="${x(t)}" x2="${x(t)}" y1="${top - 8}" y2="${H - 26}"/>`;
    s += `<text x="${x(t)}" y="${H - 8}" text-anchor="middle">${t.toFixed(1)}</text>`;
  }
  s += `<text x="${x(.5) + 4}" y="${top - 12}">coin flip</text>`;
  sorted.forEach((r, i) => {
    const y = top + i * rowH + rowH / 2;
    s += `<g class="row" data-i="${rows.indexOf(r)}"><rect class="hit" x="0" y="${y - rowH / 2}" width="${W}" height="${rowH}"/>
      <text class="lab" x="${left - 12}" y="${y + 4}" text-anchor="end">${esc(short(r.cuisine))}</text>
      <line class="gap" x1="${x(Math.min(r.city, r.qloo))}" x2="${x(Math.max(r.city, r.qloo))}" y1="${y}" y2="${y}"/>
      <circle class="d-qloo" cx="${x(r.qloo)}" cy="${y}" r="5.5"/><circle class="d-city" cx="${x(r.city)}" cy="${y}" r="5.5"/></g>`;
  });
  s += "</svg>";
  $("#chart").innerHTML = s;
  const tip = $("#tip"), fig = $(".chart-fig");
  $("#chart").querySelectorAll(".row").forEach(g => {
    g.addEventListener("mousemove", ev => {
      const r = rows[g.dataset.i], box = fig.getBoundingClientRect();
      tip.innerHTML = `<strong>${esc(short(r.cuisine))}</strong><br>City records ${r.city}, Qloo taste ${r.qloo}<br>Both together ${r.DSQ}<br>${r.openings} blocks with a new opening`;
      tip.hidden = false;
      tip.style.left = Math.max(0, Math.min(ev.clientX - box.left + 14, box.width - 270)) + "px";
      tip.style.top = (ev.clientY - box.top + 14) + "px";
    });
    g.addEventListener("mouseleave", () => { tip.hidden = true; });
  });
  $("#chart-table").innerHTML = `<table class="data"><thead><tr><th>Cuisine</th><th>Blocks with a new opening</th><th>City records</th><th>Qloo taste</th><th>Both together</th></tr></thead><tbody>` +
    sorted.map(r => `<tr><td>${esc(short(r.cuisine))}</td><td>${r.openings}</td><td>${r.city}</td><td>${r.qloo}</td><td>${r.DSQ}</td></tr>`).join("") + "</tbody></table>";
}

async function loadPanel() {
  const p = await (await fetch("/api/evidence")).json();
  state.panel = p;
  if (p.chart && p.chart.length) chart(p.chart);
  else $(".chart-fig").hidden = true;
  if (p.median) {
    $("#med-city").textContent = Number(p.median.city).toFixed(3);
    $("#med-qloo").textContent = Number(p.median.qloo).toFixed(3);
    $("#med-both").textContent = Number(p.median.b4 ?? p.median.DSQ).toFixed(3);
    $("#medians").hidden = false;
  }
  if (state.leases.length) rankNote();
}



async function loadHealth() {
  const h = await (await fetch("/health")).json();
  state.live = h.live !== false;
  setLive();
}

async function loadGolden() {
  const { runs, redacted } = await (await fetch("/api/golden")).json();
  state.redacted = !!redacted;
  if (redacted) $("#golden-hint").textContent = "Real runs we recorded earlier. Each one opens in seconds; the brief's full text is shown on the live site.";
  $("#golden").innerHTML = runs.length ? "" : `<li class="hint">No finished runs yet.</li>`;
  state.goldenRuns = runs;
  for (const r of runs) {
    const li = document.createElement("li");
    li.innerHTML = `<button type="button"><strong>${esc(r.title)}</strong><span>${r.request.goal ? "scouted from a plan" : r.request.area ? "searched " + esc(r.request.area) : r.request.leases.length + " addresses"}, recorded ${esc(r.recorded)}</span></button>`;
    r.play = () => $("button", li).click();
    $("button", li).onclick = ev => {
      if (state.running) return;
      if (ev && ev.isTrusted) state.fallbackNote = null;   // a visitor's own pick is not a fallback
      document.querySelectorAll("#golden li").forEach(x => x.classList.toggle("active", x === li));
      $("#concept").value = r.request.concept; $("#cuisine").value = r.request.cuisine || "";
      if (r.request.goal) { setWhere("goal"); $("#goal").value = r.request.goal; }
      else if (r.request.area) { setWhere("area"); $("#area").value = r.request.area; }
      else { setWhere("leases"); $("#leases").innerHTML = ""; r.request.leases.forEach(l => leaseRow(l.address)); }
      go(`/api/golden/${encodeURIComponent(r.id)}`);
    };
    $("#golden").append(li);
  }
}

function setWhere(w) {
  state.where = w;
  document.querySelectorAll(".mode-toggle button").forEach(b => b.setAttribute("aria-checked", String(b.dataset.where === w)));
  $("#where-area").hidden = w !== "area"; $("#where-leases").hidden = w !== "leases"; $("#where-goal").hidden = w !== "goal";
}

/* ---------- follow-ups ---------- */
function showAsk() {
  $("#ask-panel").hidden = false;
  const top = state.leases[0], second = state.leases[1];
  const qs = [top && "When do the competitors near the top lease close on Friday?",
    top && "Who are the competitors within 300 m of the top lease?",
    second && `Why does ${second.address.split(",")[0]} rank lower?`,
    "Find vacant storefronts in a different neighbourhood and compare them",
    "Does Qloo predict where to open?"].filter(Boolean);
  $("#chips").innerHTML = "";
  for (const q of qs) {
    const b = document.createElement("button"); b.type = "button"; b.textContent = q;
    b.onclick = () => { $("#question").value = q; $("#question").focus(); };
    $("#chips").append(b);
  }
}

function context() {
  const ctx = {};
  for (const e of state.events) {
    if (e.type === "scout_result") {
      ctx.order = "the scout's shortlist order: it weighs the founder's plan (target customers, competition, subway, street) " +
        "as well as the lease score, so it need not follow lease_score_percentile_nyc";
      ctx.scout_summary = e.data.summary;
    }
    if (e.type === "concept") { ctx.concept = e.data.label; ctx.cuisine = e.data.cuisine; }
    if (e.type === "leases") ctx.leases = e.data.map(l => ({ rank_in_this_set: l.rank, lease_score_percentile_nyc: l.score_percentile,
      address: l.address, restaurants_in_block: l.density, same_cuisine_in_and_around_block: l.same_cuisine_area,
      same_cuisine_within_400m: l.same_cuisine_400m.length, opened_within_800m_since_2024: l.openings_800m.length, storefront: l.storefront || undefined }));
    if (e.type === "brief") { ctx.brief_area = e.data.area; if (e.data.text) ctx.brief = e.data.text.slice(0, 2500); }
  }
  return ctx;
}

function followupItem(q, saved) {
  const li = document.createElement("li");
  li.innerHTML = `<p class="q"></p><ul class="tools"></ul><p class="a"></p>`;
  $(".q", li).textContent = q + (saved ? " (saved answer)" : "");
  $("#thread").prepend(li);
  return li;
}

function followupEvent(li, tools, e, q) {
  broadcast(e.type === "tool" ? { ...e, type: "scout", followup: true } : e);
  if (e.type === "tool") {
    let t = tools.get(e.n);
    if (!t) { t = document.createElement("li"); tools.set(e.n, t); $(".tools", li).append(t); }
    t.className = e.status;
    t.textContent = `${e.name.replace(/_/g, " ")}${e.summary ? ": " + e.summary : ""}${e.seconds != null ? ` (${e.seconds} s)` : ""}`;
  } else if (e.type === "answer") {
    $(".a", li).textContent = e.text;
    if (e.unchecked_numbers.length) li.insertAdjacentHTML("beforeend", `<p class="loose">Numbers not found in any tool result: ${esc(e.unchecked_numbers.join(", "))}. Treat them with care.</p>`);
    state.history.push({ q, a: e.text });
  } else if (e.type === "error") { $(".a", li).textContent = e.message; }
}

function replayFollowup(f) {
  const li = followupItem(f.q, true), tools = new Map();
  if (f.events) { for (const [, e] of f.events) followupEvent(li, tools, e, f.q); return; }
  // public copies keep the question, the tools used and the answer (or a note where it drew on Qloo data)
  (f.tools || []).forEach((name, n) => followupEvent(li, tools, { type: "tool", n, name, status: "done" }, f.q));
  followupEvent(li, tools, { type: "answer", text: f.answer || "", unchecked_numbers: f.unchecked_numbers || [] }, f.q);
}

async function ask(q) {
  if (!q || state.asking) return;
  if (!state.live) { const li = followupItem(q, false); $(".a", li).textContent = NO_KEYS; return; }
  state.asking = true; $(".ask-btn").disabled = true;
  const li = followupItem(q, false), tools = new Map(), run = state.runId;
  $(".a", li).textContent = "Thinking\u2026";
  try {
    const res = await fetch("/api/ask", { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question: q, context: context(),
        history: state.history.slice(-4).map(h => ({ q: h.q.slice(0, 300), a: h.a.slice(0, 2000) })) }) });
    if (!res.ok) { let m = `Request failed (${res.status}).`; try { m = (await res.json()).error || m; } catch (_) {} throw new Error(m); }
    const reader = res.body.getReader(), dec = new TextDecoder(); let buf = "";
    for (;;) {
      const { value, done } = await reader.read(); if (done) break;
      buf += dec.decode(value, { stream: true });
      let i;
      while ((i = buf.search(/\r?\n\r?\n/)) >= 0) {
        const chunk = buf.slice(0, i); buf = buf.slice(i).replace(/^\r?\n\r?\n/, "");
        const data = chunk.split(/\r?\n/).filter(l => l.startsWith("data:")).map(l => l.slice(5).trim()).join("\n");
        if (!data) continue;
        if (run !== state.runId) return;   // a new run started: this answer belongs to the old one
        followupEvent(li, tools, JSON.parse(data), q);
      }
    }
  } catch (err) { $(".a", li).textContent = err.message; }
  finally { state.asking = false; $(".ask-btn").disabled = false; if (run === state.runId) $("#question").value = ""; }
}

/* ---------- boot ---------- */
/* ---------- Qloo lookups (no model call) ---------- */
async function lookup(url, opts) {
  const res = await fetch(url, opts);
  const j = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(j.error || (typeof j.detail === "string" ? j.detail : `Request failed (${res.status}).`));
  return j;
}
function qfacts(q) {
  if (!q) return `<span class="nodetail">no Qloo details</span>`;
  const bits = [q.closes_friday ? `closes ${esc(q.closes_friday)} Fri` : ""].filter(Boolean);
  return `<span class="qf">${bits.join(", ")}</span>${q.mentions.length ? ` <span class="men">${q.mentions.map(esc).join(", ")}</span>` : ""}`;
}
/* The agent's top pick: rank 1 on city records (or the scout's first), whatever order the list is showing. */
function topLease() { return state.leases.find(l => l.rank === 1) || state.leases[0]; }

function showAround() {
  const top = topLease();
  $("#around-panel").hidden = !(top && state.cuisine);
  if (top) $("#around-title").textContent = `What is around ${top.address.replace(/, NY, USA$/, "")}`;
}

/* Friday closing times from Qloo's place records, on one axis from noon to 4 am. */
const hourOf = t => { const [h, m] = t.split(":").map(Number); return (h < 6 ? h + 24 : h) + m / 60; };
function hoursChart(places) {
  const rows = places.filter(p => p.q && p.q.closes_friday)
    .map(p => ({ name: p.name, t: p.q.closes_friday, late: p.q.open_late_friday, h: hourOf(p.q.closes_friday) }))
    .sort((a, b) => a.h - b.h);
  if (!rows.length) return "";
  const pct = h => Math.max(0, Math.min(100, (h - 12) / 16 * 100));
  const late = rows.filter(r => r.late).length;
  return `<h3>When they close on Friday</h3>
    <p class="hint">${rows.length} nearby place${rows.length > 1 ? "s" : ""} with hours in Qloo; ${late ? `${late} stay${late > 1 ? "" : "s"} open past 11 pm` : "none of these stays open past 11 pm"}.
      Qloo's Friday closing times matched Google Maps for 29 of 30 places in our Test 12.</p>
    <div class="hours" role="img" aria-label="${esc(rows.map(r => `${r.name} closes ${r.t}`).join("; "))}">
      <div class="hours-axis" aria-hidden="true"><span></span><span class="ticks"><span>noon</span><span>4 pm</span><span>8 pm</span><span>midnight</span><span>4 am</span></span><span></span></div>
      ${rows.map(r => `<div class="hours-row${r.late ? " late" : ""}"><span class="nm" title="${esc(r.name)}">${esc(r.name)}</span>
        <span class="lane"><i style="--w:${pct(r.h).toFixed(1)}%"></i></span><b>${esc(r.t)}</b></div>`).join("")}
    </div>`;
}

async function around() {
  const top = topLease(), body = $("#around-body"), btn = $("#around-go"), run = state.runId;
  if (!top || !state.cuisine) return;
  if (!state.live) { body.innerHTML = `<p class="form-error">${esc(NO_KEYS)}</p>`; return; }
  btn.disabled = true; body.innerHTML = `<p class="hint">Asking Qloo\u2026</p>`;
  try {
    const a = await lookup(`/api/around?concept=${encodeURIComponent(state.cuisine)}&lat=${top.lat}&lon=${top.lon}`);
    if (run !== state.runId) return;   // a new run started while Qloo answered
    const d = a.among_details;
    const row = (name, q, extra = "") => `<li><b>${esc(name)}</b>${extra} ${qfacts(q)}` +
      (q && q.closes_friday ? `<button type="button" class="duel-btn" data-name="${esc(name)}" title="Ask GPT-6 Astra when it closes, alone and with Qloo's record">ask the model</button>` : "") + `</li>`;
    body.innerHTML = `
      ${hoursChart([...a.competitors.map(c => ({ name: c.name, q: c.qloo })), ...a.also_tagged.map(c => ({ name: c.name, q: c }))])}
      <h3>${esc(a.competitors_in_city_records)} ${esc(a.concept)} restaurants within 1.5 km in city records</h3>
      ${a.competitors.length ? `<p class="hint">The ${esc(a.competitors.length)} nearest. Qloo holds details for ${esc(a.with_details)} of them.</p>
      <ul class="around-list">${a.competitors.map(c => row(c.name, c.qloo, ` <span class="m">${esc(c.metres)} m</span>`)).join("")}</ul>` : ""}
      ${a.with_details ? `<p class="among">Among the ${esc(a.with_details)} with details: ${[d.mentions.length && `reviewers mention most ${d.mentions.map(esc).join(", ")}`,
        d.latest_friday_close && `latest Friday closing ${esc(d.latest_friday_close)}`].filter(Boolean).join("; ")}.</p>` : ""}
      ${a.also_tagged.length ? `<h3>Also tagged ${esc(a.concept)} by Qloo, filed by the city under another category</h3>
      <ul class="around-list">${a.also_tagged.map(c => row(c.name, c)).join("")}</ul>` : ""}
      ${a.neighbours.length ? `<h3>Neighbours within 800 m that fans of ${esc(a.concept)} food rate highest</h3>
      <ul class="around-list">${a.neighbours.map(c => row(c.name, c, c.kind ? ` <span class="m">${esc(c.kind)}</span>` : "")).join("")}</ul>` : ""}
      ${a.unconfirmed.length ? `<p class="hint">Listed by Qloo but not found in city records, so not shown as operating: ${a.unconfirmed.map(esc).join(", ")}.</p>` : ""}
      <ul class="notes">${a.notes.map(n => `<li>${esc(n)}</li>`).join("")}</ul>`;
    btn.textContent = "Look it up again";
    if (window.L && state.layers) {
      const q = css("--qloo");
      for (const p of [...a.also_tagged, ...a.neighbours])
        L.circleMarker([p.lat, p.lon], { radius: 5, color: q, fillColor: q, fillOpacity: .85, weight: 1 }).bindTooltip(esc(p.name)).addTo(state.layers);
    }
  } catch (e) { if (run === state.runId) body.innerHTML = `<p class="form-error">${esc(e.message)}</p>`; }
  finally { btn.disabled = false; }
}
/* Test 20, live: the model alone against the model with Qloo's record, for one rival the founder picks. */
async function duel(btn) {
  const top = topLease(), li = btn.closest("li"), run = state.runId;
  if (!top) return;
  let box = li.querySelector(".duel");
  if (!box) { box = document.createElement("div"); box.className = "duel"; li.append(box); }
  if (!state.live) { box.innerHTML = `<p class="duel-note">${esc(NO_KEYS)}</p>`; return; }
  btn.disabled = true;
  box.innerHTML = `<p class="duel-note">Asking GPT-6 Astra twice: once on its own, once with Qloo's record\u2026</p>`;
  try {
    const d = await lookup("/api/duel", { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: btn.dataset.name, lat: top.lat, lon: top.lon }) });
    if (run !== state.runId) return;
    const said = t => t ? esc(t) : "doesn't know";
    box.innerHTML = `<div><span class="k">${esc(d.model)} alone</span><b>${said(d.alone)}</b></div>
      <div class="wq"><span class="k">${esc(d.model)} + Qloo</span><b>${said(d.with_qloo)}</b></div>
      <div class="rec"><span class="k">Qloo's record</span><b>${esc(d.qloo_closes_friday)}</b></div>
      <p class="duel-note">Friday closing time of ${esc(d.name)}. The same question as our Test 20, where the model alone was right
        for ${d.test20.alone_right} of ${d.test20.of} places and with Qloo for ${d.test20.with_qloo_right}. This live answer is not checked against Google Maps.</p>`;
  } catch (e) { if (run === state.runId) box.innerHTML = `<p class="duel-note">${esc(e.message)}</p>`; }
  finally { btn.disabled = false; }
}

/* Every recorded answer behind Test 20, loaded the first time the table is opened. */
async function loadTest20() {
  const body = $("#t20-body");
  if (body.dataset.loaded) return;
  body.dataset.loaded = "1";
  try {
    const d = await lookup("/api/test20");
    const cell = a => `<td class="${a.right ? "ok" : "no"}">${a.said ? esc(a.said) : "declined"}</td>`;
    const arms = ["large_alone", "large_with_qloo", "small_alone", "small_with_qloo"];
    body.innerHTML = `<div class="t20-wrap"><table class="data"><thead><tr><th>Restaurant</th><th>Google Maps</th>
      <th>GPT-6 Astra alone</th><th>GPT-6 Astra + Qloo</th><th>Gemini 3.8 Flash alone</th><th>Gemini + Qloo</th></tr></thead><tbody>` +
      d.rows.map(r => `<tr><td>${esc(r.name)}</td><td>${esc(r.google)}</td>${arms.map(a => cell(r[a])).join("")}</tr>`).join("") +
      `</tbody><tfoot><tr><td>Right</td><td></td>${arms.map(a => `<td>${esc(d.totals[a])} of ${esc(d.rows.length)}</td>`).join("")}</tr></tfoot></table></div>
      <p class="hint">${esc(d.rule[0].toUpperCase() + d.rule.slice(1))}. Recorded answers from the pre-registered test, not rerun.</p>`;
  } catch (e) { body.innerHTML = `<p class="hint">${esc(e.message)}</p>`; delete body.dataset.loaded; }
}

async function showScene() {
  const names = $("#anchors").value.split(",").map(s => s.trim()).filter(s => s.length > 1).slice(0, 3);
  const body = $("#scene-body"), err = $("#scene-error"), btn = $("#scene-go");
  err.hidden = true;
  if (!names.length) { err.textContent = "Name one to three places."; err.hidden = false; return; }
  if (!state.live) { err.textContent = NO_KEYS; err.hidden = false; return; }
  btn.disabled = true; body.innerHTML = `<p class="hint">Asking Qloo…</p>`;
  try {
    const s = await lookup("/api/scene", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ anchors: names }) });
    const found = s.anchors.map(a => `<b>${esc(a.name)}</b>${a.address ? `, ${esc(a.address)}` : ""}`).join("; ");
    let html = s.anchors.length ? `<p class="matched">Matched: ${found}.</p>` : "";
    if (s.not_found.length) html += `<p class="hint">Not found in Qloo: ${s.not_found.map(esc).join(", ")}.</p>`;
    if (s.no_signal) html += `<p class="among">${esc(s.note)}</p>`;
    if (s.places.length) {
      const taste = Object.entries(s.taste).filter(([, v]) => v.length)
        .map(([k, v]) => `<div><h4>${esc({ artist: "Music", brand: "Brands" }[k] || k)}</h4><p>${v.map(esc).join(", ")}</p></div>`).join("");
      html += `<div class="scene-grid"><div class="panel">
          <h3>${esc(s.label)}</h3>
          <p class="hint">${Math.round(100 * s.share_within_1500m_of_an_anchor)}% of these are within 1.5 km of a place you named.
            In our Test 11 a restaurant's list was specific to it, not just to its block, but nothing independent confirmed
            what the list means. We do not use it to choose where to open.</p>
          <ol class="scene-list">${s.places.map(p => `<li${p.in_city_records ? "" : ' class="unc"'}><b>${esc(p.name)}</b>
            <span class="m">${[p.kind, p.neighbourhood].filter(Boolean).map(esc).join(" · ")}</span></li>`).join("")}</ol>
          <p class="hint">Greyed names are not in city inspection records, so they may not be restaurants or may have closed.</p>
        </div>
        <div class="panel"><h3>What that crowd follows</h3>
          <p class="hint">Qloo's highest-affinity artists and brands for the places you named. Not validated by any test of ours.
            The artists change a lot from one place to the next; the brands less so, and New York food media turn up often.</p>
          <div class="taste-cols">${taste}</div></div></div>`;
    }
    body.innerHTML = html;
  } catch (e) { body.innerHTML = ""; err.textContent = e.message; err.hidden = false; }
  finally { btn.disabled = false; }
}

async function boot() {
  $("#around-go").onclick = around;
  $("#around-body").addEventListener("click", ev => { const b = ev.target.closest(".duel-btn"); if (b) duel(b); });
  $("#t20").addEventListener("toggle", () => { if ($("#t20").open) loadTest20(); });
  $("#scene-form").onsubmit = ev => { ev.preventDefault(); showScene(); };
  DEFAULT_LEASES.forEach(a => leaseRow(a));
  $("#add-lease").onclick = () => leaseRow("");
  document.querySelectorAll(".ranking .toggle button").forEach(b => b.onclick = () => setMode(b.dataset.mode));
  $("#table-toggle").onclick = () => {
    const t = $("#chart-table"), showTable = t.hidden;
    t.hidden = !showTable; $("#chart").hidden = showTable;
    $("#table-toggle").textContent = showTable ? "Show as chart" : "Show as table";
  };
  document.querySelectorAll(".mode-toggle button").forEach(b => b.onclick = () => setWhere(b.dataset.where));
  $("#brief-form").onsubmit = ev => {
    ev.preventDefault();
    const body = { concept: $("#concept").value.trim(), cuisine: $("#cuisine").value || null };
    if (state.where === "goal") {
      body.goal = $("#goal").value.trim();
      if (body.goal.length < 5) return showError("Describe your customers and where you would consider.");
    } else if (state.where === "area") {
      body.area = $("#area").value.trim();
      if (body.area.length < 2) return showError("Name a neighbourhood or borough to search.");
    } else {
      const leases = [...$("#leases").querySelectorAll("input")].map(i => i.value.trim()).filter(Boolean);
      if (leases.length < 2) return showError("Add at least two addresses to compare.");
      body.leases = leases.map(address => ({ address }));
    }
    state.fallbackNote = null;
    document.querySelectorAll("#golden li").forEach(x => x.classList.remove("active"));   // the visitor's own plan now
    if (!state.live) return playFinished(body, "Live scouting is not available right now.");
    go("/api/run", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }).then(ran => {
      if (ran && state.lastError && !state.leases.length && TRANSIENT.test(state.lastError)) playFinished(body, "The live run could not finish right now.");
    });
  };
  $("#ask-form").onsubmit = ev => { ev.preventDefault(); ask($("#question").value.trim()); };
  $("#print-report").onclick = () => window.print();
  $("#stop").onclick = () => { if (state.abort) state.abort.abort(); };
  $("#map-fit").onclick = fitMap;
  $("#tests-count").textContent = "Every test in order, 1 to 28";
  $("#tests").innerHTML = `<thead><tr><th>Test</th><th>Question</th><th>Result</th></tr></thead><tbody>` +
    TESTS.map(([n, q, r]) => `<tr><td>${esc(n)}</td><td>${esc(q)}</td><td>${esc(r)}</td></tr>`).join("") + "</tbody>";
  $("#copy-brief").onclick = () => {
    const b = state.brief; if (!b) return;
    copyText(`${$("#brief-title").textContent}\n\n` + HEADINGS.filter(h => b.sections[h]).map(h => `${h}\n${b.sections[h]}`).join("\n\n"), "Brief copied.");
  };
  for (const ex of EXAMPLES) {
    const b = document.createElement("button"); b.type = "button"; b.textContent = ex.concept;
    b.onclick = () => { $("#concept").value = ex.concept; $("#cuisine").value = ""; $("#goal").value = ex.goal; setWhere("goal"); countGoal(); $("#goal").focus(); };
    $("#examples").append(b);
  }
  const countGoal = () => { $("#goal-count").textContent = `${$("#goal").value.length} / 400`; };
  $("#goal").oninput = countGoal; countGoal();
  $("#brief-form").addEventListener("keydown", ev => {
    if (ev.key === "Enter" && (ev.ctrlKey || ev.metaKey)) { ev.preventDefault(); if (!$("#run").disabled) $("#brief-form").requestSubmit(); }
  });
  const themeBtn = $("#theme-toggle");
  const labelTheme = () => {
    const night = document.documentElement.dataset.theme === "night";
    themeBtn.setAttribute("aria-label", night ? "Switch to day sky" : "Switch to night sky");
    themeBtn.title = themeBtn.getAttribute("aria-label");
  };
  labelTheme();
  themeBtn.onclick = () => {
    const night = document.documentElement.dataset.theme !== "night";
    if (night) document.documentElement.dataset.theme = "night"; else delete document.documentElement.dataset.theme;
    try { localStorage.setItem("ws-theme", night ? "night" : "day"); } catch (_) {}
    labelTheme();
    if (state.leases.length) drawMap();   // map dots take their colour from the theme
  };
  // radio groups: arrow keys move the choice, as screen reader users expect
  document.querySelectorAll('[role="radiogroup"]').forEach(g => g.addEventListener("keydown", ev => {
    const step = { ArrowRight: 1, ArrowDown: 1, ArrowLeft: -1, ArrowUp: -1 }[ev.key];
    if (!step) return;
    const opts = [...g.querySelectorAll('[role="radio"]')], i = opts.indexOf(document.activeElement);
    if (i < 0) return;
    ev.preventDefault();
    const next = opts[(i + step + opts.length) % opts.length];
    next.focus(); next.click();
  }));
  const toTop = $("#to-top");
  toTop.onclick = () => scrollTo({ top: 0, behavior: "smooth" });
  addEventListener("scroll", () => { toTop.hidden = scrollY < 900; }, { passive: true });
  const links = [...document.querySelectorAll(".nav-links a")];
  const spy = new IntersectionObserver(es => es.forEach(e => {
    const here = "#" + ({ top: "business", saved: "scout", app: "scout", scene: "how" }[e.target.id] || e.target.id);   // sections without a link light up their nearest one
    if (e.isIntersecting) links.forEach(a => a.setAttribute("aria-current", String(a.getAttribute("href") === here)));
  }), { rootMargin: "-40% 0px -55% 0px" });
  ["top", "business", "scout", "saved", "app", "play", "why", "game", "results", "how", "scene", "evidence"].forEach(id => spy.observe(document.getElementById(id)));
  try {
    const { cuisines } = await (await fetch("/api/concepts")).json();
    for (const c of cuisines) $("#cuisine").insertAdjacentHTML("beforeend", `<option>${esc(c)}</option>`);
  } catch (_) {}
  loadPanel().catch(() => {});
  loadGolden().catch(() => {});
  loadHealth().catch(() => {});
}
boot();
