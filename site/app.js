"use strict";

/* Column definitions. `key` indexes the team object; `label` is the header;
   `sort` toggles sortability; `cls` styles the td. */
const COLS = [
  { key: "position", label: "#", sort: false, cls: "col-rank" },
  { key: "name", label: "Club", sort: true, cls: "col-team" },
  { key: "games_played", label: "GP", sort: true, cls: "col-sub" },
  { key: "wins", label: "W", sort: true, cls: "col-sub" },
  { key: "draws", label: "D", sort: true, cls: "col-sub" },
  { key: "losses", label: "L", sort: true, cls: "col-sub" },
  { key: "points", label: "Pts", sort: true, cls: "col-pts" },
  { key: "ppg", label: "PPG", sort: true, cls: "col-sub" },
  { key: "goals_for", label: "GF", sort: true, cls: "col-sub" },
  { key: "goals_against", label: "GA", sort: true, cls: "col-sub" },
  { key: "goal_diff", label: "GD", sort: true, cls: "col-gd" },
  { key: "form", label: "Form", sort: false, cls: "col-form" },
];

/* Simulations tab columns. */
const SIM_COLS = [
  { key: "index", label: "#", sort: false, cls: "col-rank" },
  { key: "name", label: "Club", sort: true, cls: "col-team" },
  { key: "proj_points", label: "Proj Pts", sort: true, cls: "col-pts" },
  { key: "proj_gd", label: "Proj GD", sort: true, cls: "col-gd" },
  { key: "avg_finish", label: "Avg Fin", sort: true, cls: "col-sub" },
  { key: "p_title", label: "Title", sort: true, cls: "col-pct", heat: "--amber" },
  { key: "p_ucl", label: "Top 4", sort: true, cls: "col-pct", heat: "--amber" },
  { key: "p_europe", label: "Europe", sort: true, cls: "col-pct", heat: "--amber" },
  { key: "p_releg", label: "Releg", sort: true, cls: "col-pct", heat: "--amber" },
];

function el(tag, cls, html) {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (html != null) e.innerHTML = html;
  return e;
}

function crest(team) {
  const img = el("img", "crest");
  img.crossOrigin = "anonymous"; // ESPN CDN sends ACAO:* -> canvas-safe for PNG
  img.src = team.logo || "";
  img.alt = team.name;
  img.onerror = () => { img.style.visibility = "hidden"; };
  return img;
}

const signed = (v) => (v == null ? "—" : (v > 0 ? "+" + v : String(v)));
const signed1 = (v) => (v == null ? "—" : (v > 0 ? "+" + v.toFixed(1) : v.toFixed(1)));

/* Probability -> display text; `zero` mutes the cell. */
function fmtPct(p) {
  if (p == null) return { text: "—", zero: true };
  const v = p * 100;
  if (v <= 0) return { text: "—", zero: true };
  if (v < 0.1) return { text: "<0.1%", zero: false };
  if (v > 99.9) return { text: ">99.9%", zero: false };
  if (v >= 9.95) return { text: v.toFixed(0) + "%", zero: false };
  return { text: v.toFixed(1) + "%", zero: false };
}

/* Heat background for a probability cell, in the given CSS color variable. */
function pctHeat(p, rgbVar) {
  const a = (0.06 + 0.5 * Math.pow(Math.min(p, 1), 0.75)).toFixed(3);
  return `rgba(var(${rgbVar}), ${a})`;
}

/* A row of recent-result pills: blue = W, grey = D, red = L, oldest -> newest. */
function formPills(form) {
  const wrap = el("div", "form-guide");
  if (!form || !form.length) { wrap.textContent = "—"; return wrap; }
  for (const m of form) {
    const pill = el("span", "pill pill-" + m.r.toLowerCase(), m.r);
    const where = m.h ? "vs" : "@";
    pill.title = `${m.r} ${where} ${m.o || "?"} ${m.s || ""}`.trim();
    wrap.appendChild(pill);
  }
  return wrap;
}

/* Amber heat for the points column, scaled across the table's points range so
   the leader anchors the top of the ramp and the bottom club is near-clear. */
function ptsHeat(v, min, max) {
  if (v == null || max <= min) return "";
  const t = (v - min) / (max - min);
  const a = (0.06 + 0.5 * Math.pow(t, 0.9)).toFixed(3);
  return `rgba(var(--amber), ${a})`;
}

/* ---------------- state ---------------- */
let DATA = null;                 // full payload
let CURRENT = null;              // active league key
const SORT = { key: "position", dir: 1 };  // default = league order

function leagueByKey(key) {
  return (DATA.leagues || []).find((l) => l.key === key) || DATA.leagues[0];
}

/* ---------------- table rendering ---------------- */
function renderTable() {
  const lg = leagueByKey(CURRENT);
  const zoneColor = {};
  (lg.zones || []).forEach((z) => { zoneColor[z.key] = z.color; });

  const table = document.querySelector("#wrap-standings table");
  const thead = table.querySelector("thead");
  const tbody = table.querySelector("tbody");

  // header
  const tr = el("tr");
  for (const c of COLS) {
    const th = el("th", c.cls + (c.key === SORT.key ? " sorted" : ""));
    th.textContent = c.label;
    if (c.key === SORT.key) th.appendChild(el("span", "arrow", SORT.dir < 0 ? "▼" : "▲"));
    if (c.sort) {
      th.onclick = () => {
        if (SORT.key === c.key) SORT.dir = -SORT.dir;
        else { SORT.key = c.key; SORT.dir = c.key === "name" ? 1 : -1; }
        renderTable();
      };
    } else th.style.cursor = "default";
    tr.appendChild(th);
  }
  thead.innerHTML = "";
  thead.appendChild(tr);

  const inLeagueOrder = SORT.key === "position";
  const sorted = [...lg.teams].sort((a, b) => {
    let av = a[SORT.key], bv = b[SORT.key];
    if (av == null) av = -Infinity;
    if (bv == null) bv = -Infinity;
    if (typeof av === "string") return av.localeCompare(bv) * SORT.dir;
    return (av - bv) * SORT.dir;
  });

  const ptsVals = lg.teams.map((t) => t.points).filter((v) => v != null);
  const ptsMin = Math.min(...ptsVals);
  const ptsMax = Math.max(...ptsVals);

  tbody.innerHTML = "";
  sorted.forEach((t, i) => {
    const row = el("tr");
    for (const c of COLS) {
      const td = el("td", c.cls);
      if (c.key === "position") {
        const band = el("span", "band");
        const col = t.zone ? zoneColor[t.zone] : null;
        if (col) { band.style.background = col; td.style.setProperty("--zone", col); }
        td.appendChild(band);
        td.appendChild(document.createTextNode(inLeagueOrder ? t.position : (i + 1)));
        if (t.note) td.title = t.note;
      } else if (c.key === "name") {
        const wrap = el("div", "cell-team");
        wrap.appendChild(crest(t));
        wrap.appendChild(el("span", "nm", t.name));
        td.appendChild(wrap);
      } else if (c.key === "points") {
        td.textContent = t.points != null ? t.points : "—";
        const bg = ptsHeat(t.points, ptsMin, ptsMax);
        if (bg) td.style.background = bg;
      } else if (c.key === "ppg") {
        td.textContent = t.ppg != null ? t.ppg.toFixed(2) : "—";
      } else if (c.key === "goal_diff") {
        td.textContent = signed(t.goal_diff);
        if (t.goal_diff > 0) td.classList.add("gd-pos");
        else if (t.goal_diff < 0) td.classList.add("gd-neg");
      } else if (c.key === "form") {
        td.appendChild(formPills(t.form));
      } else {
        td.textContent = t[c.key] != null ? t[c.key] : "—";
      }
      row.appendChild(td);
    }
    tbody.appendChild(row);
  });
}

function renderLegend() {
  const lg = leagueByKey(CURRENT);
  const wrap = document.getElementById("zone-legend");
  wrap.innerHTML = "";
  for (const z of lg.zones || []) {
    const span = el("span");
    const sw = el("i", "sw");
    sw.style.background = z.color;
    span.appendChild(sw);
    span.appendChild(document.createTextNode(z.label));
    wrap.appendChild(span);
  }
}

/* ---------------- simulations table ---------------- */
const SORT_SIM = { key: "proj_points", dir: -1 };

function renderSim() {
  const lg = leagueByKey(CURRENT);
  const table = document.querySelector("#wrap-sims table");
  const thead = table.querySelector("thead");
  const tbody = table.querySelector("tbody");

  const tr = el("tr");
  for (const c of SIM_COLS) {
    const th = el("th", c.cls + (c.key === SORT_SIM.key ? " sorted" : ""));
    th.textContent = c.label;
    if (c.key === SORT_SIM.key) th.appendChild(el("span", "arrow", SORT_SIM.dir < 0 ? "▼" : "▲"));
    if (c.sort) {
      th.onclick = () => {
        if (SORT_SIM.key === c.key) SORT_SIM.dir = -SORT_SIM.dir;
        else { SORT_SIM.key = c.key; SORT_SIM.dir = c.key === "name" ? 1 : -1; }
        renderSim();
      };
    } else th.style.cursor = "default";
    tr.appendChild(th);
  }
  thead.innerHTML = ""; thead.appendChild(tr);

  const sorted = [...lg.teams].sort((a, b) => {
    let av = a[SORT_SIM.key], bv = b[SORT_SIM.key];
    if (av == null) av = -Infinity;
    if (bv == null) bv = -Infinity;
    if (typeof av === "string") return av.localeCompare(bv) * SORT_SIM.dir;
    return (av - bv) * SORT_SIM.dir;
  });

  tbody.innerHTML = "";
  sorted.forEach((t, i) => {
    const row = el("tr");
    for (const c of SIM_COLS) {
      const td = el("td", c.cls);
      if (c.key === "index") {
        td.textContent = i + 1;
      } else if (c.key === "name") {
        const wrap = el("div", "cell-team");
        wrap.appendChild(crest(t));
        wrap.appendChild(el("span", "nm", t.name));
        td.appendChild(wrap);
      } else if (c.key === "proj_points") {
        td.textContent = t.proj_points != null ? t.proj_points.toFixed(1) : "—";
      } else if (c.key === "proj_gd") {
        td.textContent = signed1(t.proj_gd);
        if (t.proj_gd > 0) td.classList.add("gd-pos");
        else if (t.proj_gd < 0) td.classList.add("gd-neg");
      } else if (c.key === "avg_finish") {
        td.textContent = t.avg_finish != null ? t.avg_finish.toFixed(1) : "—";
      } else if (c.heat) {
        const info = fmtPct(t[c.key]);
        td.textContent = info.text;
        if (info.zero) td.classList.add("pct-zero");
        else td.style.background = pctHeat(t[c.key], c.heat);
      } else {
        td.textContent = t[c.key] != null ? t[c.key] : "—";
      }
      row.appendChild(td);
    }
    tbody.appendChild(row);
  });
}

function renderCrest() {
  const lg = leagueByKey(CURRENT);
  for (const id of ["league-crest", "league-crest-sims"]) {
    const img = document.getElementById(id);
    if (!img) continue;
    img.src = lg.logo || "";
    img.alt = lg.name;
    img.style.visibility = "visible";
    img.onerror = () => { img.style.visibility = "hidden"; };
  }
}

/* Switch to a league: reset sort to league order, re-render every tab. */
function selectLeague(key, { push = true } = {}) {
  const lg = leagueByKey(key);
  CURRENT = lg.key;
  SORT.key = "position"; SORT.dir = 1;
  document.getElementById("league-select").value = CURRENT;
  const simSel = document.getElementById("league-select-sims");
  if (simSel) simSel.value = CURRENT;
  renderCrest();
  renderLegend();
  renderTable();
  renderSim();
  updateSimNote();
  if (push) history.replaceState(null, "", "#" + CURRENT);
}

function updateSimNote() {
  const note = document.getElementById("sims-note");
  const lg = leagueByKey(CURRENT);
  if (!note) return;
  const sim = lg.sim || {};
  const n = (sim.n_sims || 0).toLocaleString();
  if (sim.n_remaining > 0) {
    note.textContent = `${n} simulations of the ${sim.n_remaining} remaining fixtures.`;
  } else {
    note.textContent = "The season is complete — the table below is final. " +
      "Live odds return once the new season kicks off.";
  }
}

/* ---------------- tabs ---------------- */
function activateTab(name) {
  let matched = false;
  document.querySelectorAll(".tab").forEach((t) => {
    const on = t.dataset.tab === name;
    t.classList.toggle("is-active", on);
    matched = matched || on;
  });
  if (!matched) return;
  document.querySelectorAll(".panel").forEach((p) =>
    p.classList.toggle("is-active", p.id === name));
}

function setupTabs() {
  document.querySelectorAll(".tab").forEach((tab) => {
    tab.onclick = () => activateTab(tab.dataset.tab);
  });
}

/* ---------------- downloads ---------------- */
let DATE_STR = "";

function triggerBlobDownload(blob, filename) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url; a.download = filename;
  document.body.appendChild(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

async function capturePng(btn) {
  const which = btn.dataset.png;                 // "standings" | "sims"
  const node = document.getElementById(`wrap-${which}`);
  if (typeof html2canvas === "undefined") {
    alert("PNG export needs the rendering library, which didn't load.");
    return;
  }
  const label = btn.textContent;
  btn.disabled = true; btn.textContent = "Rendering…";
  try {
    const surface = getComputedStyle(document.body).backgroundColor;
    const canvas = await html2canvas(node, {
      scale: 3, backgroundColor: surface, useCORS: true, logging: false,
    });
    await new Promise((res) => canvas.toBlob((b) => {
      if (b) triggerBlobDownload(b, `big5-${CURRENT}-${which}-${DATE_STR}.png`);
      res();
    }, "image/png"));
  } catch (e) {
    alert("Couldn't render the image. PNG export works best when the page is " +
          "served over http (run `python -m http.server` in site/).\n\n" + e);
  } finally {
    btn.disabled = false; btn.textContent = label;
  }
}

const CSV_COLS = {
  standings: [
    ["position", "Pos"], ["name", "Club"], ["zone", "Zone"],
    ["games_played", "GP"], ["wins", "W"], ["draws", "D"], ["losses", "L"],
    ["points", "Pts"], ["ppg", "PPG"],
    ["goals_for", "GF"], ["goals_against", "GA"], ["goal_diff", "GD"],
    ["form", "Form"],
  ],
  sims: [
    ["name", "Club"], ["proj_points", "ProjPts"], ["proj_gd", "ProjGD"],
    ["avg_finish", "AvgFinish"], ["p_title", "Title"], ["p_ucl", "Top4"],
    ["p_europe", "Europe"], ["p_releg", "Relegation"],
  ],
};

function downloadCsv(which) {
  const lg = leagueByKey(CURRENT);
  const cols = CSV_COLS[which];
  const esc = (v) => {
    const s = v == null ? "" : String(v);
    return /[",\n]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s;
  };
  const lines = [cols.map((c) => c[1]).join(",")];
  lg.teams.forEach((t) => {
    lines.push(cols.map(([k]) => {
      if (k === "form") return esc((t.form || []).map((m) => m.r).join("-"));
      return esc(t[k]);
    }).join(","));
  });
  const blob = new Blob([lines.join("\n") + "\n"], { type: "text/csv;charset=utf-8" });
  triggerBlobDownload(blob, `big5-${CURRENT}-${which}-${DATE_STR}.csv`);
}

function setupDownloads() {
  document.querySelectorAll("[data-png]").forEach((b) =>
    b.onclick = () => capturePng(b));
  document.querySelectorAll("[data-csv]").forEach((b) =>
    b.onclick = () => downloadCsv(b.dataset.csv));
}

/* ---------------- boot ---------------- */
async function boot() {
  setupTabs();
  let data = window.BIG5_DATA;
  if (!data) {
    try {
      const resp = await fetch("data.json", { cache: "no-store" });
      data = await resp.json();
    } catch (e) {
      document.getElementById("meta").textContent =
        "Could not load data — run `python run.py` to generate site/data.json.";
      return;
    }
  }
  DATA = data;

  const m = data.meta || {};
  document.getElementById("meta").innerHTML =
    `${m.season_label || m.season || ""} Season &middot; Updated <b>${m.generated || "—"}</b>`;
  DATE_STR = (m.generated || "").split(" ")[0] ||
             new Date().toISOString().slice(0, 10);

  // populate both league dropdowns (standings + sims), kept in sync
  for (const id of ["league-select", "league-select-sims"]) {
    const sel = document.getElementById(id);
    if (!sel) continue;
    sel.innerHTML = "";
    for (const lg of data.leagues) {
      const opt = document.createElement("option");
      opt.value = lg.key; opt.textContent = lg.name;
      sel.appendChild(opt);
    }
    sel.onchange = () => selectLeague(sel.value);
  }

  const fromHash = () =>
    (location.hash && data.leagues.some((l) => l.key === location.hash.slice(1)))
      ? location.hash.slice(1) : null;
  selectLeague(fromHash() || data.leagues[0].key, { push: false });

  // React to shareable deep-links and browser back/forward.
  window.addEventListener("hashchange", () => {
    const key = fromHash();
    if (key && key !== CURRENT) selectLeague(key, { push: false });
  });

  setupDownloads();
}

boot();
