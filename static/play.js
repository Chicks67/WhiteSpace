"use strict";
/* The two things to play with: drop a pin (the city-records lease score for any block, from /api/pin and
   /api/whatif, which call neither a model nor Qloo) and beat the model (a closing-time guessing game over the
   recorded Test 20 answers from /api/test20). Uses $ and esc from app.js. */

const reduced = () => matchMedia("(prefers-reduced-motion: reduce)").matches;
const cssVar = v => getComputedStyle(document.documentElement).getPropertyValue(v).trim();
async function getJSON(url) {
  const res = await fetch(url);
  const j = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(j.error || (typeof j.detail === "string" ? j.detail : "That did not work. Try another spot."));
  return j;
}

/* ---------- drop a pin ---------- */
const SPOTS = [
  ["Astoria, Queens", 40.7644, -73.9235], ["Williamsburg, Brooklyn", 40.7144, -73.9573], ["Flushing, Queens", 40.7590, -73.8303],
  ["Harlem, Manhattan", 40.8116, -73.9465], ["Fordham, the Bronx", 40.8616, -73.8905], ["Park Slope, Brooklyn", 40.6710, -73.9814],
  ["Jackson Heights, Queens", 40.7498, -73.8846], ["East Village, Manhattan", 40.7265, -73.9840], ["Bushwick, Brooklyn", 40.6958, -73.9171],
  ["Sunset Park, Brooklyn", 40.6455, -74.0101], ["Arthur Avenue, the Bronx", 40.8550, -73.8880], ["Long Island City, Queens", 40.7447, -73.9485],
];
const LETTERS = ["A", "B", "C"];
const pins = { map: null, layer: null, list: [], seq: 0 };

function pinMap() {
  if (pins.map || !window.L) return;
  pins.map = L.map("pin-map", { scrollWheelZoom: false, preferCanvas: true }).setView([40.735, -73.93], 12);
  L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19, attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
  }).addTo(pins.map);
  pins.layer = L.layerGroup().addTo(pins.map);
  pins.map.on("click", ev => dropPin(ev.latlng.lat, ev.latlng.lng));
}

async function dropPin(lat, lon, name = "") {
  if (pins.list.length >= 3) pins.list.shift();
  const p = { id: ++pins.seq, lat, lon, name, data: null, error: "" };
  pins.list.push(p);
  await scorePin(p);
  drawPins();
}
async function scorePin(p) {
  try { p.data = await getJSON(`/api/pin?concept=${encodeURIComponent($("#pin-cuisine").value)}&lat=${p.lat}&lon=${p.lon}`); p.error = ""; }
  catch (e) { p.data = null; p.error = e.message; }
}
function drawPins() {
  if (!pins.layer) return;
  pins.layer.clearLayers();
  const city = cssVar("--city");
  const best = Math.max(-1, ...pins.list.filter(p => p.data).map(p => p.data.score_percentile));
  const contest = pins.list.filter(p => p.data).length > 1;
  pins.list.forEach((p, i) => {
    if (p.data) for (const r of p.data.same_cuisine_400m)
      L.circleMarker([r.lat, r.lon], { radius: 4, color: city, fillColor: city, fillOpacity: .9, weight: 1 }).bindTooltip(esc(r.name)).addTo(pins.layer);
    const fresh = i === pins.list.length - 1 && !reduced();
    L.marker([p.lat, p.lon], { icon: L.divIcon({ className: "", html: `<div class="drop-pin${fresh ? " land" : ""}"><b>${LETTERS[i]}</b></div>`,
      iconSize: [34, 34], iconAnchor: [17, 34] }), zIndexOffset: 1000 }).addTo(pins.layer);
  });
  $("#pin-empty").hidden = pins.list.length > 0;
  $("#pin-cards").innerHTML = pins.list.map((p, i) => {
    const d = p.data, where = p.name || `${p.lat.toFixed(4)}, ${p.lon.toFixed(4)}`;
    if (!d) return `<article class="panel pin-card" data-i="${i}"><div class="ph-row"><h3><span class="tagpin">${LETTERS[i]}</span>${esc(where)}</h3>
      <button type="button" class="x" data-x="${i}" aria-label="Remove pin ${LETTERS[i]}">×</button></div><p class="form-error">${esc(p.error)}</p></article>`;
    const win = contest && d.score_percentile === best;
    const empty = d.density === 0;
    return `<article class="panel pin-card${win ? " win" : ""}" data-i="${i}" tabindex="0" title="Show this pin on the map">
      <div class="ph-row"><h3><span class="tagpin">${LETTERS[i]}</span>${esc(where)}</h3>
        <span>${win ? `<span class="crown">Best spot</span>` : ""}<button type="button" class="x" data-x="${i}" aria-label="Remove pin ${LETTERS[i]}">×</button></span></div>
      ${empty ? `<p class="hint">No restaurant in this block in city records: an empty block scores low, because new openings follow busy blocks.</p>` : ""}
      <p class="pct">${d.score_percentile}%<small>of NYC restaurant blocks score lower for ${esc(d.concept)}</small></p>
      <span class="gauge" aria-hidden="true"><i data-w="${Math.max(2, d.score_percentile)}"></i></span>
      <ul class="facts">
        <li class="lead"><b>${d.density}</b> restaurants in the block</li>
        <li class="lead"><b>${d.same_cuisine_area}</b> same cuisine in and around it</li>
        <li><b>${d.same_cuisine_400m_count}</b> within 400 m</li>
        <li><b>${d.openings_800m_count}</b> opened within 800 m since 2024</li>
      </ul>
      ${d.same_cuisine_400m.length ? `<p class="near">Nearest: ${d.same_cuisine_400m.slice(0, 3).map(r => `${esc(r.name)} (${r.metres} m)`).join(", ")}</p>` : ""}
    </article>`;
  }).join("");
  requestAnimationFrame(() => document.querySelectorAll("#pin-cards [data-w]").forEach(g => { g.style.width = g.dataset.w + "%"; }));
  const last = [...pins.list].reverse().find(p => p.data);
  if (last) seedWhatIf(last.data, LETTERS[pins.list.indexOf(last)]);
  pinGoal();
}
async function rescoreAll() {
  await Promise.all(pins.list.map(scorePin));
  drawPins();
  whatIf();
}
function pinBoot() {
  if (!$("#play")) return;
  const fill = list => { $("#pin-cuisine").innerHTML = list.map(c => `<option${c === "Korean" ? " selected" : ""}>${esc(c)}</option>`).join(""); };
  fetch("/api/concepts").then(r => r.json()).then(j => { fill(j.cuisines); pinGoal(); }).catch(() => { fill(["Korean"]); pinGoal(); });
  $("#pin-cuisine").onchange = () => { rescoreAll(); pinGoal(); };
  $("#pin-clear").onclick = () => { pins.list = []; drawPins(); };
  $("#pin-addr").onsubmit = async ev => {   // the keyboard route to the map: type an address, get a scored pin
    ev.preventDefault();
    const q = $("#pin-q").value.trim(); if (q.length < 3) return;
    const btn = $("#pin-addr button"); btn.disabled = true;
    try {
      const g = await getJSON(`/api/geocode?q=${encodeURIComponent(q)}`);
      if (pins.map) pins.map.flyTo([g.lat, g.lon], 16, { duration: reduced() ? 0 : .8 });
      await dropPin(g.lat, g.lon, g.label);
      $("#pin-q").value = "";
    } catch (e) { $("#pin-goal").textContent = e.message; }
    finally { btn.disabled = false; }
  };
  $("#pin-random").onclick = () => {
    const taken = new Set(pins.list.map(p => p.name));
    const free = SPOTS.filter(s => !taken.has(s[0]));
    const [name, lat, lon] = free[Math.floor(Math.random() * free.length)];
    if (pins.map) pins.map.flyTo([lat, lon], 14, { duration: reduced() ? 0 : .8 });
    dropPin(lat, lon, name);
  };
  $("#pin-cards").addEventListener("click", ev => {
    const x = ev.target.closest("[data-x]");
    if (x) { pins.list.splice(+x.dataset.x, 1); drawPins(); return; }
    const c = ev.target.closest(".pin-card");
    if (c && pins.map) { const p = pins.list[+c.dataset.i]; pins.map.flyTo([p.lat, p.lon], 16, { duration: reduced() ? 0 : .6 }); }
  });
  // the map loads when the section first comes near the screen, so Leaflet has its size
  const io = new IntersectionObserver(es => { if (es.some(e => e.isIntersecting)) { io.disconnect(); const t = setInterval(() => { if (window.L) { clearInterval(t); pinMap(); } }, 100); } }, { rootMargin: "200px" });
  io.observe($("#pin-map"));
  for (const id of ["wi-d", "wi-s"]) $("#" + id).addEventListener("input", () => { $(`#${id}-o`).textContent = $("#" + id).value; whatIf(); });
  whatIf();
}

/* What if: the same score for a block with the slider values, debounced. */
let wiTimer = null, wiSeq = 0;
function seedWhatIf(d, letter) {
  $("#wi-d").value = Math.min(200, d.density); $("#wi-d-o").textContent = $("#wi-d").value;
  $("#wi-s").value = Math.min(60, d.same_cuisine_area); $("#wi-s-o").textContent = $("#wi-s").value;
  $("#wi-from").textContent = `They start from pin ${letter}.`;
  whatIf();
}
function whatIf() {
  clearTimeout(wiTimer);
  wiTimer = setTimeout(async () => {
    const n = ++wiSeq, c = $("#pin-cuisine").value || "Korean";
    try {
      const r = await getJSON(`/api/whatif?concept=${encodeURIComponent(c)}&density=${$("#wi-d").value}&same=${$("#wi-s").value}`);
      if (n !== wiSeq) return;
      $("#wi-pct").textContent = r.score_percentile + "%";
      $("#wi-say").textContent = `of NYC restaurant blocks score lower for ${c}. A block this busy is busier than ${r.density_percentile}% of blocks.`;
    } catch (e) { $("#wi-say").textContent = e.message; }
  }, 120);
}

/* ---------- beat the model ---------- */
const game = { rows: [], order: [], round: 0, you: 0, alone: 0, wq: 0, locked: false };
const MIN = 48, MAX = 112;   // quarter hours: noon to 4 am
const toQ = t => { const [h, m] = t.split(":").map(Number); return (h < 6 ? h + 24 : h) * 4 + m / 15; };
const hhmm = q => { const mins = Math.round(q * 15), h = Math.floor(mins / 60) % 24, m = mins % 60;
  return h === 0 && m === 0 ? "midnight" : h === 12 && m === 0 ? "noon" : `${h % 12 || 12}:${String(m).padStart(2, "0")} ${h < 12 ? "am" : "pm"}`; };
const pos = q => `${Math.max(0, Math.min(100, (q - MIN) / (MAX - MIN) * 100))}%`;

function gameScore() {
  const n = game.round + (game.locked ? 1 : 0);
  $("#game-score").innerHTML = `<span class="you">You <b>${game.you}/${n}</b></span>
    <span>GPT-6 Astra alone <b>${game.alone}/${n}</b></span><span class="wq">GPT-6 Astra + Qloo <b>${game.wq}/${n}</b></span>`;
}
function gameRound() {
  const r = game.rows[game.order[game.round]];
  game.locked = false;
  $("#game-round").textContent = `Round ${game.round + 1} of 5`;
  $("#game-q").innerHTML = `When does ${esc(r.name)} close on Friday?${r.address ? `<span>${esc(r.address)}</span>` : ""}`;
  $("#game-dial").disabled = false; $("#game-dial").value = 88; gameDial();
  $("#game-lock").hidden = false; $("#game-next").hidden = true;
  $("#game-line").hidden = true; $("#game-verdicts").innerHTML = ""; $("#game-end").hidden = true;
  gameScore();
}
function gameDial() { $("#game-read").innerHTML = `${hhmm(+$("#game-dial").value)}<small>your guess</small>`; }
function gameLock() {
  if (game.locked) return;
  const r = game.rows[game.order[game.round]], g = +$("#game-dial").value, truth = toQ(r.google);
  const youRight = Math.abs(g - truth) <= 2;
  const a = r.large_alone, q = r.large_with_qloo;
  game.locked = true; game.you += youRight; game.alone += a.right; game.wq += q.right;
  $("#game-dial").disabled = true; $("#game-lock").hidden = true;
  const marks = [["truth", "Google Maps", truth], ["you", "You", g], ["wq", "Astra + Qloo", q.said ? toQ(q.said) : null], ["alone", "Astra alone", a.said ? toQ(a.said) : null]];
  const line = $("#game-line");
  line.innerHTML = `<span class="axis"></span>` + ["noon", "4 pm", "8 pm", "midnight", "4 am"].map((t, i) => `<span class="tick" style="left:${i * 25}%">${t}</span>`).join("") +
    marks.filter(m => m[2] != null).map(([cls, who, v], i) => `<div class="mk ${cls}" style="left:${pos(MIN)};top:${8 + i * 26}px;opacity:0" data-left="${pos(v)}">
      <span>${esc(who)}: ${hhmm(v)}</span><i style="height:${Math.max(4, 104 - i * 26 - 18)}px"></i></div>`).join("");
  line.hidden = false;
  requestAnimationFrame(() => requestAnimationFrame(() => line.querySelectorAll(".mk").forEach((m, i) => setTimeout(() => { m.style.left = m.dataset.left; m.style.opacity = 1; }, reduced() ? 0 : i * 180))));
  const v = (cls, who, said, right) => `<div class="${said == null ? "dk" : right ? "ok" : "no"}"><b>${esc(who)}</b>${said == null ? "I don't know." : `Closes at ${esc(said)}.`}</div>`;
  $("#game-verdicts").innerHTML = v("you", "You", hhmm(g), youRight) + v("alone", "GPT-6 Astra alone", a.said ? hhmm(toQ(a.said)) : null, a.right) +
    v("wq", "GPT-6 Astra + Qloo", q.said ? hhmm(toQ(q.said)) : null, q.right);
  gameScore();
  if (game.round === 4) gameEnd(); else { $("#game-next").hidden = false; $("#game-next").focus(); }
}
function gameEnd() {
  const end = $("#game-end");
  const line = game.you > game.wq ? "You beat the model with Qloo. Impressive." : game.you === game.wq ? "You tied the model with Qloo." :
    game.you > game.alone ? "You beat the model alone, but not the model with Qloo's record." : "The model with Qloo's record won this one.";
  end.innerHTML = `<strong>${esc(line)}</strong>
    <p class="hint">You ${game.you} of 5, GPT-6 Astra alone ${game.alone} of 5, GPT-6 Astra with Qloo ${game.wq} of 5. Across all 30 restaurants in Test 20 the model alone was right 0 times and with Qloo 29 times.</p>
    <div class="game-actions"><button type="button" class="primary" id="game-again">Play again</button>
    <button type="button" class="quiet" id="game-share">Copy my score</button></div>`;
  end.hidden = false;
  $("#game-again").onclick = gameStart;
  $("#game-share").onclick = () => copyText(`Whitespace closing-time game: me ${game.you}/5, GPT-6 Astra alone ${game.alone}/5, with Qloo ${game.wq}/5.`, "Score copied.");
}
function gameStart() {
  // the five rounds come from the 29 restaurants where the model with Qloo's record was right
  const idx = game.rows.map((_, i) => i).filter(i => { const t = toQ(game.rows[i].google); return t >= MIN && t <= MAX && game.rows[i].large_with_qloo.right; });
  for (let i = idx.length - 1; i > 0; i--) { const j = Math.floor(Math.random() * (i + 1)); [idx[i], idx[j]] = [idx[j], idx[i]]; }
  Object.assign(game, { order: idx.slice(0, 5), round: 0, you: 0, alone: 0, wq: 0 });
  gameRound();
}
function gameBoot() {
  if (!$("#game")) return;
  $("#game-dial").addEventListener("input", gameDial);
  $("#game-lock").onclick = gameLock;
  $("#game-next").onclick = () => { game.round++; gameRound(); };
  const io = new IntersectionObserver(async es => {
    if (!es.some(e => e.isIntersecting)) return;
    io.disconnect();
    try { game.rows = (await getJSON("/api/test20")).rows; gameStart(); }
    catch (e) { $("#game-q").textContent = "The recorded Test 20 answers are not on this server, so the game cannot run here."; $("#game-lock").disabled = true; }
  }, { rootMargin: "200px" });
  io.observe($("#game-box"));
}

/* ---------- the city map in the header: every restaurant and vacant storefront, click to score a block ---------- */
const cm = { data: null, rest: null, shop: null, cuis: null, pin: null, hi: 0, drawn: false };
function b64u16(b64) { const bin = atob(b64), u = new Uint8Array(bin.length); for (let i = 0; i < bin.length; i++) u[i] = bin.charCodeAt(i); return new Uint16Array(u.buffer); }
function b64u8(b64) { const bin = atob(b64), u = new Uint8Array(bin.length); for (let i = 0; i < bin.length; i++) u[i] = bin.charCodeAt(i); return u; }
function cmDraw(progress = 1) {
  const cv = $("#cm-canvas"), r = cv.getBoundingClientRect(), dpr = Math.min(2, devicePixelRatio || 1);
  if (!r.width) return;
  if (cv.width !== Math.round(r.width * dpr)) { cv.width = Math.round(r.width * dpr); cv.height = Math.round(r.height * dpr); }
  const g = cv.getContext("2d"), W = cv.width, H = cv.height, sx = W / 65535, sy = H / 65535;
  g.clearRect(0, 0, W, H);
  const ink = cssVar("--ink"), red = cssVar("--qloo"), blue = cssVar("--city");
  // restaurants are the base layer and give the city its shape; storefronts sit on top, small, so they never blob
  const nR = Math.floor(cm.rest.length / 2 * progress), nS = Math.floor(cm.shop.length / 2 * progress), d = 1.7 * dpr;
  g.fillStyle = ink; g.globalAlpha = cm.hi ? .2 : .42;
  for (let i = 0; i < nR; i++) g.fillRect(cm.rest[2 * i] * sx - d / 2, cm.rest[2 * i + 1] * sy - d / 2, d, d);
  if (cm.hi) {
    g.globalAlpha = .95; g.fillStyle = blue;
    for (let i = 0; i < nR; i++) if (cm.cuis[i] === cm.hi) { g.beginPath(); g.arc(cm.rest[2 * i] * sx, cm.rest[2 * i + 1] * sy, 2.2 * dpr, 0, 7); g.fill(); }
  }
  g.globalAlpha = cm.hi ? .3 : .78; g.fillStyle = red;
  const rs = 1.15 * dpr;
  for (let i = 0; i < nS; i++) { g.beginPath(); g.arc(cm.shop[2 * i] * sx, cm.shop[2 * i + 1] * sy, rs, 0, 7); g.fill(); }
  g.globalAlpha = 1;
  if (cm.pin) {
    const [px, py] = cm.pin;
    g.strokeStyle = ink; g.lineWidth = 2 * dpr; g.beginPath(); g.arc(px * W, py * H, 9 * dpr, 0, 7); g.stroke();
    g.fillStyle = red; g.beginPath(); g.arc(px * W, py * H, 4 * dpr, 0, 7); g.fill();
  }
}
function cmAnimate() {
  if (reduced()) { cmDraw(1); return; }
  const t0 = performance.now(), dur = 1600;
  const f = t => { const k = Math.min(1, (t - t0) / dur); cmDraw(1 - Math.pow(1 - k, 3)); if (k < 1) requestAnimationFrame(f); };
  requestAnimationFrame(f);
}
async function cmClick(ev) {
  if (!cm.data) return;
  const frame = $(".cm-frame"), r = frame.getBoundingClientRect(), fx = (ev.clientX - r.left) / r.width, fy = (ev.clientY - r.top) / r.height;
  const [s, w, n, e] = cm.data.box, lat = n - fy * (n - s), lon = w + fx * (e - w);
  const concept = $("#cm-cuisine").value ? Object.keys(cm.data.concepts).find(k => cm.data.concepts[k] === $("#cm-cuisine").value) || "Korean" : ($("#pin-cuisine").value || "Korean");
  cm.pin = [fx, fy]; cmDraw();
  const card = $("#cm-card");
  card.style.left = Math.min(r.width - Math.min(260, r.width * .7) - 8, Math.max(8, ev.clientX - r.left + 14)) + "px";
  card.style.top = Math.min(r.height - 130, Math.max(8, ev.clientY - r.top - 20)) + "px";
  card.hidden = false; card.innerHTML = "Scoring this block\u2026";
  try {
    const d = await getJSON(`/api/pin?concept=${encodeURIComponent(concept)}&lat=${lat.toFixed(5)}&lon=${lon.toFixed(5)}`);
    card.innerHTML = `<span class="sub">${esc(concept)} on this block</span><b class="big">${d.score_percentile}%</b>
      of NYC restaurant blocks score lower. ${d.density} restaurants here, ${d.same_cuisine_area} of the same cuisine around it.
      <br><a href="#play" id="cm-more">Compare it on the big map</a>`;
    $("#cm-more").onclick = () => { $("#pin-cuisine").value = concept; setTimeout(() => dropPin(lat, lon), 600); };
  } catch (e) { card.textContent = /422/.test(e.message) || /tested cuisine/.test(e.message) ? "That point is outside the four boroughs we cover." : e.message; }
}
async function cmBoot() {
  if (!$("#citymap")) return;
  try { cm.data = await getJSON("/api/citymap"); } catch (_) { $("#citymap").hidden = true; return; }
  const [bs, bw, bn, be] = cm.data.box;   // the frame takes the city's true shape
  $(".cm-frame").style.aspectRatio = `${((be - bw) * Math.cos((bs + bn) / 2 * Math.PI / 180)).toFixed(4)} / ${(bn - bs).toFixed(4)}`;
  cm.rest = b64u16(cm.data.restaurants); cm.shop = b64u16(cm.data.storefronts); cm.cuis = b64u8(cm.data.cuisine);
  $("#cm-n-rest").textContent = cm.data.counts.restaurants.toLocaleString("en-US");
  $("#cm-n-shop").textContent = cm.data.counts.storefronts.toLocaleString("en-US");
  $("#cm-cuisine").insertAdjacentHTML("beforeend", cm.data.cuisines.map((c, i) => `<option value="${esc(c)}" data-i="${i + 1}">${esc(c)}</option>`).join(""));
  $("#cm-cuisine").onchange = () => { const o = $("#cm-cuisine").selectedOptions[0]; cm.hi = o && o.dataset.i ? +o.dataset.i : 0; cmDraw(); };
  $(".cm-frame").addEventListener("click", ev => { if (!ev.target.closest(".cm-card")) cmClick(ev); });
  cmAnimate();
  let t; addEventListener("resize", () => { clearTimeout(t); t = setTimeout(() => cmDraw(), 120); });
  $("#theme-toggle").addEventListener("click", () => setTimeout(() => cmDraw(), 30));
}

/* ---------- the business: yearly openings and vacancies from city records, prices and shares from the visitor ---------- */
const biz = { opened: 3034, shops: 6767 };
const money = n => "$" + Math.round(n).toLocaleString("en-US");
function bizCalc() {
  const share = +$("#bz-share").value, price = +$("#bz-price").value, lshare = +$("#bz-lshare").value, lprice = +$("#bz-lprice").value;
  $("#bz-share-o").textContent = share + "%"; $("#bz-price-o").textContent = money(price);
  $("#bz-lshare-o").textContent = lshare + "%"; $("#bz-lprice-o").textContent = money(lprice);
  const founders = biz.opened * share / 100 * price, landlords = biz.shops * lshare / 100 * lprice * 12;
  $("#bz-total").textContent = money(founders + landlords);
  $("#bz-split").innerHTML = `<span><b>${money(founders)}</b> from ${Math.round(biz.opened * share / 100).toLocaleString("en-US")} founders' site reports</span>
    <span><b>${money(landlords)}</b> from ${Math.round(biz.shops * lshare / 100).toLocaleString("en-US")} landlords' storefront listings</span>`;
}
async function bizBoot() {
  if (!$("#business")) return;
  ["bz-share", "bz-price", "bz-lshare", "bz-lprice"].forEach(id => $("#" + id).addEventListener("input", bizCalc));
  bizCalc();
  try {
    const st = await getJSON("/api/stats");
    if (st.opened_last_year) {
      biz.opened = st.opened_last_year.count;
      $('[data-biz="opened"]').textContent = st.opened_last_year.count.toLocaleString("en-US");
      $('[data-biz="year"]').textContent = st.opened_last_year.year;
      $('[data-biz="active"]').textContent = st.opened_last_year.active_four_boroughs.toLocaleString("en-US");
    }
    if (st.storefronts) { biz.shops = st.storefronts; $('[data-biz="shops"]').textContent = st.storefronts.toLocaleString("en-US"); }
    bizCalc();
  } catch (_) {}
}

/* ---------- Qloo or the baseline: a quiz over the results where Qloo beat its baseline ---------- */
const quiz = { rounds: [], i: 0, right: 0, done: false };
function quizRounds() {
  const out = [];
  for (const k of RESULTS) {
    if (k.badge !== "win") continue;
    if (k.kind === "pair") out.push({ task: k.title, test: k.test, metric: k.metric, q: k.q, b: k.b, note: k.note });
    if (k.id === "F15") out.push({ task: k.title, test: k.test, metric: k.metric, q: ["Qloo", .875], b: ["Genre", .714], note: k.note });
  }
  for (let i = out.length - 1; i > 0; i--) { const j = Math.floor(Math.random() * (i + 1)); [out[i], out[j]] = [out[j], out[i]]; }
  return out.slice(0, 8);
}
function quizShow() {
  const r = quiz.rounds[quiz.i];
  $("#qz-round").textContent = `Question ${quiz.i + 1} of ${quiz.rounds.length}`;
  $("#qz-score").textContent = `${quiz.right}/${quiz.i}`;
  $("#qz-q").textContent = `${r.task}: who scored higher?`;
  $("#qz-sub").textContent = `Test ${r.test}. Measured as ${r.metric}.`;
  const opts = Math.random() < .5 ? [r.q, r.b] : [r.b, r.q];
  $("#qz-opts").innerHTML = opts.map(o => `<button type="button" class="qz-opt" data-who="${esc(o[0])}">${esc(o[0])}</button>`).join("");
  $("#qz-reveal").innerHTML = ""; $("#qz-next").hidden = true;
  $("#qz-opts").querySelectorAll(".qz-opt").forEach(b => b.onclick = () => quizPick(b));
}
function quizPick(btn) {
  const r = quiz.rounds[quiz.i], right = btn.dataset.who === r.q[0];
  quiz.right += right;
  $("#qz-opts").querySelectorAll(".qz-opt").forEach(b => { b.disabled = true; b.classList.toggle("win", b.dataset.who === r.q[0]); b.classList.toggle("picked", b === btn); });
  const bar = (who, v, cls) => `<div class="pair-row ${cls}"><span class="who">${esc(who)}</span><span class="trk"><i style="width:0" data-w="${Math.max(1.5, v * 100).toFixed(1)}"></i></span><b>${v.toFixed(3)}</b></div>`;
  $("#qz-reveal").innerHTML = `<p class="qz-verdict ${right ? "ok" : "no"}">${right ? "Right." : "Not this time."} ${esc(r.q[0])} scored ${r.q[1].toFixed(3)}, ${esc(r.b[0].toLowerCase())} ${r.b[1].toFixed(3)}.</p>
    <div class="pair">${bar(r.q[0], r.q[1], "is-q")}${bar(r.b[0], r.b[1], "is-b")}</div>${r.note ? `<p class="hint">${esc(r.note)}</p>` : ""}`;
  requestAnimationFrame(() => requestAnimationFrame(() => $("#qz-reveal").querySelectorAll("[data-w]").forEach(i => { i.style.width = i.dataset.w + "%"; })));
  $("#qz-score").textContent = `${quiz.right}/${quiz.i + 1}`;
  const last = quiz.i === quiz.rounds.length - 1;
  $("#qz-next").textContent = last ? "See my score" : "Next question";
  $("#qz-next").hidden = false;
}
function quizNext() {
  if (quiz.i < quiz.rounds.length - 1) { quiz.i++; quizShow(); return; }
  const n = quiz.rounds.length;
  $("#qz-round").textContent = "Finished";
  $("#qz-q").textContent = quiz.right === n ? `All ${n} right. You read Qloo as well as the tests do.` : `You picked the winner ${quiz.right} of ${n} times.`;
  $("#qz-sub").textContent = `In every one of these ${n} results, from pre-registered tests, Qloo scored higher than its baseline.`;
  $("#qz-opts").innerHTML = ""; $("#qz-reveal").innerHTML = "";
  $("#qz-next").textContent = "Play again"; $("#qz-next").hidden = false;
  quiz.done = true;
}
function quizStart() { Object.assign(quiz, { rounds: quizRounds(), i: 0, right: 0, done: false }); quizShow(); }
function quizBoot() {
  if (!$("#quiz") || typeof RESULTS === "undefined") return;
  $("#qz-next").onclick = () => { if (quiz.done) quizStart(); else quizNext(); };
  quizStart();
}

/* ---------- the pin challenge: find a block that beats a target for the chosen cuisine ---------- */
const GOAL = 95;
function pinGoal() {
  const el = $("#pin-goal"); if (!el) return;
  const c = $("#pin-cuisine").value || "Korean";
  const hit = pins.list.map((p, i) => [p, i]).filter(([p]) => p.data && p.data.score_percentile >= GOAL);
  el.classList.toggle("done", hit.length > 0);
  el.innerHTML = hit.length ? `Challenge done: pin ${LETTERS[hit[0][1]]} beats ${hit[0][0].data.score_percentile}% of New York blocks for ${esc(c)}.`
    : `Challenge: find a block that beats ${GOAL}% of New York blocks for ${esc(c)}. Busy streets with a little competition score best.`;
}

pinBoot();
gameBoot();
cmBoot();
bizBoot();
quizBoot();
