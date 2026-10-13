"""Music theory the arranger and the critic share: chords, scales, which melody notes fit which chord,
voicings and voice leading. Rules follow docs/MUSIC_KNOWLEDGE.md §2."""

from __future__ import annotations

from dataclasses import dataclass

NAMES = ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"]

QUALITIES = {
    "maj": [0, 4, 7], "min": [0, 3, 7], "dim": [0, 3, 6], "aug": [0, 4, 8], "sus4": [0, 5, 7], "power": [0, 7],
    "maj7": [0, 4, 7, 11], "min7": [0, 3, 7, 10], "dom7": [0, 4, 7, 10], "min7b5": [0, 3, 6, 10],
    "maj6": [0, 4, 7, 9], "min6": [0, 3, 7, 9], "add9": [0, 4, 7, 14], "min_add9": [0, 3, 7, 14],
    "maj9": [0, 4, 7, 11, 14], "min9": [0, 3, 7, 10, 14], "dom9": [0, 4, 7, 10, 14], "dom7sus4": [0, 5, 7, 10],
    "min11": [0, 3, 7, 10, 14, 17], "dom13": [0, 4, 7, 10, 14, 21], "dom7s9": [0, 4, 7, 10, 15],
}
SUFFIX = {"maj": "", "min": "m", "dim": "dim", "aug": "+", "sus4": "sus4", "power": "5", "maj7": "maj7",
          "min7": "m7", "dom7": "7", "min7b5": "m7b5", "maj6": "6", "min6": "m6", "add9": "add9",
          "min_add9": "m(add9)", "maj9": "maj9", "min9": "m9", "dom9": "9", "dom7sus4": "7sus4", "min11": "m11",
          "dom13": "13", "dom7s9": "7#9"}

# Non-chord tones a style may treat as colour ("tensions"), by chord family, in semitones above the root.
TENSIONS = {
    "major": {2, 9, 6},  # 9, 13, #11
    "minor": {2, 5, 9},  # 9, 11, 13 (dorian)
    "dominant": {2, 9, 1, 3, 6},  # 9, 13, b9, #9, #11
    "diminished": {2, 5},
    "sus": {2, 9, 4},
}
# Notes that sound wrong held over the chord ("avoid notes", MUSIC_KNOWLEDGE H1).
AVOID = {
    "major": {5, 1},  # natural 11, b9
    "minor": {1, 8},  # b9, b13 (except in aeolian colour, still harsh held)
    "dominant": {5},  # natural 11 over a 3rd
    "diminished": set(),
    "sus": {4 - 1},  # the minor 3rd against a sus4
}

MODES = {
    "major": [0, 2, 4, 5, 7, 9, 11], "minor": [0, 2, 3, 5, 7, 8, 10],
    "dorian": [0, 2, 3, 5, 7, 9, 10], "mixolydian": [0, 2, 4, 5, 7, 9, 10],
}


def family(quality: str) -> str:
    if quality.startswith("dom"):
        return "sus" if "sus" in quality else "dominant"
    if quality in ("dim", "min7b5"):
        return "diminished"
    if quality.startswith("min"):
        return "minor"
    if quality in ("sus4", "power"):
        return "sus"
    return "major"


@dataclass(frozen=True)
class Chord:
    root: int  # pitch class 0-11
    quality: str
    degree: str  # roman numeral label, e.g. "IVmaj7"
    function: str  # T (tonic), PD (pre-dominant), D (dominant), C (colour)

    @property
    def name(self) -> str:
        return NAMES[self.root] + SUFFIX[self.quality]

    def tones(self) -> list[int]:
        return [(self.root + i) % 12 for i in QUALITIES[self.quality]]

    def core(self) -> list[int]:
        """Root, 3rd (or 4th), 5th and 7th: the notes that define the chord."""
        return [(self.root + i) % 12 for i in QUALITIES[self.quality] if i < 12]

    def fit(self, pc: int, tension_ok: float) -> float:
        """How well a melody pitch class sits on this chord: 1 chord tone, `tension_ok` colour, -1 avoid."""
        rel = (pc - self.root) % 12
        if rel in {i % 12 for i in QUALITIES[self.quality]}:
            return 1.0
        fam = family(self.quality)
        if rel in AVOID.get(fam, set()):
            return -1.0
        if rel in TENSIONS.get(fam, set()):
            return tension_ok
        return -0.35


ROMAN = ["I", "II", "III", "IV", "V", "VI", "VII"]
FUNCTION_BY_DEGREE = {0: "T", 1: "PD", 2: "T", 3: "PD", 4: "D", 5: "T", 6: "D"}


def diatonic(tonic: int, mode: str, ext: str) -> list[Chord]:
    """The seven chords of a key. ext: 'triad', 'seventh' or 'ninth'."""
    scale = MODES.get(mode, MODES["major"])
    out = []
    for d in range(7):
        r = scale[d]
        third = (scale[(d + 2) % 7] - r) % 12
        fifth = (scale[(d + 4) % 7] - r) % 12
        seventh = (scale[(d + 6) % 7] - r) % 12
        if third == 4 and fifth == 7:
            q = {"triad": "maj", "seventh": "maj7" if seventh == 11 else "dom7",
                 "ninth": "maj9" if seventh == 11 else "dom9"}[ext]
        elif third == 3 and fifth == 7:
            q = {"triad": "min", "seventh": "min7", "ninth": "min9"}[ext]
        elif third == 3 and fifth == 6:
            q = "dim" if ext == "triad" else "min7b5"
        else:
            q = "aug"
        label = ROMAN[d] if third == 4 else ROMAN[d].lower()
        out.append(Chord((tonic + r) % 12, q, label + SUFFIX[q], FUNCTION_BY_DEGREE[d]))
    return out


def borrowed(tonic: int, mode: str, names: list[str], ext: str) -> list[Chord]:
    """Colour chords a style allows, by name: secondary dominants, borrowed chords, tritone subs."""
    seventh = ext != "triad"
    table = {
        "V/V": (2, "dom7" if seventh else "maj", "II7", "D"),
        "V/vi": (4, "dom7" if seventh else "maj", "III7", "D"),
        "V/ii": (9, "dom7" if seventh else "maj", "VI7", "D"),
        "V/IV": (0, "dom7", "I7", "D"),
        "iv": (5, "min7" if seventh else "min", "iv", "PD"),
        "bVII": (10, "dom7" if seventh else "maj", "bVII", "PD"),
        "bVI": (8, "maj7" if seventh else "maj", "bVI", "PD"),
        "bIII": (3, "maj7" if seventh else "maj", "bIII", "T"),
        "subV": (1, "dom7", "bII7", "D"),
        "V7": (7, "dom7", "V7", "D"),  # the major V in minor keys (harmonic minor)
        "IV7": (5, "dom7", "IV7", "PD"),  # dorian's major IV
        "Vsus": (7, "dom7sus4", "V7sus4", "D"),
        "ii7b5": (2, "min7b5", "iim7b5", "PD"),
        "bII": (1, "maj7" if seventh else "maj", "bII", "PD"),  # Neapolitan / Phrygian colour (tense, dark)
    }
    out = []
    for n in names:
        if n in table:
            off, q, label, fn = table[n]
            out.append(Chord((tonic + off) % 12, q, label, fn))
    return out


def transition(a: Chord | None, b: Chord) -> float:
    """How natural it is to go from chord a to chord b (MUSIC_KNOWLEDGE H2): functional flow, strong root
    motion, and a small cost for sitting on one chord."""
    if a is None:
        return 0.6 if b.function == "T" else 0.2
    if a == b:
        return -0.15
    s = 0.0
    down5 = (a.root - b.root) % 12 == 7
    if down5:
        s += 0.7  # root falls a fifth: the strongest progression
    if a.function == "D":
        s += 0.6 if (b.function == "T" or down5) else -0.3
    elif a.function == "PD":
        s += 0.5 if b.function == "D" else 0.1
    elif a.function == "T":
        s += 0.3 if b.function in ("PD", "T") else 0.15
    if (b.root - a.root) % 12 in (1, 2, 10, 11):
        s += 0.15  # stepwise root motion, common in pop
    # Secondary dominants and tritone subs should resolve down a fifth (or a half step for subV).
    if a.quality.startswith("dom") and a.function == "D" and not down5 and (a.root - b.root) % 12 != 1:
        s -= 0.4
    return s


def voice(chord: Chord, prev: list[int] | None, lo: int, hi: int, n: int = 4, rootless: bool = False,
          spread: bool = False) -> list[int]:
    """Pick concrete notes for a chord inside [lo, hi], moving as little as possible from `prev`
    (MUSIC_KNOWLEDGE H6), and keeping low intervals wide (H8)."""
    intervals = QUALITIES[chord.quality]
    pcs = [(chord.root + i) % 12 for i in intervals]
    if rootless and len(pcs) >= 4:
        pcs = pcs[1:]
    # Prefer the colour tones; drop the 5th first when there are too many notes.
    if len(pcs) > n:
        five = (chord.root + 7) % 12
        pcs = [p for p in pcs if p != five][:n] if five in pcs else pcs[:n]
    best, best_cost = None, 1e9
    for base in range(lo, hi - 6):
        notes = []
        cur = base
        for p in sorted(pcs, key=lambda p: (p - base) % 12):
            m = cur + (p - cur) % 12
            notes.append(m)
            cur = m + (7 if spread and len(notes) == 1 else 1)
        notes.sort()
        if notes[-1] > hi or notes[0] < lo:
            continue
        # Low interval limit: nothing closer than a 5th below C3, no 2nds below C4.
        bad = any(b - a < 7 and a < 48 for a, b in zip(notes, notes[1:])) or \
            any(b - a <= 2 and a < 60 for a, b in zip(notes, notes[1:]))
        cost = 30 if bad else 0
        if prev:
            cost += sum(min(abs(x - y) for y in prev) for x in notes) + abs(sum(notes) / len(notes) - sum(prev) / len(prev))
        else:
            cost += abs(sum(notes) / len(notes) - (lo + hi) / 2)
        if cost < best_cost:
            best, best_cost = notes, cost
    return best or [lo + (p - lo) % 12 for p in pcs]
