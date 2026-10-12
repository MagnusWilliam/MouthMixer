"""Stage D4: key and mode detection, and probabilistic scale snapping (PLAN.md §5)."""

from __future__ import annotations

import numpy as np

NAMES = ["C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"]

# Key profiles (Krumhansl-Kessler, and Temperley's, which works better on short melodies).
KK_MAJOR = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
KK_MINOR = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])
T_MAJOR = np.array([5.0, 2.0, 3.5, 2.0, 4.5, 4.0, 2.0, 4.5, 2.0, 3.5, 1.5, 4.0])
T_MINOR = np.array([5.0, 2.0, 3.5, 4.5, 2.0, 4.0, 2.0, 4.5, 3.5, 2.0, 1.5, 4.0])

MODES = {
    "major": [0, 2, 4, 5, 7, 9, 11],
    "minor": [0, 2, 3, 5, 7, 8, 10],
    "dorian": [0, 2, 3, 5, 7, 9, 10],
    "mixolydian": [0, 2, 4, 5, 7, 9, 10],
}


def histogram(pitches, weights) -> np.ndarray:
    h = np.zeros(12)
    for p, w in zip(pitches, weights):
        h[int(round(p)) % 12] += w
    return h


def detect(pitches, weights) -> list[dict]:
    """Ranked keys: [{"tonic": 2, "name": "D major", "mode": "major", "confidence": 0.71}, ...]."""
    h = histogram(pitches, weights)
    if h.sum() == 0:
        return [{"tonic": 0, "mode": "major", "name": "C major", "confidence": 0.0}]
    scores = []
    for tonic in range(12):
        hr = np.roll(h, -tonic)
        for mode, profs in (("major", (KK_MAJOR, T_MAJOR)), ("minor", (KK_MINOR, T_MINOR))):
            r = np.mean([np.corrcoef(hr, p)[0, 1] for p in profs])
            scores.append((float(np.nan_to_num(r)), tonic, mode))
    scores.sort(reverse=True)
    # Softmax-ish confidence over the top candidates.
    top = scores[:5]
    ex = np.exp(np.array([s for s, _, _ in top]) * 8)
    conf = ex / ex.sum()
    out = []
    for (r, tonic, mode), c in zip(top, conf):
        out.append({"tonic": tonic, "mode": _refine_mode(h, tonic, mode), "confidence": round(float(c), 3)})
    for o in out:
        o["name"] = f"{NAMES[o['tonic']]} {o['mode']}"
    return out


def _refine_mode(h: np.ndarray, tonic: int, mode: str) -> str:
    """Dorian = minor with a raised 6th; Mixolydian = major with a flat 7th."""
    hr = np.roll(h, -tonic)
    if mode == "minor" and hr[9] > 1.5 * hr[8] and hr[9] > 0.05 * hr.sum():
        return "dorian"
    if mode == "major" and hr[10] > 1.5 * hr[11] and hr[10] > 0.05 * hr.sum():
        return "mixolydian"
    return mode


def tuning_offset(pitches, weights) -> float:
    """Global tuning: hummers are often a little flat or sharp overall. Returns semitones (-0.5..0.5)."""
    p = np.asarray(pitches, dtype=float)
    w = np.asarray(weights, dtype=float)
    if not len(p):
        return 0.0
    ang = np.angle(np.sum(w * np.exp(2j * np.pi * (p - np.round(p)))))
    return float(ang / (2 * np.pi))


def snap(pitch: float, tonic: int, mode: str, length_beats: float) -> tuple[int, bool]:
    """Snap one (tuning-corrected) pitch into the scale.

    A clearly-pitched chromatic note held for most of a beat is kept and marked (it's probably on
    purpose); a wobbly or short out-of-scale note moves to the nearest scale note.
    Returns (midi, kept_chromatic).
    """
    scale = {(tonic + i) % 12 for i in MODES.get(mode, MODES["major"])}
    n = int(round(pitch))
    if n % 12 in scale:
        return n, False
    if abs(pitch - n) <= 0.3 and length_beats >= 0.75:
        return n, True
    up, down = n + 1, n - 1
    cands = [c for c in (up, down) if c % 12 in scale]
    best = min(cands, key=lambda c: abs(c - pitch))
    return best, False
