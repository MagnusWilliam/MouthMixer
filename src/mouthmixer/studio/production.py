"""Producing a full song by hand-written arrangement (docs/PERSONA_PRODUCTION.md): the building blocks.

Chord spellings, voice-led upper-structure voicings (no root, a second inside: "dissonant in the right
place"), 16-step drum and percussion patterns, bass lines that lock to the chord hits and fill before every
change, and helpers to place everything in song beats. A production module (e.g. `last_train`) writes the
parts with these; `build_song` turns them into an `arranger.Song` the app can render, mix and sing over.
"""

from __future__ import annotations

import re

import numpy as np

from ..arrange import theory
from ..arrange.arranger import Song, Track

NOTE = {"C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3, "E": 4, "F": 5, "F#": 6, "Gb": 6, "G": 7, "G#": 8,
        "Ab": 8, "A": 9, "A#": 10, "Bb": 10, "B": 11}
# Spellings in semitones above the root: (chord tones, the app's quality name for display)
SHAPES = {
    "": ([0, 4, 7], "maj"), "m": ([0, 3, 7], "min"), "7": ([0, 4, 7, 10], "dom7"), "9": ([0, 4, 7, 10, 14], "dom9"),
    "m7": ([0, 3, 7, 10], "min7"), "m9": ([0, 3, 7, 10, 14], "min9"), "m11": ([0, 3, 7, 10, 14, 17], "min11"),
    "maj7": ([0, 4, 7, 11], "maj7"), "6/9": ([0, 4, 7, 9, 14], "maj6"),
    "sus4": ([0, 5, 7], "sus4"), "m7b5": ([0, 3, 6, 10], "min7b5"), "maj9": ([0, 4, 7, 11, 14], "maj9"), "7sus4": ([0, 5, 7, 10], "dom7sus4"), "7#5#9": ([0, 4, 8, 10, 15], "dom7s9"),
}


def n(name: str) -> int:
    """'D4' -> 62, 'Bb2' -> 46 (C4 = 60)."""
    m = re.fullmatch(r"([A-G][#b]?)(-?\d)", name)
    return NOTE[m[1]] + (int(m[2]) + 1) * 12


def chord(name: str) -> tuple[int, list[int], str, int | None]:
    """'Am7/E' -> (root pc 9, intervals, quality, bass pc 4)."""
    m = re.fullmatch(r"([A-G][#b]?)(.*?)(?:/([A-G][#b]?))?", name)
    root = NOTE[m[1]]
    ints, quality = SHAPES[m[2]]
    return root, ints, quality, NOTE[m[3]] if m[3] else None


def tones(name: str) -> set[int]:
    root, ints, _, _ = chord(name)
    return {(root + i) % 12 for i in ints}


def upper(name: str, prev: list[int] | None, lo: int = 52, hi: int = 74, size: int = 4) -> list[int]:
    """A rootless voicing (3rd, 7th, 9th, 5th or 11th/13th) between lo and hi, as close to `prev` as
    possible, keeping a second inside when the chord has a 9th (the Persona "dissonant but chill" colour)."""
    root, ints, _, _ = chord(name)
    pcs = [(root + i) % 12 for i in ints if i % 12 != 0]
    if len(pcs) < size and (root + 2) % 12 not in pcs:  # add the 9th (the colour), not the root
        pcs = pcs + [(root + 2) % 12]
    if len(pcs) < size:
        pcs = pcs + [root % 12]
    pcs = pcs[:size] if len(pcs) > size else pcs
    best, best_cost = None, 1e9
    for base in range(lo, hi):
        v = []
        for pc in pcs:
            k = base + (pc - base) % 12
            v.append(k)
        v = sorted(v)
        if v[-1] > hi or v[0] < lo:
            continue
        cost = sum(abs(a - b) for a, b in zip(v, prev)) if prev and len(prev) == len(v) else abs(np.mean(v) - (lo + hi) / 2)
        if cost < best_cost:
            best, best_cost = v, cost
    return best or sorted(lo + (pc - lo) % 12 for pc in pcs)


def grid(pattern: str, start: float, pitch, vel: int | dict = 100, length: float = 0.2, step: float = 0.25):
    """Notes from a 16-step string: 'x' hit, 'X' accent (+20), 'g' ghost (35), 'o' (open/alt: velocity 90)."""
    out = []
    for i, c in enumerate(pattern):
        if c in ".-| ":
            continue
        v = {"x": vel if isinstance(vel, int) else vel.get("x", 100), "X": min(127, (vel if isinstance(vel, int) else 100) + 20),
             "g": 35, "o": 90}.get(c, vel if isinstance(vel, int) else 100)
        p = pitch(c) if callable(pitch) else pitch
        out.append((start + i * step, length, p, int(v)))
    return out


def humanise(notes, rng, vel_sd: float = 5.0, accent_beats=(0.0, 2.0)):
    """Velocity variation and a little accent on strong beats."""
    out = []
    for s, l, p, v in notes:
        acc = 6 if (s % 4) in accent_beats else 0
        out.append((round(s, 4), l, p, int(np.clip(v + acc + rng.normal(0, vel_sd), 1, 127))))
    return out


def bass_line(chords_by_bar: list[str], start_bar: int, style: str, rng, low: int = 33, high: int = 55):
    """(main notes, ghost notes) for the finger bass. Roots land with the chord hits; the last 8th or 16th
    before a change approaches the next root (chromatic or by step); octave jumps and dead-note ghosts keep
    it moving. Styles: funk, lean, push, halftime, pedal, riff (intro unison)."""
    main, ghosts = [], []
    for i, nm in enumerate(chords_by_bar):
        parts = nm.split("|")
        nxt = (chords_by_bar[i + 1].split("|")[0] if i + 1 < len(chords_by_bar) else parts[-1])
        b0 = (start_bar + i) * 4
        for j, part in enumerate(parts):
            root, ints, _, slash = chord(part)
            r = low + ((slash if slash is not None else root) - low) % 12
            if r + 12 <= high and r < 38:
                r += 12 if rng.random() < 0.3 else 0
            fifth = r + 7 if r + 7 <= high else r - 5
            octave = r + 12 if r + 12 <= high else r
            span = 4 / len(parts)
            s0 = b0 + j * span
            last = j == len(parts) - 1
            nroot = chord(nxt)[0]
            target = low + (nroot - low) % 12
            appr = target - 1 if rng.random() < 0.6 else target + (2 if target + 2 <= high else -2)
            if span < 4:  # a split bar: root, then a pickup
                main += [(s0, span * 0.45, r, 100), (s0 + span * 0.5, span * 0.3, octave, 84)]
                if last:
                    main.append((s0 + span - 0.25, 0.22, appr, 88))
                continue
            if style == "funk":
                main += [(s0, 0.45, r, 108), (s0 + 1.0, 0.2, octave, 88), (s0 + 1.5, 0.45, r, 96),
                         (s0 + 2.5, 0.4, fifth, 92), (s0 + 3.0, 0.2, octave, 86), (s0 + 3.5, 0.4, appr, 94)]
                ghosts += [(s0 + 0.75, 0.1, r, 60), (s0 + 2.25, 0.1, r, 55), (s0 + 3.25, 0.1, octave, 50)]
            elif style == "lean":
                main += [(s0, 0.7, r, 104), (s0 + 1.5, 0.45, r, 90), (s0 + 2.75, 0.2, octave, 84),
                         (s0 + 3.0, 0.45, fifth, 88), (s0 + 3.5, 0.4, appr, 90)]
                ghosts += [(s0 + 2.5, 0.1, r, 52)]
            elif style == "push":
                main += [(s0, 0.9, r, 110), (s0 + 1.0, 0.45, r, 92), (s0 + 1.5, 0.2, octave, 88),
                         (s0 + 2.0, 0.45, fifth, 94), (s0 + 2.75, 0.45, octave, 90)]
                ghosts += [(s0 + 0.75, 0.1, r, 58), (s0 + 2.5, 0.1, fifth, 52)]
                main.append((s0 + 3.5, 0.6, target if not last or nxt else appr, 100))  # pushes the next chord early
            elif style == "halftime":
                main += [(s0, 1.4, r, 112), (s0 + 1.75, 0.2, r, 86), (s0 + 2.5, 0.45, octave, 90),
                         (s0 + 3.25, 0.7, appr, 96)]
                ghosts += [(s0 + 1.5, 0.1, r, 55)]
            elif style == "pedal":
                main.append((s0, span * 0.95, r, 90))
            else:
                raise ValueError(style)
    # a pushed note replaces the next bar's downbeat root (no double attack)
    main.sort()
    clean = []
    for s, l, p, v in main:
        if clean and abs(clean[-1][0] - s) < 1e-6:
            continue
        if clean and clean[-1][0] + clean[-1][1] > s:
            ps, pl, pp, pv = clean[-1]
            clean[-1] = (ps, max(0.05, s - ps - 0.02), pp, pv)
        clean.append((s, l, p, v))
    # the push already plays the new root: drop the downbeat root right after it
    out = []
    for s, l, p, v in clean:
        if out and s % 4 == 0 and out[-1][0] == s - 0.5 and out[-1][2] == p:
            ps, pl, pp, pv = out[-1]
            out[-1] = (ps, pl + l, pp, pv)
            continue
        out.append((s, l, p, v))
    return out, ghosts


def clear_of(notes: list, melody: list, chord_at) -> list:
    """Keep harmony out of a half step's way of the melody note sounding with it (MUSIC_KNOWLEDGE H1): a chord
    tone a minor 2nd from the melody (or a minor 9th under it) moves down to the next chord tone that doesn't
    rub, or is dropped. The 9ths and 7ths stay everywhere the singer isn't leaning on the note next to them."""
    out = []
    for s, l, p, v in notes:
        mel = [m for m in melody if m[0] < s + l and m[0] + m[1] > s]

        def rubs(q):
            return any(abs(m[2] - q) == 1 or (q < m[2] and (m[2] - q) % 12 == 1 and m[2] - q > 12) for m in mel)

        if not rubs(p):
            out.append((s, l, p, v))
            continue
        pcs = tones(chord_at(s))
        for q in range(p - 1, p - 8, -1):
            if q % 12 in pcs and not rubs(q):
                out.append((s, l, q, v))
                break
    return out


def build_song(pack: str, bpm: float, tonic: int, mode: str, sections, chords_by_bar: list[str], tracks: list[Track],
               seed: int = 1) -> Song:
    """An arranger.Song from a hand-written arrangement (one chord name per bar, 'A|B' for two)."""
    ch = []
    for bar, nm in enumerate(chords_by_bar):
        parts = nm.split("|")
        for j, part in enumerate(parts):
            root, _, quality, _ = chord(part)
            ch.append((bar * 4 + j * 4 / len(parts), 4 / len(parts), theory.Chord(root, quality, "", "C")))
    return Song(pack=pack, bpm=bpm, tonic=tonic, mode=mode, swing=0.5, sections=sections, chords=ch, tracks=tracks,
                seed=seed)


def swing(notes: list, amount: float) -> list:
    """Swung 8ths: every note on an off-beat 8th moves later, to `amount` of the beat (0.5 straight, 0.62
    a jazz swing, 0.67 a full triplet)."""
    if abs(amount - 0.5) < 1e-3:
        return notes
    out = []
    for s, l, p, v in notes:
        frac = s % 1
        if abs(frac - 0.5) < 1e-3:
            s = s - 0.5 + amount
        out.append((s, l, p, v))
    return out


def add_version(song_dir, song: Song, gains: dict, title: str, base: dict | None = None, extra: dict | None = None) -> int:
    """Put a produced song into an app song as a new version: summary, mixer state (levels and pans from
    `gains` and the tracks), stems through the app's mixer, the match-EQ'd master and the critic's verdict.
    `base`: the version the words and section feels come from (default: the newest with a lyric sheet, or the
    newest). Backs up song.json first. Returns the version index."""
    import json
    import shutil
    import time
    from pathlib import Path

    from ..arrange import critic, mixer, render
    from ..arrange.songwriter import song_summary

    song_dir = Path(song_dir)
    rec_path = song_dir / "song.json"
    shutil.copy2(rec_path, song_dir / f"song.backup-{time.strftime('%Y%m%d-%H%M%S')}.json")
    record = json.loads(rec_path.read_text())
    if base is None:
        base = next((v for v in reversed(record["versions"]) if v.get("lyric_sheet")), record["versions"][-1])
    idx_file = mixer.next_version_index(song_dir, record)
    new = {k: v for k, v in base.items() if k not in ("vocal_stem", "vocal_stems", "vocals", "vocal_tracks",
                                                       "audio_parts", "working", "mixed_from", "mixed_at")}
    new.update(song_summary(song))
    new.update({"file": f"v{idx_file}.ogg", "midi": f"v{idx_file}.mid", "title": title, "made_at": time.time(),
                "added": [t.name for t in song.tracks], "critic": {"ok": True, "score": 0.0}, "score": 0.0})
    new.update(extra or {})
    record["versions"].append(new)
    vi = len(record["versions"]) - 1
    parts = [{"id": f"p{i}", "name": t.name, "role": t.role, "instrument": t.instrument, "kind": f"orig:{t.role}",
              "mine": False, "muted": False, "gain_db": float(gains.get(t.name, 0.0)), "pan": t.pan,
              "notes": [list(x) for x in t.notes]} for i, t in enumerate(song.tracks)]
    mixer.write_json(song_dir / f"mixer-v{vi}.json", {"version": vi, "parts": parts, "next_id": len(parts),
                                                      "lead_mode": "duck"})
    mixer.write_json(rec_path, record)
    m = mixer.Mixer(song_dir, vi)
    m.render_stems()
    sng = m.song(False)
    _, n_ = render.song_length(sng)
    music, lead, _, stems = m._stems(n_)
    out, _ = render.match_tone(music + lead, amount=0.9, limit_db=4.0)
    mix = render.master(out)
    verdict = critic.judge(sng, mix, stems)
    render.write_audio(mix, song_dir / f"v{idx_file}.ogg")
    render.write_midi(sng, song_dir / f"v{idx_file}.mid")
    record = json.loads(rec_path.read_text())
    record["versions"][vi].update({"critic": verdict, "score": verdict["score"]})
    mixer.write_json(rec_path, record)
    return vi
