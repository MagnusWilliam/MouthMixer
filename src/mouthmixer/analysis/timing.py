"""Stage D1-D3: tempo (with drift), downbeat, swing and quantising (PLAN.md §5).

People speed up and slow down while humming, so instead of one tempo we fit a tempo that changes
linearly over the clip, then map every onset to a beat position on that curve ("warping") before
snapping to the grid.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np


@dataclass
class Grid:
    bpm: float  # tempo at the start of the clip
    drift: float  # tempo change over the clip (0.05 = 5% faster by the end)
    phase: float  # seconds of the first beat
    span: float  # seconds the drift is spread over
    meter: int = 4
    downbeat: int = 0  # which beat (0..meter-1) of the fitted grid is "1"
    swing: float = 0.5  # 0.5 straight, about 0.6-0.67 swung
    alternatives: list = field(default_factory=list)  # [{"bpm":..}] other plausible tempos (half/double)
    confidence: float = 0.0

    def beats(self, t) -> np.ndarray:
        """Seconds -> beats on the fitted (drifting) grid, counted from the downbeat."""
        t = np.asarray(t, dtype=float) - self.phase
        rate = self.bpm / 60.0
        k = self.drift / max(self.span, 1e-6)
        return rate * (t + 0.5 * k * t * t) - self.downbeat

    def seconds(self, b) -> np.ndarray:
        b = np.asarray(b, dtype=float) + self.downbeat
        rate = self.bpm / 60.0
        k = self.drift / max(self.span, 1e-6)
        if abs(k) < 1e-9:
            return self.phase + b / rate
        # Solve rate*(t + k t^2/2) = b for t.
        return self.phase + (-1 + np.sqrt(np.maximum(0.0, 1 + 2 * k * b / rate))) / k

    def to_dict(self):
        return {
            "bpm": round(self.bpm, 2),
            "bpm_end": round(self.bpm * (1 + self.drift), 2),
            "drift": round(self.drift, 3),
            "meter": self.meter,
            "swing": round(self.swing, 3),
            "alternatives": self.alternatives,
            "confidence": round(self.confidence, 3),
        }


SWINGS = (0.5, 0.58, 0.64, 0.67)


def _targets(subdiv: int, swing: float) -> np.ndarray:
    """Allowed positions inside one beat: straight 8ths/16ths, or swung 8ths."""
    if swing <= 0.5:
        return np.arange(subdiv + 1) / subdiv
    return np.array([0.0, swing, 1.0])


def _score(onsets, weights, bpm, drift, span, targets, sigma=0.035):
    """Best phase and fit score for one tempo hypothesis. Returns (score, phase_seconds)."""
    rate = bpm / 60.0
    k = drift / span
    t = onsets - onsets[0]
    pos = rate * (t + 0.5 * k * t * t)  # in beats
    phases = np.linspace(0, 1, 32, endpoint=False)[:, None]
    rel = pos[None, :] - phases
    frac = rel - np.floor(rel)
    d = np.min(np.abs(frac[:, :, None] - targets[None, None, :]), axis=2)
    fit = np.exp(-((d / rate / sigma) ** 2))
    # Onsets that also land on whole beats make a reading more likely (rules out 3:2 readings).
    db = np.minimum(frac, 1 - frac)
    on_beat = np.exp(-((db / rate / sigma) ** 2))
    scores = np.sum(weights[None, :] * fit * (0.6 + 0.4 * on_beat), axis=1)
    b = int(np.argmax(scores))
    return float(scores[b]) / max(1e-9, weights.sum()), onsets[0] + float(phases[b, 0]) / rate


def fit_tempo(onsets, weights=None, *, subdiv: int = 2, lo: float = 60.0, hi: float = 180.0,
              prior_bpm: float = 100.0) -> Grid:
    """Fit tempo + linear drift to onset times. `subdiv` is the finest grid notes are expected on
    (2 = 8th notes for melodies, 4 = 16ths for beatbox)."""
    onsets = np.sort(np.asarray(onsets, dtype=float))
    if len(onsets) < 3:
        return Grid(prior_bpm, 0.0, float(onsets[0]) if len(onsets) else 0.0, 1.0, confidence=0.0)
    weights = np.ones_like(onsets) if weights is None else np.asarray(weights, dtype=float)
    span = max(1.0, onsets[-1] - onsets[0])
    ioi = float(np.median(np.diff(onsets))) if len(onsets) > 1 else 0.5
    results = []
    for bpm in np.arange(lo, hi + 0.01, 1.0):
        # Fast/slow ambiguity: prefer tempos near a typical value, and readings where notes come about
        # every half to whole beat (not one note every two beats).
        prior = np.exp(-0.5 * (np.log2(bpm / prior_bpm) / 0.6) ** 2)
        ioi_beats = ioi * bpm / 60.0
        dens = np.exp(-0.5 * (np.log2(ioi_beats / 0.6) / 0.8) ** 2)
        plaus = prior * dens
        for drift in (-0.08, -0.04, 0.0, 0.04, 0.08):
            for sw in SWINGS:
                s, ph = _score(onsets, weights, bpm, drift, span, _targets(subdiv, sw))
                # Swing must earn its place: a small cost keeps straight readings for straight playing.
                s -= 0.01 * (sw > 0.5)
                results.append((s * (0.6 + 0.4 * plaus) - 0.02 * abs(drift) / 0.08, s, bpm, drift, sw, ph))
    results.sort(reverse=True)
    # Refine around the best with finer steps.
    _, _, b0, d0, sw0, _ = results[0]
    fine = []
    for bpm in np.arange(b0 - 1.0, b0 + 1.01, 0.1):
        for drift in np.arange(d0 - 0.03, d0 + 0.031, 0.01):
            s, ph = _score(onsets, weights, bpm, drift, span, _targets(subdiv, sw0))
            fine.append((s - 0.02 * abs(drift) / 0.08, s, bpm, drift, ph))
    fine.sort(reverse=True)
    _, s, bpm, drift, ph = fine[0]
    grid = Grid(float(bpm), float(drift), float(ph), float(span), swing=float(sw0), confidence=float(s))
    # Phase: the fitted grid point may be an off-beat; pick the beat alignment that puts most weight on beats.
    best_off, best_w = 0.0, -1.0
    for off in np.arange(subdiv) / subdiv:
        g = Grid(grid.bpm, grid.drift, grid.phase + off * 60 / grid.bpm, span)
        b = g.beats(onsets)
        on_beat = np.abs(b - np.round(b)) < 0.12
        w = float(np.sum(weights[on_beat]))
        if w > best_w:
            best_w, best_off = w, off
    grid.phase += best_off * 60 / grid.bpm
    # Half and double tempo are always plausible readings; offer them if in range.
    alts = []
    for f in (0.5, 2.0):
        if 50 <= bpm * f <= 220:
            alts.append({"bpm": round(float(bpm * f), 1)})
    grid.alternatives = alts
    return grid


def find_downbeat(grid: Grid, onsets, weights, kicks=None, snares=None) -> int:
    """Which beat is "1": strongest notes on 1 (and 3), kicks on 1, snares on 2 and 4."""
    b = grid.beats(onsets)
    near = np.abs(b - np.round(b)) < 0.15
    best, best_s = 0, -1e9
    for d in range(grid.meter):
        idx = (np.round(b).astype(int) - d) % grid.meter
        s = float(np.sum(weights[near & (idx == 0)])) * 1.0 + float(np.sum(weights[near & (idx == 2)])) * 0.4
        # Only hits that sit on a beat count (an off-beat kick says nothing about where "1" is).
        if kicks is not None and len(kicks):
            kf = grid.beats(kicks)
            kb = np.round(kf[np.abs(kf - np.round(kf)) < 0.15]).astype(int)
            s += 1.5 * float(np.sum((kb - d) % grid.meter == 0))
        if snares is not None and len(snares):
            sf_ = grid.beats(snares)
            sb = np.round(sf_[np.abs(sf_ - np.round(sf_)) < 0.15]).astype(int)
            s += 1.5 * float(np.sum(((sb - d) % grid.meter) % 2 == 1))
        # When the evidence is even, the first onset is most likely on "1".
        if near[0] and (int(np.round(b[0])) - d) % grid.meter == 0:
            s += 0.5 * float(np.max(weights))
        if s > best_s:
            best, best_s = d, s
    return best


def detect_swing(grid: Grid, onsets) -> float:
    """How late the off-beat 8ths land: 0.5 is straight, 0.67 is triplet swing."""
    b = grid.beats(onsets)
    frac = b - np.floor(b)
    off = frac[(frac > 0.35) & (frac < 0.8)]
    if len(off) < 3:
        return 0.5
    s = float(np.median(off))
    return s if s > 0.56 else 0.5


def quantize(beats: np.ndarray, *, strength: float = 0.7, swing: float = 0.5, subdiv: int = 4) -> np.ndarray:
    """Move beat positions part of the way to the grid. With swing, off-beat 8ths go to the swing point."""
    beats = np.asarray(beats, dtype=float)
    base = np.floor(beats)
    frac = beats - base
    if swing > 0.5:
        targets = np.array([0.0, swing, 1.0])
    else:
        targets = np.arange(subdiv + 1) / subdiv
    nearest = targets[np.argmin(np.abs(frac[:, None] - targets[None, :]), axis=1)]
    return beats + strength * (base + nearest - beats)


def snap_length(length: float, swing: float = 0.5) -> float:
    """Note lengths to musical values (16ths, or swung 8ths)."""
    unit = 0.25 if swing <= 0.5 else 1 / 3
    return max(unit, round(length / unit) * unit)
