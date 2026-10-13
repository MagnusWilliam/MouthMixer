"""Stage A: the always-on part (PLAN.md §2), with no hardware in it so it can be tested anywhere.

Audio arrives in small blocks. A rolling noise floor decides when there's sound; a clip starts with a
few seconds of pre-roll (ideas often start quietly) and ends after a stretch of quiet. Finished clips go
to a callback; whether they're music is decided elsewhere, off the audio thread. Nothing here touches
the disk: the last 30 seconds live in RAM and are overwritten continuously.
"""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass
from typing import Callable

import numpy as np


@dataclass
class SegmenterSettings:
    frame_sec: float = 0.03
    open_db: float = 12.0
    min_db: float = -65.0
    hangover_sec: float = 2.5
    min_clip_sec: float = 1.5
    max_clip_sec: float = 180.0
    pre_roll_sec: float = 5.0
    ring_sec: float = 30.0
    mute_sec: float = 2.0  # this long of digital silence = the mic's mute button is on


class Ring:
    """A fixed-size circular buffer of the most recent audio."""

    def __init__(self, n: int):
        self.buf = np.zeros(n, dtype=np.float32)
        self.pos = 0
        self.filled = 0

    def write(self, x: np.ndarray) -> None:
        n = len(self.buf)
        x = x[-n:]
        end = self.pos + len(x)
        if end <= n:
            self.buf[self.pos : end] = x
        else:
            k = n - self.pos
            self.buf[self.pos :] = x[:k]
            self.buf[: end - n] = x[k:]
        self.pos = end % n
        self.filled = min(n, self.filled + len(x))

    def last(self, count: int) -> np.ndarray:
        count = min(count, self.filled)
        start = (self.pos - count) % len(self.buf)
        if start + count <= len(self.buf):
            return self.buf[start : start + count].copy()
        return np.concatenate([self.buf[start:], self.buf[: (start + count) % len(self.buf)]])


class Segmenter:
    def __init__(self, sr: int, on_clip: Callable[[np.ndarray, str], None], s: SegmenterSettings | None = None):
        self.sr = sr
        self.s = s or SegmenterSettings()
        self.on_clip = on_clip
        self.frame = int(sr * self.s.frame_sec)
        self.ring = Ring(int(sr * self.s.ring_sec))
        self.recent_db: deque = deque(maxlen=int(10 / self.s.frame_sec))
        self.floor = -60.0
        self.active = False
        self.parts: list[np.ndarray] = []
        self.quiet_frames = 0
        self.loud_frames = 0
        self.silent_frames = 0
        self.muted = False
        self._carry = np.zeros(0, dtype=np.float32)
        self.last_feed = 0.0  # time.monotonic() of the last audio fed in (0 = none yet)

    @property
    def capturing(self) -> bool:
        return self.active

    def feed(self, block: np.ndarray) -> None:
        self.last_feed = time.monotonic()
        x = np.concatenate([self._carry, np.asarray(block, dtype=np.float32).reshape(-1)])
        n = len(x) // self.frame * self.frame
        self._carry = x[n:]
        for i in range(0, n, self.frame):
            self._frame(x[i : i + self.frame])

    def _frame(self, f: np.ndarray) -> None:
        self.ring.write(f)
        energy = float(np.mean(f.astype(np.float64) ** 2))
        # Mute detection: a muted USB mic sends (near) digital zeros.
        self.silent_frames = self.silent_frames + 1 if energy < 1e-12 else 0
        self.muted = self.silent_frames * self.s.frame_sec >= self.s.mute_sec
        db = 10 * np.log10(energy + 1e-12)
        loud = db > max(self.s.min_db, self.floor + self.s.open_db)
        if not self.active:
            self.recent_db.append(db)
            if len(self.recent_db) >= 20:
                self.floor = float(np.percentile(self.recent_db, 20))
            if loud:
                pre = self.ring.last(int(self.s.pre_roll_sec * self.sr))
                self.parts = [pre]
                self.active = True
                self.quiet_frames = 0
                self.loud_frames = 1
            return
        self.parts.append(f.copy())
        if loud:
            self.quiet_frames = 0
            self.loud_frames += 1
        else:
            self.quiet_frames += 1
        length = sum(len(p) for p in self.parts) / self.sr
        if self.quiet_frames * self.s.frame_sec >= self.s.hangover_sec:
            self._finish(trim_quiet=True)
        elif length >= self.s.pre_roll_sec + self.s.max_clip_sec:
            self._finish(trim_quiet=False)
            # A long performance continues as a new linked clip.
            self.active, self.parts, self.quiet_frames, self.loud_frames = True, [], 0, 0

    def _finish(self, trim_quiet: bool) -> None:
        audio = np.concatenate(self.parts) if self.parts else np.zeros(0, dtype=np.float32)
        if trim_quiet:
            keep_tail = int(0.5 * self.sr)
            cut = self.quiet_frames * self.frame - keep_tail
            if cut > 0:
                audio = audio[:-cut]
        loud_sec = self.loud_frames * self.s.frame_sec
        self.active, self.parts, self.quiet_frames, self.loud_frames = False, [], 0, 0
        if loud_sec >= self.s.min_clip_sec * 0.5 and len(audio) / self.sr >= self.s.min_clip_sec:
            self.on_clip(audio, "auto")

    def save_last(self, seconds: float | None = None) -> None:
        """The "save that!" hotkey: keep the last 30 s whatever the gate would have said."""
        n = int((seconds or self.s.ring_sec) * self.sr)
        self.on_clip(self.ring.last(n), "hotkey")

    def reset(self) -> None:
        """Used when pausing: forget everything in memory."""
        self.ring = Ring(len(self.ring.buf))
        self.active, self.parts, self.quiet_frames, self.loud_frames = False, [], 0, 0
        self._carry = np.zeros(0, dtype=np.float32)
        self.last_feed = 0.0
