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

def track_f0(x: np.ndarray, sr: int = SR, fast: bool = True) -> tuple[np.ndarray, np.ndarray]:
    """f0 (Hz, 0 = unvoiced) every 5 ms, analysed at 16 kHz. Voicing (and so note onsets) always comes
    from DIO + StoneMask: Harvest smears voicing 20-150 ms into the consonants before a note (measured
    on synthetic singing). With fast=False the pitch values come from Harvest where both agree a frame
    is voiced (Harvest has fewer octave slips, which WORLD resynthesis would turn into glitches)."""
    import librosa
    import pyworld as pw

    y = librosa.resample(np.asarray(x, dtype=np.float32), orig_sr=sr, target_sr=16000).astype(np.float64)
    f0, t = pw.dio(y, 16000, f0_floor=70, f0_ceil=1100, frame_period=FRAME_MS)
    f0 = pw.stonemask(y, f0, t, 16000)
    if not fast:
        fh, _ = pw.harvest(y, 16000, f0_floor=70, f0_ceil=1100, frame_period=FRAME_MS)
        m = min(len(fh), len(f0))
        f0[:m] = np.where((f0[:m] > 0) & (fh[:m] > 0), fh[:m], f0[:m])
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
    if not covered:
        return {"lines": {}, "score": 0.0, "notes": 0}
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
    # Fill each run from its take, crossfading 5 ms at every change of owner.
    fade = int(0.005 * SR)
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
    # Room noise for the profile: the first take's lead-in before its first note.
    first = min(takes, key=lambda tk: tk.t0)
    return out, picks, first.t0


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


def take_noise(takes: list[Take], notes: list[Note]) -> tuple[np.ndarray, float]:
    """The room noise: the longest lead-in (the count-in, before the first sung note) of any take."""
    best = np.zeros(1, dtype=np.float32)
    for tk in takes:
        first = min((n.start for n in notes if n.start >= tk.t0), default=tk.end)
        seg = tk.audio[: max(0, int((first - 0.4 - tk.t0) * SR))]
        if len(seg) > len(best):
            best = seg
    if len(best) < SR // 10:  # no lead-in: the quietest 250 ms of the first take
        x = takes[0].audio
        w = SR // 4
        e = np.convolve(x.astype(np.float64) ** 2, np.ones(w) / w, mode="valid")
        i = int(np.argmin(e)) if len(e) else 0
        best = x[i:i + w]
    return best, _db(np.sqrt(np.mean(best.astype(np.float64) ** 2)) + 1e-12)


def clean(x: np.ndarray, notes: list[Note], noise: np.ndarray, noise_db: float, report: dict) -> np.ndarray:
    """High-pass, noise reduction from the pre-roll (VOCALS §2), plosive pops near onsets."""
    lowest = min(n.midi for n in notes)
    hp = float(np.clip(0.7 * 440 * 2 ** ((lowest - 69) / 12), 70, 150))
    y = _filt(x, _sos("high", hp))
    report["highpass_hz"] = round(hp)
    if noise_db > -65 and len(noise) > SR // 10:
        import noisereduce as nr

        # prop_decrease 0.6 is about 8 dB of reduction: enough to lift the room, too little for "musical noise".
        y = nr.reduce_noise(y=y, sr=SR, y_noise=_filt(noise, _sos("high", hp)), stationary=True,
                            prop_decrease=0.6, n_fft=2048).astype(np.float32)
        report["noise_reduction_db"] = 8
    else:
        report["noise_reduction_db"] = 0
    y, pops = fix_plosives(y, notes)
    report["plosives_fixed"] = pops
    return y


def fix_plosives(x: np.ndarray, notes: list[Note]) -> tuple[np.ndarray, int]:
    """A burst under 150 Hz more than 10 dB above the line's average, within 40 ms of an onset, gets a
    60 ms high-pass at 120 Hz with 10 ms fades."""
    low = _filt(x, _sos("low", 150, 2))
    w = int(0.01 * SR)
    env = np.sqrt(np.convolve(low.astype(np.float64) ** 2, np.ones(w) / w, mode="same"))
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
    """Timing and pitch correction, one sung passage at a time (bounded memory). Returns (audio, f0 before,
    f0 after) with f0 on the 5 ms grid of song time."""
    import pyworld as pw

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
        # WORLD analysis of this passage, with the f0 track we already have (resampled to its frames).
        t = np.arange(int(len(seg) / SR / (FRAME_MS / 1000)) + 1) * FRAME_MS / 1000
        f0 = np.interp(t + a, t_all, f0_all)
        f0 = np.where(np.interp(t + a, t_all, (f0_all > 0).astype(float)) > 0.5, f0, 0.0)
        sp = pw.cheaptrick(seg, f0, t, SR)
        ap = pw.d4c(seg, f0, t, SR)
        # Time map: output frame time -> input frame time.
        outs, ins = _warp_anchors([onsets_all[k] for k in sel], [corr[k] for k in sel], a, b)
        src_t = np.interp(t + a, outs, ins) - a
        fi = np.clip(src_t / (FRAME_MS / 1000), 0, len(t) - 1)
        i0 = np.floor(fi).astype(int)
        i1 = np.minimum(i0 + 1, len(t) - 1)
        w = (fi - i0)[:, None]
        sp_w = sp[i0] * (1 - w) + sp[i1] * w
        ap_w = ap[i0] * (1 - w) + ap[i1] * w
        f0_w = np.where((f0[i0] > 0) & (f0[i1] > 0), f0[i0] * (1 - w[:, 0]) + f0[i1] * w[:, 0], f0[np.round(fi).astype(int)])
        # Pitch: notes at their corrected onsets.
        on_new = [None if onsets_all[k] is None else onsets_all[k] - (corr[k] or 0.0) for k in sel]
        f0_new, fixes = pitch_curve(f0_w, t + a, [notes[k] for k in sel], on_new, p)
        for f in fixes:
            f["note"] = sel[f["note"]]
        fixes_all += fixes
        world = pw.synthesize(np.ascontiguousarray(f0_new), np.ascontiguousarray(sp_w), np.ascontiguousarray(ap_w),
                              SR, FRAME_MS)[: len(seg)]
        if len(world) < len(seg):
            world = np.pad(world, (0, len(seg) - len(world)))
        # Consonants and breaths from the original (time-mapped), voiced sounds from WORLD.
        samp_t = np.arange(len(seg)) / SR
        src_samples = (np.interp(samp_t + a, outs, ins) - a) * SR
        orig = np.interp(src_samples, np.arange(len(seg)), seg)
        vmask = np.interp(samp_t, t, (f0_new > 0).astype(float))
        k = int(0.01 * SR)
        vmask = np.convolve(vmask, np.ones(k) / k, mode="same")
        # Match WORLD's level to the original's in voiced parts.
        vv = vmask > 0.9
        if vv.sum() > SR // 20:
            world *= np.sqrt(np.mean(orig[vv] ** 2) / max(np.mean(world[vv] ** 2), 1e-12))
        y[ia:ib] = (vmask * world + (1 - vmask) * orig).astype(np.float32)
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
    return (x * gain).astype(np.float32)


# --------------------------------------------------------------------------------------------------
# The processing chain
# --------------------------------------------------------------------------------------------------

def _env(x: np.ndarray, ms: float) -> np.ndarray:
    w = max(1, int(ms / 1000 * SR))
    return np.sqrt(np.convolve(x.astype(np.float64) ** 2, np.ones(w) / w, mode="same"))


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
    gr = np.convolve(gr, np.ones(int(0.003 * SR)) / int(0.003 * SR), mode="same")
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
    gain_db = np.convolve(np.pad(gain_db, (k // 2, k - k // 2 - 1), mode="edge"), np.ones(k) / k, mode="valid")
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
    return np.convolve(m, np.ones(k) / k, mode="same").astype(np.float32)


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
    # 3 de-esser.
    x, gr = deess(x, p["deess_db"])
    report["deess_max_db"] = round(gr, 1)
    # 4-5 two compressors (thresholds from the take's own levels, so the amount of compression is what we want).
    ta = _threshold(x, voiced, 0.99) - 4.0 / (1 - 1 / p["comp_a"])
    x = Pedalboard([Compressor(threshold_db=ta, ratio=p["comp_a"], attack_ms=2, release_ms=50)])(x[None], SR)[0]
    tb = _threshold(x, voiced, 0.5) - p["comp_b_db"] / (1 - 1 / p["comp_b"])
    x = Pedalboard([Compressor(threshold_db=tb, ratio=p["comp_b"], attack_ms=20, release_ms=120)])(x[None], SR)[0]
    # 6 presence + air (rock adds bite at 2 kHz), lo-fi band-pass instead of air.
    eq = [PeakFilter(cutoff_frequency_hz=3500, gain_db=p["presence_db"], q=0.8)]
    if p["drive_bite"]:
        eq.append(PeakFilter(cutoff_frequency_hz=2000, gain_db=p["drive_bite"], q=1.0))
    if p["bandpass"]:
        eq += [HighpassFilter(p["bandpass"][0]), LowpassFilter(p["bandpass"][1])]
    elif p["air_db"]:
        eq.append(HighShelfFilter(cutoff_frequency_hz=11000, gain_db=p["air_db"], q=0.7))
    x = Pedalboard(eq)(x[None], SR)[0]
    # 7 saturation. 8 riding.
    x = _saturate(x, p["sat"])
    x = ride(x, notes, report)
    lead = _pan(x, 0.0)
    layers = {"lead": lead}
    # 9 doubles: synthetic ADT (+12 ms / +5 cents left, +19 ms / -5 cents right), -8 dB, ±30%.
    if p["doubles"]:
        m = _mask(x, notes, None if p["doubles"] == "all" else hook)
        g = 10 ** (-8 / 20)
        d1 = _shift(_pitch_shift(x, 5), 12) * m * g
        d2 = _shift(_pitch_shift(x, -5), 19) * m * g
        layers["doubles"] = _pan(d1, -0.3) + _pan(d2, 0.3)
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
    spb = 60.0 / bpm
    duck = 1 - 0.7 * np.clip(_env(x, 150) / (np.quantile(_env(x, 150)[voiced], 0.9) + 1e-9 if voiced.any() else 1), 0, 1)
    if p["delay"]:
        dl = Pedalboard([Delay(delay_seconds=p["delay_beats"] * spb, feedback=0.2, mix=1.0), HighpassFilter(300),
                         LowpassFilter(5000)])
        space += dl(bus * p["delay"], SR) * duck
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
    v = (np.convolve(v, np.ones(k) / k, mode="same") > 0.05).astype(np.float32)
    k = int(0.15 * SR)
    return np.convolve(v, np.ones(k) / k, mode="same").astype(np.float32)


def voice_envelope(f0_after: np.ndarray, n: int) -> np.ndarray:
    """1 while singing (with 150 ms ramps and short gaps bridged), else 0, per sample."""
    hop = int(FRAME_MS / 1000 * SR)
    v = np.repeat((f0_after > 0).astype(np.float32), hop)[:n]
    v = np.pad(v, (0, max(0, n - len(v))))
    k = int(0.4 * SR)
    v = (np.convolve(v, np.ones(k) / k, mode="same") > 0.05).astype(np.float32)
    k = int(0.15 * SR)
    return np.convolve(v, np.ones(k) / k, mode="same").astype(np.float32)


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
            preset_name: str | None, length: float, choice: dict | None = None, hook: set | None = None) -> Result:
    """Takes in, a processed vocal out (song time, `length` seconds)."""
    p = preset(preset_name)
    notes = notes_in_seconds(lead, bpm, sections)
    if not notes:
        raise ValueError("this song has no melody to sing")
    report: dict = {"preset": p["name"], "preset_label": p["label"]}
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
    x = clean(raw, sung, noise, noise_db, report)
    y, f0_before, f0_after = correct(x, sung, p, report)
    y = tame_breaths(y, f0_after, noise_db, report)
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
    report["quality"] = quality(raw, layers["lead"][0] * np.sqrt(2), f0_before, f0_after, sung, report, noise_db)
    for k in ("onsets", "corrections"):
        report[k] = [None if v is None else round(float(v), 4) for v in report[k]]
    return Result(layers, y, f0_after, report)
