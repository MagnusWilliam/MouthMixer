"""Stage D: cleanup with music rules (PLAN.md §5). Everything is non-destructive: the raw notes are
kept next to the cleaned ones, and each step has a strength."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from . import key as keymod
from .beatbox import Hit
from .melody import Note
from .timing import Grid, quantize, snap_length


@dataclass
class CleanSettings:
    strength: float = 0.7  # how far notes move toward the grid (PLAN §D3)
    snap_scale: bool = True
    key_rank: int = 0  # 0 = most likely key; 1 = second reading ("not what I hummed")
    drum_strength: float = 0.85


def clean_melody(notes: list[Note], grid: Grid, s: CleanSettings) -> tuple[list[dict], dict]:
    if not notes:
        return [], {"keys": [], "tuning_offset": 0.0}
    raw_p = np.array([n.pitch for n in notes])
    dur = np.array([n.duration for n in notes])
    offset = keymod.tuning_offset(raw_p, dur)
    tuned = raw_p - offset

    # Octave errors from the pitch tracker: a lone note an octave away from both neighbours.
    for i in range(1, len(tuned) - 1):
        a, b, c = tuned[i - 1], tuned[i], tuned[i + 1]
        if abs(a - c) <= 5:
            for shift in (-12, 12):
                if abs(b + shift - a) <= 5 and abs(b + shift - c) <= 5 and abs(b - a) > 9:
                    tuned[i] = b + shift

    keys = keymod.detect(tuned, dur)
    k = keys[min(s.key_rank, len(keys) - 1)]

    onsets = np.array([n.onset for n in notes])
    ends = onsets + dur
    b_on = grid.beats(onsets)
    b_end = grid.beats(ends)
    q_on = quantize(b_on, strength=s.strength, swing=grid.swing)
    q_full = quantize(b_on, strength=1.0, swing=grid.swing)

    out = []
    for i, n in enumerate(notes):
        length = b_end[i] - b_on[i]
        # Very short blips are dropped unless they sit right on a beat (PLAN §D5).
        if n.duration < 0.05 and abs(b_on[i] - np.round(b_on[i])) > 0.1:
            continue
        if s.snap_scale:
            midi, chromatic = keymod.snap(tuned[i], k["tonic"], k["mode"], length)
        else:
            midi, chromatic = int(round(tuned[i])), False
        out.append({
            "start": float(q_on[i]),
            "grid_start": float(q_full[i]),
            "length": float(snap_length(length, grid.swing)),
            "pitch": int(midi),
            "velocity": n.velocity,
            "chromatic": bool(chromatic),
            "raw_pitch": round(float(raw_p[i]), 2),
        })
    # Monophonic line: a note ends where the next one starts.
    out.sort(key=lambda d: d["start"])
    for a, b in zip(out, out[1:]):
        a["length"] = float(min(a["length"], max(0.25, b["grid_start"] - a["grid_start"])))
    # Merge stutters: the same pitch re-hit within a 16th, the second one tiny.
    merged = []
    for d in out:
        if merged and d["pitch"] == merged[-1]["pitch"] and d["grid_start"] - merged[-1]["grid_start"] < 0.25 \
                and d["length"] <= 0.25:
            merged[-1]["length"] += d["length"]
            continue
        merged.append(d)
    return merged, {"keys": keys, "key": k, "tuning_offset": round(offset, 3)}


def clean_drums(hits: list[Hit], grid: Grid, s: CleanSettings) -> list[dict]:
    if not hits:
        return []
    b = grid.beats([h.onset for h in hits])
    q = quantize(b, strength=s.drum_strength, swing=grid.swing, subdiv=4)
    return [{"start": float(qq), "name": h.name, "velocity": h.velocity, "confidence": round(h.confidence, 3)}
            for qq, h in zip(q, hits)]


def phrases(notes: list[dict]) -> list[dict]:
    """Phrase ends: a rest of a beat or more, or a note of two beats or more (PLAN §D6)."""
    if not notes:
        return []
    out, start = [], notes[0]["start"]
    for a, b in zip(notes, notes[1:]):
        gap = b["start"] - (a["start"] + a["length"])
        if gap >= 1.0 or a["length"] >= 2.0:
            out.append({"start": round(start, 3), "end": round(a["start"] + a["length"], 3)})
            start = b["start"]
    last = notes[-1]
    out.append({"start": round(start, 3), "end": round(last["start"] + last["length"], 3)})
    for p in out:
        p["bars"] = round((p["end"] - p["start"]) / 4, 2)
    return out
