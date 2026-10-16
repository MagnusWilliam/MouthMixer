"""Seven instrumentals modelled on the user's reference tracks, two takes each (PERSONA_PRODUCTION section 10).

Each song is written part by part with `refkit`. It takes from its reference only what the measurements say
(reference/profile.py and the sound sheet): tempo, swing, key, the instruments and how each one plays (how
busy, how long its notes are, its register), how loud each group of parts sits, the section layout. The
chords, melodies, riffs and hooks are new. The lead instrument stands where the reference's singer is, on its
own track, so it can be muted for singing.

`make(song_id, lib)` adds one app song per reference with both takes as versions.
"""

from __future__ import annotations

import json

import numpy as np

from ..arrange.arranger import Track
from . import refkit as K
from .production import build_song


def T(name: str, role: str, inst: str, notes: list, pan: float = 0.0) -> Track:
    return Track(name, role, inst, sorted(notes), pan=pan)


# ==================================================================================================
# 5. Safety Off (after Pull the Trigger, with A Way of Life): a swung jazz-funk shuffle in G minor
# ==================================================================================================
# Measured (Pull the Trigger): 97.5 BPM, swing 0.61-0.66 (a triplet shuffle), drums -6.8 LU and bass -7.2 (9-10
# short notes a bar, 0.13 beats long, mono), guitar -19 (busy chops, 11 a bar), piano -16 (5 a bar), other -10
# (a horn section and strings, sustained), vocals -4.8. Chords: Imaj7 and bVImaj7 trade places, iv7, v7, bvii7.

def safety_off(variant: str = "A", seed: int = 5):
    rng = np.random.default_rng(seed)
    # the patterns are on a triplet-8th grid (12 steps a bar): the shuffle is written in, not swung afterwards
    form = [("Intro", "intro", 4, 2), ("Verse 1", "verse", 8, 2), ("Verse 1b", "verse", 8, 2), ("Hook", "chorus", 8, 3),
            ("Verse 2", "verse", 8, 2), ("Hook 2", "chorus", 8, 3), ("Break", "break", 8, 1), ("Verse 3", "verse", 8, 2),
            ("Hook 3", "chorus", 8, 3), ("Hook 4", "chorus", 8, 3), ("Outro", "outro", 4, 1)]
    progs = {"intro": ["Gm9|Ebmaj7", "Cm9|D7#5#9"],
             "verse": ["Gm9|Ebmaj7", "Cm9|Dm7", "Gm9|Ebmaj7", "Fm7|Bb7"],
             "chorus": ["Gmaj7|Ebmaj7", "Gmaj7|Ebmaj7", "Cm9|Dm7", "Ebmaj7|D7#5#9"],
             "break": ["Ebmaj7", "Dm7", "Cm9", "D7sus4|D7#5#9"],
             "outro": ["Gmaj7|Ebmaj7", "Gmaj7|Ebmaj7", "Gmaj7", "Gmaj7"]}
    plan = K.Plan(97.5, 7, "minor", form, progs)
    kit = {1: {"kick": "x.....x.....", "snare": "...r.....r..", "hat": "x.xx.xx.xx.x"},
           2: {"kick": ["x.x..xx..x..", "x.x..x...x.x"], "snare": ["...x....gx.g", "...x.g...x.."],
               "hat": ["xhxxhxxhxxhx", "x.xxhxx.xxho"]},
           3: {"kick": ["x.x..xx..x.x", "x.x..x.x.x.."], "snare": ["...x.g..gx.g", "...X.g.g.x.g"],
               "hat": ["xhxxhxxhxxhx", "xhxxhxxhxxho"], "ride": None}}
    drums = K.drums(plan, kit, rng, fills="toms")
    # the rolling shuffle bass: nearly every triplet 8th, short (Pull the Trigger's ~10 a bar at 0.13 beats)
    bpat = {1: "R.....5..R..", 2: ["R.rRr5R.rO.A", "R.rR.5RrO7.A"], 3: ["RrrRr5RrrO7A", "R.rRr5R.rOrA"]}
    bass, ghost = K.bass(plan, bpat, lo=31, legato=0.55, rng=rng)
    # quiet, busy guitar chops on the right (the reference's guitar sits 19 dB down)
    gpat = {2: ["m.xm.xm.xm.x", "m.xm.xm.x..x"], 3: ["x.xm.xx.xm.x", "m.xm.xx.xm.x"]}
    guitar = K.comp(plan, gpat, lo=62, hi=79, size=3, vel=78, short=0.12, rng=rng)
    # piano: a few held chords a bar, low-mid (the reference's piano: 5 a bar, F#3-Bb4)
    ppat = {1: "x-----x-----", 2: ["x..x-----x..", "x-----x..x--"], 3: ["x..x-----x..", "X..x--x--x.."]}
    keys_inst = "sfz:piano" if variant == "A" else "sfz:rhodes"
    keys = K.comp(plan, ppat, lo=52, hi=72, size=4, vel=72, rng=rng)
    # the horn section: stabs in the verses, long chords and stabs in the hooks
    hpat = {2: ["s.....s..s..", "x-----------"], 3: ["X-----s..s..", "x-----x-----"], "intro": "X..s..X-----"}
    trp, sax, tbn = K.horns(plan, hpat, rng)
    strings = K.pad(plan, (2, 3, "break"), lo=58, hi=80, vel=60)  # the reference's horns and strings play 96% of the time
    cellos = K.pad(plan, (3,), low=True, vel=60)
    # the lead (where the rapper and singer are): a call in the verse, the hook in the chorus
    v1 = ". 5 . 5 7 - 5 4 | 5 - . . . 3 4 5 | 1' - 7 5 4 - 3 4 | 5 - - - . . . ."
    v2 = ". 5 . 5 7 - 5 4 | 5 - . . . 3 4 3 | 1 - 2 3 4 - 3 2 | 1 - - - . . . ."
    h1 = "5 - #3 5 1' - 7 5 | #7 - 1' 2' 5 - 3 - | 4 - 3 4 5 - 4 3 | 3 - 5 - #7 - . ."
    h2 = "5 - #3 5 1' - 7 5 | #7 - 1' 2' #3' - 2' - | 1' - 7 6 5 - 4 3 | 5 - - - - - . ."
    lead = []
    for s in plan.secs:
        if s.kind == "verse":
            a, b = (v2, v1) if s.name == "Verse 1b" else (v1, v2)
            for k in range(0, s.bars, 8):  # 8-bar phrases: the call, then the answer
                lead += K.melody(plan, s.start + k, a + " | " + b, base=60)
        elif s.kind == "chorus":
            lead += K.melody(plan, s.start, h1 + " | " + h2, base=60, vel=104)
    lead = K.humanise(K.shuffle(K.lengthen(K.fit(lead, plan), 0.26), 0.64), rng, 4)
    lead_inst = "sfz:trumpet" if variant == "A" else "sfz:tenor_sax"
    rev, boom = K.risers(plan)
    tracks = [T("Drums", "drums", "kit:band" if variant == "A" else "kit:break", drums),
              T("Bass", "bass", "sfz:bass_tight", bass), T("Bass ghost notes", "bass", "sfz:bass_ghost", ghost),
              T("Guitar chops", "comp", "sfz:hollow_stac", guitar, pan=0.45),
              T("Piano" if variant == "A" else "Rhodes", "comp", keys_inst, keys, pan=-0.2),
              T("Horns: trumpet", "counter", "sfz:trumpet", trp, pan=0.15), T("Horns: tenor sax", "counter", "sfz:weresax", sax, pan=-0.3),
              T("Horns: trombone", "counter", "sfz:trombone", tbn, pan=0.35),
              T("Strings", "pad", "sfz:violins", strings, pan=-0.1), T("Low strings", "pad", "sfz:cellos", cellos, pan=0.2),
              T("Lead: " + ("trumpet" if variant == "A" else "tenor sax"), "lead", lead_inst, lead),
              T("Reverse crash", "fx", "sfx:reverse_crash", rev), T("Boom", "fx", "sfx:boom", boom)]
    cats = {"Drums": "drums", "Bass": "bass", "Bass ghost notes": "bass", "Guitar chops": "guitar",
            "Piano": "piano", "Rhodes": "piano", "Lead: trumpet": "lead", "Lead: tenor sax": "lead"}
    gains = {"Bass ghost notes": -6, "Horns: trombone": -2, "Low strings": -3, "Reverse crash": -6, "Boom": -4}
    return plan, tracks, gains, cats


def _lead(plan, phrases: dict, base: int, vel: int = 98, skip=()) -> list:
    """The lead through the form: phrases {section name or kind: [4-bar phrase, ...]} played in turn through
    each section (a list cycles)."""
    out = []
    for s in plan.secs:
        if s.name in skip or s.kind in skip:
            continue
        ph = phrases.get(s.name) or phrases.get(s.kind)
        if not ph:
            continue
        ph = ph if isinstance(ph, list) else [ph]
        for k, bar in enumerate(range(0, s.bars, 4)):
            out += K.melody(plan, s.start + bar, ph[k % len(ph)], base=base, vel=vel + (6 if s.kind == "chorus" else 0))
    return [n for n in out if n[0] < plan.total * 4]


# ==================================================================================================
# 1. Hollow Hour (after Burn My Dread): dark P3 hip-hop rock in G minor
# ==================================================================================================
# Measured: 97.5 BPM, a sampled break (14 hits a bar, 16th hats, hip-hop swing 0.58), bass -7.9 (sparse, 4 a
# bar), double-tracked overdriven guitars -9.2 the whole song, piano -18 (quiet high 16ths), other -9 (string
# and synth swells; the Virus "Acid" patch), vocals -2. Chords: bIImaj7, iv7 to bvii7, IV in minor.

def hollow_hour(variant: str = "A", seed: int = 1):
    rng = np.random.default_rng(seed)
    form = [("Intro", "intro", 8, 1), ("Verse 1", "verse", 8, 2), ("Pre 1", "pre", 4, 2), ("Chorus 1", "chorus", 8, 3),
            ("Interlude", "break", 4, 2), ("Verse 2", "verse", 8, 2), ("Pre 2", "pre", 4, 2), ("Chorus 2", "chorus", 8, 3),
            ("Bridge", "bridge", 8, 1), ("Chorus 3", "chorus", 8, 3), ("Final Chorus", "chorus", 8, 3),
            ("Outro", "outro", 4, 1)]
    progs = {"intro": ["Gm9", "Abmaj7", "Gm9", "Abmaj7"], "break": ["Gm9", "Abmaj7", "Gm9", "Abmaj7"],
             "verse": ["Gm9", "Abmaj7", "Cm9|Fm7", "Ebmaj7|D7#5#9"],
             "pre": ["Cm9", "Fm7|Bb7sus4", "Ebmaj7", "Abmaj7|D7sus4"],
             "chorus": ["Ebmaj7", "F", "Dm7|Gm9", "Cm9|C", "Abmaj7", "Bb7sus4|Bb", "Cm9", "D7#5#9"],
             "bridge": ["Abmaj7", "Gm9", "Fm7", "Ebmaj7|D7sus4"], "outro": ["Gm9", "Abmaj7", "Gm9", "Gm9"]}
    plan = K.Plan(97.5, 7, "minor", form, progs, swing16=0.56)
    kit = {1: {"kick": "x.......x.......", "hat": "x.x.x.x.x.x.x.x."},
           2: {"kick": ["x...xx..x...xx..", "x...x...x.x.xx.."], "snare": ["....x.......x..g", "....x..g....x..x"],
               "hat": ["xhxhxhxhxhxhxhxh", "xhxhxhxoxhxhxhxh"]},
           3: {"kick": ["x...xx..x...xx..", "x.x.x...x..xxx.."], "snare": ["....X..g....X..g", "....X.......X.gX"],
               "hat": "xhxhxoxhxhxhxoxh"},
           "bridge": {"kick": "x.........x.....", "snare": "........x.......", "hat": "x...x...x...x..."}}
    drums = K.drums(plan, kit, rng, fills="snare")
    bass, _ = K.bass(plan, {2: ["R.....R..R.R....", "R.....R..R.R..A."], 3: ["R...R.R..R.RO..A", "R.....R..R.R5.O."],
                            "bridge": "R-------R-------", "outro": "R---------------"}, lo=31, legato=0.8, rng=rng)
    gpat = {1: ["x---------------", "x-------x-------"], 2: ["x-----x-----x---", "x-----x---x-x---"],
            3: ["x--x--x---x-x---", "x--x--x---x--x--"]}
    gl = K.power(plan, gpat, lo=40, rng=np.random.default_rng(seed + 10))
    gr = K.power(plan, gpat, lo=40, rng=np.random.default_rng(seed + 11))
    gr = [(s + 0.012, l_, p, v - 4) for s, l_, p, v in gr]  # the second take, a hair late: a double-tracked pair
    # the riff (intro, interlude): an original Phrygian line on the lead guitar, an octave over the chords
    riff_txt = "1 . b2 1 . 4 . 3 | 1 . . 5, . 6, 7, . | 1 . b2 1 . 4 . 5 | 6 - 5 - 4 - 3 -"
    riff = []
    for s in plan.secs:
        if s.kind in ("intro", "break") and (s.kind == "break" or s.start + 4 <= plan.total):
            for bar in range(0 if s.kind == "break" else 4, s.bars, 4):
                riff += K.melody(plan, s.start + bar, riff_txt, base=60, grid=0.5, vel=100)  # G3 up: in the guitar's range
    piano = K.arp(plan, {1: "1.3.4.3.1.3.4.3.", 2: "1.3.4.3.1.3.4.3.", "bridge": "1-3-4-3-2-3-4-3-"}, lo=67, hi=86, vel=58,
                  rng=rng)
    if variant == "B":  # take B: the piano carries the bridge and verses with its left hand too
        piano = K.comp(plan, {"bridge": "x-------x-------", 2: "x-------x---x---"}, lo=55, hi=79, vel=70, left_hand=True,
                       rng=rng) + piano
    acid = K.arp(plan, {3: ["1.11.21.1.13.1.2", "1.11.21.1.14.3.2"], "break": "1.11.21.1.13.1.2"}, lo=36, hi=55, vel=96,
                 rng=rng)
    strings = K.pad(plan, (2, 3, "bridge"), lo=60, hi=84, vel=62)
    swell = K.pad(plan, ("pre",), lo=55, hi=79, vel=70)
    phrases = {"verse": ["5 . 5 6 5 . 4 3 | 4 - - . . . . . | 3 . 3 4 3 . 2 1 | 2 - - - . . . .",
                         "5 . 5 6 5 . 4 3 | 4 - 5 - 6 - 5 - | 4 . 3 . 2 . 1 . | 7, - - - . . . ."],
               "pre": "1' - 7 6 5 - 4 - | 3 - 4 5 - - . . | 6 - 5 4 3 - 2 - | 5 - - - - - . .",
               "chorus": ["5' - 4' 3' 4' - 3' 2' | 1' - - - 7 - 1' - | 2' - 1' 7 1' - 5 - | 4 - 5 - 3 - . .",
                          "5' - 4' 3' 4' - 3' 2' | 1' - - - 7 - 1' 2' | 3' - 2' 1' 7 - 1' - | #7 - - - 2' - - -"]}
    lead_inst = "synth:virus_lead" if variant == "A" else "sfz:violins"
    lead = K.humanise(K.swing(K.lengthen(K.fit(_lead(plan, phrases, 60), plan), 0.26), plan), rng, 4)
    scratch = [(s.start * 4.0 + 3.5, 0.5, 60, 100) for s in plan.secs if s.kind in ("verse", "chorus")]
    rev, boom = K.risers(plan)
    tracks = [T("Drums (break)", "drums", "kit:break", drums), T("Bass", "bass", "sfz:bass_tight", bass),
              T("Guitar L", "comp", "sfz:egtr_drive", gl, pan=-0.75), T("Guitar R", "comp", "sfz:egtr_drive", gr, pan=0.75),
              T("Riff guitar", "counter", "sfz:egtr_drive", riff, pan=0.1),
              T("Piano", "arp", "sfz:piano", piano, pan=0.25), T("Acid synth", "counter", "synth:acid", acid, pan=-0.15),
              T("Strings", "pad", "sfz:violins", strings), T("Synth swell", "pad", "synth:super_pad", swell),
              T("Lead: " + ("synth" if variant == "A" else "violins"), "lead", lead_inst, lead),
              T("Scratches", "fx", "sfx:scratch", scratch), T("Reverse crash", "fx", "sfx:reverse_crash", rev),
              T("Boom", "fx", "sfx:boom", boom)]
    cats = {"Drums (break)": "drums", "Bass": "bass", "Guitar L": "guitar", "Guitar R": "guitar", "Riff guitar": "guitar",
            "Piano": "piano", "Lead: synth": "lead", "Lead: violins": "lead"}
    gains = {"Riff guitar": 2, "Scratches": -4, "Reverse crash": -6, "Boom": -4, "Synth swell": -3}
    return plan, tracks, gains, cats


# ==================================================================================================
# 2. Paint the City (after Color Your Night): night city-pop funk in Db major
# ==================================================================================================
# Measured: 95.7 BPM, straight 16ths; the grand piano is the main instrument (-8.8, held chords); bass -4.7
# (9 staccato notes a bar, 0.08 beats, mono), drums -9.1, guitar -17.6 (a few chops), other -10 (Groove Holmes
# jazz organ, strings), vocals -5.9. The same energy the whole song. Chords every two beats: vi7 to V, ii7 to
# iii7, IVmaj7 to II.

def paint_the_city(variant: str = "A", seed: int = 2):
    rng = np.random.default_rng(seed)
    form = [("Intro", "intro", 8, 2), ("Verse 1", "verse", 8, 2), ("Verse 1b", "verse", 8, 2), ("Hook 1", "chorus", 8, 3),
            ("Verse 2", "verse", 8, 2), ("Hook 2", "chorus", 8, 3), ("Break", "break", 8, 1), ("Hook 3", "chorus", 8, 3),
            ("Hook 4", "chorus", 8, 3), ("Outro", "outro", 4, 1)]
    progs = {"intro": ["Gbmaj7|Fm7", "Bbm7|Ab", "Gbmaj7|Fm7", "Ebm7|Ab7sus4"],
             "verse": ["Gbmaj7|Fm7", "Bbm7|Ab", "Gbmaj7|Fm7", "Ebm7|Ab7sus4"],
             "chorus": ["Dbmaj7|Ebm7", "Fm7|Bbm7", "Gbmaj7|Ebmaj7", "Fm7|F7", "Bbm7|Ab", "Gbmaj7|Fm7", "Ebm7|Ab7sus4", "Dbmaj7"],
             "break": ["Bbm7", "Ebm7|Ab", "Bbm7", "Gbmaj7|F7"], "outro": ["Gbmaj7|Fm7", "Ebm7|Ab7sus4", "Dbmaj7", "Dbmaj7"]}
    plan = K.Plan(95.7, 1, "major", form, progs)
    kit = {1: {"kick": "x.......x.......", "snare": "....r.......r...", "hat": "x.h.x.h.x.h.x.h."},
           2: {"kick": ["x.x....x.......x", "x.x....x..x....."], "snare": ["....x.......x...", "....x..g....x..g"],
               "hat": ["x.h.xhxxh.x.xhxx", "x.h.xhxxh.x.x.ox"]},
           3: {"kick": ["x.x....x.......x", "x.x....x..x....x"], "snare": ["....X.......X...", "....X..g....X.g."],
               "hat": ["xhxhxhxxhhxhxhxo", "xhxhxhxxhhxhxhxx"]}}
    drums = K.drums(plan, kit, rng)
    bpat = {1: "R.......R.....5.", 2: ["R..R.ROR.RO.R.R.", "R..R.RRO.R5.R.OA"], 3: ["R..R.ROR.RO.R.RA", "R.OR.RRO.R5.ROOA"]}
    bass, ghost = K.bass(plan, {k: [p.replace("R.R.", "RDR.") for p in (v if isinstance(v, list) else [v])]
                                for k, v in bpat.items()}, lo=25, legato=0.38, rng=rng)
    piano = K.comp(plan, {1: "x-------x-------", 2: ["x--x--x---x-----", "x--x--x---x--x--"],
                          3: ["x--x--x---x--x--", "X--x--x-x-x--x--"]}, lo=54, hi=73, size=4, vel=84, left_hand=True, rng=rng)
    organ = K.comp(plan, {2: "x---------------", 3: ["x-------x-------", "x-----------x---"], 1: "x---------------"},
                   lo=58, hi=79, size=4, vel=72, rng=rng)
    guitar = K.comp(plan, {2: "....x.......x...", 3: ["....x..x....x...", "....x.......x..x"]}, lo=64, hi=81, size=3,
                    vel=82, short=0.14, rng=rng)
    strings = K.pad(plan, (3,), lo=62, hi=86, vel=60)
    phrases = {"verse": [". . 3 5 6 - 5 3 | 2 - 1 - . . . . | . . 3 5 6 - 1' 6 | 5 - - - . . . .",
                         ". . 3 5 6 - 5 3 | 2 - 1 - . 1 2 3 | 4 - 3 2 1 - 2 - | 5, - - - . . . ."],
               "chorus": ["1' - 7 5 . 5 6 1' | 2' - 1' 6 . . 5 6 | 1' - 7 6 5 - 3 - | 5 - 3 - 2 - . .",
                          "1' - 7 5 . 5 6 1' | 2' - 1' 6 . 6 1' 2' | 3' - 2' 1' 6 - 5 - | 1' - - - - - . ."]}
    lead_inst = "sfz:weresax" if variant == "A" else "synth:virus_lead"
    lead = K.humanise(K.lengthen(K.fit(_lead(plan, phrases, 60 if variant == "A" else 72), plan), 0.26), rng, 4)
    # take B adds the sax as an answer in the hooks under the synth lead
    answer = []
    if variant == "B":
        for s in plan.secs:
            if s.kind == "chorus":
                for bar in range(1, s.bars, 2):
                    answer += K.melody(plan, s.start + bar, ". . . . 5 6 1' 6", base=60, vel=84)
        answer = K.humanise(K.fit(answer, plan), rng, 4)
    rev, boom = K.risers(plan)
    tracks = [T("Drums", "drums", "kit:band", drums), T("Bass", "bass", "sfz:bass_tight", bass),
              T("Bass ghost notes", "bass", "sfz:bass_ghost", ghost),
              T("Piano", "comp", "sfz:piano", piano, pan=-0.1), T("Organ", "pad", "synth:organ_jazz", organ, pan=0.25),
              T("Guitar", "comp", "sfz:hollow_stac", guitar, pan=0.55), T("Strings", "pad", "sfz:violins", strings, pan=-0.2),
              T("Lead: " + ("sax" if variant == "A" else "synth"), "lead", lead_inst, lead),
              T("Sax answers", "counter", "sfz:weresax", answer, pan=-0.35),
              T("Reverse crash", "fx", "sfx:reverse_crash", rev), T("Boom", "fx", "sfx:boom", boom)]
    cats = {"Drums": "drums", "Bass": "bass", "Bass ghost notes": "bass", "Piano": "piano", "Guitar": "guitar",
            "Lead: sax": "lead", "Lead: synth": "lead"}
    gains = {"Bass ghost notes": -5, "Reverse crash": -8, "Boom": -6, "Sax answers": -3}
    return plan, tracks, gains, cats


# ==================================================================================================
# 3. High Tide (after Full Moon Full Life): bright J-rock in Ab major
# ==================================================================================================
# Measured: 95.7 BPM, straight 16ths; wide overdriven guitars -8.5 (97% of the time, big chords), bass -6.8 (6 a
# bar, held), drums -8.7, piano -12 (held chords F3-C#5), other -12 (strings), vocals -5.8. Builds intro, verse,
# pre, chorus; a long last chorus. Chords: iii7 to VI7 to ii7, bVImaj7 to vi7, IVmaj7 to Imaj7.

def high_tide(variant: str = "A", seed: int = 3):
    rng = np.random.default_rng(seed)
    form = [("Intro", "intro", 4, 3), ("Verse 1", "verse", 8, 2), ("Pre 1", "pre", 4, 2), ("Chorus 1", "chorus", 12, 3),
            ("Interlude", "break", 4, 2), ("Verse 2", "verse", 8, 2), ("Pre 2", "pre", 4, 2), ("Chorus 2", "chorus", 12, 3),
            ("Bridge", "bridge", 8, 1), ("Final Chorus", "chorus", 16, 3), ("Outro", "outro", 4, 2)]
    progs = {"intro": ["Dbmaj7", "Eb", "Cm7", "Fm7"], "break": ["Dbmaj7", "Eb", "Cm7", "Fm7"],
             "verse": ["Dbmaj7|Cm7", "Fm7|Abmaj7", "Bbm7|Cm7", "Dbmaj7|Eb"],
             "pre": ["Bbm7", "Cm7|F7", "Bbm7|Abmaj7", "Emaj7|Eb7sus4"],
             "chorus": ["Dbmaj7", "Eb|Cm7", "F7|Bbm7", "Abmaj7|Ab7", "Dbmaj7", "Eb|Cm7", "Emaj7|Fm7", "Bbm7|Eb7sus4"],
             "bridge": ["Emaj7", "Fm7", "Dbmaj7", "Eb7sus4|Eb"], "outro": ["Dbmaj7", "Eb", "Abmaj7", "Abmaj7"]}
    plan = K.Plan(95.7, 8, "major", form, progs)
    kit = {1: {"kick": "x.......x.......", "snare": "............x...", "hat": "x...x...x...x..."},
           2: {"kick": ["x..x..x...x..x..", "x..x..x...x.xx.."], "snare": "....x.......x...",
               "hat": ["XhxhXhxhXhxhXhxh", "XhxhXhxhXhxhXhxo"]},
           3: {"kick": ["x..x..x...x..x..", "x..x..x.x.x..x.."], "snare": ["....X.......X...", "....X.......X.x."],
               "ride": "X.x.X.x.X.x.X.x."}}
    drums = K.drums(plan, kit, rng, fills="toms")
    bass, _ = K.bass(plan, {1: "R-------R-------", 2: ["R--R--R---R--R--", "R--R--R---R--RO-"],
                            3: ["R..R..R...R..RO.", "R..R..R.5.R..ROA"]}, lo=32, legato=0.85, rng=rng)
    gpat = {2: ["x-----x---x-----", "x-----x---x--x--"], 3: ["x--x--x---x--x--", "x--x--x-x-x--x--"]}
    gl = K.power(plan, gpat, lo=44, rng=np.random.default_rng(seed + 10))
    gr = [(s + 0.012, l_, p, v - 4) for s, l_, p, v in K.power(plan, gpat, lo=44, rng=np.random.default_rng(seed + 11))]
    clean = K.arp(plan, {2: ["1.2.3.4.3.2.1.2.", "1.2.3.4.5.4.3.2."], "pre": "1.2.3.4.3.2.1.2.", "bridge": "1-2-3-4-3-2-1-2-"},
                  lo=60, hi=84, vel=70, rng=rng)
    piano = K.comp(plan, {1: "x-------x-------", 2: "x-------x-------", 3: ["x-------x-------", "x-----x-x-------"]},
                   lo=53, hi=73, vel=76, rng=rng)
    strings = K.pad(plan, (3, "bridge", "pre"), lo=63, hi=87, vel=64)
    cellos = K.pad(plan, (3,), low=True, vel=60)
    phrases = {"verse": ["3 - 3 2 3 - 5 - | 6 - 5 3 2 - . . | 3 - 3 2 3 - 5 6 | 1' - 7 6 5 - . .",
                         "3 - 3 2 3 - 5 - | 6 - 5 3 2 - 1 2 | 3 - 2 1 6, - 1 - | 2 - - - . . . ."],
               "pre": "6 - 6 5 6 - 1' - | 7 - 6 5 3 - . . | 6 - 6 5 6 - 1' 2' | 3' - - - 2' - - -",
               "chorus": ["5' - - 3' 2' - 1' - | 2' - 3' - 5 - . . | 6 - 1' 2' 3' - 2' 1' | 2' - - - . . . .",
                          "5' - - 3' 2' - 1' - | 2' - 3' - 5 - 5 6 | 1' - 7 6 5 - 3 2 | 3 - - - . . . .",
                          "5' - - 3' 2' - 1' - | 2' - 3' - 5 - . . | 6 - 1' 2' 3' - 2' 1' | 2' - - - . . . .",
                          "6 - 1' 2' 3' - 2' 1' | 2' - 1' 7 1' - - - | 1' - - - - - - - | . . . . . . . ."]}
    lead_inst = "synth:virus_lead" if variant == "A" else "sfz:violins"
    lead = K.humanise(K.lengthen(K.fit(_lead(plan, phrases, 60), plan), 0.26), rng, 4)
    rev, boom = K.risers(plan)
    tracks = [T("Drums", "drums", "kit:band", drums), T("Bass", "bass", "sfz:bass_tight", bass),
              T("Guitar L", "comp", "sfz:egtr_drive", gl, pan=-0.8), T("Guitar R", "comp", "sfz:egtr_drive", gr, pan=0.8),
              T("Clean guitar", "arp", "sfz:egtr_clean", clean, pan=0.35), T("Piano", "comp", "sfz:piano", piano, pan=-0.2),
              T("Strings", "pad", "sfz:violins", strings), T("Low strings", "pad", "sfz:cellos", cellos, pan=0.15),
              T("Lead: " + ("synth" if variant == "A" else "violins"), "lead", lead_inst, lead),
              T("Reverse crash", "fx", "sfx:reverse_crash", rev), T("Boom", "fx", "sfx:boom", boom)]
    cats = {"Drums": "drums", "Bass": "bass", "Guitar L": "guitar", "Guitar R": "guitar", "Clean guitar": "guitar",
            "Piano": "piano", "Lead: synth": "lead", "Lead: violins": "lead"}
    gains = {"Clean guitar": -4, "Low strings": -3, "Reverse crash": -6, "Boom": -4}
    if variant == "B":  # take B: the clean guitar arpeggios carry the verses, no overdrive until the chorus
        gpat_b = {3: gpat[3]}
        tracks[2] = T("Guitar L", "comp", "sfz:egtr_drive", K.power(plan, gpat_b, lo=44, rng=np.random.default_rng(seed + 10)), pan=-0.8)
        tracks[3] = T("Guitar R", "comp", "sfz:egtr_drive",
                      [(s + 0.012, l_, p, v - 4) for s, l_, p, v in K.power(plan, gpat_b, lo=44, rng=np.random.default_rng(seed + 11))],
                      pan=0.8)
        gains["Clean guitar"] = 0
    return plan, tracks, gains, cats


# ==================================================================================================
# 4. Down to the Wire (after It's Going Down Now): acid-jazz battle in C# minor at 166
# ==================================================================================================
# Measured: 166.7 BPM; the snare on beat 3 (half time) with a full backbeat in the big parts, drums -6.8, bass
# -6.9 (7 a bar, rarely on the root: it moves), guitar -10 (held, wide), piano -14.5 (2 held chords a bar), other
# -14.7 (bright brass, strings, a jazz organ, cowbell), vocals -6.4 (rap). Chords: bIIImaj7, bVImaj7 to v7,
# the half-step slide up into bIIImaj7.

def down_to_the_wire(variant: str = "A", seed: int = 4):
    rng = np.random.default_rng(seed)
    form = [("Intro", "intro", 8, 3), ("Verse 1", "verse", 16, 2), ("Pre 1", "pre", 8, 2), ("Chorus 1", "chorus", 8, 3),
            ("Riff", "break", 4, 3), ("Verse 2", "verse", 16, 2), ("Pre 2", "pre", 8, 2), ("Chorus 2", "chorus", 8, 3),
            ("Breakdown", "bridge", 8, 1), ("Chorus 3", "chorus", 8, 3), ("Final Chorus", "chorus", 8, 3),
            ("Outro", "outro", 4, 3)]
    progs = {"intro": ["C#m9", "Amaj7|G#m7", "F#m9|Emaj7", "Dmaj7|G#7#5#9"],
             "verse": ["C#m9|Emaj7", "Amaj7|G#m7", "F#m9|Emaj7", "Dmaj7|Emaj7"],
             "pre": ["Amaj7", "G#m7", "F#m9", "G#7sus4|G#7#5#9"],
             "chorus": ["Amaj7|Emaj7", "G#m7|C#m9", "F#m9|Emaj7", "Dmaj7|G#7#5#9"],
             "break": ["C#m9", "C#m9|Emaj7", "F#m9", "G#7#5#9"], "bridge": ["Amaj7", "G#m7", "F#m9", "Emaj7|G#7sus4"],
             "outro": ["C#m9", "Amaj7|G#m7", "F#m9|G#7#5#9", "C#m9"]}
    plan = K.Plan(166.7, 1, "minor", form, progs)
    kit = {1: {"kick": "x.........x.....", "snare": "........x.......", "ride": "x...x...x...x..."},
           2: {"kick": ["x.....xx..x.....", "x.....x...x...x."], "snare": ["........x......g", "........x.....gx"],
               "hat": ["x.x.x.x.x.x.x.x.", "x.x.x.x.x.x.x.o."]},
           3: {"kick": ["x.....x.x.x.....", "x.x...x...x...x."], "snare": ["....X.......X...", "....X.......X..x"],
               "hat": "x.x.x.o.x.x.x.o."}}
    drums = K.drums(plan, kit, rng, fills="toms")
    perc = K.percussion(plan, {3: {"tamb": "....x.......x..."}, 2: {"shaker": "x.x.x.x.x.x.x.x."}}, rng)
    bass, ghost = K.bass(plan, {1: "R-------5-------", 2: ["R.R.5.O.R.R.7.A.", "R.5.O.7.R.5.3.A."],
                                3: ["R.RO5.O.R.RO7.A.", "R.O.5.7.R.O.5.A."]}, lo=25, legato=0.8, rng=rng)
    gpat = {2: "x---------------", 3: ["x-------x---x---", "x---x---x---x---"], "intro": "x-------x---x---"}
    gl = K.power(plan, gpat, lo=40, rng=np.random.default_rng(seed + 10))
    gr = [(s + 0.012, l_, p, v - 4) for s, l_, p, v in K.power(plan, gpat, lo=40, rng=np.random.default_rng(seed + 11))]
    piano = K.comp(plan, {1: "x---------------", 2: "x-------x-------", 3: "x-------x-------"}, lo=49, hi=78, vel=74, rng=rng)
    organ = K.comp(plan, {2: "x---------------", 3: ["x-------x-------", "x-----x---x-----"], 1: "x---------------"},
                   lo=56, hi=79, vel=72, rng=rng)
    hpat = {3: ["X..s..s.X...s...", "X..s..s...s.X---"], 2: ["s.......s.......", "................"],
            "intro": ["X-------s.s.X---", "X..s..s.X-------"], "break": "X.s.X.s.X.s.X---"}
    trp, sax, tbn = K.horns(plan, hpat, rng)
    strings = K.pad(plan, (3, "bridge"), lo=61, hi=85, vel=62)
    phrases = {"verse": ["1' - - - 7 - 1' - | 3' - - - 2' - 1' - | 7 - - - 5 - 6 - | 5 - - - . . . .",
                         "1' - - - 7 - 1' - | 3' - - - 4' - 3' - | 2' - - - 1' - 7 - | 1' - - - . . . ."],
               "pre": ["6 - - - 5 - 4 - | 5 - - - . . . . | 6 - - - 7 - 1' - | 2' - - - #7 - - -"],
               "chorus": ["5' - - - 4' - 3' - | 4' - 3' - 2' - - - | 3' - - - 2' - 1' - | 7 - 1' - 2' - - -",
                          "5' - - - 4' - 3' - | 4' - 3' - 2' - 1' - | 6 - - - 1' - 3' - | 2' - - - #7 - - -"]}
    lead_inst = "sfz:trumpet" if variant == "A" else "synth:organ_rock"
    lead = K.humanise(K.lengthen(K.fit(_lead(plan, phrases, 60), plan), 0.3), rng, 4)
    rev, boom = K.risers(plan)
    tracks = [T("Drums", "drums", "kit:band", drums), T("Percussion", "perc", "kit:latin", perc, pan=0.3),
              T("Bass", "bass", "sfz:bass_tight", bass),
              T("Guitar L", "comp", "sfz:egtr_drive", gl, pan=-0.8), T("Guitar R", "comp", "sfz:egtr_drive", gr, pan=0.8),
              T("Piano", "comp", "sfz:piano", piano, pan=-0.15), T("Organ", "pad", "synth:organ_jazz", organ, pan=0.2),
              T("Horns: trumpet", "counter", "sfz:trumpet", trp, pan=0.15), T("Horns: tenor sax", "counter", "sfz:weresax", sax, pan=-0.3),
              T("Horns: trombone", "counter", "sfz:trombone", tbn, pan=0.35), T("Strings", "pad", "sfz:violins", strings),
              T("Lead: " + ("trumpet" if variant == "A" else "organ"), "lead", lead_inst, lead),
              T("Reverse crash", "fx", "sfx:reverse_crash", rev), T("Boom", "fx", "sfx:boom", boom)]
    if variant == "B":  # take B: no rock guitars; the organ leads, the horns answer
        tracks = [t for t in tracks if not t.name.startswith("Guitar")]
    cats = {"Drums": "drums", "Percussion": "drums", "Bass": "bass", "Guitar L": "guitar", "Guitar R": "guitar",
            "Piano": "piano", "Lead: trumpet": "lead", "Lead: organ": "lead"}
    gains = {"Percussion": -6, "Horns: trombone": -2, "Reverse crash": -6, "Boom": -4}
    return plan, tracks, gains, cats


# ==================================================================================================
# 6. Lunchbell (after School Days, with Signs of Love): disco funk in D major
# ==================================================================================================
# Measured (School Days): 117.5 BPM, four on the floor, drums loud (-3.5), octave synth bass -9.3 (9 short notes
# a bar, D1-G1), piano -16 (6 a bar, F#2-G4), other -12.5 (bright synth arps and strings, C#4-A6, 8 a bar), a
# guitar only now and then, vocals -5.5. All major sevenths: IImaj7 to IIImaj7, iii7 to ii7, IVmaj7 to iii7.

def lunchbell(variant: str = "A", seed: int = 6):
    rng = np.random.default_rng(seed)
    form = [("Intro", "intro", 8, 2), ("Verse 1", "verse", 8, 2), ("Verse 1b", "verse", 8, 2), ("Chorus 1", "chorus", 8, 3),
            ("Chorus 1b", "chorus", 8, 3), ("Verse 2", "verse", 8, 2), ("Chorus 2", "chorus", 8, 3),
            ("Chorus 2b", "chorus", 8, 3), ("Break", "break", 8, 1), ("Final Chorus", "chorus", 8, 3), ("Outro", "outro", 4, 1)]
    progs = {"intro": ["Dmaj7|F#m7", "Gmaj7|F#m7", "Em7|F#m7", "Gmaj7|A"],
             "verse": ["Dmaj7|F#m7", "Gmaj7|F#m7", "Em7|F#m7", "Gmaj7|A"],
             "chorus": ["Gmaj7|F#m7", "Em7|Dmaj7", "Emaj7|F#maj7", "Gmaj7|A7sus4", "Gmaj7|F#m7", "Bm7|Em7", "Emaj7|F#maj7",
                        "Gmaj7|A"],
             "break": ["Bm7", "F#m7", "Gmaj7", "A7sus4|A"], "outro": ["Gmaj7|F#m7", "Em7|A7sus4", "Dmaj7", "Dmaj7"]}
    plan = K.Plan(117.5, 2, "major", form, progs)
    kit = {1: {"kick": "x...x...x...x...", "hat": "..o...o...o...o."},
           2: {"kick": "x...x...x...x...", "snare": ["....x.......x...", "....x.......x..x"], "hat": "xho.xho.xho.xhox"},
           3: {"kick": "x...x...x...x...", "snare": ["....X.......X...", "....X.......X.xX"], "hat": "xhohxhohxhohxhox"}}
    drums = K.drums(plan, kit, rng)
    perc = K.percussion(plan, {3: {"tamb": "xhxhxhxhxhxhxhxh"}, 2: {"shaker": "xhxhxhxhxhxhxhxh"}}, rng)
    bass, _ = K.bass(plan, {1: "R.O.R.O.R.O.R.O.", 2: ["R.O.R.O.R.O.R.OA", "R.OOR.O.R.O.ROO."],
                            3: ["R.OOR.O.R.OOR.OA", "R.O.R.OOR.O.ROOA"]}, lo=26, legato=0.45, rng=rng)
    piano = K.comp(plan, {2: ["x..x..x..x.x.x..", "x..x..x..x..x..."], 3: ["x..x..x..x.x.x..", "X..x..x..x.x.x.x"],
                          1: "x-------x-------"}, lo=48, hi=70, size=4, vel=74, rng=rng)
    arp_ = K.arp(plan, {2: ["1234321412343214", "1234543212345432"], 3: ["1234543212345432", "1324354213243542"],
                        "intro": "1-3-4-3-1-3-4-3-"}, lo=66, hi=90, vel=70, rng=rng)
    strings = K.pad(plan, (3, "break"), lo=66, hi=91, vel=60)
    guitar = K.comp(plan, {3: ["....x..x....x..x", "....x..x..x.x..."]}, lo=64, hi=81, size=3, vel=80, short=0.12, rng=rng)
    phrases = {"verse": ["3 - 2 1 2 - 3 - | 5 - 3 - 2 - . . | 3 - 2 1 2 - 3 5 | 6 - 5 - 3 - . .",
                         "3 - 2 1 2 - 3 - | 5 - 3 - 2 - 1 2 | 3 - 5 - 6 - 5 3 | 2 - - - . . . ."],
               "chorus": ["1' - 7 6 5 - 3 - | 6 - 5 3 2 - 3 - | 6 - #4 - 7 - #5 - | 6 - - - 5 - . .",
                          "1' - 7 6 5 - 3 - | 6 - 5 3 2 - 3 5 | 6 - #4 - 7 - #5 - | 1' - - - - - . ."]}
    lead_inst = "synth:virus_lead" if variant == "A" else "sfz:hollow"
    lead = K.humanise(K.lengthen(K.fit(_lead(plan, phrases, 60 if variant == "B" else 72), plan), 0.26), rng, 4)
    rev, boom = K.risers(plan)
    tracks = [T("Drums", "drums", "kit:disco", drums), T("Percussion", "perc", "kit:latin", perc, pan=-0.3),
              T("Synth bass", "bass", "synth:virus_bass", bass),
              T("Piano", "comp", "sfz:piano", piano, pan=-0.15), T("Synth arp", "arp", "synth:pluck", arp_, pan=0.3),
              T("Strings", "pad", "sfz:violins", strings), T("Guitar", "comp", "sfz:hollow_stac", guitar, pan=0.55),
              T("Lead: " + ("synth" if variant == "A" else "guitar"), "lead", lead_inst, lead),
              T("Reverse crash", "fx", "sfx:reverse_crash", rev), T("Boom", "fx", "sfx:boom", boom)]
    if variant == "B":  # take B: a finger bass instead of the synth, Rhodes instead of piano
        tracks[2] = T("Bass", "bass", "sfz:bass_tight", [(s, l_, p + 12 if p < 28 else p, v) for s, l_, p, v in bass])
        tracks[3] = T("Rhodes", "comp", "sfz:rhodes", piano, pan=-0.15)
    cats = {"Drums": "drums", "Percussion": "drums", "Synth bass": "bass", "Bass": "bass", "Piano": "piano",
            "Rhodes": "piano", "Guitar": "guitar", "Lead: synth": "lead", "Lead: guitar": "lead"}
    gains = {"Percussion": -6, "Reverse crash": -8, "Boom": -6}
    return plan, tracks, gains, cats


# ==================================================================================================
# 7. Reach for the Stars (after When the Moon's Reaching Out Stars -Reload-): a swung city shuffle in Ab major
# ==================================================================================================
# Measured: 120.2 BPM, swung (hats 0.59, bass 0.67); drums -7 (busy), bass -4.8 (loud, 7 a bar, C2-C3, rarely on
# the root: a moving line), guitar -10 (chords on the off-beats), piano -11 (held), other -10 (FM pad, strings,
# percussion), vocals -5.4. Chords: ii7 and iii7 and vi7 into IVmaj7, IIsus4 to vi7, bVIImaj7.

def reach_for_the_stars(variant: str = "A", seed: int = 7):
    rng = np.random.default_rng(seed)
    form = [("Intro", "intro", 4, 2), ("Verse 1", "verse", 16, 2), ("Pre 1", "pre", 4, 2), ("Chorus 1", "chorus", 12, 3),
            ("Verse 2", "verse", 8, 2), ("Pre 2", "pre", 4, 2), ("Chorus 2", "chorus", 12, 3), ("Break", "break", 8, 1),
            ("Final Chorus", "chorus", 16, 3), ("Outro", "outro", 4, 2)]
    progs = {"intro": ["Dbmaj7|Cm7", "Bbm7|Eb7sus4"], "verse": ["Bbm7|Dbmaj7", "Cm7|Dbmaj7", "Bb7sus4|Fm7", "Fm7|Abmaj7"],
             "pre": ["Dbmaj7", "Cm7|Fm7", "Bbm7|Dbmaj7", "Eb7sus4|Eb"],
             "chorus": ["Dbmaj7|Cm7", "Bbm7|Dbmaj7", "Fm7|Abmaj7", "Gbmaj7|Eb7sus4", "Dbmaj7|Cm7", "Bbm7|Dbmaj7", "Fm7|Abmaj7",
                        "Dbmaj7|Eb7sus4"],
             "break": ["Dbmaj7", "Cm7", "Bbm7", "Eb7sus4"], "outro": ["Dbmaj7|Cm7", "Bbm7|Eb7sus4", "Abmaj7", "Abmaj7"]}
    plan = K.Plan(120.2, 8, "major", form, progs, swing8=0.62)
    kit = {1: {"kick": "x.........x.....", "snare": "....r.......r...", "ride": "x.x.x.x.x.x.x.x."},
           2: {"kick": ["x.....x...x.....", "x.....x...x..x.."], "snare": ["....x.......x..g", "....x..g....x..."],
               "hat": ["xhxxxhxxxhxxxhxx", "xhxxxhxxxhxxxhxo"]},
           3: {"kick": ["x.....x.x.x.....", "x.....x...x..x.."], "snare": ["....X.......X..g", "....X..g....X.g."],
               "ride": "x.xbx.xhx.xbx.xh", "hat": "..p...p...p...p."}}
    drums = K.drums(plan, kit, rng)
    perc = K.percussion(plan, {3: {"shaker": "x.xxx.xxx.xxx.xx", "conga_hi": "......x.....x.x."}}, rng)
    bass, ghost = K.bass(plan, {1: "R.......5.......", 2: ["R..3.5..O..7.5.A", "R..5.O..7..5.3.A"],
                                3: ["R.R3.5.RO.75.3.A", "R..5.O.R7.O5.3.A"]}, lo=36, legato=0.8, rng=rng)
    guitar = K.comp(plan, {2: "..x...x...x...x.", 3: ["..x...x...x...x.", "..x...x...x.x.x."]}, lo=54, hi=80, size=3,
                    vel=74, short=0.18, rng=rng)
    piano = K.comp(plan, {1: "x-------x-------", 2: "x-----x-----x---", 3: ["x-----x-----x---", "x-----x---x-----"]},
                   lo=51, hi=80, vel=76, rng=rng)
    fmpad = K.pad(plan, (1, 2, 3), lo=58, hi=82, vel=64)
    strings = K.pad(plan, (3,), lo=65, hi=89, vel=60)
    phrases = {"verse": [". 3 4 5 . 3 2 1 | 2 - - - . . . . | . 3 4 5 . 6 5 3 | 5 - - - . . . .",
                         ". 3 4 5 . 3 2 1 | 2 - - - . 2 3 4 | 5 - 4 3 2 - 1 6, | 1 - - - . . . ."],
               "pre": "6 - 5 4 3 - 4 5 | 3 - 2 1 . . . . | 6 - 5 4 3 - 4 5 | 2' - - - 1' - - -",
               "chorus": ["1' - 6 5 6 - 1' - | 3' - 2' 1' 2' - . . | 1' - 6 5 6 - 3 - | 5 - - - . . . .",
                          "1' - 6 5 6 - 1' - | 3' - 2' 1' 2' - 3' 4' | 5' - 4' 3' 2' - 1' 6 | 1' - - - . . . ."]}
    lead_inst = "sfz:hollow" if variant == "A" else "sfz:weresax"
    lead = K.humanise(K.swing(K.lengthen(K.fit(_lead(plan, phrases, 60), plan), 0.26), plan), rng, 4)
    rev, boom = K.risers(plan)
    tracks = [T("Drums", "drums", "kit:band", drums), T("Percussion", "perc", "kit:latin", perc, pan=0.35),
              T("Bass", "bass", "sfz:bass_tight", bass),
              T("Guitar", "comp", "sfz:hollow", guitar, pan=0.5), T("Piano", "comp", "sfz:piano", piano, pan=-0.2),
              T("FM pad", "pad", "synth:fm_pad", fmpad), T("Strings", "pad", "sfz:violins", strings, pan=-0.15),
              T("Lead: " + ("guitar" if variant == "A" else "sax"), "lead", lead_inst, lead),
              T("Reverse crash", "fx", "sfx:reverse_crash", rev), T("Boom", "fx", "sfx:boom", boom)]
    if variant == "B":  # take B: Rhodes and a vibraphone answering instead of the FM pad
        tracks[4] = T("Rhodes", "comp", "sfz:rhodes", piano, pan=-0.2)
        tracks[5] = T("Vibraphone", "counter", "vibraphone",
                      K.arp(plan, {3: "..1.3...4.3...2.", 2: "....1.3.....4.3."}, lo=65, hi=86, vel=70, rng=rng), pan=0.25)
    cats = {"Drums": "drums", "Percussion": "drums", "Bass": "bass", "Guitar": "guitar", "Piano": "piano",
            "Rhodes": "piano", "Lead: guitar": "lead", "Lead: sax": "lead"}
    gains = {"Percussion": -6, "Reverse crash": -8, "Boom": -6}
    return plan, tracks, gains, cats


# ==================================================================================================
# Making the app songs
# ==================================================================================================

SONGS = {
    "hollow_hour": {"title": "Hollow Hour", "build": hollow_hour, "refs": ["burn-my-dread"], "pack": "persona_night",
                    "takes": {"A": "synth lead, sampled break, double-tracked guitars, acid synth",
                              "B": "violin lead, more piano"}},
    "paint_the_city": {"title": "Paint the City", "build": paint_the_city, "refs": ["color-your-night"],
                       "pack": "persona_city", "takes": {"A": "sax lead, grand piano, jazz organ",
                                                         "B": "synth lead with sax answers"}},
    "high_tide": {"title": "High Tide", "build": high_tide, "refs": ["full-moon-full-life"], "pack": "persona_city",
                  "takes": {"A": "synth lead, overdriven guitars throughout",
                            "B": "violin lead, clean guitar verses, overdrive in the chorus"}},
    "down_to_the_wire": {"title": "Down to the Wire", "build": down_to_the_wire, "refs": ["it-s-going-down-now"],
                         "pack": "persona_battle", "takes": {"A": "trumpet lead, horn section, rock guitars",
                                                             "B": "organ lead, horns, no guitars"}},
    "lunchbell": {"title": "Lunchbell", "build": lunchbell, "refs": ["school-days", "signs-of-love"], "pack": "persona_city",
                  "takes": {"A": "synth lead, synth bass, piano", "B": "guitar lead, finger bass, Rhodes"}},
    "reach_for_the_stars": {"title": "Reach for the Stars", "build": reach_for_the_stars,
                            "refs": ["when-the-moon-s-reaching-out-stars-reload"], "pack": "persona_city",
                            "takes": {"A": "guitar lead, piano, FM pad", "B": "sax lead, Rhodes, vibraphone"}},
    "safety_off": {"title": "Safety Off", "build": safety_off, "refs": ["pull-the-trigger", "a-way-of-life"],
                   "pack": "persona_city", "takes": {"A": "trumpet lead, grand piano, live kit",
                                                      "B": "tenor sax lead, Rhodes, sampled break kit"}},
}
# Group trims (dB) from the like-for-like check: the first takes, split into six stems and profiled exactly as their
# references were (2026-10-16), sat this far from the reference's levels (reference minus ours).
TRIMS = {"hollow_hour": {"drums": 1.8, "guitar": 1.8, "piano": -3.3},
         "paint_the_city": {"drums": 2.1, "bass": 1.6},
         "high_tide": {"drums": 2.0, "piano": 2.2},
         "down_to_the_wire": {"drums": 1.0, "piano": 2.5},
         "lunchbell": {"drums": 2.8, "bass": -4.0, "guitar": 2.0, "piano": -1.5},
         "reach_for_the_stars": {"drums": 1.0, "bass": 1.1, "guitar": 1.8, "piano": 6.7},
         "safety_off": {"bass": -1.0, "piano": 1.7}}
FEEL = {"intro": "intro", "verse": "verse", "pre": "pre", "chorus": "lift", "bridge": "breakdown", "break": "breakdown",
        "solo": "lift", "outro": "outro"}


def produce(song_id: str, variant: str, seed: int | None = None):
    """(song, gains, balance report) for one take, levels balanced against the references' stems."""
    spec = SONGS[song_id]
    plan, tracks, gains, cats = spec["build"](variant) if seed is None else spec["build"](variant, seed)
    tracks = [t for t in tracks if t.notes]
    song = build_song(spec["pack"], plan.bpm, plan.tonic, plan.mode,
                      [(s.name, s.start, s.bars) for s in plan.secs], plan.bars, tracks, seed=7)
    cats = {t.name: cats.get(t.name, "other") for t in tracks}
    gains, report = K.balance(song, gains, cats, K.target_levels(spec["refs"]))
    # the like-for-like trim: our first takes, split and profiled exactly as the reference was, sat this far off
    for name in gains:
        if not name.startswith("Lead"):
            gains[name] = round(gains[name] + TRIMS.get(song_id, {}).get(cats.get(name, "other"), 0.0), 2)
    report["trim"] = TRIMS.get(song_id, {})
    return plan, song, gains, report


def make(song_id: str, lib, variants=("A", "B")) -> tuple[str, list[int]]:
    """One app song with each take as a version (instrumental: no lyric sheet)."""
    from ..arrange import render
    from .production import add_version
    from .project import Project

    spec = SONGS[song_id]
    title = spec["title"]
    plan0 = spec["build"](variants[0])[0]
    p = Project.create("night_jazz", title)
    p.apply_lyrics(title + "\n" + "\n".join(f"[{s.name}, {s.bars} bars]" for s in plan0.secs))
    p.save()
    sid = p.build(lib)["song_id"]
    d = lib.song_dir(sid)
    out = []
    for v in variants:
        plan, song, gains, report = produce(song_id, v)
        record = json.loads((d / "song.json").read_text())
        base = {**record["versions"][0], "sections": [{"name": s.name, "start": s.start, "bars": s.bars} for s in plan.secs],
                "section_feels": [FEEL[s.kind] for s in plan.secs], "lyric_sheet": []}
        vi = add_version(d, song, gains, f"{title} · take {v}: {spec['takes'][v]}", base,
                         {"spec": {**base.get("spec", {}), "production": f"refsong:{song_id}:{v}"}, "balance": report},
                         tone_target=render.ref_bands(spec["refs"]), target_lufs=-11.0)
        out.append(vi)
    lib.update_song(sid, json.loads((d / "song.json").read_text()), out[-1])
    return sid, out
