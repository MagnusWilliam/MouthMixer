"use strict";

const $ = (s) => document.querySelector(s);
const api = async (path, opts = {}) => {
  const r = await fetch(path, opts);
  if (!r.ok) throw new Error((await r.text()) || r.statusText);
  return r.json();
};
const post = (path, body) =>
  api(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body || {}) });
const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

let view = "songs";
let selected = null;
let currentSong = null;
let currentClip = null;
let listenerPaused = false;
let lastStatus = null;

const NAMES = ["C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"];
const noteName = (m) => NAMES[m % 12] + (Math.floor(m / 12) - 1);
const fmtTime = (t) => new Date(t * 1000).toLocaleString([], { weekday: "short", hour: "2-digit", minute: "2-digit" });
const fmtLen = (s) => `${Math.floor(s / 60)}:${String(Math.round(s % 60)).padStart(2, "0")}`;
const KIND = { melody: "Melody", beat: "Beat", both: "Melody + beat" };
const css = (n) => getComputedStyle(document.documentElement).getPropertyValue(n).trim();

// ---- status bar -------------------------------------------------------------------------------
async function refreshStatus() {
  try {
    const s = await api("/api/status");
    lastStatus = s;
    const L = s.listener;
    const st = L.state || "not running";
    $("#dot").className = "dot " + st;
    let text = { listening: "Listening", capturing: "Capturing…", paused: "Paused", muted: "Mic muted",
      "no mic": "Mic not found (pick one in Setup)", "not running": "Background listening off" }[st] || st;
    if (L.auto_pause_reason) text += ` (${L.auto_pause_reason})`;
    if (L.device && st !== "not running") text += ` · ${L.device}`;
    if (st !== "not running") text += ` · kept ${L.kept_today || 0}, ignored ${L.dropped_today || 0} today`;
    if (st !== "not running" && L.audio_age_s != null && L.audio_age_s > 2) text += ` · no sound from the mic for ${Math.round(L.audio_age_s)} s`;
    if (st !== "not running" && L.notice) text += ` · ${L.notice}`;
    $("#state").textContent = text;
    listenerPaused = !!L.paused_by_user;
    $("#pause").textContent = listenerPaused ? "Resume" : "Pause";
    $("#pause").disabled = $("#save-last").disabled = st === "not running";
    $("#count-songs").textContent = (s.songs && s.songs.new) || "";
    const busy = s.writing > 0 ? "Writing a song: trying styles and combinations, checking each one…" :
      s.processing > 0 ? "Listening to a new clip…" : "";
    $("#working").classList.toggle("hidden", !busy);
    $("#working-text").textContent = busy;
    if (view === "setup") updateLevel(L);
  } catch (e) {
    $("#state").textContent = "App not responding";
  }
}
$("#pause").onclick = async () => { await post("/api/listener/" + (listenerPaused ? "resume" : "pause")); setTimeout(refreshStatus, 700); };
$("#save-last").onclick = async () => { await post("/api/listener/save_last"); setTimeout(refreshList, 2500); };

// ---- list ---------------------------------------------------------------------------------------
async function refreshList() {
  if (view === "setup" || view === "make") return;
  const list = $("#list");
  let items;
  if (view === "clips") items = await api("/api/clips?view=all");
  else items = await api("/api/songs?view=" + (view === "kept" ? "kept" : "inbox"));
  list.innerHTML = "";
  const empty = $("#empty");
  empty.classList.toggle("hidden", items.length > 0);
  empty.innerHTML = view === "songs"
    ? "No songs yet. Hum, whistle or beatbox while you work (or press the hotkey right after an idea). Each good clip becomes a finished song here; this takes a little while after you stop."
    : view === "kept" ? "Songs you keep show up here." : "Every clip MouthMixer kept shows up here.";
  for (const it of items) {
    const el = document.createElement("div");
    el.className = "item" + (it.id === selected ? " sel" : "");
    if (view === "clips") {
      const q = it.quality == null ? "" : it.quality >= 0.6 ? " · good" : " · unsure";
      const what = it.status === "processing" ? "Working on it…" : it.status === "failed" ? "Couldn't analyse" :
        [KIND[it.kind], it.key, it.bpm ? Math.round(it.bpm) + " BPM" : null].filter(Boolean).join(" · ");
      el.innerHTML = `<div class="t">${fmtTime(it.created)}${it.source === "hotkey" ? " · hotkey" : ""}</div>
        <div class="s">${esc(what)}${q}${it.song_id ? " · in a song" : ""}</div>`;
      el.onclick = () => selectClip(it.id);
    } else {
      el.innerHTML = `<div class="t">${esc(it.title || "Song")}</div>
        <div class="s">${fmtTime(it.created)} · ${it.versions} version${it.versions > 1 ? "s" : ""}</div>`;
      el.onclick = () => selectSong(it.id);
    }
    list.appendChild(el);
  }
  if (!selected && items.length) (view === "clips" ? selectClip : selectSong)(items[0].id);
}

function showPane(name) {
  $("#song").classList.toggle("hidden", name !== "song");
  $("#clip").classList.toggle("hidden", name !== "clip");
}
function markSelected() {
  document.querySelectorAll(".item").forEach((e) => e.classList.remove("sel"));
}

// ---- songs --------------------------------------------------------------------------------------
async function selectSong(id) {
  selected = id;
  markSelected();
  currentSong = await api("/api/songs/" + id);
  showPane("song");
  renderSong();
  refreshList();
}

function renderSong() {
  const s = currentSong, rec = s.record, vi = s.version || 0, v = rec.versions[vi];
  $("#s-title").textContent = v.title;
  const secs = v.critic.details.seconds || 0;
  $("#s-chips").innerHTML = [v.style, v.key, Math.round(v.bpm) + " BPM", fmtLen(secs), `version ${vi + 1} of ${rec.versions.length}`]
    .map((c) => `<span class="chip">${esc(c)}</span>`).join("");
  // Songs built in Make: a way back to that track to change the music (rebuilding adds a new version here)
  const pid = (v.spec && v.spec.project) || rec.project;
  $("#s-make").innerHTML = pid ? `<button id="s-tomake" class="ghost">✎ Back to Make: change the music</button>
    <span class="small muted">Rebuild there and it comes back here as a new version.</span>` : "";
  if (pid) $("#s-tomake").onclick = () => openInMake(pid);
  const mine = v.tracks.filter((t) => t.mine).map((t) => `${t.name.toLowerCase()} (${t.instrument})`);
  const clips = [...new Set(v.spec.clips)];
  $("#s-parts").innerHTML = `<b>Yours:</b> ${mine.length ? esc(mine.join(", ")) : "the idea it grew from"} ` +
    `<span class="muted">(from ${clips.length} clip${clips.length > 1 ? "s" : ""})</span><br>` +
    `<b>Added:</b> ${esc((v.added || []).join(", "))}`;
  $("#s-audio").src = `/api/songs/${s.id}/file/${v.file}`;
  $("#s-dl-audio").href = `/api/songs/${s.id}/file/${v.file}`;
  $("#s-dl-midi").href = `/api/songs/${s.id}/file/${v.midi}`;
  const vers = $("#s-versions");
  vers.innerHTML = "";
  rec.versions.forEach((x, i) => {
    const b = document.createElement("button");
    b.className = "ver" + (i === vi ? " on" : "");
    b.innerHTML = `<b>${i + 1}</b> ${esc(x.style)} <span class="muted">${Math.round(x.score * 100)}</span>`;
    b.title = x.describe;
    b.onclick = async () => { await post(`/api/songs/${s.id}/version`, { version: i }); await selectSong(s.id); };
    vers.appendChild(b);
  });
  $("#s-summary").textContent = rec.summary + (rec.history ? " " + rec.history.join(" ") : "");
  const d = v.critic.details, sec = v.critic.sections;
  const checks = [
    [`Melody notes on the beat that belong to the chord: ${Math.round(d.chord_tones_on_beats * 100)}%`, d.chord_tones_on_beats >= 0.6],
    [`Clashing notes: ${d.clashes}`, d.clashes === 0],
    [`Chord flow ${Math.round(d.progression_flow * 100)}/100, smooth voice leading (avg ${d.voice_leading} semitones)`, d.progression_flow >= 0.5],
    [`Kick and bass together: ${Math.round(d.kick_bass_lock * 100)}% of kicks`, d.kick_bass_lock >= 0.4],
    [`Melody ${d.lead_vs_rest_db > 0 ? d.lead_vs_rest_db + " dB above" : Math.abs(d.lead_vs_rest_db) + " dB under"} the band where the ear listens (1-4 kHz)`, d.lead_vs_rest_db >= -2],
    [`Bass still heard on phone speakers (${Math.round(d.bass_audible_on_phones * 100)}% of its energy above 150 Hz)`, d.bass_audible_on_phones >= 0.05],
    [`Loudness -14 LUFS, peak ${d.peak_db} dB (no clipping), stereo safe in mono (${d.stereo_corr})`, true],
    [`Scores: melody ${pct(sec.melody)}, harmony ${pct(sec.harmony)}, bass ${pct(sec.bass)}, arrangement ${pct(sec.arrangement)}, mix ${pct(sec.mix)}`, true],
  ];
  $("#s-checks").innerHTML = checks.map(([t, ok]) => `<li class="${ok ? "ok" : "warn"}">${esc(t)}</li>`).join("");
  drawScore();
  if (window.onSongShown) window.onSongShown(currentSong);
}
const pct = (x) => Math.round(x * 100);

for (const [btn, status] of [["#s-keep", "kept"], ["#s-toss", "tossed"]]) {
  $(btn).onclick = async () => {
    if (!currentSong) return;
    await post(`/api/songs/${currentSong.id}/status`, { status });
    selected = null; currentSong = null; showPane(null);
    refreshList(); refreshStatus();
  };
}
async function another(different) {
  if (!currentSong) return;
  const id = currentSong.id, before = currentSong.record.versions.length;
  await post(`/api/songs/${id}/another`, { different_style: different });
  refreshStatus();
  for (let i = 0; i < 120; i++) {  // poll until the new version is there (up to 4 minutes)
    await new Promise((r) => setTimeout(r, 2000));
    const s = await api("/api/songs/" + id);
    if (s.record.versions.length > before) { if (selected === id) { currentSong = s; renderSong(); } return; }
    if (!(lastStatus && lastStatus.writing > 0) && i > 3) break;
  }
}
$("#s-another").onclick = () => another(false);
$("#s-different").onclick = () => another(true);

// The score: one lane per part, sections and chords on top, a playhead while it plays.
const ROLE_ORDER = ["lead", "counter", "arp", "comp", "pad", "bass", "timpani", "drums"];
function drawScore(playBeat) {
  if (!currentSong) return;
  const v = currentSong.record.versions[currentSong.version || 0];
  const tracks = v.tracks.slice().sort((a, b) => ROLE_ORDER.indexOf(a.role) - ROLE_ORDER.indexOf(b.role));
  const cv = $("#score"), dpr = window.devicePixelRatio || 1;
  const laneH = 30, top = 40, left = 150;
  const w = cv.clientWidth, h = top + tracks.length * laneH + 6;
  cv.style.height = h + "px"; cv.width = w * dpr; cv.height = h * dpr;
  const ctx = cv.getContext("2d");
  ctx.scale(dpr, dpr);
  const total = v.bars * 4;
  const X = (b) => left + (b / total) * (w - left - 8);
  ctx.font = "11px system-ui";
  // Sections
  v.sections.forEach((s, i) => {
    ctx.fillStyle = i % 2 ? css("--grid") : css("--bg");
    ctx.fillRect(X(s.start * 4), 0, X((s.start + s.bars) * 4) - X(s.start * 4), h);
    ctx.fillStyle = css("--ink");
    ctx.fillText(s.name, X(s.start * 4) + 4, 13);
  });
  // Chords
  ctx.fillStyle = css("--muted");
  let lastX = -99;
  for (const c of v.chords) {
    const x = X(c.start);
    if (x - lastX > 34) { ctx.fillText(c.name, x + 2, 29); lastX = x; }
  }
  // Bar lines
  for (let b = 0; b <= v.bars; b++) {
    ctx.strokeStyle = css("--bar"); ctx.globalAlpha = b % 4 === 0 ? 0.9 : 0.35;
    ctx.beginPath(); ctx.moveTo(X(b * 4), top - 4); ctx.lineTo(X(b * 4), h); ctx.stroke();
  }
  ctx.globalAlpha = 1;
  const colours = { lead: "--clean", counter: "--violet", arp: "--teal", comp: "--green", pad: "--pad", bass: "--amber", timpani: "--red", drums: "--muted" };
  tracks.forEach((t, i) => {
    const y0 = top + i * laneH;
    ctx.fillStyle = css("--ink");
    ctx.fillText(t.name + (t.mine ? "  ★ yours" : ""), 6, y0 + 12);
    ctx.fillStyle = css("--muted");
    ctx.fillText(t.instrument, 6, y0 + 25);
    ctx.strokeStyle = css("--line"); ctx.beginPath(); ctx.moveTo(0, y0); ctx.lineTo(w, y0); ctx.stroke();
    if (!t.notes.length) return;
    const ps = t.notes.map((n) => n[2]);
    const lo = Math.min(...ps), hi = Math.max(...ps), span = Math.max(1, hi - lo);
    ctx.fillStyle = css(colours[t.role] || "--clean");
    for (const [s, l, p, vel] of t.notes) {
      const y = t.role === "drums" ? y0 + 4 + (1 - (p - lo) / span) * (laneH - 10) : y0 + 3 + (1 - (p - lo) / span) * (laneH - 9);
      ctx.globalAlpha = 0.35 + 0.65 * vel / 127;
      ctx.fillRect(X(s), y, Math.max(1.5, X(s + l) - X(s) - 0.5), t.role === "drums" ? 2.5 : 3);
    }
    ctx.globalAlpha = 1;
  });
  if (playBeat != null) {
    ctx.strokeStyle = css("--red"); ctx.lineWidth = 2;
    ctx.beginPath(); ctx.moveTo(X(playBeat), 0); ctx.lineTo(X(playBeat), h); ctx.stroke();
  }
}
$("#s-audio").ontimeupdate = () => {
  if (!currentSong) return;
  const v = currentSong.record.versions[currentSong.version || 0];
  drawScore($("#s-audio").currentTime * v.bpm / 60);
};

// ---- clips --------------------------------------------------------------------------------------
async function selectClip(id) {
  selected = id;
  markSelected();
  currentClip = await api("/api/clips/" + id);
  showPane("clip");
  const c = currentClip, r = c.result;
  $("#d-title").textContent = fmtTime(c.created) + (r ? " · " + KIND[r.kind] : "");
  const chips = [];
  if (r) {
    const t = r.tempo;
    chips.push(Math.round(t.bpm) + " BPM" + (Math.abs(t.drift) >= 0.02 ? ` (drifted ${t.drift > 0 ? "faster" : "slower"} ${Math.round(Math.abs(t.drift) * 100)}%, fixed)` : ""));
    if (r.key && r.notes.length) chips.push(r.key.name);
    if (t.swing > 0.5) chips.push("swung " + Math.round(t.swing * 100) + "%");
    if (r.notes.length) chips.push(r.notes.length + " notes");
    if (r.drums.length) chips.push(r.drums.length + " drum hits");
    if (Math.abs(r.tuning_offset) > 0.15) chips.push(`${Math.round(Math.abs(r.tuning_offset) * 100)} cents ${r.tuning_offset < 0 ? "flat" : "sharp"} overall (fixed)`);
  }
  $("#d-chips").innerHTML = chips.map((x) => `<span class="chip">${esc(x)}</span>`).join("");
  const reasons = c.quality_reasons ? JSON.parse(c.quality_reasons) : [];
  $("#d-quality").innerHTML = c.quality == null ? "" : c.quality >= 0.6
    ? `<span class="okc">Follows musical rules (${pct(c.quality)}/100)</span>${c.song_id ? " · already in a song" : ""}`
    : `<span class="warnc">Unsure (${pct(c.quality)}/100): ${esc(reasons.join(", ") || "weak")}</span> · no song was made automatically`;
  $("#a-raw").src = `/api/clips/${id}/audio/raw`;
  $("#a-preview").src = `/api/clips/${id}/audio/preview?r=${c.reading || 0}`;
  $("#m-clean").href = `/api/clips/${id}/midi/clean`;
  $("#m-raw").href = `/api/clips/${id}/midi/raw`;
  $("#d-reading").textContent = c.reading ? "Reading: " + c.reading_label : "";
  drawRoll();
  refreshList();
}
$("#b-song").onclick = async () => {
  if (!currentClip) return;
  await post(`/api/clips/${currentClip.id}/song`);
  $("#b-song").textContent = "Writing… it'll appear under Songs";
  setTimeout(() => { $("#b-song").textContent = "Make a song from this"; }, 8000);
  refreshStatus();
};
for (const [btn, status] of [["#b-toss", "tossed"], ["#b-notmusic", "not_music"]]) {
  $(btn).onclick = async () => {
    if (!currentClip) return;
    await post(`/api/clips/${currentClip.id}/status`, { status });
    selected = null; currentClip = null; showPane(null); refreshList();
  };
}
$("#b-reading").onclick = async () => {
  if (!currentClip) return;
  $("#b-reading").disabled = true;
  $("#d-reading").textContent = "Listening again…";
  try { await post(`/api/clips/${currentClip.id}/reading`); await selectClip(currentClip.id); }
  finally { $("#b-reading").disabled = false; }
};

function beatsOf(t, g) {
  const tt = t - g.phase, rate = g.bpm / 60, k = g.drift / Math.max(g.span, 1e-6);
  return rate * (tt + 0.5 * k * tt * tt) - g.downbeat;
}
function drawRoll(playBeat) {
  const r = currentClip && currentClip.result;
  const cv = $("#roll"), dpr = window.devicePixelRatio || 1;
  const hasNotes = r && (r.notes.length || r.notes_raw.length);
  const w = cv.clientWidth, h = hasNotes ? 300 : 70;
  cv.style.height = h + "px"; cv.width = w * dpr; cv.height = h * dpr;
  const ctx = cv.getContext("2d");
  ctx.scale(dpr, dpr);
  if (!r) return;
  const g = r.grid;
  const raw = r.notes_raw.map((n) => ({ s: beatsOf(n.onset, g), e: beatsOf(n.onset + n.duration, g), p: n.pitch }));
  const end = Math.max(4, ...r.notes.map((n) => n.start + n.length), ...r.drums.map((d) => d.start + 0.5), ...raw.map((n) => n.e));
  const bars = Math.ceil(end / 4);
  const pitches = r.notes.map((n) => n.pitch).concat(raw.map((n) => n.p));
  const lo = pitches.length ? Math.floor(Math.min(...pitches)) - 2 : 60, hi = pitches.length ? Math.ceil(Math.max(...pitches)) + 2 : 72;
  const drumH = r.drums.length ? 46 : 0;
  const left = 36, top = 6, rollH = hasNotes ? h - top - drumH - 8 : 0;
  const X = (b) => left + (b / (bars * 4)) * (w - left - 6);
  const Y = (p) => top + (hi - p) / (hi - lo + 1) * rollH;
  const rowH = rollH / (hi - lo + 1);
  ctx.font = "10px system-ui";
  for (let p = lo; hasNotes && p <= hi; p++) {
    if (NAMES[p % 12].length === 2) { ctx.fillStyle = css("--grid"); ctx.fillRect(left, Y(p), w - left, rowH); }
    if (p % 12 === 0 || p === lo) { ctx.fillStyle = css("--muted"); ctx.fillText(noteName(p), 2, Y(p) + rowH - 2); }
  }
  for (let b = 0; b <= bars * 4; b++) {
    ctx.strokeStyle = b % 4 === 0 ? css("--bar") : css("--grid");
    ctx.beginPath(); ctx.moveTo(X(b), top); ctx.lineTo(X(b), h - 4); ctx.stroke();
  }
  ctx.fillStyle = css("--raw");
  for (const n of raw) ctx.fillRect(X(n.s), Y(n.p) + 1, Math.max(2, X(n.e) - X(n.s)), rowH - 2);
  for (const n of r.notes) {
    ctx.fillStyle = n.chromatic ? css("--chrom") : css("--clean");
    const x = X(n.start), wd = Math.max(3, X(n.start + n.length) - x - 1);
    ctx.beginPath(); ctx.roundRect(x, Y(n.pitch) + 1, wd, rowH - 2, 3); ctx.fill();
  }
  if (drumH) {
    const lanes = { kick: 0, snare: 1, hat: 2, open_hat: 2, clap: 1, rim: 1, tom: 0 };
    const y0 = h - drumH - 2;
    ctx.fillStyle = css("--muted");
    ["kick", "snare", "hats"].forEach((l, i) => ctx.fillText(l, 2, y0 + i * 15 + 11));
    for (const d of r.drums) {
      ctx.fillStyle = d.name === "open_hat" ? css("--chrom") : css("--clean");
      ctx.globalAlpha = 0.35 + 0.65 * d.velocity / 127;
      ctx.beginPath(); ctx.arc(X(d.start), y0 + (lanes[d.name] ?? 1) * 15 + 7, 5, 0, 7); ctx.fill();
    }
    ctx.globalAlpha = 1;
  }
  if (playBeat != null) {
    ctx.strokeStyle = css("--red"); ctx.lineWidth = 2;
    ctx.beginPath(); ctx.moveTo(X(playBeat), top); ctx.lineTo(X(playBeat), h - 4); ctx.stroke();
  }
}
$("#a-preview").ontimeupdate = () => { if (currentClip && currentClip.result) drawRoll($("#a-preview").currentTime * currentClip.result.tempo.bpm / 60); };
$("#a-raw").ontimeupdate = () => { if (currentClip && currentClip.result) drawRoll(beatsOf($("#a-raw").currentTime, currentClip.result.grid)); };
window.onresize = () => { if (currentSong && view !== "clips") drawScore(); if (currentClip) drawRoll(); };

// Open a Make track (from a song built from it).
async function openInMake(pid) {
  try {
    const p = await api("/api/projects/" + pid);
    if (window.Eng) Eng.stop(true);
    Make.proj = p; Make.on = {};
    document.querySelector('[data-view="make"]').click();  // Make.open() shows the track that's set
  } catch (e) { alert("That Make track isn't there any more (it may have been deleted)."); }
}

// ---- tabs -------------------------------------------------------------------------------------
document.querySelectorAll(".tab").forEach((t) => {
  t.onclick = () => {
    document.querySelectorAll(".tab").forEach((x) => x.classList.remove("active"));
    t.classList.add("active");
    view = t.dataset.view;
    selected = null; currentSong = null; currentClip = null;
    showPane(null);
    const setup = view === "setup", make = view === "make";
    $("#setup").classList.toggle("hidden", !setup);
    $("#make").classList.toggle("hidden", !make);
    $("#list-pane").classList.toggle("hidden", setup || make);
    if (!make && window.Make) Make.leave();
    if (setup) { refreshMics(); refreshCalibration(); if (window.refreshKey) refreshKey(); }
    else if (make) Make.open();
    else refreshList();
  };
});

// ---- setup: microphone --------------------------------------------------------------------------
async function refreshMics() {
  const m = await api("/api/mics");
  const sel = $("#mic-select");
  sel.innerHTML = "";
  if (!m.devices.length) sel.innerHTML = `<option value="">(no microphones found)</option>`;
  for (const d of m.devices) {
    const o = document.createElement("option");
    o.value = d.name; o.textContent = d.name;
    if (d.name === m.current || (!m.devices.some((x) => x.name === m.current) && m.current && d.name.toLowerCase().includes(m.current.toLowerCase()))) o.selected = true;
    sel.appendChild(o);
  }
}
$("#mic-use").onclick = async () => {
  await post("/api/mic", { name: $("#mic-select").value });
  $("#mic-now").textContent = "Switching…";
  setTimeout(refreshStatus, 1500);
};
function updateLevel(L) {
  const db = L.level_db;
  $("#mic-level").style.width = db == null ? "0%" : Math.max(0, Math.min(100, (db + 70) * 1.6)) + "%";
  $("#mic-now").textContent = L.device ? `Listening on: ${L.device}${db != null ? ` (${Math.round(db)} dB)` : ""}` :
    L.state === "not running" ? "The listener isn't running." : "No mic open.";
}

// ---- setup: calibration, mic test, upload -------------------------------------------------------
async function record(seconds, onLevel) {
  const dev = localStorage.getItem("mm-sing-mic") || "";
  const stream = await navigator.mediaDevices.getUserMedia({ audio: { deviceId: dev ? { ideal: dev } : undefined,
    echoCancellation: false, noiseSuppression: false, autoGainControl: false, channelCount: 1 } });
  const ctx = new AudioContext();
  const src = ctx.createMediaStreamSource(stream);
  const chunks = [];
  const take = (d) => {
    chunks.push(d);
    if (onLevel) { let s = 0; for (const v of d) s += v * v; onLevel(Math.sqrt(s / d.length)); }
  };
  let node;
  try {  // on the audio thread, so a busy page can't drop audio (see capture-worklet.js)
    await ctx.audioWorklet.addModule("/static/capture-worklet.js");
    node = new AudioWorkletNode(ctx, "mm-capture", { channelCount: 1, channelCountMode: "explicit" });
    node.port.onmessage = (e) => take(e.data.d);
  } catch {
    node = ctx.createScriptProcessor(4096, 1, 1);
    node.onaudioprocess = (e) => take(new Float32Array(e.inputBuffer.getChannelData(0)));
  }
  const sink = ctx.createGain(); sink.gain.value = 0;
  src.connect(node); node.connect(sink).connect(ctx.destination);
  await new Promise((r) => setTimeout(r, seconds * 1000));
  node.disconnect(); src.disconnect(); stream.getTracks().forEach((t) => t.stop());
  const sr = ctx.sampleRate; await ctx.close();
  const n = chunks.reduce((a, c) => a + c.length, 0);
  const all = new Float32Array(n); let o = 0; for (const c of chunks) { all.set(c, o); o += c.length; }
  return { samples: all, sr };
}
function wavBlob(samples, sr) {
  const buf = new ArrayBuffer(44 + samples.length * 2), v = new DataView(buf);
  const w = (o, s) => { for (let i = 0; i < s.length; i++) v.setUint8(o + i, s.charCodeAt(i)); };
  w(0, "RIFF"); v.setUint32(4, 36 + samples.length * 2, true); w(8, "WAVE"); w(12, "fmt ");
  v.setUint32(16, 16, true); v.setUint16(20, 1, true); v.setUint16(22, 1, true); v.setUint32(24, sr, true);
  v.setUint32(28, sr * 2, true); v.setUint16(32, 2, true); v.setUint16(34, 16, true); w(36, "data");
  v.setUint32(40, samples.length * 2, true);
  for (let i = 0; i < samples.length; i++) v.setInt16(44 + i * 2, Math.max(-1, Math.min(1, samples[i])) * 32767, true);
  return new Blob([buf], { type: "audio/wav" });
}
const CAL = [["kick", "Kick (\"b\" / \"puh\")"], ["snare", "Snare (\"pf\" / \"k\")"], ["hat", "Closed hat (\"ts\" / \"t\")"], ["open_hat", "Open hat (\"tsss\")"]];
async function refreshCalibration() {
  const c = await api("/api/calibration");
  const rows = $("#cal-rows");
  rows.innerHTML = "";
  for (const [label, name] of CAL) {
    const row = document.createElement("div");
    row.className = "calrow";
    row.innerHTML = `<b>${name}</b><span class="n">${c.counts[label] || 0} examples</span><button>Record 6 s</button>`;
    row.querySelector("button").onclick = async (e) => {
      const b = e.target; b.disabled = true; b.textContent = "Go! (6 s)";
      try {
        const { samples, sr } = await record(6);
        const res = await api("/api/calibration/" + label, { method: "POST", body: wavBlob(samples, sr) });
        b.textContent = `Added ${res.added}`;
      } catch (err) { b.textContent = "Mic error"; alert(err.message); }
      setTimeout(refreshCalibration, 1200);
    };
    rows.appendChild(row);
  }
}
$("#cal-reset").onclick = async () => { if (confirm("Forget all your beatbox examples?")) { await api("/api/calibration", { method: "DELETE" }); refreshCalibration(); } };
$("#mic-test").onclick = async () => {
  const out = $("#mic-result"), btn = $("#mic-test");
  btn.disabled = true;
  out.innerHTML = `<p><b>Type now</b> (8 s)</p><div class="meter"><div></div></div>`;
  const bar = () => out.querySelector(".meter > div");
  const lvl = (x) => { bar().style.width = Math.min(100, Math.max(0, (20 * Math.log10(x + 1e-9) + 70) * 1.6)) + "%"; };
  const dbOf = (s) => { const f = 1024, v = []; for (let i = 0; i + f <= s.length; i += f) { let e = 0; for (let j = i; j < i + f; j++) e += s[j] * s[j]; v.push(10 * Math.log10(e / f + 1e-12)); } v.sort((a, b) => a - b); return v[Math.floor(v.length * 0.9)]; };
  try {
    const typing = await record(8, lvl);
    out.innerHTML = `<p><b>Now hum</b> (8 s)</p><div class="meter"><div></div></div>`;
    const hum = await record(8, lvl);
    const diff = dbOf(hum.samples) - dbOf(typing.samples);
    const verdict = diff >= 15 ? "Great: your voice stands well clear of the keyboard." :
      diff >= 8 ? "OK, but closer would be better: bring the mic nearer your mouth and point its back at the keyboard." :
      "Too close: the keyboard is nearly as loud as your hum. Move the mic (boom arm, back toward the keyboard) and lower the gain.";
    out.innerHTML = `<p><b>${diff.toFixed(1)} dB</b> between humming and typing. ${verdict}</p>`;
  } catch (err) { out.textContent = "Couldn't use the mic: " + err.message; }
  btn.disabled = false;
};
$("#upload").onchange = async (e) => {
  const f = e.target.files[0];
  if (!f) return;
  $("#upload-result").textContent = "Scanning…";
  try {
    const r = await api("/api/upload?name=" + encodeURIComponent(f.name), { method: "POST", body: f });
    $("#upload-result").textContent = `Found ${r.segments} sound${r.segments === 1 ? "" : "s"}, kept ${r.kept}. Songs from them will show up under Songs.`;
  } catch (err) { $("#upload-result").textContent = "Couldn't read that file: " + err.message; }
};

refreshStatus();
refreshList();
setInterval(refreshStatus, 1000);
setInterval(() => { if (view !== "setup" && view !== "make") refreshList(); }, 5000);
