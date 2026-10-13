"""Turning a booth recording into pieces. Unlike background clips, everything is known in advance: the
tempo, the key, where bar 1 is, and how long the piece is. So notes are read straight onto the grid.

A recording loops the backing: every pass of the piece's length is a separate take. Sample 0 of the
recording is at loop time `start` seconds (negative during the count-in; latency already subtracted).
"""

from __future__ import annotations

import math

import numpy as np

from ..analysis import beatbox, key as keymod, melody, pitch

SR = 16000
DRUM_NOTES = {"kick": 36, "snare": 38, "hat": 42, "open_hat": 46}
PERC_NOTES = {"kick": 64, "snare": 39, "hat": 70, "open_hat": 54}  # low conga, clap, shaker, tambourine


def _to16k(y: np.ndarray, sr: int) -> np.ndarray:
    import librosa

    y = np.asarray(y, dtype=np.float32)
    return y if sr == SR else librosa.resample(y, orig_sr=sr, target_sr=SR).astype(np.float32)


def passes(audio_len_s: float, start: float, cycle_s: float) -> list[int]:
    """Which passes the recording covers well enough to be a take (at least 85% of the pass)."""
    end = start + audio_len_s
    out = []
    k = 0
    while k * cycle_s < end:
        a, b = k * cycle_s, (k + 1) * cycle_s
        covered = max(0.0, min(b, end) - max(a, start))
        if covered >= 0.85 * cycle_s:
            out.append(k)
        k += 1
    return out


def hum(y: np.ndarray, sr: int, start: float, bpm: float, bars: int, tonic: int, mode: str) -> dict[int, dict]:
    """Hummed notes per pass: {pass: {"notes": [[start, length, pitch, vel]], "score": 0..1, "detail": ...}}.
    Times are beats inside the pass; pitches snapped to the key (a clearly held chromatic note is kept)."""
    y16 = _to16k(y, sr)
    tr = pitch.track(y16, SR)
    notes = melody.transcribe(tr)
    spb = 60.0 / bpm
    length = bars * 4
    cycle_s = length * spb
    ks = passes(len(y16) / SR, start, cycle_s)
    tune = keymod.tuning_offset([n.pitch for n in notes], [n.duration for n in notes]) if notes else 0.0
    out = {k: {"notes": [], "off_grid": [], "wobble": []} for k in ks}
    for n in notes:
        beat = (start + n.onset) / spb
        k = math.floor((beat + 0.2) / length)  # a note sung a little early belongs to the next pass
        if k not in out:
            continue
        rel = beat - k * length
        q = max(0.0, round(rel * 4) / 4)
        if q >= length - 0.01:
            continue
        dur = max(0.25, round(n.duration / spb * 4) / 4)
        dur = min(dur, length - q)
        p, _kept = keymod.snap(n.pitch - tune, tonic, mode, dur)
        out[k]["notes"].append([q, dur, int(p), int(n.velocity)])
        out[k]["off_grid"].append(abs(rel - q))
        bend = np.asarray(n.bend, dtype=float) if n.bend else np.zeros(1)
        out[k]["wobble"].append(float(np.median(np.abs(bend))) if len(bend) else 0.0)
    for k, d in out.items():
        d["notes"] = _tidy(d["notes"])
        d["score"] = _score(d, length)
        d["detail"] = {"notes": len(d["notes"]),
                       "timing": round(float(np.mean(d["off_grid"])) if d["off_grid"] else 0.0, 3),
                       "steadiness": round(float(np.mean(d["wobble"])) if d["wobble"] else 0.0, 3)}
        d.pop("off_grid"), d.pop("wobble")
    return out


def _tidy(notes: list) -> list:
    """Sort, drop quiet 16th-note blips (pitch tracker glitches at note ends), keep one note per grid start
    (the longer), and trim overlaps (a mono line)."""
    loud = max((n[3] for n in notes), default=0)
    notes = [n for n in notes if not (n[1] <= 0.25 and n[3] < 0.45 * loud)]
    notes.sort(key=lambda n: (n[0], -n[1]))
    out: list = []
    for n in notes:
        if out and abs(out[-1][0] - n[0]) < 1e-6:
            continue
        if out and out[-1][0] + out[-1][1] > n[0]:
            out[-1][1] = max(0.25, n[0] - out[-1][0])
        out.append(n)
    return out


def _score(d: dict, length: float) -> float:
    """0-1: something was sung, on the grid, steadily. Used to pick the best take (you can override)."""
    if not d["notes"]:
        return 0.0
    timing = float(np.mean(d["off_grid"])) if d["off_grid"] else 0.0  # beats off the 16th grid (0..0.125)
    wobble = float(np.mean(d["wobble"])) if d["wobble"] else 0.0  # semitones of drift inside notes
    filled = min(1.0, sum(n[1] for n in d["notes"]) / (0.3 * length))
    return round(max(0.0, 0.45 * filled + 0.35 * (1 - min(1.0, timing / 0.125)) + 0.2 * (1 - min(1.0, wobble / 0.5))), 3)


def beat(y: np.ndarray, sr: int, start: float, bpm: float, bars: int, cal=None, perc: bool = False) -> dict[int, dict]:
    """Beatboxed hits per pass as drum notes [[start, 0.2, drum, vel]] (16th grid)."""
    y16 = _to16k(y, sr)
    hits = beatbox.transcribe(y16, SR, cal)
    spb = 60.0 / bpm
    length = bars * 4
    ks = passes(len(y16) / SR, start, length * spb)
    table = PERC_NOTES if perc else DRUM_NOTES
    out = {k: {"notes": [], "off_grid": []} for k in ks}
    for h in hits:
        b = (start + h.onset) / spb
        k = math.floor((b + 0.12) / length)
        if k not in out:
            continue
        rel = b - k * length
        q = max(0.0, round(rel * 4) / 4)
        if q >= length - 0.01:
            continue
        out[k]["notes"].append([q, 0.2, table.get(h.name, 38), int(h.velocity)])
        out[k]["off_grid"].append(abs(rel - q))
    for k, d in out.items():
        seen = {}
        for n in d["notes"]:  # one hit per drum per step
            seen.setdefault((n[0], n[2]), n)
        d["notes"] = sorted(seen.values())
        timing = float(np.mean(d["off_grid"])) if d["off_grid"] else 0.0
        d["score"] = round(min(1.0, len(d["notes"]) / (2 * length)) * 0.5 + 0.5 * (1 - min(1.0, timing / 0.125)), 3) \
            if d["notes"] else 0.0
        d["detail"] = {"hits": len(d["notes"]), "timing": round(timing, 3)}
        d.pop("off_grid")
    return out


def cut_pass(y: np.ndarray, sr: int, start: float, k: int, cycle_s: float, out_sr: int) -> np.ndarray:
    """The audio of pass k, exactly one pass long, with 5 ms fades (for vocal chops)."""
    import librosa

    a = int(round((k * cycle_s - start) * sr))
    n = int(round(cycle_s * sr))
    seg = np.zeros(n, dtype=np.float32)
    lo, hi = max(0, a), min(len(y), a + n)
    if hi > lo:
        seg[lo - a:hi - a] = y[lo:hi]
    if sr != out_sr:
        seg = librosa.resample(seg, orig_sr=sr, target_sr=out_sr).astype(np.float32)
    f = int(0.005 * out_sr)
    seg[:f] *= np.linspace(0, 1, f)
    seg[-f:] *= np.linspace(1, 0, f)
    return seg
