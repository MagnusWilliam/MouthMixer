"use strict";

const $ = (s) => document.querySelector(s);
const api = async (path, opts = {}) => {
  const r = await fetch(path, opts);
  if (!r.ok) throw new Error((await r.text()) || r.statusText);
  return r.json();
};
const post = (path, body) =>
  api(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body || {}) });

let view = "inbox";
let selected = null;
let current = null;
let listenerPaused = false;

const NAMES = ["C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"];
const noteName = (m) => NAMES[m % 12] + (Math.floor(m / 12) - 1);
const fmtTime = (t) => new Date(t * 1000).toLocaleString([], { weekday: "short", hour: "2-digit", minute: "2-digit" });
const KIND = { melody: "Melody", beat: "Beat", both: "Melody + beat" };

// ---- listener status --------------------------------------------------------------------------
async function refreshStatus() {
  try {
    const s = await api("/api/status");
    const st = s.listener.state || "not running";
    $("#dot").className = "dot " + st;
    let text = { listening: "Listening", capturing: "Capturing…", paused: "Paused", muted: "Mic muted", "no mic": "Mic not found (retrying)",
      "not running": "Listener not running" }[st] || st;
    if (s.listener.auto_pause_reason) text += ` (${s.listener.auto_pause_reason})`;
    if (st !== "not running") text += ` · kept ${s.listener.kept_today || 0}, ignored ${s.listener.dropped_today || 0} today`;
    $("#state").textContent = text;
    listenerPaused = !!s.listener.paused_by_user;
    $("#pause").textContent = listenerPaused ? "Resume" : "Pause";
    $("#pause").disabled = $("#save-last").disabled = st === "not running";
    const inbox = (s.counts.new || 0) + (s.counts.processing || 0);
    $("#count-inbox").textContent = inbox || "";
    $("#hotkey-hint").textContent = (s.hotkey || "").replace(/[<>]/g, "").replace(/\+/g, "+").replace(/\b\w/g, (c) => c.toUpperCase());
  } catch (e) {
    $("#state").textContent = "App not responding";
  }
}
$("#pause").onclick = async () => { await post("/api/listener/" + (listenerPaused ? "resume" : "pause")); setTimeout(refreshStatus, 700); };
$("#save-last").onclick = async () => { await post("/api/listener/save_last"); setTimeout(refreshList, 2500); };

// ---- list ---------------------------------------------------------------------------------------
async function refreshList() {
  if (view === "setup") return;
  const items = await api("/api/clips?view=" + view);
  const list = $("#list");
  list.innerHTML = "";
  $("#empty").classList.toggle("hidden", items.length > 0);
  for (const c of items) {
    const el = document.createElement("div");
    el.className = "item" + (c.id === selected ? " sel" : "");
    const what = c.status === "processing" ? "Working on it…" : c.status === "failed" ? "Couldn't analyse this one" :
      [KIND[c.kind], c.key, c.bpm ? Math.round(c.bpm) + " BPM" : null].filter(Boolean).join(" · ");
    el.innerHTML = `<div class="t">${fmtTime(c.created)}${c.source === "hotkey" ? " · saved by hotkey" : ""}</div>
      <div class="s">${what} · ${c.duration ? c.duration.toFixed(1) + " s" : ""}</div>`;
    el.onclick = () => select(c.id);
    list.appendChild(el);
  }
  if (!selected && items.length && items[0].status !== "processing") select(items[0].id);
}

// ---- detail -------------------------------------------------------------------------------------
async function select(id) {
  selected = id;
  document.querySelectorAll(".item").forEach((e) => e.classList.remove("sel"));
  current = await api("/api/clips/" + id);
  $("#detail").classList.remove("hidden");
  const r = current.result;
  $("#d-title").textContent = fmtTime(current.created) + (r ? " · " + KIND[r.kind] : "");
  const chips = [];
  if (r) {
    const t = r.tempo;
    chips.push(Math.round(t.bpm) + " BPM" + (Math.abs(t.drift) >= 0.02 ? ` (drifted ${t.drift > 0 ? "faster" : "slower"} ${Math.round(Math.abs(t.drift) * 100)}%, fixed)` : ""));
    if (r.key && r.notes.length) chips.push(r.key.name + (r.keys[0] ? ` (${Math.round(r.keys[0].confidence * 100)}% sure)` : ""));
    if (t.swing > 0.5) chips.push("swung " + Math.round(t.swing * 100) + "%");
    if (r.notes.length) chips.push(r.notes.length + " notes");
    if (r.drums.length) chips.push(r.drums.length + " drum hits");
    if (r.phrases.length) chips.push(r.phrases.length + " phrase" + (r.phrases.length > 1 ? "s" : ""));
    if (Math.abs(r.tuning_offset) > 0.15) chips.push(`you were ${Math.round(Math.abs(r.tuning_offset) * 100)} cents ${r.tuning_offset < 0 ? "flat" : "sharp"} overall (fixed)`);
  }
  $("#d-chips").innerHTML = chips.map((c) => `<span class="chip">${c}</span>`).join("");
  $("#a-raw").src = `/api/clips/${id}/audio/raw`;
  $("#a-preview").src = `/api/clips/${id}/audio/preview?r=${current.reading || 0}`;
  $("#m-clean").href = `/api/clips/${id}/midi/clean`;
  $("#m-raw").href = `/api/clips/${id}/midi/raw`;
  $("#d-reading").textContent = current.reading ? "Reading: " + current.reading_label : "";
  drawRoll();
  refreshList();
}

for (const [btn, status] of [["#b-keep", "kept"], ["#b-toss", "tossed"], ["#b-notmusic", "not_music"]]) {
  $(btn).onclick = async () => {
    if (!selected) return;
    await post(`/api/clips/${selected}/status`, { status });
    selected = null;
    $("#detail").classList.add("hidden");
    refreshList();
    refreshStatus();
  };
}
$("#b-reading").onclick = async () => {
  if (!selected) return;
  $("#b-reading").disabled = true;
  $("#d-reading").textContent = "Listening again…";
  try {
    await post(`/api/clips/${selected}/reading`);
    await select(selected);
  } finally {
    $("#b-reading").disabled = false;
  }
};

// ---- piano roll (read only: you steer, you don't edit) ------------------------------------------
function beatsOf(t, g) {
  const tt = t - g.phase, rate = g.bpm / 60, k = g.drift / Math.max(g.span, 1e-6);
  return rate * (tt + 0.5 * k * tt * tt) - g.downbeat;
}
function drawRoll(playBeat) {
  const r = current && current.result;
  const cv = $("#roll");
  const dpr = window.devicePixelRatio || 1;
  const hasNotes = r && (r.notes.length || r.notes_raw.length);
  const w = cv.clientWidth, h = hasNotes ? 300 : 70;
  cv.style.height = h + "px";
  cv.width = w * dpr; cv.height = h * dpr;
  const ctx = cv.getContext("2d");
  ctx.scale(dpr, dpr);
  ctx.clearRect(0, 0, w, h);
  if (!r) return;
  const css = getComputedStyle(document.documentElement);
  const col = (n) => css.getPropertyValue(n).trim();
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
    if (NAMES[p % 12].length === 2) { ctx.fillStyle = col("--grid"); ctx.fillRect(left, Y(p), w - left, rowH); }
    if (p % 12 === 0 || p === lo) { ctx.fillStyle = col("--muted"); ctx.fillText(noteName(p), 2, Y(p) + rowH - 2); }
  }
  for (let b = 0; b <= bars * 4; b++) {
    ctx.strokeStyle = b % 4 === 0 ? col("--bar") : col("--grid");
    ctx.beginPath(); ctx.moveTo(X(b), top); ctx.lineTo(X(b), h - 4); ctx.stroke();
  }
  ctx.fillStyle = col("--raw");
  for (const n of raw) ctx.fillRect(X(n.s), Y(n.p) + 1, Math.max(2, X(n.e) - X(n.s)), rowH - 2);
  for (const n of r.notes) {
    ctx.fillStyle = n.chromatic ? col("--chrom") : col("--clean");
    const x = X(n.start), wd = Math.max(3, X(n.start + n.length) - x - 1);
    ctx.beginPath(); ctx.roundRect(x, Y(n.pitch) + 1, wd, rowH - 2, 3); ctx.fill();
  }
  if (drumH) {
    const lanes = { kick: 0, snare: 1, hat: 2, open_hat: 2, clap: 1, rim: 1, tom: 0 };
    const y0 = h - drumH - 2;
    ctx.fillStyle = col("--muted");
    ["kick", "snare", "hats"].forEach((l, i) => ctx.fillText(l, 2, y0 + i * 15 + 11));
    for (const d of r.drums) {
      ctx.fillStyle = d.name === "open_hat" ? col("--chrom") : col("--clean");
      ctx.globalAlpha = 0.35 + 0.65 * d.velocity / 127;
      ctx.beginPath(); ctx.arc(X(d.start), y0 + (lanes[d.name] ?? 1) * 15 + 7, 5, 0, 7); ctx.fill();
    }
    ctx.globalAlpha = 1;
  }
  if (playBeat != null) {
    ctx.strokeStyle = col("--red"); ctx.lineWidth = 2;
    ctx.beginPath(); ctx.moveTo(X(playBeat), top); ctx.lineTo(X(playBeat), h - 4); ctx.stroke();
  }
}
$("#a-preview").ontimeupdate = () => {
  if (current && current.result) drawRoll($("#a-preview").currentTime * current.result.tempo.bpm / 60);
};
$("#a-raw").ontimeupdate = () => {
  if (current && current.result) drawRoll(beatsOf($("#a-raw").currentTime, current.result.grid));
};
window.onresize = () => drawRoll();

// ---- tabs -------------------------------------------------------------------------------------
document.querySelectorAll(".tab").forEach((t) => {
  t.onclick = () => {
    document.querySelectorAll(".tab").forEach((x) => x.classList.remove("active"));
    t.classList.add("active");
    view = t.dataset.view;
    selected = null;
    $("#detail").classList.add("hidden");
    const setup = view === "setup";
    $("#setup").classList.toggle("hidden", !setup);
    $("#list-pane").classList.toggle("hidden", setup);
    if (setup) refreshCalibration(); else refreshList();
  };
});

// ---- browser recording (calibration and mic test) -----------------------------------------------
async function record(seconds, onLevel) {
  const stream = await navigator.mediaDevices.getUserMedia({
    audio: { echoCancellation: false, noiseSuppression: false, autoGainControl: false } });
  const ctx = new AudioContext();
  const src = ctx.createMediaStreamSource(stream);
  const proc = ctx.createScriptProcessor(4096, 1, 1);
  const chunks = [];
  proc.onaudioprocess = (e) => {
    const d = e.inputBuffer.getChannelData(0);
    chunks.push(new Float32Array(d));
    if (onLevel) { let s = 0; for (const v of d) s += v * v; onLevel(Math.sqrt(s / d.length)); }
  };
  src.connect(proc); proc.connect(ctx.destination);
  await new Promise((r) => setTimeout(r, seconds * 1000));
  proc.disconnect(); src.disconnect(); stream.getTracks().forEach((t) => t.stop());
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

const CAL = [["kick", "Kick (\"b\" / \"puh\")"], ["snare", "Snare (\"pf\" / \"k\")"], ["hat", "Closed hat (\"ts\" / \"t\")"],
  ["open_hat", "Open hat (\"tsss\")"]];
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
$("#cal-reset").onclick = async () => {
  if (confirm("Forget all your beatbox examples?")) { await api("/api/calibration", { method: "DELETE" }); refreshCalibration(); }
};

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
    $("#upload-result").textContent = `Found ${r.segments} sound${r.segments === 1 ? "" : "s"}, kept ${r.kept}. They'll show up in the inbox.`;
  } catch (err) { $("#upload-result").textContent = "Couldn't read that file: " + err.message; }
};

refreshStatus();
refreshList();
setInterval(refreshStatus, 2000);
setInterval(() => { if (view !== "setup") refreshList(); }, 4000);
