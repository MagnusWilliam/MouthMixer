"use strict";
// The Make tab: starter beats, the booth (record pieces on purpose), pieces as Incredibox-style
// characters, one-note fixes, and the song board. Uses Eng, Sing (mic), busy, errText, dbToGain,
// prettySound, ROLE_ICON from studio.js and $, api, post, esc, wavBlob, NAMES, noteName from app.js.

const SLOT_ICON = { beat: "🥁", bass: "〰", riff: "⚡", stab: "💥", chop: "🎤", perc: "🪘", hook: "★", lead: "♪",
  bridge: "🌉", counter: "↩", intro: "✦", fill: "🥁", chords: "🎹", pad: "☁" };
const SLOT_COLOR = { beat: "drums", fill: "drums", perc: "perc", bass: "bass", riff: "riff", stab: "riff", chop: "vocal",
  hook: "lead", lead: "lead", bridge: "lead", counter: "counter", intro: "counter", chords: "comp", pad: "pad" };

const Make = {
  proj: null, starters: null, which: "A", on: {}, loops: [], playing: false, sel: null, selNote: null,
  slot: null, recPiece: null, recording: false,

  async open() {
    if (this.proj) { this.showProject(); return; }
    this.showHome();
  },
  leave() { this.stop(); },

  // ---- home: starters and track list ----------------------------------------------------------
  async showHome() {
    this.stop();
    this.proj = null;
    $("#mk-home").classList.remove("hidden"); $("#mk-project").classList.add("hidden");
    if (!this.starters) this.starters = await api("/api/starters");
    const box = $("#mk-moods");
    box.innerHTML = "";
    for (const m of this.starters.moods) {
      const row = document.createElement("div");
      row.className = "mood";
      row.innerHTML = `<div class="mood-head"><b>${esc(m.label)}</b> <span class="small muted">${esc(m.hint)}</span></div>`;
      const cards = document.createElement("div");
      cards.className = "starter-cards";
      for (const st of this.starters.starters.filter((x) => x.mood === m.id)) {
        const c = document.createElement("button");
        c.className = "starter";
        c.innerHTML = `<b>${esc(st.style)}</b><span class="small">${esc(st.key)} · ${st.bpm} BPM</span><span class="small muted">${esc(st.describe)}</span>`;
        c.onclick = async () => {
          c.disabled = true;
          const p = await post("/api/projects", { starter: st.id, title: `${m.label} track` });
          this.proj = p; this.on = {}; this.showProject();
        };
        cards.appendChild(c);
      }
      row.appendChild(cards);
      box.appendChild(row);
    }
    const list = await api("/api/projects");
    const pl = $("#mk-projects");
    pl.innerHTML = list.length ? "" : `<p class="muted small">None yet: pick a starter beat above.</p>`;
    for (const t of list) {
      const el = document.createElement("div");
      el.className = "item";
      el.innerHTML = `<div class="t">${esc(t.title)}</div><div class="s">${esc(t.mood)} · ${t.pieces} piece${t.pieces === 1 ? "" : "s"} recorded${t.song_id ? " · built" : ""}</div>`;
      el.onclick = async () => { this.proj = await api("/api/projects/" + t.id); this.on = {}; this.showProject(); };
      pl.appendChild(el);
    }
  },

  // ---- a project ------------------------------------------------------------------------------
  url(p) { return `/api/projects/${this.proj.id}${p}`; },
  piece(id) { return this.proj.pieces.find((p) => p.id === id); },
  get spb() { return 60 / this.proj.starter.bpm; },

  async showProject() {
    $("#mk-home").classList.add("hidden"); $("#mk-project").classList.remove("hidden");
    const p = this.proj;
    $("#mk-name").value = p.title;
    $("#mk-chips").innerHTML = [p.style, p.starter.bpm + " BPM"].map((c) => `<span class="chip">${esc(c)}</span>`).join("");
    const ks = $("#mk-key");
    ks.innerHTML = NAMES.map((n, i) => `<option value="${i}"${i === p.starter.tonic ? " selected" : ""}>${n} ${p.starter.mode}</option>`).join("");
    $("#mk-chords").textContent = `Main loop: ${p.chords_a.join(" → ")}   ·   Bridge: ${p.chords_b.join(" → ")}`;
    for (const q of p.pieces) if (!(q.id in this.on)) this.on[q.id] = true;
    this.renderSlots(); this.renderPieces(); this.renderDetail(); this.renderBoard();
    $("#mk-built").innerHTML = p.song_id ? `Built before. <a href="#" id="mk-open">Open it in Songs</a> (Mix, Lyrics, Sing).` : "";
    const o = $("#mk-open"); if (o) o.onclick = (e) => { e.preventDefault(); this.openSong(p.song_id); };
    await this.loadLoops();
  },
  async refresh(p) {  // after any change: new state from the server, new loops
    if (p) this.proj = p;
    for (const q of this.proj.pieces) if (!(q.id in this.on)) this.on[q.id] = true;
    this.renderPieces(); this.renderDetail(); this.renderBoard();
    await this.loadLoops();
  },

  async loadLoops() {
    const st = $("#mk-status");
    busy(st, "Getting the loops ready…");
    try {
      const r = await api(this.url(`/booth?chords=${this.which}`));
      Eng.init();
      await Promise.all(r.loops.map(async (l) => {
        const key = "keep:mk:" + l.stem;
        if (!Eng.buffers[key]) {
          const res = await fetch(this.url(`/stems/${l.stem}`));
          Eng.buffers[key] = await Eng.ctx.decodeAudioData(await res.arrayBuffer());
        }
      }));
      this.loops = r.loops;
      busy(st, "");
      if (this.playing && !this.recording) this.play();
    } catch (e) { busy(st, ""); st.textContent = errText(e); }
  },

  gainOf(q) { return dbToGain(q.gain_db || 0); },
  play(exclude = null) {
    Eng.stop(true);
    const ctx = Eng.init();
    const at = ctx.currentTime + 0.1;
    Eng.nodes = {};
    for (const l of this.loops) {
      const buf = Eng.buffers["keep:mk:" + l.stem];
      const q = this.piece(l.id);
      if (!buf || !q) continue;
      const src = ctx.createBufferSource();
      src.buffer = buf; src.loop = true;
      const g = ctx.createGain();
      g.gain.value = this.on[q.id] && q.id !== exclude ? this.gainOf(q) : 0;
      src.connect(g).connect(Eng.master);
      src.start(at);
      Eng.nodes[q.id] = { src, g };
    }
    Eng.playing = true; Eng.t0 = at; Eng.from = 0;
    this.playing = true;
    this.t0 = at;
    $("#mk-play").textContent = "■ Stop";
    if ($("#mk-click").checked) this.scheduleClicks(at, 64);
    return at;
  },
  scheduleClicks(at, beats) {
    for (let b = 0; b < beats; b++) Eng.click(at + b * this.spb, b % 4 === 0);
  },
  stop() {
    if (this.recording) return;
    Eng.stop(true);
    this.playing = false;
    if ($("#mk-play")) $("#mk-play").textContent = "▶ Play loop";
  },
  setOn(id, on) {
    this.on[id] = on;
    const q = this.piece(id);
    if (Eng.nodes[id] && q) Eng.setGain(id, this.gainOf(q), on);
  },

  // ---- pieces (characters) --------------------------------------------------------------------
  renderPieces() {
    const box = $("#mk-pieces");
    box.innerHTML = "";
    for (const q of this.proj.pieces) {
      const el = document.createElement("div");
      el.className = `tile r-${SLOT_COLOR[q.slot] || "lead"}` + (this.on[q.id] ? "" : " off") + (this.sel === q.id ? " solo" : "");
      const empty = !q.notes.length && !q.gen && !q.audio;
      const choices = q.choices.length > 1 ? `<select title="Swap the sound">${q.choices.map((c) =>
        `<option value="${esc(c)}"${c === q.instrument ? " selected" : ""}>${esc(prettySound(c))}</option>`).join("")}</select>`
        : `<span class="small muted">${esc(prettySound(q.instrument))}</span>`;
      el.innerHTML = `
        <button class="power" title="On / off">${SLOT_ICON[q.slot] || "♪"}</button>
        <div class="tname">${esc(q.name)}${q.source === "starter" ? ' <span class="tag">starter</span>' : ' <span class="yours">yours</span>'}</div>
        <div class="trole small muted">${esc(this.proj.slots[q.slot].label)} · ${q.bars} bar${q.bars > 1 ? "s" : ""}${empty ? " · not recorded yet" : ""}</div>
        ${choices}
        <div class="tctl"><input type="range" min="-18" max="6" step="1" value="${q.gain_db || 0}" title="Volume">
          <button class="ghost more" title="Takes, notes, variations">⋯</button></div>`;
      el.querySelector(".power").onclick = () => { this.setOn(q.id, !this.on[q.id]); el.classList.toggle("off", !this.on[q.id]); };
      const sel = el.querySelector("select");
      if (sel) sel.onchange = async () => this.refresh(await post(this.url(`/pieces/${q.id}`), { instrument: sel.value }));
      const vol = el.querySelector("input[type=range]");
      vol.oninput = () => { q.gain_db = +vol.value; Eng.setGain(q.id, this.gainOf(q), this.on[q.id]); };
      vol.onchange = () => post(this.url(`/pieces/${q.id}`), { gain_db: q.gain_db });
      el.querySelector(".more").onclick = () => { this.sel = this.sel === q.id ? null : q.id; this.selNote = null; this.renderPieces(); this.renderDetail(); };
      box.appendChild(el);
    }
  },

  renderDetail() {
    const box = $("#mk-detail");
    const q = this.sel && this.piece(this.sel);
    if (!q) { box.classList.add("hidden"); return; }
    box.classList.remove("hidden");
    const takes = q.takes.slice().sort((a, b) => b.score - a.score);
    const pitched = !q.instrument.startsWith("kit:") && q.source !== "voice";
    box.innerHTML = `
      <div class="row"><b>${esc(q.name)}</b><span class="small muted">${esc(this.proj.slots[q.slot].hint || "")}</span><span class="spacer"></span>
        <button class="ghost" data-a="close">Close</button></div>
      ${q.source === "starter" ? `<p class="small muted">A starter part: it follows each section's chords. Switch it off, swap its sound, or record your own ${esc(this.proj.slots[q.slot].label.toLowerCase())} to replace it.</p>` : ""}
      ${q.notes.length ? `<canvas class="notes" height="140"></canvas>
      <div class="row small noteops">
        <span class="muted">Click a note, then:</span>
        ${pitched ? `<button data-op="up" title="Up a note of the key">▲</button><button data-op="down" title="Down a note of the key">▼</button>
        <button data-op="up1" title="Up a half step">♯</button><button data-op="down1" title="Down a half step">♭</button>` : ""}
        <button data-op="earlier" title="Earlier by a 16th">◀</button><button data-op="later" title="Later by a 16th">▶</button>
        ${pitched ? `<button data-op="shorter" title="Shorter">−</button><button data-op="longer" title="Longer">+</button>` : ""}
        <button data-op="delete" title="Remove the note">✕</button>
      </div>` : ""}
      <div class="row small">
        ${q.notes.length ? `<button data-v="simpler">Simpler</button><button data-v="busier">Busier</button>` : ""}
        ${pitched ? `<span>Octave <button data-o="-1">−</button> <b>${q.octave > 0 ? "+" : ""}${q.octave}</b> <button data-o="1">+</button></span>` : ""}
        ${q.kind === "one" && !this.proj.slots[q.slot].at_end ? `<label><input type="checkbox" data-a="repeat"${q.repeat ? " checked" : ""}> Repeat to fill the section</label>` : ""}
        <span class="spacer"></span>
        ${q.source !== "starter" ? `<button data-a="again">● Record more takes</button>` : ""}
        <button data-a="delete" class="ghost">Delete piece</button>
      </div>
      ${takes.length ? `<div class="small"><b>Takes</b> (best first; the best is used unless you pick another)</div>
        <div class="takes">${takes.map((t) => `<div class="take${t.id === q.take ? " on" : ""}">
          <span class="bar"><span style="width:${Math.round(t.score * 100)}%"></span></span> <span>${Math.round(t.score * 100)}</span>
          <span class="small muted">${t.detail.notes != null ? t.detail.notes + " notes" : t.detail.hits + " hits"}, pass ${t.pass + 1}</span>
          <span class="spacer"></span>
          ${t.id === q.take ? '<span class="small">in use</span>' : `<button data-t="${t.id}">Use</button>`}
          <button class="ghost" data-del="${t.id}">✕</button></div>`).join("")}</div>` : ""}`;
    box.querySelector('[data-a="close"]').onclick = () => { this.sel = null; this.renderPieces(); this.renderDetail(); };
    const edit = async (body) => this.refresh(await post(this.url(`/pieces/${q.id}`), body));
    box.querySelectorAll("[data-op]").forEach((b) => b.onclick = async () => {
      if (this.selNote == null) return;
      const op = b.dataset.op;
      await edit({ note_op: op, index: this.selNote });
      if (op === "delete") this.selNote = null;
    });
    box.querySelectorAll("[data-v]").forEach((b) => b.onclick = () => edit({ variation: b.dataset.v }));
    box.querySelectorAll("[data-o]").forEach((b) => b.onclick = () => edit({ octave: q.octave + +b.dataset.o }));
    box.querySelectorAll("[data-t]").forEach((b) => b.onclick = () => edit({ take: b.dataset.t }));
    box.querySelectorAll("[data-del]").forEach((b) => b.onclick = async () =>
      this.refresh(await api(this.url(`/pieces/${q.id}/takes/${b.dataset.del}`), { method: "DELETE" })));
    const rep = box.querySelector('[data-a="repeat"]'); if (rep) rep.onchange = () => edit({ repeat: rep.checked });
    const ag = box.querySelector('[data-a="again"]'); if (ag) ag.onclick = () => this.pickSlot(q.slot, q.id);
    box.querySelector('[data-a="delete"]').onclick = async () => {
      if (!confirm(`Delete "${q.name}"?`)) return;
      this.sel = null;
      this.refresh(await api(this.url(`/pieces/${q.id}`), { method: "DELETE" }));
    };
    const cv = box.querySelector("canvas.notes");
    if (cv) this.drawNotes(cv, q);
  },

  drawNotes(cv, q) {
    const dpr = window.devicePixelRatio || 1, w = cv.clientWidth, h = 140;
    cv.width = w * dpr; cv.height = h * dpr;
    const ctx = cv.getContext("2d"); ctx.scale(dpr, dpr);
    const L = q.bars * 4, ps = q.notes.map((n) => n[2]);
    const lo = Math.min(...ps) - 2, hi = Math.max(...ps) + 2;
    const X = (b) => 6 + b / L * (w - 12), Y = (m) => h - 8 - (m - lo) / Math.max(1, hi - lo) * (h - 16);
    ctx.fillStyle = css("--bg"); ctx.fillRect(0, 0, w, h);
    for (let b = 0; b <= L; b++) {
      ctx.strokeStyle = css("--bar"); ctx.globalAlpha = b % 4 === 0 ? 0.9 : 0.3;
      ctx.beginPath(); ctx.moveTo(X(b), 0); ctx.lineTo(X(b), h); ctx.stroke();
    }
    ctx.globalAlpha = 1; ctx.font = "10px system-ui";
    const drums = q.instrument.startsWith("kit:");
    const DRUMN = { 36: "kick", 38: "snare", 42: "hat", 46: "open hat", 39: "clap", 64: "conga", 70: "shaker", 54: "tamb." };
    q.notes.forEach(([s, l, p], i) => {
      ctx.fillStyle = css(i === this.selNote ? "--amber" : "--clean");
      ctx.fillRect(X(s), Y(p) - 5, Math.max(4, X(s + l) - X(s) - 1), 10);
      if (i === this.selNote) { ctx.fillStyle = css("--ink"); ctx.fillText(drums ? (DRUMN[p] || p) : noteName(p), X(s), Y(p) - 8); }
    });
    cv.onclick = (e) => {
      const r = cv.getBoundingClientRect(), x = e.clientX - r.left, y = e.clientY - r.top;
      let best = null, bd = 1e9;
      q.notes.forEach(([s, l, p], i) => {
        const cx = Math.max(X(s), Math.min(x, X(s + l))), d = Math.hypot(cx - x, Y(p) - y);
        if (d < bd) { bd = d; best = i; }
      });
      this.selNote = bd < 30 ? best : null;
      this.drawNotes(cv, q);
    };
  },

  // ---- recording ------------------------------------------------------------------------------
  renderSlots() {
    const p = this.proj;
    for (const [kind, boxId] of [["loop", "#mk-slots-loop"], ["one", "#mk-slots-one"]]) {
      const box = $(boxId);
      box.innerHTML = "";
      for (const id of p.recordable.filter((s) => p.slots[s].kind === kind)) {
        const b = document.createElement("button");
        b.className = "chip" + (this.slot === id && !this.recPiece ? " on" : "");
        b.textContent = `${SLOT_ICON[id] || ""} ${p.slots[id].label}`;
        b.title = p.slots[id].hint;
        b.onclick = () => this.pickSlot(id, null);
        box.appendChild(b);
      }
    }
  },
  pickSlot(slot, pieceId) {
    this.slot = slot; this.recPiece = pieceId;
    const s = this.proj.slots[slot];
    const q = pieceId && this.piece(pieceId);
    $("#mk-rec").classList.remove("hidden");
    $("#mk-rec-hint").innerHTML = `<b>${esc(q ? "More takes for " + q.name : s.label)}</b>: ${esc(s.hint)}` +
      (s.chords === "B" ? " <i>(recorded over the bridge chords)</i>" : "");
    $("#mk-rec-bars").value = String(q ? q.bars : s.bars);
    $("#mk-rec-bars").disabled = !!q;
    $("#mk-rec-pass").textContent = "";
    this.renderSlots();
    $("#mk-rec").scrollIntoView({ block: "nearest" });
  },
  async record() {
    const st = $("#mk-status");
    try { await Sing.openMic(); } catch (e) { st.textContent = "Couldn't open the mic: " + e.message; return; }
    let pid = this.recPiece;
    if (!pid) {  // a new piece for this slot
      const r = await post(this.url("/pieces"), { slot: this.slot, bars: +$("#mk-rec-bars").value });
      this.proj = r; pid = r.added; this.on[pid] = true;
      this.renderPieces();
    }
    this.recPiece = pid;
    const q = this.piece(pid);
    const want = this.proj.slots[q.slot].chords === "B" ? "B" : "A";
    if (this.which !== want) { this.setChords(want); await this.loadLoops(); }
    this.recording = true;
    Eng.stop(true);
    const ctx = Eng.init();
    // One bar of count-in clicks, then the loops start at bar 1 (everything that's on, minus this piece).
    const loopAt = ctx.currentTime + 0.15 + 4 * this.spb;
    for (let b = 0; b < 4; b++) Eng.click(loopAt - (4 - b) * this.spb, b === 0);
    this.startLoopsAt(loopAt, pid);
    this.t0 = loopAt;
    $("#mk-play").textContent = "■ Stop";
    Sing.recording = { chunks: [] };
    $("#mk-rec-go").disabled = true; $("#mk-rec-stop").disabled = false;
    const passLen = q.bars * 4 * this.spb;
    this.passTimer = setInterval(() => {
      const t = ctx.currentTime - loopAt;
      $("#mk-rec-pass").textContent = t < 0 ? `count-in ${Math.ceil(-t / this.spb)}` : `take ${Math.floor(t / passLen) + 1} · bar ${Math.floor((t % passLen) / (4 * this.spb)) + 1} of ${q.bars}`;
    }, 100);
  },
  startLoopsAt(at, exclude) {
    const ctx = Eng.ctx;
    Eng.nodes = {};
    for (const l of this.loops) {
      const buf = Eng.buffers["keep:mk:" + l.stem];
      const q = this.piece(l.id);
      if (!buf || !q) continue;
      const src = ctx.createBufferSource();
      src.buffer = buf; src.loop = true;
      const g = ctx.createGain();
      g.gain.value = this.on[q.id] && q.id !== exclude ? this.gainOf(q) : 0;
      src.connect(g).connect(Eng.master);
      src.start(at);
      Eng.nodes[q.id] = { src, g };
    }
    if ($("#mk-click").checked) this.scheduleClicks(at, 256);
    Eng.playing = true; Eng.t0 = at; this.playing = true;
  },
  async stopRecording() {
    clearInterval(this.passTimer);
    const rec = Sing.recording; Sing.recording = null;
    this.recording = false;
    this.stop();
    $("#mk-rec-go").disabled = false; $("#mk-rec-stop").disabled = true;
    if (!rec || !rec.chunks.length) return;
    const sr = Eng.ctx.sampleRate, n = rec.chunks.reduce((a, c) => a + c.d.length, 0);
    const all = new Float32Array(n); let o = 0; for (const c of rec.chunks) { all.set(c.d, o); o += c.d.length; }
    const start = rec.chunks[0].t - this.t0;  // loop time of the first sample
    const st = $("#mk-status");
    busy(st, "Reading your takes…");
    try {
      const r = await api(this.url(`/pieces/${this.recPiece}/record?start=${start.toFixed(4)}`), { method: "POST", body: wavBlob(all, sr) });
      busy(st, "");
      const q = r.pieces.find((x) => x.id === this.recPiece);
      $("#mk-rec-pass").textContent = `${r.new_takes.length} take${r.new_takes.length === 1 ? "" : "s"} saved`;
      this.sel = this.recPiece;
      await this.refresh(r);
      if (q && !q.notes.length && !q.audio) st.textContent = "Nothing was heard in those takes: check the mic (Setup) and try again.";
    } catch (e) { busy(st, ""); st.textContent = errText(e); }
  },

  setChords(w) {
    this.which = w;
    document.querySelectorAll("[data-ch]").forEach((b) => b.classList.toggle("on", b.dataset.ch === w));
  },

  // ---- the song board -------------------------------------------------------------------------
  renderBoard() {
    const p = this.proj, t = $("#mk-board");
    const secs = p.sections;
    let html = `<thead><tr><th></th>${secs.map((s, i) => `<th data-i="${i}">
        <input class="secname" value="${esc(s.name)}">
        <div class="secctl"><select class="secbars">${[2, 4, 8, 12, 16].map((b) => `<option${b === s.bars ? " selected" : ""}>${b}</option>`).join("")}</select>
        <select class="secch"><option value="A"${s.chords === "A" ? " selected" : ""}>main</option><option value="B"${s.chords === "B" ? " selected" : ""}>bridge</option></select>
        <button class="ghost secx" title="Remove section">✕</button></div></th>`).join("")}</tr></thead><tbody>`;
    for (const q of p.pieces) {
      html += `<tr><th class="rowname"><span>${SLOT_ICON[q.slot] || "♪"}</span> ${esc(q.name)}</th>` +
        secs.map((s, i) => `<td><button class="cell${s.parts.includes(q.id) ? " on" : ""}" data-s="${i}" data-q="${q.id}"></button></td>`).join("") + "</tr>";
    }
    t.innerHTML = html + "</tbody>";
    const save = async () => { this.proj = await post(this.url(""), { sections: p.sections }); this.renderBoard(); };
    t.querySelectorAll(".cell").forEach((c) => c.onclick = () => {
      const s = secs[+c.dataset.s], id = c.dataset.q;
      s.parts = s.parts.includes(id) ? s.parts.filter((x) => x !== id) : [...s.parts, id];
      c.classList.toggle("on");
      save();
    });
    t.querySelectorAll("th[data-i]").forEach((th) => {
      const s = secs[+th.dataset.i];
      th.querySelector(".secname").onchange = (e) => { s.name = e.target.value; save(); };
      th.querySelector(".secbars").onchange = (e) => { s.bars = +e.target.value; save(); };
      th.querySelector(".secch").onchange = (e) => { s.chords = e.target.value; save(); };
      th.querySelector(".secx").onclick = () => { if (secs.length > 1) { secs.splice(+th.dataset.i, 1); save(); } };
    });
  },

  async build() {
    const out = $("#mk-built"), btn = $("#mk-build");
    btn.disabled = true;
    busy(out, "Building the whole song: placing every piece, mixing, checking… (about a minute)");
    try {
      const r = await post(this.url("/build"));
      const c = r.critic;
      out.innerHTML = `<p><b>Built (${fmtLen(r.seconds)}).</b> ${c.ok ? "It passed the music checks." :
        "The checks flagged: " + esc(c.rejects.join("; ")) + " (you can still listen and tweak)."}
        <a href="#" id="mk-open">Open it in Songs</a> to listen, mix, write lyrics and sing over it.</p>`;
      $("#mk-open").onclick = (e) => { e.preventDefault(); this.openSong(r.song_id); };
      this.proj.song_id = r.song_id;
    } catch (e) { out.textContent = errText(e); }
    btn.disabled = false;
  },
  async openSong(id) {
    this.stop();
    document.querySelector('[data-view="songs"]').click();
    await selectSong(id);
  },
};
window.Make = Make;

$("#mk-back").onclick = (e) => { e.preventDefault(); Make.showHome(); };
$("#mk-name").onchange = async () => { Make.proj = await post(Make.url(""), { title: $("#mk-name").value }); };
$("#mk-key").onchange = async () => { Make.stop(); await Make.refresh(await post(Make.url(""), { tonic: +$("#mk-key").value })); Make.showProject(); };
$("#mk-play").onclick = () => { if (Make.playing) Make.stop(); else Make.play(); };
document.querySelectorAll("[data-ch]").forEach((b) => b.onclick = async () => { Make.setChords(b.dataset.ch); await Make.loadLoops(); });
$("#mk-rec-go").onclick = () => Make.record();
$("#mk-rec-stop").onclick = () => Make.stopRecording();
$("#mk-add-sec").onclick = async () => {
  Make.proj.sections.push({ name: "Hook " + (Make.proj.sections.length + 1), bars: 8, chords: "A", parts: [] });
  Make.proj = await post(Make.url(""), { sections: Make.proj.sections }); Make.renderBoard();
};
$("#mk-build").onclick = () => Make.build();
window.mkLevel = (pk) => {
  const m = $("#mk-level span"); if (!m) return;
  m.style.width = Math.min(100, Math.max(0, (20 * Math.log10(pk + 1e-9) + 60) * 1.67)) + "%";
  $("#mk-level").classList.toggle("hot", pk > 0.7);
};
setInterval(() => {
  if (!Make.proj || !Make.playing || !Eng.ctx) return;
  const t = Eng.ctx.currentTime - Make.t0;
  $("#mk-bar").textContent = t < 0 ? "" : `bar ${Math.floor(t / (4 * Make.spb)) % 4 + 1} of 4`;
}, 150);
// The Make tab is where you start.
document.querySelector('[data-view="make"]').click();
