"""Synthetic test audio.

The build sessions have no microphone, so every stage is tested against generated sounds whose right
answer is known: hums (with human wobble, drift and off-pitch notes), beatbox, talking and typing.
The same helpers render cleaned results back to audio as a rough preview.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

SR = 16000


@dataclass
class TrueNote:
    onset: float  # seconds
    duration: float  # seconds
    midi: int


def midi_to_hz(m):
    return 440.0 * 2.0 ** ((np.asarray(m, dtype=float) - 69.0) / 12.0)


def _beat_times(n_beats: float, bpm: float, drift: float) -> callable:
    """Return beat -> seconds for a tempo that changes linearly by `drift` (0.05 = 5% faster at the end)."""
    total = n_beats

    def to_sec(b):
        b = np.asarray(b, dtype=float)
        # Tempo at beat b: bpm * (1 + drift * b / total); integrate dt = 60 / tempo.
        if abs(drift) < 1e-9:
            return b * 60.0 / bpm
        k = drift / total
        return 60.0 / (bpm * k) * np.log1p(k * b)

    return to_sec


def hum(
    notes: list[tuple[int, float]],
    bpm: float = 96.0,
    sr: int = SR,
    *,
    drift: float = 0.0,
    detune_cents: float = 25.0,
    global_offset_cents: float = 0.0,
    vibrato_cents: float = 18.0,
    timing_jitter: float = 0.015,
    gap_beats: float = 0.08,
    noise_db: float = -45.0,
    seed: int = 0,
    lead_in: float = 0.5,
    tail: float = 0.6,
) -> tuple[np.ndarray, list[TrueNote]]:
    """A hummed melody. `notes` is [(midi, beats)], with midi < 0 meaning a rest."""
    rng = np.random.default_rng(seed)
    n_beats = sum(b for _, b in notes)
    to_sec = _beat_times(n_beats, bpm, drift)
    total = lead_in + float(to_sec(n_beats)) + tail
    n = int(total * sr)
    t = np.arange(n) / sr
    f0 = np.zeros(n)
    amp = np.zeros(n)
    truth: list[TrueNote] = []
    beat = 0.0
    for midi, beats in notes:
        start = lead_in + float(to_sec(beat)) + rng.normal(0, timing_jitter)
        end = lead_in + float(to_sec(beat + beats - gap_beats))
        beat += beats
        if midi < 0:
            continue
        start = max(start, 0.0)
        i0, i1 = int(start * sr), int(end * sr)
        if i1 <= i0:
            continue
        cents = rng.normal(0, detune_cents / 2) + global_offset_cents
        seg_t = t[i0:i1] - start
        vib = vibrato_cents * np.sin(2 * np.pi * rng.uniform(4.8, 6.2) * seg_t) * np.clip(seg_t / 0.25, 0, 1)
        # A short scoop up into the note, like a real voice.
        scoop = -60.0 * np.exp(-seg_t / 0.03)
        f0[i0:i1] = midi_to_hz(midi + (cents + vib + scoop) / 100.0)
        env = np.minimum(1.0, seg_t / 0.03) * np.minimum(1.0, (i1 - i0 - np.arange(i1 - i0)) / (0.04 * sr))
        amp[i0:i1] = env * rng.uniform(0.6, 1.0)
        truth.append(TrueNote(start, end - start, midi))
    phase = 2 * np.pi * np.cumsum(f0) / sr
    # A hum ("mmm") is mostly fundamental with a few weak harmonics.
    sig = np.sin(phase) + 0.35 * np.sin(2 * phase) + 0.15 * np.sin(3 * phase) + 0.05 * np.sin(4 * phase)
    sig *= amp
    sig += rng.normal(0, 10 ** (noise_db / 20), n)
    return (0.3 * sig / max(1e-9, np.max(np.abs(sig)))).astype(np.float32), truth


def melody(name: str = "ode") -> list[tuple[int, float]]:
    """A few test melodies (public-domain or made up)."""
    if name == "ode":  # Beethoven's Ode to Joy, public domain, D major
        d = [66, 66, 67, 69, 69, 67, 66, 64, 62, 62, 64, 66]
        return [(m, 1.0) for m in d] + [(66, 1.5), (64, 0.5), (64, 2.0)]
    if name == "minor":  # made up, A minor, 8th-note runs
        return [(69, 0.5), (71, 0.5), (72, 1.0), (71, 0.5), (69, 0.5), (67, 1.0), (69, 0.5), (72, 0.5),
                (76, 1.0), (74, 0.5), (72, 0.5), (71, 1.0), (69, 2.0)]
    if name == "repeat":  # repeated same pitch, re-articulated
        return [(64, 0.5)] * 4 + [(67, 1.0), (65, 1.0)] + [(64, 0.5)] * 4 + [(62, 2.0)]
    raise ValueError(name)


# --- Beatbox ------------------------------------------------------------------------------------

DRUM_MIDI = {"kick": 36, "snare": 38, "hat": 42, "open_hat": 46}


def _kick(sr, rng):
    d = int(0.16 * sr)
    tt = np.arange(d) / sr
    f = 50 + 110 * np.exp(-tt / 0.03)
    s = np.sin(2 * np.pi * np.cumsum(f) / sr) * np.exp(-tt / 0.06)
    s[: int(0.004 * sr)] += rng.normal(0, 0.3, int(0.004 * sr))  # the "b" click
    return s


def _snare(sr, rng):
    from scipy.signal import butter, lfilter

    d = int(0.16 * sr)
    tt = np.arange(d) / sr
    b, a = butter(2, [1200 / (sr / 2), min(0.95, 5000 / (sr / 2))], btype="band")
    noise = lfilter(b, a, rng.normal(0, 1, d))
    return (1.6 * noise + 0.4 * np.sin(2 * np.pi * 210 * tt)) * np.exp(-tt / 0.045)


def _hat(sr, rng, open_=False):
    from scipy.signal import butter, lfilter

    d = int((0.25 if open_ else 0.06) * sr)
    tt = np.arange(d) / sr
    b, a = butter(4, min(0.95, 5500 / (sr / 2)), btype="high")
    return 0.8 * lfilter(b, a, rng.normal(0, 1, d)) * np.exp(-tt / (0.09 if open_ else 0.015))


def beatbox(
    pattern: list[str] | None = None,
    bpm: float = 92.0,
    bars: int = 2,
    sr: int = SR,
    *,
    swing: float = 0.5,
    timing_jitter: float = 0.01,
    seed: int = 0,
    lead_in: float = 0.4,
) -> tuple[np.ndarray, list[tuple[float, str]]]:
    """Beatbox from an 8th-note pattern per bar ('k', 's', 'h', 'o' or '-')."""
    rng = np.random.default_rng(seed)
    pattern = pattern or ["k", "h", "s", "h", "k", "k", "s", "h"]
    names = {"k": "kick", "s": "snare", "h": "hat", "o": "open_hat"}
    beat = 60.0 / bpm
    total = lead_in + bars * 4 * beat + 0.6
    out = np.zeros(int(total * sr))
    truth = []
    for bar in range(bars):
        for i, sym in enumerate(pattern):
            if sym == "-":
                continue
            pos = i // 2 + (swing if i % 2 else 0.0)
            t0 = lead_in + (bar * 4 + pos) * beat + rng.normal(0, timing_jitter)
            name = names[sym]
            hit = {"kick": _kick, "snare": _snare, "hat": _hat}.get(name, lambda s, r: _hat(s, r, True))(sr, rng)
            hit = hit * rng.uniform(0.7, 1.0)
            i0 = int(t0 * sr)
            out[i0 : i0 + len(hit)] += hit[: len(out) - i0]
            truth.append((t0, name))
    out += rng.normal(0, 10 ** (-50 / 20), len(out))
    return (0.4 * out / np.max(np.abs(out))).astype(np.float32), truth


# --- Things that are NOT music ------------------------------------------------------------------

def talking(seconds: float = 6.0, sr: int = SR, seed: int = 0) -> np.ndarray:
    """Speech-like sound: syllables with constantly gliding pitch and noisy consonants."""
    rng = np.random.default_rng(seed)
    n = int(seconds * sr)
    t = np.arange(n) / sr
    out = np.zeros(n)
    pos = 0.2
    while pos < seconds - 0.3:
        dur = rng.uniform(0.12, 0.28)
        i0, i1 = int(pos * sr), int((pos + dur) * sr)
        tt = t[i0:i1] - pos
        # Pitch falls or rises through the syllable (intonation), never holding still.
        start = rng.uniform(110, 190)
        f = start * (1 + rng.uniform(-0.35, 0.35) * tt / dur)
        ph = 2 * np.pi * np.cumsum(f) / sr
        env = np.sin(np.pi * tt / dur)
        out[i0:i1] += env * (np.sin(ph) + 0.6 * np.sin(2 * ph) + 0.4 * np.sin(3 * ph) + 0.3 * np.sin(5 * ph))
        c = int(0.04 * sr)
        if rng.random() < 0.6 and i0 > c:
            out[i0 - c : i0] += rng.normal(0, 0.25, c) * np.hanning(c)
        pos += dur + rng.uniform(0.02, 0.12)
        if rng.random() < 0.12:
            pos += rng.uniform(0.2, 0.5)  # pauses between phrases
    out += rng.normal(0, 10 ** (-45 / 20), n)
    return (0.3 * out / np.max(np.abs(out))).astype(np.float32)


def typing(seconds: float = 6.0, sr: int = SR, seed: int = 0) -> np.ndarray:
    """Keyboard clatter: short, similar, bright clicks at an uneven rate."""
    from scipy.signal import butter, lfilter

    rng = np.random.default_rng(seed)
    n = int(seconds * sr)
    out = np.zeros(n)
    b, a = butter(2, [2000 / (sr / 2), min(0.95, 7000 / (sr / 2))], btype="band")
    pos = 0.1
    while pos < seconds - 0.1:
        d = int(0.025 * sr)
        click = lfilter(b, a, rng.normal(0, 1, d)) * np.exp(-np.arange(d) / (0.004 * sr))
        i0 = int(pos * sr)
        out[i0 : i0 + d] += click * rng.uniform(0.5, 1.0)
        pos += rng.exponential(0.14) + 0.04
    out += rng.normal(0, 10 ** (-50 / 20), n)
    return (0.3 * out / np.max(np.abs(out))).astype(np.float32)


def silence(seconds: float, sr: int = SR, noise_db: float = -55.0, seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return rng.normal(0, 10 ** (noise_db / 20), int(seconds * sr)).astype(np.float32)


# --- Singing ------------------------------------------------------------------------------------

VOWELS = {"ah": (730, 1090, 2440), "oh": (570, 840, 2410), "eh": (530, 1840, 2480), "ee": (270, 2290, 3010),
          "oo": (300, 870, 2240)}


@dataclass
class SungNote:
    grid: float  # where the note belongs (seconds, in song time)
    onset: float  # where it was sung
    duration: float
    midi: int
    cents: float  # how far off pitch it was sung


def _formants(src: np.ndarray, sr: int, vowel: str) -> np.ndarray:
    from scipy.signal import lfilter

    out = np.zeros_like(src)
    for f, gain in zip(VOWELS[vowel], (1.0, 0.6, 0.25)):
        r = np.exp(-np.pi * 90 / sr)
        a = [1, -2 * r * np.cos(2 * np.pi * f / sr), r * r]
        out += gain * lfilter([1 - r], a, src)
    return out


def sing(
    notes: list[tuple[float, float, int]],
    bpm: float = 100.0,
    sr: int = 44100,
    *,
    start: float = 0.0,
    pre_roll: float = 1.0,
    detune_cents: float = 30.0,
    global_offset_cents: float = 0.0,
    timing_ms: float = 30.0,
    lateness_ms: float = 0.0,
    vibrato_cents: float = 30.0,
    sibilants: float = 0.3,
    breaths: bool = True,
    plosives: float = 0.0,
    noise_db: float = -62.0,
    seed: int = 0,
    tail: float = 0.8,
) -> tuple[np.ndarray, list[SungNote]]:
    """A synthetic singer: a glottal-like source through vowel formants, with scoops, vibrato, detuned
    notes, early/late onsets, "s" sounds, breaths before phrases and optional "p" pops.

    `notes` are [(start_beat, length_beats, midi)] in song beats; sample 0 of the result is song time
    `start - pre_roll` seconds (the pre-roll is room noise, for the noise profile)."""
    rng = np.random.default_rng(seed)
    spb = 60.0 / bpm
    t0 = start - pre_roll
    end = max(s + l for s, l, _ in notes) * spb + tail
    n = int((end - t0) * sr)
    f0 = np.zeros(n)
    amp = np.zeros(n)
    vowel_of = np.zeros(n, dtype=int)
    out_noise = np.zeros(n)
    truth: list[SungNote] = []
    names = list(VOWELS)
    prev_end = -1e9
    for k, (sb, lb, m) in enumerate(sorted(notes)):
        grid = sb * spb
        onset = grid + rng.normal(lateness_ms, timing_ms) / 1000.0
        dur = max(0.08, lb * spb * 0.92)
        i0, i1 = int((onset - t0) * sr), int((onset + dur - t0) * sr)
        i0, i1 = max(i0, 0), min(i1, n)
        if i1 - i0 < 10:
            continue
        cents = rng.normal(0, detune_cents) + global_offset_cents
        tt = np.arange(i1 - i0) / sr
        vib = vibrato_cents * np.sin(2 * np.pi * rng.uniform(5.0, 6.0) * tt) * np.clip((tt - 0.15) / 0.3, 0, 1)
        scoop = -70.0 * np.exp(-tt / 0.035)
        f0[i0:i1] = midi_to_hz(m + (cents + vib + scoop) / 100.0)
        env = np.minimum(1, tt / 0.02) * np.minimum(1, (tt[-1] - tt) / 0.03) * rng.uniform(0.6, 1.0)
        amp[i0:i1] = env
        vowel_of[i0:i1] = rng.integers(0, 3)  # ah / oh / eh mostly
        if rng.random() < sibilants:  # an "s" just before the vowel
            ls = int(0.07 * sr)
            a = max(0, i0 - ls)
            s_noise = rng.normal(0, 1, i0 - a) * np.hanning(i0 - a) * 0.25
            out_noise[a:i0] += _highpass(s_noise, sr, 5000)
        if plosives and rng.random() < plosives:  # a "p" pop: a low thump at the onset
            lp = int(0.05 * sr)
            seg = np.sin(2 * np.pi * 60 * np.arange(min(lp, n - i0)) / sr) * np.exp(-np.arange(min(lp, n - i0)) / (0.012 * sr))
            out_noise[i0:i0 + len(seg)] += 0.8 * seg
        if breaths and onset - prev_end > 0.6:  # a breath before each phrase
            lb_ = int(0.3 * sr)
            a = max(0, i0 - int(0.1 * sr) - lb_)
            b = a + lb_
            if b < i0:
                br = _bandpass(rng.normal(0, 1, b - a), sr, 500, 3000) * np.hanning(b - a) * 0.08
                out_noise[a:b] += br
        prev_end = onset + dur
        truth.append(SungNote(grid, onset, dur, m, float(cents)))
    phase = 2 * np.pi * np.cumsum(f0) / sr
    src = np.zeros(n)
    for h in range(1, 40):
        src += np.where(h * f0 < sr / 2 - 500, 1.0 / h, 0.0) * np.sin(h * phase)
    src *= amp
    voiced = np.zeros(n)
    for vi in range(3):
        voiced += _formants(src * (vowel_of == vi), sr, names[vi])
    voiced = 0.5 * voiced / max(1e-9, np.max(np.abs(voiced)))
    x = voiced + out_noise + rng.normal(0, 10 ** (noise_db / 20), n)
    return x.astype(np.float32), truth


def _highpass(x, sr, f):
    from scipy.signal import butter, sosfilt

    return sosfilt(butter(4, f, btype="high", fs=sr, output="sos"), x)


def _bandpass(x, sr, lo, hi):
    from scipy.signal import butter, sosfilt

    return sosfilt(butter(2, [lo, hi], btype="band", fs=sr, output="sos"), x)


# --- Preview rendering --------------------------------------------------------------------------

def render_preview(notes: list[dict], drums: list[dict], bpm: float, sr: int = 22050) -> np.ndarray:
    """A rough preview of cleaned notes and drums: a soft electric-piano-like tone and simple drums.

    `notes` / `drums` use beats (`start`, `length`) as produced by the cleanup stage.
    """
    spb = 60.0 / bpm
    end_beats = max([n["start"] + n["length"] for n in notes] + [d["start"] + 1 for d in drums] + [1.0])
    out = np.zeros(int((end_beats * spb + 1.5) * sr))
    rng = np.random.default_rng(0)
    for n in notes:
        t0 = n["start"] * spb
        dur = max(0.08, n["length"] * spb)
        tt = np.arange(int((dur + 0.4) * sr)) / sr
        f = float(midi_to_hz(n["pitch"]))
        env = np.exp(-tt / 0.9) * np.minimum(1, tt / 0.005)
        env[tt > dur] *= np.exp(-(tt[tt > dur] - dur) / 0.08)
        tone = np.sin(2 * np.pi * f * tt) + 0.25 * np.sin(4 * np.pi * f * tt) * np.exp(-tt / 0.2)
        v = n.get("velocity", 90) / 127
        i0 = int(t0 * sr)
        seg = (tone * env * v)[: len(out) - i0]
        out[i0 : i0 + len(seg)] += 0.5 * seg
    makers = {"kick": _kick, "snare": _snare, "hat": _hat, "open_hat": lambda s, r: _hat(s, r, True)}
    for d in drums:
        hit = makers.get(d["name"], _snare)(sr, rng) * d.get("velocity", 100) / 127
        i0 = int(d["start"] * spb * sr)
        seg = hit[: len(out) - i0]
        out[i0 : i0 + len(seg)] += 0.6 * seg
    peak = np.max(np.abs(out)) or 1.0
    return (0.8 * out / peak).astype(np.float32)
