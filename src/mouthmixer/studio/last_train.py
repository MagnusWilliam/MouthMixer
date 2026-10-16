"""'Last Train, First Light': the hand-produced base (docs/PERSONA_PRODUCTION.md §3).

Persona 5 acid-jazz/funk band with a Persona 3 Reload rap pocket: finger bass that never stops moving, Rhodes
at the centre (doubling the bass in the intro), a roomy live kit with congas and a constant triangle, B3
organ, strings and brass saved for the choruses, clean guitars left and right, a sax in the instrumental.
126 BPM, D minor, the 92-bar layout of the lyric sheet. The station chime (A-F-D, LINE ZERO's motif) is the
hook the brass answers with and the finale restates. A guide melody for the singer is written to the words.
"""

from __future__ import annotations

import numpy as np

from ..arrange.arranger import Track
from .production import bass_line, build_song, chord, clear_of, grid, humanise, n, tones, upper

BPM = 126.0
SECTIONS = [("Intro", 0, 8), ("Verse 1", 8, 8), ("Pre-Chorus", 16, 8), ("Chorus", 24, 16),
            ("Chorus instrumental", 40, 8), ("Rap Verse", 48, 8), ("Chorus 2", 56, 8), ("Bridge", 64, 4),
            ("Bridge build", 68, 4), ("Final Chorus", 72, 16), ("Outro", 88, 4)]
INTRO = ["Dm9", "Bbmaj7", "Gm9", "A7#5#9"] * 2
VERSE = ["Dm9", "Dm9", "Bbmaj7", "A7sus4|A7", "Dm9", "Dm9", "Gm9", "C9"]
PRE = ["Bbmaj7", "C6/9", "Am7", "Dm9", "Bbmaj7", "C", "Ebmaj7", "A7#5#9"]
CHORUS = ["Bbmaj7", "C7", "Am7", "Dm9", "Bbmaj7", "C7", "Fmaj7|Am7/E", "Dm9",
          "Gm9", "C7", "Fmaj7", "Bbmaj7", "Gm9", "Ebmaj7", "Asus4", "A7#5#9"]
CHORUS8 = CHORUS[:8]
RAP = ["Dm9", "Bbmaj7", "Gm9", "A7"] * 2
BRIDGE = ["Bbmaj7", "Am7", "Gm9", "Asus4"]
BUILD = ["Bbmaj7", "C", "Ebmaj7", "A7#5#9"]
OUTRO = ["Dm9", "Dm9", "Dm9", "Dm9"]
BARS = INTRO + VERSE + PRE + CHORUS + CHORUS8 + RAP + CHORUS8 + BRIDGE + BUILD + CHORUS + OUTRO
assert len(BARS) == 92
SEC = {name: start for name, start, _ in SECTIONS}
CHORUS_SECTIONS = [("Chorus", 16), ("Chorus instrumental", 8), ("Chorus 2", 8), ("Final Chorus", 16)]
DRUM = {"kick": 36, "snare": 38, "side": 37, "hat": 42, "pedal": 44, "open": 46, "ride": 51, "bell": 53,
        "crash": 49, "crash2": 57, "china": 52, "t1": 50, "t2": 48, "t3": 45, "t4": 41}
PERC = {"bongo_hi": 60, "bongo_lo": 61, "conga_mute": 62, "conga_open": 63, "conga_low": 64, "tamb": 54,
        "tri_mute": 80, "tri_open": 81, "shaker": 82}


def bars(name: str) -> list[str]:
    s = SEC[name]
    length = next(b for nm, st, b in SECTIONS if nm == name)
    return BARS[s:s + length]


def chord_at(beat: float) -> str:
    parts = BARS[int(beat // 4)].split("|")
    return parts[min(len(parts) - 1, int((beat % 4) / (4 / len(parts))))]


# --------------------------------------------------------------------------------------------------
# The guide melody (the singer's line; range A3-G4, the chorus peaking on G4)
# --------------------------------------------------------------------------------------------------
# (beat within the section, length in beats, note) per sung syllable; rap sections have no guide.

def _line(start: float, notes: list[tuple[float, float, str]]) -> list:
    return [(start + b, l, n(p), 96) for b, l, p in notes]


def guide_melody() -> list:
    v, p, c = SEC["Verse 1"] * 4, SEC["Pre-Chorus"] * 4, SEC["Chorus"] * 4
    out = []
    # Verse: low and steady, two bars a line
    out += _line(v + 0, [(0.5, .5, "A3"), (1, .5, "C4"), (1.5, 1, "D4"), (3, .5, "C4"), (3.5, .5, "D4"), (4, .75, "F4"),
                         (4.75, .25, "E4"), (5, .5, "D4"), (5.5, 1.5, "D4")])                         # Midnight hum on an empty platform
    out += _line(v + 8, [(0.5, .5, "A3"), (1, .5, "C4"), (1.5, .5, "D4"), (2, 1, "F4"), (3.5, .5, "E4"), (4, .5, "D4"),
                         (4.5, 1, "E4"), (5.5, .5, "D4"), (6, 1.75, "C#4")])                          # clock says zero, but my heart says go
    out += _line(v + 16, [(0.5, .5, "A3"), (1, .5, "C4"), (1.5, .5, "D4"), (2, .5, "D4"), (2.5, .5, "C4"), (3, .5, "D4"),
                          (3.5, 1, "F4"), (4.5, .5, "E4"), (5, .5, "D4"), (5.5, 1.5, "C4")])          # Paper ticket with a name unwritten
    out += _line(v + 24, [(0.5, .5, "Bb3"), (1, .5, "D4"), (1.5, .5, "F4"), (2, .5, "G4"), (2.5, 1, "F4"), (4, .5, "D4"),
                          (4.5, .5, "E4"), (5, .5, "F4"), (5.5, 2.25, "E4")])                         # something in the dark already knows
    # Pre-chorus: climbing
    out += _line(p + 0, [(0, .75, "D4"), (.75, .75, "E4"), (1.5, 1.5, "F4"), (3.5, .5, "E4"), (4, .5, "D4"), (4.5, 1.5, "E4")])
    out += _line(p + 8, [(0.5, .5, "D4"), (1, .5, "E4"), (1.5, 1, "F4"), (2.5, .5, "E4"), (3, .5, "C4"), (3.5, .5, "C4"),
                         (4, .5, "D4"), (4.5, .5, "E4"), (5, 2, "D4")])
    out += _line(p + 16, [(0, .75, "F4"), (.75, .75, "F4"), (1.5, .5, "E4"), (2, .5, "F4"), (2.5, .5, "G4"), (3, 1, "F4"),
                          (4, .5, "E4"), (4.5, 2, "G4")])
    out += _line(p + 24, [(0, .75, "G4"), (.75, .75, "F4"), (1.5, .5, "Eb4"), (2, 1.5, "D4"), (4.5, .5, "G4"), (5, .5, "F4"),
                          (5.5, 1, "G4")])                                                            # ... here we go!
    out += chorus_melody(c, final=False, lines=range(8))
    out += chorus_melody(SEC["Chorus 2"] * 4, final=False, lines=[0, 1, 6, 7])
    b, bb = SEC["Bridge"] * 4, SEC["Bridge build"] * 4
    out += _line(b, [(0.5, .5, "D4"), (1, .5, "E4"), (1.5, 1, "F4"), (2.5, .5, "E4"), (3, 1.5, "F4"), (4.5, .5, "E4"),
                     (5, .5, "D4"), (5.5, 2.5, "E4")])                                               # If I lose my way, call my name
    out += _line(b + 8, [(0.5, .5, "D4"), (1, .5, "D4"), (1.5, 1, "F4"), (2.5, .5, "G4"), (3, .5, "F4"), (3.5, .5, "D4"),
                         (4, .5, "E4"), (4.5, 1, "E4"), (5.5, .5, "D4"), (6, 2, "E4")])
    out += _line(bb, [(0.5, .5, "D4"), (1, 1, "F4"), (2, 1, "G4"), (3, 3, "F4")])                    # The line goes dark...
    out += _line(bb + 8, [(0.5, .5, "G4"), (1, .5, "G4"), (1.5, 1.5, "G4"), (3, .5, "F4"), (3.5, .5, "G4"), (4, 3, "G4")])
    out += chorus_melody(SEC["Final Chorus"] * 4, final=True, lines=range(8))
    return out


def chorus_melody(start: float, final: bool, lines) -> list:
    """The chorus, line by line (two bars each); the hook "Ride, ride, ride" climbs D-F-G."""
    L = [
        [(0, .75, "D4"), (.75, .75, "F4"), (1.5, 1, "G4"), (2.5, .5, "F4"), (3, .5, "E4"), (3.5, 1, "F4"), (4.5, 2.5, "E4")],
        [(0, .5, "C4"), (.5, .5, "D4"), (1, .5, "E4"), (1.5, .5, "E4"), (2, 1, "G4"), (3, .5, "E4"), (3.5, .5, "D4"),
         (4, .5, "F4"), (4.5, .5, "E4"), (5, 2.5, "D4")],
        [(0, .5, "D4"), (.5, .5, "F4"), (1, 1.5, "G4"), (3, .5, "F4"), (3.5, .5, "G4"), (4, 2, "G4")],
        [(0, .5, "C4"), (.5, .5, "C4"), (1, .5, "F4"), (1.5, .5, "E4"), (2, .5, "C4"), (2.5, .5, "C4"), (3, 1, "E4"),
         (4, .5, "F4"), (4.5, 2.5, "D4")],
        [(0, .75, "D4"), (.75, .75, "F4"), (1.5, 1, "G4"), (2.5, .5, "F4"), (3, .5, "E4"), (3.5, .5, "F4"), (4, .5, "G4"),
         (4.5, 2.5, "E4")],
        [(0, .5, "C4"), (.5, .5, "D4"), (1, .5, "F4"), (1.5, .5, "E4"), (2, 1, "C4"), (3, .5, "C4"), (4, .5, "D4"),
         (4.5, .5, "D4"), (5, .5, "C4"), (5.5, 2, "D4")],
        [(0, .75, "D4"), (.75, .25, "F4"), (1, .5, "F4"), (1.5, .5, "G4"), (2, .5, "F4"), (2.5, .5, "D4"), (4, .5, "Eb4"),
         (4.5, .5, "F4"), (5, 2.5, "G4")],
        [(0, .5, "E4"), (.5, .5, "E4"), (1, .5, "D4"), (1.5, 1, "E4"), (3, .5, "E4"), (3.5, .5, "F4"), (4, 1, "G4"),
         (5, .5, "F4"), (5.5, 1.5, "G4")],
    ]
    if final:  # "Hold on, hold on, here comes the first light" / "...and we ride tonight!"
        L[6] = [(0, .5, "D4"), (.5, 1, "F4"), (1.5, .5, "D4"), (2, 1, "G4"), (3, .5, "F4"), (3.5, .5, "G4"), (4, .5, "G4"),
                (4.5, .5, "G4"), (5, 2.5, "G4")]
        L[7] = [(0, .5, "E4"), (.5, .5, "E4"), (1, .5, "D4"), (1.5, 1, "E4"), (3, .5, "E4"), (3.5, .5, "F4"), (4, 1, "G4"),
                (5, .5, "F4"), (5.5, 2.5, "G4")]
    out = []
    for slot, li in enumerate(lines):
        out += _line(start + slot * 8, L[li])
    return out


# --------------------------------------------------------------------------------------------------
# The band
# --------------------------------------------------------------------------------------------------

def drums(rng) -> list:
    D = DRUM
    out = []

    def bar(b, kick, snare, hat, hat_note="hat", extra=None, hv=78):
        s = b * 4
        out.extend(grid(kick, s, D["kick"], 104))
        out.extend(grid(snare, s, D["snare"], 100))
        out.extend(grid(hat, s, lambda c: D["open"] if c == "o" else D[hat_note], hv, length=0.1))
        for e in extra or []:
            out.extend(e)

    def fill(b, kind="toms"):
        s = b * 4 + 3
        if kind == "toms":  # a descending 16th run on beat 4
            for i, t in enumerate(["t1", "t1", "t2", "t3"]):
                out.append((s + i * 0.25, 0.2, D[t], 92 + i * 6))
        else:  # snare pickup
            for i in range(4):
                out.append((s + i * 0.25, 0.2, D["snare"], 70 + i * 12))

    def crash(b, beat=0.0, v=110):
        out.append((b * 4 + beat, 1.5, D["crash"] if (b % 2 == 0) else D["crash2"], v))

    # Intro: bars 0-3 bass and Rhodes alone; the kit comes in on bar 4 (layers one at a time)
    for b in range(4, 8):
        bar(b, "x.........x.....", "....x.......x...", "x.x.x.x.x.x.x.o.", hv=70)
    fill(7, "toms")
    crash(4)
    # Verse: lean, syncopated kick, ghosted snare, 8th hats
    v = SEC["Verse 1"]
    for i in range(8):
        kick = "x.....x...x..x.." if i % 2 else "x.....x...x....."
        hat = "x.x.x.x.x.x.x.o." if i % 4 == 3 else "x.x.x.x.x.x.x.x."
        bar(v + i, kick, "....x....g..x..g", hat, hv=72)
    fill(v + 7, "toms")
    # Pre-chorus: 16th hats, the kick turning four-on-the-floor in the second half, a snare build into the stop
    p = SEC["Pre-Chorus"]
    for i in range(7):
        kick = "x.....x...x....." if i < 4 else "x...x...x...x..."
        bar(p + i, kick, "....x.......x...", "xxxxxxxxxxxxxxxx", hv=60)
    out.extend(grid("x...x...", (p + 7) * 4, D["kick"], 104))
    for i in range(8):  # 16th snare roll, crescendo, then silence on "here we go!"
        out.append(((p + 7) * 4 + i * 0.25, 0.2, D["snare"], 60 + i * 8))
    out.append(((p + 7) * 4 + 2.0, 1.0, D["crash"], 112))

    def chorus_groove(start, length, ride_last=False, half=False):
        for i in range(length):
            b = start + i
            if half:
                bar(b, "x......xx.x.....", "........X.......", "x.x.x.x.x.x.x.x.", hv=70)
                continue
            kick = "x.....x.x.....x." if i % 2 == 0 else "x.....x.x..x..x."
            hat_note = "ride" if ride_last and i >= length - 8 else "hat"
            bar(b, kick, "....X..g....X..g", "xxxxxxoxxxxxxxox", hat_note=hat_note, hv=74)
            if i % 4 == 0:
                crash(b)
            if i % 4 == 3 and i != length - 1:
                fill(b, "toms" if i % 8 == 7 else "snare")

    chorus_groove(SEC["Chorus"], 16)
    fill(SEC["Chorus"] + 15, "toms")
    chorus_groove(SEC["Chorus instrumental"], 8)
    # Rap: half-time hip-hop pocket (snare on 3), last bar stops for the chorus freeze
    r = SEC["Rap Verse"]
    for i in range(7):
        bar(r + i, "x......x..x...x." if i % 2 else "x......xx.x.....", "........X......g", "x.x.x.x.x.x.x.x.", hv=68)
    out.append(((r + 7) * 4, 1.0, D["crash"], 105))
    chorus_groove(SEC["Chorus 2"], 8)
    # Bridge: drums out. Build: kick quarters, snare 8ths then 16ths, toms, into the final chorus
    bb = SEC["Bridge build"]
    for i in range(4):
        out.extend(grid("x...x...x...x...", (bb + i) * 4, D["kick"], 96 + i * 6))
        sn = "x.x.x.x.x.x.x.x." if i < 2 else "xxxxxxxxxxxxxxxx"
        out.extend((s, l, p, min(127, 50 + i * 14 + int(10 * (s % 4)))) for s, l, p, _ in grid(sn, (bb + i) * 4, D["snare"], 80))
    for i, t in enumerate(["t1", "t1", "t2", "t2", "t3", "t3", "t4", "t4"]):
        out.append(((bb + 3) * 4 + 2 + i * 0.25, 0.2, D[t], 100 + i * 3))
    chorus_groove(SEC["Final Chorus"], 16, ride_last=True)
    # Outro: the groove for three bars, then one last hit
    o = SEC["Outro"]
    for i in range(3):
        bar(o + i, "x.....x.x.....x.", "....X.......X...", "xxxxxxoxxxxxxxox", hv=70)
    crash(o)
    out += [((o + 3) * 4, 2.0, D["kick"], 120), ((o + 3) * 4, 3.0, D["crash"], 124), ((o + 3) * 4, 3.0, D["crash2"], 110)]
    return humanise(out, rng, vel_sd=6)


def percussion(rng) -> list:
    P = PERC
    out = []
    tri = "xxoxxxoxxxoxxxox"  # muted 16ths, open on the off-beat 8ths ("Ice Brushes" triangle)
    conga = ["gx..x.oogx..x.oo", "gx..x.oogx..xoo."]  # heel-toe, slap on 2, two opens on 4

    def tri_bar(b, vel=48):
        out.extend(grid(tri, b * 4, lambda c: P["tri_open"] if c == "o" else P["tri_mute"], vel, length=0.15))

    def conga_bar(b, i, vel=80):
        pat = conga[i % 2]
        for k, ch in enumerate(pat):
            if ch == ".":
                continue
            note = {"g": P["conga_mute"], "x": P["conga_mute"], "o": P["conga_open"]}[ch]
            if ch == "o" and k >= 14:
                note = P["conga_low"]
            v = {"g": 40, "x": vel + 15 if k in (4, 12) else vel - 15, "o": vel}[ch]
            out.append((b * 4 + k * 0.25, 0.2, note, v))

    for b in range(4, 8):
        tri_bar(b, 40)
        conga_bar(b, b, 70)
    for b in range(SEC["Verse 1"], SEC["Pre-Chorus"] + 8):  # verses stay lean: the triangle only, soft
        tri_bar(b, 34)
    for name, length in CHORUS_SECTIONS + [("Rap Verse", 8)]:
        s = SEC[name]
        for i in range(length):
            tri_bar(s + i, 46)
            if name != "Rap Verse":
                conga_bar(s + i, i, 84)
                out.extend(grid("....x.......x...", (s + i) * 4, P["tamb"], 76))
            else:
                conga_bar(s + i, i, 62)
    for b in range(SEC["Outro"], SEC["Outro"] + 3):
        tri_bar(b, 44)
        conga_bar(b, b, 80)
    return humanise(out, rng, vel_sd=7)


def bass(rng) -> tuple[list, list]:
    main, ghosts = [], []
    # Intro: the riff, Rhodes doubling it two octaves up (the Persona 5 trick)
    riff = intro_riff()
    main += riff
    for name, style in [("Verse 1", "lean"), ("Pre-Chorus", "funk"), ("Chorus", "push"), ("Chorus instrumental", "push"),
                        ("Rap Verse", "halftime"), ("Chorus 2", "push"), ("Bridge", "pedal"), ("Bridge build", "funk"),
                        ("Final Chorus", "push"), ("Outro", "funk")]:
        m, g = bass_line(bars(name), SEC[name], style, rng)
        if name == "Pre-Chorus":  # the stop: nothing after "here we go!"
            end = (SEC["Pre-Chorus"] + 7) * 4 + 2
            m = [x for x in m if x[0] < end - 1e-6]
            g = [x for x in g if x[0] < end - 1e-6]
            m.append((end, 1.0, n("A1"), 118))
        if name == "Rap Verse":
            end = (SEC["Rap Verse"] + 7) * 4 + 1
            m = [x for x in m if x[0] < end - 1e-6]
            g = [x for x in g if x[0] < end - 1e-6]
        if name == "Outro":
            end = (SEC["Outro"] + 3) * 4
            m = [x for x in m if x[0] < end - 1e-6] + [(end, 2.5, n("D1"), 124)]
            g = [x for x in g if x[0] < end - 1e-6]
        main += m
        ghosts += g
    return humanise(main, rng, 4), humanise(ghosts, rng, 4)


def intro_riff() -> list:
    """Two bars of riff over Dm9-Bbmaj7, then Gm9-A7alt: octave jumps, a chromatic approach back to D."""
    bar_notes = [
        [(0, .75, "D2"), (1, .25, "D2"), (1.5, .5, "D3"), (2.5, .5, "C3"), (3, .5, "A2"), (3.5, .5, "F2")],
        [(0, .75, "Bb1"), (1, .5, "F2"), (1.5, .5, "Bb2"), (2.5, .5, "A2"), (3, .5, "F2"), (3.5, .5, "D2")],
        [(0, .75, "G1"), (1, .5, "D2"), (1.5, .5, "G2"), (2.5, .5, "F2"), (3, .5, "D2"), (3.5, .5, "Bb1")],
        [(0, .75, "A1"), (1, .25, "A1"), (1.5, .5, "A2"), (2.5, .5, "G2"), (3, .25, "E2"), (3.25, .25, "C#2"),
         (3.5, .5, "C#2")],
    ]
    out = []
    for b in range(8):
        for s, l, p in bar_notes[b % 4]:
            out.append((b * 4 + s, l, n(p), 108 if s == 0 else 92))
    return out


def rhodes(rng) -> list:
    """Comping: voice-led upper structures. Verse: sparse stabs; pre: half notes; chorus: pushes; rap: off-beat
    stabs; bridge: rolled whole notes; intro: doubling the bass riff two octaves up, then the chime."""
    out = []
    for s, l, p, v in intro_riff()[:24]:  # bars 0-3: the riff on Rhodes, two octaves up
        out += [(s, l, p + 24, 72), (s, l, p + 36, 58)]
    prev = None
    rhythms = {
        "stab": [(0.5, .25), (1.75, .5), (3.0, .25), (3.5, .25)],
        "half": [(0, 1.9), (2, 1.9)],
        "push": [(0, 1.4), (1.5, .4), (2.5, 1.0)],
        "offbeat": [(1.5, .25), (3.5, .25)],
        "roll": [(0, 3.9)],
        "intro": [(0, .3), (0.75, .3), (1.5, .5), (3, .25), (3.5, .25)],
    }
    plan = [(4, 8, "intro"), (SEC["Verse 1"], 8, "stab"), (SEC["Pre-Chorus"], 8, "half"), (SEC["Chorus"], 16, "push"),
            (SEC["Chorus instrumental"], 8, "push"), (SEC["Rap Verse"], 8, "offbeat"), (SEC["Chorus 2"], 8, "push"),
            (SEC["Bridge"], 4, "roll"), (SEC["Bridge build"], 4, "half"), (SEC["Final Chorus"], 16, "push"),
            (SEC["Outro"], 3, "intro")]
    for start, length, kind in plan:
        for b in range(start, start + length):
            for s, l in rhythms[kind]:
                beat = b * 4 + s
                if kind == "half" and b == SEC["Pre-Chorus"] + 7 and s > 1:
                    continue  # the stop
                nm = chord_at(beat)
                v = upper(nm, prev, 55, 74)
                prev = v
                vel = {"stab": 84, "half": 70, "push": 80, "offbeat": 76, "roll": 58, "intro": 78}[kind]
                for k, p in enumerate(v):
                    roll = 0.03 * k if kind == "roll" else 0.0
                    out.append((beat + roll, l - roll, p, vel - 4 * k))
            if kind == "push" and b % 2 == 1:  # anticipate the next chord on the last 16th
                nm = chord_at(b * 4 + 4) if b * 4 + 4 < len(BARS) * 4 else chord_at(b * 4)
                for p in upper(nm, prev, 52, 72):
                    out.append((b * 4 + 3.75, 0.5, p, 84))
    # the station chime on the Rhodes, high, at the top of the intro and the outro
    for s in (0.0, SEC["Outro"] * 4 + 8):
        out += [(s, 1.0, n("A5"), 86), (s + 1, 1.0, n("F5"), 82), (s + 2, 2.0, n("D5"), 90)]
    out.append(((SEC["Outro"] + 3) * 4, 3.0, n("D4"), 100))
    for p in upper("Dm9", None, 55, 74):
        out.append(((SEC["Outro"] + 3) * 4, 3.0, p, 96))
    return humanise(out, rng, 5)


def organ(rng) -> list:
    """Upper-structure pads in the pre-chorus and choruses, whole bars, with a stab on the 'and' of 4."""
    out = []
    prev = None
    for name in ["Pre-Chorus", "Chorus", "Chorus 2", "Final Chorus", "Bridge build"]:
        s = SEC[name]
        for i, nm in enumerate(bars(name)):
            b = s + i
            if name == "Pre-Chorus" and i == 7:
                v = upper(chord_at(b * 4), prev, 55, 79)
                out += [(b * 4, 1.9, p, 80) for p in v]
                continue
            for j, part in enumerate(nm.split("|")):
                span = 4 / len(nm.split("|"))
                v = upper(part, prev, 55, 79)
                prev = v
                out += [(b * 4 + j * span, span - 0.1, p, 74) for p in v]
    return humanise(out, rng, 4)


def strings(rng) -> tuple[list, list, list]:
    """(violins long, low strings long, short stabs): the pre-chorus rise, chorus top line doubled in octaves,
    the bridge pad, and in the final chorus the station chime as a counter-line."""
    hi, lo, stabs = [], [], []
    p = SEC["Pre-Chorus"]
    rise = ["F4", "G4", "A4", "A4", "Bb4", "C5", "D5", "C#5"]
    for i, nm in enumerate(bars("Pre-Chorus")):
        lo.append(((p + i) * 4, 3.9 if i < 7 else 2.0, n(["Bb2", "C3", "A2", "D3", "Bb2", "C3", "Eb3", "A2"][i]), 70 + i * 4))
        if i >= 4:
            hi.append(((p + i) * 4, 3.9 if i < 7 else 2.0, n(rise[i]), 66 + i * 5))
    for name, length in CHORUS_SECTIONS:
        s = SEC[name]
        for i, nm in enumerate(bars(name)):
            b = s + i
            first = nm.split("|")[0]
            root, ints, _, _ = chord(first)
            top = sorted(tones(first) - {root % 12})
            # a long top note: the chord's 9th or 3rd, high, with the octave below
            pc = (root + (14 if 14 in ints else ints[1])) % 12
            t = 72 + (pc - 72) % 12
            hi += [(b * 4, 3.9, t, 74), (b * 4, 3.9, t + 12, 62)]
            lo.append((b * 4, 3.9, 36 + (root - 36) % 12, 72))
            if i % 4 == 0:  # "Ride, ride, ride": staccato hits with the brass
                for beat in (0, .75, 1.5):
                    stabs += [(b * 4 + beat, .2, p_, 100) for p_ in upper(first, None, 64, 84, 3)]
        if name == "Final Chorus":  # the station chime as a slow counter-line, every 4 bars
            for k in range(0, length, 4):
                st = (s + k) * 4 + 4
                hi += [(st, 1.5, n("A5"), 80), (st + 1.5, 1.5, n("F5"), 78), (st + 3, 3.0, n("D5"), 82)]
    for b, nm in zip(range(SEC["Bridge"], SEC["Bridge"] + 4), BRIDGE):
        v = upper(nm, None, 60, 79, 3)
        hi += [(b * 4, 3.95, x, 58) for x in v]
        lo.append((b * 4, 3.95, 36 + (chord(nm)[0] - 36) % 12, 60))
    return humanise(hi, rng, 3), humanise(lo, rng, 3), humanise(stabs, rng, 4)


def brass(rng) -> tuple[list, list]:
    """(trumpets, trombones): chorus hits on "Ride, ride, ride", the chime as an answer after "last train",
    the pre-chorus stop hit, and the final hit."""
    tp, tb = [], []
    for name, length in CHORUS_SECTIONS:
        s = SEC[name]
        for i in range(0, length, 4):
            b = s + i
            nm = chord_at(b * 4)
            for beat in (0, .75, 1.5):
                v = upper(nm, None, 64, 79, 2)
                tp += [(b * 4 + beat, .3, x, 104) for x in v]
                tb += [(b * 4 + beat, .3, x, 98) for x in upper(nm, None, 50, 62, 2)]
            # the answer: the station chime (A-F-D) in 8ths at the end of the second bar
            st = (b + 1) * 4 + 2.5
            tp += [(st, .4, n("A4"), 100), (st + .5, .4, n("F4"), 96), (st + 1.0, .9, n("D4"), 104)]
            tb += [(st, .4, n("F3"), 94), (st + .5, .4, n("D3"), 90), (st + 1.0, .9, n("A2"), 98)]
    stop = (SEC["Pre-Chorus"] + 7) * 4 + 2
    tp += [(stop, 1.0, x, 112) for x in upper("A7#5#9", None, 64, 79, 3)]
    tb += [(stop, 1.0, x, 108) for x in (n("A2"), n("G3"))]
    end = (SEC["Outro"] + 3) * 4
    tp += [(end, 2.5, x, 116) for x in (n("A4"), n("C5"), n("E5"))]
    tb += [(end, 2.5, x, 110) for x in (n("D3"), n("F3"), n("C4"))]
    return humanise(tp, rng, 4), humanise(tb, rng, 4)


def guitar(rng, side: int) -> list:
    """Funk chops: muted 16th scratches with chord stabs on the off-beats (chorus and rap), two takes panned
    apart. `side` changes the small variations between the two takes."""
    out = []
    pat = "g.gxg.gxg.gxg.gx" if side == 0 else "gg.xgg.xgg.xgg.x"
    for name, length in CHORUS_SECTIONS + [("Rap Verse", 8)]:
        s = SEC[name]
        for i in range(length):
            b = s + i
            if name == "Rap Verse" and i == 7:
                continue
            for k, c in enumerate(pat):
                if c == ".":
                    continue
                beat = b * 4 + k * 0.25
                nm = chord_at(beat)
                v = upper(nm, None, 60, 74, 3)
                if c == "x":
                    out += [(beat, .18, p, 92) for p in v]
                else:  # a dead scratch: very short and soft
                    out += [(beat, .05, p, 32) for p in v[:2]]
    return humanise(out, rng, 6)


def sax(rng) -> list:
    """The hook on tenor sax in the instrumental chorus (the vocal's first and fifth lines, then a fill),
    and the chime in the outro."""
    out = []
    s = SEC["Chorus instrumental"] * 4
    mel = chorus_melody(s, final=False, lines=[0, 1, 4, 5])
    out += [(st, l, p - 12 if p > 70 else p, 100) for st, l, p, _ in mel]
    o = SEC["Outro"] * 4
    out += [(o + 0.5, .5, n("A3"), 96), (o + 1, .5, n("C4"), 98), (o + 1.5, 1, n("D4"), 104), (o + 3, 1, n("F4"), 100),
            (o + 4.5, .5, n("E4"), 96), (o + 5, 2.5, n("D4"), 104)]
    return humanise(out, rng, 5)


def transitions() -> tuple[list, list]:
    """(reverse cymbals swelling into section starts, booms on the big downbeats)."""
    into = [SEC["Verse 1"], SEC["Chorus"], SEC["Chorus instrumental"], SEC["Chorus 2"], SEC["Final Chorus"]]
    rev = [(b * 4 - 3.5, 3.5, 49, 100) for b in into]
    boom = [(b * 4, 2.0, 36, 110) for b in (SEC["Chorus"], SEC["Chorus 2"], SEC["Final Chorus"])]
    return rev, boom


def piano(rng) -> list:
    """The bridge: rolled chords, inner seconds; and a high octave doubling of the hook in the final chorus."""
    out = []
    for b, nm in zip(range(SEC["Bridge"], SEC["Bridge"] + 4), BRIDGE):
        root = chord(nm)[0]
        lowp = 36 + (root - 36) % 12
        v = [lowp, lowp + 12] + upper(nm, None, 55, 76, 4)
        for k, p in enumerate(sorted(v)):
            out.append((b * 4 + 0.06 * k, 3.9 - 0.06 * k, p, 64 + 2 * k))
    f = SEC["Final Chorus"] * 4
    for st, l, p, _ in chorus_melody(f, final=True, lines=[0, 4]):
        out.append((st, l, p + 12, 70))
    return humanise(out, rng, 4)


# Each part's level against its role's standard level (render.LEVEL), in dB: the guide sits under the band.
GAINS = {"Guide melody (for singing)": -9, "Bass ghost notes": -7, "String stabs": -1, "Trombones": 0,
         "Trumpets": 2, "Guitar left": -3, "Guitar right": -3, "Tenor sax": 2, "Piano": -4, "Organ": -3, "Violins": -2, "Cellos": -3,
         "Reverse cymbals": -2, "Boom": -3, "Congas, triangle, tambourine": -2}


def tracks(seed: int = 7) -> list[Track]:
    rng = np.random.default_rng(seed)
    b_main, b_ghost = bass(rng)
    s_hi, s_lo, s_stab = strings(rng)
    tp, tb = brass(rng)
    rev, boom = transitions()
    mel = guide_melody()
    clear = lambda notes: clear_of(notes, mel, chord_at)  # noqa: E731
    return [
        Track("Guide melody (for singing)", "lead", "sfz:piano", mel, pan=0.0),
        Track("Drums", "drums", "kit:muldjord", drums(rng)),
        Track("Congas, triangle, tambourine", "perc", "kit:latin", percussion(rng), pan=0.25),
        Track("Finger bass", "bass", "sfz:bass_finger", b_main),
        Track("Bass ghost notes", "bass", "sfz:bass_ghost", b_ghost),
        Track("Rhodes", "comp", "sfz:rhodes", clear(rhodes(rng)), pan=-0.1),
        Track("Organ", "pad", "synth:organ_jazz", clear(organ(rng)), pan=0.15),
        Track("Violins", "pad", "sfz:violins", clear(s_hi), pan=-0.35),
        Track("Cellos", "pad", "sfz:cellos", s_lo, pan=0.3),
        Track("String stabs", "riff", "sfz:violins_spic", clear(s_stab), pan=-0.25),
        Track("Trumpets", "counter", "sfz:trumpet_stac", clear(tp), pan=0.2),
        Track("Trombones", "counter", "sfz:trombone_stac", tb, pan=-0.2),
        Track("Guitar left", "arp", "sfz:guitar_clean", clear(guitar(rng, 0)), pan=-0.8),
        Track("Guitar right", "arp", "sfz:guitar_clean", clear(guitar(np.random.default_rng(seed + 1), 1)), pan=0.8),
        Track("Tenor sax", "counter", "sfz:tenor_sax", sax(rng), pan=0.1),
        Track("Piano", "comp", "sfz:piano", clear(piano(rng)), pan=0.15),
        Track("Reverse cymbals", "fx", "sfx:reverse_crash", rev),
        Track("Boom", "fx", "sfx:boom", boom),
    ]


def song(seed: int = 7):
    return build_song("persona_acid_jazz", BPM, 2, "minor", SECTIONS, BARS, tracks(seed), seed)


def add_to_song(song_dir, title_suffix: str = "Persona band (base)") -> int:
    """Add this production to the user's 'Last Train, First Light' song as a new version (the newest version
    with a lyric sheet supplies the words and section feels; vocals are left out so they can be sung again).
    Renders the stems through the app's mixer, masters (with the match EQ) and returns the version index."""
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
    base = next(v for v in reversed(record["versions"]) if v.get("lyric_sheet"))
    s = song()
    summary = song_summary(s)
    idx_file = mixer.next_version_index(song_dir, record)
    new = {k: v for k, v in base.items() if k not in ("vocal_stem", "vocal_stems", "vocals", "vocal_tracks",
                                                       "audio_parts", "working", "mixed_from", "mixed_at")}
    new.update(summary)
    new.update({"file": f"v{idx_file}.ogg", "midi": f"v{idx_file}.mid",
                "title": base["title"].split(" · ")[0] + " · " + title_suffix, "made_at": time.time(),
                "spec": {**base.get("spec", {}), "production": "studio.last_train"},
                "added": [t.name for t in s.tracks], "critic": {"ok": True, "score": 0.0}, "score": 0.0})
    record["versions"].append(new)
    vi = len(record["versions"]) - 1
    parts = []
    for i, t in enumerate(s.tracks):
        parts.append({"id": f"p{i}", "name": t.name, "role": t.role, "instrument": t.instrument, "kind": f"orig:{t.role}",
                      "mine": False, "muted": False, "gain_db": float(GAINS.get(t.name, 0.0)), "pan": t.pan,
                      "notes": [list(x) for x in t.notes]})
    mixer.write_json(song_dir / f"mixer-v{vi}.json", {"version": vi, "parts": parts, "next_id": len(parts),
                                                      "lead_mode": "duck"})
    mixer.write_json(rec_path, record)
    m = mixer.Mixer(song_dir, vi)
    m.render_stems()
    sng = m.song(False)
    _, n = render.song_length(sng)
    music, lead, _, stems = m._stems(n)
    out, _ = render.match_tone(music + lead, amount=0.9, limit_db=4.0)
    mix = render.master(out)
    verdict = critic.judge(sng, mix, stems)
    render.write_audio(mix, song_dir / f"v{idx_file}.ogg")
    render.write_midi(sng, song_dir / f"v{idx_file}.mid")
    record = json.loads(rec_path.read_text())
    record["versions"][vi].update({"critic": verdict, "score": verdict["score"]})
    mixer.write_json(rec_path, record)
    return vi
