"""Stage C2: beatbox -> drum hits (PLAN.md §4).

Before calibration a simple rule set sorts hits by their sound (low thump = kick, bright hiss = hat,
noisy middle = snare). After calibration (about 10 examples of each of your sounds) a nearest-neighbour
classifier trained on *your* mouth sounds takes over. Every correction adds another example.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

import librosa
import numpy as np

GM = {"kick": 36, "snare": 38, "hat": 42, "open_hat": 46, "clap": 39, "rim": 37, "tom": 45}
WINDOW = 0.08


@dataclass
class Hit:
    onset: float
    name: str
    velocity: int
    confidence: float

    def to_dict(self):
        d = asdict(self)
        d["onset"] = round(self.onset, 4)
        d["confidence"] = round(self.confidence, 3)
        return d


def onsets(y: np.ndarray, sr: int, mask_voiced: np.ndarray | None = None) -> np.ndarray:
    """Onset times (seconds). `mask_voiced` (10 ms frames) hides hum notes in mixed clips."""
    hop = int(sr * 0.01)
    env = librosa.onset.onset_strength(y=y, sr=sr, hop_length=hop)
    if mask_voiced is not None:
        m = np.zeros_like(env, dtype=bool)
        m[: min(len(m), len(mask_voiced))] = mask_voiced[: len(m)]
        env = np.where(m, 0.0, env)
    idx = librosa.onset.onset_detect(onset_envelope=env, sr=sr, hop_length=hop, backtrack=False, units="frames",
                                     delta=0.04, wait=4)
    times = idx * 0.01
    if not len(times):
        return times
    # Keep real attacks only: loud enough overall, and clearly louder than just before (not a tail).
    a = np.abs(y)
    top = float(np.max(a)) or 1.0
    keep = []
    for t in times:
        # The onset-strength peak lands just after the attack: step back to where the hit starts.
        i0 = max(0, int((t - 0.04) * sr))
        w = a[i0 : int((t + 0.03) * sr)]
        i = i0 + int(np.argmax(w >= 0.3 * w.max())) if len(w) else int(t * sr)
        t = i / sr
        if keep and t - keep[-1] < 0.05:
            continue
        after = float(np.max(a[i : i + int(0.05 * sr)], initial=0.0))
        before = float(np.max(a[max(0, i - int(0.03 * sr)) : i], initial=0.0))
        if after >= 0.06 * top and after >= 1.8 * before:
            keep.append(t)
    return np.array(keep)


def features(y: np.ndarray, sr: int, t: float) -> np.ndarray:
    i0 = int(t * sr)
    w = y[i0 : i0 + int(WINDOW * sr)]
    if len(w) < int(WINDOW * sr):
        w = np.pad(w, (0, int(WINDOW * sr) - len(w)))
    win = w * np.hanning(len(w))
    spec = np.abs(np.fft.rfft(win)) + 1e-9
    freqs = np.fft.rfftfreq(len(w), 1 / sr)
    tot = spec.sum()
    centroid = (spec * freqs).sum() / tot
    low = spec[freqs < 250].sum() / tot
    high = spec[freqs > 5000].sum() / tot
    flat = np.exp(np.mean(np.log(spec))) / np.mean(spec)
    # Decay time from a smoothed 5 ms loudness envelope over a longer window (open hats ring on).
    long = y[i0 : i0 + int(0.3 * sr)]
    fr = max(1, int(0.005 * sr))
    env = np.sqrt(np.mean(long[: len(long) // fr * fr].reshape(-1, fr) ** 2, axis=1)) if len(long) >= fr else np.zeros(1)
    peak_i = int(np.argmax(env))
    below = np.nonzero(env[peak_i:] < 0.2 * env[peak_i])[0]
    decay = (below[0] if len(below) else len(env) - peak_i) * fr / sr
    mfcc = librosa.feature.mfcc(y=w.astype(np.float32), sr=sr, n_mfcc=13, n_fft=512, hop_length=128).mean(axis=1)
    return np.concatenate([[np.log(centroid + 1), low, high, flat, decay * 10], mfcc / 50.0])


def rule_classify(f: np.ndarray) -> tuple[str, float]:
    logc, low, high, flat, decay10 = f[:5]
    centroid = np.exp(logc) - 1
    if low > 0.3 and centroid < 1500:
        return "kick", min(1.0, low / 0.5)
    if high > 0.45 or centroid > 5000:
        return ("open_hat", 0.6) if decay10 > 0.6 else ("hat", min(1.0, high / 0.6))
    return "snare", 0.6


class Calibration:
    """Your personal beatbox sounds, stored as feature vectors per label."""

    def __init__(self, path: Path | None = None):
        self.path = path
        self.examples: list[tuple[str, list]] = []
        if path and path.exists():
            self.examples = [(e["label"], e["f"]) for e in json.loads(path.read_text())["examples"]]

    @property
    def ready(self) -> bool:
        labels = {lab for lab, _ in self.examples}
        return len(labels) >= 2 and len(self.examples) >= 10

    def add(self, label: str, f: np.ndarray):
        self.examples.append((label, [float(x) for x in f]))

    def save(self):
        if self.path:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps({"examples": [{"label": lab, "f": f} for lab, f in self.examples]}))

    def classify(self, f: np.ndarray, k: int = 3) -> tuple[str, float]:
        X = np.array([e for _, e in self.examples])
        labels = [lab for lab, _ in self.examples]
        mu, sd = X.mean(axis=0), X.std(axis=0) + 1e-6
        d = np.linalg.norm((X - mu) / sd - (f - mu) / sd, axis=1)
        order = np.argsort(d)[:k]
        votes: dict[str, float] = {}
        for i in order:
            votes[labels[i]] = votes.get(labels[i], 0.0) + 1.0 / (1e-3 + d[i])
        best = max(votes, key=votes.get)
        return best, votes[best] / sum(votes.values())


def calibrate_from_take(y: np.ndarray, sr: int, label: str, cal: Calibration) -> int:
    """Add every hit in a take of one sound ("do your kick 10 times") as examples. Returns the count."""
    count = 0
    for t in onsets(y, sr):
        cal.add(label, features(y, sr, t))
        count += 1
    return count


def transcribe(y: np.ndarray, sr: int, cal: Calibration | None = None,
               mask_voiced: np.ndarray | None = None) -> list[Hit]:
    hits = []
    times = onsets(y, sr, mask_voiced)
    if not len(times):
        return hits
    peaks = []
    for t in times:
        w = y[int(t * sr) : int((t + 0.05) * sr)]
        peaks.append(float(np.max(np.abs(w))) if len(w) else 0.0)
    top = max(peaks) or 1.0
    for t, pk in zip(times, peaks):
        f = features(y, sr, t)
        name, conf = cal.classify(f) if (cal is not None and cal.ready) else rule_classify(f)
        vel = int(np.clip(35 + 85 * pk / top, 20, 120))
        hits.append(Hit(float(t), name, vel, float(conf)))
    return hits
