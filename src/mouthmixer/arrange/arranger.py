"""The arranger (PLAN.md §7): your melody and/or beat + a style pack -> a full multi-instrument song.

Steps: fit the melody to the style's tempo and to bars; harmonise it (beam search over the pack's chord
vocabulary, scored on melody fit, functional flow and cadences); write bass, comping, pad, arpeggio,
counter-line and drums from the pack's patterns; lay out a game-friendly form
(intro, A, A', B, A'', ending) with layers building up; and record what is yours and what was added.
Every choice comes from a seeded random generator, so any result can be rebuilt exactly.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from . import theory
from .styles import DRUM, INSTRUMENTS, PACKS, VEL


@dataclass
class Track:
    name: str
    role: str  # lead, comp, pad, bass, arp, counter, drums, timpani
    instrument: str  # key in INSTRUMENTS, or "kit:<name>" for drums
    notes: list = field(default_factory=list)  # (start_beat, length_beats, pitch, velocity)
    mine: bool = False  # made from the user's own clip
    pan: float = 0.0  # -1 left .. 1 right


@dataclass
class Song:
    pack: str
    bpm: float
    tonic: int
    mode: str
    swing: float
    sections: list  # (name, start_bar, bars)
    chords: list  # (start_beat, length_beats, Chord)
    tracks: list
    seed: int
    notes_for_user: list = field(default_factory=list)  # human-readable "what was added"
    sources: dict = field(default_factory=dict)

    @property
    def bars(self) -> int:
        return sum(b for _, _, b in self.sections)

    @property
    def key_name(self) -> str:
        return f"{theory.NAMES[self.tonic]} {self.mode}"

    def chord_at(self, beat: float):
        for s, length, c in self.chords:
            if s <= beat < s + length:
                return c
        return None


# --------------------------------------------------------------------------------------------------
# Melody preparation
# --------------------------------------------------------------------------------------------------

def _scale_pcs(tonic: int, mode: str) -> list[int]:
    return [(tonic + i) % 12 for i in theory.MODES.get(mode, theory.MODES["major"])]


def prepare_melody(notes: list[dict], max_bars: int = 16) -> list[tuple]:
    """Clean notes (beats) -> (start, length, pitch, vel) starting in bar 0, at most `max_bars` long."""
    if not notes:
        return []
    # Finished songs sit on the grid (the swing grid when the clip swung): polish over the raw feel.
    key = "grid_start" if all("grid_start" in n for n in notes) else "start"
    first = min(n[key] for n in notes)
    shift = -math.floor(first / 4) * 4  # keep pickups' position inside the bar
    out = []
    for n in sorted(notes, key=lambda n: n[key]):
        s = n[key] + shift
        if s >= max_bars * 4:
            break
        out.append((s, max(0.25, n["length"]), int(n["pitch"]), int(n.get("velocity", 90))))
    return out


def scale_time(mel: list[tuple], factor: float) -> list[tuple]:
    return [(s * factor, l * factor, p, v) for s, l, p, v in mel]


def section_bars(mel: list[tuple]) -> int:
    end = max(s + l for s, l, _, _ in mel)
    bars = max(1, math.ceil(end / 4 - 0.05))
    for size in (4, 8, 16):
        if bars <= size:
            return size
    return 16


def fill_section(mel: list[tuple], bars: int, tonic: int, mode: str) -> list[tuple]:
    """Repeat a short idea to fill the section; the last repeat ends on a stable note (an "answer")."""
    if not mel:
        return []
    length = max(1, math.ceil(max(s + l for s, l, _, _ in mel) / 4 - 0.05)) * 4
    out = []
    k = 0
    while k * length < bars * 4:
        for s, l, p, v in mel:
            if s + k * length < bars * 4:
                out.append((s + k * length, min(l, bars * 4 - (s + k * length)), p, v))
        k += 1
    # Answer phrase: make the final note a tonic-chord tone and let it ring.
    if out:
        s, l, p, v = out[-1]
        stable = {tonic % 12, (tonic + (3 if mode in ("minor", "dorian") else 4)) % 12, (tonic + 7) % 12}
        if p % 12 not in stable:
            p = min((p + d for d in range(-4, 5) if (p + d) % 12 in stable), key=lambda q: abs(q - p))
        out[-1] = (s, max(l, bars * 4 - s), p, v)
    return out


def diatonic_shift(mel: list[tuple], steps: int, tonic: int, mode: str) -> list[tuple]:
    """Move a melody up/down by scale steps (a sequence), staying in the key."""
    scale = theory.MODES.get(mode, theory.MODES["major"])
    out = []
    for s, l, p, v in mel:
        rel = (p - tonic) % 12
        deg = min(range(7), key=lambda d: abs(scale[d] - rel))
        octave = (p - tonic - scale[deg]) // 12
        nd = deg + steps
        np_ = tonic + scale[nd % 7] + 12 * (octave + nd // 7)
        out.append((s, l, int(np_), v))
    return out


def develop(mel: list[tuple], bars: int, tonic: int, mode: str, rng) -> list[tuple]:
    """A B section grown from the first idea (MUSIC_KNOWLEDGE §5 F1, PLAN §7.12): the motif sequenced up
    and back down, ending on a long note over the dominant so it leads back to A."""
    motif_len = 8 if bars >= 8 else 4
    motif = [n for n in mel if n[0] < motif_len]
    if not motif:
        return mel
    steps = [2, 1, 0] if rng.random() < 0.6 else [1, 3, 2]
    out = []
    for i, st in enumerate(steps):
        off = i * motif_len
        if off >= bars * 4 - 4:
            break
        for s, l, p, v in diatonic_shift(motif, st, tonic, mode):
            if s + off < bars * 4 - 4:
                out.append((s + off, l, p, v))
    # Last bars: a held scale degree 2 or 5, over the dominant (a half cadence).
    last_start = (bars - 2) * 4 if bars >= 8 else (bars - 1) * 4
    out = [n for n in out if n[0] < last_start]
    prev = out[-1][2] if out else (mel[0][2] if mel else 72)
    target_pcs = [(tonic + 7) % 12, (tonic + 2) % 12]
    p = min((prev + d for d in range(-7, 8) if (prev + d) % 12 in target_pcs), key=lambda q: abs(q - prev))
    out.append((last_start, bars * 4 - last_start, p, 92))
    return out


def compose(chords: list, bars: int, tonic: int, mode: str, rng, centre: int = 74) -> list[tuple]:
    """A melody for beat-only songs (PLAN §7.12 additions): a 2-bar rhythm motif, chord tones on strong
    beats, steps between them, repeated with variation, ending on the tonic."""
    cells = [[1, 0.5, 0.5, 1, 1], [0.5, 0.5, 1, 0.5, 0.5, 1], [1.5, 0.5, 1, 1], [0.5, 1, 0.5, 2], [1, 1, 2]]
    motif = [cells[rng.integers(len(cells))], cells[rng.integers(len(cells))]]
    scale = _scale_pcs(tonic, mode)
    out = []
    prev = centre
    for bar in range(bars):
        cell = motif[bar % 2]
        if bar % 4 == 3:
            cell = [2, 2] if rng.random() < 0.5 else [1, 1, 2]  # breathe at phrase ends
        t = 0.0
        for d in cell:
            beat = bar * 4 + t
            chord = next((c for s, l, c in chords if s <= beat < s + l), chords[-1][2])
            strong = abs(t - round(t)) < 1e-6 and (int(round(t)) % 2 == 0 or d >= 1)
            pool = chord.tones() if strong else scale
            cands = [prev + k for k in range(-5, 6) if (prev + k) % 12 in pool and abs(prev + k - centre) <= 9]
            if not cands:
                cands = [prev]
            weights = np.array([1.0 / (1 + abs(c - prev)) for c in cands])
            p = int(rng.choice(cands, p=weights / weights.sum()))
            out.append((beat, d * 0.95, p, 88 if strong else 76))
            prev = p
            t += d
    # Final note: tonic.
    s, l, p, v = out[-1]
    out[-1] = (s, bars * 4 - s, min((p + k for k in range(-6, 7) if (p + k) % 12 == tonic), key=lambda q: abs(q - p)), v)
    return out


# --------------------------------------------------------------------------------------------------
# Harmony
# --------------------------------------------------------------------------------------------------

def chord_set(pack: dict, tonic: int, mode: str, ext: str) -> list:
    base_mode = "minor" if mode in ("minor", "dorian") else "major"
    chords = theory.diatonic(tonic, mode if mode in theory.MODES else base_mode, ext)
    allowed = list(pack["borrowed"])
    if base_mode == "minor":
        allowed = [b for b in allowed if b not in ("iv", "bVI", "bVII", "bIII")] + ["V7"]
    chords += theory.borrowed(tonic, base_mode, allowed, ext)
    # Drop the diminished vii in pop styles: it rarely sounds good in this music.
    return [c for c in chords if c.quality not in ("dim", "aug") or pack["tension"] > 0.75]


def harmonise(mel: list[tuple], bars: int, pack: dict, tonic: int, mode: str, ext: str, rng,
              per_bar: int = 1, end: str = "tonic", beam: int = 10) -> list:
    """Chords for `bars` bars under the melody. Returns [(start_beat, length, Chord)].

    Score = melody fit (strong beats and long notes count most, MUSIC_KNOWLEDGE M11/H1) + functional flow
    (H2) + cadence at the end (H3/H14) + a little noise so each seed finds a different good answer."""
    chords = chord_set(pack, tonic, mode, ext)
    slot_len = 4 / per_bar
    n_slots = bars * per_bar
    weights, held = [], []
    for i in range(n_slots):
        a, b = i * slot_len, (i + 1) * slot_len
        w = np.zeros(12)
        h = set()
        for s, l, p, _ in mel:
            ov = min(b, s + l) - max(a, s)
            if ov <= 0:
                continue
            strength = 1.6 if abs((max(a, s) % 2)) < 1e-6 else 1.0  # notes starting on beats 1/3 matter more
            w[p % 12] += ov * strength
            # A note that starts on a beat inside this slot and is held a beat or more: it must not be an
            # avoid note (the critic rejects that, MUSIC_KNOWLEDGE H1).
            if a - 1e-6 <= s < b and abs(s - round(s)) < 0.05 and l >= 1.0:
                h.add(p % 12)
        weights.append(w)
        held.append(h)
    beams = [(0.0, [])]
    for i in range(n_slots):
        nxt = []
        for score, path in beams:
            prev = path[-1] if path else None
            for c in chords:
                fit = 0.0
                for pc in range(12):
                    if weights[i][pc] > 0:
                        f = c.fit(pc, pack["tension"])
                        fit += weights[i][pc] * (f if f >= 0 else 2.0 * f)  # clashes cost double
                if any(c.fit(pc, pack["tension"]) <= -1.0 for pc in held[i]):
                    fit -= 8.0
                s = score + 1.4 * fit + theory.transition(prev, c) + rng.normal(0, 0.25)
                if i == 0 and c.function != "T" and c.degree not in ("IV", "IVmaj7", "IVmaj9", "ii7", "ii9", "iv"):
                    s -= 0.8
                if path.count(c) >= max(2, n_slots // 3):
                    s -= 0.6  # variety
                # Phrase ends (every 4 bars): favour a cadence.
                if (i + 1) % (4 * per_bar) == 0 and i != n_slots - 1:
                    s += 0.3 if c.function in ("D", "T") else -0.2
                if i == n_slots - 1:
                    if end == "tonic":
                        s += 1.2 if c.function == "T" and c.root == tonic else -0.6
                    else:  # "loop" or "half": land on the dominant so it turns around
                        s += 1.2 if c.function == "D" else -0.4
                nxt.append((s, path + [c]))
        nxt.sort(key=lambda x: -x[0])
        beams = nxt[:beam]
    best = beams[0][1]
    return [(i * slot_len, slot_len, c) for i, c in enumerate(best)]


_NUMERALS = {"I": 0, "II": 2, "III": 4, "IV": 5, "V": 7, "VI": 9, "VII": 11}


def resolve_degree(name: str, tonic: int, ext: str) -> theory.Chord:
    """A roman numeral as written in a style's favourite loops ("i", "bVI", "IV", "V", "bII") -> a chord.
    Case gives major/minor, b/# move the root, offsets count from the major scale (so "bVI" in a minor key
    is the usual C chord in E minor). Sevenths follow the style's extension: V and bVII get dominant
    7ths, other major chords major 7ths, minor chords minor 7ths."""
    acc = 0
    n = name
    while n and n[0] in "b#":
        acc += -1 if n[0] == "b" else 1
        n = n[1:]
    core = n.rstrip("0123456789")
    upper = core.upper()
    off = (_NUMERALS.get(upper, 0) + acc) % 12
    minor = core != upper
    if ext == "triad":
        q = "min" if minor else "maj"
    elif minor:
        q = "min9" if ext == "ninth" else "min7"
    elif off in (7, 10):
        q = "dom9" if ext == "ninth" else "dom7"
    else:
        q = "maj9" if ext == "ninth" else "maj7"
    fn = "T" if off in (0, 3, 4, 8, 9) else "D" if off in (7, 11) else "PD"
    return theory.Chord((tonic + off) % 12, q, name, fn)


def progression_from_favourite(pack: dict, tonic: int, mode: str, ext: str, bars: int, rng,
                               fav: list[str] | None = None) -> list:
    """One of the style's favourite loops (or `fav`), one chord per bar, repeated to fill `bars`."""
    fav = fav or pack["favourites"][rng.integers(len(pack["favourites"]))]
    seq = [resolve_degree(d, tonic, ext) for d in fav]
    return [(i * 4, 4, seq[i % len(seq)]) for i in range(bars)]


# --------------------------------------------------------------------------------------------------
# Parts
# --------------------------------------------------------------------------------------------------

def fit_range(notes: list[tuple], instrument: str) -> list[tuple]:
    """Move a part by octaves so it sits in the instrument's range (MUSIC_KNOWLEDGE A4)."""
    if not notes:
        return notes
    _, _, lo, hi, _, _ = INSTRUMENTS[instrument]
    ps = [p for _, _, p, _ in notes]
    best, best_out = 0, 1e9
    for k in range(-4, 5):
        out = sum(1 for p in ps if not lo <= p + 12 * k <= hi)
        centre_cost = abs((min(ps) + max(ps)) / 2 + 12 * k - (lo + hi) / 2) / 100
        if out + centre_cost < best_out:
            best, best_out = k, out + centre_cost
    return [(s, l, min(hi, max(lo, p + 12 * best)), v) for s, l, p, v in notes]


def steps_to_beat(step: int, swing: float) -> float:
    """16th-note step inside a bar -> beat position, with 8th-note swing."""
    beat, sub = divmod(step, 4)
    if swing <= 0.5:
        return beat + sub / 4
    pos = {0: 0.0, 1: swing / 2, 2: swing, 3: swing + (1 - swing) / 2}[sub]
    return beat + pos


def bass_part(chords: list, bars_range: tuple, cell: list, swing: float, rng) -> list:
    out = []
    b0, b1 = bars_range
    for bar in range(b0, b1):
        for step, ln, slot in cell:
            beat = bar * 4 + steps_to_beat(step, swing)
            c = next((c for s, l, c in chords if s <= beat < s + l), None)
            if c is None:
                continue
            root = 36 + (c.root - 36) % 12
            if root > 43:
                root -= 12
            if slot == "R":
                p = root
            elif slot == "5":
                p = root + 7
            elif slot == "8":
                p = root + 12
            elif slot == "3":
                p = root + (theory.QUALITIES[c.quality][1])
            else:  # approach: a half step into the next bar's root
                nb = (bar + 1) * 4
                nc = next((c2 for s, l, c2 in chords if s <= nb < s + l), c)
                nroot = 36 + (nc.root - 36) % 12
                if nroot > 43:
                    nroot -= 12
                p = nroot + (1 if rng.random() < 0.5 else -1)
            out.append((beat, ln / 4 * 0.92, int(p), 96 if step == 0 else 82))
    return out


def dodge(voicing: list[int], melody: list[tuple], start: float, end: float, lo: int) -> list[int]:
    """Keep chord notes out of a half step's way of the melody (MUSIC_KNOWLEDGE H1): a voice a minor 2nd
    from a melody note sounding at the same time moves down an octave (a 7th is fine), or is dropped."""
    sounding = [p for s, l, p, _ in melody if s < end and s + l > start]
    out = []
    for v in voicing:
        def bad(x):
            return any(abs(m - x) == 1 or (m > x and (m - x) % 12 == 1) for m in sounding)
        if bad(v):
            if v - 12 >= lo and not bad(v - 12):
                out.append(v - 12)
            continue
        out.append(v)
    return out or voicing[:1]


def comp_part(chords: list, bars_range: tuple, rhythm: list, swing: float, lo: int, hi: int, rootless: bool,
              spread: bool, vel: int = 76, melody: list | None = None) -> list:
    out = []
    prev = None
    b0, b1 = bars_range
    for bar in range(b0, b1):
        for step, ln in rhythm:
            beat = bar * 4 + steps_to_beat(step, swing)
            c = next((c for s, l, c in chords if s <= beat < s + l), None)
            if c is None:
                continue
            voicing = theory.voice(c, prev, lo, hi, n=4, rootless=rootless, spread=spread)
            prev = voicing
            end = min(beat + ln / 4, next((s + l for s, l, cc in chords if s <= beat < s + l), beat + ln / 4))
            if melody:
                voicing = dodge(voicing, melody, beat, end, lo - 12)
            for p in voicing:
                out.append((beat, max(0.2, end - beat - 0.02), p, vel))
    return out


def pad_part(chords: list, bars_range: tuple, lo: int, hi: int, spread: bool, melody: list | None = None) -> list:
    out = []
    prev = None
    b0, b1 = bars_range
    for s, l, c in chords:
        if not (b0 * 4 <= s < b1 * 4):
            continue
        v = theory.voice(c, prev, lo, hi, n=4, spread=spread)
        prev = v
        if melody:
            v = dodge(v, melody, s, s + l, lo - 12)
        for p in v:
            out.append((s, l - 0.05, p, 58))
    return out


def arp_part(chords: list, bars_range: tuple, lo: int, hi: int, sixteenths: bool, swing: float, rng) -> list:
    out = []
    shapes = [[0, 1, 2, 3, 2, 1, 0, 1], [0, 2, 1, 3, 0, 2, 1, 3], [0, 1, 2, 3, 3, 2, 1, 0]]
    shape = shapes[rng.integers(len(shapes))]
    step = 0.25 if sixteenths else 0.5
    b0, b1 = bars_range
    for s, l, c in chords:
        if not (b0 * 4 <= s < b1 * 4):
            continue
        tones = sorted(set(theory.voice(c, None, lo, hi, n=4)))
        t = 0.0
        i = 0
        while t < l - 1e-6:
            sub = (s + t) % 1
            beat = math.floor(s + t) + (swing if (abs(sub - 0.5) < 1e-6 and not sixteenths and swing > 0.5) else sub)
            out.append((beat, step * 0.9, tones[shape[i % len(shape)] % len(tones)], 62 + (8 if i % 4 == 0 else 0)))
            t += step
            i += 1
    return out


def counter_part(chords: list, bars_range: tuple, lo: int, hi: int) -> list:
    """A guide-tone line: the 3rd or 7th of each chord, whichever moves least (smooth and always right)."""
    out = []
    prev = (lo + hi) // 2
    b0, b1 = bars_range
    for s, l, c in chords:
        if not (b0 * 4 <= s < b1 * 4):
            continue
        ivs = theory.QUALITIES[c.quality]
        guide = [(c.root + ivs[1]) % 12] + ([(c.root + ivs[3]) % 12] if len(ivs) > 3 else [(c.root + 7) % 12])
        cands = [m for m in range(lo, hi + 1) if m % 12 in guide]
        p = min(cands, key=lambda m: abs(m - prev)) if cands else prev
        out.append((s, l - 0.1, p, 64))
        prev = p
    return out


def riff_part(chords: list, bars_range: tuple, instrument: str, rng) -> list:
    """A catchy 2-bar riff, the hook of funk / acid-jazz / J-pop tracks (docs/PERSONA_STYLE.md §6): a
    syncopated rhythm cell on chord tones, repeated every two bars so the ear locks on, following the chords."""
    cells = [[(0, 0.5), (0.75, 0.25), (1.5, 0.5), (2.5, 0.5), (3.25, 0.25)],
             [(0, 0.25), (0.5, 0.25), (1, 0.5), (2, 0.25), (2.75, 0.75)],
             [(0.5, 0.5), (1.5, 0.25), (2, 0.5), (3, 0.25), (3.5, 0.5)]]
    rhythm = [cells[rng.integers(len(cells))], cells[rng.integers(len(cells))]]
    shape = rng.permutation(4)[:3].tolist() + [0]
    i_lo, i_hi = INSTRUMENTS[instrument][2:4]
    lo = max(i_lo, 60)
    out = []
    a, b = bars_range
    for bar in range(a, b):
        for k, (t, d) in enumerate(rhythm[bar % 2]):
            beat = bar * 4 + t
            c = next((c for s, l, c in chords if s <= beat + 1e-6 < s + l), None)
            if c is None:
                continue
            tones = sorted(theory.voice(c, None, lo, min(i_hi, lo + 16), n=4))
            out.append((beat, d * 0.9, tones[shape[k % len(shape)] % len(tones)], 96 if t % 1 == 0 else 84))
    return out


def drum_grid_from_beat(drums: list[dict]) -> dict | None:
    """Turn a transcribed beatbox take into a one-bar 16-step pattern (the bar with the most hits)."""
    if not drums:
        return None
    bars: dict[int, list] = {}
    for d in drums:
        b = int(math.floor(max(0.0, d["start"]) / 4))
        bars.setdefault(b, []).append(d)
    bar, hits = max(bars.items(), key=lambda kv: len(kv[1]))
    names = {"kick": "kick", "snare": "snare", "hat": "hat", "open_hat": "open_hat", "clap": "clap", "rim": "rim"}
    grid: dict[str, list] = {}
    for d in hits:
        step = int(round((d["start"] - bar * 4) * 4)) % 16
        n = names.get(d["name"], "snare")
        row = grid.setdefault(n, ["."] * 16)
        row[step] = "X" if d.get("velocity", 90) > 100 else "x" if d.get("velocity", 90) > 55 else "g"
    return {k: "".join(v) for k, v in grid.items()}


def drum_part(pattern: dict, bars_range: tuple, swing: float, *, fill_last: bool, crash_first: bool,
              variant: str = "full", rng=None) -> list:
    out = []
    b0, b1 = bars_range
    for bar in range(b0, b1):
        last = fill_last and bar == b1 - 1
        for name, row in pattern.items():
            if variant == "light" and name not in ("hat", "shaker", "rim", "pedal_hat"):
                if not (name in ("kick", "concert_bd") and bar % 2 == 0):
                    continue
            if variant == "half" and name in ("snare",):
                row = "........X......."
            note = DRUM.get(name if name != "ghost" else "snare", 38)
            for step, ch in enumerate(row):
                if ch == "." or (last and step >= 12 and name in ("snare", "ghost", "hat")):
                    continue
                v = VEL.get(ch, 80)
                if variant == "light":
                    v = int(v * 0.75)
                out.append((bar * 4 + steps_to_beat(step, swing), 0.2, note, v))
        if last:  # a 16th-note fill on the last beat (MUSIC_KNOWLEDGE R7)
            toms = [DRUM["tom_hi"], DRUM["tom_hi"], DRUM["tom_mid"], DRUM["tom_lo"]]
            for i in range(4):
                out.append((bar * 4 + 3 + i / 4, 0.2, toms[i] if rng is not None and rng.random() < 0.5 else DRUM["snare"],
                            70 + i * 12))
        if crash_first and bar == b0:
            out.append((bar * 4, 1.0, DRUM["crash"], 100))
    return out


# --------------------------------------------------------------------------------------------------
# The whole song
# --------------------------------------------------------------------------------------------------

def choose_tempo(clip_bpm: float | None, pack: dict) -> tuple[float, float]:
    """Song tempo and the factor applied to melody beats so the melody keeps its real speed."""
    lo, hi = pack["bpm"]
    if not clip_bpm:
        return (lo + hi) / 2, 1.0
    best = None
    for f in (1.0, 2.0, 0.5):
        b = clip_bpm * f
        dist = 0 if lo <= b <= hi else min(abs(b - lo), abs(b - hi))
        if best is None or dist < best[0] - 1e-9:
            best = (dist, f)
    f = best[1]
    return float(min(hi, max(lo, clip_bpm * f))), f


def arrange(*, pack_name: str, seed: int, melody: list[dict] | None, clip_bpm: float | None,
            key: dict | None, beat: list[dict] | None = None, partner_melody: list[dict] | None = None,
            partner_key: dict | None = None, beat_bpm: float | None = None) -> Song:
    pack = PACKS[pack_name]
    rng = np.random.default_rng(seed)
    notes_for_user = []
    tonic = (key or {}).get("tonic", 0)
    mode = (key or {}).get("mode", "major")
    if mode not in theory.MODES:
        mode = "major"
    ext = pack["ext"][rng.integers(len(pack["ext"]))]
    per_bar = pack["harmonic_rhythm"][rng.integers(len(pack["harmonic_rhythm"]))]
    bpm, factor = choose_tempo(clip_bpm or beat_bpm, pack)
    swing = pack["swing"]

    mel = scale_time(prepare_melody(melody or []), factor)
    have_melody = len(mel) >= 4
    LA = section_bars(mel) if have_melody else 8
    if have_melody:
        a_mel = fill_section(mel, LA, tonic, mode)
        a_chords = harmonise(a_mel, LA, pack, tonic, mode, ext, rng, per_bar=per_bar, end="loop")
    else:
        a_chords = progression_from_favourite(pack, tonic, mode, ext, LA, rng)
        a_mel = compose(a_chords, LA, tonic, mode, rng)
        notes_for_user.append("the melody (from the style's rules, over your beat)")

    # B section: a partner clip's melody if there is one (combination), else the developed motif.
    if partner_melody:
        pm = prepare_melody(partner_melody)
        shift = ((tonic - (partner_key or {}).get("tonic", tonic)) + 6) % 12 - 6
        pm = [(s, l, p + shift, v) for s, l, p, v in pm]
        b_mel = fill_section(scale_time(pm, factor), LA, tonic, mode)
        b_source = "your other clip"
    else:
        b_mel = develop(a_mel, LA, tonic, mode, rng)
        b_source = "grown from your melody" if have_melody else "grown from the melody"
        notes_for_user.append(f"a B section {b_source}")
    b_chords = harmonise(b_mel, LA, pack, tonic, mode, ext, rng, per_bar=per_bar, end="loop")
    end_chords = harmonise(a_mel, LA, pack, tonic, mode, ext, rng, per_bar=per_bar, end="tonic")

    # Form: intro 4 | A | A' | B | A'' | ending 2
    intro = 4
    sections = [("Intro", 0, intro), ("A", intro, LA), ("A'", intro + LA, LA), ("B", intro + 2 * LA, LA),
                ("A''", intro + 3 * LA, LA), ("Ending", intro + 4 * LA, 2)]
    chords = []
    for name, start, bars in sections:
        if name == "Intro":
            src = a_chords[-intro * per_bar:] if len(a_chords) >= intro * per_bar else a_chords
            src = [(s - src[0][0], l, c) for s, l, c in src]
        elif name == "B":
            src = b_chords
        elif name == "A''":
            src = end_chords
        elif name == "Ending":
            tonic_chord = next((c for _, _, c in end_chords[::-1] if c.function == "T"), end_chords[-1][2])
            src = [(0, 8, tonic_chord)]
        else:
            src = a_chords
        for s, l, c in src:
            if s < bars * 4:
                chords.append((start * 4 + s, min(l, bars * 4 - s), c))

    roles = pack["roles"]
    # Every part gets its own sound where the style allows (MUSIC_KNOWLEDGE A5: contrast of colour).
    pick, used = {}, set()
    for r in ("lead", "comp", "bass", "pad", "arp", "counter"):
        opts = [o for o in roles[r] if o not in used] or roles[r]
        pick[r] = opts[rng.integers(len(opts))]
        used.add(pick[r])
    # The B section hands the tune to a different instrument for contrast.
    b_opts = [o for o in roles["lead"] if o not in used] or [o for o in roles["lead"] if o != pick["lead"]] \
        or [pick["lead"]]
    b_lead = b_opts[rng.integers(len(b_opts))]

    def place(melody_notes, start_bar):
        return [(s + start_bar * 4, l, p, v) for s, l, p, v in melody_notes]

    lead_notes = place(a_mel, intro) + place(a_mel, intro + LA) + place(a_mel, intro + 3 * LA)
    lead = Track("Lead", "lead", pick["lead"], fit_range(lead_notes, pick["lead"]), mine=have_melody, pan=0.0)
    lead_b = Track("Lead (B)", "lead", b_lead, fit_range(place(b_mel, intro + 2 * LA), b_lead),
                   mine=bool(partner_melody), pan=0.0)
    # Final note of the song: the tonic, held through the ending.
    if lead.notes:
        last = lead.notes[-1][2]
        fin = min((last + k for k in range(-6, 7) if (last + k) % 12 == tonic), key=lambda q: abs(q - last))
        lead.notes.append(((intro + 4 * LA) * 4, 6.0, fin, 84))

    total_bars = intro + 4 * LA + 2
    drum_pattern_opts = pack["drums"]
    user_grid = drum_grid_from_beat(beat) if beat else None
    main_pat = user_grid or drum_pattern_opts[rng.integers(len(drum_pattern_opts))]
    alt_pat = drum_pattern_opts[(drum_pattern_opts.index(main_pat) + 1) % len(drum_pattern_opts)] \
        if main_pat in drum_pattern_opts else drum_pattern_opts[0]
    if user_grid and "hat" not in user_grid:
        main_pat = {**main_pat, "hat": drum_pattern_opts[0].get("hat", "x.x.x.x.x.x.x.x.")}
        notes_for_user.append("hi-hats on top of your beat")
    if not user_grid:
        notes_for_user.append("the drums")
    kit = "kit:" + pack["kit"][rng.integers(len(pack["kit"]))]
    drums = []
    drums += drum_part(main_pat, (0, intro), swing, fill_last=True, crash_first=False, variant="light", rng=rng)
    drums += drum_part(main_pat, (intro, intro + LA), swing, fill_last=True, crash_first=True, rng=rng)
    drums += drum_part(main_pat, (intro + LA, intro + 2 * LA), swing, fill_last=True, crash_first=True, rng=rng)
    drums += drum_part(alt_pat, (intro + 2 * LA, intro + 3 * LA), swing, fill_last=True, crash_first=True,
                       variant="half" if rng.random() < 0.4 else "full", rng=rng)
    drums += drum_part(main_pat, (intro + 3 * LA, intro + 4 * LA), swing, fill_last=False, crash_first=True, rng=rng)
    drums.append(((intro + 4 * LA) * 4, 2.0, DRUM["crash"], 110))
    drums.append(((intro + 4 * LA) * 4, 0.5, DRUM["kick"] if "kick" in main_pat else DRUM["concert_bd"], 110))

    cell = pack["bass"][rng.integers(len(pack["bass"]))]
    bass = bass_part(chords, (intro, intro + 4 * LA), cell, swing, rng)
    bass += [((intro + 4 * LA) * 4, 6.0, 36 + (tonic - 36) % 12 - (12 if 36 + (tonic - 36) % 12 > 43 else 0), 96)]
    rhythm = pack["comp_rhythm"][rng.integers(len(pack["comp_rhythm"]))]
    comp_lo, comp_hi = (52, 77) if INSTRUMENTS[pick["comp"]][4] != "strings" else (48, 76)
    melody_all = lead.notes + lead_b.notes
    comp = comp_part(chords, (0, total_bars - 2), rhythm, swing, comp_lo, comp_hi, pack["rootless"], pack["spread"],
                     melody=melody_all)
    comp += [(s, 7.5, p, 70) for s, _, p, _ in comp_part(chords, (total_bars - 2, total_bars - 1), [(0, 16)], swing,
                                                          comp_lo, comp_hi, pack["rootless"], pack["spread"])]
    pad = pad_part(chords, (0, intro), 55, 79, pack["spread"]) + \
        pad_part(chords, (intro + LA, total_bars), 55, 79, pack["spread"], melody=melody_all)
    a_lo, a_hi = INSTRUMENTS[pick["arp"]][2:4]
    arp_lo = max(60, a_lo) if a_hi - max(60, a_lo) >= 18 else max(a_lo, a_hi - 24)
    arp_hi = min(arp_lo + 24, a_hi)
    arp = arp_part(chords, (intro + LA, intro + 2 * LA), arp_lo, arp_hi, pack.get("fast_arp", False), swing, rng) + \
        arp_part(chords, (intro + 3 * LA, intro + 4 * LA), arp_lo, arp_hi, pack.get("fast_arp", False), swing, rng)
    clo, chi = INSTRUMENTS[pick["counter"]][2:4]
    counter = counter_part(chords, (intro + LA, intro + 2 * LA), max(clo, 55), min(chi, 79)) + \
        counter_part(chords, (intro + 2 * LA, intro + 3 * LA), max(clo, 55), min(chi, 79))

    tracks = [lead, lead_b,
              Track("Chords", "comp", pick["comp"], comp, pan=-0.3),
              Track("Pad", "pad", pick["pad"], pad, pan=0.0),
              Track("Bass", "bass", pick["bass"], fit_range(bass, pick["bass"]), pan=0.0),
              Track("Arpeggio", "arp", pick["arp"], arp, pan=0.35),
              Track("Counter-line", "counter", pick["counter"], counter, pan=-0.35),
              Track("Drums", "drums", kit, drums, mine=bool(user_grid), pan=0.0)]
    if "riff" in roles:
        # The hook: from A' on, so the first A belongs to your melody (docs/ARRANGING.md R1.6).
        r_inst = [o for o in roles["riff"] if o not in used] or roles["riff"]
        r_pick = r_inst[rng.integers(len(r_inst))]
        riff_notes = riff_part(chords, (intro + LA, intro + 2 * LA), r_pick, rng) + \
            riff_part(chords, (intro + 3 * LA, intro + 4 * LA), r_pick, rng)
        riff_notes = [n for n in riff_notes if not any(abs(n[2] - m[2]) == 1 and m[0] <= n[0] < m[0] + m[1]
                                                       for m in lead.notes)]
        tracks.append(Track("Riff", "riff", r_pick, riff_notes, pan=0.25))
    if pack.get("timpani"):
        tim = []
        for name, start, bars in sections[1:]:
            c = next((c for s, l, c in chords if s <= start * 4 < s + l), None)
            if c:
                tim.append((start * 4, 1.5, 38 + (c.root - 38) % 12, 100))
        tracks.append(Track("Timpani", "timpani", "timpani", tim, pan=0.1))
    tracks = [t for t in tracks if t.notes]
    added = [f"{t.name.lower()} ({t.instrument.replace('kit:', '').replace('_', ' ')})" for t in tracks
             if not t.mine and t.role not in ("lead",)]
    notes_for_user = added + [n for n in notes_for_user if n not in ("the drums",)]

    return Song(pack=pack_name, bpm=round(bpm, 1), tonic=tonic, mode=mode, swing=swing, sections=sections,
                chords=chords, tracks=tracks, seed=seed, notes_for_user=notes_for_user,
                sources={"factor": factor, "ext": ext, "per_bar": per_bar, "lead": pick["lead"], "b_lead": b_lead,
                         "user_beat": bool(user_grid), "partner_melody": bool(partner_melody),
                         "have_melody": have_melody})
