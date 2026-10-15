"""Vocal processing (docs/VOCALS.md): your sung takes, cleaned, timed, tuned, comped, processed and mixed
into a song.

Pipeline (each step is its own function so it can be tested on synthetic singing, `synth.sing`):

1. `Take`: a recording placed in song time (latency already subtracted).
2. `comp`: the best take per phrase, spliced with 5 ms crossfades placed just before the phrase.
3. `clean`: high-pass, noise reduction from the pre-roll, plosive pops.
4. `correct`: WORLD vocoder (pyworld) per phrase: onsets found against the melody, timing pulled in,
   pitch moved note by note (natural or hard), resynthesised with the voice's own spectral envelope;
   consonants and breaths come from the original audio.
5. `tame_breaths`: breaths turned down, never deleted.
6. `chain`: the 13-step effect chain with per-style presets.
7. `sit_in_song`: vocal level against the music, the music carved at 1-4 kHz under the voice, and your
   hummed lead ducked while you sing.
8. `quality`: the §9 quality gates.

Everything runs at the render rate (44.1 kHz) in song time: sample 0 is the song's first beat.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .render import SR

FRAME_MS = 5.0

# Style presets (VOCALS.md §6). Values not set fall back to DEFAULT.
DEFAULT = {
    "label": "Natural", "tune": "natural", "strength": 0.8, "retune_ms": 40, "comp_a": 8.0, "comp_b": 3.0,
    "comp_b_db": 4.0, "presence_db": 2.0, "air_db": 3.0, "sat": 0.15, "drive_bite": 0.0, "doubles": None,
    "harmony": None, "reverb": 0.18, "room": 0.55, "decay_s": 1.4, "predelay_ms": 30, "delay": 0.12,
    "delay_beats": 0.75, "slap_ms": 0, "throws": True, "bandpass": None, "shimmer": 0.0, "octave_layer": 0.0,
    "level_lu": -1.0, "deess_db": 6.0,
    # Switches for each step (the "Processing" tweaks): raw skips everything but level and timing.
    "raw": False, "highpass": True, "denoise": 0.35, "breaths": True, "compress": 1.0, "tone_match": True, "gate": True,
}
PRESETS = {
    "soul": {"label": "Soul / city pop: warm, natural tuning, plate", "strength": 0.6, "retune_ms": 45,
             "comp_a": 6.0, "comp_b": 2.5, "comp_b_db": 3.0, "air_db": 2.0, "sat": 0.25, "harmony": "hook",
             "decay_s": 1.6, "room": 0.6, "level_lu": -1.0},
    "bright_pop": {"label": "Bright pop: tight tuning, airy, doubled hook", "strength": 0.85, "retune_ms": 25,
                   "comp_a": 8.0, "comp_b": 4.0, "comp_b_db": 5.0, "air_db": 3.0, "doubles": "hook",
                   "decay_s": 1.2, "room": 0.5, "delay": 0.16, "delay_beats": 0.5, "level_lu": 0.5},
    "rock": {"label": "Rock / battle: bite and drive, short space", "retune_ms": 30, "comp_a": 10.0, "comp_b": 4.0,
             "comp_b_db": 6.0, "presence_db": 3.5, "sat": 0.45, "drive_bite": 2.5, "decay_s": 0.9, "room": 0.35,
             "delay": 0.0, "slap_ms": 100, "level_lu": -2.0},
    "cinematic": {"label": "Cinematic: light touch, big hall", "strength": 0.6, "retune_ms": 50, "comp_a": 4.0,
                  "comp_b": 2.0, "comp_b_db": 2.0, "sat": 0.05, "reverb": 0.3, "room": 0.85, "decay_s": 2.8,
                  "predelay_ms": 50, "delay": 0.06, "level_lu": -3.0},
    "lofi": {"label": "Lo-fi: loose tuning, band-passed, tape", "strength": 0.5, "retune_ms": 60, "sat": 0.4,
             "air_db": 0.0, "bandpass": (300, 4000), "reverb": 0.12, "room": 0.3, "decay_s": 0.6, "delay": 0.08,
             "level_lu": -3.0},
    "arcade": {"label": "Arcade / hyperpop: hard tuning, stacked", "tune": "hard", "strength": 1.0, "retune_ms": 0,
               "comp_a": 10.0, "comp_b": 4.0, "comp_b_db": 6.0, "doubles": "all", "octave_layer": 0.18,
               "decay_s": 0.8, "room": 0.35, "level_lu": 0.0},
    "dreamy": {"label": "Dreamy: airy, long hall, shimmer", "strength": 0.7, "retune_ms": 40, "comp_a": 4.0,
               "comp_b": 2.0, "comp_b_db": 2.5, "air_db": 3.0, "reverb": 0.32, "room": 0.9, "decay_s": 3.0,
               "predelay_ms": 40, "shimmer": 0.12, "delay": 0.14, "level_lu": -3.0},
}


def preset(name: str | None) -> dict:
    return DEFAULT | PRESETS.get(name or "soul", PRESETS["soul"]) | {"name": name or "soul"}



def _movavg(x: np.ndarray, k: int) -> np.ndarray:
    """Centred moving average (same length), O(n) with a running sum: np.convolve with a long box is
    O(n*k) and took most of the processing time on whole-song tracks."""
    k = max(1, int(k))
    x = np.asarray(x, dtype=np.float64)
    if k == 1 or len(x) == 0:
        return x.copy()
    c = np.cumsum(np.pad(x, (k // 2 + 1, k - k // 2 - 1), mode="constant"))
    return (c[k:] - c[:-k])[: len(x)] / k


# --------------------------------------------------------------------------------------------------
# Takes and notes
# --------------------------------------------------------------------------------------------------

@dataclass
class Take:
    """A recording. `t0` is the song time (seconds) of its first sample, latency already removed."""
    audio: np.ndarray
    t0: float
    id: str = ""

    @classmethod
    def from_recording(cls, x: np.ndarray, sr: int, start_sec: float, latency_ms: float, id: str = "") -> "Take":
        """`start_sec`: the song position the browser was playing when recording began. What you hear
        comes out `latency` late and what you sing comes in late too; the sync test measures the sum."""
        x = np.asarray(x, dtype=np.float32)
        if x.ndim > 1:
            x = x.mean(axis=1 if x.shape[0] > x.shape[1] else 0)
        if sr != SR:
            import librosa

            x = librosa.resample(x, orig_sr=sr, target_sr=SR).astype(np.float32)
        return cls(x, start_sec - latency_ms / 1000.0, id)

    @property
    def end(self) -> float:
        return self.t0 + len(self.audio) / SR


@dataclass
class Note:
    start: float  # seconds, song time
    end: float
    midi: int
    line: int = 0
    section: str = ""


def notes_in_seconds(lead: list, bpm: float, sections: list[dict] | None = None) -> list[Note]:
    """Lead notes [(start_beat, length_beats, midi, ...)] to seconds, numbered into lines (phrases)
    exactly as the lyrics are (lyrics.phrases, per section), so a comped line is a lyric line."""
    from .lyrics import phrases

    spb = 60.0 / bpm
    notes = sorted(tuple(x)[:3] for x in lead)
    secs = sections or [{"name": "", "start": 0, "bars": 10 ** 6}]
    out: list[Note] = []
    line = 0
    for sc in secs:
        a, b = sc["start"] * 4, (sc["start"] + sc["bars"]) * 4
        for ln in phrases([n for n in notes if a <= n[0] < b]):
            for s, l, p in ln:
                out.append(Note(s * spb, (s + l) * spb, int(p), line, sc["name"]))
            line += 1
    return out


def lines_of(notes: list[Note]) -> list[tuple[float, float, list[int]]]:
    """(start, end, note indices) per line."""
    out = {}
    for i, n in enumerate(notes):
        out.setdefault(n.line, []).append(i)
    return [(notes[ix[0]].start, notes[ix[-1]].end, ix) for ix in out.values()]


# --------------------------------------------------------------------------------------------------
# Pitch tracking (fast) for scoring takes
# --------------------------------------------------------------------------------------------------

def _active_regions(y: np.ndarray, sr: int, floor_db: float = -55.0, gap: float = 0.4, pad: float = 0.2):
    """(start, end) samples of the parts with sound in them: a whole song's vocal track is mostly silence,
    and pitch tracking silence is wasted time."""
    w = max(1, int(0.05 * sr))
    n = len(y) // w
    if n == 0:
        return [(0, len(y))]
    e = 10 * np.log10(np.mean(y[: n * w].reshape(n, w).astype(np.float64) ** 2, axis=1) + 1e-12)
    on = np.flatnonzero(e > floor_db)
    if not len(on):
        return []
    out = []
    a = prev = on[0]
    for k in on[1:]:
        if (k - prev) * w > gap * sr:
            out.append((a, prev + 1))
            a = k
        prev = k
    out.append((a, prev + 1))
    p = int(pad * sr)
    return [(max(0, s0 * w - p), min(len(y), e0 * w + p)) for s0, e0 in out]


def track_f0(x: np.ndarray, sr: int = SR, fast: bool = True) -> tuple[np.ndarray, np.ndarray]:
    """f0 (Hz, 0 = unvoiced) every 5 ms, analysed at 16 kHz, only where there is sound. Voicing (and so
    note onsets) always comes from DIO + StoneMask: Harvest smears voicing 20-150 ms into the consonants
    before a note (measured on synthetic singing). With fast=False the pitch values come from Harvest
    where both agree a frame is voiced (Harvest has fewer octave slips, which WORLD resynthesis would
    turn into glitches)."""
    import librosa
    import pyworld as pw

    y = librosa.resample(np.asarray(x, dtype=np.float32), orig_sr=sr, target_sr=16000).astype(np.float64)
    hop = int(16000 * FRAME_MS / 1000)
    n_frames = len(y) // hop + 1
    t = np.arange(n_frames) * FRAME_MS / 1000
    f0 = np.zeros(n_frames)
    for a, b in _active_regions(y, 16000):
        a = (a // hop) * hop
        seg = y[a:b]
        if len(seg) < hop * 4:
            continue
        fs, ts = pw.dio(seg, 16000, f0_floor=70, f0_ceil=1100, frame_period=FRAME_MS)
        fs = pw.stonemask(seg, fs, ts, 16000)
        if not fast:
            fh, _ = pw.harvest(seg, 16000, f0_floor=70, f0_ceil=1100, frame_period=FRAME_MS)
            m = min(len(fh), len(fs))
            fs[:m] = np.where((fs[:m] > 0) & (fh[:m] > 0), fh[:m], fs[:m])
        k = a // hop
        m = min(len(fs), n_frames - k)
        f0[k:k + m] = fs[:m]
    # Drop single-frame voicing blips.
    v = f0 > 0
    for i in range(1, len(v) - 1):
        if v[i] and not v[i - 1] and not v[i + 1]:
            f0[i] = 0
    return f0, t


def cents(f: np.ndarray, midi: float) -> np.ndarray:
    return 1200 * np.log2(np.maximum(f, 1e-6) / (440.0 * 2 ** ((midi - 69) / 12)))


def _octave_fold(c: np.ndarray) -> np.ndarray:
    """Any octave counts (VOCALS §7): fold cents into -600..600."""
    return (c + 600) % 1200 - 600


def find_onsets(f0: np.ndarray, t: np.ndarray, t0: float, notes: list[Note], window: float = 0.15) -> list[float | None]:
    """Where each note was actually sung (song time), or None if not found. Use DIO voicing (track_f0
    with fast=True): Harvest's smoother pitch moves note changes earlier. A note starts at the voicing
    onset nearest its slot (after at least 10 ms of silence); when sung legato (no gap), at the first
    frame closer to its own pitch than to the previous note's."""
    times = t + t0
    voiced = f0 > 0
    out: list[float | None] = []
    for k, n in enumerate(notes):
        a, b = np.searchsorted(times, [n.start - window, min(n.start + window, n.end)])
        if b <= a:
            out.append(None)
            continue
        starts = [i for i in range(max(a, 2), b) if voiced[i] and not voiced[i - 1] and not voiced[i - 2]]
        if starts:
            out.append(float(times[min(starts, key=lambda i: abs(times[i] - n.start))]))
            continue
        prev = notes[k - 1] if k else None
        found = None
        if prev is not None and prev.midi != n.midi and n.start - prev.end < 0.08:
            for i in range(a, b):
                if voiced[i]:
                    c = f0[i:i + 1]
                    if abs(_octave_fold(cents(c, n.midi)))[0] < abs(_octave_fold(cents(c, prev.midi)))[0]:
                        found = float(times[i])
                        break
        elif a == 0 and voiced[0]:
            found = float(times[0])
        out.append(found)
    return out


def note_errors(f0: np.ndarray, t: np.ndarray, t0: float, notes: list[Note], onsets: list) -> list[dict]:
    """Per note: the median pitch error of its stable middle 60% (cents, octave-folded) and onset error."""
    times = t + t0
    res = []
    for k, n in enumerate(notes):
        on = onsets[k] if onsets[k] is not None else n.start
        dur = n.end - n.start
        a, b = np.searchsorted(times, [on + 0.2 * dur, on + 0.8 * dur])
        seg = f0[a:b]
        seg = seg[seg > 0]
        err = float(np.median(_octave_fold(cents(seg, n.midi)))) if len(seg) >= 3 else None
        res.append({"pitch_cents": err, "onset_ms": None if onsets[k] is None else 1000 * (onsets[k] - n.start)})
    return res


def score_take(take: Take, notes: list[Note]) -> dict:
    """How good a take is, per line and overall (for the take list and for comping)."""
    covered = [i for i, n in enumerate(notes) if n.start >= take.t0 + 0.05 and n.end <= take.end]
    if not covered:  # no melody to score against (your own tune, rap): just the levels
        pre = take.audio[: max(1, int(0.5 * SR))]
        return {"lines": {}, "score": 0.0, "notes": 0, "peak_db": round(_db(np.abs(take.audio).max()), 1),
                "noise_db": round(_db(np.sqrt(np.mean(pre.astype(np.float64) ** 2))), 1)}
    sub = [notes[i] for i in covered]
    f0, t = track_f0(take.audio)
    onsets = find_onsets(f0, t, take.t0, sub)
    errs = note_errors(f0, t, take.t0, sub, onsets)
    late = [e["onset_ms"] for e in errs if e["onset_ms"] is not None]
    lateness = float(np.median(late)) if late else 0.0
    lines: dict[int, dict] = {}
    for n, e in zip(sub, errs):
        d = lines.setdefault(n.line, {"pitch": [], "timing": [], "missing": 0, "n": 0})
        d["n"] += 1
        if e["pitch_cents"] is None or e["onset_ms"] is None:
            d["missing"] += 1
        if e["pitch_cents"] is not None:
            d["pitch"].append(abs(e["pitch_cents"]))
        if e["onset_ms"] is not None:
            d["timing"].append(abs(e["onset_ms"] - lateness))
    out = {}
    for ln, d in lines.items():
        p = float(np.mean(d["pitch"])) if d["pitch"] else 100.0
        tm = float(np.mean(d["timing"])) if d["timing"] else 100.0
        miss = d["missing"] / d["n"]
        # 1.0 = in tune and on time; 0 = 100 cents off or 150 ms off or nothing sung.
        s = max(0.0, 1 - 0.5 * min(1, p / 100) - 0.3 * min(1, tm / 150) - 0.6 * miss)
        out[ln] = {"pitch_cents": round(p, 1), "timing_ms": round(tm, 1), "missing": d["missing"], "score": round(s, 3),
                   "sung": d["missing"] < d["n"] / 2}
    raw = take.audio
    pre = raw[: max(1, int(0.5 * SR))]
    # Lines you didn't attempt (a take that runs past its section) don't count against it.
    tried = [v["score"] for v in out.values() if v["sung"]] or [0.0]
    return {"lines": out, "score": round(float(np.mean(tried)), 3), "notes": len(sub),
            "lateness_ms": round(lateness, 1), "peak_db": round(_db(np.abs(raw).max()), 1),
            "noise_db": round(_db(np.sqrt(np.mean(pre ** 2))), 1)}


def _db(x) -> float:
    return float(20 * np.log10(max(float(x), 1e-9)))


# --------------------------------------------------------------------------------------------------
# Comping: the best take for each line
# --------------------------------------------------------------------------------------------------

def comp(takes: list[Take], notes: list[Note], scores: list[dict] | None = None, length: float | None = None,
         choice: dict[int, str] | None = None) -> tuple[np.ndarray, dict[int, str], float]:
    """Splice the best take per line into one track in song time. Returns (audio, line -> take id,
    the start time of the noise pre-roll). `choice` overrides the pick for some lines."""
    scores = scores or [score_take(tk, notes) for tk in takes]
    length = length or max(tk.end for tk in takes) + 0.5
    n = int(length * SR)
    out = np.zeros(n, dtype=np.float32)
    picks: dict[int, str] = {}
    ls = lines_of(notes)
    owner = np.full(n, -1)
    for li, (a, b, _) in enumerate(ls):
        cands = [(sc["lines"][li]["score"], j) for j, sc in enumerate(scores)
                 if sc["lines"].get(li, {}).get("sung") and takes[j].t0 <= a - 0.05 and takes[j].end >= b]
        if choice and li in choice:
            cands = [(9, j) for j, tk in enumerate(takes) if tk.id == choice[li]] or cands
        if not cands:
            continue
        j = max(cands)[1]
        picks[li] = takes[j].id
        # The line runs from a cut just before it (the quietest 5 ms in the 250 ms before) to the next line.
        nxt = ls[li + 1][0] if li + 1 < len(ls) else b + 1.0
        lo = _quiet_point(takes[j], a - 0.25, a - 0.02)
        hi = min(nxt - 0.25, takes[j].end)
        hi = _quiet_point(takes[j], max(b, hi - 0.25), max(b + 0.01, hi)) if hi > b else b
        owner[max(0, int(lo * SR)):min(n, int(hi * SR))] = j
    out = _fill(takes, owner, n)
    # Room noise for the profile: the first take's lead-in before its first note.
    first = min(takes, key=lambda tk: tk.t0)
    return out, picks, first.t0


def _fill(takes: list[Take], owner: np.ndarray, n: int, fade_s: float = 0.005) -> np.ndarray:
    """Audio from each sample's owning take (-1 = silence), crossfading at every change of owner."""
    out = np.zeros(n, dtype=np.float32)
    fade = int(fade_s * SR)
    i = 0
    while i < n:
        j = owner[i]
        k = i
        while k < n and owner[k] == j:
            k += 1
        if j >= 0:
            tk = takes[j]
            a, b = max(i - fade, 0), min(k + fade, n)
            src0 = int(round((a / SR - tk.t0) * SR))
            seg = np.zeros(b - a, dtype=np.float32)
            s0, s1 = max(0, src0), min(len(tk.audio), src0 + (b - a))
            if s1 > s0:
                seg[s0 - src0:s1 - src0] = tk.audio[s0:s1]
            env = np.ones(b - a)
            if a < i:  # fade in across [i - fade, i + fade)
                m = min(2 * fade, len(env))
                env[:m] = np.linspace(0, 1, m)
            if b > k:  # fade out across [k - fade, k + fade)
                m = min(2 * fade, len(env))
                env[-m:] = np.minimum(env[-m:], np.linspace(1, 0, m))
            out[a:b] += seg * env
        i = k
    return out


def _quiet_point(tk: Take, a: float, b: float) -> float:
    i0, i1 = int((a - tk.t0) * SR), int((b - tk.t0) * SR)
    i0, i1 = max(0, i0), min(len(tk.audio), i1)
    w = int(0.005 * SR)
    if i1 - i0 <= w * 2:
        return max(a, tk.t0)
    e = np.convolve(tk.audio[i0:i1] ** 2, np.ones(w) / w, mode="valid")
    return tk.t0 + (i0 + int(np.argmin(e)) + w // 2) / SR


# --------------------------------------------------------------------------------------------------
# Clean-up
# --------------------------------------------------------------------------------------------------

def _sos(kind, f, order=4):
    from scipy.signal import butter

    return butter(order, f, btype=kind, fs=SR, output="sos")


def _filt(x, sos):
    from scipy.signal import sosfiltfilt

    return sosfiltfilt(sos, x).astype(np.float32)


def _quietest(x: np.ndarray, w: int) -> np.ndarray:
    if len(x) <= w:
        return x
    c = np.cumsum(np.r_[0.0, x.astype(np.float64) ** 2])
    i = int(np.argmin(c[w:] - c[:-w]))
    return x[i:i + w]


def take_noise(takes: list[Take], notes: list[Note]) -> tuple[np.ndarray, float]:
    """The room noise: the quietest 300 ms of the lead-ins (the count-in, before the first sung note),
    above 100 Hz. Measured on the user's takes (VOCALS §13): most of the "noise" was 43-59 Hz rumble, which
    the low cut removes anyway, and the count-in also carries the click bleeding from the headphones, so
    a whole count-in made a wrong profile for noise reduction."""
    w = int(0.3 * SR)
    lead_ins = []
    for tk in takes:
        first = min((n.start for n in notes if n.start >= tk.t0), default=tk.end)
        seg = tk.audio[: max(0, int((first - 0.4 - tk.t0) * SR))]
        if len(seg) >= SR // 10:
            lead_ins.append(_filt(seg, _sos("high", 100)))
    if lead_ins:
        cands = [_quietest(s, w) for s in lead_ins]
    else:  # no lead-in: the quietest 300 ms of the first take
        cands = [_quietest(_filt(takes[0].audio, _sos("high", 100)), w)]
    best = min(cands, key=lambda s: float(np.mean(s.astype(np.float64) ** 2)))
    return best, _db(np.sqrt(np.mean(best.astype(np.float64) ** 2)) + 1e-12)


def did(report: dict, step: str, detail: str = "") -> None:
    """Note a processing step that ran, in order, for the "What was done to your voice" list."""
    report.setdefault("steps", []).append({"step": step, "detail": detail})


def denoise(x: np.ndarray, noise: np.ndarray, noise_db: float, amount: float, hp: float | None,
            report: dict) -> np.ndarray:
    """Stationary noise reduction from the count-in. `amount` is noisereduce's prop_decrease: 0.35 (light,
    about 4 dB) is the default since measuring the user's takes (VOCALS §13): 0.6 (about 8 dB) added ~40%
    more abrupt level jumps between syllables on a quiet verse. Skipped in a quiet room."""
    if amount <= 0 or noise_db <= -65 or len(noise) <= SR // 10:
        report["noise_reduction_db"] = 0
        return x
    import noisereduce as nr

    ref = _filt(noise, _sos("high", hp)) if hp else noise
    y = nr.reduce_noise(y=x, sr=SR, y_noise=ref, stationary=True, prop_decrease=amount, n_fft=2048).astype(np.float32)
    report["noise_reduction_db"] = round(-20 * np.log10(1 - amount))
    did(report, "Noise reduction", f"about {report['noise_reduction_db']} dB off the room noise ({noise_db:.0f} dBFS)")
    return y


def clean(x: np.ndarray, notes: list[Note], noise: np.ndarray, noise_db: float, report: dict,
          p: dict | None = None) -> np.ndarray:
    """High-pass, noise reduction from the pre-roll (VOCALS §2), plosive pops near onsets."""
    p = p or DEFAULT
    lowest = min(n.midi for n in notes)
    hp = float(np.clip(0.7 * 440 * 2 ** ((lowest - 69) / 12), 70, 150)) if p["highpass"] else None
    y = _filt(x, _sos("high", hp)) if hp else np.asarray(x, dtype=np.float32)
    report["highpass_hz"] = round(hp) if hp else 0
    if hp:
        did(report, "Low cut", f"below {round(hp)} Hz")
    y = denoise(y, noise, noise_db, p["denoise"], hp, report)
    if hp:
        y, pops = fix_plosives(y, notes)
        report["plosives_fixed"] = pops
        if pops:
            did(report, "Pops softened", f"{pops} plosive{'s' if pops > 1 else ''}")
    return y


def fix_plosives(x: np.ndarray, notes: list[Note]) -> tuple[np.ndarray, int]:
    """A burst under 150 Hz more than 10 dB above the line's average, within 40 ms of an onset, gets a
    60 ms high-pass at 120 Hz with 10 ms fades."""
    low = _filt(x, _sos("low", 150, 2))
    w = int(0.01 * SR)
    env = np.sqrt(_movavg(low.astype(np.float64) ** 2, w))
    hp = _filt(x, _sos("high", 120, 4))
    y = x.copy()
    count = 0
    for li, (a, b, _) in enumerate(lines_of(notes)):
        ia, ib = max(0, int(a * SR)), min(len(x), int(b * SR))
        if ib - ia < w:
            continue
        avg = _db(np.sqrt(np.mean(env[ia:ib] ** 2)))
        for n in notes:
            if n.line != li:
                continue
            i0, i1 = max(0, int((n.start - 0.06) * SR)), min(len(x), int((n.start + 0.04) * SR))
            if i1 <= i0:
                continue
            if _db(env[i0:i1].max()) > avg + 10:
                j0, j1 = i0, min(len(x), i0 + int(0.08 * SR))
                m = np.ones(j1 - j0)
                f = min(w, (j1 - j0) // 2)
                m[:f] = np.linspace(0, 1, f)
                m[-f:] = np.linspace(1, 0, f)
                y[j0:j1] = x[j0:j1] * (1 - m) + hp[j0:j1] * m
                count += 1
    return y, count


# --------------------------------------------------------------------------------------------------
# Timing and pitch correction (WORLD)
# --------------------------------------------------------------------------------------------------

def timing_targets(notes: list[Note], onsets: list) -> tuple[list[float | None], float, list[int]]:
    """Corrections (seconds, positive = move earlier) per note. Your average lateness is kept as feel;
    the rest: ±25 ms left alone, beyond that pulled halfway (at most 40 ms), over 80 ms flagged."""
    devs = [o - n.start for o, n in zip(onsets, notes) if o is not None]
    lateness = float(np.median(devs)) if devs else 0.0
    corr: list[float | None] = []
    flagged = []
    for k, (o, n) in enumerate(zip(onsets, notes)):
        if o is None:
            corr.append(None)
            continue
        r = o - n.start - lateness
        if abs(r) <= 0.025:
            corr.append(0.0)
        else:
            corr.append(float(np.clip(r / 2, -0.04, 0.04)))
            if abs(r) > 0.08:
                flagged.append(k)
    return corr, lateness, flagged


def _warp_anchors(onsets, corr, seg_a: float, seg_b: float) -> tuple[np.ndarray, np.ndarray]:
    """(output times, input times) for a piecewise-linear time map; segment edges stay put and no
    stretch beyond ±20% (VOCALS §3)."""
    outs, ins = [seg_a], [seg_a]
    for o, c in zip(onsets, corr):
        if o is None or c is None or not seg_a + 0.03 < o < seg_b - 0.03:
            continue
        new = o - c
        if new <= outs[-1] + 0.01:
            continue
        outs.append(new)
        ins.append(o)
    outs.append(seg_b)
    ins.append(seg_b)
    outs, ins = np.array(outs), np.array(ins)
    # Limit stretch: shrink corrections until every piece is within 0.8-1.25x.
    for _ in range(8):
        r = np.diff(outs) / np.maximum(np.diff(ins), 1e-6)
        if np.all((r >= 0.8) & (r <= 1.25)):
            break
        outs[1:-1] = ins[1:-1] + 0.5 * (outs[1:-1] - ins[1:-1])
    return outs, ins


def pitch_curve(f0: np.ndarray, times: np.ndarray, notes: list[Note], onsets: list, p: dict) -> tuple[np.ndarray, list]:
    """The corrected f0 (same frames). Natural: each note's whole contour moves by (error × strength)
    if it's more than 10 cents off, eased in over retune_ms; slow drift (< 2 Hz) halved; vibrato and
    scoops kept. Hard: snapped to the note, vibrato removed."""
    out = f0.copy()
    fixes = []
    hard = p["tune"] == "hard"
    hop = FRAME_MS / 1000
    for k, n in enumerate(notes):
        on = onsets[k] if onsets[k] is not None else n.start
        nxt = notes[k + 1].start if k + 1 < len(notes) else n.end + 0.2
        a, b = np.searchsorted(times, [on, min(max(n.end, on + 0.05), nxt)])
        if b - a < 3:
            continue
        idx = np.arange(a, b)
        v = f0[idx] > 0
        if v.sum() < 3:
            continue
        c = cents(f0[idx[v]], n.midi)
        octave = 1200 * np.round(np.median(c) / 1200)
        c = c - octave
        L = len(idx)
        mid = c[(np.arange(L)[v] >= int(0.2 * L)) & (np.arange(L)[v] < max(int(0.8 * L), 1))]
        med = float(np.median(mid if len(mid) >= 3 else c))
        tt = times[idx[v]] - on
        if hard:
            ease = np.clip(tt / max(p["retune_ms"] / 1000, 1e-3), 0, 1) if p["retune_ms"] else np.ones(len(tt))
            newc = c + (0 - c) * ease
            out[idx[v]] = 440 * 2 ** ((n.midi - 69 + (newc + octave) / 100) / 12)
            fixes.append({"note": k, "error_cents": round(med, 1), "moved_cents": round(-med, 1)})
            continue
        shift = 0.0 if abs(med) <= 10 else -med * p["strength"]
        ease = np.clip(tt / max(p["retune_ms"] / 1000, 1e-3), 0, 1)
        newc = c + shift * ease
        if (n.end - n.start) > 0.3 and len(c) > int(0.5 / hop):
            # Slow drift: a 0.5 s moving average sits below 2 Hz; vibrato (4-8 Hz) averages out of it.
            w = int(0.5 / hop)
            slow = np.convolve(np.pad(c, (w // 2, w - w // 2 - 1), mode="edge"), np.ones(w) / w, mode="valid")
            newc = newc - 0.5 * (slow - med) * ease
        out[idx[v]] = 440 * 2 ** ((n.midi - 69 + (newc + octave) / 100) / 12)
        fixes.append({"note": k, "error_cents": round(med, 1), "moved_cents": round(shift, 1)})
    return out, fixes


def correct(x: np.ndarray, notes: list[Note], p: dict, report: dict) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Timing and pitch correction, one sung passage at a time (bounded memory), with PSOLA (your own
    voice, re-spaced; see `psola`). Returns (audio, f0 before, f0 after) with f0 on the 5 ms grid of song
    time."""
    f0_on, _ = track_f0(x, fast=True)
    f0_all, t_all = track_f0(x, fast=False)
    onsets_all = find_onsets(f0_on, t_all, 0.0, notes)
    corr, lateness, flagged = timing_targets(notes, onsets_all)
    report["lateness_ms"] = round(1000 * lateness, 1)
    report["timing_flagged"] = flagged
    report["timing_moved"] = sum(1 for c in corr if c)
    y = x.copy()
    f0_after = f0_all.copy()
    fixes_all = []
    for a, b in _passages(f0_all, t_all):
        ia, ib = int(a * SR), min(len(x), int(b * SR))
        seg = x[ia:ib].astype(np.float64)
        if len(seg) < SR // 10:
            continue
        sel = [k for k, n in enumerate(notes) if a <= n.start < b]
        if not sel:
            continue
        # This passage's pitch track (resampled to its frames).
        t = np.arange(int(len(seg) / SR / (FRAME_MS / 1000)) + 1) * FRAME_MS / 1000
        f0 = np.interp(t + a, t_all, f0_all)
        f0 = np.where(np.interp(t + a, t_all, (f0_all > 0).astype(float)) > 0.5, f0, 0.0)
        # Time map: output frame time -> input frame time.
        outs, ins = _warp_anchors([onsets_all[k] for k in sel], [corr[k] for k in sel], a, b)
        src_t = np.interp(t + a, outs, ins) - a
        fi = np.clip(src_t / (FRAME_MS / 1000), 0, len(t) - 1)
        i0 = np.floor(fi).astype(int)
        i1 = np.minimum(i0 + 1, len(t) - 1)
        w = fi - i0
        f0_w = np.where((f0[i0] > 0) & (f0[i1] > 0), f0[i0] * (1 - w) + f0[i1] * w, f0[np.round(fi).astype(int)])
        # Pitch: notes at their corrected onsets.
        on_new = [None if onsets_all[k] is None else onsets_all[k] - (corr[k] or 0.0) for k in sel]
        f0_new, fixes = pitch_curve(f0_w, t + a, [notes[k] for k in sel], on_new, p)
        for f in fixes:
            f["note"] = sel[f["note"]]
        fixes_all += fixes
        both = (f0_w > 0) & (f0_new > 0)
        shift_c = np.where(both, 1200 * np.log2(np.maximum(f0_new, 1e-6) / np.maximum(f0_w, 1e-6)), 0.0)
        if p["tune"] == "hard":  # the snap target is steady; keep the tracker's frame jitter out of the move
            shift_c = np.where(both, _run_median(np.where(both, shift_c, np.nan), both, 4), 0.0)
        timed = any(corr[k] for k in sel)
        samp_t = np.arange(len(seg)) / SR
        src_samples = (np.interp(samp_t + a, outs, ins) - a) * SR if timed else None
        y[ia:ib] = psola(seg, f0, 2 ** (shift_c / 1200), src_samples)
        fa, fb = np.searchsorted(t_all, [a, b])
        f0_after[fa:fb] = np.interp(t_all[fa:fb], t + a, f0_new)
        f0_after[fa:fb][np.interp(t_all[fa:fb], t + a, (f0_new > 0).astype(float)) < 0.5] = 0
    report["pitch_fixes"] = fixes_all
    report["onsets"] = onsets_all
    report["corrections"] = corr
    return y, f0_all, f0_after


def _passages(f0: np.ndarray, t: np.ndarray, gap: float = 0.3, pad: float = 0.12, max_len: float = 25.0):
    """Sung passages: voiced stretches separated by at least `gap` seconds of silence."""
    v = f0 > 0
    if not v.any():
        return []
    idx = np.flatnonzero(v)
    out = []
    a = idx[0]
    prev = idx[0]
    for i in idx[1:]:
        if t[i] - t[prev] > gap or t[i] - t[a] > max_len and t[i] - t[prev] > 0.06:
            out.append((max(0.0, t[a] - pad), t[prev] + pad))
            a = i
        prev = i
    out.append((max(0.0, t[a] - pad), t[prev] + pad))
    # Merge overlaps from the padding.
    merged = []
    for s, e in out:
        if merged and s <= merged[-1][1]:
            merged[-1] = (merged[-1][0], e)
        else:
            merged.append((s, e))
    return merged


# --------------------------------------------------------------------------------------------------
# Pitch shifting that keeps your voice (PSOLA)
# --------------------------------------------------------------------------------------------------
# Measured on the user's real takes (2026-10-15, VOCALS §13): WORLD resynthesis, even with no pitch change
# at all, made the level wobble -8 to +5 dB from one 5 ms frame to the next inside sung notes (the pitch
# tracker's jitter changes WORLD's spectral envelope) and about doubled the abrupt level jumps: that is the
# "choppy" tuning. PSOLA moves pitch by re-spacing the voice's own cycles, so consonants, breath and the
# top end are the recording itself, and a run that needs no change comes back sample for sample.

def _pitch_marks(seg: np.ndarray, f0: np.ndarray, hop_s: float) -> tuple[np.ndarray, np.ndarray]:
    """One mark per glottal cycle (source samples) in a voiced run, on the peaks of the signal low-passed
    just above f0, and the spacing from each mark to the next (the local period)."""
    from scipy.signal import butter, sosfiltfilt

    fmed = float(np.median(f0))
    P = SR / np.interp(np.arange(len(seg)) / SR, np.arange(len(f0)) * hop_s, np.clip(f0, fmed / 1.8, fmed * 1.8))
    lp = sosfiltfilt(butter(2, min(0.45 * SR, 1.5 * fmed), "low", fs=SR, output="sos"), seg) if len(seg) > 15 else seg
    first = int(P[0])
    if first >= len(lp):
        return np.zeros(0, dtype=int), np.zeros(0)
    marks = [int(np.argmax(lp[:first]))]
    while True:
        i = marks[-1]
        p = P[i]
        w = int(p * 0.2)
        lo, hi = max(i + 1, int(i + p) - w), min(len(lp), int(i + p) + w + 1)
        if lo >= hi:
            break
        marks.append(lo + int(np.argmax(lp[lo:hi])))
    marks = np.array(marks)
    spacing = np.diff(marks).astype(float)
    return marks, np.r_[spacing, spacing[-1:]] if len(spacing) else np.zeros(len(marks))


def psola(x: np.ndarray, f0: np.ndarray, ratio: np.ndarray, src: np.ndarray | None = None,
          min_cents: float = 1.0) -> np.ndarray:
    """Pitch (and optionally timing) change by pitch-synchronous overlap-add.
    `f0`: 5 ms frames of `x` (Hz, 0 = unvoiced). `ratio`: pitch factor per 5 ms frame of the OUTPUT.
    `src`: for each output sample, the source sample it comes from (a time map for timing correction);
    None keeps the timing. Unvoiced sounds are the original (time-mapped); voiced runs are rebuilt from
    two-period grains of the original and crossfaded in over 10 ms. Without a time map, a run that moves
    less than `min_cents` anywhere is left exactly as recorded."""
    x = np.asarray(x, dtype=np.float64)
    hop_s = FRAME_MS / 1000
    n_out = len(src) if src is not None else len(x)
    y = np.interp(src, np.arange(len(x)), x) if src is not None else x.copy()
    v = f0 > 0
    runs = np.flatnonzero(np.diff(np.r_[0, v.astype(int), 0])).reshape(-1, 2)
    fl = int(0.01 * SR)
    for a, b in runs:
        if b - a < 4:
            continue
        s0, s1 = int(a * hop_s * SR), min(len(x), int(b * hop_s * SR))
        if src is None:
            o0, o1 = s0, s1
            r_run = ratio[a:min(b, len(ratio))]
            if not len(r_run) or np.max(np.abs(np.log2(np.maximum(r_run, 1e-6)))) * 1200 < min_cents:
                continue
        else:
            o0, o1 = (int(i) for i in np.searchsorted(src, [s0, s1]))
        if o1 - o0 < 4 * fl // 10:
            continue
        marks, spacing = _pitch_marks(x[s0:s1], f0[a:b], hop_s)
        if len(marks) < 3:
            continue
        marks = marks + s0
        margin = int(spacing.max()) + 2
        out = np.zeros(o1 - o0 + 2 * margin)
        ws = np.zeros_like(out)
        R = np.interp((np.arange(o0, o1) + 0.5) / SR, np.arange(len(ratio)) * hop_s, ratio)
        t = float(marks[0] if src is None else np.searchsorted(src, marks[0]))
        while t < o1:
            ti = int(t)
            s = src[min(ti, n_out - 1)] if src is not None else t
            k = int(np.argmin(np.abs(marks - s)))
            m, p = int(marks[k]), max(2, int(spacing[k]))
            win = np.hanning(2 * p + 1)[:-1]
            g = np.zeros(2 * p)
            lo, hi = max(0, m - p), min(len(x), m + p)
            g[lo - (m - p):hi - (m - p)] = x[lo:hi]
            c = int(round(t)) - o0 + margin
            if 0 <= c - p and c + p <= len(out):
                out[c - p:c + p] += g * win
                ws[c - p:c + p] += win
            t += spacing[k] / max(0.25, R[min(max(ti - o0, 0), len(R) - 1)])
        z = np.where(ws > 0.15, out / np.maximum(ws, 1e-9), 0.0)[margin:margin + o1 - o0]
        cover = _movavg((ws[margin:margin + o1 - o0] > 0.15).astype(float), fl // 2)
        f = min(fl, (o1 - o0) // 4)
        fade = np.ones(o1 - o0)
        fade[:f] = np.linspace(0, 1, f)
        fade[-f:] = np.linspace(1, 0, f)
        w = fade * cover
        y[o0:o1] = w * z + (1 - w) * y[o0:o1]
    return y.astype(np.float32)


# --------------------------------------------------------------------------------------------------
# Breaths
# --------------------------------------------------------------------------------------------------

def tame_breaths(x: np.ndarray, f0: np.ndarray, noise_db: float, report: dict) -> np.ndarray:
    """Breaths: sounds of 120 ms to 1 s between sung notes, clearly above the room noise (+10 dB) and not
    hissy (an "s" has most of its energy above 4 kHz). Turned down 6 dB, or 4 dB when a phrase starts
    right after (within 250 ms), so the entry stays natural; never deleted (VOCALS §2)."""
    hop = int(FRAME_MS / 1000 * SR)
    v = np.repeat(f0 > 0, hop)[: len(x)]
    v = np.pad(v, (0, max(0, len(x) - len(v))))
    env_db = 20 * np.log10(_env(x, 20) + 1e-9)
    loud = (~v) & (env_db > noise_db + 10)
    hi = _filt(x, _sos("high", 4000, 2))
    gain = np.ones(len(x))
    count = 0
    n = len(x)
    i = 0
    while i < n:
        if not loud[i]:
            i += 1
            continue
        j = i
        while j < n and loud[j]:
            j += 1
        if int(0.12 * SR) <= j - i <= SR:
            seg = x[i:j].astype(np.float64)
            hiss = np.mean(hi[i:j].astype(np.float64) ** 2) / max(np.mean(seg ** 2), 1e-12)
            if hiss < 0.5:
                nxt = np.flatnonzero(v[j:j + int(0.25 * SR)])
                cut = 4.0 if len(nxt) else 6.0
                g = np.full(j - i, 10 ** (-cut / 20))
                f = min(int(0.01 * SR), (j - i) // 4)
                g[:f] = np.linspace(1, g[f], f)
                g[-f:] = np.linspace(g[-f - 1], 1, f)
                gain[i:j] = g
                count += 1
        i = j
    report["breaths_lowered"] = count
    if count:
        did(report, "Breaths", f"{count} turned down 4-6 dB")
    return (x * gain).astype(np.float32)


def phrase_gate(x: np.ndarray, report: dict, voiced: np.ndarray | None = None, ratio: float = 2.0,
                below_db: float = 15.0, depth_db: float = 18.0) -> np.ndarray:
    """Studio silence: a downward expander after compression. Anything more than `below_db` under the typical
    singing level is turned down at `ratio` (1:2: 6 dB under the threshold becomes 12 dB under), at most
    `depth_db`, following a 10 ms level with 3 ms attack and 120 ms release, so word endings fade naturally and
    the gaps between words get quieter too, not just between phrases.
    Measured on the user's takes (VOCALS §13): compression lifted the room between words from about 45 to 26 dB
    under the loudest singing; the reference vocals keep it 53-66 dB under."""
    from scipy.signal import lfilter

    x = np.asarray(x, dtype=np.float32)
    env = 20 * np.log10(_env(x, 10) + 1e-9)
    sung = voiced[: len(x)] if voiced is not None and voiced[: len(x)].sum() > SR // 2 else env > np.percentile(env, 99) - 30
    thr = float(np.median(env[sung])) - below_db
    gr = np.clip((thr - env) * (ratio - 1), 0, depth_db)  # dB of reduction wanted
    # fast to let go (3 ms) when you sing again, slow to close (120 ms) after a word
    a_dn, a_up = np.exp(-1 / (0.003 * SR)), np.exp(-1 / (0.12 * SR))
    fast = lfilter([1 - a_dn], [1, -a_dn], gr)
    slow = lfilter([1 - a_up], [1, -a_up], gr)
    gr = np.minimum(fast, slow)
    report["expander_mean_db"] = round(float(np.mean(gr)), 1)
    did(report, "Silence between words", f"room under {thr:.0f} dBFS turned down 1:{ratio:g}, up to {depth_db:.0f} dB")
    return (x * 10 ** (-gr / 20)).astype(np.float32)


# --------------------------------------------------------------------------------------------------
# The processing chain
# --------------------------------------------------------------------------------------------------

def _env(x: np.ndarray, ms: float) -> np.ndarray:
    w = max(1, int(ms / 1000 * SR))
    return np.sqrt(_movavg(x.astype(np.float64) ** 2, w))


def resonance(x: np.ndarray, voiced: np.ndarray) -> tuple[float, float]:
    """The strongest resonance in 200-500 Hz: (frequency, how far it sticks out in dB)."""
    from scipy.signal import welch

    seg = x[voiced] if voiced.sum() > SR // 2 else x
    f, pxx = welch(seg, SR, nperseg=8192)
    db = 10 * np.log10(pxx + 1e-20)
    k = 31
    smooth = np.convolve(np.pad(db, (k // 2, k // 2), mode="edge"), np.ones(k) / k, mode="valid")
    band = (f >= 200) & (f <= 500)
    i = np.argmax((db - smooth)[band])
    return float(f[band][i]), float((db - smooth)[band][i])


# The nine reference songs' separated vocals (docs/REFERENCE_ANALYSIS.md §4): median level of each band
# against 200-1000 Hz, in dB.
REF_TONE = {"3-6k": -18.4, "6-10k": -25.0, "10-16k": -28.2}
# Their median third-octave curve (dB against the 400-1000 Hz bands); only 250 Hz-12.5 kHz is used, where the nine
# vocals agree (25-75% spread 1.5-3 dB; below 250 Hz each song's high-pass differs by up to 25 dB).
REF_THIRDS = {250: 4.7, 315: 4.6, 400: 0.9, 500: -0.4, 630: 0.6, 800: 0.7, 1000: -2.2, 1250: -4.5, 1600: -6.4,
              2000: -8.6, 2500: -11.6, 3150: -12.9, 4000: -14.9, 5000: -22.7, 6300: -25.4, 8000: -22.4, 10000: -22.3,
              12500: -27.2}


def thirds(x: np.ndarray, voiced: np.ndarray | None = None) -> dict:
    """Third-octave band levels (dB) against the 400-1000 Hz bands, over the sung part."""
    from scipy.signal import welch

    y = x[voiced[: len(x)]] if voiced is not None and voiced[: len(x)].sum() > SR // 2 else x
    f, pw = welch(y.astype(np.float64), SR, nperseg=8192)
    lv = {c: 10 * np.log10(pw[(f >= c / 2 ** (1 / 6)) & (f < c * 2 ** (1 / 6))].mean() + 1e-20) for c in REF_THIRDS}
    ref = np.mean([lv[c] for c in (400, 500, 630, 800, 1000)])
    return {c: v - ref for c, v in lv.items()}


def mic_check(x: np.ndarray) -> str | None:
    """A warning when a take sounds like it was sung past the mic rather than into it: the top (3-6 kHz) well
    under the reference vocals while 1-2 kHz is not (dull and boxy). The user's chorus takes read like this;
    a side-address mic such as the QuadCast 2 is sung into from the side, not the top."""
    env = _env(x, 20)
    sung = env > env.max() * 0.1
    if sung.sum() < SR:
        return None
    th = thirds(x, sung)
    top = np.mean([th[c] - REF_THIRDS[c] for c in (3150, 4000, 5000)])
    mid = np.mean([th[c] - REF_THIRDS[c] for c in (1250, 1600, 2000)])
    if top < -7 and mid > top + 4:
        return ("This take sounds dull and boxy, as if sung past the mic: sing into the side of the mic with the "
                "logo (QuadCast: not into the top), 10-20 cm away.")
    return None


def match_eq_gains(x: np.ndarray, voiced: np.ndarray | None = None, amount: float = 0.8) -> dict:
    """Per third-octave band: the boost or cut (dB) that moves this vocal `amount` of the way to the
    reference curve, smoothed across neighbours, within ±6 dB (up to +8 dB from 8 kHz, where dark takes miss most)."""
    have = thirds(x, voiced)
    cs = list(REF_THIRDS)
    d = np.array([REF_THIRDS[c] - have[c] for c in cs])
    d = np.convolve(np.pad(d, 1, mode="edge"), [0.25, 0.5, 0.25], mode="valid")
    return {c: round(float(np.clip(v * amount, -6, 8 if c >= 8000 else 6)), 1) for c, v in zip(cs, d)}


def vocal_tone(x: np.ndarray, voiced: np.ndarray | None = None) -> dict:
    """Bands against 200-1000 Hz (dB), over the sung part when `voiced` is given."""
    from scipy.signal import welch

    y = x[voiced[: len(x)]] if voiced is not None and voiced[: len(x)].sum() > SR // 2 else x
    f, pw = welch(y.astype(np.float64), SR, nperseg=4096)
    ref = pw[(f >= 200) & (f < 1000)].mean() + 1e-20
    return {k: round(float(10 * np.log10(pw[(f >= lo) & (f < hi)].mean() / ref + 1e-20)), 1)
            for k, (lo, hi) in {"3-6k": (3000, 6000), "6-10k": (6000, 10000), "10-16k": (10000, 16000)}.items()}


def deess(x: np.ndarray, max_db: float, top: float = 0.15) -> tuple[np.ndarray, float]:
    """Split-band de-esser on 5-10 kHz: only the loudest ~15% of sibilant moments, up to `max_db`."""
    band = _filt(x, _sos("band", [5000, 10000], 2))
    env = _env(band, 5)
    whole = _env(x, 5)
    sib = env > 0.35 * whole  # moments where the hiss band dominates
    if sib.sum() < 50:
        return x, 0.0
    thr = np.quantile(env[sib], 1 - top)
    over = np.where(sib & (env > thr), 20 * np.log10(np.maximum(env, 1e-9) / thr), 0.0)
    gr = np.minimum(over, max_db)
    gr = _movavg(gr, int(0.003 * SR))
    g = 10 ** (-gr / 20)
    return (x - band + band * g).astype(np.float32), float(gr.max())


def _threshold(x: np.ndarray, voiced: np.ndarray, q: float) -> float:
    e = 20 * np.log10(_env(x, 50) + 1e-9)
    e = e[voiced] if voiced.sum() > SR // 4 else e
    return float(np.quantile(e, q))


def ride(x: np.ndarray, notes: list[Note], report: dict) -> np.ndarray:
    """Each line pulled toward the median line level, ±6 dB max, with 80 ms ramps."""
    lv = []
    ls = lines_of(notes)
    for a, b, _ in ls:
        seg = x[max(0, int(a * SR)):min(len(x), int(b * SR))]
        lv.append(_db(np.sqrt(np.mean(seg.astype(np.float64) ** 2))) if len(seg) > SR // 20 else None)
    vals = [v for v in lv if v is not None and v > -70]
    if len(vals) < 2:
        report["riding_db"] = []
        return x
    target = float(np.median(vals))
    gain_db = np.zeros(len(x))
    moves = []
    for (a, b, _), v in zip(ls, lv):
        if v is None or v <= -70:
            continue
        g = float(np.clip(target - v, -6, 6))
        moves.append(round(g, 1))
        ia, ib = max(0, int((a - 0.05) * SR)), min(len(x), int((b + 0.1) * SR))
        gain_db[ia:ib] = g
    k = int(0.08 * SR)
    gain_db = _movavg(gain_db, k)
    report["riding_db"] = moves
    return (x * 10 ** (gain_db / 20)).astype(np.float32)


def _saturate(x: np.ndarray, amount: float) -> np.ndarray:
    if amount <= 0:
        return x
    peak = np.abs(x).max() + 1e-9
    drive = 1 + 3 * amount
    wet = np.tanh(drive * x / peak) / np.tanh(drive) * peak
    return ((1 - amount) * x + amount * wet).astype(np.float32)


def _pitch_shift(x: np.ndarray, cents_: float) -> np.ndarray:
    from pedalboard import Pedalboard, PitchShift

    return Pedalboard([PitchShift(semitones=cents_ / 100)])(x[None, :].astype(np.float32), SR)[0]


def _shift(x: np.ndarray, ms: float) -> np.ndarray:
    k = int(ms / 1000 * SR)
    return np.concatenate([np.zeros(k, dtype=np.float32), x[: len(x) - k]]) if k > 0 else x


def _pan(x: np.ndarray, pan: float) -> np.ndarray:
    a = (pan + 1) * np.pi / 4
    return np.stack([x * np.cos(a), x * np.sin(a)]).astype(np.float32)


def _mask(x: np.ndarray, notes: list[Note], sections: set | None) -> np.ndarray:
    """1 inside the given sections' lines (all lines if None)."""
    m = np.zeros(len(x), dtype=np.float32)
    for n in notes:
        if sections is None or n.section in sections:
            m[max(0, int((n.start - 0.1) * SR)):min(len(x), int((n.end + 0.15) * SR))] = 1
    k = int(0.02 * SR)
    return _movavg(m, k).astype(np.float32)


def harmony_line(f0_after: np.ndarray, notes: list[Note], tonic: int, mode: str) -> np.ndarray:
    """Per 5 ms frame: the f0 a diatonic third above (in key)."""
    from . import theory

    scale = [(tonic + i) % 12 for i in theory.MODES.get(mode, theory.MODES["major"])]
    out = np.zeros_like(f0_after)
    hop = FRAME_MS / 1000
    for n in notes:
        a, b = int(n.start / hop), min(len(out), int((n.end + 0.1) / hop))
        pc = n.midi % 12
        if pc in scale:
            up = scale[(scale.index(pc) + 2) % len(scale)]
        else:
            up = (pc + 4) % 12
        semis = (up - pc) % 12
        out[a:b] = f0_after[a:b] * 2 ** (semis / 12)
    return out


def chain(dry: np.ndarray, notes: list[Note], f0_after: np.ndarray, p: dict, bpm: float, tonic: int, mode: str,
          hook: set, report: dict, take_sp=None) -> dict[str, np.ndarray]:
    """The 13-step chain (VOCALS §5) with the preset's deltas. Returns stereo layers: lead, doubles,
    harmony, space (reverb + delay)."""
    from pedalboard import (Compressor, Delay, HighShelfFilter, HighpassFilter, LowpassFilter, Pedalboard, PeakFilter,
                            Reverb)

    hop = int(FRAME_MS / 1000 * SR)
    voiced = np.repeat(f0_after > 0, hop)[: len(dry)]
    voiced = np.pad(voiced, (0, max(0, len(dry) - len(voiced))))
    x = dry.astype(np.float32)
    # 1 high-pass was applied in clean(). 2 clean-up EQ.
    f, prom = resonance(x, voiced)
    fx = []
    if prom > 2.0:
        fx.append(PeakFilter(cutoff_frequency_hz=f, gain_db=-min(4.0, 1 + prom / 2), q=4.0))
        report["resonance_cut"] = {"hz": round(f), "db": round(-min(4.0, 1 + prom / 2), 1)}
    if fx:
        x = Pedalboard(fx)(x[None], SR)[0]
        did(report, "Resonance cut", f"{report['resonance_cut']['db']} dB at {report['resonance_cut']['hz']} Hz")
    # 3 de-esser.
    gr = 0.0
    if p["deess_db"] > 0:
        x, gr = deess(x, p["deess_db"])
        if gr > 0.5:
            did(report, "De-esser", f"'s' sounds down up to {gr:.1f} dB")
    report["deess_max_db"] = round(gr, 1)
    # 4-5 two compressors (thresholds from the take's own levels, so the amount of compression is what we want).
    tb = _threshold(x, voiced, 0.5) - 6.0
    if p["compress"] > 0:
        k = p["compress"]
        ta = _threshold(x, voiced, 0.99) - 4.0 * k / (1 - 1 / p["comp_a"])
        x = Pedalboard([Compressor(threshold_db=ta, ratio=p["comp_a"], attack_ms=2, release_ms=50)])(x[None], SR)[0]
        # comp_b_db of levelling at the loud end of the singing (90th percentile), not at its middle: measured
        # against the reference vocals (VOCALS §13), levelling at the median squashed the quiet half 3 dB more
        # than theirs and brought the room between words up with it.
        tb = _threshold(x, voiced, 0.9) - p["comp_b_db"] * k / (1 - 1 / p["comp_b"])
        x = Pedalboard([Compressor(threshold_db=tb, ratio=p["comp_b"], attack_ms=20, release_ms=120)])(x[None], SR)[0]
        did(report, "Compression", f"peaks caught, then about {p['comp_b_db'] * k:.0f} dB of levelling")
    # 5b studio silence between words and phrases (after compression, which would bring the room back up)
    if p["gate"]:
        x = phrase_gate(x, report, voiced)
    # 6 presence + air (rock adds bite at 2 kHz), lo-fi band-pass instead of air.
    eq = [PeakFilter(cutoff_frequency_hz=3500, gain_db=p["presence_db"], q=0.8)] if p["presence_db"] else []
    if p["drive_bite"]:
        eq.append(PeakFilter(cutoff_frequency_hz=2000, gain_db=p["drive_bite"], q=1.0))
    if p["bandpass"]:
        eq += [HighpassFilter(p["bandpass"][0]), LowpassFilter(p["bandpass"][1])]
    elif p["air_db"]:
        eq.append(HighShelfFilter(cutoff_frequency_hz=11000, gain_db=p["air_db"], q=0.7))
    if eq:
        x = Pedalboard(eq)(x[None], SR)[0]
        did(report, "Brightness", "band-passed (lo-fi)" if p["bandpass"] else
            f"presence {p['presence_db']:+.1f} dB at 3.5 kHz, air {p['air_db']:+.1f} dB above 11 kHz")
    # 6b match EQ (docs/REFERENCE_ANALYSIS.md §4-5): third-octave bands from 250 Hz to 12.5 kHz moved toward the
    # nine reference vocals' median curve, where those vocals agree within about 3 dB. Not for lo-fi or flat EQ.
    if p["tone_match"] and not p["bandpass"] and (p["presence_db"] or p["air_db"]):
        gains = match_eq_gains(x, voiced)
        fx2 = [PeakFilter(cutoff_frequency_hz=c, gain_db=g, q=4.3) for c, g in gains.items() if abs(g) >= 0.5]
        if fx2:
            x = Pedalboard(fx2)(x[None], SR)[0]
            report["tone_match"] = gains
            up = {c: g for c, g in gains.items() if g >= 1.5}
            down = {c: g for c, g in gains.items() if g <= -1.5}
            fmt = lambda d: ", ".join(f"{c / 1000:g} kHz {g:+.0f}" if c >= 1000 else f"{c} Hz {g:+.0f}" for c, g in d.items())  # noqa: E731
            did(report, "Match EQ", "toward the reference vocals' tone" + (f"; up: {fmt(up)}" if up else "") +
                (f"; down: {fmt(down)}" if down else ""))
    # 7 saturation. 8 riding.
    if p["sat"] > 0:
        x = _saturate(x, p["sat"])
        did(report, "Warmth", f"saturation {p['sat']:.2f}")
    x = ride(x, notes, report)
    lead = _pan(x, 0.0)
    layers = {"lead": lead}
    # 9 doubles: synthetic ADT (+12 ms / +5 cents left, +19 ms / -5 cents right), -8 dB, ±30%.
    if p["doubles"]:
        m = _mask(x, notes, None if p["doubles"] == "all" else hook)
        g = 10 ** (p.get("double_db", -8) / 20)
        d1 = _shift(_pitch_shift(x, 5), 12) * m * g
        d2 = _shift(_pitch_shift(x, -5), 19) * m * g
        layers["doubles"] = _pan(d1, -0.3) + _pan(d2, 0.3)
        did(report, "Doubles", f"two copies of you left and right, {p.get('double_db', -8):.0f} dB")
        if p["octave_layer"]:
            layers["doubles"] += _pan(_pitch_shift(x, 1200) * m * p["octave_layer"], 0.0)
    # 10 harmonies: a third above on the hook, two voices at ±55%, -9 dB each, high-passed, de-essed harder.
    if p["harmony"] and take_sp is not None:
        m = _mask(x, notes, hook)
        if m.any():
            h = take_sp(harmony_line(f0_after, [n for n in notes if n.section in hook], tonic, mode))
            h = Pedalboard([HighpassFilter(180)])(h[None].astype(np.float32), SR)[0]
            h, _ = deess(h, 10.0)
            h = Pedalboard([Compressor(threshold_db=tb, ratio=p["comp_b"], attack_ms=20, release_ms=120)])(h[None], SR)[0]
            h = h * m * 10 ** (-9 / 20)
            layers["harmony"] = _pan(_shift(h, 8), -0.55) + _pan(_shift(_pitch_shift(h, 6), 15), 0.55)
            did(report, "Harmony", "a third above on the hook")
    # 11 reverb send (plate-ish), pre-delay, return band-limited. 12 delay send, ducked by the dry vocal.
    bus = layers["lead"] + layers.get("doubles", 0) + layers.get("harmony", 0)
    space = np.zeros_like(bus)
    if p["reverb"]:
        rv = Pedalboard([Reverb(room_size=p["room"], damping=0.45, wet_level=1.0, dry_level=0.0, width=1.0),
                         HighpassFilter(250), LowpassFilter(8000)])
        pre = np.stack([_shift(c, p["predelay_ms"]) for c in bus])
        wet = rv(pre * p["reverb"], SR)
        if p["shimmer"]:
            wet = wet + p["shimmer"] * np.stack([_pitch_shift(c, 1200) for c in wet])
        space += wet
        did(report, "Reverb", f"{p['decay_s']:.1f} s room, send {p['reverb']:.2f}")
    spb = 60.0 / bpm
    duck = 1 - 0.7 * np.clip(_env(x, 150) / (np.quantile(_env(x, 150)[voiced], 0.9) + 1e-9 if voiced.any() else 1), 0, 1)
    if p["delay"]:
        dl = Pedalboard([Delay(delay_seconds=p["delay_beats"] * spb, feedback=p.get("delay_feedback", 0.2), mix=1.0), HighpassFilter(300),
                         LowpassFilter(5000)])
        space += dl(bus * p["delay"], SR) * duck
        did(report, "Echo", f"{p['delay_beats']:g}-beat delay, send {p['delay']:.2f}")
        if p["throws"]:
            # A quarter-note "throw" on the last word of each line.
            tm = np.zeros(len(x), dtype=np.float32)
            for a, b, _ in lines_of(notes):
                tm[max(0, int((b - 0.35) * SR)):min(len(x), int(b * SR))] = 1
            th = Pedalboard([Delay(delay_seconds=spb, feedback=0.25, mix=1.0), HighpassFilter(300), LowpassFilter(5000)])
            space += th(lead * tm * 0.25, SR)
    if p["slap_ms"]:
        space += Pedalboard([Delay(delay_seconds=p["slap_ms"] / 1000, feedback=0.0, mix=1.0), HighpassFilter(300),
                             LowpassFilter(5000)])(bus * 0.18, SR)
    layers["space"] = space.astype(np.float32)
    return layers


# --------------------------------------------------------------------------------------------------
# Into the song
# --------------------------------------------------------------------------------------------------

def _lufs(x: np.ndarray) -> float:
    import pyloudnorm as pyln

    v = pyln.Meter(SR).integrated_loudness(x.T if x.ndim == 2 else x)
    return float(v) if np.isfinite(v) else -70.0


def sit_in_song(music: np.ndarray, vocal: np.ndarray, voice_env: np.ndarray, p: dict, lead: np.ndarray | None = None,
                lead_mode: str = "duck", report: dict | None = None, match_level: bool = True
                ) -> tuple[np.ndarray, np.ndarray, np.ndarray | None]:
    """Pre-master mix with the vocal: the vocal set `level_lu` against the music (measured while you
    sing), the music dipped up to 3 dB at 1-4 kHz under the voice, and the hummed lead ducked (or muted)
    while you sing. `music` excludes `lead`; both (2, n)."""
    report = report if report is not None else {}
    n = music.shape[1]
    vocal = vocal[:, :n] if vocal.shape[1] >= n else np.pad(vocal, ((0, 0), (0, n - vocal.shape[1])))
    env = voice_env[:n] if len(voice_env) >= n else np.pad(voice_env, (0, n - len(voice_env)))
    sung = env > 0.5
    full = music + (lead if lead is not None else 0)
    if match_level and sung.sum() > SR:
        m_l = _lufs(full[:, sung])
        v_l = _lufs(vocal[:, sung])
        g = m_l + p["level_lu"] - v_l
        vocal = vocal * 10 ** (g / 20)
        report["vocal_gain_db"] = round(g, 1)
        report["music_lufs_while_singing"] = round(m_l, 1)
    # The pocket: 1-4 kHz of the music dips up to 3 dB while you sing.
    band = np.stack([_filt(c, _sos("band", [1000, 4000], 2)) for c in music])
    dip = 1 - 10 ** (-3 * env / 20)
    music = music - band * dip
    if lead is not None:
        lg = {"duck": 10 ** (-12 / 20), "mute": 0.0, "keep": 1.0}[lead_mode]
        lead = lead * (1 - (1 - lg) * env)
        music = music + lead
    report["lead_while_singing"] = lead_mode
    return (music + vocal).astype(np.float32), vocal.astype(np.float32), lead


def envelope_from_audio(vocal: np.ndarray) -> np.ndarray:
    """voice_envelope for a finished vocal stem (no f0 at hand): sung where its level is within 30 dB
    of its loud parts."""
    mono = vocal.mean(axis=0) if vocal.ndim == 2 else vocal
    e = 20 * np.log10(_env(mono, 50) + 1e-9)
    if not np.isfinite(e).any() or e.max() < -80:
        return np.zeros(len(mono), dtype=np.float32)
    v = (e > np.quantile(e[e > -80], 0.95) - 30).astype(np.float32) if (e > -80).any() else np.zeros(len(mono))
    k = int(0.4 * SR)
    v = (_movavg(v, k) > 0.05).astype(np.float32)
    k = int(0.15 * SR)
    return _movavg(v, k).astype(np.float32)


def voice_envelope(f0_after: np.ndarray, n: int) -> np.ndarray:
    """1 while singing (with 150 ms ramps and short gaps bridged), else 0, per sample."""
    hop = int(FRAME_MS / 1000 * SR)
    v = np.repeat((f0_after > 0).astype(np.float32), hop)[:n]
    v = np.pad(v, (0, max(0, n - len(v))))
    k = int(0.4 * SR)
    v = (_movavg(v, k) > 0.05).astype(np.float32)
    k = int(0.15 * SR)
    return _movavg(v, k).astype(np.float32)


# --------------------------------------------------------------------------------------------------
# Quality gates (VOCALS §9)
# --------------------------------------------------------------------------------------------------

def quality(raw: np.ndarray, processed: np.ndarray, f0_before: np.ndarray, f0_after: np.ndarray, notes: list[Note],
            report: dict, noise_db: float) -> dict:
    t = np.arange(len(f0_after)) * FRAME_MS / 1000
    onsets = report.get("onsets") or [None] * len(notes)
    corr = report.get("corrections") or [None] * len(notes)
    new_on = [None if o is None else o - (c or 0.0) for o, c in zip(onsets, corr)]
    before = note_errors(f0_before, t, 0.0, notes, onsets)
    after = note_errors(f0_after, t, 0.0, notes, new_on)
    pb = [abs(e["pitch_cents"]) for e in before if e["pitch_cents"] is not None]
    pa = [abs(e["pitch_cents"]) for e in after if e["pitch_cents"] is not None]
    # Frames within ±25 cents, vibrato averaged out (200 ms), the 60 ms scoop at each start skipped.
    within = []
    hop = FRAME_MS / 1000
    for k, n in enumerate(notes):
        on = new_on[k] if new_on[k] is not None else n.start
        a, b = int((on + 0.06) / hop), min(len(f0_after), int(n.end / hop))
        seg = f0_after[a:b]
        seg = seg[seg > 0]
        if len(seg) < 8:
            continue
        c = _octave_fold(cents(seg, n.midi))
        w = min(len(c), int(0.2 / hop))
        c = np.convolve(c, np.ones(w) / w, mode="valid")
        within += list(np.abs(c) <= 25)
    lateness = report.get("lateness_ms", 0.0) / 1000
    tim = [abs(o - n.start - lateness) * 1000 for o, n in zip(new_on, notes) if o is not None]
    # Sibilance after processing: the loudest 5-10 kHz moments against the line's median level (all
    # frequencies, sung frames). Measured against the whole voice: the hiss band alone is near silent
    # during vowels, so its own median says nothing.
    band = _env(_filt(processed, _sos("band", [5000, 10000], 2)), 10)
    full = _env(processed, 10)
    sib = []
    for a, b, _ in lines_of(notes):
        ia, ib = max(0, int(a * SR)), min(len(band), int(b * SR))
        if ib - ia > SR // 10:
            loud = full[ia:ib][full[ia:ib] > full[ia:ib].max() * 0.05]
            sib.append(float(20 * np.log10(np.quantile(band[ia:ib], 0.995) + 1e-9)
                             - 20 * np.log10(np.median(loud) + 1e-9)))
    lines_db = []
    for a, b, _ in lines_of(notes):
        seg = processed[max(0, int(a * SR)):min(len(processed), int(b * SR))]
        if len(seg) > SR // 10:
            lines_db.append(_db(np.sqrt(np.mean(seg.astype(np.float64) ** 2))))
    silent = np.ones(len(processed), dtype=bool)
    for n in notes:
        silent[max(0, int((n.start - 0.6) * SR)):min(len(processed), int((n.end + 0.6) * SR))] = False
    proc_noise = _db(np.sqrt(np.mean(processed[silent].astype(np.float64) ** 2))) if silent.sum() > SR // 4 else None
    g = {
        "pitch_before_cents": round(float(np.median(pb)), 1) if pb else None,
        "pitch_after_cents": round(float(np.median(pa)), 1) if pa else None,
        "in_tune_frames": round(float(np.mean(within)), 3) if within else None,
        "timing_median_ms": round(float(np.median(tim)), 1) if tim else None,
        "timing_p95_ms": round(float(np.percentile(tim, 95)), 1) if tim else None,
        "sibilance_db": round(max(sib), 1) if sib else None,
        "line_spread_db": round(float(np.percentile(lines_db, 90) - np.percentile(lines_db, 10)), 1) if len(lines_db) > 1 else 0.0,
        "noise_raw_db": round(noise_db, 1),
        "noise_processed_db": round(proc_noise, 1) if proc_noise is not None else None,
        "clipped": bool(np.abs(raw).max() >= 10 ** (-0.1 / 20)),
        "missed_notes": sum(1 for o in onsets if o is None),
    }
    checks = []

    def add(ok, warn, text):
        checks.append({"level": "ok" if ok else ("warn" if warn else "bad"), "text": text})

    if g["pitch_after_cents"] is not None:
        v = g["pitch_after_cents"]
        add(v <= 15, v <= 30, f"Pitch: notes {v:.0f} cents off on average after tuning (was {g['pitch_before_cents']:.0f})")
    if g["timing_median_ms"] is not None:
        add(g["timing_median_ms"] < 30 and g["timing_p95_ms"] < 60, g["timing_median_ms"] < 45,
            f"Timing: {g['timing_median_ms']:.0f} ms typical, {g['timing_p95_ms']:.0f} ms worst")
    if g["sibilance_db"] is not None:
        add(g["sibilance_db"] <= 0, g["sibilance_db"] <= 4,
            f"'S' sounds: loudest {g['sibilance_db']:+.0f} dB against the singing" + (" (harsh)" if g["sibilance_db"] > 4 else ""))
    add(g["line_spread_db"] <= 2, g["line_spread_db"] <= 4, f"Lines within {g['line_spread_db']:.1f} dB of each other")
    add(noise_db < -60, noise_db < -50, f"Room noise {noise_db:.0f} dBFS")
    add(not g["clipped"], False, "No clipping in the recording" if not g["clipped"] else "The recording clipped: sing a bit further from the mic")
    if g["missed_notes"]:
        add(False, g["missed_notes"] <= max(1, len(notes) // 10), f"{g['missed_notes']} notes not found in the takes")
    g["checks"] = checks
    g["ok"] = all(c["level"] != "bad" for c in checks)
    return g


# --------------------------------------------------------------------------------------------------
# All together
# --------------------------------------------------------------------------------------------------

@dataclass
class Result:
    layers: dict  # stereo (2, n) per layer, song time
    dry: np.ndarray  # tuned and timed, before effects (mono)
    f0_after: np.ndarray
    report: dict = field(default_factory=dict)

    @property
    def stereo(self) -> np.ndarray:
        return sum(self.layers.values())


def produce(takes: list[Take], lead: list, bpm: float, sections: list[dict], tonic: int, mode: str,
            preset_name: str | None, length: float, choice: dict | None = None, hook: set | None = None,
            character: str = "natural", tweaks: dict | None = None) -> Result:
    """Takes in, a processed vocal out (song time, `length` seconds)."""
    p = tweak_preset(preset(preset_name), tweaks)
    notes = notes_in_seconds(lead, bpm, sections)
    if not notes:
        raise ValueError("this song has no melody to sing")
    report: dict = {"preset": p["name"], "preset_label": p["label"], "breaths_lowered": 0}
    scores = [score_take(tk, notes) for tk in takes]
    raw, picks, _ = comp(takes, notes, scores, length, choice)
    report["picks"] = {str(k): v for k, v in picks.items()}
    report["takes"] = {tk.id: sc for tk, sc in zip(takes, scores)}
    sung = [n for n in notes if n.line in picks]
    if not sung:
        raise ValueError("couldn't find your singing on the melody in these takes: check that the right mic is "
                         "picked (its meter should move), then sing the melody (words or \"la\") after the count-in")
    noise, noise_db = take_noise(takes, notes)
    report["noise_db"] = round(noise_db, 1)
    if p["raw"]:
        return _raw_result(raw, noise_db, report, tonic, mode)
    x = clean(raw, sung, noise, noise_db, report, p)
    y, f0_before, f0_after = correct(x, sung, p, report)
    did(report, "Timing and tuning", f"{report['timing_moved']} notes moved in time, " +
        ("snapped to the notes" if p["tune"] == "hard" else f"pitch pulled {round(p['strength'] * 100)}% toward the notes"))
    if p["breaths"]:
        y = tame_breaths(y, f0_after, noise_db, report)
    y, stack = apply_character(y, f0_after, character, report, tweaks=tweaks, scale=(tonic, mode))
    ch = character_spec(character, tweaks)
    if ch.get("octave") or ch.get("steps") or ch.get("stack") or ch.get("whisper") or ch.get("pa") or ch.get("harmony_voice"):
        p = dict(p, harmony=None)  # the harmony voice follows the plain pitch line; skip it for changed voices
    if hook is None:
        from .lyrics import is_hook

        hook = {sc["name"] for sc in sections if is_hook(sc["name"])}

    def synth_from(f0_target):
        """Resynthesise the corrected vocal on another pitch line (harmonies), passage by passage."""
        import pyworld as pw

        out = np.zeros(len(y), dtype=np.float32)
        t_all = np.arange(len(f0_after)) * FRAME_MS / 1000
        for pa, pb in _passages(f0_target, t_all):
            ia, ib = int(pa * SR), min(len(y), int(pb * SR))
            seg = y[ia:ib].astype(np.float64)
            if len(seg) < SR // 10:
                continue
            t = np.arange(int(len(seg) / SR / (FRAME_MS / 1000)) + 1) * FRAME_MS / 1000
            f0s = np.interp(t + pa, t_all, f0_after)
            f0s[np.interp(t + pa, t_all, (f0_after > 0).astype(float)) < 0.5] = 0
            sp = pw.cheaptrick(seg, f0s, t, SR)
            ap = pw.d4c(seg, f0s, t, SR)
            ft = np.interp(t + pa, t_all, f0_target) * (f0s > 0)
            h = pw.synthesize(ft, sp, ap, SR, FRAME_MS)[: len(seg)]
            out[ia:ia + len(h)] = h
        return out

    layers = chain(y, sung, f0_after, p, bpm, tonic, mode, hook, report, synth_from)
    if stack is not None:
        layers["stack"] = stack
    report["quality"] = quality(raw, layers["lead"][0] * np.sqrt(2), f0_before, f0_after, sung, report, noise_db)
    for k in ("onsets", "corrections"):
        report[k] = [None if v is None else round(float(v), 4) for v in report[k]]
    return Result(layers, y, f0_after, report)


# --------------------------------------------------------------------------------------------------
# Free singing and rap: vocals without a hummed melody to follow
# --------------------------------------------------------------------------------------------------
# When you sing your own tune over the song (or rap, or speak), there are no target notes. Then:
# - comping is per section: the most recent take that covers the whole section wins (re-record a
#   section to replace it), with a 30 ms crossfade at a quiet moment near the section change;
# - sung sections are tuned to the KEY: each moment's pitch is pulled toward the nearest note of the
#   scale (natural mode keeps vibrato and slides, eased over the preset's retune time; ±10 cents is left
#   alone), like a key-based tuner;
# - rap and spoken sections are not tuned at all, only cleaned and processed;
# - no timing correction (there's no grid of notes to correct against).

def _raw_result(raw: np.ndarray, noise_db: float, report: dict, tonic: int, mode: str,
                spans: list | None = None) -> Result:
    """The raw voice: the chosen takes spliced together exactly as recorded, centred. The only things
    that happen later are the level against the music and the timing nudge (Mixer.with_vocals)."""
    f0, _ = track_f0(raw, fast=True)  # only to know where you sing (level matching, the music's pocket)
    notes = phrase_notes(f0, spans or [])
    report.update({"character": "natural", "character_label": "Your voice (raw)", "raw": True,
                   "tuned_frames_moved_cents": 0.0, "breaths_lowered": 0, "timing_moved": 0})
    did(report, "Raw voice", "exactly as recorded: no clean-up, tuning, voice or effects")
    layers = {"lead": _pan(np.asarray(raw, dtype=np.float32), 0.0)}
    report["quality"] = quality_free(raw, raw, f0, notes, [], tonic, mode, noise_db)
    return Result(layers, np.asarray(raw, dtype=np.float32), f0, report)


def comp_sections(takes: list[Take], spans: list[tuple[str, float, float]], length: float,
                  choice: dict[str, str] | None = None) -> tuple[np.ndarray, dict[str, str]]:
    n = int(length * SR)
    owner = np.full(n, -1)
    picks: dict[str, str] = {}
    for name, a, b in spans:
        cands = [j for j, tk in enumerate(takes) if tk.t0 <= a + 0.1 and tk.end >= b - 0.1]
        if choice and name in choice:
            cands = [j for j, tk in enumerate(takes) if tk.id == choice[name]] or cands
        if not cands:  # partly covered: the take covering the most of it
            cov = [(min(b, tk.end) - max(a, tk.t0), j) for j, tk in enumerate(takes)]
            cov = [c for c in cov if c[0] > 0.5 * (b - a)]
            if not cov:
                continue
            cands = [max(cov)[1]]
        j = cands[-1]  # the newest
        picks[name] = takes[j].id
        lo = _quiet_point(takes[j], a - 0.25, a + 0.05) if a > 0.3 else max(a, takes[j].t0)
        hi = _quiet_point(takes[j], b - 0.05, b + 0.25)
        owner[max(0, int(lo * SR)):min(n, int(hi * SR))] = j
    return _fill(takes, owner, n, fade_s=0.03), picks


def _scale_target(midi: np.ndarray, tonic: int, mode: str) -> np.ndarray:
    from . import theory

    pcs = np.array(sorted({(tonic + i) % 12 for i in theory.MODES.get(mode, theory.MODES["major"])}))
    base = np.floor(midi)
    cands = []
    for o in (-12, 0, 12):
        for pc in pcs:
            cands.append(base - (base % 12) + pc + o)
    cands = np.stack(cands)
    idx = np.argmin(np.abs(cands - midi[None, :]), axis=0)
    return cands[idx, np.arange(len(midi))]


def tune_to_key(x: np.ndarray, tonic: int, mode: str, p: dict, keep: list[tuple[float, float]],
                report: dict) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Key-based pitch correction with PSOLA; `keep` = (start, end) song times left untouched (rap,
    spoken). Tuning off (strength 0) returns the audio exactly as it came in. Returns (audio, f0 before,
    f0 after) on the 5 ms grid."""
    f0_all, t_all = track_f0(x, fast=False)
    hard = p["tune"] == "hard"
    if not hard and p["strength"] <= 0:
        report["tuned_frames_moved_cents"] = 0.0
        return np.asarray(x, dtype=np.float32).copy(), f0_all, f0_all.copy()
    hop = FRAME_MS / 1000
    v = f0_all > 0
    held = np.zeros(len(f0_all), dtype=bool)
    for k0, k1 in keep:
        held |= (t_all >= k0) & (t_all < k1)
    m = np.full(len(f0_all), np.nan)
    m[v] = 69 + 12 * np.log2(f0_all[v] / 440)
    # The note being aimed at: a 150 ms running median of the contour, snapped to the scale.
    smooth = _run_median(m, v, int(0.15 / hop))
    target = m.copy()
    target[v] = _scale_target(smooth[v], tonic, mode)
    if hard:
        # Snap (vibrato and scoops flattened), against a 20 ms median so the tracker's jitter isn't copied.
        corr = np.where(v, target - _run_median(m, v, 4), 0.0)
    else:
        dev = np.where(v, target - smooth, 0.0)
        dev[np.abs(dev) * 100 <= 10] = 0.0
        corr = _movavg(dev * p["strength"], max(1, int(max(p["retune_ms"], 5) / 1000 / hop)))
    corr[~v | held] = 0.0
    y = psola(x, f0_all, 2 ** (corr / 12))
    f0_after = np.where(v, f0_all * 2 ** (corr / 12), 0.0)
    moved = np.abs(corr[v & ~held]) * 100
    report["tuned_frames_moved_cents"] = round(float(np.median(moved)), 1) if len(moved) else 0.0
    return y, f0_all, f0_after


def _run_median(m: np.ndarray, v: np.ndarray, w: int) -> np.ndarray:
    """Running median of a pitch contour inside each voiced run (never across silences)."""
    from scipy.ndimage import median_filter

    out = m.copy()
    idx = np.flatnonzero(v)
    if not len(idx):
        return out
    starts = np.r_[idx[0], idx[1:][np.diff(idx) > 1]]
    ends = np.r_[idx[:-1][np.diff(idx) > 1], idx[-1]] + 1
    for a, b in zip(starts, ends):
        out[a:b] = median_filter(m[a:b], size=max(1, min(w, b - a)), mode="nearest")
    return out


def phrase_notes(f0: np.ndarray, spans: list[tuple[str, float, float]]) -> list[Note]:
    """Stand-in "notes" for the processing chain (riding per phrase, doubles on the hook, delay throws
    on phrase ends): one per sung phrase, at its median pitch."""
    t = np.arange(len(f0)) * FRAME_MS / 1000
    out = []
    for i, (a, b) in enumerate(_passages(f0, t, gap=0.25, pad=0.0)):
        i0, i1 = np.searchsorted(t, [a, b])
        seg = f0[i0:i1]
        seg = seg[seg > 0]
        if len(seg) < 5:
            continue
        midi = int(round(69 + 12 * np.log2(np.median(seg) / 440)))
        name = next((nm for nm, s0, s1 in spans if s0 <= (a + b) / 2 < s1), "")
        out.append(Note(a, b, midi, i, name))
    return out


def produce_free(takes: list[Take], bpm: float, sections: list[dict], tonic: int, mode: str,
                 preset_name: str | None, length: float, section_modes: dict[str, str] | None = None,
                 choice: dict | None = None, hook: set | None = None, character: str = "natural",
                 stack_all: bool = False, tweaks: dict | None = None) -> Result:
    """Takes in, a processed vocal out, for singing without a melody to follow (and for rap)."""
    from .lyrics import is_hook

    p = tweak_preset(preset(preset_name), tweaks)
    p["harmony"] = None  # harmonies need real notes
    section_modes = section_modes or {}
    spb = 60.0 / bpm
    spans = [(sc["name"], sc["start"] * 4 * spb, (sc["start"] + sc["bars"]) * 4 * spb) for sc in sections]
    report: dict = {"preset": p["name"], "preset_label": p["label"], "mode": "free", "breaths_lowered": 0,
                    "timing_moved": 0}
    raw, picks = comp_sections(takes, spans, length, choice)
    # Gang and backing tracks: every other take is sung alongside the chosen one (real takes make width;
    # copies of one take don't).
    extra_takes = [tk for tk in takes if tk.id not in set(picks.values())] if stack_all else []
    if not picks:
        raise ValueError("none of the takes covers a whole section: record from the count-in to the end of the section")
    report["picks"] = picks
    noise, noise_db = take_noise(takes, [Note(a, b, 60) for _, a, b in spans])  # the count-in before a section
    report["noise_db"] = round(noise_db, 1)
    if p["raw"]:
        return _raw_result(raw, noise_db, report, tonic, mode, spans)
    x = _filt(raw, _sos("high", 100)) if p["highpass"] else np.asarray(raw, dtype=np.float32)
    if p["highpass"]:
        did(report, "Low cut", "below 100 Hz")
    x = denoise(x, noise, noise_db, p["denoise"], 100 if p["highpass"] else None, report)
    untuned = ("rap", "spoken", "whisper")
    keep = [(a, b) for nm, a, b in spans if section_modes.get(nm) in untuned]
    report["untuned_sections"] = [nm for nm, a, b in spans if section_modes.get(nm) in untuned]
    y, f0_before, f0_after = tune_to_key(x, tonic, mode, p, keep, report)
    if p["tune"] == "hard" or p["strength"] > 0:
        did(report, "Tuning to the key", ("snapped to the notes" if p["tune"] == "hard" else
            f"pulled {round(p['strength'] * 100)}% toward the notes, {p['retune_ms']} ms") +
            f"; median move {report['tuned_frames_moved_cents']} cents" +
            (f" (not tuned: {', '.join(report['untuned_sections'])})" if report["untuned_sections"] else ""))
    breaths = (lambda z, r: tame_breaths(z, f0_after, noise_db, r)) if p["breaths"] else (lambda z, r: z)
    y = breaths(y, report)
    if (character or "natural") != "natural" or clean_tweaks(tweaks):
        # rap/spoken parts keep their own pitch line; the character still applies to them
        y, stack = apply_character(y, f0_after, character, report, source=breaths(x, {}),
                                   tweaks=tweaks, scale=(tonic, mode))
    else:
        stack = None
        report["character"] = "natural"
    if extra_takes:
        st2 = stack_takes(extra_takes, spans, length, tonic, mode, p, keep)
        stack = st2 if stack is None else stack + st2
        report["stacked_takes"] = len(extra_takes)
    notes = phrase_notes(f0_after, spans)
    if not notes:
        raise ValueError("no singing found in the takes: check that the right mic is picked")
    hook = hook if hook is not None else {nm for nm, _, _ in spans if is_hook(nm)}
    layers = chain(y, notes, f0_after, p, bpm, tonic, mode, hook, report, None)
    if stack is not None:
        layers["stack"] = stack
    report["quality"] = quality_free(raw, layers["lead"][0] * np.sqrt(2), f0_after, notes, keep, tonic, mode, noise_db)
    return Result(layers, y, f0_after, report)


def quality_free(raw, processed, f0_after, notes, keep, tonic, mode, noise_db) -> dict:
    """The quality gates that make sense without target notes: in key (sung parts), 's' sounds, phrase
    levels, noise, clipping."""
    hop = FRAME_MS / 1000
    t = np.arange(len(f0_after)) * hop
    v = (f0_after > 0) & ~np.array([any(a <= x < b for a, b in keep) for x in t])
    in_key = None
    if v.sum() > 20:
        # Each moment's pitch with vibrato averaged out (200 ms median inside the sung run), skipping the
        # first 80 ms of each run (the scoop into a note), against the nearest note of the key.
        m = np.where(v, 69 + 12 * np.log2(np.maximum(f0_after, 1e-6) / 440), np.nan)
        sm = _run_median(m, v, int(0.2 / hop))
        settled = v.copy()
        run_start = np.flatnonzero(v & ~np.r_[False, v[:-1]])
        for a in run_start:
            settled[a:a + int(0.08 / hop)] = False
        if settled.sum() > 10:
            x = sm[settled]
            in_key = float(np.mean(np.abs(x - _scale_target(x, tonic, mode)) * 100 <= 25))
    band = _env(_filt(processed, _sos("band", [5000, 10000], 2)), 10)
    full = _env(processed, 10)
    sib, lines_db = [], []
    for a, b, _ in lines_of(notes):
        ia, ib = max(0, int(a * SR)), min(len(band), int(b * SR))
        if ib - ia > SR // 10:
            loud = full[ia:ib][full[ia:ib] > full[ia:ib].max() * 0.05]
            sib.append(float(20 * np.log10(np.quantile(band[ia:ib], 0.995) + 1e-9) - 20 * np.log10(np.median(loud) + 1e-9)))
            lines_db.append(_db(np.sqrt(np.mean(processed[ia:ib].astype(np.float64) ** 2))))
    g = {"in_key_frames": round(in_key, 3) if in_key is not None else None,
         "sibilance_db": round(max(sib), 1) if sib else None,
         "line_spread_db": round(float(np.percentile(lines_db, 90) - np.percentile(lines_db, 10)), 1) if len(lines_db) > 1 else 0.0,
         "noise_raw_db": round(noise_db, 1), "clipped": bool(np.abs(raw).max() >= 10 ** (-0.1 / 20))}
    checks = []

    def add(ok, warn, text):
        checks.append({"level": "ok" if ok else ("warn" if warn else "bad"), "text": text})

    if in_key is not None:
        add(in_key >= 0.85, in_key >= 0.7, f"Sung parts in key: {in_key * 100:.0f}% of the time")
    if g["sibilance_db"] is not None:
        add(g["sibilance_db"] <= 0, g["sibilance_db"] <= 4, f"'S' sounds: loudest {g['sibilance_db']:+.0f} dB against the singing")
    add(g["line_spread_db"] <= 3, g["line_spread_db"] <= 5, f"Phrases within {g['line_spread_db']:.1f} dB of each other")
    add(noise_db < -60, noise_db < -50, f"Room noise {noise_db:.0f} dBFS")
    add(not g["clipped"], False, "No clipping in the recording" if not g["clipped"] else "The recording clipped: sing a bit further from the mic")
    g["checks"] = checks
    g["ok"] = all(c["level"] != "bad" for c in checks)
    return g


# --------------------------------------------------------------------------------------------------
# Voice characters: one singer, many voices
# --------------------------------------------------------------------------------------------------
# WORLD splits a voice into pitch (f0), the spectral envelope (the shape of the mouth and throat: what
# makes a voice sound female, male, young or big) and aperiodicity (breath and noise). Changing them
# separately turns your takes into other characters while keeping your timing, words and tuning:
# - formant ratio: >1 moves the envelope up (smaller, brighter, more "female/young"), <1 down (bigger,
#   darker, more "male"); about 1.15-1.2 is the average adult female/male difference [S, U];
# - pitch: whole octaves only, so the melody stays in key with the music;
# - breath: more aperiodicity above 1 kHz; rasp: aperiodicity bursts plus pitch jitter; whisper: no
#   pitch at all (every frame unvoiced), which is what a whisper is;
# - stacks (gang, choir): several copies with different formants, tiny pitch and timing offsets, panned.
# Values are [U] engineering defaults; tune them by ear.

CHARACTERS = {
    "natural": {"label": "Your voice", "formant": 1.0},
    "female": {"label": "Female lead (an octave up, lighter tone)", "octave": 1, "formant": 1.17, "breath": 0.15},
    "female_low": {"label": "Female, same octave (alto)", "formant": 1.15, "breath": 0.1},
    "male_deep": {"label": "Deeper male (bigger, darker tone)", "formant": 0.88},
    "male_low": {"label": "Male, an octave down", "octave": -1, "formant": 0.92},
    "young": {"label": "Younger / brighter", "formant": 1.08},
    "raspy": {"label": "Raspy / gritty", "rasp": 0.45, "drive": 0.35},
    "breathy": {"label": "Breathy / soft", "breath": 0.45, "air_db": 2.0},
    "whisper": {"label": "Whisper", "whisper": True, "breath": 1.0, "formant": 1.05},
    "gang": {"label": "Gang shout (a crowd of you)", "drive": 0.3,
             "stack": [(0.92, -6, 0, -0.7), (0.97, 4, 11, -0.35), (1.04, -3, 19, 0.35), (1.09, 6, 27, 0.7),
                       (0.9, 0, 15, 0.0)]},
    "choir": {"label": "Choir (stacked voices, octave above and below)", "breath": 0.15,
              "stack": [(0.95, -5, 9, -0.6), (1.06, 5, 17, 0.6), (1.12, 0, 13, -0.3, 12), (0.9, 0, 21, 0.3, -12)]},
    "announcer": {"label": "Station announcer (PA speaker)", "pa": True},
}


def _warp_envelope(sp: np.ndarray, ratio: float) -> np.ndarray:
    if abs(ratio - 1.0) < 1e-3:
        return sp
    n = sp.shape[1]
    src = np.arange(n) / ratio
    out = np.empty_like(sp)
    for i in range(sp.shape[0]):
        out[i] = np.interp(src, np.arange(n), sp[i], right=sp[i, -1])
    return out


def world_passages(y: np.ndarray, f0: np.ndarray) -> list[tuple]:
    """WORLD analysis (envelope and aperiodicity) of each sung passage, done once and shared by every
    voice made from it: (start, end samples, frame times, f0, sp, ap, audio)."""
    import pyworld as pw

    hop = FRAME_MS / 1000
    t_all = np.arange(len(f0)) * hop
    out = []
    for a, b in _passages(f0, t_all, gap=0.3, pad=0.15):
        ia, ib = int(a * SR), min(len(y), int(b * SR))
        seg = y[ia:ib].astype(np.float64)
        if len(seg) < SR // 10:
            continue
        t = np.arange(int(len(seg) / SR / hop) + 1) * hop
        f = np.interp(t + a, t_all, f0)
        f[np.interp(t + a, t_all, (f0 > 0).astype(float)) < 0.5] = 0
        out.append((ia, ib, t, f, pw.cheaptrick(seg, f, t, SR), pw.d4c(seg, f, t, SR), seg))
    return out


def voice_variant(y: np.ndarray, f0: np.ndarray, *, formant: float = 1.0, octave: int = 0, cents: float = 0.0,
                  breath: float = 0.0, rasp: float = 0.0, whisper: bool = False, seed: int = 0,
                  analysis: list | None = None, steps: int = 0, scale: tuple | None = None) -> np.ndarray:
    """One re-voiced copy of the vocal, passage by passage with WORLD. `f0` is the 5 ms pitch track to
    sing (already tuned), in the time base of `y`. `steps` (with `scale` = (tonic, mode)): a harmony
    voice that many notes of the key away from each sung note (2 = a third above), keeping its bends."""
    import pyworld as pw

    rng = np.random.default_rng(seed)
    out = np.zeros(len(y), dtype=np.float32)
    shift = 2 ** (octave + cents / 1200)
    for ia, ib, t, f, sp, ap, seg in (analysis if analysis is not None else world_passages(y, f0)):
        f = f.copy()
        sp = _warp_envelope(sp, formant)
        freqs = np.linspace(0, SR / 2, sp.shape[1])
        if breath or whisper:
            k = np.clip((freqs - 1000) / 2000, 0, 1)[None, :] * min(1.0, breath)
            ap = 1 - (1 - ap) * (1 - k)
        if rasp:
            # Rough, uneven bursts of noise in the voice, and a little pitch jitter.
            burst = np.clip(rng.normal(0, 1, (len(t), 1)) * 0.5 + 0.5, 0, 1) * rasp
            ap = 1 - (1 - ap) * (1 - burst * np.clip((freqs - 600) / 1500, 0, 1)[None, :])
            f = f * (1 + rasp * 0.012 * rng.normal(0, 1, len(f)))
        f_new = np.zeros_like(f) if whisper else f * shift
        if steps and not whisper:
            f_new = f_new * (_harmony_ratio(f, steps, *scale) if scale is not None else 2 ** (steps / 7))
        if whisper:
            ap = np.ones_like(ap)
        z = pw.synthesize(np.ascontiguousarray(f_new), np.ascontiguousarray(sp), np.ascontiguousarray(ap), SR, FRAME_MS)
        z = z[: len(seg)]
        if len(z) < len(seg):
            z = np.pad(z, (0, len(seg) - len(z)))
        g = np.sqrt(np.mean(seg ** 2) / max(np.mean(z ** 2), 1e-12))
        fade = np.ones(len(seg))
        fl = min(int(0.01 * SR), len(seg) // 4)
        fade[:fl] = np.linspace(0, 1, fl)
        fade[-fl:] = np.linspace(1, 0, fl)
        out[ia:ib] += (z * g * fade).astype(np.float32)
    return out


def _aspirate(x: np.ndarray, f0: np.ndarray, amount: float, seed: int = 0) -> np.ndarray:
    """Breathiness without resynthesis: soft noise (1.5-9 kHz) that follows the voice's own 1-4 kHz
    envelope while you sing, about `amount` x 30% of the voice's level."""
    x = np.asarray(x, dtype=np.float32)
    hop = int(FRAME_MS / 1000 * SR)
    v = np.repeat(f0 > 0, hop)[: len(x)].astype(float)
    v = _movavg(np.pad(v, (0, max(0, len(x) - len(v)))), int(0.02 * SR))
    env = _env(_filt(x, _sos("band", [1000, 4000], 2)), 10)
    noise = _filt(np.random.default_rng(seed).normal(0, 1, len(x)).astype(np.float32), _sos("band", [1500, 9000], 2))
    noise = noise / (np.sqrt(np.mean(noise.astype(np.float64) ** 2)) + 1e-12)
    return (x + noise * env * v * 0.3 * min(1.0, amount)).astype(np.float32)


def _harmony_ratio(f: np.ndarray, steps: int, tonic: int, mode: str) -> np.ndarray:
    """Per frame: how far to move each sung note to land `steps` notes of the key away from it."""
    from . import theory

    sc = [(tonic + i) % 12 for i in theory.MODES.get(mode, theory.MODES["major"])]
    out = np.ones(len(f))
    v = f > 0
    if not v.any():
        return out
    m = 69 + 12 * np.log2(f[v] / 440.0)
    near = np.round(m).astype(int)
    tgt = np.empty_like(near)
    for i, n in enumerate(near):
        q = n
        while q % 12 not in sc:  # snap to the key first
            q -= 1
        k, d = abs(steps), 1 if steps > 0 else -1
        while k:
            q += d
            if q % 12 in sc:
                k -= 1
        tgt[i] = q - n
    # Smooth the move over ~60 ms so a glide between notes doesn't step.
    shift = tgt.astype(float)
    if len(shift) > 12:
        shift = _movavg(shift, 12)
    out[v] = 2 ** (shift / 12.0)
    return out


# Your own voice settings on top of a character (the "Voice tweaks" on the Sing screen). Each one only
# changes what you move; values are [U] defaults to tune by ear (docs/VOCALS.md §12).
TWEAKS = [
    {"id": "process", "label": "Processing", "group": "steps", "hint": "raw voice: your takes exactly as recorded, "
     "only set to the right level and place in the song (no clean-up, tuning, voice or effects)",
     "options": [["", "full vocal chain"], ["raw", "raw voice (exactly as recorded)"]]},
    {"id": "cleanup", "label": "Low cut (rumble, pops)", "group": "steps", "options": [["", "on"], ["off", "off"]]},
    {"id": "denoise", "label": "Noise reduction", "group": "steps", "hint": "removes steady room noise; "
     "stronger settings can make the voice watery", "options": [["", "light"], ["off", "off"], ["normal", "stronger"]]},
    {"id": "breaths", "label": "Breaths turned down", "group": "steps", "options": [["", "on"], ["off", "off"]]},
    {"id": "gate", "label": "Silence between words", "group": "steps", "hint": "turns the room sound down between "
     "your words and lines (up to 18 dB), like a studio vocal", "options": [["", "on"], ["off", "off"]]},
    {"id": "deess", "label": "De-esser ('s' sounds)", "group": "steps",
     "options": [["", "as the style sets it"], ["off", "off"], ["strong", "stronger"]]},
    {"id": "compress", "label": "Compression (evens loud and quiet)", "group": "steps",
     "options": [["", "as the style sets it"], ["off", "off"], ["light", "light"], ["strong", "strong"]]},
    {"id": "eq", "label": "Brightness (presence and air)", "group": "steps",
     "options": [["", "as the style sets it"], ["off", "off (flat)"], ["bright", "brighter"]]},
    {"id": "tonematch", "label": "Match EQ (reference vocals' tone)", "group": "steps", "hint": "moves each third-octave "
     "band toward the nine reference songs' vocals (within ±6 dB)", "options": [["", "on"], ["off", "off"]]},
    {"id": "pitch", "label": "Pitch (notes of the key)", "hint": "higher or lower by notes of the key, so it stays in key "
     "(7 = an octave)", "min": -7, "max": 7, "step": 1, "default": 0},
    {"id": "tone", "label": "Tone", "hint": "bigger and darker (left) or smaller and lighter (right); any change re-voices with WORLD, which softens detail", "min": -30,
     "max": 30, "step": 1, "default": 0},
    {"id": "breath", "label": "Breathiness", "min": 0, "max": 100, "step": 5, "default": 0},
    {"id": "grit", "label": "Grit / rasp", "hint": "re-voices with WORLD, which softens detail", "min": 0, "max": 100, "step": 5, "default": 0},
    {"id": "warmth", "label": "Warmth / drive", "min": 0, "max": 100, "step": 5, "default": 15},
    {"id": "tuning", "label": "Tuning", "options": [["", "as the style sets it"], ["off", "off (exactly as sung)"],
                                                   ["gentle", "gentle"], ["tight", "tight"], ["robot", "robot (hard snap)"]]},
    {"id": "double", "label": "Double (wider, thicker)", "min": 0, "max": 100, "step": 5, "default": 0},
    {"id": "harmony", "label": "Harmony voice", "options": [["", "none"], ["third_up", "a third above"],
                                                          ["fifth_up", "a fifth above"], ["third_down", "a third below"],
                                                          ["octave_up", "an octave above"], ["octave_down", "an octave below"]]},
    {"id": "echo", "label": "Echo", "min": 0, "max": 100, "step": 5, "default": 0},
    {"id": "space", "label": "Space (reverb)", "min": 0, "max": 100, "step": 5, "default": 40},
    {"id": "timing", "label": "Timing (ms)", "hint": "move this whole track earlier (left) or later (right) if it "
     "doesn't sit on the beat", "min": -400, "max": 400, "step": 10, "default": 0},
    {"id": "fx", "label": "Effect", "options": [["", "none"], ["radio", "old radio"], ["megaphone", "megaphone"],
                                               ["phone", "phone call"], ["robot", "robot"], ["tape", "lo-fi tape"]]},
]
HARMONY_STEPS = {"third_up": 2, "fifth_up": 4, "third_down": -2, "octave_up": 7, "octave_down": -7}
FX = ("radio", "megaphone", "phone", "robot", "tape")


def clean_tweaks(t: dict | None) -> dict:
    """Only known settings, clamped; anything left out keeps the character's and style's own value."""
    out: dict = {}
    for spec in TWEAKS:
        k = spec["id"]
        if not t or k not in t or t[k] in (None, ""):
            continue
        if "options" in spec:
            if t[k] in {o[0] for o in spec["options"]}:
                out[k] = t[k]
        else:
            try:
                out[k] = float(np.clip(float(t[k]), spec["min"], spec["max"]))
            except (TypeError, ValueError):
                pass
    return out


def tweak_preset(p: dict, t: dict | None) -> dict:
    """The style's processing with your tweaks on top: tuning, warmth, doubling, echo, space, tape."""
    t = clean_tweaks(t)
    p = dict(p)
    tuning = "robot" if t.get("fx") == "robot" else t.get("tuning")
    if tuning == "off":
        p["strength"], p["tune"] = 0.0, "natural"
    elif tuning == "gentle":
        p["strength"], p["retune_ms"], p["tune"] = 0.5, 60, "natural"
    elif tuning == "tight":
        p["strength"], p["retune_ms"], p["tune"] = 0.95, 20, "natural"
    elif tuning == "robot":
        p["strength"], p["retune_ms"], p["tune"] = 1.0, 0, "hard"
    if "warmth" in t:
        p["sat"] = t["warmth"] / 100 * 0.7
    if "double" in t:
        p["doubles"] = "all" if t["double"] > 0 else None
        p["double_db"] = -14 + 9 * t["double"] / 100  # -14 dB (a hint) to -5 dB (thick)
    if "echo" in t:
        p["delay"], p["delay_beats"], p["throws"] = t["echo"] / 100 * 0.35, 0.75, t["echo"] > 0 and p.get("throws", True)
        p["delay_feedback"] = 0.2 + 0.35 * t["echo"] / 100
    if "space" in t:
        v = t["space"] / 100
        p["reverb"], p["room"], p["decay_s"] = 0.45 * v, 0.35 + 0.55 * v, 0.6 + 2.6 * v
    if t.get("fx") == "tape":
        p["bandpass"], p["sat"] = (300, 4000), max(p.get("sat", 0.15), 0.4)
    # The processing switches.
    if t.get("process") == "raw":
        p["raw"] = True
    if t.get("cleanup") == "off":
        p["highpass"] = False
    if "denoise" in t:
        p["denoise"] = {"off": 0.0, "normal": 0.6}[t["denoise"]]
    if t.get("breaths") == "off":
        p["breaths"] = False
    if t.get("gate") == "off":
        p["gate"] = False
    if "deess" in t:
        p["deess_db"] = {"off": 0.0, "strong": 10.0}[t["deess"]]
    if "compress" in t:
        p["compress"] = {"off": 0.0, "light": 0.5, "strong": 1.5}[t["compress"]]
    if t.get("tonematch") == "off":
        p["tone_match"] = False
    if t.get("eq") == "off":
        p["presence_db"], p["air_db"], p["drive_bite"] = 0.0, 0.0, 0.0
    elif t.get("eq") == "bright":
        p["presence_db"], p["air_db"] = p["presence_db"] + 2.0, p["air_db"] + 2.5
    return p


def _fx(x: np.ndarray, fx: str) -> np.ndarray:
    """A whole-voice effect, level-matched: radio and megaphone are band-passed and distorted (the megaphone
    narrower and harder), phone is the telephone band, robot rings the voice against a 60 Hz tone."""
    from pedalboard import Distortion, PeakFilter, Pedalboard

    x = np.asarray(x, dtype=np.float32)
    if fx in ("radio", "megaphone", "phone"):
        lo, hi, drive, peak = {"radio": (400, 3200, 12, 1500), "megaphone": (650, 2800, 22, 1800),
                               "phone": (300, 3400, 8, 1100)}[fx]
        z = _filt(_filt(x, _sos("high", lo, 4)), _sos("low", hi, 4))
        z = Pedalboard([PeakFilter(cutoff_frequency_hz=peak, gain_db=5.0, q=0.8), Distortion(drive_db=drive)])(
            z[None].astype(np.float32), SR)[0]
    elif fx == "robot":
        t = np.arange(len(x)) / SR
        z = x * (0.35 + 0.65 * np.sin(2 * np.pi * 60 * t)).astype(np.float32)
    else:
        return x
    return (z * np.sqrt(np.mean(x.astype(np.float64) ** 2) / max(np.mean(z.astype(np.float64) ** 2), 1e-12))).astype(np.float32)


def character_spec(name: str | None, tweaks: dict | None = None) -> dict:
    """A character's settings with your tweaks applied (pitch, tone, breath, grit, harmony, effect)."""
    c = dict(CHARACTERS.get(name or "natural", CHARACTERS["natural"]))
    t = clean_tweaks(tweaks)
    if t.get("pitch"):
        c["steps"] = int(t["pitch"])
    if t.get("tone"):
        c["formant"] = c.get("formant", 1.0) * (1 + t["tone"] / 100)
    if "breath" in t:
        c["breath"] = max(c.get("breath", 0.0) if not t["breath"] else 0.0, t["breath"] / 100)
    if "grit" in t:
        c["rasp"] = t["grit"] / 100 * 0.7
        c["drive"] = max(c.get("drive", 0.0), t["grit"] / 100 * 0.3)
    if t.get("harmony"):
        c["harmony_voice"] = t["harmony"]
    if t.get("fx") in FX:
        c["fx"] = t["fx"]
    return c


def apply_character(y: np.ndarray, f0: np.ndarray, name: str, report: dict,
                    source: np.ndarray | None = None, tweaks: dict | None = None,
                    scale: tuple | None = None) -> tuple[np.ndarray, np.ndarray | None]:
    """(the main voice as the character, extra stacked voices as a stereo layer or None).
    `source`: the untuned audio, when it lines up with `f0` (free singing). Then pitch correction and the
    character happen in one WORLD pass: running WORLD twice adds artifacts."""
    c = character_spec(name, tweaks)
    report["character"] = name or "natural"
    report["character_label"] = c["label"]
    if tweaks:
        report["tweaks"] = clean_tweaks(tweaks)
    main = y
    src = source if source is not None else y
    # Only a new tone (formant), grit or a whisper needs WORLD; pitch moves go through PSOLA (your formants
    # stay where they are) and breathiness is shaped noise, so those tweaks keep the recording's detail.
    revoice = c.get("formant", 1.0) != 1.0 or c.get("rasp") or c.get("whisper")
    pitched = bool(c.get("octave") or c.get("steps")) and not revoice and not c.get("pa")
    needs = revoice or c.get("stack") or c.get("harmony_voice")
    analysis = world_passages(src, f0) if needs and not c.get("pa") else None
    if c.get("pa"):
        # A phone / PA speaker: 300-3400 Hz at 24 dB/octave, a lift near 1 kHz, then light distortion
        # after the EQ, level-matched.
        from pedalboard import Distortion, PeakFilter, Pedalboard

        band = _filt(_filt(y, _sos("high", 300, 4)), _sos("low", 3400, 4))
        main = Pedalboard([PeakFilter(cutoff_frequency_hz=1100, gain_db=4.0, q=0.7), Distortion(drive_db=10)])(
            band[None].astype(np.float32), SR)[0]
        main = (main * np.sqrt(np.mean(y ** 2) / max(np.mean(main ** 2), 1e-12))).astype(np.float32)
    elif revoice:
        main = voice_variant(src, f0, formant=c.get("formant", 1.0), octave=c.get("octave", 0),
                             breath=c.get("breath", 0.0), rasp=c.get("rasp", 0.0), whisper=c.get("whisper", False),
                             analysis=analysis, steps=c.get("steps", 0), scale=scale)
        if c.get("whisper"):
            from pedalboard import HighShelfFilter, Pedalboard

            main = Pedalboard([HighShelfFilter(cutoff_frequency_hz=4000, gain_db=3.0)])(main[None], SR)[0]
    else:
        f_main = f0
        if pitched:
            ratio = 2.0 ** c.get("octave", 0) * (_harmony_ratio(f0, c["steps"], *scale) if c.get("steps") and scale
                                                 else 2 ** (c.get("steps", 0) / 7))
            main = psola(y, f0, np.where(f0 > 0, ratio, 1.0))
            f_main = f0 * ratio
        if c.get("breath"):
            main = _aspirate(main, f_main, c["breath"])
    if c.get("drive"):
        main = _saturate(main, c["drive"])
    layer = None
    if c.get("stack"):
        layer = np.zeros((2, len(y)), dtype=np.float32)
        for i, v in enumerate(c["stack"]):
            ratio, cents_, ms, pan = v[:4]
            octv = (v[4] // 12) if len(v) > 4 else c.get("octave", 0)
            z = voice_variant(src, f0, formant=ratio * c.get("formant", 1.0), octave=octv, cents=cents_,
                              breath=c.get("breath", 0.0), rasp=c.get("rasp", 0.0), seed=i + 1, analysis=analysis,
                              steps=c.get("steps", 0), scale=scale)
            z = _filt(z, _sos("high", 180, 2))  # backing layers keep out of the low end
            if c.get("drive"):
                z = _saturate(z, c["drive"])
            layer += _pan(_shift(z, ms), pan) * 10 ** (-7 / 20)
        report["stack_voices"] = len(c["stack"])
    hv = c.get("harmony_voice")
    if hv and scale is not None and not c.get("whisper"):
        # A second you, singing a harmony that follows the key, a little to one side and under the lead.
        steps = HARMONY_STEPS[hv]
        z = voice_variant(src, f0, formant=c.get("formant", 1.0) * (1.03 if steps > 0 else 0.97),
                          octave=c.get("octave", 0), cents=4, breath=c.get("breath", 0.0), rasp=c.get("rasp", 0.0),
                          seed=11, analysis=analysis, steps=steps + c.get("steps", 0), scale=scale)
        z = _filt(z, _sos("high", 150, 2))
        if c.get("drive"):
            z = _saturate(z, c["drive"])
        h = _pan(_shift(z, 9), -0.35) * 10 ** (-6 / 20)
        layer = h if layer is None else layer + h
        report["harmony_voice"] = hv
    if c.get("fx"):
        main = _fx(main, c["fx"])
        if layer is not None:
            layer = np.stack([_fx(ch, c["fx"]) for ch in layer])
        report["fx"] = c["fx"]
    changed = [w for w, on in (("re-voiced with WORLD", revoice), ("pitch moved (PSOLA)", pitched),
                               ("breath added", c.get("breath") and not revoice), ("PA speaker", c.get("pa")), ("stacked voices", c.get("stack")),
                               ("harmony voice", hv), ("drive", c.get("drive")), (f"effect: {c.get('fx')}", c.get("fx"))) if on]
    if changed:
        did(report, "Voice", f"{c['label']}: {', '.join(changed)}")
    return main.astype(np.float32), layer


def stack_takes(takes: list[Take], spans: list, length: float, tonic: int, mode: str, p: dict,
                keep: list) -> np.ndarray:
    """The other takes of a gang / backing track as a wide stack: each tuned to the key (unless rap or
    spoken), high-passed, compressed, panned alternately left and right, a few dB under the lead."""
    from pedalboard import Compressor, Pedalboard

    n = int(length * SR)
    out = np.zeros((2, n), dtype=np.float32)
    pans = [-0.75, 0.75, -0.45, 0.45, -0.9, 0.9]
    for i, tk in enumerate(takes):
        raw, picks = comp_sections([tk], spans, length)
        if not picks:
            continue
        x = _filt(raw, _sos("high", 180, 2))
        y, _, _ = tune_to_key(x, tonic, mode, p, keep, {})
        y = Pedalboard([Compressor(threshold_db=-24, ratio=4, attack_ms=5, release_ms=100)])(y[None].astype(np.float32), SR)[0]
        y = y * 10 ** (-5 / 20)
        out += _pan(y[:n], pans[i % len(pans)])
    return out


def preview(take: Take, tonic: int, mode: str, preset_name: str | None, character: str = "natural",
            tweaks: dict | None = None, seconds: float = 8.0, untuned: bool = False, with_start: bool = False):
    """A few seconds of one take as a character with your tweaks, without the band (for trying voices
    quickly): from the first sung sound, tuned to the key (unless `untuned`, for rap and spoken parts),
    re-voiced, with the style's drive and a quick reverb and echo. Stereo float32 at SR (and, with
    `with_start`, the song time it starts at)."""
    from pedalboard import Delay, Pedalboard, Reverb

    x = np.asarray(take.audio, dtype=np.float32)
    env = _env(x, 20)
    on = np.flatnonzero(env > max(float(env.max()) * 0.1, 1e-4))
    i0 = max(0, int(on[0]) - int(0.1 * SR)) if len(on) else 0
    p = tweak_preset(preset(preset_name), tweaks)
    seg = x[i0:i0 + int(seconds * SR)]
    if len(seg) < SR // 4:
        raise ValueError("that take is too short to preview")
    if p["raw"]:  # exactly as recorded, only brought up to a listening level
        out = _pan(seg, 0.0)
        out = (out / (float(np.abs(out).max()) or 1.0) * 0.89).astype(np.float32)
        return (out, take.t0 + i0 / SR) if with_start else out
    if p["highpass"]:
        seg = _filt(seg, _sos("high", 100))
    keep = [(0.0, len(seg) / SR + 1)] if untuned else []
    y, _, f0 = tune_to_key(seg, tonic, mode, p, keep, {})
    main, layer = apply_character(y, f0, character, {}, source=seg, tweaks=tweaks, scale=(tonic, mode))
    main = _saturate(main, p["sat"])
    if p.get("bandpass"):
        main = _filt(_filt(main, _sos("high", p["bandpass"][0], 2)), _sos("low", p["bandpass"][1], 2))
    out = _pan(main, 0.0)
    if p["doubles"]:
        g = 10 ** (p.get("double_db", -8) / 20)
        out = out + _pan(_shift(_pitch_shift(main, 5), 12) * g, -0.3) + _pan(_shift(_pitch_shift(main, -5), 19) * g, 0.3)
    if layer is not None:
        out = out + layer[:, :out.shape[1]]
    fx = []
    if p["reverb"]:
        fx.append(Reverb(room_size=p["room"], damping=0.45, wet_level=min(1.0, p["reverb"] * 1.6), dry_level=1.0))
    if p["delay"]:
        fx.append(Delay(delay_seconds=0.375, feedback=p.get("delay_feedback", 0.2), mix=min(0.5, p["delay"] * 1.2)))
    if fx:
        out = Pedalboard(fx)(out.astype(np.float32), SR)
    pk = float(np.abs(out).max()) or 1.0
    out = (out / pk * 0.89).astype(np.float32)
    return (out, take.t0 + i0 / SR) if with_start else out


def shift_ms(x: np.ndarray, ms: float) -> np.ndarray:
    """Move audio (mono or stereo, song time) later by `ms` (earlier if negative), keeping its length."""
    k = int(round(ms / 1000 * SR))
    if k == 0:
        return x
    out = np.zeros_like(x)
    if k > 0:
        out[..., k:] = x[..., :-k]
    else:
        out[..., :k] = x[..., -k:]
    return out
