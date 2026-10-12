"""Stage C1: hums, whistles and sung melodies -> notes (PLAN.md §4).

The pitch curve is cut into notes with hysteresis, so vibrato and wobble don't become extra notes.
Each note keeps its float pitch, loudness and pitch curve; cleanup (Stage D) decides what it means.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

import numpy as np

from .pitch import HOP_SEC, PitchTrack


@dataclass
class Note:
    onset: float  # seconds
    duration: float  # seconds
    pitch: float  # float MIDI (not snapped yet)
    velocity: int
    bend: list = field(default_factory=list)  # pitch curve in semitones relative to `pitch`, every 10 ms

    def to_dict(self):
        d = asdict(self)
        d["pitch"] = round(self.pitch, 3)
        d["onset"] = round(self.onset, 4)
        d["duration"] = round(self.duration, 4)
        d["bend"] = [round(b, 2) for b in self.bend[::3]]  # 30 ms resolution is enough to store
        return d


def _median_filter(x: np.ndarray, k: int = 5) -> np.ndarray:
    out = x.copy()
    h = k // 2
    for i in range(len(x)):
        w = x[max(0, i - h) : i + h + 1]
        w = w[np.isfinite(w)]
        if np.isfinite(x[i]) and len(w):
            out[i] = np.median(w)
    return out


def transcribe(tr: PitchTrack, *, jump: float = 0.6, hold_frames: int = 6, min_note: float = 0.06,
               dip_ratio: float = 0.55) -> list[Note]:
    """Cut a pitch track into notes.

    A new note starts when (a) the voice stops and starts again, (b) the pitch moves more than `jump`
    semitones and stays there for `hold_frames` (60 ms), or (c) the loudness dips and comes back on the
    same pitch (a re-articulated "hm-hm").
    """
    midi = _median_filter(tr.midi)
    rms = tr.rms
    n = len(midi)
    # Loudness dips: local minima well below the surrounding peaks.
    dips = set()
    w = 8
    for i in range(w, n - w):
        if not np.isfinite(midi[i]) and not (np.isfinite(midi[i - 1]) and np.isfinite(midi[i + 1])):
            continue
        seg = rms[i - w : i + w + 1]
        if rms[i] == seg.min() and rms[i] < dip_ratio * min(rms[i - w : i].max(), rms[i + 1 : i + w + 1].max()):
            dips.add(i)

    bounds: list[tuple[int, int]] = []
    start = None
    i = 0
    while i < n:
        voiced = np.isfinite(midi[i])
        if start is None:
            if voiced:
                start = i
            i += 1
            continue
        if not voiced:
            bounds.append((start, i))
            start = None
            i += 1
            continue
        ref = np.median(midi[start:i]) if i > start else midi[i]
        if i in dips and i - start >= 3:
            bounds.append((start, i))
            start = i + 1
            i += 1
            continue
        if abs(midi[i] - ref) > jump:
            j = i
            while j < n and np.isfinite(midi[j]) and abs(midi[j] - ref) > jump and j - i < hold_frames:
                j += 1
            if j - i >= hold_frames:
                bounds.append((start, i))
                start = i
        i += 1
    if start is not None:
        bounds.append((start, n))

    notes = []
    peak = float(np.max(rms)) if len(rms) else 1.0
    for a, b in bounds:
        if (b - a) * HOP_SEC < min_note:
            continue
        seg = tr.midi[a:b]
        seg = seg[np.isfinite(seg)]
        if not len(seg):
            continue
        # Ignore the first 30 ms (the scoop into the note) when deciding its pitch.
        core = seg[min(3, len(seg) // 3) :]
        p = float(np.median(core))
        loud = float(np.max(rms[a:b])) / (peak + 1e-9)
        vel = int(np.clip(40 + 80 * loud, 30, 120))
        notes.append(Note(a * HOP_SEC, (b - a) * HOP_SEC, p, vel, list(tr.midi[a:b] - p)))
    return notes
