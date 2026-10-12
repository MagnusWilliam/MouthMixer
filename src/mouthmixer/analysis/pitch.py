"""Pitch tracking shared by the music gate and melody transcription."""

from __future__ import annotations

from dataclasses import dataclass

import librosa
import numpy as np

HOP_SEC = 0.01  # 10 ms frames everywhere in analysis


@dataclass
class PitchTrack:
    times: np.ndarray  # frame centre times, seconds
    midi: np.ndarray  # float MIDI pitch, NaN when unvoiced
    voiced: np.ndarray  # bool
    prob: np.ndarray  # voicing probability
    rms: np.ndarray  # frame loudness (linear)


def track(y: np.ndarray, sr: int, fmin: float = 65.0, fmax: float = 1050.0) -> PitchTrack:
    hop = int(round(sr * HOP_SEC))
    frame = 2048 if sr > 24000 else 1024
    f0, voiced, prob = librosa.pyin(
        y, fmin=fmin, fmax=fmax, sr=sr, frame_length=frame, hop_length=hop, center=True
    )
    # A short loudness window (32 ms) so quick re-articulations ("hm-hm" on one pitch) show as dips.
    rms = librosa.feature.rms(y=y, frame_length=frame // 2, hop_length=hop, center=True)[0]
    n = min(len(f0), len(rms))
    midi = np.full(n, np.nan)
    ok = voiced[:n] & np.isfinite(f0[:n])
    midi[ok] = librosa.hz_to_midi(f0[:n][ok])
    times = np.arange(n) * HOP_SEC
    return PitchTrack(times, midi, ok, np.nan_to_num(prob[:n]), rms[:n])


def plateaus(midi: np.ndarray, min_frames: int = 12, tol: float = 0.5) -> list[tuple[int, int]]:
    """Runs of voiced frames that hold one pitch (within +-tol semitones of the run's median)."""
    runs = []
    i, n = 0, len(midi)
    while i < n:
        if not np.isfinite(midi[i]):
            i += 1
            continue
        j = i + 1
        while j < n and np.isfinite(midi[j]) and abs(midi[j] - np.median(midi[i : j + 1])) <= tol:
            j += 1
        if j - i >= min_frames:
            runs.append((i, j))
            i = j
        else:
            i += 1
    return runs
