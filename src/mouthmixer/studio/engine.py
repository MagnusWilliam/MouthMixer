"""A production engine for Persona-style songs from a lyric sheet (docs/PERSONA_PRODUCTION.md §5).

`last_train.py` was written bar by bar. This engine produces the same kind of arrangement for any song in the
songbook: a *style* says how each section feel (intro, verse, pre, lift = chorus, final, rap, breakdown,
outro) is played (drums, bass, comping, pads, percussion, brass, extra colours), a *song spec* gives the
chords per section, and the melody writer composes a guide melody to the words. Everything stays within the
rules learned so far: rootless voicings with a second inside, roots locked to the chord hits, chord tones
moved out of a half step's way of the melody, verses lean and choruses wide, a hook motif that comes back.
"""

from __future__ import annotations

import numpy as np

from ..arrange import lyrics as LY
from ..arrange.arranger import Track
from .production import bass_line, build_song, chord, clear_of, grid, humanise, n, swing, tones, upper

PACK_OF = {"citypop": "persona_city", "night_jazz": "persona_night", "battle_rush": "persona_battle",
           "bossa": "persona_bossa", "boss_choir": "persona_boss", "ballad": "persona_ballad", "dungeon": "persona_dungeon",
           "lost_car": "persona_night", "sad": "persona_ballad", "hideout": "persona_hideout", "results": "persona_city",
           "night_brushes": "persona_night", "night_trio": "persona_night", "night_lofi": "persona_hideout",
           "p3_urban": "persona_city", "p4_jpop": "persona_city", "p5_heavy": "persona_battle", "anthem": "persona_boss",
           "velvet": "persona_ballad", "chip_city": "persona_city", "chip_swing": "persona_night", "hope": "persona_boss"}

DRUM = {"kick": 36, "snare": 38, "side": 37, "hat": 42, "pedal": 44, "open": 46, "ride": 51, "bell": 53,
        "crash": 49, "crash2": 57, "t1": 50, "t2": 48, "t3": 45, "t4": 41}
PERC = {"bongo_hi": 60, "bongo_lo": 61, "conga_mute": 62, "conga_open": 63, "conga_low": 64, "tamb": 54,
        "tri_mute": 80, "tri_open": 81, "shaker": 82}

# --------------------------------------------------------------------------------------------------
# Styles
# --------------------------------------------------------------------------------------------------
# Per feel: drums (kick, snare, hats as 16-step strings, hat sound), bass style, comp rhythm, and which
# layers play. Rhythms: lists of (beat, length) within a bar.
RHYTHMS = {
    "stab": [(0.5, .25), (1.75, .5), (3.0, .25), (3.5, .25)],
    "push": [(0, 1.4), (1.5, .4), (2.5, 1.0)],
    "half": [(0, 1.9), (2, 1.9)],
    "whole": [(0, 3.9)],
    "offbeat": [(1.5, .25), (3.5, .25)],
    "charleston": [(0, .6), (1.5, .9)],
    "city": [(0, .4), (0.75, .4), (1.5, .4), (2.5, .4), (3.25, .5)],
    "bossa": [(0, .4), (0.75, .3), (1.5, .4), (2.25, .3), (3.0, .4)],
    "eighths": [(i * 0.5, 0.4) for i in range(8)],
    "ballad": [(0, 1.9), (2, 0.9), (3, 0.9)],
    "pulse": [(i * 1.0, 0.5) for i in range(4)],
}

STYLES: dict[str, dict] = {
    "citypop": {
        "title": "Persona city pop", "bpm": 112, "tonic": 7, "mode": "major",  # G major
        "kit": "kit:muldjord", "bass": "sfz:bass_finger", "comp": "sfz:rhodes", "pad": "sfz:violins",
        "lead_colour": "vibraphone", "guitar": "sfz:guitar_clean", "brass": True, "organ": None,
        "feels": {
            "intro": {"drums": ("x.......x.......", "....x.......x...", "x.x.x.x.x.x.x.x."), "bass": "lean", "comp": "city",
                      "layers": {"perc"}},
            "verse": {"drums": ("x.....x...x.....", "....x.......x...", "x.x.x.x.x.x.x.x."), "bass": "lean", "comp": "city",
                      "layers": {"perc"}},
            "pre": {"drums": ("x.......x.......", "....x.......x...", "xxxxxxxxxxxxxxxx"), "bass": "lean", "comp": "half",
                    "layers": {"perc", "pad"}},
            "lift": {"drums": ("x.....x.x.......", "....X.......X...", "xxxxxxoxxxxxxxox"), "bass": "push", "comp": "city",
                     "layers": {"perc", "pad", "guitar", "brass", "congas"}},
            "final": {"drums": ("x.....x.x.......", "....X.......X...", "xxxxxxoxxxxxxxox"), "bass": "push", "comp": "city",
                      "layers": {"perc", "pad", "guitar", "brass", "congas", "lead_colour"}},
            "breakdown": {"drums": None, "bass": "pedal", "comp": "whole", "layers": {"pad"}},
            "outro": {"drums": ("x.......x.......", "....x.......x...", "x.x.x.x.x.x.x.x."), "bass": "lean", "comp": "city",
                      "layers": {"perc", "lead_colour"}},
        },
    },
    "night_jazz": {
        "transitions": False,
        "title": "Persona night jazz", "bpm": 86, "tonic": 9, "mode": "minor", "swing": 0.62,  # A minor
        "kit": "kit:muldjord", "bass": "sfz:bass_finger", "comp": "sfz:rhodes", "pad": "sfz:violins",
        "lead_colour": "sfz:tenor_sax", "guitar": None, "brass": False, "organ": "synth:organ_soft",
        "ride": True,
        "feels": {
            "intro": {"drums": ("x...............", "............x...", "x..xx..xx..xx..x"), "bass": "pedal", "comp": "charleston",
                      "layers": {"lead_colour"}},
            "verse": {"drums": ("x.........x.....", "........g...x...", "x..xx..xx..xx..x"), "bass": "lean", "comp": "charleston",
                      "layers": {"answers"}},
            "lift": {"drums": ("x.....x...x.....", "....x.......x...", "x..xx..xx..xx..x"), "bass": "lean", "comp": "half",
                     "layers": {"pad", "organ", "answers"}},
            "final": {"drums": ("x.....x...x.....", "....x.......x...", "x..xx..xx..xx..x"), "bass": "lean", "comp": "half",
                      "layers": {"pad", "organ", "answers"}},
            "outro": {"drums": ("x...............", "............x...", "x..xx..xx..xx..x"), "bass": "pedal", "comp": "whole",
                      "layers": {"lead_colour"}},
        },
    },
    "battle_rush": {
        "title": "Persona battle rush", "bpm": 158, "tonic": 4, "mode": "minor",  # E minor
        "kit": "kit:muldjord", "bass": "sfz:bass_finger", "comp": "sfz:rhodes", "pad": "sfz:violins",
        "lead_colour": "synth:saw_lead", "guitar": "sfz:guitar_clean", "brass": True, "organ": "synth:organ_rock",
        "feels": {
            "intro": {"drums": ("x.x...x.x.x...x.", "....X.......X...", "x.x.x.x.x.x.x.x."), "bass": "funk", "comp": "stab",
                      "layers": {"brass", "organ", "guitar"}},
            "lift": {"drums": ("x.x...x.x.x...x.", "....X.......X...", "x.x.x.x.x.x.x.x."), "bass": "funk", "comp": "stab",
                     "layers": {"brass", "organ", "guitar", "pad", "congas"}},
            "final": {"drums": ("x.x...x.x.x...x.", "....X.......X...", "x.x.x.x.x.x.x.x."), "bass": "funk", "comp": "stab",
                      "layers": {"brass", "organ", "guitar", "pad", "congas", "lead_colour"}},
            "rap": {"drums": ("x......xx.x.....", "........X.......", "x.x.x.x.x.x.x.x."), "bass": "halftime", "comp": "offbeat",
                    "layers": {"guitar"}},
            "pre": {"drums": ("x...x...x...x...", "....x.......x...", "xxxxxxxxxxxxxxxx"), "bass": "funk", "comp": "half",
                    "layers": {"pad", "organ"}},
            "hits_end": {"drums": ("x.x...x.x.x...x.", "....X.......X...", "x.x.x.x.x.x.x.x."), "bass": "funk", "comp": "stab",
                         "layers": {"brass", "organ"}},
        },
    },
    "bossa": {
        "transitions": False,
        "title": "Persona rain bossa", "bpm": 132, "tonic": 2, "mode": "major",  # D major
        "kit": "kit:muldjord", "bass": "sfz:bass_finger", "comp": "nylon_guitar", "pad": "sfz:violins",
        "lead_colour": "flute", "guitar": None, "brass": False, "organ": None, "rim": True,
        "feels": {
            "intro": {"drums": ("x..x....x..x....", "..x..x....x..x..", "x.x.x.x.x.x.x.x."), "bass": "bossa", "comp": "bossa",
                      "layers": {"perc", "lead_colour"}},
            "verse": {"drums": ("x..x....x..x....", "..x..x....x..x..", "x.x.x.x.x.x.x.x."), "bass": "bossa", "comp": "bossa",
                      "layers": {"perc", "rhodes_pad"}},
            "lift": {"drums": ("x..x....x..x....", "..x..x....x..x..", "x.x.x.x.x.x.x.x."), "bass": "bossa", "comp": "bossa",
                     "layers": {"perc", "pad", "rhodes_pad", "lead_colour"}},
            "final": {"drums": ("x..x....x..x....", "..x..x....x..x..", "x.x.x.x.x.x.x.x."), "bass": "bossa", "comp": "bossa",
                      "layers": {"perc", "pad", "rhodes_pad", "lead_colour"}},
            "outro": {"drums": ("x..x....x..x....", "..x..x....x..x..", "x.x.x.x.x.x.x.x."), "bass": "bossa", "comp": "bossa",
                      "layers": {"perc", "lead_colour"}},
        },
    },
    "boss_choir": {
        "title": "Persona boss orchestra", "bpm": 150, "tonic": 0, "mode": "minor",  # C minor
        "kit": "kit:muldjord", "bass": "sfz:bass_finger", "comp": "sfz:piano", "pad": "sfz:violins",
        "lead_colour": "choir", "guitar": "sfz:guitar_clean", "brass": True, "organ": "synth:organ_rock",
        "ostinato": True,
        "feels": {
            "intro": {"drums": None, "bass": "pedal", "comp": "whole", "layers": {"ostinato", "choir"}},
            "verse": {"drums": ("x.....x...x.....", "....x.......x...", "x.x.x.x.x.x.x.x."), "bass": "eighths", "comp": "half",
                      "layers": {"ostinato", "low_strings"}},
            "pre": {"drums": ("x...x...x...x...", "....x.......x...", "xxxxxxxxxxxxxxxx"), "bass": "eighths", "comp": "half",
                    "layers": {"ostinato", "low_strings", "pad", "timpani"}},
            "lift": {"drums": ("x.x...x.x.x...x.", "....X.......X...", "x.x.x.x.x.x.x.x."), "bass": "eighths", "comp": "half",
                     "layers": {"ostinato", "low_strings", "pad", "choir", "brass", "organ", "timpani", "guitar"}},
            "final": {"drums": ("x.x...x.x.x...x.", "....X.......X...", "x.x.x.x.x.x.x.x."), "bass": "eighths", "comp": "half",
                      "layers": {"ostinato", "low_strings", "pad", "choir", "brass", "organ", "timpani", "guitar"}},
            "breakdown": {"drums": None, "bass": "pedal", "comp": "ballad", "layers": {"choir", "pad"}},
            "hits_end": {"drums": ("x.x...x.x.x...x.", "....X.......X...", "x.x.x.x.x.x.x.x."), "bass": "eighths", "comp": "half",
                         "layers": {"ostinato", "brass", "choir", "timpani"}},
        },
    },
    "ballad": {
        "transitions": False,
        "title": "Persona ending ballad", "bpm": 76, "tonic": 5, "mode": "major",  # F major
        "kit": "kit:muldjord", "bass": "sfz:bass_finger", "comp": "sfz:piano", "pad": "sfz:violins",
        "lead_colour": "sfz:harp", "guitar": None, "brass": False, "organ": None,
        "feels": {
            "intro": {"drums": None, "bass": None, "comp": "ballad", "layers": {"motif"}},
            "verse": {"drums": None, "bass": "pedal", "comp": "ballad", "layers": set()},
            "pre": {"drums": ("x.......x.......", "....x.......x...", "x.x.x.x.x.x.x.x."), "bass": "lean", "comp": "ballad",
                    "layers": {"pad", "low_strings"}},
            "lift": {"drums": ("x.......x.x.....", "....x.......x...", "x.x.x.x.x.x.x.x."), "bass": "lean", "comp": "ballad",
                     "layers": {"pad", "low_strings", "lead_colour"}},
            "final": {"drums": ("x.......x.x.....", "....X.......X...", "x.x.x.x.x.x.x.o."), "bass": "lean", "comp": "ballad",
                      "layers": {"pad", "low_strings", "lead_colour", "choir"}},
            "outro": {"drums": None, "bass": "pedal", "comp": "whole", "layers": {"motif"}},
        },
    },
    "dungeon": {
        "transitions": False,
        "title": "Persona labyrinth pulse", "bpm": 120, "tonic": 6, "mode": "minor",  # F# minor
        "kit": "kit:muldjord", "bass": "synth:sub_bass", "comp": "synth:pluck", "pad": "synth:super_pad",
        "lead_colour": "sfz:violins_pizz", "guitar": None, "brass": False, "organ": None,
        "feels": {
            "intro": {"drums": None, "bass": "pulse", "comp": "whole", "layers": {"pad"}},
            "verse": {"drums": ("x.........x.....", "........x.......", "..x...x...x...x."), "bass": "pulse", "comp": "eighths",
                      "layers": {"pad", "lead_colour"}},
            "breakdown": {"drums": None, "bass": "pulse", "comp": "whole", "layers": {"pad"}},
            "outro": {"drums": None, "bass": "pulse", "comp": "whole", "layers": {"pad"}},
        },
    },
}
# Wrong Side of Midnight, softer (the user found the night-jazz drums overpowering): three alternatives.
STYLES["night_brushes"] = dict(STYLES["night_jazz"]) | {
    "title": "night jazz, brushes", "kit": "kit:brush", "bass": "acoustic_bass", "comp": "sfz:piano", "drum_gain": -7,
    "feels": {k: dict(v, bass="walk" if v["bass"] == "lean" else v["bass"]) for k, v in STYLES["night_jazz"]["feels"].items()},
}
STYLES["night_trio"] = dict(STYLES["night_jazz"]) | {
    "title": "night jazz, piano trio", "bass": "acoustic_bass", "comp": "sfz:piano", "organ": None,
    "feels": {k: dict(v, drums=None, bass="walk" if v["bass"] == "lean" else v["bass"],
                      layers=set(v["layers"]) - {"organ"}) for k, v in STYLES["night_jazz"]["feels"].items()},
}
STYLES["night_lofi"] = dict(STYLES["night_jazz"]) | {
    "title": "night jazz, lo-fi", "bpm": 80, "swing": 0.58, "comp": "sfz:rhodes", "lead_colour": "vibraphone",
    "drum_gain": -9, "organ": None,
    "feels": {k: dict(v, drums=("x......x..x.....", "....x.......x...", "x.x.x.x.x.x.x.x.") if v["drums"] else None,
                      layers=set(v["layers"]) - {"organ"}) for k, v in STYLES["night_jazz"]["feels"].items()},
}

# Distinct Persona sounds (the user: "more unique, more distinct Persona sounds"; PERSONA_PRODUCTION §7).
STYLES["p3_urban"] = {  # Persona 3 (Reload): boom-bap breaks, piano loop, string stabs, record scratches
    "title": "Persona 3 urban", "bpm": 96, "tonic": 11, "mode": "minor", "swing": 0.56,  # B minor
    "kit": "kit:muldjord", "bass": "sfz:bass_finger", "comp": "sfz:piano", "pad": "sfz:violins",
    "lead_colour": "sfz:violins_spic", "guitar": None, "brass": False, "organ": None,
    "feels": {
        "intro": {"drums": None, "bass": None, "comp": "stab", "layers": {"scratch"}},
        "verse": {"drums": ("x......xx.x.....", "....x.......x...", "x.x.x.x.x.x.x.x."), "bass": "halftime", "comp": "stab",
                  "layers": {"scratch"}},
        "pre": {"drums": ("x......xx.x.....", "....x.......x...", "xxxxxxxxxxxxxxxx"), "bass": "halftime", "comp": "half",
                "layers": {"pad"}},
        "lift": {"drums": ("x......xx.x...x.", "....x.......x...", "x.x.x.x.x.x.x.x."), "bass": "lean", "comp": "push",
                 "layers": {"pad", "low_strings", "scratch", "lead_colour"}},
        "breakdown": {"drums": None, "bass": "pedal", "comp": "whole", "layers": {"pad"}},
        "outro": {"drums": ("x......xx.x.....", "....x.......x...", "x.x.x.x.x.x.x.x."), "bass": "halftime", "comp": "stab",
                  "layers": {"scratch"}},
    },
}
STYLES["p4_jpop"] = {  # Persona 4: bright J-pop rock: piano 8ths, crunchy guitar, synth strings, disco hats
    "title": "Persona 4 J-pop rock", "bpm": 120, "tonic": 4, "mode": "major",  # E major
    "kit": "kit:muldjord", "bass": "sfz:bass_finger", "comp": "sfz:piano", "pad": "synth:super_pad",
    "lead_colour": "synth:saw_lead", "guitar": "sfz:guitar_clean", "brass": False, "organ": None,
    "feels": {
        "intro": {"drums": ("x.......x.......", "....x.......x...", "x.x.x.x.x.x.x.x."), "bass": "eighths", "comp": "eighths",
                  "layers": {"power", "lead_colour"}},
        "verse": {"drums": ("x.......x.x.....", "....x.......x...", "x.x.x.x.x.x.x.x."), "bass": "eighths", "comp": "half",
                  "layers": {"guitar"}},
        "pre": {"drums": ("x...x...x...x...", "....x.......x...", "x.x.x.x.x.x.x.x."), "bass": "eighths", "comp": "eighths",
                "layers": {"pad", "guitar"}},
        "lift": {"drums": ("x...x...x...x...", "....X.......X...", "..x...x...x...x."), "bass": "eighths", "comp": "eighths",
                 "layers": {"pad", "power", "low_strings"}},
        "final": {"drums": ("x...x...x...x...", "....X.......X...", "..x...x...x...x."), "bass": "eighths", "comp": "eighths",
                  "layers": {"pad", "power", "low_strings", "lead_colour"}},
        "breakdown": {"drums": None, "bass": "pedal", "comp": "half", "layers": {"pad"}},
    },
}
STYLES["p5_heavy"] = {  # Persona 5 boss/battle rock: organ, distorted guitar, brass, driving 16ths
    "title": "Persona 5 battle rock", "bpm": 166, "tonic": 7, "mode": "minor",  # G minor
    "kit": "kit:muldjord", "bass": "sfz:bass_finger", "comp": "sfz:rhodes", "pad": "sfz:violins",
    "lead_colour": "sfz:trumpet", "guitar": "sfz:guitar_clean", "brass": True, "organ": "synth:organ_rock",
    "feels": {
        "intro": {"drums": ("x.x...x.x.x...x.", "....X.......X...", "x.x.x.x.x.x.x.x."), "bass": "funk", "comp": "stab",
                  "layers": {"brass", "organ", "power"}},
        "verse": {"drums": ("x.x...x...x...x.", "....X.......X...", "x.x.x.x.x.x.x.x."), "bass": "funk", "comp": "stab",
                  "layers": {"organ"}},
        "rap": {"drums": ("x......xx.x.....", "........X.......", "x.x.x.x.x.x.x.x."), "bass": "halftime", "comp": "offbeat",
                "layers": {"guitar"}},
        "pre": {"drums": ("x...x...x...x...", "....x.......x...", "xxxxxxxxxxxxxxxx"), "bass": "funk", "comp": "half",
                "layers": {"pad", "organ", "power"}},
        "lift": {"drums": ("x.x...x.x.x...x.", "....X.......X...", "xxxxxxoxxxxxxxox"), "bass": "funk", "comp": "stab",
                 "layers": {"brass", "organ", "power", "pad", "congas"}},
        "final": {"drums": ("x.x...x.x.x...x.", "....X.......X...", "xxxxxxoxxxxxxxox"), "bass": "funk", "comp": "stab",
                  "layers": {"brass", "organ", "power", "pad", "congas", "lead_colour"}},
    },
}
STYLES["anthem"] = {  # the departure-day anthem: rock band, organ, strings and a gang/choir on the hook
    "title": "Persona anthem", "bpm": 140, "tonic": 9, "mode": "minor",  # A minor
    "kit": "kit:muldjord", "bass": "sfz:bass_finger", "comp": "sfz:piano", "pad": "sfz:violins",
    "lead_colour": "choir", "guitar": "sfz:guitar_clean", "brass": True, "organ": "synth:organ_rock",
    "feels": {
        "intro": {"drums": ("x.......x.......", "....X.......X...", "x.x.x.x.x.x.x.x."), "bass": "eighths", "comp": "half",
                  "layers": {"organ", "power"}},
        "verse": {"drums": ("x.....x.x.......", "....x.......x...", "x.x.x.x.x.x.x.x."), "bass": "push", "comp": "stab",
                  "layers": {"guitar"}},
        "pre": {"drums": ("x...x...x...x...", "....x.......x...", "xxxxxxxxxxxxxxxx"), "bass": "eighths", "comp": "half",
                "layers": {"pad", "organ"}},
        "lift": {"drums": ("x.....x.x.x.....", "....X.......X...", "xxxxxxoxxxxxxxox"), "bass": "eighths", "comp": "half",
                 "layers": {"pad", "organ", "power", "choir", "brass", "low_strings"}},
        "final": {"drums": ("x.....x.x.x.....", "....X.......X...", "xxxxxxoxxxxxxxox"), "bass": "eighths", "comp": "half",
                  "layers": {"pad", "organ", "power", "choir", "brass", "low_strings", "timpani"}},
        "breakdown": {"drums": None, "bass": "pedal", "comp": "ballad", "layers": {"pad", "choir"}},
    },
}
STYLES["velvet"] = {  # the Velvet Room idea: piano arpeggios, organ, a wordless soprano (here: the Hum)
    "title": "Velvet piano and soprano", "bpm": 80, "tonic": 1, "mode": "minor", "transitions": False,  # C# minor
    "arp_range": (64, 83),
    "kit": "kit:muldjord", "bass": None, "comp": "sfz:piano", "pad": "sfz:violins",
    "lead_colour": "sfz:harp", "guitar": None, "brass": False, "organ": "synth:organ_soft",
    "feels": {
        "intro": {"drums": None, "bass": None, "comp": "arp", "layers": set()},
        "verse": {"drums": None, "bass": None, "comp": "arp", "layers": {"pad"}},
        "lift": {"drums": None, "bass": None, "comp": "arp", "layers": {"pad", "low_strings"}},
    },
}
# Undertale-inspired (Toby Fox research, PERSONA_PRODUCTION §8): chip voices over a real groove, motifs reused.
STYLES["chip_city"] = {  # Stop 3 AFTER HOURS: chiptune and city pop (Soren's song in chip)
    "title": "chip city pop", "bpm": 128, "tonic": 5, "mode": "major",  # F major
    "kit": "kit:muldjord", "bass": "synth:chip_triangle", "comp": "sfz:rhodes", "pad": "synth:super_pad",
    "lead_colour": "synth:chip_square", "guitar": None, "brass": False, "organ": None,
    "feels": {
        "intro": {"drums": None, "bass": "lean", "comp": "city", "layers": set()},
        "verse": {"drums": ("x.....x...x.....", "....x.......x...", "x.x.x.x.x.x.x.x."), "bass": "funk", "comp": "city",
                  "layers": {"chipkit"}},
        "lift": {"drums": ("x.....x.x.......", "....X.......X...", "xxxxxxoxxxxxxxox"), "bass": "funk", "comp": "city",
                 "layers": {"chipkit", "pad"}},
    },
}
STYLES["chip_swing"] = {  # a swung shop/menu tune: walking bass, Rhodes, the melody on square + vibraphone
    "title": "chip swing", "bpm": 102, "tonic": 10, "mode": "major", "swing": 0.64, "transitions": False,  # Bb
    "kit": "kit:brush", "bass": "acoustic_bass", "comp": "sfz:rhodes", "pad": "sfz:violins",
    "lead_colour": "vibraphone", "guitar": None, "brass": False, "organ": None, "ride": True,
    "feels": {
        "verse": {"drums": ("x.......x.......", "....x.......x...", "x..xx..xx..xx..x"), "bass": "walk", "comp": "charleston",
                  "layers": set()},
        "lift": {"drums": ("x.......x.......", "....x.......x...", "x..xx..xx..xx..x"), "bass": "walk", "comp": "charleston",
                 "layers": {"chipkit"}},
    },
}
STYLES["hope"] = {  # the finale: band + chip lead, earlier motifs stacked as melody and countermelody
    "title": "hope finale", "bpm": 140, "tonic": 0, "mode": "major",  # C major
    "kit": "kit:muldjord", "bass": "sfz:bass_finger", "comp": "sfz:piano", "pad": "sfz:violins",
    "lead_colour": "synth:chip_square", "guitar": "sfz:guitar_clean", "brass": True, "organ": "synth:organ_gospel",
    "feels": {
        "intro": {"drums": None, "bass": None, "comp": "arp", "layers": set()},
        "verse": {"drums": ("x.......x.x.....", "....x.......x...", "x.x.x.x.x.x.x.x."), "bass": "push", "comp": "push",
                  "layers": {"pad", "chipkit"}},
        "lift": {"drums": ("x.....x.x.x.....", "....X.......X...", "xxxxxxoxxxxxxxox"), "bass": "push", "comp": "push",
                 "layers": {"pad", "low_strings", "organ", "power", "brass", "timpani", "chipkit"}},
    },
}

# Instrumental cues for LINE ZERO's scenes (studio/cues.py; AUDIO_PLAN section 3.2).
STYLES["lost_car"] = {
    "transitions": False,
    "title": "LINE ZERO Lost Car", "bpm": 72, "tonic": 2, "mode": "minor", "swing": 0.6,  # D minor, slow swing
    "kit": "kit:brush", "bass": "acoustic_bass", "comp": "sfz:rhodes", "pad": "sfz:violins",
    "lead_colour": "celesta", "guitar": None, "brass": False, "organ": None, "ride": True,
    "feels": {
        "intro": {"drums": None, "bass": "pedal", "comp": "whole", "layers": {"clock"}},
        "verse": {"drums": ("x.........x.....", "............g...", "x..xx..xx..xx..x"), "bass": "lean",
                  "comp": "charleston", "layers": {"clock"}},
        "lift": {"drums": ("x.........x.....", "....g.......x...", "x..xx..xx..xx..x"), "bass": "lean", "comp": "half",
                 "layers": {"clock", "pad", "low_strings"}},
        "outro": {"drums": None, "bass": "pedal", "comp": "whole", "layers": {"clock"}},
    },
}
STYLES["sad"] = {
    "transitions": False,
    "title": "LINE ZERO sad", "bpm": 66, "tonic": 2, "mode": "minor",
    "kit": "kit:muldjord", "bass": None, "comp": "sfz:piano", "pad": "sfz:violins",
    "lead_colour": "sfz:cellos", "guitar": None, "brass": False, "organ": None,
    "feels": {
        "intro": {"drums": None, "bass": None, "comp": "ballad", "layers": set()},
        "verse": {"drums": None, "bass": None, "comp": "ballad", "layers": set()},
        "lift": {"drums": None, "bass": None, "comp": "ballad", "layers": {"pad"}},
        "outro": {"drums": None, "bass": None, "comp": "whole", "layers": set()},
    },
}
STYLES["hideout"] = {
    "transitions": False,
    "title": "LINE ZERO hideout", "bpm": 90, "tonic": 5, "mode": "major", "swing": 0.56,  # F major, lo-fi
    "kit": "kit:muldjord", "bass": "sfz:bass_finger", "comp": "sfz:rhodes", "pad": "sfz:violins",
    "lead_colour": "vibraphone", "guitar": None, "brass": False, "organ": None,
    "feels": {
        "intro": {"drums": None, "bass": None, "comp": "whole", "layers": set()},
        "verse": {"drums": ("x......xx.x.....", "....x.......x...", "x.x.x.x.x.x.x.x."), "bass": "lean", "comp": "stab",
                  "layers": set()},
        "lift": {"drums": ("x......xx.x.....", "....x.......x...", "x.x.x.x.x.x.x.x."), "bass": "lean", "comp": "half",
                 "layers": {"pad"}},
        "outro": {"drums": None, "bass": "pedal", "comp": "whole", "layers": set()},
    },
}
STYLES["results"] = {
    "title": "LINE ZERO results", "bpm": 100, "tonic": 5, "mode": "major",  # F major, light funk
    "kit": "kit:muldjord", "bass": "sfz:bass_finger", "comp": "sfz:rhodes", "pad": "sfz:violins",
    "lead_colour": "sfz:trumpet_harmon", "guitar": "sfz:guitar_clean", "brass": True, "organ": None,
    "feels": {
        "verse": {"drums": ("x.....x...x.....", "....x.......x...", "xxxxxxoxxxxxxxox"), "bass": "funk", "comp": "city",
                  "layers": {"guitar", "perc"}},
        "lift": {"drums": ("x.....x.x.......", "....X.......X...", "xxxxxxoxxxxxxxox"), "bass": "funk", "comp": "city",
                 "layers": {"guitar", "perc", "congas", "brass"}},
        "sting": {"drums": ("x...............", "................", "................"), "bass": "pedal", "comp": "whole",
                  "layers": set()},
    },
}

# Feels a style doesn't spell out borrow from the nearest one.
FALLBACK_FEEL = {"lift": "verse", "final": "lift", "pre": "verse", "rap": "verse", "breakdown": "verse",
                 "outro": "intro", "hits_end": "final", "intro": "verse", "verse": "lift", "build": "pre"}


def feel_spec(style: dict, feel: str) -> dict:
    seen = set()
    while feel not in style["feels"] and feel not in seen:
        seen.add(feel)
        feel = FALLBACK_FEEL.get(feel, "verse")
    return style["feels"].get(feel) or next(iter(style["feels"].values()))


# --------------------------------------------------------------------------------------------------
# The guide melody writer
# --------------------------------------------------------------------------------------------------

def scale_pcs(tonic: int, mode: str) -> list[int]:
    steps = [0, 2, 4, 5, 7, 9, 11] if mode == "major" else [0, 2, 3, 5, 7, 8, 10]
    return [(tonic + s) % 12 for s in steps]


REGISTER = {"verse": (57, 64), "pre": (60, 66), "lift": (62, 67), "final": (62, 67), "breakdown": (60, 65),
            "intro": (57, 64), "outro": (57, 64)}  # (centre, peak) for a low male voice, A3-G4


def line_rhythm(syl: list[dict], span: float, pickup: bool, dense_ok: bool) -> list[tuple[float, float]]:
    """Onsets and lengths for one sung line within `span` beats: stressed syllables on beats where they fit,
    8ths otherwise (16ths for long lines), the last syllable held, half a beat to breathe before the next."""
    k = len(syl)
    if k == 0:
        return []
    avail = span - 0.5
    start = 0.5 if pickup else 0.0
    last_len = min(2.0, max(1.0, avail - start - (k - 1) * 0.5))
    room = avail - start - last_len
    step = 0.5 if (k - 1) * 0.5 <= room else 0.25 if dense_ok else room / max(1, k - 1)
    onsets, t = [], start
    for i, s in enumerate(syl[:-1]):
        onsets.append(t)
        nxt_stress = syl[i + 1]["stress"] == 1
        # give a stressed syllable that would fall off the beat the extra 8th to land on it, if there's room
        spare = room - (t - start) - step * (k - 1 - i)
        t += step
        if nxt_stress and (t % 1) and spare >= step + 0.5 and step == 0.5:
            t += 0.5
    onsets.append(t)
    out = []
    for i, o in enumerate(onsets):
        end = onsets[i + 1] if i + 1 < len(onsets) else min(avail, o + last_len)
        out.append((o, max(0.2, end - o - 0.05)))
    return out


def write_melody(sheet: list[dict], chord_at, tonic: int, mode: str, feels: dict[str, str], rng,
                 lo: int = 57, hi: int = 67) -> list:
    """Guide melody for every sung line in the lyric sheet (rap, spoken and whispered sections stay free).
    Pitches by beam search: chord tones on strong beats, scale steps between, an arch per line, open endings
    on odd lines and the tonic or third on even ones, repeated lines sung the same way."""
    pcs = scale_pcs(tonic, mode)
    notes_in = [p for p in range(lo, hi + 1) if p % 12 in pcs]
    memo: dict[str, list] = {}
    out = []
    for sec in sheet:
        if sec.get("mode", "sung") != "sung" or not sec.get("lines"):
            continue
        feel = feels.get(sec["section"], "verse")
        centre, peak = REGISTER.get(feel, (60, 66))
        span = sec["beats"] / max(1, len(sec["lines"]))
        prev_last = None
        for li, text in enumerate(sec["lines"]):
            start = sec["start"] + li * span
            key = " ".join(text.lower().split())
            if key in memo:  # the same words: the same tune (hooks)
                rel = memo[key]
                out += [(start + o, l, p, v) for o, l, p, v in rel]
                prev_last = rel[-1][2] if rel else prev_last
                continue
            syl = LY.line_syllables(text.replace("…", " ").replace("...", " "))
            syl = [s for s in syl if s["text"].strip(",.!?;:—-")]
            if not syl:
                continue
            rhythm = line_rhythm(syl, span, pickup=feel in ("verse", "pre", "breakdown") and li % 2 == 0,
                                 dense_ok=len(syl) > 10)
            closed = li % 2 == 1
            lift = (li / max(1, len(sec["lines"]) - 1)) * (2 if feel == "pre" else 0)

            def target(i):
                x = i / max(1, len(rhythm) - 1)
                return centre + lift + (peak - centre) * np.sin(np.pi * min(1.0, x * 1.1))

            beams = [(0.0, [])]
            for i, (o, l) in enumerate(rhythm):
                t = start + o
                ch = tones(chord_at(t))
                strong = abs(o - round(o)) < 1e-6 or l >= 1.0
                last = i == len(rhythm) - 1
                cand = []
                for cost, seq in beams:
                    prev = seq[-1] if seq else (prev_last if prev_last else centre)
                    for p in notes_in:
                        c = 0.0
                        step = abs(p - prev)
                        c += {0: 0.6, 1: 0.0, 2: 0.0, 3: 0.6, 4: 0.9, 5: 1.4, 7: 2.0}.get(step, 3.0 + step * 0.2)
                        if len(seq) >= 2 and abs(seq[-1] - seq[-2]) > 4 and step > 2:
                            c += 1.5  # leap after leap
                        if strong and p % 12 not in ch:
                            c += 3.0
                        if not strong and p % 12 not in ch and p % 12 not in pcs:
                            c += 5.0
                        c += 0.25 * abs(p - target(i))
                        if last:
                            if closed and p % 12 not in {tonic, (tonic + (3 if mode == "minor" else 4)) % 12}:
                                c += 2.5
                            if not closed and p % 12 == tonic:
                                c += 1.5
                            if p % 12 not in ch:
                                c += 4.0
                        if len(seq) >= 2 and seq[-1] == seq[-2] == p:
                            c += 1.2
                        cand.append((cost + c + rng.random() * 0.05, seq + [p]))
                cand.sort(key=lambda x: x[0])
                beams = cand[:12]
            pitches = beams[0][1]
            rel = [(o, l, p, 92 + (8 if s["stress"] == 1 else 0)) for (o, l), p, s in zip(rhythm, pitches, syl)]
            memo[key] = rel
            out += [(start + o, l, p, v) for o, l, p, v in rel]
            prev_last = pitches[-1]
    return out


# --------------------------------------------------------------------------------------------------
# The band
# --------------------------------------------------------------------------------------------------

def produce(spec: dict, version: dict, seed: int = 11) -> tuple:
    """(Song, gains) for a songbook song. `spec`: {"style", "chords": {section name or feel: [chords per bar]},
    "bpm"/"tonic"/"mode" overrides, "hook": [(beat, len, note)...] the motif, "hits": [words]}. `version`: the
    built song's version (sections, section_feels, lyric_sheet)."""
    rng = np.random.default_rng(seed)
    style = STYLES[spec["style"]]
    bpm = spec.get("bpm", style["bpm"])
    tonic, mode = spec.get("tonic", style["tonic"]), spec.get("mode", style["mode"])
    secs = [(s["name"], s["start"], s["bars"]) for s in version["sections"]]
    feels = dict(zip([s["name"] for s in version["sections"]], version.get("section_feels") or ["verse"] * len(secs)))
    feels = {k: ("lift" if v in ("chorus", "lift") else v) for k, v in feels.items()}
    feels.update(spec.get("feels", {}))  # instrumental cues name their own feels (a sting, a lift...)
    for nm_ in feels:  # an instrumental solo (added to make a song long enough): the whole band
        if nm_.lower().startswith("solo"):
            feels[nm_] = "final"
    bars: list[str] = []
    for name, start, length in secs:
        kind = _kind(name, feels[name])
        prog = (spec["chords"].get(name) or spec["chords"].get(kind)
                or spec["chords"].get({"final": "chorus", "pre": "verse"}.get(kind, ""))  # a final chorus is a chorus
                or spec["chords"].get("verse") or next(iter(spec["chords"].values())))
        bars += [prog[i % len(prog)] for i in range(length)]
    total_bars = len(bars)

    def chord_at(beat: float) -> str:
        b = min(int(beat // 4), total_bars - 1)
        parts = bars[b].split("|")
        return parts[min(len(parts) - 1, int((beat % 4) / (4 / len(parts))))]

    sheet = version.get("lyric_sheet") or []
    mel = write_melody(sheet, chord_at, tonic, mode, feels, rng)
    clear = lambda notes: clear_of(notes, mel, chord_at)  # noqa: E731
    parts: dict[str, list] = {k: [] for k in ("drums", "perc", "bass", "ghost", "comp", "pad", "low", "brass_hi", "brass_lo",
                                              "guitar_l", "guitar_r", "organ", "colour", "choir", "ostinato", "timpani",
                                              "rim", "fx_rev", "fx_boom", "perc_gm", "theme", "theme2",
                                              "power", "scratch", "chip")}
    prev_v = None
    for si, (name, start, length) in enumerate(secs):
        fs = feel_spec(style, feels[name])
        b0, b1 = start, start + length
        sec_bars = bars[b0:b1]
        nxt_feel = feels[secs[si + 1][0]] if si + 1 < len(secs) else None
        big_next = nxt_feel in ("lift", "final")
        # drums
        if fs["drums"]:
            k, s, h = fs["drums"]
            for i in range(length):
                b = (b0 + i) * 4
                last = i == length - 1
                parts["drums"] += grid(k, b, DRUM["kick"], 104)
                parts["drums"] += grid(s, b, DRUM["snare"], 100 if not style.get("rim") else 55)
                hat_note = DRUM["ride"] if style.get("ride") else DRUM["hat"]
                parts["drums"] += grid(h, b, lambda c: DRUM["open"] if c == "o" else hat_note, 74, length=0.1)
                if i == 0 and feels[name] in ("lift", "final", "intro"):
                    parts["drums"].append((b, 1.5, DRUM["crash"], 110))
                if last and big_next:  # a fill into the chorus
                    for j, t in enumerate(["t1", "t1", "t2", "t3"]):
                        parts["drums"].append((b + 3 + j * 0.25, 0.2, DRUM[t], 96 + j * 6))
                elif i % 4 == 3 and not last and feels[name] in ("lift", "final"):
                    for j in range(4):
                        parts["drums"].append((b + 3 + j * 0.25, 0.2, DRUM["snare"], 66 + j * 12))
            if style.get("rim"):
                parts["rim"] += [x for i in range(length) for x in grid("x..x..x...x..x..", (b0 + i) * 4, 37, 80)]
        # bass
        if fs["bass"]:
            bstyle = fs["bass"]
            if bstyle == "walk":  # quarter notes: root, chord tones, a chromatic step into the next root
                for i, nm in enumerate(sec_bars):
                    b = (b0 + i) * 4
                    cur = nm.split("|")[0]
                    root, ints, _, _ = chord(cur)
                    nxt = bars[min(b0 + i + 1, total_bars - 1)].split("|")[0]
                    r = 33 + (root - 33) % 12
                    nr = 33 + (chord(nxt)[0] - 33) % 12
                    third, fifth = r + ints[1], r + ints[2]
                    line = [r, third if rng.random() < 0.6 else fifth, fifth if rng.random() < 0.5 else r + 12,
                            nr - 1 if rng.random() < 0.6 else nr + 1]
                    parts["bass"] += [(b + j, 0.9, p, 96 if j == 0 else 84) for j, p in enumerate(line)]
            elif bstyle in ("bossa", "eighths", "pulse"):
                for i, nm in enumerate(sec_bars):
                    root = chord(nm.split("|")[0])[0]
                    r = 33 + (root - 33) % 12
                    b = (b0 + i) * 4
                    if bstyle == "bossa":  # root on 1, fifth on 3 with a pickup root before it
                        parts["bass"] += [(b, 1.4, r, 100), (b + 1.5, .45, r + 7 if r + 7 <= 52 else r - 5, 86),
                                          (b + 2, 1.4, r + 7 if r + 7 <= 52 else r - 5, 96), (b + 3.5, .45, r, 84)]
                    elif bstyle == "eighths":  # driving 8th-note roots with octave pops on the "and" of 4
                        parts["bass"] += [(b + j * 0.5, 0.4, r + (12 if j == 7 else 0), 104 if j % 2 == 0 else 86) for j in range(8)]
                    else:  # heartbeat pulse: one per beat and a half
                        parts["bass"] += [(b + j * 1.5, 0.6, r, 100 - 10 * (j % 2)) for j in range(3)]
            else:
                m, g = bass_line(sec_bars, b0, bstyle, rng)
                parts["bass"] += m
                parts["ghost"] += g
        # comping
        if fs["comp"] == "arp":  # broken chords in 8ths, up and back down (the Velvet Room piano)
            for i, nm in enumerate(sec_bars):
                b = (b0 + i) * 4
                lo_, hi_ = style.get("arp_range", (55, 74))
                v = upper(nm.split("|")[0], prev_v, lo_, hi_)
                prev_v = v
                root = chord(nm.split("|")[0])[0]
                seq = [lo_ - 12 + (root - lo_) % 12] + v + v[::-1][1:-1]
                parts["comp"] += [(b + k * 0.5, 0.9, seq[k % len(seq)], 74 if k % 4 == 0 else 62) for k in range(8)]
        elif fs["comp"]:
            for i, nm in enumerate(sec_bars):
                b = (b0 + i) * 4
                for s_, l_ in RHYTHMS[fs["comp"]]:
                    nm_ = chord_at(b + s_)
                    v = upper(nm_, prev_v, 55, 74)
                    prev_v = v
                    vel = 70 if feels[name] in ("verse", "breakdown", "intro", "outro") else 82
                    if fs["comp"] == "ballad" and s_ == 0:  # the piano's left hand: root and fifth low
                        root = chord(nm_)[0]
                        lowr = 36 + (root - 36) % 12
                        parts["comp"] += [(b, 3.9, lowr, 74), (b, 3.9, lowr + 7, 66)]
                    parts["comp"] += [(b + s_, l_, p, vel - 3 * j) for j, p in enumerate(v)]
        L = fs["layers"]
        for i, nm in enumerate(sec_bars):
            b = (b0 + i) * 4
            first = nm.split("|")[0]
            root = chord(first)[0]
            if "pad" in L:
                top = sorted(tones(first))
                pc = (root + (14 if 14 in chord(first)[1] else chord(first)[1][1])) % 12
                t = 72 + (pc - 72) % 12
                parts["pad"] += [(b, 3.9, t, 70), (b, 3.9, t + 12, 58)]
            if "low_strings" in L or "pad" in L:
                parts["low"].append((b, 3.9, 36 + (root - 36) % 12, 68))
            if "organ" in L:
                parts["organ"] += [(b, 3.85, p, 72) for p in upper(first, None, 55, 79)]
            if "rhodes_pad" in L:
                parts["organ"] += [(b, 3.85, p, 60) for p in upper(first, None, 57, 76)]
            if "guitar" in L:
                pat_l, pat_r = "g.gxg.gxg.gxg.gx", "gg.xgg.xgg.xgg.x"
                for k_, (pat, key) in enumerate(((pat_l, "guitar_l"), (pat_r, "guitar_r"))):
                    for j, c in enumerate(pat):
                        if c == ".":
                            continue
                        v = upper(chord_at(b + j * 0.25), None, 60, 74, 3)
                        parts[key] += [(b + j * 0.25, .18 if c == "x" else .05, p, 90 if c == "x" else 30) for p in
                                       (v if c == "x" else v[:2])]
            if "perc" in L:
                parts["perc"] += grid("xxoxxxoxxxoxxxox", b, lambda c: PERC["tri_open"] if c == "o" else PERC["tri_mute"], 40,
                                      length=0.15)
                if style.get("rim") or spec["style"] == "bossa":
                    parts["perc"] += grid("xxxxxxxxxxxxxxxx", b, PERC["shaker"], 36, length=0.1)
            if "congas" in L:
                for j, c in enumerate("gx..x.oogx..x.oo"):
                    if c != ".":
                        parts["perc"].append((b + j * 0.25, 0.2, PERC["conga_open"] if c == "o" else PERC["conga_mute"],
                                              {"g": 40, "x": 92 if j in (4, 12) else 64, "o": 82}[c]))
                parts["perc"] += grid("....x.......x...", b, PERC["tamb"], 74)
            if "brass" in L and style.get("brass") and i % 4 == 0:
                for beat in (0, .75, 1.5):
                    parts["brass_hi"] += [(b + beat, .3, p, 104) for p in upper(first, None, 64, 79, 2)]
                    parts["brass_lo"] += [(b + beat, .3, p, 98) for p in upper(first, None, 50, 62, 2)]
            if "choir" in L:
                parts["choir"] += [(b, 3.9, p, 76) for p in upper(first, None, 60, 76, 3)]
            if "ostinato" in L:  # 8th-note strings repeating the root and the fifth/flat-sixth above (boss drive)
                r = 55 + (root - 55) % 12
                fig = [r, r + 7, r + 8, r + 7] if mode == "minor" else [r, r + 7, r + 9, r + 7]
                parts["ostinato"] += [(b + j * 0.5, 0.4, fig[j % 4], 92 if j % 2 == 0 else 76) for j in range(8)]
            if "power" in L:  # distorted power chords: root and fifth in driving 8ths, palm-muted except on 1
                r = 40 + (root - 40) % 12
                parts["power"] += [(b + k * 0.5, 0.4 if k else 0.9, p, 100 if k % 2 == 0 else 84) for k in range(8)
                                   for p in (r, r + 7, r + 12)]
            if "scratch" in L and i % 2 == 1:  # Persona 3's DJ: a scratch on the last beat of every second bar
                parts["scratch"] += [(b + 3, 0.45, 60, 100), (b + 3.5, 0.4, 62 if i % 4 == 1 else 64, 92)]
            if "chipkit" in L:  # the noise-channel hats and a triangle kick under the real kit
                parts["chip"] += grid("x.......x.......", b, 36, 90) + grid("..x...x...x...x.", b, 42, 70, length=0.05)
            if "clock" in L:  # a ticking clock: a soft wood block on every beat, a deeper tock on 1
                parts["perc_gm"] += [(b + j, 0.1, 77 if j == 0 else 76, 54 if j == 0 else 40) for j in range(4)]
            if "timpani" in L and i % 2 == 0:
                parts["timpani"] += [(b, 1.0, 36 + (root - 36) % 12, 104), (b + 3.5, .4, 36 + (root - 36) % 12, 88)]
        # the hook motif (the song's own) on its colour instrument: intro, chorus answers, outro
        hook = spec.get("hook")
        if hook and ("lead_colour" in L or "motif" in L or "answers" in L or name.lower().startswith("solo")):
            for i in range(0, length, 4 if "answers" not in L else 2):
                b = (b0 + i) * 4 + (4 if "answers" in L else 0)
                parts["colour"] += [(b + s_, l_, n(p) if isinstance(p, str) else p, 92) for s_, l_, p in hook
                                    if b + s_ < b1 * 4]
        # an instrumental cue's themes: a phrase per section kind, repeated through the section
        themes = spec.get("themes") or {}
        th = themes.get(name) or themes.get(_kind(name, feels[name]))
        if th:
            phrase_beats = max(4.0, 4 * np.ceil(max(s_ + l_ for s_, l_, _ in th) / 4))
            k = 0
            while k * phrase_beats < length * 4:
                for s_, l_, p in th:
                    at = b0 * 4 + k * phrase_beats + s_
                    if at < b1 * 4:
                        parts["theme"].append((at, l_, n(p) if isinstance(p, str) else p, 96))
                k += 1
        th2 = (spec.get("themes2") or {}).get(name) or (spec.get("themes2") or {}).get(_kind(name, feels[name]))
        if th2:
            pb = max(4.0, 4 * np.ceil(max(s_ + l_ for s_, l_, _ in th2) / 4))
            k = 0
            while k * pb < length * 4:
                parts["theme2"] += [(b0 * 4 + k * pb + s_, l_, n(p) if isinstance(p, str) else p, 88) for s_, l_, p in th2
                                    if b0 * 4 + k * pb + s_ < b1 * 4]
                k += 1
        # transitions into big sections
        if big_next and si + 1 < len(secs) and style.get("transitions", True):
            nb = secs[si + 1][1] * 4
            parts["fx_rev"].append((nb - 3.5, 3.5, 49, 100))
            parts["fx_boom"].append((nb, 2.0, 36, 110))
    # battle songs: band hits on the shout words
    hits = []
    for sec in sheet:
        span = sec["beats"] / max(1, len(sec["lines"]))
        for li, text in enumerate(sec.get("lines", [])):
            if any(w.lower() in text.lower() for w in spec.get("hits", [])):
                hits.append(sec["start"] + li * span)
    for h in hits:
        parts["drums"] += [(h, 0.3, DRUM["kick"], 120), (h, 1.0, DRUM["crash"], 110)]
        parts["brass_hi"] += [(h, .4, p, 112) for p in upper(chord_at(h), None, 64, 79, 3)]
    tr = [
        ("Guide melody (for singing)", "lead", "sfz:piano", mel, 0.0),
        ("Drums", "drums", style["kit"], humanise(parts["drums"], rng, 6), 0.0),
        ("Percussion", "perc", "kit:latin", humanise(parts["perc"], rng, 6), 0.25),
        ("Rim clicks", "perc", "kit:jazz", humanise(parts["rim"], rng, 5), -0.15),
        ("Bass", "bass", style["bass"], humanise(parts["bass"], rng, 4), 0.0),
        ("Bass ghost notes", "bass", "sfz:bass_ghost",
         humanise(parts["ghost"], rng, 4) if str(style["bass"]).startswith("sfz:bass") else [], 0.0),
        ("Keys", "comp", style["comp"], clear(humanise(parts["comp"], rng, 5)), -0.1),
        ("Strings", "pad", style["pad"], clear(humanise(parts["pad"], rng, 3)), -0.35),
        ("Low strings", "pad", "sfz:cellos", humanise(parts["low"], rng, 3), 0.3),
        ("Organ / pad", "pad", style.get("organ") or "sfz:rhodes", clear(humanise(parts["organ"], rng, 4)), 0.15),
        ("Brass high", "counter", "sfz:trumpet_stac", clear(humanise(parts["brass_hi"], rng, 4)), 0.2),
        ("Brass low", "counter", "sfz:trombone_stac", clear(humanise(parts["brass_lo"], rng, 4)), -0.2),
        ("Guitar left", "arp", style.get("guitar") or "sfz:guitar_clean", clear(humanise(parts["guitar_l"], rng, 6)), -0.8),
        ("Guitar right", "arp", style.get("guitar") or "sfz:guitar_clean", clear(humanise(parts["guitar_r"], rng, 6)), 0.8),
        ("Hook", "counter", style["lead_colour"], clear(humanise(parts["colour"], rng, 4)), 0.1),
        ("Choir", "pad", "choir", clear(humanise(parts["choir"], rng, 3)), 0.0),
        ("String ostinato", "riff", "sfz:violins_spic", clear(humanise(parts["ostinato"], rng, 4)), -0.3),
        ("Timpani", "timpani", "timpani", humanise(parts["timpani"], rng, 4), 0.0),
        ("Theme", "counter" if sheet else "lead", spec.get("theme_inst") or style["lead_colour"],
         clear(humanise(parts["theme"], rng, 4)) if sheet else humanise(parts["theme"], rng, 4), 0.05),
        ("Countermelody", "counter", spec.get("theme2_inst") or "sfz:violins", humanise(parts["theme2"], rng, 4), -0.2),
        ("Power guitar", "arp", "distortion_guitar", clear(humanise(parts["power"], rng, 5)), 0.45),
        ("Scratches", "fx", "sfx:scratch", parts["scratch"], 0.2),
        ("Chip drums", "perc", "kit:chip", humanise(parts["chip"], rng, 3), 0.0),
        ("Clock", "perc", "kit:standard", parts["perc_gm"], 0.4),
        ("Reverse cymbals", "fx", "sfx:reverse_crash", parts["fx_rev"], 0.0),
        ("Boom", "fx", "sfx:boom", parts["fx_boom"], 0.0),
    ]
    sw = style.get("swing", 0.5)
    tracks = [Track(nm, role, inst, swing(sorted(notes), sw), pan=pan) for nm, role, inst, notes, pan in tr if notes]
    gains = {"Theme": 0, "Clock": -6, "Countermelody": -3, "Power guitar": -4, "Scratches": -2, "Guide melody (for singing)": -9, "Bass ghost notes": -7, "Percussion": -2, "Rim clicks": -6, "Strings": -2,
             "Low strings": -3, "Organ / pad": -3, "Guitar left": -3, "Guitar right": -3, "Hook": 1, "Choir": -2,
             "String ostinato": -1, "Reverse cymbals": -2, "Boom": -3}
    if style.get("drum_gain") is not None:
        gains["Drums"] = style["drum_gain"]
    song = build_song(spec.get("pack", PACK_OF[spec["style"]]), bpm, tonic, mode, secs, bars, tracks, seed)
    return song, gains


def _kind(name: str, feel: str) -> str:
    low = name.lower()
    for k in ("intro", "pre", "chorus", "rap", "bridge", "break", "outro", "verse", "final"):
        if low.startswith(k):
            return {"break": "bridge"}.get(k, k)
    return feel
