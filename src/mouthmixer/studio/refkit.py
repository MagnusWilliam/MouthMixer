"""A toolkit for songs modelled on reference tracks (docs/PERSONA_PRODUCTION.md section 10).

The engine's feel templates made every song the same thin band. Here each song is written part by part, as
`last_train.py` was, from patterns: a plan (form, chords, swing) and pattern strings per section energy for
the drums, bass, keys, guitars, horns and strings, a lead melody written in scale degrees and fitted to the
chords, and a level balance taken from the reference's stems (`reference/profile.py`): every group of parts
(drums, bass, guitar, keys, lead, other) sits against the others as the reference's stems do.

Pattern strings: one character per 16th (16 per bar) unless noted; '.' rest, '-' hold the previous note.
A list of patterns plays one per bar in turn (bar-to-bar variation).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

import numpy as np

from ..arrange.arranger import Track
from .production import chord, tones, upper

SCALES = {"major": [0, 2, 4, 5, 7, 9, 11], "minor": [0, 2, 3, 5, 7, 8, 10], "dorian": [0, 2, 3, 5, 7, 9, 10]}
DRUM = {"kick": 36, "snare": 38, "side": 37, "rim": 40, "hat": 42, "pedal": 44, "open": 46, "ride": 51, "bell": 53,
        "crash": 49, "crash2": 57, "t1": 50, "t2": 48, "t3": 45, "t4": 41}
PERC = {"conga_hi": 62, "conga_open": 63, "conga_low": 64, "bongo_hi": 60, "bongo_lo": 61, "tamb": 54, "shaker": 82,
        "tri": 81}


# --------------------------------------------------------------------------------------------------
# The plan: form and chords
# --------------------------------------------------------------------------------------------------

@dataclass
class Sec:
    name: str
    kind: str  # intro, verse, pre, chorus, bridge, break, solo, outro
    bars: int
    energy: int  # 0 sparse .. 3 everything
    start: int = 0


class Plan:
    """Form, chords per bar (one name, or 'A|B' for two per bar), key, tempo and swing.
    `swing8`: where off-beat 8ths land (0.5 straight, 0.62 jazz, 0.67 triplet); `swing16`: the same for 16ths
    within each 8th (hip-hop swing)."""

    def __init__(self, bpm: float, tonic: int, mode: str, form: list[tuple], progs: dict, swing8: float = 0.5,
                 swing16: float = 0.5):
        self.bpm, self.tonic, self.mode, self.swing8, self.swing16 = bpm, tonic, mode, swing8, swing16
        self.secs: list[Sec] = []
        self.bars: list[str] = []
        at = 0
        for name, kind, bars, energy in form:
            s = Sec(name, kind, bars, energy, at)
            prog = progs.get(name) or progs[kind]
            self.bars += [prog[i % len(prog)] for i in range(bars)]
            self.secs.append(s)
            at += bars
        self.total = at

    def chord_at(self, beat: float) -> str:
        b = min(int(beat // 4), self.total - 1)
        parts = self.bars[b].split("|")
        return parts[min(len(parts) - 1, int((beat % 4) / (4 / len(parts))))]

    def sec_at(self, bar: int) -> Sec:
        return next(s for s in self.secs if s.start <= bar < s.start + s.bars)

    def next_sec(self, s: Sec) -> Sec | None:
        i = self.secs.index(s)
        return self.secs[i + 1] if i + 1 < len(self.secs) else None

    def scale_pc(self) -> list[int]:
        return [(self.tonic + d) % 12 for d in SCALES[self.mode]]


def _pick(p, energy: int, kind: str = ""):
    """A pattern for a section: dict keyed by kind or energy (a kind wins), or one pattern for all."""
    if isinstance(p, dict):
        if kind in p:
            return p[kind]
        e = energy
        while e >= 0 and e not in p:
            e -= 1
        return p.get(e)
    return p


def _bar_pattern(p, i: int) -> str | None:
    if p is None:
        return None
    return p[i % len(p)] if isinstance(p, list) else p


def events(pattern: str, bar_start: float, steps: int | None = None):
    """(beat, length in beats, char) for each hit in a one-bar pattern; holds ('-') lengthen the hit before."""
    steps = steps or len(pattern)
    step = 4.0 / steps
    out = []
    for i, c in enumerate(pattern):
        if c == "-" and out:
            b, l_, ch = out[-1]
            out[-1] = (b, l_ + step, ch)
        elif c not in ".- ":
            out.append((bar_start + i * step, step, c))
    return out


def swing(notes: list, plan: Plan) -> list:
    """Swing 8ths and/or 16ths: an off-beat 8th moves to `swing8` of the beat; an off-beat 16th to `swing16` of
    its 8th."""
    out = []
    for s, l_, p, v in notes:
        frac = s % 1
        if plan.swing8 != 0.5 and abs(frac - 0.5) < 1e-3:
            s += plan.swing8 - 0.5
        elif plan.swing16 != 0.5 and abs(frac % 0.5 - 0.25) < 1e-3:
            s += (plan.swing16 - 0.5) * 0.5
        out.append((s, l_, p, v))
    return out


def shuffle(notes: list, amount: float = 0.66) -> list:
    """8th-note lines over a triplet groove: off-beat 8ths move to `amount` of the beat (and shorten to fit)."""
    out = []
    for s, l_, p, v in notes:
        if abs(s % 1 - 0.5) < 1e-3:
            d = amount - 0.5
            s, l_ = s + d, max(0.06, l_ - d)
        out.append((s, l_, p, v))
    return out


def humanise(notes: list, rng, vel_sd: float = 5.0) -> list:
    return [(s, l_, p, int(np.clip(v + rng.normal(0, vel_sd), 1, 127))) for s, l_, p, v in notes]


# --------------------------------------------------------------------------------------------------
# Drums
# --------------------------------------------------------------------------------------------------

KICK_V = {"x": 106, "X": 120, "h": 82}
SNARE_V = {"x": 104, "X": 118, "g": 40, "h": 72, "r": 96}  # r = rim shot (40)
HAT_V = {"x": 76, "X": 92, "h": 58, "o": 84, "p": 58}  # o = open hat, p = pedal hat
RIDE_V = {"x": 80, "X": 94, "b": 88}  # b = bell


def drums(plan: Plan, styles: dict, rng, fills: str = "snare", crash_from: int = 2) -> list:
    """styles: {energy or kind: {"kick", "snare", "hat", "ride"?, "perc"?: pattern or [patterns]}}; energy 0 or a
    missing style = no kit. Fills into a bigger next section, a crash on big section starts."""
    notes = []
    for s in plan.secs:
        st = _pick(styles, s.energy, s.kind)
        nxt = plan.next_sec(s)
        for i in range(s.bars):
            bar = s.start + i
            b0 = bar * 4.0
            if not st:
                continue
            last = i == s.bars - 1
            fill = last and fills and nxt is not None and (nxt.energy > s.energy or nxt.kind in ("chorus", "solo"))
            for part, vel, key in (("kick", KICK_V, DRUM["kick"]), ("snare", SNARE_V, None), ("hat", HAT_V, None),
                                   ("ride", RIDE_V, None)):
                p = _bar_pattern(st.get(part), i)
                if not p:
                    continue
                for beat, _, c in events(p, b0):
                    if fill and beat >= b0 + 2 and part in ("snare", "hat", "ride"):
                        continue
                    if part == "snare":
                        k = DRUM["rim"] if c == "r" else DRUM["snare"]
                    elif part == "hat":
                        k = DRUM["open"] if c == "o" else DRUM["pedal"] if c == "p" else DRUM["hat"]
                    elif part == "ride":
                        k = DRUM["bell"] if c == "b" else DRUM["ride"]
                    else:
                        k = key
                    v = vel.get(c, 90)
                    if part == "hat" and abs(beat % 1) < 1e-3:
                        v += 6
                    notes.append((beat, 0.2, k, v))
            if fill:
                if fills == "toms" and s.energy >= 2:
                    for j, t in enumerate(["t1", "t1", "t2", "t2", "t3", "t3", "t4", "t4"]):
                        notes.append((b0 + 2 + j * 0.25, 0.2, DRUM[t], 92 + j * 3))
                else:
                    for j in range(8):
                        notes.append((b0 + 2 + j * 0.25, 0.2, DRUM["snare"], 54 + j * 9))
            if i == 0 and s.energy >= crash_from and st:
                notes.append((b0, 2.0, DRUM["crash"], 112))
        # the last bar of the song: one hit and a crash
    end = plan.total * 4.0
    if _pick(styles, plan.secs[-1].energy, plan.secs[-1].kind):
        notes.append((end, 2.0, DRUM["crash"], 110))
        notes.append((end, 0.3, DRUM["kick"], 112))
    return humanise(swing(notes, plan), rng, 4)


def percussion(plan: Plan, styles: dict, rng) -> list:
    """Hand percussion: styles {energy: {perc name: pattern}}."""
    notes = []
    for s in plan.secs:
        st = _pick(styles, s.energy, s.kind)
        if not st:
            continue
        for i in range(s.bars):
            b0 = (s.start + i) * 4.0
            for name, p in st.items():
                for beat, _, c in events(_bar_pattern(p, i), b0):
                    notes.append((beat, 0.2, PERC[name], 96 if c == "X" else 78 if c == "x" else 56))
    return humanise(swing(notes, plan), rng, 6)


# --------------------------------------------------------------------------------------------------
# Bass
# --------------------------------------------------------------------------------------------------

def _place(pc: int, lo: int) -> int:
    return lo + (pc - lo) % 12


def _next_chord(plan: Plan, beat: float) -> str:
    """The next different chord after `beat` (within a bar and a half), or the next bar's chord."""
    now = plan.chord_at(beat + 0.01)
    t = (int(beat * 2) + 1) / 2
    while t < min(beat + 6, plan.total * 4):
        if plan.chord_at(t + 0.01) != now:
            return plan.chord_at(t + 0.01)
        t += 0.5
    return plan.chord_at(min((beat // 4 + 1) * 4, plan.total * 4 - 1) + 0.01)


def bass(plan: Plan, styles: dict, lo: int = 28, legato: float = 0.85, rng=None) -> tuple[list, list]:
    """styles {energy or kind: pattern(s)}; tokens R root, r soft root, O octave, 5 fifth, 3 third, 7 seventh,
    A a half step under the next chord's root (an approach), D a dead note (to the ghost track).
    Returns (notes, ghost notes)."""
    rng = rng or np.random.default_rng(0)
    main, ghosts = [], []
    for s in plan.secs:
        st = _pick(styles, s.energy, s.kind)
        if not st:
            continue
        for i in range(s.bars):
            b0 = (s.start + i) * 4.0
            p = _bar_pattern(st, i)
            evs = events(p, b0)
            for j, (beat, length, c) in enumerate(evs):
                name = plan.chord_at(beat + 0.01)
                root, ints, _, slash = chord(name)
                r = _place(slash if slash is not None else root, lo)
                if c in "Rr":
                    pitch = r
                elif c == "O":
                    pitch = r + 12
                elif c == "5":  # the chord's own fifth (a #5 chord's raised one)
                    f5 = ints[2] if len(ints) > 2 and ints[2] in (6, 7, 8) else 7
                    pitch = r + f5 if r + f5 <= lo + 19 else r + f5 - 12
                elif c == "3":
                    pitch = r + ints[1]
                elif c == "7":
                    pitch = r + (ints[3] if len(ints) > 3 else 10)
                elif c == "A":
                    nxt_root = chord(_next_chord(plan, beat))[0]
                    pitch = _place(nxt_root, lo) - 1
                elif c == "D":
                    ghosts.append((beat, 0.1, r, 70))
                    continue
                else:
                    continue
                vel = 70 if c == "r" else 108 if abs(beat % 1) < 1e-3 else 94
                main.append((beat, max(0.08, length * legato), pitch, vel))
    return humanise(swing(main, plan), rng, 4), humanise(swing(ghosts, plan), rng, 4)


# --------------------------------------------------------------------------------------------------
# Harmony parts
# --------------------------------------------------------------------------------------------------

def comp(plan: Plan, styles: dict, lo: int = 55, hi: int = 76, size: int = 4, vel: int = 80, left_hand: bool = False,
         short: float = 0.22, rng=None) -> list:
    """Chords on a rhythm: 'x' a hit held to the next one (or its holds), 'X' accented, 's' a short stab, 'm' a
    muted chop (guitar), '.' rest. `left_hand`: a piano's root and fifth low on each bar's first hit."""
    rng = rng or np.random.default_rng(0)
    notes, prev = [], None
    for s in plan.secs:
        st = _pick(styles, s.energy, s.kind)
        if not st:
            continue
        for i in range(s.bars):
            b0 = (s.start + i) * 4.0
            for j, (beat, length, c) in enumerate(events(_bar_pattern(st, i), b0)):
                name = plan.chord_at(beat + 0.01)
                v = upper(name, prev, lo, hi, size)
                prev = v
                if c == "m":
                    notes += [(beat, 0.07, p, 34) for p in v[-3:]]
                    continue
                ln = short if c == "s" else length * 0.92
                vv = vel + (14 if c == "X" else 0) + (4 if abs(beat % 1) < 1e-3 else 0)
                for k, p in enumerate(v):
                    notes.append((beat + k * 0.012 * (1 if c != "s" else 0.3), ln, p, vv - 2 * k))
                if left_hand and j == 0:
                    root = chord(name)[0]
                    lr = _place(root, 36)
                    notes += [(beat, max(length, 1.5), lr, vv - 6), (beat, max(length, 1.5), lr + 7, vv - 12)]
    return humanise(swing(notes, plan), rng, 5)


def power(plan: Plan, styles: dict, lo: int = 40, rng=None) -> list:
    """Power chords (root, fifth, octave) for an overdriven guitar: 'x' held, 'm' palm-muted 8th, 'X' accent."""
    rng = rng or np.random.default_rng(0)
    notes = []
    for s in plan.secs:
        st = _pick(styles, s.energy, s.kind)
        if not st:
            continue
        for i in range(s.bars):
            b0 = (s.start + i) * 4.0
            for beat, length, c in events(_bar_pattern(st, i), b0):
                root, ints, _, slash = chord(plan.chord_at(beat + 0.01))
                r = _place(slash if slash is not None else root, lo)
                fifth = ints[2] if slash is None and len(ints) > 2 and ints[2] in (6, 7, 8) else 7  # #5 and b5 chords
                ln, v = (0.18, 78) if c == "m" else (length * 0.95, 112 if c == "X" else 100)
                notes += [(beat, ln, r, v), (beat + 0.008, ln, r + fifth, v - 4), (beat + 0.016, ln, r + 12, v - 8)]
    return humanise(swing(notes, plan), rng, 4)


def arp(plan: Plan, styles: dict, lo: int = 60, hi: int = 84, vel: int = 76, rng=None) -> list:
    """Broken chords: digits pick the chord's tones from the bottom of the voicing (1 lowest), '-' holds."""
    rng = rng or np.random.default_rng(0)
    notes, prev = [], None
    for s in plan.secs:
        st = _pick(styles, s.energy, s.kind)
        if not st:
            continue
        for i in range(s.bars):
            b0 = (s.start + i) * 4.0
            for beat, length, c in events(_bar_pattern(st, i), b0):
                if not c.isdigit():
                    continue
                v = sorted(upper(plan.chord_at(beat + 0.01), prev, lo, hi, 4))
                prev = v
                k = int(c) - 1
                p = v[k % len(v)] + 12 * (k // len(v))
                notes.append((beat, length * 0.95, p, vel + (6 if abs(beat % 1) < 1e-3 else 0)))
    return humanise(swing(notes, plan), rng, 5)


def pad(plan: Plan, energies, lo: int = 55, hi: int = 79, size: int = 4, vel: int = 70, low: bool = False) -> list:
    """Sustained chords, one voicing per chord change, in sections whose energy is in `energies` (or whose kind
    is). `low`: cellos/basses instead: root and fifth, 36-55."""
    notes, prev = [], None
    for s in plan.secs:
        if s.energy not in energies and s.kind not in energies:
            continue
        for i in range(s.bars):
            bar = s.start + i
            parts = plan.bars[bar].split("|")
            for j, name in enumerate(parts):
                b, ln = bar * 4.0 + j * 4 / len(parts), 4 / len(parts)
                if low:
                    root, _, _, slash = chord(name)
                    r = _place(slash if slash is not None else root, 36)
                    notes += [(b, ln * 0.98, r, vel), (b, ln * 0.98, r + 7, vel - 8)]
                    continue
                v = upper(name, prev, lo, hi, size)
                prev = v
                notes += [(b, ln * 0.98, p, vel + (6 if s.energy >= 3 else 0)) for p in v]
    return notes


def horns(plan: Plan, styles: dict, rng=None) -> tuple[list, list, list]:
    """A three-horn section on stabs and pads (comp tokens): trumpet on top, sax in the middle, trombone under,
    in close position (Session Horns / Kick-Ass Brass in the sound sheet)."""
    rng = rng or np.random.default_rng(0)
    trp, sax, tbn = [], [], []
    prev = None
    for s in plan.secs:
        st = _pick(styles, s.energy, s.kind)
        if not st:
            continue
        for i in range(s.bars):
            b0 = (s.start + i) * 4.0
            for beat, length, c in events(_bar_pattern(st, i), b0):
                v = sorted(upper(plan.chord_at(beat + 0.01), prev, 62, 81, 3))
                prev = v
                ln = 0.22 if c == "s" else length * 0.9
                vv = 104 + (12 if c == "X" else 0)
                top = v[-1] if v[-1] >= 68 else v[-1] + 12
                trp.append((beat, ln, top, vv))
                sax.append((beat, ln, v[-2] if v[-2] < top else v[-2] - 12, vv - 6))
                tb = v[0] - 12 if v[0] > 60 else v[0]
                tbn.append((beat, ln, tb, vv - 4))
    sw = lambda x: humanise(swing(x, plan), rng, 4)  # noqa: E731
    return sw(trp), sw(sax), sw(tbn)


# --------------------------------------------------------------------------------------------------
# Melody: written in scale degrees, fitted to the chords
# --------------------------------------------------------------------------------------------------

_DEG = re.compile(r"^([#b]?)([1-7])([',]*)$")


def melody(plan: Plan, bar: int, text: str, base: int = 60, grid: float = 0.5, vel: int = 96) -> list:
    """Notes from scale degrees in the plan's key: one token per `grid` beats ('1'..'7', with # or b and ' up or
    , down an octave; '-' holds; '.' rests; '|' is just a bar line). `base`: the tonic's octave (60 = middle C's)."""
    sc = SCALES[plan.mode]
    tonic = base + (plan.tonic - base) % 12
    if tonic - base > 6:
        tonic -= 12
    notes = []
    t = bar * 4.0
    for tok in text.split():
        if tok == "|":
            continue
        if tok == "-":
            if notes:
                s, l_, p, v = notes[-1]
                notes[-1] = (s, l_ + grid, p, v)
        elif tok != ".":
            m = _DEG.match(tok)
            if not m:
                raise ValueError(f"bad melody token {tok!r}")
            acc, d, octs = m.groups()
            p = tonic + sc[int(d) - 1] + (1 if acc == "#" else -1 if acc == "b" else 0) + 12 * (octs.count("'") - octs.count(","))
            notes.append((t, grid, p, vel + (6 if abs(t % 2) < 1e-3 else 0)))
        t += grid
    return notes


def fit(notes: list, plan: Plan) -> list:
    """Melody against the chords: a note on a beat (or held a beat or more) a half step from a chord tone, and
    not a 9th, 11th or 13th the chord can carry, moves to the nearest chord tone."""
    out = []
    for s, l_, p, v in notes:
        name = plan.chord_at(s + 0.01)
        root, ints, _, _ = chord(name)
        ct = tones(name)
        pc = p % 12
        strong = abs(s % 1) < 1e-3 or l_ >= 1.0
        ok_tension = (pc - root) % 12 in ((2, 9) if 4 in ints else (2, 5, 9) if 3 in ints else (2,))
        if strong and pc not in ct and not ok_tension and any((pc - t) % 12 in (1, 11) for t in ct):
            cands = [p + d for d in range(-2, 3) if (p + d) % 12 in ct]
            p = min(cands, key=lambda q: (abs(q - p), q)) if cands else p
        out.append((s, l_, p, v))
    return out


def lengthen(notes: list, max_gap: float = 0.5) -> list:
    """Legato for a held lead: each note runs into the next unless there is a rest longer than `max_gap`."""
    notes = sorted(notes)
    out = []
    for i, (s, l_, p, v) in enumerate(notes):
        if i + 1 < len(notes) and notes[i + 1][0] - (s + l_) <= max_gap:
            l_ = max(l_, notes[i + 1][0] - s - 0.03)
        out.append((s, l_, p, v))
    return out


# --------------------------------------------------------------------------------------------------
# Effects lane
# --------------------------------------------------------------------------------------------------

def risers(plan: Plan) -> tuple[list, list]:
    """A reverse cymbal into every section start that is bigger than the one before, and a low boom on it."""
    rev, boom = [], []
    for a, b in zip(plan.secs, plan.secs[1:]):
        if b.energy > a.energy or b.kind == "chorus":
            rev.append((b.start * 4.0 - 3.5, 3.5, 49, 100))
            boom.append((b.start * 4.0, 2.0, 36, 110))
    return rev, boom


# --------------------------------------------------------------------------------------------------
# Level balance against the reference's stems
# --------------------------------------------------------------------------------------------------

CATS = ("drums", "bass", "guitar", "piano", "lead", "other")
DEFAULT_TARGET = {"drums": -7.0, "bass": -6.5, "guitar": -12.0, "piano": -14.0, "lead": -5.5, "other": -11.5}


def target_levels(slugs: list[str]) -> dict:
    """Each group's level against the full mix (LU), averaged over the references' stem profiles (vocals = the
    lead); the defaults where a profile is missing."""
    from .. import config

    got: dict[str, list[float]] = {}
    for sl in slugs:
        p = config.home() / "analysis" / sl / "profile.json"
        if not p.exists():
            continue
        st = json.loads(p.read_text())["stems"]
        for name, prof in st.items():
            if prof.get("lu_vs_mix") is None:
                continue
            got.setdefault("lead" if name == "vocals" else name, []).append(prof["lu_vs_mix"])
    return {c: (float(np.mean(got[c])) if c in got else DEFAULT_TARGET[c]) for c in CATS}


def balance(song, gains: dict, cats: dict, target: dict, rounds: int = 3) -> tuple[dict, dict]:
    """Gains (dB per part) that put each group of parts at the target level against the others (drums as the
    anchor). Renders every part once; level changes are linear after that. Returns (gains, report)."""
    from ..arrange import render
    from ..reference.analyse import lufs

    rng = np.random.default_rng(song.seed)
    _, n_ = render.song_length(song)
    duck = render._sidechain(n_, render.kick_times(song))
    stems = {t.name: render.render_stem(t, song, rng, duck, gain_db=0.0) for t in song.tracks}
    g = {t.name: float(gains.get(t.name, 0.0)) for t in song.tracks}
    present = sorted({cats.get(t.name, "other") for t in song.tracks} & set(target))
    anchor = "drums" if "drums" in present else present[0]
    report = {}
    for _ in range(rounds):
        groups = {c: sum(stems[t] * 10 ** (g[t] / 20) for t in stems if cats.get(t, "other") == c) for c in present}
        total = sum(groups.values())
        whole = lufs(total)
        cur = {c: (lufs(groups[c]) or -70) - (whole or 0) for c in present}
        report = {c: round(cur[c], 1) for c in present}
        for c in present:
            if c == anchor:
                continue
            d = (target[c] - target[anchor]) - (cur[c] - cur[anchor])
            d = float(np.clip(d, -9, 9))
            for t in g:
                if cats.get(t, "other") == c:
                    g[t] += d
    report["target"] = {c: round(target[c], 1) for c in present}
    return {k: round(v, 2) for k, v in g.items()}, report
