"""Stage A/B: find sound in a recording and decide whether it's music (PLAN.md §2-3).

Version 1 uses the hand-written musical features of PLAN §3 B2. The pretrained classifier (B1),
the speaker check and the personal classifier (B3) plug in later as extra scores.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import librosa
import numpy as np

from . import pitch

FRAME_SEC = 0.03


@dataclass
class GateSettings:
    open_db: float = 12.0  # sound must be this far above the noise floor
    hangover_sec: float = 2.5  # a clip ends after this much quiet
    min_clip_sec: float = 1.5
    max_clip_sec: float = 180.0
    pre_roll_sec: float = 1.0  # offline scans; the live listener keeps more
    melody_threshold: float = 0.45
    beat_threshold: float = 0.35


@dataclass
class Verdict:
    is_music: bool
    kind: str  # "melody", "beat", "both" or "none"
    scores: dict = field(default_factory=dict)

    def to_dict(self):
        return {"is_music": self.is_music, "kind": self.kind, "scores": self.scores}


def frame_db(y: np.ndarray, sr: int) -> np.ndarray:
    hop = int(sr * FRAME_SEC)
    if len(y) < hop:
        return np.array([-120.0])
    frames = y[: len(y) // hop * hop].reshape(-1, hop)
    return 10 * np.log10(np.mean(frames.astype(np.float64) ** 2, axis=1) + 1e-12)


def active_regions(y: np.ndarray, sr: int, s: GateSettings | None = None) -> list[tuple[float, float]]:
    """Offline version of the live segmenter: (start, end) seconds of sound worth checking."""
    s = s or GateSettings()
    db = frame_db(y, sr)
    floor = np.percentile(db, 10)
    on = db > floor + s.open_db
    regions, start, quiet = [], None, 0
    hang = int(s.hangover_sec / FRAME_SEC)
    for i, a in enumerate(on):
        if a:
            if start is None:
                start = i
            quiet = 0
        elif start is not None:
            quiet += 1
            if quiet > hang:
                regions.append((start, i - quiet + 1))
                start, quiet = None, 0
    if start is not None:
        regions.append((start, len(on) - quiet))
    out = []
    for a, b in regions:
        t0, t1 = a * FRAME_SEC, b * FRAME_SEC
        if t1 - t0 >= s.min_clip_sec:
            out.append((max(0.0, t0 - s.pre_roll_sec), min(len(y) / sr, t1 + 0.5)))
    return out


def _melodic_scores(y: np.ndarray, sr: int, active: np.ndarray) -> dict:
    tr = pitch.track(y, sr)
    n_active = max(1, int(active.sum()))
    voiced_ratio = float(tr.voiced.sum()) / n_active
    # Held notes: steady runs whose pitch doesn't drift from start to end (talking glides).
    runs = []
    for a, b in pitch.plateaus(tr.midi, min_frames=15):
        k = max(3, (b - a) // 3)
        if abs(np.median(tr.midi[b - k : b]) - np.median(tr.midi[a : a + k])) < 0.3:
            runs.append((a, b))
    held = sum(b - a for a, b in runs)
    plateau_frac = held / max(1, int(tr.voiced.sum()))
    # How close the held notes sit to a 12-note grid, after the best tuning offset.
    if runs:
        meds = np.array([np.median(tr.midi[a:b]) for a, b in runs])
        frac = meds - np.round(meds)
        offset = np.angle(np.mean(np.exp(2j * np.pi * frac))) / (2 * np.pi)
        dev = np.abs(((meds - offset) - np.round(meds - offset)))
        grid_fit = float(1 - np.mean(dev) / 0.5)
        distinct = len(set(np.round(meds - offset).astype(int)))
    else:
        grid_fit, distinct = 0.0, 0
    score = plateau_frac * min(1.0, voiced_ratio / 0.3) * (0.5 + 0.5 * grid_fit) * (1.0 if distinct >= 2 else 0.5)
    return {
        "voiced_ratio": round(voiced_ratio, 3),
        "plateau_frac": round(plateau_frac, 3),
        "grid_fit": round(grid_fit, 3),
        "distinct_pitches": distinct,
        "melody": round(float(score), 3),
    }


def _beat_scores(y: np.ndarray, sr: int) -> dict:
    hop = int(sr * 0.01)
    env = librosa.onset.onset_strength(y=y, sr=sr, hop_length=hop)
    onsets = librosa.onset.onset_detect(onset_envelope=env, sr=sr, hop_length=hop, units="samples", backtrack=True)
    if len(onsets) < 6:
        return {"onsets": int(len(onsets)), "beat": 0.0}
    # Periodicity: autocorrelation of the onset envelope between 0.25 and 1.5 s.
    e = env - env.mean()
    ac = np.correlate(e, e, mode="full")[len(e) - 1 :]
    ac /= ac[0] + 1e-9
    lo, hi = int(0.25 / 0.01), min(len(ac) - 1, int(1.5 / 0.01))
    periodicity = float(np.max(ac[lo:hi])) if hi > lo else 0.0
    # Variety of hit types: kicks (low), snares (mid noise), hats (high).
    cents, lows = [], []
    for o in onsets:
        w = y[o : o + int(0.06 * sr)]
        if len(w) < 256:
            continue
        spec = np.abs(np.fft.rfft(w * np.hanning(len(w))))
        freqs = np.fft.rfftfreq(len(w), 1 / sr)
        tot = spec.sum() + 1e-9
        cents.append(float((spec * freqs).sum() / tot))
        lows.append(float(spec[freqs < 250].sum() / tot))
    variety = float(np.std(np.log(np.array(cents) + 1.0))) if cents else 0.0
    low_hits = float(np.mean(np.array(lows) > 0.3)) if lows else 0.0
    rate = len(onsets) / (len(y) / sr)
    score = max(0.0, periodicity) * min(1.0, variety / 0.45) * (1.0 if low_hits > 0.1 else 0.35)
    if rate > 12:
        score *= 0.5
    return {
        "onsets": int(len(onsets)),
        "periodicity": round(periodicity, 3),
        "variety": round(variety, 3),
        "low_hits": round(low_hits, 3),
        "beat": round(float(score), 3),
    }


def judge(y: np.ndarray, sr: int, s: GateSettings | None = None) -> Verdict:
    """Is this clip music? Returns the kind and every score (scores are logged for later training)."""
    s = s or GateSettings()
    db = frame_db(y, sr)
    floor = np.percentile(db, 10)
    active = db > floor + s.open_db
    # Re-sample the activity mask to 10 ms frames for the pitch features.
    active10 = np.repeat(active, 3)
    mel = _melodic_scores(y, sr, active10)
    beat = _beat_scores(y, sr)
    m_ok = mel["melody"] >= s.melody_threshold
    b_ok = beat["beat"] >= s.beat_threshold
    kind = "both" if (m_ok and b_ok) else "melody" if m_ok else "beat" if b_ok else "none"
    return Verdict(kind != "none", kind, {**mel, **beat})


def scan(y: np.ndarray, sr: int, s: GateSettings | None = None) -> list[dict]:
    """Run the whole gate over a long recording (used for Phase 0 recordings and testing)."""
    s = s or GateSettings()
    out = []
    for t0, t1 in active_regions(y, sr, s):
        clip = y[int(t0 * sr) : int(t1 * sr)]
        for c0 in np.arange(0, len(clip) / sr, s.max_clip_sec):
            part = clip[int(c0 * sr) : int((c0 + s.max_clip_sec) * sr)]
            v = judge(part, sr, s)
            out.append({"start": round(t0 + c0, 2), "end": round(t0 + c0 + len(part) / sr, 2), **v.to_dict()})
    return out
