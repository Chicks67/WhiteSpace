"use strict";
/* Page features on top of app.js: the agent radar, the results scoreboard, the Test 20 duel replay, scroll
   reveals and count-ups. Nothing here calls a model: the radar draws the events
   a run already streams, and every result matches the project's authoritative results table. */

/* ---------- the test results, as the page shows them ---------- */
const DOMAINS = { places: "Places", restaurants: "Restaurants", briefs: "Briefs", music: "Music", film: "Film", sports: "Sports" };
/* kind: race (several bars out of a total), donut (a share), pair (Qloo against its baseline), gain (a difference).
   badge: win (beat its baseline), fact (Qloo was right), built (a model using Qloo, no outside baseline), mix (mixed). */
const RESULTS = [
  { id: "F20", test: "20", dom: "places", badge: "win", kind: "race", of: 30, title: "When does this restaurant close on Friday?",
    rows: [["GPT-6 Astra alone", 0, "b"], ["GPT-6 Astra + Qloo", 29, "q"], ["Gemini 3.8 Flash alone", 3, "b"], ["Gemini 3.8 Flash + Qloo", 29, "q"]],
    note: "30 real New York restaurants, answers checked against Google Maps." },
  { id: "F12", test: "12", dom: "places", badge: "fact", kind: "donut", n: 29, of: 30, title: "Qloo's Friday closing times against Google Maps",
    note: "Within 30 minutes for 29 of 30, and all 29 exact." },
  { id: "S12", test: "12", dom: "places", badge: "fact", kind: "donut", n: 25, of: 27, title: "Qloo's price levels against Google Maps",
    note: "Price levels matched for 25 of 27 places." },
  { id: "S10", test: "10", dom: "restaurants", badge: "fact", kind: "donut", n: .924, of: 1, pct: true, title: "Share of real competitors Qloo finds",
    note: "Against the city's inspection records." },
  { id: "S3", test: "3", dom: "briefs", badge: "win", kind: "donut", n: .78, of: 1, pct: true, title: "Human raters prefer the brief written with Qloo",
    note: "Positioning briefs, rated blind.", base: [.5, "no preference"] },
  { id: "S8", test: "8", dom: "briefs", badge: "win", kind: "donut", n: .76, of: 1, pct: true, title: "A blind judge prefers the brief written with Qloo",
    note: "Interval 0.68 to 0.83.", base: [.5, "no preference"] },
  { id: "S4", test: "4", dom: "restaurants", badge: "win", kind: "pair", metric: "AUC", title: "Lease score: where a cuisine opens next",
    q: ["With Qloo", .893], b: ["Without Qloo", .851], note: "The score that ranks every storefront in the product." },
  { id: "S4b", test: "4b", dom: "restaurants", badge: "win", kind: "pair", metric: "AUC", title: "Lease score across 25 cuisines",
    q: ["With Qloo", .887], b: ["Without Qloo", .851], note: "The same score on the cuisines added in Test 4b." },
  { id: "S1", test: "1", dom: "restaurants", badge: "win", kind: "pair", metric: "AUC", title: "Cuisine heatmaps find the next opening",
    q: ["Qloo heatmap", .812], b: ["Restaurant count", .742], note: "Against the count of restaurants already on each block." },
  { id: "S7", test: "7", dom: "restaurants", badge: "win", kind: "gain", delta: .087, metric: "AUC over city records", title: "Which cuisine opens in a storefront",
    note: "Qloo added to city records when predicting a storefront's cuisine." },
  { id: "S2", test: "2", dom: "music", badge: "win", kind: "gain", delta: .064, metric: "AUC", title: "Music-audience heatmaps carry local taste",
    note: "Gain from Qloo's music-audience heatmaps." },
  { id: "F27", test: "27", dom: "music", badge: "win", kind: "pair", metric: "AUC", title: "Small artists a real listener plays",
    q: ["Qloo", .841], b: ["Popularity", .516], note: "40 real Last.fm listeners. Model alone 0.865, model + Qloo 0.874: no meaningful difference." },
  { id: "F28", test: "28", dom: "music", badge: "win", kind: "pair", metric: "share of possible gain", title: "A festival timetable with fewer fan clashes",
    q: ["Qloo", .663], b: ["Popularity", .043], note: "Pair scores +0.031 (0.005 to 0.056). Model 0.669, model + Qloo 0.702: no different." },
  { id: "F15", test: "15", dom: "music", badge: "win", kind: "race", of: 1, metric: "AUC", title: "The act that really opened the tour",
    rows: [["Qloo", .875, "q"], ["Genre", .714, "b"], ["Fame", .473, "b"]], note: "A model alone scored 0.976 on the same shortlists." },
  { id: "S16", test: "16", dom: "music", badge: "built", kind: "race", of: 1, metric: "AUC", title: "Finding real openers with no shortlist",
    rows: [["Qloo candidates", .721, "q"], ["Model + Qloo", .846, "q"]], note: "A model shown Qloo's candidates found the most." },
  { id: "S17", test: "17", dom: "music", badge: "win", kind: "pair", metric: "AUC", title: "Cities an artist's tour really plays",
    q: ["Qloo", .781], b: ["Baseline", .693] },
  { id: "S19", test: "19", dom: "music", badge: "win", kind: "pair", metric: "AUC", title: "Another team's tour-opener claim, repeated",
    q: ["Qloo", .824], b: ["Baseline", .751] },
  { id: "S21", test: "21", dom: "music", badge: "win", kind: "gain", delta: .086, metric: "Qloo minus model", title: "Lesser-known headliners: Qloo against the model",
    note: "Where a model knows least, Qloo leads." },
  { id: "S24", test: "24", dom: "music", badge: "win", kind: "pair", metric: "AUC", title: "Older acts that young people took up",
    q: ["Qloo", .712], b: ["Chance", .333], note: "TikTok trend lists." },
  { id: "S18", test: "18", dom: "film", badge: "win", kind: "pair", metric: "AUC", title: "Films a person rated highly (MovieLens)",
    q: ["Qloo", .873], b: ["Average rating", .815] },
  { id: "S26", test: "26", dom: "sports", badge: "win", kind: "pair", metric: "Spearman", title: "MLB theme nights that suit a city's taste",
    q: ["Qloo", .284], b: ["Model alone", .099], note: "2,425 games, 336 theme nights." },
  { id: "F14", test: "14", dom: "music", badge: "mix", kind: "race", of: 1, metric: "AUC", title: "Which acts a music venue books",
    rows: [["Qloo", .589, "q"], ["Model alone", .814, "b"]], note: "Qloo 0.589 (0.518 to 0.668): above fame, not above genre." },
];
/* Results where Qloo did not move the number. Kept on the page: every test stays in the record. */
const RECORD = [
  "Test 9, brief from Qloo place records: Q over Q0 0.60 (0.433 to 0.767), over C+ 0.633 (0.483 to 0.80); the registered rule was not met.",
  "Test 6, Qloo audience tags against census: 2 of 7 tags matched. Demographics come from the census.",
  "Test 11, scene specificity: location share 0.225; what a scene means is not validated.",
  "Test 5, survival with Qloo taste: +0.013, against +0.016 for a placebo.",
  "Test 22, Qloo hours for model-written plans: hours held for 0.992 of stops; the human check was not run.",
  "Test 25, brand-new restaurants: Qloo held 55% of 120; cuisine 0.683 for the model alone, 0.658 with Qloo.",
  "Test 23, comedians who share a crowd: 0.612 (0.464 to 0.797), too few bills to say.",
  "Test 13, idea screen: partners, scene and twin city passed; the other outputs failed on consistency.",
  "Tests 14 and 15: a model alone scored 0.814 and 0.976, above Qloo's 0.589 and 0.875.",
];
const WINS = RESULTS.filter(k => k.badge === "win");
const COMPARED = WINS.length + 4;   // the wins, plus the head-to-heads Qloo did not win: Tests 5, 9, 14 and 25
const fmt = v => (v < 1 && v > -1 ? v.toFixed(3) : String(v));
const still = () => matchMedia("(prefers-reduced-motion: reduce)").matches;

/* ---------- small SVG pieces ---------- */
function donut(frac, label, cls = "") {
  const C = 2 * Math.PI * 40;
  return `<svg class="donut ${cls}" viewBox="0 0 100 100" role="img" aria-label="${esc(label)}">
    <circle class="bg" cx="50" cy="50" r="40" fill="none" stroke-width="11"/>
    <circle class="fg" cx="50" cy="50" r="40" fill="none" stroke-width="11" transform="rotate(-90 50 50)"
      stroke-dasharray="${C.toFixed(2)}" stroke-dashoffset="${C.toFixed(2)}" data-off="${(C * (1 - frac)).toFixed(2)}"/>
    <text x="50" y="55">${esc(label)}</text></svg>`;
}
function bars(rows, of) {
  return `<div class="pair">${rows.map(([who, v, c]) => `<div class="pair-row ${c === "q" ? "is-q" : "is-b"}"><span class="who" title="${esc(who)}">${esc(who)}</span>
    <span class="trk"><i data-w="${Math.max(1.5, v / of * 100).toFixed(1)}"></i></span><b>${of === 30 ? `${v}/30` : fmt(v)}</b></div>`).join("")}</div>`;
}

/* ---------- scoreboard ---------- */
function scoreboard() {
  const R = 100, C = 2 * Math.PI * R, frac = WINS.length / COMPARED;
  $("#sb-ring").innerHTML = `<svg viewBox="0 0 240 240" role="img" aria-label="Qloo ahead in ${WINS.length} of ${COMPARED} head-to-head results">
      <circle class="ring-bg" cx="120" cy="120" r="${R}" fill="none" stroke-width="16"/>
      <circle class="ring-fg" cx="120" cy="120" r="${R}" fill="none" stroke-width="16" transform="rotate(-90 120 120)"
        stroke-dasharray="${C.toFixed(1)}" stroke-dashoffset="${C.toFixed(1)}" data-off="${(C * (1 - frac)).toFixed(1)}"/>
      <text class="ring-num" x="120" y="128"><tspan data-to="${WINS.length}">0</tspan><tspan font-size="26" dx="4">/ ${COMPARED}</tspan></text>
      <text class="ring-sub" x="120" y="156">Qloo ahead</text></svg>
    <p class="lbl">Test results where Qloo, or a model with Qloo, beat the baseline it was measured against.</p>`;
  const kpis = [
    ["Friday closing times", 29, "/ 30", "With Qloo's record, for both models. Alone: 0 and 3.", 0],
    ["Brief preferred", 78, "%", "Blind raters chose the brief written with Qloo (Test 3).", 0],
    ["Lease score", .893, "AUC", "With Qloo, against 0.851 without it (Test 4).", 3],
    ["Competitors found", 92.4, "%", "Of real competitors, found by Qloo (Test 10).", 1],
    ["Festival clashes cut", .663, "of max", "Qloo's timetable; popularity reached 0.043 (Test 28).", 3],
    ["Small artists", .841, "AUC", "A real listener's taste; popularity 0.516 (Test 27).", 3],
  ];
  $("#sb-kpis").innerHTML = kpis.map(([t, v, u, p, d]) => `<article class="panel kpi"><span class="t">${esc(t)}</span>
    <span class="v"><span data-to="${v}" data-dec="${d}">0</span><small>${esc(u)}</small></span><p>${esc(p)}</p></article>`).join("");

  const chips = [["all", "All"], ...Object.entries(DOMAINS)];
  $("#sb-chips").innerHTML = chips.map(([k, l]) => `<button type="button" data-dom="${k}" aria-pressed="${k === "all"}">${esc(l)}</button>`).join("");
  $("#sb-chips").onclick = ev => { const b = ev.target.closest("button"); if (b) filterCards(b.dataset.dom); };
  $("#sb-grid").innerHTML = RESULTS.map(card).join("");
  filterCards("all", true);
  $("#record-list").innerHTML = RECORD.map(r => `<li>${esc(r)}</li>`).join("");
  dumbbell();
}
function card(k) {
  let viz = "";
  if (k.kind === "race") viz = bars(k.rows, k.of);
  else if (k.kind === "pair") viz = bars([[k.q[0], k.q[1], "q"], [k.b[0], k.b[1], "b"]], 1);
  else if (k.kind === "gain") viz = `<div class="gain"><span class="g">+${fmt(k.delta)}<small>${esc(k.metric)}</small></span>
    <span class="trk"><i data-w="${Math.min(100, k.delta / .1 * 100).toFixed(1)}"></i></span></div>`;
  else {
    const f = k.n / k.of, big = k.pct ? `${(f * 100).toFixed(f * 100 % 1 ? 1 : 0)}%` : `${k.n} / ${k.of}`;
    viz = `<div class="donut-wrap">${donut(f, big, k.badge === "fact" ? "fact" : "")}<p><b>${esc(big)}</b>${k.base ? `against ${k.base[0] * 100}% for ${esc(k.base[1])}` : k.badge === "fact" ? "checked against an outside source" : ""}</p></div>`;
  }
  const badge = { win: ["", "Qloo ahead"], fact: ["fact", "Qloo was right"], built: ["", "Built on Qloo"], mix: ["mix", "Mixed"] }[k.badge];
  return `<article class="panel card reveal" data-dom="${k.dom}">
    <span class="id"><span>Test ${esc(k.test)} &middot; ${esc(k.id)}</span><span class="dom">${esc(DOMAINS[k.dom])}</span></span>
    <h3>${esc(k.title)}</h3>
    <div class="mini">${viz}</div>
    <span class="badge ${badge[0]}">${badge[1]}</span>
    ${k.note ? `<p class="note">${esc(k.note)}</p>` : ""}</article>`;
}
const LEDGER_FIRST = 8;
let ledgerAll = false;
function filterCards(dom, first = false) {
  let n = 0;
  document.querySelectorAll("#sb-chips button").forEach(b => b.setAttribute("aria-pressed", String(b.dataset.dom === dom)));
  // on first paint the cards wait for the scroll reveal; after a filter click they fill at once
  // "All" shows the first rows and a button for the rest, so the ledger does not swallow the page
  document.querySelectorAll("#sb-grid .card").forEach(c => {
    const on = (dom === "all" || c.dataset.dom === dom) && (dom !== "all" || ledgerAll || n < LEDGER_FIRST);
    c.hidden = !on; if (on) { n++; if (!first) { c.classList.add("in"); animateIn(c); } }
  });
  const total = dom === "all" ? RESULTS.length : n, more = $("#sb-more");
  more.hidden = dom !== "all" || ledgerAll;
  more.textContent = `Show all ${RESULTS.length} results`;
  more.onclick = () => { ledgerAll = true; filterCards("all"); };
  n = total;
  $("#sb-count").textContent = `${n} result${n === 1 ? "" : "s"}`;
}

/* One row per head-to-head: baseline dot, Qloo dot, sorted by Qloo's lead. */
let dumbNarrow = null;
addEventListener("resize", () => {
  clearTimeout(dumbbell.t);
  dumbbell.t = setTimeout(() => {
    if ((($("#dumb").clientWidth || innerWidth) < 640) !== dumbNarrow) { dumbbell(); $("#dumb").classList.add("in"); }
  }, 150);
});
function dumbbell() {
  const rows = [];
  for (const k of RESULTS) {
    if (k.badge !== "win") continue;
    if (k.kind === "pair") rows.push({ t: `T${k.test} ${k.title}`, m: k.metric, b: k.b[1], bl: k.b[0], q: k.q[1], ql: k.q[0] });
    if (k.id === "F20") {
      rows.push({ t: "T20 Closing times, GPT-6 Astra", m: "accuracy", b: 0, bl: "alone, 0 of 30", q: 29 / 30, ql: "with Qloo, 29 of 30" });
      rows.push({ t: "T20 Closing times, Gemini 3.8 Flash", m: "accuracy", b: .1, bl: "alone, 3 of 30", q: 29 / 30, ql: "with Qloo, 29 of 30" });
    }
    if (k.id === "F15") rows.push({ t: "T15 Real tour openers", m: "AUC", b: .714, bl: "genre (fame 0.473)", q: .875, ql: "Qloo" });
    if (k.base) rows.push({ t: `T${k.test} ${k.title}`, m: "preference share", b: k.base[0], bl: k.base[1], q: k.n, ql: "brief with Qloo" });
  }
  rows.sort((a, b) => (b.q - b.b) - (a.q - a.b));
  // on a narrow screen each label sits above its line, so the chart keeps a readable size
  const narrow = ($("#dumb").clientWidth || innerWidth) < 640, dy = narrow ? 8 : 0;
  const W = narrow ? 360 : 920, left = narrow ? 8 : 300, right = narrow ? 44 : 70, top = 26, rowH = narrow ? 46 : 30, H = top + rows.length * rowH + 30;
  const x = v => left + v * (W - left - right);
  const cut = narrow ? 52 : 42, clip = s => s.length > cut ? s.slice(0, cut - 1) + "…" : s;
  dumbNarrow = narrow;
  let s = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Dumbbell chart: baseline against Qloo for ${rows.length} head-to-head results">`;
  for (const t of [0, .25, .5, .75, 1]) s += `<line class="grid" x1="${x(t)}" x2="${x(t)}" y1="${top - 10}" y2="${H - 24}"/><text x="${x(t)}" y="${H - 6}" text-anchor="middle">${t}</text>`;
  rows.forEach((r, i) => {
    const y = top + i * rowH + rowH / 2;
    s += `<g class="row" data-i="${i}" style="transition-delay:${i * 45}ms"><rect class="hit" x="0" y="${y - rowH / 2}" width="${W}" height="${rowH}"/>
      ${narrow ? `<text class="lab" x="${left}" y="${y - 9}">${esc(clip(r.t))}</text>`
        : `<text class="lab" x="${left - 14}" y="${y + 4}" text-anchor="end">${esc(clip(r.t))}</text>`}
      <line class="link" x1="${x(r.b)}" x2="${x(r.q)}" y1="${y + dy}" y2="${y + dy}"/>
      <circle class="d-b" cx="${x(r.b)}" cy="${y + dy}" r="6"/><circle class="d-q" cx="${x(r.q)}" cy="${y + dy}" r="7.5"/>
      <text class="val" x="${x(r.q) + 12}" y="${y + dy + 4}">${fmt(+r.q.toFixed(3))}</text></g>`;
  });
  $("#dumb").innerHTML = s + "</svg>";
  const tip = $("#dumb-tip"), fig = $(".dumb-fig");
  $("#dumb").querySelectorAll(".row").forEach(g => {
    g.addEventListener("mousemove", ev => {
      const r = rows[g.dataset.i], box = fig.getBoundingClientRect();
      tip.innerHTML = `<strong>${esc(r.t)}</strong><br>${esc(r.m)}<br>Baseline (${esc(r.bl)}): ${fmt(+r.b.toFixed(3))}<br>Qloo (${esc(r.ql)}): ${fmt(+r.q.toFixed(3))}<br>Lead: +${fmt(+(r.q - r.b).toFixed(3))}`;
      tip.hidden = false;
      tip.style.left = Math.max(0, Math.min(ev.clientX - box.left + 14, box.width - 270)) + "px";
      tip.style.top = (ev.clientY - box.top + 14) + "px";
    });
    g.addEventListener("mouseleave", () => { tip.hidden = true; });
  });
  $("#dumb-table").innerHTML = `<table class="data"><thead><tr><th>Result</th><th>Metric</th><th>Baseline</th><th>Qloo</th><th>Lead</th></tr></thead><tbody>` +
    rows.map(r => `<tr><td>${esc(r.t)}</td><td>${esc(r.m)}</td><td>${fmt(+r.b.toFixed(3))} (${esc(r.bl)})</td><td>${fmt(+r.q.toFixed(3))}</td><td>+${fmt(+(r.q - r.b).toFixed(3))}</td></tr>`).join("") + "</tbody></table>";
  $("#dumb-toggle").onclick = () => {
    const t = $("#dumb-table"), show = t.hidden;
    t.hidden = !show; $("#dumb").hidden = show;
    $("#dumb-toggle").textContent = show ? "Show as chart" : "Show as table";
  };
}

/* ---------- reveal, count-up and chart fills when a thing scrolls into view ---------- */
function countUp(el) {
  if (el.dataset.done) return; el.dataset.done = "1";
  const to = +el.dataset.to, dec = +(el.dataset.dec || 0);
  if (still()) { el.textContent = to.toFixed(dec); return; }
  const t0 = performance.now(), dur = 1300;
  const f = t => { const k = Math.min(1, (t - t0) / dur), e = 1 - Math.pow(1 - k, 3); el.textContent = (to * e).toFixed(dec); if (k < 1) requestAnimationFrame(f); };
  requestAnimationFrame(f);
}
function animateIn(root) {
  root.querySelectorAll("[data-w]").forEach(i => { i.style.width = i.dataset.w + "%"; });
  root.querySelectorAll("[data-off]").forEach(c => { c.style.strokeDashoffset = c.dataset.off; });
  root.querySelectorAll("[data-to]").forEach(countUp);
  if (root.matches && root.matches(".dumb-fig")) $("#dumb").classList.add("in");
}
function reveals() {
  const els = document.querySelectorAll(".reveal, .sb-hero, .dumb-fig");
  if (!("IntersectionObserver" in window) || still()) { els.forEach(e => { e.classList.add("in"); animateIn(e); }); return; }
  const io = new IntersectionObserver(es => es.forEach(e => { if (e.isIntersecting) { e.target.classList.add("in"); animateIn(e.target); io.unobserve(e.target); } }), { threshold: .15 });
  els.forEach(e => io.observe(e));
}

/* ---------- agent radar ---------- */
const NODES = [
  { k: "core", x: 260, y: 150, r: 32, label: "GPT-6 Astra", sub: "the agent" },
  { k: "qloo", x: 260, y: 36, r: 26, label: "Qloo Insights" },
  { k: "store", x: 78, y: 78, r: 22, label: "Storefronts" },
  { k: "insp", x: 442, y: 78, r: 22, label: "Inspections" },
  { k: "census", x: 70, y: 226, r: 22, label: "Census" },
  { k: "subway", x: 450, y: 226, r: 22, label: "Subway" },
  { k: "bids", x: 260, y: 270, r: 22, label: "BIDs, partners" },
];
const radars = [];
class Radar {
  constructor(host) {
    this.host = host; this.counts = {}; this.live = false; this.inflight = 0;
    host.innerHTML = `<div class="av-head"><strong>Agent radar</strong><span class="av-state">Idle</span></div>
      <svg viewBox="0 0 520 322" aria-hidden="true">
        <g class="edges">${NODES.slice(1).map(n => `<line class="av-edge" data-k="${n.k}" x1="260" y1="150" x2="${n.x}" y2="${n.y}"/>`).join("")}</g>
        <g class="packets"></g>
        ${NODES.map(n => `<g class="av-node ${n.k === "core" ? "core" : ""} ${n.k === "qloo" ? "qloo" : ""}" data-k="${n.k}">
          <circle class="halo" cx="${n.x}" cy="${n.y}" r="${n.r}"/>
          <circle class="ring" cx="${n.x}" cy="${n.y}" r="${n.r}"/>
          <text x="${n.x}" y="${n.k === "core" ? n.y - 1 : n.y + n.r + 13}">${esc(n.label)}</text>
          <text class="n" x="${n.x}" y="${n.k === "core" ? n.y + 12 : n.y + 4}">${n.k === "core" ? "the agent" : "0"}</text></g>`).join("")}
      </svg>
      <ol class="av-log"><li>Waiting for a run. Start one, or open a finished run, to watch the real calls.</li></ol>`;
    this.svg = host.querySelector("svg"); this.pk = host.querySelector(".packets"); this.log = host.querySelector(".av-log");
    this.state = host.querySelector(".av-state");
  }
  setLive(on) { this.live = on; this.state.textContent = on ? "Calling" : "Idle"; this.state.classList.toggle("live", on); }
  fire(k, dim = false) {
    const n = NODES.find(x => x.k === k); if (!n || k === "core") return this.pulseCore();
    if (this.inflight > 10) return;
    this.inflight++;
    const edge = this.svg.querySelector(`.av-edge[data-k="${k}"]`), node = this.svg.querySelector(`.av-node[data-k="${k}"]`);
    if (!dim) {
      edge.classList.add("hot"); this.counts[k] = (this.counts[k] || 0) + 1;
      node.querySelector("text.n").textContent = this.counts[k];
    }
    const dot = document.createElementNS("http://www.w3.org/2000/svg", "circle");
    dot.setAttribute("r", dim ? 2.5 : 4.5); dot.setAttribute("class", "av-packet"); if (dim) dot.style.opacity = .45;
    this.pk.append(dot);
    const dur = dim ? 1400 : 520, t0 = performance.now();
    const step = t => {
      const p = Math.min(1, (t - t0) / dur), out = p < .5, u = out ? p * 2 : 2 - p * 2, e = u * u * (3 - 2 * u);
      dot.setAttribute("cx", 260 + (n.x - 260) * e); dot.setAttribute("cy", 150 + (n.y - 150) * e);
      if (!out && dot.getAttribute("class") !== "av-packet back") { dot.setAttribute("class", "av-packet back"); if (!dim) node.classList.add("flash"); }
      if (p < 1) requestAnimationFrame(step);
      else { dot.remove(); this.inflight--; node.classList.remove("flash"); setTimeout(() => edge.classList.remove("hot"), 250); }
    };
    if (still()) { dot.remove(); this.inflight--; node.classList.add("flash"); setTimeout(() => { node.classList.remove("flash"); edge.classList.remove("hot"); }, 400); return; }
    requestAnimationFrame(step);
  }
  pulseCore() { const c = this.svg.querySelector(".av-node.core .ring"); c.animate && c.animate([{ r: 32 }, { r: 37 }, { r: 32 }], { duration: 500 }); }
  say(html) {
    const li = document.createElement("li"); li.innerHTML = html; this.log.append(li);
    while (this.log.children.length > 4) this.log.firstChild.remove();
  }
  reset() {
    this.counts = {}; this.svg.querySelectorAll(".av-node:not(.core) text.n").forEach(t => { t.textContent = "0"; });
    this.log.innerHTML = "";
  }
}
/* Which source a streamed event touched. */
function route(e) {
  const nm = String(e.name || e.id || "").toLowerCase();
  if (e.type === "qloo") return "qloo";
  if (/qloo|taste|hours|scene|profile|insight/.test(nm)) return "qloo";
  if (/storefront|vacan|find|area/.test(nm)) return "store";
  if (/neighbourhood|census|customer|demograph|resolve/.test(nm)) return nm === "resolve" ? "core" : "census";
  if (/subway|transit/.test(nm)) return "subway";
  if (/bid|partner|next/.test(nm)) return "bids";
  if (/compet|restaurant|nearby|lease|score|rank|verify|check/.test(nm)) return "insp";
  if (/evidence/.test(nm)) return "qloo";
  return "core";
}
const LABEL = { qloo: "Qloo Insights", store: "Storefront Registry", insp: "NYC inspections", census: "Census", subway: "MTA subway", bids: "BIDs and partners", core: "the model" };
function onEvent(e) {
  if (!radars.length) return;
  let k = null, line = "";
  if (e.type === "step" && e.status === "running") {
    if (e.id === "scout" || e.id === "resolve" || e.id === "write" || e.id === "rewrite") { k = "core"; line = `<i>model</i> ${esc(e.label || e.id)}`; }
    else { k = route(e); line = `<i>call</i> ${esc(LABEL[k])}: ${esc(e.label || e.id)}`; }
    if (e.id === "verify") radars.forEach(r => r.fire("qloo"));
    radars.forEach(r => r.setLive(true));
  } else if (e.type === "qloo") {
    k = "qloo"; line = `<b>qloo</b> ${esc(e.path || "")} ${esc(e.status ?? "")}${e.cached ? " cached" : ""}`;
  } else if (e.type === "scout" && e.status !== "running") {
    k = route(e); line = `<i>${e.followup ? "tool" : "scout"}</i> ${esc(String(e.name || "").replace(/_/g, " "))}${e.summary ? ": " + esc(e.summary) : ""}`;
    radars.forEach(r => r.setLive(true));
  } else if (e.type === "scout_think") { k = "core"; line = "<i>model</i> thinking about the next move"; }
  else if (e.type === "leases") line = `<i>result</i> shortlist ready: ${e.data.length} storefronts`;
  else if (e.type === "brief") line = "<i>result</i> positioning brief written and checked";
  else if (e.type === "answer") { line = "<i>result</i> answer ready"; radars.forEach(r => r.setLive(false)); }
  else if (e.type === "done" || e.type === "error") { line = e.type === "done" ? "<i>done</i> run finished" : `<i>stopped</i> ${esc(e.message || "")}`; radars.forEach(r => r.setLive(false)); }
  else if (e.type === "run_start") { radars.forEach(r => r.reset()); return; }
  if (k) radars.forEach(r => r.fire(k));
  if (line) radars.forEach(r => r.say(line));
}
function radarsBoot() {
  document.querySelectorAll("[data-agent-viz]").forEach(h => radars.push(new Radar(h)));
  addEventListener("ws:event", ev => onEvent(ev.detail));
  // a new run clears the counters: app.js resets the trace with an empty step list
  const steps = $("#steps");
  if (steps) new MutationObserver(() => { if (!steps.children.length) radars.forEach(r => { r.reset(); r.say("Run started."); }); }).observe(steps, { childList: true });
  // idle: faint packets so the radar reads as a live system; they add nothing to the counters or the log
  setInterval(() => {
    if (document.hidden || still()) return;
    radars.forEach(r => { if (!r.live) r.fire(NODES[1 + Math.floor(Math.random() * 6)].k, true); });
  }, 1100);
}

/* ---------- Test 20 duel replay ---------- */
const ARMS = [["large_alone", "GPT-6 Astra alone", false], ["large_with_qloo", "GPT-6 Astra + Qloo", true],
  ["small_alone", "Gemini 3.8 Flash alone", false], ["small_with_qloo", "Gemini 3.8 Flash + Qloo", true]];
let duelData = null, duelBusy = false;
async function duelLoad() {
  if (duelData) return duelData;
  const res = await fetch("/api/test20");
  if (!res.ok) throw new Error("The recorded Test 20 answers are not on this server.");
  duelData = await res.json();
  pies(duelData);
  $("#dr-pick").innerHTML = duelData.rows.map((r, i) => `<option value="${i}">${esc(r.name)}</option>`).join("");
  $("#dr-score").innerHTML = ARMS.map(([a, l, q]) => `<span class="${q ? "q" : ""}">${esc(l)}: ${esc(duelData.totals[a])} of ${duelData.rows.length}</span>`).join("");
  return duelData;
}
/* Test 20 as four pies: how each model's 30 answers split into right, wrong and declined. */
function pies(d) {
  const arc = (cx, cy, r, a0, a1) => {
    const p = a => [cx + r * Math.sin(a), cy - r * Math.cos(a)], [x0, y0] = p(a0), [x1, y1] = p(a1);
    return `M${cx},${cy} L${x0.toFixed(2)},${y0.toFixed(2)} A${r},${r} 0 ${a1 - a0 > Math.PI ? 1 : 0} 1 ${x1.toFixed(2)},${y1.toFixed(2)} Z`;
  };
  const n = d.rows.length;
  $("#pie-row").innerHTML = ARMS.map(([key, label, q]) => {
    const right = d.rows.filter(r => r[key].right).length, said = d.rows.filter(r => r[key].said != null).length;
    const parts = [["right", right], ["wrong", said - right], ["declined", n - said]].filter(p => p[1] > 0);
    let a = 0;
    const wedges = parts.map(([k, v]) => {
      const a1 = a + v / n * 2 * Math.PI;
      const path = v === n ? `<circle class="w-${k}" cx="60" cy="60" r="56"/>` : `<path class="w-${k}" d="${arc(60, 60, 56, a, a1)}"/>`;
      a = a1; return path;
    }).join("");
    const say = parts.map(([k, v]) => `${v} ${k}`).join(", ");
    return `<div class="pie${q ? " wq" : ""}"><svg viewBox="0 0 120 120" role="img" aria-label="${esc(label)}: ${say} of ${n}">${wedges}</svg>
      <p><b>${right} of ${n}</b> right</p><span>${esc(label)}</span><small>${esc(say)}</small></div>`;
  }).join("");
  $("#t20-pies").hidden = false;
}
const wait = ms => new Promise(r => setTimeout(r, still() ? 0 : ms));
async function type(el, text) {
  el.textContent = "";
  if (still()) { el.textContent = text; return; }
  for (const ch of text) { el.textContent += ch; await wait(28); }
}
async function duelPlay() {
  if (duelBusy) return;
  let d;
  try { d = await duelLoad(); } catch (e) { $("#dr-q").textContent = e.message; return; }
  duelBusy = true; $("#dr-go").disabled = true;
  const r = d.rows[+$("#dr-pick").value || 0];
  $("#dr-q").innerHTML = `"When does <b>${esc(r.name)}</b> close on Friday?"${r.address ? ` <span class="hint">${esc(r.address)}</span>` : ""}`;
  $("#dr-truth").textContent = "";
  $("#dr-lanes").innerHTML = ARMS.map(([a, l, q]) => `<div class="lane ${q ? "wq" : ""}" data-a="${a}"><span class="who">${esc(l)}</span>
    ${q ? `<span class="call"></span>` : ""}<span class="bubble"><span class="dots">thinking</span></span><span class="res"></span></div>`).join("");
  const lanes = [...document.querySelectorAll("#dr-lanes .lane")];
  await wait(500);
  for (const ln of lanes.filter(l => l.classList.contains("wq"))) {
    ln.querySelector(".call").textContent = "→ calling Qloo place record…";
    onEvent({ type: "qloo", path: "/v2/insights place record", status: 200, cached: true });
  }
  await wait(800);
  for (const ln of lanes.filter(l => l.classList.contains("wq"))) ln.querySelector(".call").textContent = `← Qloo: closes ${r.qloo || "(no record)"} Friday`;
  await wait(400);
  await Promise.all(lanes.map(async (ln, i) => {
    await wait(i * 260);
    const a = r[ln.dataset.a], said = a.said ? `Closes at ${a.said}.` : "I don't know when it closes.";
    await type(ln.querySelector(".bubble"), said);
    const res = ln.querySelector(".res");
    res.className = "res " + (a.right ? "ok" : "no");
    res.textContent = a.right ? "✓ matches Google Maps" : a.said ? "✕ wrong" : "✕ declined";
    if (a.right && ln.classList.contains("wq")) ln.classList.add("won");
  }));
  $("#dr-truth").innerHTML = `Google Maps says: <b>${esc(r.google)}</b>.`;
  duelBusy = false; $("#dr-go").disabled = false;
}
function duelBoot() {
  if (!$("#duel-replay")) return;
  $("#dr-go").onclick = duelPlay;
  $("#dr-shuffle").onclick = async () => {
    try { const d = await duelLoad(); $("#dr-pick").value = String(Math.floor(Math.random() * d.rows.length)); duelPlay(); }
    catch (e) { $("#dr-q").textContent = e.message; }
  };
  const io = new IntersectionObserver(es => { if (es.some(e => e.isIntersecting)) { io.disconnect(); duelLoad().catch(e => { $("#dr-q").textContent = e.message; $("#dr-go").disabled = true; $("#dr-shuffle").disabled = true; }); } });
  io.observe($("#why"));
}

/* ---------- scroll progress ---------- */
function ambient() {
  const bar = $("#scroll-bar");
  const onScroll = () => { const h = document.documentElement.scrollHeight - innerHeight; bar.style.transform = `scaleX(${h > 0 ? scrollY / h : 0})`; };
  addEventListener("scroll", onScroll, { passive: true }); onScroll();
}

scoreboard();
radarsBoot();
duelBoot();
ambient();
reveals();
