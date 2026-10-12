"""One clip in, everything out: the verdict, raw and clean notes, drums, tempo, key, phrases, MIDI files
and a listenable preview (PLAN.md stages B-D)."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

import librosa
import numpy as np
import pretty_midi
import soundfile as sf

from .. import synth
from . import beatbox, cleanup, detect, melody, pitch, timing

ANALYSIS_SR = 16000
MIDI_PROGRAM = 4  # Electric Piano 1

# The readings "not what I hummed" steps through, in order (PLAN §7.10 / Phase 2 done-when).
READINGS = [
    {},
    {"tempo_factor": 0.5},
    {"tempo_factor": 2.0},
    {"strength": 0.35},
    {"key_rank": 1},
    {"snap_scale": False},
]


def load(path: Path) -> tuple[np.ndarray, int]:
    y, sr = sf.read(str(path), dtype="float32", always_2d=True)
    return y.mean(axis=1), sr


def analyse(y: np.ndarray, sr: int, *, reading: dict | None = None, calibration: beatbox.Calibration | None = None,
            verdict: detect.Verdict | None = None) -> dict:
    reading = reading or {}
    y16 = librosa.resample(y, orig_sr=sr, target_sr=ANALYSIS_SR) if sr != ANALYSIS_SR else y
    y16 = y16 / (np.max(np.abs(y16)) + 1e-9) * 0.5
    verdict = verdict or detect.judge(y16, ANALYSIS_SR)
    kind = verdict.kind if verdict.kind != "none" else "melody"

    tr = pitch.track(y16, ANALYSIS_SR)
    notes = melody.transcribe(tr) if kind in ("melody", "both") else []
    hits: list[beatbox.Hit] = []
    if kind in ("beat", "both"):
        hits = beatbox.transcribe(y16, ANALYSIS_SR, calibration, mask_voiced=tr.voiced if kind == "both" else None)

    # Tempo from everything that has an onset. Long notes and kicks/snares count most.
    on = [n.onset for n in notes] + [h.onset for h in hits]
    w = [min(2.0, 0.5 + n.duration) for n in notes] + [1.5 if h.name in ("kick", "snare") else 0.6 for h in hits]
    grid = timing.fit_tempo(on, w, subdiv=4 if hits else 2)
    factor = reading.get("tempo_factor", 1.0)
    if factor != 1.0:
        grid.bpm *= factor
    grid.downbeat = 0
    on_a, w_a = np.array(on), np.array(w)
    kicks = np.array([h.onset for h in hits if h.name == "kick"])
    snares = np.array([h.onset for h in hits if h.name == "snare"])
    if len(on_a):
        grid.downbeat = timing.find_downbeat(grid, on_a, w_a, kicks, snares)
        # Pickup notes before the first downbeat get negative beats; shift so bar 1 starts at 0.
        first = float(np.min(grid.beats(on_a)))
        if first < -0.5:
            grid.downbeat -= int(np.ceil(-first / grid.meter)) * grid.meter
        # Measure the swing on the final grid; keep the fitted value when too few off-beats to tell.
        measured = timing.detect_swing(grid, on_a)
        grid.swing = measured if measured > 0.5 or grid.swing <= 0.5 else grid.swing

    settings = cleanup.CleanSettings(
        strength=reading.get("strength", 0.7),
        snap_scale=reading.get("snap_scale", True),
        key_rank=reading.get("key_rank", 0),
    )
    clean_notes, key_info = cleanup.clean_melody(notes, grid, settings)
    clean_drums = cleanup.clean_drums(hits, grid, settings)
    return {
        "verdict": verdict.to_dict(),
        "kind": kind,
        "reading": reading,
        "tempo": grid.to_dict(),
        "grid": {k: v for k, v in asdict(grid).items() if k != "alternatives"},
        "key": key_info.get("key"),
        "keys": key_info.get("keys", []),
        "tuning_offset": key_info.get("tuning_offset", 0.0),
        "notes_raw": [n.to_dict() for n in notes],
        "notes": clean_notes,
        "drums_raw": [h.to_dict() for h in hits],
        "drums": clean_drums,
        "phrases": cleanup.phrases(clean_notes),
        "duration": round(len(y) / sr, 3),
    }


def write_midi(result: dict, path: Path, clean: bool = True) -> None:
    bpm = result["tempo"]["bpm"]
    pm = pretty_midi.PrettyMIDI(initial_tempo=bpm)
    spb = 60.0 / bpm
    if clean:
        lead = pretty_midi.Instrument(program=MIDI_PROGRAM, name="melody")
        for n in result["notes"]:
            s = max(0.0, n["start"]) * spb
            lead.notes.append(pretty_midi.Note(n["velocity"], n["pitch"], s, s + n["length"] * spb))
        drums = pretty_midi.Instrument(program=0, is_drum=True, name="drums")
        for d in result["drums"]:
            s = max(0.0, d["start"]) * spb
            drums.notes.append(pretty_midi.Note(d["velocity"], beatbox.GM.get(d["name"], 38), s, s + 0.1))
    else:
        lead = pretty_midi.Instrument(program=MIDI_PROGRAM, name="melody (raw)")
        for n in result["notes_raw"]:
            p = int(round(n["pitch"]))
            lead.notes.append(pretty_midi.Note(n["velocity"], p, n["onset"], n["onset"] + n["duration"]))
        drums = pretty_midi.Instrument(program=0, is_drum=True, name="drums (raw)")
        for h in result["drums_raw"]:
            drums.notes.append(pretty_midi.Note(h["velocity"], beatbox.GM.get(h["name"], 38), h["onset"], h["onset"] + 0.1))
    if lead.notes:
        pm.instruments.append(lead)
    if drums.notes:
        pm.instruments.append(drums)
    pm.write(str(path))


def process_file(audio_path: Path, out_dir: Path, *, reading: dict | None = None,
                 calibration: beatbox.Calibration | None = None, verdict: detect.Verdict | None = None) -> dict:
    """Analyse one clip and write result.json, raw.mid, clean.mid and preview.wav into out_dir."""
    out_dir.mkdir(parents=True, exist_ok=True)
    y, sr = load(audio_path)
    result = analyse(y, sr, reading=reading, calibration=calibration, verdict=verdict)
    write_midi(result, out_dir / "clean.mid", clean=True)
    write_midi(result, out_dir / "raw.mid", clean=False)
    preview = synth.render_preview(
        [{**n, "start": max(0.0, n["start"])} for n in result["notes"]],
        [{**d, "start": max(0.0, d["start"])} for d in result["drums"]],
        result["tempo"]["bpm"],
    )
    sf.write(str(out_dir / "preview.wav"), preview, 22050)
    (out_dir / "result.json").write_text(json.dumps(result, indent=1))
    return result
