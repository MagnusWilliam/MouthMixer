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
      const ch = o.check || { score: 0, issues: [] };
      const fit = ch.score >= 0.9 ? "fits the melody well" : ch.score >= 0.7 ? "mostly fits" : "needs work";
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
    this.sections = v.sections.filter((s) => !/^(intro|outro|ending)/i.test(s.name));
    if (!this.sections.length) { st.textContent = "This song has no sections to sing."; return; }
    const NAMES_ = new Proxy({ A: "Verse 1", "A'": "Verse 2", B: "Bridge", "A''": "Final chorus" }, { get: (o, k) => o[k] || k });
    const box = $("#sg-sections");
    box.innerHTML = "";
    if (!this.section || !this.sections.some((s) => s.name === this.section.name)) this.section = this.sections[0];
    for (const s of [...this.sections, { name: "all", start: this.sections[0].start, bars: this.sections.at(-1).start + this.sections.at(-1).bars - this.sections[0].start }]) {
      const b = document.createElement("button");
      b.className = "chip" + (this.section && this.section.name === s.name ? " on" : "");
      b.textContent = s.name === "all" ? "Whole song" : NAMES_[s.name] || s.name;
      b.onclick = () => { this.section = s; [...box.children].forEach((c) => c.classList.toggle("on", c === b)); this.draw(); };
      box.appendChild(b);
    }
    this.notes = v.tracks.filter((t) => t.role === "lead").flatMap((t) => t.notes).sort((a, b) => a[0] - b[0]);
    const ly = await api(songUrl(`/lyrics?v=${curV()}`));
    this.events = ly.events || [];
    const presets = await api("/api/vocal_presets");
    const t = await api(songUrl("/takes"));
    this.takes = t.takes;
    this.latency = t.latency_ms || 0;
    $("#sg-lat").textContent = Math.round(this.latency);
    $("#sg-latr").value = Math.round(this.latency);
    $("#sg-preset").innerHTML = presets.map((p) => `<option value="${p.id}"${p.id === t.preset ? " selected" : ""}>${esc(p.label)}${p.id === t.preset ? " (suits this style)" : ""}</option>`).join("");
    await this.listMics();
    this.renderTakes();
    this.draw();
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
    const src = Eng.ctx.createMediaStreamSource(this.stream);
    const proc = Eng.ctx.createScriptProcessor(2048, 1, 1);
    const sink = Eng.ctx.createGain(); sink.gain.value = 0;
    const hist = new Float32Array(4096);
    proc.onaudioprocess = (e) => {
      const d = e.inputBuffer.getChannelData(0);
      // the input block ends roughly when this callback's output would start: song time of its first sample
      const t = e.playbackTime - d.length / Eng.ctx.sampleRate;
      if (this.recording) this.recording.chunks.push({ t, d: new Float32Array(d) });
      hist.copyWithin(0, d.length); hist.set(d, hist.length - d.length);
      let pk = 0; for (const x of d) pk = Math.max(pk, Math.abs(x));
      $("#sg-level span").style.width = Math.min(100, Math.max(0, (20 * Math.log10(pk + 1e-9) + 60) * 1.67)) + "%";
      $("#sg-level").classList.toggle("hot", pk > 0.7);
      if (window.mkLevel) window.mkLevel(pk);
      if (Eng.playing && this.mode) {
        const f = detectPitch(hist, Eng.ctx.sampleRate);
        this.trail.push({ s: this.songPosAt(t + d.length / Eng.ctx.sampleRate) * this.bpm / 60, m: f ? hzToMidi(f) : null });
        if (this.trail.length > 600) this.trail.shift();
      }
    };
    src.connect(proc); proc.connect(sink).connect(Eng.ctx.destination);
    this.proc = proc;
  },
  closeMic() {
    if (this.proc) { this.proc.disconnect(); this.proc = null; }
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
    const sr = Eng.ctx.sampleRate, n = rec.chunks.reduce((a, c) => a + c.d.length, 0);
    const all = new Float32Array(n); let o = 0; for (const c of rec.chunks) { all.set(c.d, o); o += c.d.length; }
    const start = this.songPosAt(rec.chunks[0].t);
    const st = $("#sg-result");
    busy($("#sg-status"), "Checking the take…");
    try {
      const t = await api(songUrl(`/takes?start=${start.toFixed(4)}&section=${encodeURIComponent(rec.range && this.section.name)}&v=${curV()}`),
        { method: "POST", body: wavBlob(all, sr) });
      busy($("#sg-status"), "");
      this.takes.push(t);
      const s = t.score;
      st.textContent = s.peak_db > -1 ? "That take clipped: lean back a little or turn the mic gain down." :
        s.peak_db < -24 ? "That take is very quiet: move a little closer or turn the mic gain up." : "";
      this.renderTakes();
    } catch (e) { busy($("#sg-status"), ""); st.textContent = errText(e); }
  },
  renderTakes() {
    const box = $("#sg-takes");
    box.innerHTML = this.takes.length ? "" : `<p class="muted small">No takes yet.</p>`;
    const NAMES_ = { A: "Verse 1", "A'": "Verse 2", B: "Bridge", "A''": "Final chorus", all: "Whole song" };
    this.takes.slice().reverse().forEach((t) => {
      const s = t.score || { score: 0, lines: {} };
      const el = document.createElement("div");
      el.className = "take";
      const lines = Object.entries(s.lines).filter(([, l]) => l.sung).map(([k, l]) =>
        `<span class="lchip ${l.score >= 0.8 ? "g" : l.score >= 0.6 ? "y" : "r"}" title="${l.pitch_cents} cents off, ${l.timing_ms} ms off the beat">line ${+k + 1}</span>`).join("");
      el.innerHTML = `<b>${esc(NAMES_[t.section] || t.section || "Take")}</b>
        <span class="bar"><span style="width:${Math.round(s.score * 100)}%"></span></span>
        <span class="small">${Math.round(s.score * 100)}</span> ${lines}
        <span class="spacer"></span><audio controls preload="none" src="${songUrl(`/takes/${t.id}/audio`)}"></audio>
        <button class="ghost">✕</button>`;
      el.querySelector("button").onclick = async () => {
        await api(songUrl(`/takes/${t.id}`), { method: "DELETE" });
        this.takes = this.takes.filter((x) => x.id !== t.id); this.renderTakes();
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
    const ps = (vis.length ? vis : this.notes).map((n) => n[2]);
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
  drawLyrics(beat) {
    const ev = this.events, box = $("#sg-lyrics");
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
  const s = await post("/api/settings", { vocal_latency_ms: +$("#sg-latr").value });
  Sing.latency = s.vocal_latency_ms; $("#sg-lat").textContent = Math.round(Sing.latency);
};
// Sync test: 8 clicks; say "ta" on each one. Your recorded "ta"s land late by the round-trip latency.
$("#sg-sync").onclick = async () => {
  const st = $("#sg-result");
  try { await Sing.openMic(); } catch (e) { st.textContent = "Couldn't open the mic: " + e.message; return; }
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
  const peak = Math.max(...env.map((x) => x.e));
  const thr = peak * 0.25, offs = [];
  for (let i = 4; i < n; i++) {
    const want = i * spb, hit = env.find((x) => x.t > want - 0.25 && x.t < want + 0.45 && x.e > thr);
    if (hit) offs.push((hit.t - want) * 1000);
  }
  if (offs.length < 5 || peak < 0.01) { st.textContent = "Didn't hear enough \"ta\"s. Try again a bit louder."; return; }
  offs.sort((a, b) => a - b);
  const med = offs[Math.floor(offs.length / 2)], spread = offs.at(-1) - offs[0];
  const s = await post("/api/settings", { vocal_latency_ms: med });
  Sing.latency = s.vocal_latency_ms; $("#sg-lat").textContent = Math.round(med); $("#sg-latr").value = Math.round(med);
  st.textContent = `Your recordings arrive ${Math.round(med)} ms late; that's now corrected.` +
    (spread > 120 ? " Your taps were uneven, so you may want to run it once more." : "");
};
$("#sg-make").onclick = async () => {
  const st = $("#sg-result");
  if (!Sing.takes || !Sing.takes.length) { st.textContent = "Record a take first."; return; }
  Eng.stop(true);
  $("#sg-make").disabled = true;
  st.textContent = "";
  busy($("#sg-status"), "Picking the best line from each take, cleaning, timing, tuning and mixing… (about a minute)");
  try {
    const r = await post(songUrl("/vocals"), { v: curV(), preset: $("#sg-preset").value, lead_mode: $("#sg-lead").value });
    const q = r.vocals.quality;
    busy($("#sg-status"), "");
    Mix.state = null;
    await reloadSong(r.version);
    st.innerHTML = `<p><b>Done: version ${r.version + 1}, "${esc(r.title)}".</b> Your vocals are now a part in the Mix tab,
      so you can turn them up, down or off.</p>
      <ul class="checks">${q.checks.map((c) => `<li class="${c.level === "ok" ? "ok" : "warn"}">${esc(c.text)}</li>`).join("")}</ul>
      <p class="small muted">Moved ${r.vocals.timing_moved} notes in time, lowered ${r.vocals.breaths_lowered} breaths, ` +
      `vocal ${r.vocals.vocal_gain_db > 0 ? "+" : ""}${r.vocals.vocal_gain_db} dB to sit with the music.</p>`;
  } catch (e) { busy($("#sg-status"), ""); st.textContent = errText(e); }
  $("#sg-make").disabled = false;
};

$("#bg-listen").onchange = async () => { await post("/api/settings", { background_listening: $("#bg-listen").checked }); setTimeout(refreshStatus, 1500); };
