"use strict";
// The studio: Mix (Incredibox-style parts), Lyrics and Sing for the song on screen.
// Uses $, api, post, esc, fmtLen, noteName, css, wavBlob and currentSong from app.js.

const errText = (e) => { try { return JSON.parse(e.message).detail || JSON.parse(e.message).error || e.message; } catch { return e.message; } };
let sub = "listen";
let shownSongId = null;

// ---- audio engine: stems on one clock -----------------------------------------------------------
const Eng = {
  ctx: null, buffers: {}, nodes: {}, master: null, playing: false, t0: 0, from: 0, onstop: null, extra: [],
  init() {
    if (!this.ctx) {
      this.ctx = new AudioContext({ sampleRate: 44100, latencyHint: "interactive" });
      this.master = this.ctx.createGain();
      this.master.connect(this.ctx.destination);
    }
    if (this.ctx.state === "suspended") this.ctx.resume();
    return this.ctx;
  },
  async load(songId, names, onProgress) {
    this.init();
    let done = 0;
    await Promise.all(names.map(async (n) => {
      if (!this.buffers[n]) {
        const r = await fetch(`/api/songs/${songId}/stems/${n}`);
        this.buffers[n] = await this.ctx.decodeAudioData(await r.arrayBuffer());
      }
      done++; if (onProgress) onProgress(done, names.length);
    }));
    // Keep memory in check: forget stems this song no longer uses.
    for (const k of Object.keys(this.buffers)) if (!names.includes(k) && !k.startsWith("keep:")) delete this.buffers[k];
  },
  // parts: [{stem, gain (linear), on}] ; returns the context time playback starts at
  play(parts, from = 0, when = null) {
    this.stop(true);
    const ctx = this.init();
    const at = when ?? ctx.currentTime + 0.08;
    this.nodes = {};
    for (const p of parts) {
      const buf = this.buffers[p.stem];
      if (!buf) continue;
      const src = ctx.createBufferSource();
      src.buffer = buf;
      const g = ctx.createGain();
      g.gain.value = p.on ? p.gain : 0;
      src.connect(g).connect(this.master);
      const off = Math.max(0, from);
      if (off < buf.duration) src.start(at + Math.max(0, -from), off);
      this.nodes[p.id] = { src, g };
    }
    this.playing = true; this.t0 = at; this.from = from;
    const first = Object.values(this.nodes)[0];
    if (first) first.src.onended = () => { if (this.playing && this.pos() > 1) this.stop(); };
    return at;
  },
  setGain(id, gain, on) {
    const n = this.nodes[id];
    if (n) n.g.gain.setTargetAtTime(on ? gain : 0, this.ctx.currentTime, 0.015);
  },
  pos() { return this.playing ? this.from + (this.ctx.currentTime - this.t0) : this.from; },
  stop(quiet) {
    for (const n of Object.values(this.nodes)) { try { n.src.onended = null; n.src.stop(); } catch { } }
    for (const x of this.extra) { try { x.stop(); } catch { } }
    this.nodes = {}; this.extra = [];
    const was = this.playing;
    this.playing = false;
    if (was && !quiet && this.onstop) this.onstop();
  },
  click(at, accent) {  // a soft woodblock-ish tick
    const ctx = this.ctx, o = ctx.createOscillator(), g = ctx.createGain();
    o.frequency.value = accent ? 1600 : 1100;
    g.gain.setValueAtTime(0.0001, at); g.gain.exponentialRampToValueAtTime(accent ? 0.5 : 0.3, at + 0.002);
    g.gain.exponentialRampToValueAtTime(0.0001, at + 0.05);
    o.connect(g).connect(this.master); o.start(at); o.stop(at + 0.06);
    this.extra.push(o);
  },
};
const dbToGain = (db) => Math.pow(10, db / 20);

// ---- sub-tabs -----------------------------------------------------------------------------------
document.querySelectorAll(".sub").forEach((b) => b.onclick = () => showSub(b.dataset.sub));
function showSub(name) {
  sub = name;
  document.querySelectorAll(".sub").forEach((b) => b.classList.toggle("on", b.dataset.sub === name));
  for (const n of ["listen", "mix", "lyrics", "sing"]) $("#sub-" + n).classList.toggle("hidden", n !== name);
  if (name !== "listen") $("#s-audio").pause();
  if (name !== "mix" && name !== "sing") Eng.stop(true);
  if (!currentSong) return;
  if (name === "mix") Mix.open();
  if (name === "lyrics") Lyr.open();
  if (name === "sing") Sing.open();
}
window.onSongShown = (s) => {
  if (s.id !== shownSongId) { shownSongId = s.id; Mix.state = null; Sing.takes = null; Eng.stop(true); }
  if (sub !== "listen") showSub(sub);
};
const songUrl = (p) => `/api/songs/${currentSong.id}${p}`;
const curV = () => currentSong.version || 0;
async function reloadSong(version) {
  if (version != null) await post(songUrl("/version"), { version });
  currentSong = await api("/api/songs/" + currentSong.id);
  renderSong();
}
function busy(el, text) {
  el.innerHTML = text ? `<span class="spin"></span> ${esc(text)}` : "";
}

// ---- Mix ----------------------------------------------------------------------------------------
const ROLE_ICON = { lead: "★", vocal: "🎤", drums: "🥁", perc: "🪘", bass: "〰", comp: "🎹", pad: "☁", arp: "✦", riff: "⚡",
  counter: "♪", timpani: "◉", fx: "🌧" };
const ROLE_NAME = { lead: "melody", vocal: "vocals", drums: "beat", perc: "percussion", bass: "bass", comp: "chords", pad: "pad",
  arp: "arpeggio", riff: "riff / hook", counter: "counter-melody", timpani: "timpani", fx: "ambience" };
const prettySound = (k) => k.replace(/^kit:/, "").replace(/^fx:/, "").replace(/_/g, " ") + (k.startsWith("kit:") ? " kit" : "");
const Mix = {
  state: null, solo: null, dirty: false, vibe: null, cat: null, sugs: null,
  async open() {
    const st = $("#mx-status");
    if (!this.state || this.state.version !== curV()) {
      busy(st, "Getting the parts ready (the first time takes a little while)…");
      try { this.state = await api(songUrl(`/mixer?v=${curV()}`)); } catch (e) { busy(st, ""); $("#mx-msg").textContent = errText(e); return; }
      this.dirty = false;
    }
    await this.loadStems();
    this.render();
    this.suggest();
  },
  async loadStems() {
    const st = $("#mx-status");
    await Eng.load(currentSong.id, this.state.parts.map((p) => p.stem), (d, n) => busy(st, `Loading parts ${d}/${n}…`));
    busy(st, "");
  },
  engineParts() {
    return this.state.parts.map((p) => ({ id: p.id, stem: p.stem, gain: dbToGain(p.gain_db || 0),
      on: this.solo ? p.id === this.solo : !p.muted }));
  },
  render() {
    const box = $("#mx-parts");
    box.innerHTML = "";
    const order = ["vocal", "lead", "riff", "counter", "arp", "comp", "pad", "bass", "drums", "perc", "timpani", "fx"];
    const parts = this.state.parts.slice().sort((a, b) => order.indexOf(a.role) - order.indexOf(b.role));
    for (const p of parts) {
      const el = document.createElement("div");
      el.className = "tile r-" + p.role + (p.muted ? " off" : "") + (this.solo === p.id ? " solo" : "");
      const choices = p.choices && p.choices.length > 1 ? `<select title="Swap the sound">${p.choices.map((c) =>
        `<option value="${esc(c)}"${c === p.instrument ? " selected" : ""}>${esc(prettySound(c))}</option>`).join("")}</select>`
        : `<span class="small muted">${esc(prettySound(p.instrument))}</span>`;
      el.innerHTML = `
        <button class="power" title="${p.muted ? "Turn on" : "Turn off"}">${ROLE_ICON[p.role] || "♪"}</button>
        <div class="tname">${esc(p.label || p.name)}${p.mine ? ' <span class="yours">yours</span>' : ""}</div>
        <div class="trole small muted">${esc(ROLE_NAME[p.role] || p.role)}</div>
        ${choices}
        <div class="tctl"><input type="range" min="-18" max="6" step="1" value="${p.gain_db || 0}" title="Volume">
          <button class="ghost s" title="Hear only this part">S</button>
          ${p.mine ? "" : '<button class="ghost x" title="Remove this part">✕</button>'}</div>`;
      el.querySelector(".power").onclick = () => this.toggle(p);
      const sel = el.querySelector("select");
      if (sel) sel.onchange = () => this.swap(p, sel.value, el);
      const vol = el.querySelector("input[type=range]");
      vol.oninput = () => { p.gain_db = +vol.value; Eng.setGain(p.id, dbToGain(p.gain_db), this.solo ? this.solo === p.id : !p.muted); };
      vol.onchange = () => { this.dirty = true; this.persist(p, { gain_db: p.gain_db }); };
      el.querySelector(".s").onclick = () => { this.solo = this.solo === p.id ? null : p.id; this.applyGains(); this.render(); };
      const x = el.querySelector(".x");
      if (x) x.onclick = () => this.remove(p);
      box.appendChild(el);
    }
    const hasVocal = this.state.parts.some((p) => p.role === "vocal");
    $("#mx-leadmode").classList.toggle("hidden", !hasVocal);
    $("#mx-hits").classList.toggle("hidden", !hasVocal);
    $("#mx-lead").value = this.state.lead_mode || "duck";
    $("#mx-save").disabled = !this.dirty;
  },
  applyGains() { for (const p of this.state.parts) Eng.setGain(p.id, dbToGain(p.gain_db || 0), this.solo ? p.id === this.solo : !p.muted); },
  toggle(p) {
    p.muted = !p.muted; this.dirty = true;
    this.applyGains(); this.render();
    this.persist(p, { muted: p.muted });
    this.suggest();
  },
  async persist(p, change) {
    try { await post(songUrl("/mixer/part"), { v: curV(), id: p.id, ...change }); } catch (e) { $("#mx-msg").textContent = errText(e); }
  },
  async swap(p, inst, el) {
    el.classList.add("busy");
    busy($("#mx-status"), `Changing the ${ROLE_NAME[p.role] || p.role} to ${prettySound(inst)}…`);
    try {
      this.state = await post(songUrl("/mixer/part"), { v: curV(), id: p.id, instrument: inst });
      this.dirty = true;
      await this.loadStems();
      this.restartIfPlaying();
      this.render();
      $("#mx-msg").textContent = "";
    } catch (e) { busy($("#mx-status"), ""); $("#mx-msg").textContent = errText(e); }
    el.classList.remove("busy");
  },
  async add(kind, inst) {
    busy($("#mx-status"), "Writing the new part to fit your song…");
    try {
      this.state = await post(songUrl("/mixer/add"), { v: curV(), kind, instrument: inst });
      this.dirty = true;
      await this.loadStems();
      this.restartIfPlaying();
      this.render(); this.suggest();
      const added = this.state.parts.find((p) => p.id === this.state.added);
      $("#mx-msg").textContent = added ? `Added: ${added.label || added.name}. Turn it off or remove it if it doesn't fit.` : "";
    } catch (e) { busy($("#mx-status"), ""); $("#mx-msg").textContent = errText(e); }
  },
  async remove(p) {
    try {
      this.state = await post(songUrl("/mixer/remove"), { v: curV(), id: p.id });
      this.dirty = true; Eng.setGain(p.id, 0, false);
      this.render(); this.suggest();
    } catch (e) { $("#mx-msg").textContent = errText(e); }
  },
  restartIfPlaying() { if (Eng.playing) { const at = Eng.pos(); Eng.play(this.engineParts(), at); } },
  async suggest() {
    let r;
    try { r = await api(songUrl(`/mixer/suggest?v=${curV()}${this.vibe ? "&vibe=" + this.vibe : ""}`)); } catch { return; }
    this.sugs = r;
    const vb = $("#mx-vibes");
    vb.innerHTML = "";
    const mk = (label, on, fn, extra = "") => { const b = document.createElement("button"); b.className = "chip" + (on ? " on" : "") + extra; b.textContent = label; b.onclick = fn; return b; };
    vb.appendChild(mk("Suits this style", !this.vibe, () => { this.vibe = null; this.suggest(); }));
    for (const v of r.vibes) vb.appendChild(mk(v.label, this.vibe === v.id, () => { this.vibe = v.id; this.suggest(); },
      r.pack_vibes.includes(v.id) ? " fits" : ""));
    const cb = $("#mx-cats");
    cb.innerHTML = "";
    cb.appendChild(mk("Top picks", !this.cat, () => { this.cat = null; this.renderSugs(); }));
    for (const c of r.categories) cb.appendChild(mk(c, this.cat === c, () => { this.cat = c; this.renderSugs(); }));
    this.renderSugs();
  },
  renderSugs() {
    const r = this.sugs, box = $("#mx-sugs");
    [...$("#mx-cats").children].forEach((b, i) => b.classList.toggle("on", i === 0 ? !this.cat : b.textContent === this.cat));
    const list = this.cat ? r.suggestions.filter((s) => s.cat === this.cat) : r.suggestions.slice(0, 8);
    box.innerHTML = list.length ? "" : `<p class="muted small">Nothing left to add here.</p>`;
    for (const s of list) {
      const el = document.createElement("div");
      el.className = "sug";
      const stars = s.score >= 4 ? "great match" : s.score >= 2.5 ? "good match" : s.score >= 1 ? "worth a try" : "a different colour";
      el.innerHTML = `<div><b>${esc(s.label)}</b> <span class="tag">${stars}</span><div class="small muted">${esc(s.why)}</div></div>
        <select>${s.sounds.map((c) => `<option value="${esc(c)}">${esc(prettySound(c))}</option>`).join("")}</select>
        <button>Add</button>`;
      el.querySelector("button").onclick = () => this.add(s.id, el.querySelector("select").value);
      box.appendChild(el);
    }
  },
};
$("#mx-play").onclick = () => {
  if (!Mix.state) return;
  if (Eng.playing) { Eng.stop(); return; }
  Eng.onstop = () => { $("#mx-play").textContent = "▶ Play"; };
  Eng.play(Mix.engineParts(), Eng.from >= Mix.state.seconds - 1 ? 0 : Eng.from);
  $("#mx-play").textContent = "■ Stop";
};
$("#mx-seek").parentElement.onclick = (e) => {
  if (!Mix.state) return;
  const r = e.currentTarget.getBoundingClientRect(), t = (e.clientX - r.left) / r.width * Mix.state.seconds;
  if (Eng.playing) Eng.play(Mix.engineParts(), t); else Eng.from = t;
};
$("#mx-lead").onchange = async () => {
  const vp = Mix.state.parts.find((p) => p.role === "vocal");
  if (vp) { Mix.dirty = true; Mix.state.lead_mode = $("#mx-lead").value; await post(songUrl("/mixer/part"), { v: curV(), id: vp.id, lead_mode: Mix.state.lead_mode }); Mix.render(); }
};
$("#mx-save").onclick = async () => {
  const st = $("#mx-msg");
  Eng.stop(true); $("#mx-play").textContent = "▶ Play";
  busy($("#mx-status"), "Mixing and checking your version…");
  $("#mx-save").disabled = true;
  try {
    const r = await post(songUrl("/mixer/save"), { v: curV(), lead_mode: Mix.state.lead_mode });
    Mix.state = null; Mix.dirty = false;
    busy($("#mx-status"), "");
    await reloadSong(r.version);
    st.innerHTML = r.critic.ok ? `Saved as version ${r.version + 1}. ` + `<a href="#" id="mx-tolisten">Listen to it</a>`
      : `Saved as version ${r.version + 1}, but the checks found: ${esc(r.critic.rejects.join("; "))}.`;
    const a = $("#mx-tolisten"); if (a) a.onclick = (e) => { e.preventDefault(); showSub("listen"); };
  } catch (e) { busy($("#mx-status"), ""); st.textContent = errText(e); $("#mx-save").disabled = false; }
};
setInterval(() => {
  if (sub !== "mix" || !Mix.state) return;
  const p = Eng.pos(), T = Mix.state.seconds;
  $("#mx-pos").textContent = fmtLen(Math.min(p, T)) + " / " + fmtLen(T);
  $("#mx-seek").style.width = Math.min(100, p / T * 100) + "%";
}, 150);

// ---- Lyrics -------------------------------------------------------------------------------------
const IDEAS = ["a heist at midnight", "friends on the last day of summer", "a rooftop chase in the rain", "the calm before a big battle",
  "a train ride home through the city", "finding courage", "a secret only we know"];
const Lyr = {
  data: null, settings: null,
  async open() {
    this.data = await api(songUrl(`/lyrics?v=${curV()}`));
    this.settings = await api("/api/settings");
    const keyNote = $("#ly-keynote");
    $("#ly-write").disabled = !this.settings.has_claude_key;
    keyNote.innerHTML = this.settings.has_claude_key ? "Takes about 20-40 seconds." :
      `Add your Claude API key in <a href="#" id="ly-tosetup">Setup</a> first, or type your own words below.`;
    const ts = $("#ly-tosetup"); if (ts) ts.onclick = (e) => { e.preventDefault(); document.querySelector('[data-view="setup"]').click(); };
    $("#ly-brief").value = this.data.brief || "";
    $("#ly-ideas").innerHTML = "";
    for (const idea of IDEAS) {
      const b = document.createElement("button"); b.className = "chip"; b.textContent = idea;
      b.onclick = () => { $("#ly-brief").value = idea; }; $("#ly-ideas").appendChild(b);
    }
    this.renderMap(); this.renderOptions(); this.renderOwn();
  },
  renderMap() {
    const m = this.data.map;
    $("#ly-map").innerHTML = m.length ? "<b>Your melody:</b> " + m.map((s) =>
      `${esc(s.role)}: ${s.lines.length} line${s.lines.length > 1 ? "s" : ""} (${s.lines.map((l) => l.count).join(", ")} syllables)`).join(" · ")
      : "This song has no melody to write words for.";
  },
  renderOptions() {
    const box = $("#ly-options");
    box.innerHTML = "";
    this.data.options.forEach((o, i) => {
      const el = document.createElement("div");
      el.className = "lyopt" + (i === this.data.chosen ? " on" : "");
      const secs = o.sections.map((s, si) => {
        const m = this.data.map[si];
        const lines = s.lines.map((l, li) => {
          const want = m && m.lines[li] ? m.lines[li].count : null;
          return `<div class="lyline">${esc(l.text || l)}${want ? ` <span class="cnt">${want} notes</span>` : ""}</div>`;
        }).join("");
        return `<div class="lysec"><div class="small muted">${esc(m ? m.role : s.name)}</div>${lines}</div>`;
      }).join("");
      const ch = o.check || { score: null, issues: [] };
      const fit = ch.score == null ? "your words" : ch.score >= 0.9 ? "fits the melody well" : ch.score >= 0.7 ? "mostly fits" : "needs work";
      el.innerHTML = `<div class="row"><b>${esc(o.title)}</b><span class="tag">${fit}</span><span class="small muted">${esc(o.idea || "")}</span>
          <span class="spacer"></span><button class="${i === this.data.chosen ? "" : "primary"}">${i === this.data.chosen ? "In use" : "Use these words"}</button></div>
        ${secs}${ch.issues.length ? `<ul class="checks small">${ch.issues.map((x) => `<li class="warn">${esc(x)}</li>`).join("")}</ul>` : ""}`;
      el.querySelector("button").onclick = async () => { this.data = await post(songUrl("/lyrics/choose"), { v: curV(), index: i }); this.renderOptions(); };
      box.appendChild(el);
    });
  },
  renderOwn() {
    const box = $("#ly-own");
    box.innerHTML = "";
    const own = this.data.options.find((o) => o.idea === "your own words");
    if (own) $("#ly-title").value = own.title;
    this.data.map.forEach((s, si) => {
      const d = document.createElement("div");
      d.innerHTML = `<label class="small">${esc(s.role)} <span class="muted">(${s.lines.map((l) => l.count).join(", ")})</span></label>
        <textarea rows="${Math.max(2, s.lines.length)}" data-sec="${esc(s.section)}"></textarea>`;
      if (own && own.sections[si]) d.querySelector("textarea").value = own.sections[si].lines.map((l) => l.text || l).join("\n");
      box.appendChild(d);
    });
  },
};
$("#ly-write").onclick = async () => {
  const btn = $("#ly-write"), note = $("#ly-keynote");
  btn.disabled = true; busy(note, "Claude is writing and checking three options…");
  try {
    Lyr.data = await post(songUrl("/lyrics/write"), { v: curV(), brief: $("#ly-brief").value });
    note.textContent = "Pick the one you like; you can sing any of them.";
    Lyr.renderOptions();
  } catch (e) { note.textContent = errText(e); }
  btn.disabled = false;
};
$("#ly-own-check").onclick = async () => {
  const sections = {};
  document.querySelectorAll("#ly-own textarea").forEach((t) => { sections[t.dataset.sec] = t.value; });
  Lyr.data = await post(songUrl("/lyrics/own"), { v: curV(), title: $("#ly-title").value, sections });
  Lyr.renderOptions();
};

// ---- Setup: Claude key --------------------------------------------------------------------------
window.refreshKey = async () => {
  const s = await api("/api/settings");
  $("#bg-listen").checked = !!s.background_listening;
  $("#key-now").textContent = s.has_claude_key ? (s.claude_key_from_env ? "Using the key from ANTHROPIC_API_KEY." : "A key is saved.") : "No key yet.";
};
$("#key-save").onclick = async () => { await post("/api/settings", { claude_api_key: $("#key-input").value }); $("#key-input").value = ""; refreshKey(); };
$("#key-clear").onclick = async () => { await post("/api/settings", { claude_api_key: "" }); refreshKey(); };

// ---- Sing ---------------------------------------------------------------------------------------
// Live pitch: YIN-style difference function on the latest 2048 samples.
function detectPitch(buf, sr) {
  const n = 1024, W = buf.length - n;
  if (W < 200) return 0;
  let rms = 0; for (let i = 0; i < buf.length; i++) rms += buf[i] * buf[i];
  if (Math.sqrt(rms / buf.length) < 0.01) return 0;
  const minLag = Math.floor(sr / 1000), maxLag = Math.min(W, Math.floor(sr / 75));
  const d = new Float32Array(maxLag + 1);
  for (let lag = minLag; lag <= maxLag; lag++) { let s = 0; for (let i = 0; i < n; i++) { const x = buf[i] - buf[i + lag]; s += x * x; } d[lag] = s; }
  let run = 0, best = -1;
  const cm = new Float32Array(maxLag + 1);
  for (let lag = minLag; lag <= maxLag; lag++) { run += d[lag]; cm[lag] = d[lag] * (lag - minLag + 1) / (run || 1); }
  for (let lag = minLag + 1; lag < maxLag; lag++) if (cm[lag] < 0.15 && cm[lag] <= cm[lag - 1] && cm[lag] <= cm[lag + 1]) { best = lag; break; }
  if (best < 0) return 0;
  const a = cm[best - 1], b = cm[best], c = cm[best + 1], shift = (a - c) / (2 * (a - 2 * b + c) || 1);
  return sr / (best + shift);
}
const hzToMidi = (f) => 69 + 12 * Math.log2(f / 440);

const TRACK_HUES = { Lead: 210, "Verse lead": 190, "Chorus lead": 330, Rap: 30, Gang: 0, Backing: 270, Harmony: 290,
  "Ad-libs": 50, Announcer: 160, Whisper: 240 };

const Sing = {
  takes: null, sections: [], section: null, events: [], notes: [], trail: [], mic: null, stream: null, proc: null,
  recording: null, latency: 0, mode: null, deviceId: localStorage.getItem("mm-sing-mic") || "",
  async open() {
    const st = $("#sg-status");
    if (!Mix.state || Mix.state.version !== curV()) {
      busy(st, "Getting the parts ready…");
      try { Mix.state = await api(songUrl(`/mixer?v=${curV()}`)); } catch (e) { busy(st, ""); $("#sg-result").textContent = errText(e); return; }
    }
    await Eng.load(currentSong.id, Mix.state.parts.map((p) => p.stem), (d, n) => busy(st, `Loading the song ${d}/${n}…`));
    busy(st, "");
    const v = currentSong.record.versions[curV()];
    this.bpm = v.bpm;
    this.sheet = v.lyric_sheet || [];
    const worded = new Set(this.sheet.map((x) => x.section));
    this.sections = v.sections.filter((s) => worded.has(s.name) || (!worded.size && !/^(intro|outro|ending)/i.test(s.name)));
    this.key = v.key;
    if (!this.sections.length) { st.textContent = "This song has no sections to sing."; return; }
    const NAMES_ = new Proxy({ A: "Verse 1", "A'": "Verse 2", B: "Bridge", "A''": "Final chorus" }, { get: (o, k) => o[k] || k });
    const box = $("#sg-sections");
    box.innerHTML = "";
    // the fresh section (its start and length may have changed in a rebuild, or this is another song)
    this.section = this.sections.find((s) => this.section && s.name === this.section.name) || this.sections[0];
    for (const s of [...this.sections, { name: "all", start: this.sections[0].start, bars: this.sections.at(-1).start + this.sections.at(-1).bars - this.sections[0].start }]) {
      const b = document.createElement("button");
      b.className = "chip" + (this.section && this.section.name === s.name ? " on" : "");
      b.dataset.name = s.name;
      const who = this.singersOf(s.name);
      b.innerHTML = esc(s.name === "all" ? "Whole song" : NAMES_[s.name] || s.name) +
        (who.length ? ` <span class="who">${who.map((w) => `<span class="dot" style="--h:${this.trackColor(w)}" title="${esc(w)}"></span>`).join("")}</span>` : "");
      if (who.length) b.title = "Sung by: " + who.join(", ");
      b.onclick = () => {
        this.section = s; [...box.children].forEach((c) => c.classList.toggle("on", c === b));
        // a section's singer: switch to that track unless you're already on one of its singers
        if (who.length && !who.includes(this.track)) this.setTrack(who[0]); else this.renderWorking();
        this.draw();
      };
      box.appendChild(b);
    }
    this.notes = v.tracks.filter((t) => t.role === "lead").flatMap((t) => t.notes).sort((a, b) => a[0] - b[0]);
    const ly = await api(songUrl(`/lyrics?v=${curV()}`));
    this.events = ly.events || [];
    const opts = await api("/api/vocal_options");
    const presets = opts.presets;
    const fill = (sel, items, keep) => { const cur = $(sel).value; $(sel).innerHTML = items; if (keep && cur) $(sel).value = cur; };
    fill("#sg-track", opts.tracks.map((t) => `<option>${esc(t)}</option>`).join(""), true);
    fill("#sg-mk-track", opts.tracks.map((t) => `<option>${esc(t)}</option>`).join(""), true);
    fill("#sg-character", opts.characters.map((c) => `<option value="${c.id}">${esc(c.label)}</option>`).join(""), true);
    this.tweakSpec = opts.tweaks || [];
    this.trackNames = opts.tracks;
    this.characters = opts.characters;
    const t = await api(songUrl("/takes"));
    this.takes = t.takes;
    this.latency = t.latency_ms || 0;
    this.measured = !!t.latency_measured;
    $("#sg-lat").textContent = this.measured ? Math.round(this.latency) + " ms" : `about ${latencyEstimateMs()} ms (a guess: press Sync test)`;
    $("#sg-latr").value = Math.round(this.latency);
    $("#sg-preset").innerHTML = presets.map((p) => `<option value="${p.id}"${p.id === t.preset ? " selected" : ""}>${esc(p.label)}${p.id === t.preset ? " (suits this style)" : ""}</option>`).join("");
    await this.listMics();
    let want = this.track;
    try { want = want || localStorage.getItem("mm-track:" + currentSong.id); } catch { }
    if (!want || !this.trackNames.includes(want)) {  // the track with the newest take, else Lead
      const last = this.takes.slice().reverse().find((x) => this.trackNames.includes(x.track || "Lead"));
      want = last ? last.track || "Lead" : "Lead";
    }
    this.setTrack(want);
    this.draw();
  },

  // ---- the vocal track you're working on --------------------------------------------------------
  setTrack(name) {
    this.track = name;
    try { localStorage.setItem("mm-track:" + currentSong.id, name); } catch { }
    $("#sg-track").value = name; $("#sg-mk-track").value = name;
    let voice = null;
    try { voice = localStorage.getItem("mm-voice:" + currentSong.id + ":" + name); } catch { }
    const made = this.madeReport(name);
    $("#sg-character").value = voice || (made && made.character) || "natural";
    // jump to a section this track has takes for, if the one showing has none
    const mine = (this.takes || []).filter((t) => (t.track || "Lead") === name);
    if (mine.length && this.section && !mine.some((t) => t.section === this.section.name)) {
      const sec = (this.sections || []).find((x) => x.name === mine[mine.length - 1].section);
      if (sec) {
        this.section = sec;
        [...$("#sg-sections").children].forEach((c) => c.classList.toggle("on", c.dataset.name === sec.name));
        this.draw();
      }
    }
    this.renderTracks(); this.renderTakes(); this.renderTweaks(); this.renderWorking();
  },
  trackColor(name) { return TRACK_HUES[name] ?? 200; },
  // who sings a section, from the lyric headers ("[Chorus, Chorus lead + Gang]")
  singersOf(section) { const x = (this.sheet || []).find((l) => l.section === section); return (x && x.singers) || []; },
  pills(names) { return (names || []).map((w) => `<span class="pill sing" style="--h:${this.trackColor(w)}">${esc(w)}</span>`).join(" "); },
  madeReport(name) {
    const v = currentSong && currentSong.record.versions[curV()];
    return v && v.vocal_tracks ? v.vocal_tracks[name] : null;
  },
  vocalPart(name) {
    return Mix.state ? Mix.state.parts.find((p) => p.role === "vocal" && (p.track || "Lead") === name) : null;
  },
  renderWorking() {
    const name = this.track, voice = (this.characters || []).find((c) => c.id === $("#sg-character").value);
    const html = `<span class="dot" style="--h:${this.trackColor(name)}"></span> Working on <b>${esc(name)}</b>
      <span class="muted">· voice: ${esc(voice ? voice.label : "your voice")}</span>`;
    const who = this.section ? this.singersOf(this.section.name) : [];
    const fit = !who.length ? "" : who.includes(name) ? ` <span class="muted">· ${esc(this.section.name)} is sung by ${esc(who.join(" + "))}</span>`
      : ` <span class="warnc">· ${esc(this.section.name)} is sung by ${esc(who.join(" + "))}, not ${esc(name)}</span>`;
    $("#sg-working").innerHTML = html + fit + `<span class="muted"> · new takes go to this track</span>`;
    $("#sg-working").style.setProperty("--h", this.trackColor(name));
    $("#sg-mk-name").innerHTML = `<span class="dot" style="--h:${this.trackColor(name)}"></span> ${esc(name)}`;
    $("#sg-takes-for").textContent = $("#sg-alltakes").checked ? "(every track)" : `for ${name}`;
  },
  renderTracks() {
    const box = $("#sg-tracks");
    box.innerHTML = "";
    for (const name of this.trackNames || []) {
      const mine = (this.takes || []).filter((t) => (t.track || "Lead") === name);
      const secs = [...new Set(mine.map((t) => t.section).filter(Boolean))];
      const part = this.vocalPart(name), made = this.madeReport(name);
      const status = part ? (part.muted ? ["muted", "Muted (not in the song)"] : ["in", "In the song"])
        : mine.length ? ["todo", "Not made yet"] : ["empty", "No takes yet"];
      const el = document.createElement("div");
      el.className = "vtrack" + (name === this.track ? " on" : "") + (mine.length || part ? "" : " empty");
      el.style.setProperty("--h", this.trackColor(name));
      el.innerHTML = `<div class="vt-name">${name === this.track ? "● " : ""}${esc(name)}</div>
        <div class="pill ${status[0]}">${status[1]}</div>
        <div class="small muted">${mine.length} take${mine.length === 1 ? "" : "s"}${secs.length ? " · " + esc(secs.join(", ")) : ""}</div>
        ${(() => { const sings = (this.sheet || []).filter((x) => (x.singers || []).includes(name) || (x.line_singers || []).some((l) => (l || []).includes(name))).map((x) => x.section);
          return sings.length ? `<div class="small">sings: ${esc(sings.join(", "))}</div>` : ""; })()}
        ${made ? `<div class="small muted">voice: ${esc(made.character_label || made.character || "your voice")}</div>` : ""}
        ${part ? `<button class="ghost small" data-mute>${part.muted ? "Put back in the song" : "Take out of the song"}</button>` : ""}`;
      el.onclick = (e) => { if (!e.target.closest("button")) this.setTrack(name); };
      const mb = el.querySelector("[data-mute]");
      if (mb) mb.onclick = () => this.toggleInSong(name, mb);
      box.appendChild(el);
    }
  },
  async toggleInSong(name, btn) {
    const part = this.vocalPart(name);
    if (!part) return;
    btn.disabled = true;
    busy($("#sg-status"), `${part.muted ? "Putting" : "Taking"} ${name} ${part.muted ? "back in" : "out of"} the song and saving it…`);
    try {
      await post(songUrl("/mixer/part"), { v: curV(), id: part.id, muted: !part.muted });
      const r = await post(songUrl("/mixer/save"), { v: curV(), working: true });
      Mix.state = null;
      await reloadSong(r.version);
      busy($("#sg-status"), "");
      await this.open();
    } catch (e) { busy($("#sg-status"), ""); $("#sg-result").textContent = errText(e); btn.disabled = false; }
  },
  // Which take goes into the track for each section: your pick, else the newest.
  choiceKey() { return "mm-choice:" + currentSong.id + ":" + this.track; },
  getChoice() { try { return JSON.parse(localStorage.getItem(this.choiceKey()) || "{}"); } catch { return {}; } },
  setChoice(c) { try { localStorage.setItem(this.choiceKey(), JSON.stringify(c)); } catch { } },
  stacks() { return ["Gang", "Backing", "Harmony"].includes(this.track); },
  takeInUse(section) {
    const mine = (this.takes || []).filter((t) => (t.track || "Lead") === this.track && t.section === section);
    const pick = this.getChoice()[section];
    return mine.find((t) => t.id === pick) || mine[mine.length - 1] || null;
  },
  // Voice tweaks: only the settings you touch are sent; they're remembered per vocal track.
  tweakKey() { return "mm-tweaks:" + (this.track || "Lead"); },
  getTweaks() { try { return JSON.parse(localStorage.getItem(this.tweakKey()) || "{}"); } catch { return {}; } },
  setTweaks(t) { try { localStorage.setItem(this.tweakKey(), JSON.stringify(t)); } catch { } },
  renderTweaks() {
    const box = $("#sg-tweaks"); if (!box) return;
    const t = this.getTweaks();
    box.innerHTML = "";
    const raw = t.process === "raw";
    let group = null;
    for (const sp of this.tweakSpec || []) {
      if ((sp.group || "voice") !== group) {
        group = sp.group || "voice";
        const h = document.createElement("h4");
        h.className = "tw-head";
        h.textContent = group === "steps" ? "Processing steps (switch any of them off)" : "Voice and effects";
        box.appendChild(h);
      }
      const el = document.createElement("label");
      const na = raw && sp.id !== "process" && sp.id !== "timing";
      el.className = "tweak" + (sp.id in t ? " set" : "") + (na ? " na" : "");
      if (na) el.title = "Not used with the raw voice";
      if (sp.options) {
        el.innerHTML = `<span>${esc(sp.label)}</span><select>${sp.options.map(([v, l]) =>
          `<option value="${esc(v)}"${(t[sp.id] ?? "") === v ? " selected" : ""}>${esc(l)}</option>`).join("")}</select>`;
        el.querySelector("select").onchange = (e) => {
          const cur = this.getTweaks();
          if (e.target.value) cur[sp.id] = e.target.value; else delete cur[sp.id];
          this.setTweaks(cur); el.classList.toggle("set", sp.id in cur);
          if (sp.id === "process") this.renderTweaks();
        };
      } else {
        const v = t[sp.id] ?? sp.default;
        el.innerHTML = `<span>${esc(sp.label)} <b class="mono">${sp.id in t ? (v > 0 && sp.min < 0 ? "+" : "") + v : "–"}</b></span>
          <input type="range" min="${sp.min}" max="${sp.max}" step="${sp.step}" value="${v}" title="${esc(sp.hint || "")}">`;
        const r = el.querySelector("input"), b = el.querySelector("b");
        r.oninput = () => { b.textContent = (r.value > 0 && sp.min < 0 ? "+" : "") + r.value; };
        r.onchange = () => { const cur = this.getTweaks(); cur[sp.id] = +r.value; this.setTweaks(cur); el.classList.add("set"); };
      }
      box.appendChild(el);
    }
  },
  async listMics() {
    try {
      const devs = (await navigator.mediaDevices.enumerateDevices()).filter((d) => d.kind === "audioinput");
      const sel = $("#sg-mic");
      sel.innerHTML = devs.map((d, i) => `<option value="${esc(d.deviceId)}">${esc(d.label || "Microphone " + (i + 1))}</option>`).join("");
      const quad = devs.find((d) => /quadcast/i.test(d.label));
      sel.value = this.deviceId && devs.some((d) => d.deviceId === this.deviceId) ? this.deviceId : quad ? quad.deviceId : sel.value;
      this.deviceId = sel.value;
    } catch { }
  },
  range() {  // song seconds of the chosen section, plus one bar of count-in
    const spb = 60 / this.bpm, s = this.section;
    const a = s.start * 4 * spb, b = (s.start + s.bars) * 4 * spb;
    const takesBefore = (this.takes || []).length;
    const countBars = takesBefore === 0 ? 2 : 1;  // two bars of count-in on the first take
    return { a, b, from: a - countBars * 4 * spb, countBars };
  },
  engineParts() {
    const music = $("#sg-music").value / 100, guide = $("#sg-guide").value / 100;
    return Mix.state.parts.filter((p) => p.role !== "vocal").map((p) => ({ id: p.id, stem: p.stem,
      gain: dbToGain(p.gain_db || 0) * (p.role === "lead" ? guide * 0.6 : music), on: !p.muted }));
  },
  async openMic() {
    Eng.init();
    if (this.stream) return;
    this.stream = await navigator.mediaDevices.getUserMedia({ audio: { deviceId: this.deviceId ? { exact: this.deviceId } : undefined,
      echoCancellation: false, noiseSuppression: false, autoGainControl: false, channelCount: 1 } });
    await this.listMics();
    const ctx = Eng.ctx;
    const src = ctx.createMediaStreamSource(this.stream);
    const sink = ctx.createGain(); sink.gain.value = 0;
    this.hist = new Float32Array(4096);
    this.lastMeter = 0;
    try {
      // On the audio thread: nothing the page does can drop mic audio (the old way lost blocks when busy).
      if (!this.workletReady) { await ctx.audioWorklet.addModule("/static/capture-worklet.js"); this.workletReady = true; }
      const node = new AudioWorkletNode(ctx, "mm-capture", { numberOfInputs: 1, numberOfOutputs: 1, channelCount: 1,
        channelCountMode: "explicit" });
      node.port.onmessage = (e) => this.onBlock(e.data.t, e.data.d);
      src.connect(node); node.connect(sink).connect(ctx.destination);
      this.proc = node; this.pipeline = "worklet";
    } catch (err) {
      const proc = ctx.createScriptProcessor(2048, 1, 1);
      proc.onaudioprocess = (e) => {
        const d = e.inputBuffer.getChannelData(0);
        this.onBlock(e.playbackTime - d.length / ctx.sampleRate, new Float32Array(d));
      };
      src.connect(proc); proc.connect(sink).connect(ctx.destination);
      this.proc = proc; this.pipeline = "script";
    }
    this.src = src;
  },
  // One block of mic audio: `t` = context time of its first sample.
  onBlock(t, d) {
    if (this.micStart == null) this.micStart = t;
    if (this.recording) this.recording.chunks.push({ t, d });
    const hist = this.hist;
    hist.copyWithin(0, d.length); hist.set(d, hist.length - d.length);
    let pk = 0; for (const x of d) pk = Math.max(pk, Math.abs(x));
    this.peak = Math.max(this.peak || 0, pk);
    const now = performance.now();
    if (now - this.lastMeter > 60) {  // the meter at ~16 fps is plenty, and keeps the page light
      this.lastMeter = now;
      const p = this.peak; this.peak = 0;
      const m = $("#sg-level span");
      if (m) { m.style.width = Math.min(100, Math.max(0, (20 * Math.log10(p + 1e-9) + 60) * 1.67)) + "%"; $("#sg-level").classList.toggle("hot", p > 0.7); }
      if (window.mkLevel) window.mkLevel(p);
    }
    if (Eng.playing && this.mode) {
      const f = detectPitch(hist, Eng.ctx.sampleRate);
      this.trail.push({ s: this.songPosAt(t + d.length / Eng.ctx.sampleRate) * this.bpm / 60, m: f ? hzToMidi(f) : null });
      if (this.trail.length > 600) this.trail.shift();
    }
  },
  closeMic() {
    if (this.proc) { this.proc.disconnect(); this.proc = null; }
    if (this.src) { this.src.disconnect(); this.src = null; }
    this.micStart = null;
    if (this.stream) { this.stream.getTracks().forEach((t) => t.stop()); this.stream = null; }
  },
  songPosAt(ctxTime) { return Eng.from + (ctxTime - Eng.t0); },
  start(mode) {
    const r = this.range(), spb = 60 / this.bpm;
    this.mode = mode; this.trail = [];
    const at = Eng.play(this.engineParts(), r.from);
    // Count-in clicks; with "click in quiet bits", keep ticking on beats where the guide has no note.
    for (let b = 0; b < r.countBars * 4; b++) Eng.click(at + b * spb, b % 4 === 0);
    if ($("#sg-click").checked) {
      const endBeat = r.b / spb;
      for (let beat = Math.ceil(r.a / spb); beat < endBeat; beat++) {
        const busy_ = this.notes.some((n) => n[0] <= beat + 0.01 && n[0] + n[1] > beat - 0.25);
        if (!busy_) Eng.click(at + (beat * spb - r.from), beat % 4 === 0);
      }
    }
    if (mode === "rec") this.recording = { chunks: [], range: r };
    $("#sg-stop").disabled = false; $("#sg-rec").disabled = $("#sg-listen").disabled = true;
    Eng.onstop = () => this.finish();
    this.endTimer = setInterval(() => { if (Eng.pos() > r.b + 1.0) Eng.stop(); }, 100);
    this.anim();
  },
  async finish() {
    clearInterval(this.endTimer);
    $("#sg-stop").disabled = true; $("#sg-rec").disabled = $("#sg-listen").disabled = false;
    const mode = this.mode; this.mode = null;
    const rec = this.recording; this.recording = null;
    if (mode !== "rec" || !rec || !rec.chunks.length) return;
    const sr = Eng.ctx.sampleRate;
    const { audio: all, start: t0, gaps } = joinChunks(rec.chunks, sr);
    const start = this.songPosAt(t0);
    const st = $("#sg-result");
    busy($("#sg-status"), "Checking the take…");
    try {
      const t = await api(songUrl(`/takes?start=${start.toFixed(4)}&section=${encodeURIComponent(rec.range && this.section.name)}&v=${curV()}&track=${encodeURIComponent($("#sg-track").value || "Lead")}&est_ms=${latencyEstimateMs()}&gaps=${gaps}&pipe=${Sing.pipeline || "worklet"}`),
        { method: "POST", body: wavBlob(all, sr) });
      busy($("#sg-status"), "");
      this.takes.push(t);
      const c = this.getChoice(); delete c[t.section]; this.setChoice(c);  // a new take is the one in use
      this.renderTracks();
      const s = t.score;
      st.textContent = (s.peak_db > -1 ? "That take clipped: lean back a little or turn the mic gain down." :
        s.peak_db < -24 ? "That take is very quiet: move a little closer or turn the mic gain up." : "") + dropoutNote(gaps);
      this.renderTakes();
    } catch (e) { busy($("#sg-status"), ""); st.textContent = errText(e); }
  },
  renderTakes() {
    const box = $("#sg-takes");
    const all = $("#sg-alltakes").checked;
    const list = (this.takes || []).filter((t) => all || (t.track || "Lead") === this.track);
    box.innerHTML = list.length ? "" : `<p class="muted small">No takes on ${esc(this.track || "this track")} yet: pick a section and press Record.</p>`;
    const NAMES_ = { A: "Verse 1", "A'": "Verse 2", B: "Bridge", "A''": "Final chorus", all: "Whole song" };
    const order = (this.sections || []).map((x) => x.name);
    list.slice().sort((a, b) => (order.indexOf(a.section) - order.indexOf(b.section)) || (b.created || 0) - (a.created || 0)).forEach((t) => {
      const s = t.score || { score: 0, lines: {} };
      const track = t.track || "Lead", ours = track === this.track;
      const inUse = ours && (this.stacks() || (this.takeInUse(t.section) || {}).id === t.id);
      const el = document.createElement("div");
      el.className = "take" + (inUse ? " inuse" : "") + (ours ? "" : " other");
      el.style.setProperty("--h", this.trackColor(track));
      const lines = Object.entries(s.lines || {}).filter(([, l]) => l.sung).map(([k, l]) =>
        `<span class="lchip ${l.score >= 0.8 ? "g" : l.score >= 0.6 ? "y" : "r"}" title="${l.pitch_cents} cents off, ${l.timing_ms} ms off the beat">line ${+k + 1}</span>`).join("");
      const scored = s.notes > 0;
      const old = !t.pipeline;  // recorded before the timing fix
      const when = t.created ? new Date(t.created * 1000).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) : "";
      el.innerHTML = `<span class="tag trk">${esc(track)}</span> <b>${esc(NAMES_[t.section] || t.section || "Take")}</b>
        <span class="small muted">${esc(when)}</span>
        ${inUse ? `<span class="pill in">${this.stacks() ? "★ stacked" : "★ in use"}</span>` : ""}
        ${old ? `<span class="pill warn" title="Recorded before the timing fix: it may sit up to ~0.2 s late. Re-record it, or use the Timing tweak.">old recorder</span>` : ""}
        ${t.dropouts ? `<span class="pill warn">${t.dropouts} dropout${t.dropouts > 1 ? "s" : ""}</span>` : ""}
        ${scored ? `<span class="bar"><span style="width:${Math.round(s.score * 100)}%"></span></span>
        <span class="small">${Math.round(s.score * 100)}</span> ${lines}` : `<span class="small muted">${s.peak_db != null ? "peak " + s.peak_db + " dB" : ""}</span>`}
        <span class="spacer"></span><audio controls preload="none" src="${songUrl(`/takes/${t.id}/audio`)}"></audio>
        ${ours && !inUse && !this.stacks() ? `<button data-use>Use this one</button>` : ""}
        ${ours ? `<button data-try>▶ Try voice</button>` : ""}
        <button class="ghost" data-del title="Delete this take">✕</button>`;
      const use = el.querySelector("[data-use]");
      if (use) use.onclick = () => { const c = this.getChoice(); c[t.section] = t.id; this.setChoice(c); this.renderTakes(); };
      const tr = el.querySelector("[data-try]");
      if (tr) tr.onclick = () => previewVoice(t.id, tr);
      el.querySelector("[data-del]").onclick = async () => {
        if (!confirm(`Delete this ${track} take of ${NAMES_[t.section] || t.section}?`)) return;
        await api(songUrl(`/takes/${t.id}`), { method: "DELETE" });
        this.takes = this.takes.filter((x) => x.id !== t.id); this.renderTakes(); this.renderTracks();
      };
      box.appendChild(el);
    });
  },
  anim() {
    if (!Eng.playing) { this.draw(); return; }
    this.draw(Eng.pos() * this.bpm / 60);
    requestAnimationFrame(() => this.anim());
  },
  draw(beat) {
    const cv = $("#sg-lane"); if (!cv || !this.notes) return;
    const dpr = window.devicePixelRatio || 1, w = cv.clientWidth, h = 260;
    cv.width = w * dpr; cv.height = h * dpr;
    const ctx = cv.getContext("2d"); ctx.scale(dpr, dpr);
    const r = this.section ? this.range() : null;
    const spb = 60 / (this.bpm || 100);
    const now = beat ?? (r ? r.a / spb : 0);
    const left = now - 2, right = now + 8;
    const vis = this.notes.filter((n) => n[0] + n[1] > left && n[0] < right);
    let ps = (vis.length ? vis : this.notes).map((n) => n[2]);
    if (!ps.length) ps = this.trail.filter((x) => x.m != null).map((x) => x.m).concat([57, 74]);
    const lo = Math.min(...ps) - 3, hi = Math.max(...ps) + 3;
    const X = (b) => (b - left) / (right - left) * w, Y = (m) => h - 10 - (m - lo) / (hi - lo) * (h - 20);
    ctx.fillStyle = css("--bg"); ctx.fillRect(0, 0, w, h);
    ctx.font = "10px system-ui";
    for (let m = Math.ceil(lo); m <= hi; m++) {
      ctx.strokeStyle = css("--grid"); ctx.globalAlpha = m % 12 === 0 ? 1 : 0.5;
      ctx.beginPath(); ctx.moveTo(0, Y(m)); ctx.lineTo(w, Y(m)); ctx.stroke();
      if (m % 12 === 0 || m % 12 === 7) { ctx.fillStyle = css("--muted"); ctx.fillText(noteName(m), 2, Y(m) - 2); }
    }
    ctx.globalAlpha = 1;
    for (let b = Math.ceil(left); b < right; b++) {
      ctx.strokeStyle = css("--bar"); ctx.globalAlpha = b % 4 === 0 ? 0.9 : 0.25;
      ctx.beginPath(); ctx.moveTo(X(b), 0); ctx.lineTo(X(b), h); ctx.stroke();
    }
    ctx.globalAlpha = 1;
    for (const [s, l, p] of vis) {
      ctx.fillStyle = css("--clean"); ctx.globalAlpha = 0.35;
      ctx.fillRect(X(s), Y(p) - 6, Math.max(3, X(s + l) - X(s) - 2), 12);
    }
    ctx.globalAlpha = 1;
    // Your pitch: green within 25 cents of the note, yellow within 50, red beyond (any octave counts).
    for (const pt of this.trail) {
      if (pt.m == null || pt.s < left) continue;
      const n = this.notes.find((x) => x[0] <= pt.s && pt.s < x[0] + x[1]);
      let m = pt.m, col = "--muted";
      if (!n && !this.notes.length && this.key) {  // no melody to follow: in key or not
        const [kn, km] = this.key.split(" ");
        const tonic = NAMES.indexOf(kn) >= 0 ? NAMES.indexOf(kn) : ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"].indexOf(kn);
        const sc = (km === "major" ? [0, 2, 4, 5, 7, 9, 11] : [0, 2, 3, 5, 7, 8, 10]).map((x) => (x + tonic) % 12);
        const near = Math.min(...[-1, 0, 1].flatMap((o) => sc.map((pc) => Math.abs(m - (Math.floor(m / 12 + o) * 12 + pc)))));
        col = near * 100 <= 25 ? "--green" : near * 100 <= 50 ? "--amber" : "--red";
      }
      if (n) {
        const diff = ((m - n[2]) % 12 + 18) % 12 - 6;
        m = n[2] + diff;
        const c = Math.abs(diff * 100);
        col = c <= 25 ? "--green" : c <= 50 ? "--amber" : "--red";
      }
      ctx.fillStyle = css(col);
      ctx.beginPath(); ctx.arc(X(pt.s), Y(m), 2.5, 0, 6.3); ctx.fill();
    }
    ctx.strokeStyle = css("--red"); ctx.lineWidth = 2;
    ctx.beginPath(); ctx.moveTo(X(now), 0); ctx.lineTo(X(now), h); ctx.stroke();
    if (Eng.playing && r && now < r.a / spb) {  // count-in dots
      const left_ = Math.ceil(r.a / spb - now);
      ctx.fillStyle = css("--ink"); ctx.font = "bold 28px system-ui";
      ctx.fillText(left_ <= 4 ? String(left_) : "…", w / 2 - 8, 40);
    }
    this.drawLyrics(now);
  },
  // The words by section: from your own lyric sheet, or from the chosen lyrics' note events.
  lyricSections() {
    if (this.sheet && this.sheet.length) return this.sheet.map((x) => ({ name: x.section, start: x.start, beats: x.beats, mode: x.mode,
      lines: x.lines, singers: x.singers || [], line_singers: x.line_singers || [] }));
    const out = [];
    for (const e of this.events || []) {
      let sec = out.find((x) => x.name === e.section);
      if (!sec) { sec = { name: e.section, start: e.start, beats: 0, mode: "sung", lines: [], starts: [] }; out.push(sec); }
      if (!sec.lines[e.line]) { sec.lines[e.line] = ""; sec.starts[e.line] = e.start; }
      if (e.text) sec.lines[e.line] += (sec.lines[e.line] ? " " : "") + e.text;
      sec.beats = Math.max(sec.beats, e.start + e.length - sec.start);
    }
    for (const x of out) x.lines = x.lines.filter((l) => l != null);
    return out;
  },
  drawFullLyrics(beat, mode) {
    const box = $("#sg-lyrics"), secs = this.lyricSections();
    if (!secs.length) { box.innerHTML = `<div class="muted small">No words yet: paste lyrics in Make, or pick lyrics on the Lyrics tab.</div>`; return; }
    const playing = Eng.playing;
    const cur = (playing && secs.find((x) => beat >= x.start && beat < x.start + x.beats)) ||
      secs.find((x) => this.section && x.name === this.section.name) || secs[0];
    const per = cur.beats / Math.max(1, cur.lines.length);
    const li = playing && beat >= cur.start ? Math.min(cur.lines.length - 1, Math.floor((beat - cur.start) / per)) : -1;
    const key = mode + "|" + cur.name + "|" + li + "|" + secs.length;
    if (box.dataset.key === key) return;
    box.dataset.key = key;
    const show = mode === "song" ? secs : [cur];
    box.className = "karaoke full" + (mode === "song" ? " song" : "");
    box.innerHTML = show.map((x) => `<div class="lsec${x === cur ? " cur" : ""}"><div class="lhead">${esc(x.name)}${x.mode && x.mode !== "sung" && !(x.singers || []).some((w) => w.toLowerCase() === x.mode) ? ` <span class="tag">${esc(x.mode)}</span>` : ""} ${this.pills(x.singers)}</div>` +
      x.lines.map((l, i) => `<div class="lline${x === cur && i === li ? " on" : ""}">${esc(l)}${((x.line_singers || [])[i] || []).length ? ` <span class="small muted">+</span> ${this.pills(x.line_singers[i])}` : ""}</div>`).join("") + "</div>").join("");
    const on = box.querySelector(".lline.on") || box.querySelector(".lsec.cur");
    if (on && mode === "song") on.scrollIntoView({ block: "nearest" });
  },
  drawLyrics(beat) {
    const mode = $("#sg-words").value;
    if (mode !== "line") { this.drawFullLyrics(beat, mode); return; }
    const ev = this.events, box = $("#sg-lyrics");
    if (box.classList.contains("full")) { box.className = "karaoke"; box.dataset.key = ""; box.innerHTML = `<div class="now"></div><div class="next"></div>`; }
    if (!ev.length && this.sheet && this.sheet.length) {  // your own words, no melody: a teleprompter by section
      const sec = this.sheet.find((x) => beat >= x.start && beat < x.start + x.beats) ||
        this.sheet.find((x) => x.start > beat);
      if (!sec) { box.querySelector(".now").innerHTML = ""; box.querySelector(".next").textContent = ""; return; }
      const per = sec.beats / Math.max(1, sec.lines.length);
      const i = Math.max(0, Math.min(sec.lines.length - 1, Math.floor((beat - sec.start) / per)));
      const f = beat < sec.start ? 0 : Math.max(0, Math.min(1, (beat - sec.start - i * per) / per));
      const lineWho = (sec.line_singers || [])[i] || [];
      const sameAsSinger = (sec.singers || []).some((w) => w.toLowerCase() === sec.mode);
      const tag = (sec.mode !== "sung" && !sameAsSinger ? `<span class="tag">${esc(sec.mode)}</span> ` : "") +
        (sec.singers && sec.singers.length ? this.pills(sec.singers) + " " : "") +
        (lineWho.length ? `<span class="small muted">+</span> ${this.pills(lineWho)} ` : "");
      box.querySelector(".now").innerHTML = tag + `<span class="syl" style="--f:${(f * 100).toFixed(0)}%">${esc(sec.lines[i])}</span>`;
      const nxt = sec.lines[i + 1] || ((this.sheet[this.sheet.indexOf(sec) + 1] || {}).lines || [])[0] || "";
      box.querySelector(".next").textContent = nxt;
      return;
    }
    if (!ev.length) { box.querySelector(".now").innerHTML = `<span class="muted small">No words chosen yet: hum or sing "la", or pick lyrics on the Lyrics tab.</span>`; box.querySelector(".next").innerHTML = ""; return; }
    const key = (e) => e.section + "|" + e.line;
    let i = ev.findIndex((e) => e.start + e.length > beat);
    if (i < 0) i = ev.length - 1;
    const cur = key(ev[i]);
    const line = ev.filter((e) => key(e) === cur);
    const nextStart = ev.findIndex((e, j) => j > i && key(e) !== cur);
    const next = nextStart >= 0 ? ev.filter((e) => key(e) === key(ev[nextStart])) : [];
    // Syllable-by-syllable wipe driven by note times (a constant-speed wipe drifts).
    box.querySelector(".now").innerHTML = line.map((e) => {
      if (!e.text) return "";
      const f = Math.max(0, Math.min(1, (beat - e.start) / e.length));
      return `<span class="syl" style="--f:${(f * 100).toFixed(0)}%">${esc(e.text)}</span>`;
    }).join(" ");
    box.querySelector(".next").textContent = next.map((e) => e.text).filter(Boolean).join(" ");
  },
};
$("#sg-mic").onchange = () => { Sing.deviceId = $("#sg-mic").value; localStorage.setItem("mm-sing-mic", Sing.deviceId); Sing.closeMic(); };
$("#sg-rec").onclick = async () => {
  try { await Sing.openMic(); } catch (e) { $("#sg-result").textContent = "Couldn't open the mic: " + e.message; return; }
  Sing.start("rec");
};
$("#sg-listen").onclick = async () => { try { await Sing.openMic(); } catch { } Sing.start("listen"); };
$("#sg-stop").onclick = () => Eng.stop();
for (const id of ["#sg-music", "#sg-guide"]) $(id).oninput = () => {
  if (!Eng.playing) return;
  for (const p of Sing.engineParts()) Eng.setGain(p.id, p.gain, p.on);
};
$("#sg-latr").onchange = async () => {
  const s = await post("/api/settings", { vocal_latency_ms: +$("#sg-latr").value, latency_pipeline: Sing.pipeline || "worklet" });
  Sing.latency = s.vocal_latency_ms; Sing.measured = true; $("#sg-lat").textContent = Math.round(Sing.latency) + " ms";
};
// How late recordings arrive, as the browser sees it (sound out to the headphones plus the mic back in).
// Used until the sync test has measured the real delay.
function latencyEstimateMs() {
  const ctx = Eng.ctx;
  if (!ctx) return 0;
  let ms = ((ctx.baseLatency || 0) + (ctx.outputLatency || 0)) * 1000;
  let inMs = 10;
  try { const st = Sing.stream && Sing.stream.getAudioTracks()[0].getSettings(); if (st && st.latency) inMs = st.latency * 1000; } catch { }
  return Math.round(ms + inMs);
}
window.latencyEstimateMs = latencyEstimateMs;

// The recorded blocks as one buffer, each at its own time: if the browser ever drops a block, the gap
// becomes silence instead of pulling everything after it early. Returns {audio, start, gaps}. Only the
// audio-thread capture has exact block times; the old fallback's are jittery, so its blocks go back to back.
function joinChunks(chunks, sr, byTime = Sing.pipeline !== "script") {
  const t0 = chunks[0].t;
  if (!byTime) {
    const audio = new Float32Array(chunks.reduce((a, c) => a + c.d.length, 0));
    let o = 0; for (const c of chunks) { audio.set(c.d, o); o += c.d.length; }
    return { audio, start: t0, gaps: 0 };
  }
  const end = chunks.reduce((m, c) => Math.max(m, Math.round((c.t - t0) * sr) + c.d.length), 0);
  const audio = new Float32Array(end);
  let gaps = 0, expect = 0;
  for (const c of chunks) {
    let at = Math.round((c.t - t0) * sr);
    if (Math.abs(at - expect) <= 2) at = expect;  // tiny timing jitter: keep blocks back to back
    else if (at > expect && c.t > (Sing.micStart || 0) + 0.5) gaps++;  // (the mic's own start-up pause doesn't count)
    audio.set(c.d, Math.max(0, Math.min(at, end - c.d.length)));
    expect = at + c.d.length;
  }
  return { audio, start: t0, gaps };
}
window.joinChunks = joinChunks;
function dropoutNote(gaps) {
  return gaps ? ` The recording had ${gaps} dropout${gaps > 1 ? "s" : ""} (the computer was busy or the mic paused); ` +
    "they were filled with silence so the timing holds. If you hear gaps, close other apps and record again." : "";
}
window.dropoutNote = dropoutNote;

// Sync test: 12 clicks; say "ta" on each one (the first four are a count-in). Your recorded "ta"s land late
// by the round trip; the median is saved and used for every recording from then on (Make and Sing).
async function syncTest(st) {
  try { await Sing.openMic(); } catch (e) { st.textContent = "Couldn't open the mic: " + e.message; return null; }
  Eng.stop(true);
  const ctx = Eng.ctx, spb = 0.6, n = 12, at = ctx.currentTime + 0.5;
  Eng.from = 0; Eng.t0 = at; Eng.playing = true;
  st.innerHTML = `<b>Say "ta" exactly on each click</b> (the first four are a count-in).`;
  Sing.recording = { chunks: [] };
  for (let i = 0; i < n; i++) Eng.click(at + i * spb, i % 4 === 0);
  await new Promise((r) => setTimeout(r, (n * spb + 0.9) * 1000));
  Eng.playing = false;
  const rec = Sing.recording; Sing.recording = null;
  const sr = ctx.sampleRate, hop = Math.round(sr * 0.005);
  const env = [];
  for (const c of rec.chunks) for (let i = 0; i + hop <= c.d.length; i += hop) {
    let e = 0; for (let j = i; j < i + hop; j++) e += c.d[j] * c.d[j];
    env.push({ t: Sing.songPosAt(c.t + i / sr), e: Math.sqrt(e / hop) });
  }
  const peak = env.length ? Math.max(...env.map((x) => x.e)) : 0;
  const thr = peak * 0.25, offs = [];
  for (let i = 4; i < n; i++) {
    const want = i * spb, hit = env.find((x) => x.t > want - 0.2 && x.t < want + 0.5 && x.e > thr);
    if (hit) offs.push((hit.t - want) * 1000);
  }
  if (offs.length < 5 || peak < 0.01) { st.textContent = "Didn't hear enough \"ta\"s. Try again a bit louder."; return null; }
  offs.sort((a, b) => a - b);
  const med = offs[Math.floor(offs.length / 2)], spread = offs.at(-1) - offs[0];
  const s = await post("/api/settings", { vocal_latency_ms: med, latency_pipeline: Sing.pipeline });
  Sing.latency = s.vocal_latency_ms; Sing.measured = true;
  st.textContent = `Your recordings arrive ${Math.round(med)} ms late; that's now corrected for every recording.` +
    (spread > 120 ? " Your taps were uneven, so you may want to run it once more." : "");
  return med;
}
window.syncTest = syncTest;
$("#sg-sync").onclick = async () => {
  const med = await syncTest($("#sg-result"));
  if (med != null) { $("#sg-lat").textContent = Math.round(med) + " ms"; $("#sg-latr").value = Math.round(med); }
};
$("#sg-make").onclick = async () => {
  const st = $("#sg-result");
  if (!Sing.takes || !Sing.takes.length) { st.textContent = "Record a take first."; return; }
  Eng.stop(true);
  $("#sg-make").disabled = true;
  st.textContent = "";
  busy($("#sg-status"), "Picking the best line from each take, cleaning, timing, tuning and mixing… (about a minute)");
  try {
    const r = await post(songUrl("/vocals"), { v: curV(), preset: $("#sg-preset").value, lead_mode: $("#sg-lead").value,
      track: $("#sg-mk-track").value || "Lead", character: $("#sg-character").value || "natural", tune: $("#sg-tune").value,
      tweaks: Sing.getTweaks(), choice: Sing.stacks() ? undefined : Sing.getChoice() });
    const q = r.vocals.quality;
    busy($("#sg-status"), "");
    Mix.state = null;
    await reloadSong(r.version);
    await Sing.open();
    const steps = (r.vocals.steps || []).concat(r.vocals.vocal_gain_db != null ?
      [{ step: "Level", detail: `${r.vocals.vocal_gain_db > 0 ? "+" : ""}${r.vocals.vocal_gain_db} dB to sit with the music` }] : []);
    st.innerHTML = `<p><b>Done: ${esc(r.vocals.track || "the track")} is in the working version (version ${r.version + 1}).</b>
      Every vocal track you make goes into this same version; your vocals are parts in the Mix tab, so you can turn them up, down or off.
      <button id="sg-keep" class="primary">Save as a version</button></p>
      <ul class="checks">${q.checks.map((c) => `<li class="${c.level === "ok" ? "ok" : "warn"}">${esc(c.text)}</li>`).join("")}</ul>
      <details open><summary class="small"><b>What was done to your voice</b>, in order</summary><ol class="steps-done">${
        steps.map((s) => `<li><b>${esc(s.step)}</b>${s.detail ? ": " + esc(s.detail) : ""}</li>`).join("")}</ol></details>`;
    $("#sg-keep").onclick = () => keepVersion($("#sg-keep"));
  } catch (e) { busy($("#sg-status"), ""); st.textContent = errText(e); }
  $("#sg-make").disabled = false;
};

$("#sg-tw-reset").onclick = () => { Sing.setTweaks({}); Sing.renderTweaks(); };
// "Save as a version": the working version (where vocal tracks collect) is kept under a name of your choice.
async function keepVersion(btn) {
  const name = prompt("A name for this version (for example \"first full vocals\"):", "with vocals");
  if (name === null) return;
  btn.disabled = true;
  try {
    const r = await post(songUrl("/keep_version"), { v: curV(), name });
    await reloadSong(r.version);
    btn.textContent = "Saved"; btn.classList.remove("primary");
  } catch (e) { btn.disabled = false; alert(errText(e)); }
}
window.keepVersion = keepVersion;
// Try the voice and tweaks on a take (the one in use for the chosen section, or any take you click).
async function previewVoice(takeId, btn) {
  const msg = $("#sg-prev-msg"), au = $("#sg-prev-audio");
  btn.disabled = true; busy(msg, "Making the preview…");
  if (!$("#sg-tweaks-box").open) $("#sg-tweaks-box").open = true;
  try {
    const res = await fetch(songUrl("/vocals/preview"), { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ v: curV(), track: Sing.track || "Lead", take: takeId || undefined,
        character: $("#sg-character").value || "natural", preset: $("#sg-preset").value, tweaks: Sing.getTweaks(),
        band: $("#sg-prev-band").checked }) });
    if (!res.ok) { let d = ""; try { d = (await res.json()).detail; } catch { } throw new Error(d || res.statusText); }
    if (au.src) URL.revokeObjectURL(au.src);
    au.src = URL.createObjectURL(await res.blob());
    au.classList.remove("hidden"); busy(msg, ""); Eng.stop(true); au.play();
    au.scrollIntoView({ block: "nearest" });
  } catch (e) { busy(msg, ""); msg.textContent = e.message; }
  btn.disabled = false;
}
$("#sg-preview").onclick = (e) => {
  const t = Sing.section && Sing.takeInUse(Sing.section.name);
  previewVoice(t ? t.id : null, e.currentTarget);
};
$("#sg-alltakes").onchange = () => { Sing.renderTakes(); Sing.renderWorking(); };
$("#sg-words").onchange = () => { try { localStorage.setItem("mm-words", $("#sg-words").value); } catch { } Sing.draw(); };
try { const w = localStorage.getItem("mm-words"); if (w) $("#sg-words").value = w; } catch { }
$("#sg-character").onchange = () => {
  try { localStorage.setItem("mm-voice:" + currentSong.id + ":" + Sing.track, $("#sg-character").value); } catch { }
  Sing.renderWorking();
};

$("#bg-listen").onchange = async () => { await post("/api/settings", { background_listening: $("#bg-listen").checked }); setTimeout(refreshStatus, 1500); };

$("#mx-hits-go").onclick = async () => {
  busy($("#mx-status"), "Finding the hard accents in your vocal…");
  try {
    Mix.state = await post(songUrl("/mixer/vocal_hits"), { v: curV(), amount: $("#mx-hits-amount").value });
    Mix.dirty = true;
    await Mix.loadStems(); Mix.restartIfPlaying(); Mix.render();
    $("#mx-msg").textContent = `Added hits on ${Mix.state.hits} accents. Switch them off or try "a few" / "lots" if it's too much or too little.`;
  } catch (e) { busy($("#mx-status"), ""); $("#mx-msg").textContent = errText(e); }
};
