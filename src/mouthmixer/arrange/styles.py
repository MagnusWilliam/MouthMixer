"""Instruments and style packs (PLAN.md §8). Packs are data: adding a style means adding an entry.

Every instrument comes from GeneralUser GS (assets/soundfonts, free for commercial music); numbers are
General MIDI programs. Ranges are sounding MIDI notes (MUSIC_KNOWLEDGE §11): parts are moved by
octaves to fit, and the critic rejects anything that still doesn't.
"""

from __future__ import annotations

# name: (bank, program, low, high, family, gain)
INSTRUMENTS = {
    "piano": (0, 0, 21, 108, "keys", 0.9), "bright_piano": (0, 1, 21, 108, "keys", 0.85),
    "rhodes": (0, 4, 28, 103, "keys", 1.0), "fm_piano": (0, 5, 28, 103, "keys", 0.9),
    "celesta": (0, 8, 60, 108, "mallet", 0.8), "glockenspiel": (0, 9, 72, 108, "mallet", 0.55),
    "music_box": (0, 10, 60, 96, "mallet", 0.7), "vibraphone": (0, 11, 53, 89, "mallet", 0.9),
    "marimba": (0, 12, 45, 96, "mallet", 0.9), "drawbar_organ": (0, 16, 36, 96, "keys", 0.6),
    "rock_organ": (0, 18, 36, 96, "keys", 0.6), "accordion": (0, 21, 53, 89, "reed", 0.6),
    "nylon_guitar": (0, 24, 40, 84, "guitar", 1.0), "steel_guitar": (0, 25, 40, 84, "guitar", 0.9),
    "jazz_guitar": (0, 26, 40, 84, "guitar", 1.0), "clean_guitar": (0, 27, 40, 86, "guitar", 0.9),
    "muted_guitar": (0, 28, 40, 76, "guitar", 0.9), "overdrive_guitar": (0, 29, 40, 86, "guitar", 0.55),
    "acoustic_bass": (0, 32, 28, 55, "bass", 1.1), "finger_bass": (0, 33, 28, 55, "bass", 1.1),
    "pick_bass": (0, 34, 28, 55, "bass", 1.0), "fretless_bass": (0, 35, 28, 55, "bass", 1.1),
    "slap_bass": (0, 36, 28, 60, "bass", 0.9), "synth_bass": (0, 38, 24, 55, "bass", 0.8),
    "violin": (0, 40, 55, 100, "strings", 0.8), "cello": (0, 42, 36, 76, "strings", 0.9),
    "contrabass": (0, 43, 28, 55, "bass", 1.1), "pizzicato": (0, 45, 36, 96, "strings", 1.0),
    "harp": (0, 46, 24, 103, "strings", 1.0), "timpani": (0, 47, 38, 55, "perc", 1.0),
    "strings": (0, 48, 36, 96, "strings", 0.7), "slow_strings": (0, 49, 36, 96, "strings", 0.7),
    "synth_strings": (0, 50, 36, 96, "strings", 0.6), "choir": (0, 52, 48, 81, "voice", 0.6),
    "voice_oohs": (0, 53, 48, 79, "voice", 0.7), "trumpet": (0, 56, 52, 84, "brass", 0.7),
    "trombone": (0, 57, 40, 72, "brass", 0.7), "muted_trumpet": (0, 59, 52, 82, "brass", 0.85),
    "french_horn": (0, 60, 41, 77, "brass", 0.75), "brass_section": (0, 61, 40, 84, "brass", 0.6),
    "synth_brass": (0, 62, 36, 84, "brass", 0.55), "clarinet": (0, 71, 50, 91, "wind", 0.8),
    "flute": (0, 73, 60, 96, "wind", 0.8), "pan_flute": (0, 75, 60, 96, "wind", 0.8),
    "shakuhachi": (0, 77, 55, 91, "wind", 0.8), "ocarina": (0, 79, 60, 91, "wind", 0.8),
    "square_lead": (0, 80, 48, 96, "synth", 0.45), "saw_lead": (0, 81, 48, 96, "synth", 0.4),
    "chiff_lead": (0, 83, 48, 96, "synth", 0.5), "bass_lead": (0, 87, 28, 60, "bass", 0.6),
    "new_age_pad": (0, 88, 36, 96, "pad", 0.55), "warm_pad": (0, 89, 36, 96, "pad", 0.6),
    "polysynth": (0, 90, 36, 96, "pad", 0.5), "choir_pad": (0, 91, 36, 96, "pad", 0.55),
    "bowed_pad": (0, 92, 36, 96, "pad", 0.55), "halo_pad": (0, 94, 36, 96, "pad", 0.55),
    "kalimba": (0, 108, 60, 96, "mallet", 0.8), "steel_drums": (0, 114, 52, 88, "mallet", 0.7),
}

# More unique sounds (GeneralUser GS variation banks and the rest of General MIDI).
INSTRUMENTS.update({
    "electric_grand": (0, 2, 28, 103, "keys", 0.9), "honky_tonk": (0, 3, 28, 103, "keys", 0.8),
    "harpsichord": (0, 6, 29, 89, "keys", 0.8), "clavinet": (0, 7, 36, 96, "keys", 0.7),
    "tubular_bells": (0, 14, 60, 77, "mallet", 0.7), "dulcimer": (0, 15, 48, 84, "mallet", 0.8),
    "church_organ": (0, 19, 36, 96, "keys", 0.5), "harmonica": (0, 22, 60, 84, "reed", 0.7),
    "tremolo_strings": (0, 44, 36, 96, "strings", 0.7), "orchestra_hit": (0, 55, 48, 72, "brass", 0.6),
    "tuba": (0, 58, 28, 58, "brass", 0.8), "oboe": (0, 68, 58, 91, "wind", 0.8), "bassoon": (0, 70, 34, 72, "wind", 0.8),
    "piccolo": (0, 72, 74, 108, "wind", 0.6), "recorder": (0, 74, 60, 96, "wind", 0.8), "whistle": (0, 78, 60, 96, "wind", 0.6),
    "calliope": (0, 82, 48, 96, "synth", 0.5), "voice_lead": (0, 85, 48, 84, "synth", 0.5), "fifths_lead": (0, 86, 48, 84, "synth", 0.4),
    "ice_rain": (0, 96, 48, 96, "fxpad", 0.5), "soundtrack_pad": (0, 97, 36, 96, "fxpad", 0.5),
    "crystal": (0, 98, 60, 96, "fxpad", 0.6), "atmosphere": (0, 99, 36, 96, "fxpad", 0.5),
    "echo_drops": (0, 102, 48, 96, "fxpad", 0.5), "star_theme": (0, 103, 36, 96, "fxpad", 0.5),
    "sitar": (0, 104, 48, 84, "world", 0.7), "banjo": (0, 105, 48, 84, "guitar", 0.8), "shamisen": (0, 106, 50, 84, "world", 0.8),
    "koto": (0, 107, 48, 96, "world", 0.8), "fiddle": (0, 110, 55, 96, "strings", 0.7), "tinker_bell": (0, 112, 72, 108, "mallet", 0.5),
    "taiko": (0, 116, 36, 60, "perc", 1.0), "reverse_cymbal": (0, 119, 48, 72, "sfx", 0.6),
    "chorus_rhodes": (8, 4, 28, 103, "keys", 1.0), "chorus_fm_piano": (8, 5, 28, 103, "keys", 0.9),
    "church_bells": (8, 14, 48, 84, "mallet", 0.6), "carillon": (9, 14, 48, 84, "mallet", 0.6),
    "ukulele": (8, 24, 60, 84, "guitar", 0.9), "twelve_string": (8, 25, 40, 84, "guitar", 0.9),
    "hawaiian_guitar": (8, 26, 40, 84, "guitar", 0.8), "chorus_guitar": (8, 27, 40, 86, "guitar", 0.9),
    "funk_guitar": (8, 28, 40, 79, "guitar", 0.9), "mandolin": (16, 25, 55, 88, "guitar", 0.8),
    "acid_bass": (8, 38, 24, 55, "bass", 0.6), "fm_bass": (8, 39, 24, 55, "bass", 0.7),
    "techno_bass": (11, 38, 24, 55, "bass", 0.6), "pulse_bass": (11, 39, 24, 55, "bass", 0.6),
    "orchestra_pad": (8, 48, 36, 96, "strings", 0.6), "full_orchestra": (12, 48, 36, 96, "strings", 0.6),
    "woodwind_choir": (13, 48, 48, 91, "wind", 0.6), "brass_section_2": (8, 61, 40, 84, "brass", 0.6),
    "synth_brass_3": (8, 62, 36, 84, "brass", 0.5), "sine_lead": (8, 80, 48, 96, "synth", 0.6),
    "doctor_solo": (8, 81, 48, 96, "synth", 0.4), "saw_stab": (11, 81, 36, 84, "synth", 0.4),
    "bright_saw_stack": (11, 100, 36, 84, "synth", 0.35), "synth_chime": (11, 98, 60, 96, "mallet", 0.6),
    "synth_mallet": (1, 98, 48, 96, "mallet", 0.7), "mystery_pad": (11, 96, 36, 96, "fxpad", 0.5),
    "solar_wind": (11, 89, 36, 96, "pad", 0.5), "night_vision": (13, 88, 36, 96, "pad", 0.5),
    "bell_piano": (12, 0, 28, 103, "keys", 0.8), "bell_rhodes": (12, 4, 28, 103, "keys", 0.9),
    "whistling": (11, 78, 60, 91, "wind", 0.6), "tin_whistle": (24, 75, 62, 96, "wind", 0.6),
    "taisho_koto": (8, 107, 48, 96, "world", 0.7), "windchime": (5, 124, 60, 84, "sfx", 0.5),
    "birds": (0, 123, 60, 84, "sfx", 0.4), "stream": (4, 122, 48, 72, "sfx", 0.5), "rain_sfx": (1, 122, 48, 72, "sfx", 0.5),
    "thunder": (2, 122, 36, 60, "sfx", 0.5), "seashore": (0, 122, 48, 72, "sfx", 0.5), "train": (6, 125, 48, 72, "sfx", 0.5),
})

# Drum kits are bank 128 presets in GeneralUser GS.
KITS = {"standard": 0, "room": 8, "power": 16, "electronic": 24, "tr808": 25, "dance": 26, "jazz": 32, "brush": 40,
        "orchestra": 48, "sfx": 56}
DRUM = {"kick": 36, "snare": 38, "rim": 37, "clap": 39, "hat": 42, "pedal_hat": 44, "open_hat": 46,
        "crash": 49, "ride": 51, "tom_lo": 45, "tom_mid": 47, "tom_hi": 50, "tambourine": 54, "shaker": 70,
        "concert_bd": 35, "ride_bell": 53, "splash": 55, "cowbell": 56, "hi_bongo": 60, "lo_bongo": 61,
        "mute_conga": 62, "hi_conga": 63, "lo_conga": 64, "hi_timbale": 65, "lo_timbale": 66, "hi_agogo": 67,
        "lo_agogo": 68, "cabasa": 69, "maracas": 70, "claves": 75, "hi_wood": 76, "lo_wood": 77, "mute_triangle": 80,
        "triangle": 81}

# Drum grids: 16 steps per bar. X accent, x normal, g ghost, . rest.
VEL = {"X": 112, "x": 88, "g": 38, "o": 80}

PACKS = {
    "city_pop_day": {
        "title": "City-pop day",
        "describe": "bright city pop: 7th chords, finger bass, Rhodes, light swing",
        "bpm": (92, 104), "swing": 0.54, "ext": ["seventh", "seventh", "ninth"], "tension": 0.6,
        "borrowed": ["V/V", "V/vi", "iv", "bVII"], "harmonic_rhythm": [1, 1, 2],
        "favourites": [["IV", "V", "iii", "vi"], ["I", "vi", "ii", "V"], ["ii", "V", "I", "vi"]],
        "kit": ["standard", "room"],
        "drums": [{"kick": "x.....x...x.....", "snare": "....x.......x...", "hat": "x.x.x.x.x.x.x.xo"},
                  {"kick": "x..x....x.x.....", "snare": "....x.......x..g", "hat": "xxxxxxxxxxxxxxxx"}],
        "bass": [[(0, 3, "R"), (3, 1, "8"), (6, 2, "R"), (8, 3, "5"), (11, 1, "8"), (14, 2, "A")],
                 [(0, 4, "R"), (6, 2, "R"), (8, 2, "5"), (10, 2, "8"), (13, 3, "A")]],
        "comp_rhythm": [[(0, 6), (6, 4), (10, 6)], [(2, 2), (6, 2), (10, 2), (14, 2)]],
        "roles": {
            "lead": ["muted_trumpet", "flute", "vibraphone", "clean_guitar", "jazz_guitar"],
            "comp": ["rhodes", "fm_piano", "clean_guitar"],
            "pad": ["warm_pad", "slow_strings", "strings"],
            "bass": ["finger_bass", "fretless_bass", "slap_bass"],
            "arp": ["vibraphone", "glockenspiel", "clean_guitar", "marimba"],
            "counter": ["flute", "strings", "voice_oohs"],
        },
        "rootless": False, "spread": True, "reverb": 0.45, "delay": 0.12, "chorus": True,
    },
    "neon_night": {
        "title": "Neon night",
        "describe": "neo-soul / lo-fi night: minor 9ths, laid-back swing, Wurlitzer and muted trumpet",
        "bpm": (82, 92), "swing": 0.6, "ext": ["ninth", "seventh"], "tension": 0.85,
        "borrowed": ["iv", "bVI", "subV", "IV7"], "harmonic_rhythm": [1, 1, 2],
        "favourites": [["ii", "V", "I", "I"], ["vi", "ii", "V", "I"], ["i", "iv", "bVII", "bIII"]],
        "kit": ["jazz", "brush", "standard"],
        "drums": [{"kick": "x......x..x.....", "snare": "....x.......x...", "hat": "x.x.x.x.x.x.x.x.",
                   "ghost": "..g........g...."},
                  {"kick": "x.........x..x..", "rim": "....x.......x...", "hat": "x.xxx.x.x.xxx.x."}],
        "bass": [[(0, 6, "R"), (7, 1, "R"), (10, 4, "5"), (14, 2, "A")], [(0, 10, "R"), (10, 2, "8"), (13, 3, "A")]],
        "comp_rhythm": [[(0, 14)], [(0, 6), (7, 9)]],
        "roles": {
            "lead": ["muted_trumpet", "flute", "vibraphone", "nylon_guitar", "voice_oohs"],
            "comp": ["fm_piano", "rhodes", "jazz_guitar"],
            "pad": ["halo_pad", "warm_pad", "new_age_pad"],
            "bass": ["fretless_bass", "finger_bass", "acoustic_bass"],
            "arp": ["vibraphone", "kalimba", "celesta"],
            "counter": ["clarinet", "voice_oohs", "flute"],
        },
        "rootless": True, "spread": False, "reverb": 0.55, "delay": 0.18, "chorus": True, "vinyl": True,
    },
    "acid_jazz_battle": {
        "title": "Acid-jazz battle",
        "describe": "fast acid-jazz / funk battle: breakbeat drums, walking bass, brass stabs, driven guitar",
        "bpm": (150, 170), "swing": 0.5, "ext": ["seventh"], "tension": 0.7, "double_time": True,
        "borrowed": ["V/V", "subV", "V/ii", "bVII"], "harmonic_rhythm": [1, 2],
        "favourites": [["i", "iv", "bVII", "V"], ["ii", "V", "I", "VI"], ["vi", "ii", "V", "I"]],
        "kit": ["power", "standard", "room"],
        "drums": [{"kick": "x..x..x...x..x..", "snare": "....X.......X...", "ghost": "..g..g.g..g..g.g",
                   "hat": "xxxxxxxxxxxxxxxx"},
                  {"kick": "x.x...x.x.x...x.", "snare": "....X..g....X.g.", "hat": "x.x.x.x.x.x.x.x.",
                   "open_hat": "..............o."}],
        "bass": [[(0, 2, "R"), (2, 2, "3"), (4, 2, "5"), (6, 2, "8"), (8, 2, "5"), (10, 2, "3"), (12, 2, "R"),
                  (14, 2, "A")],
                 [(0, 2, "R"), (3, 1, "8"), (4, 2, "R"), (7, 1, "5"), (8, 2, "R"), (11, 1, "8"), (12, 2, "5"),
                  (14, 2, "A")]],
        "comp_rhythm": [[(0, 1), (3, 1), (6, 1), (10, 2), (13, 1)], [(2, 1), (6, 1), (10, 1), (14, 1)]],
        "roles": {
            "lead": ["overdrive_guitar", "brass_section", "synth_brass", "trumpet", "saw_lead"],
            "comp": ["rhodes", "clean_guitar", "rock_organ"],
            "pad": ["brass_section", "synth_strings", "strings"],
            "bass": ["slap_bass", "finger_bass", "synth_bass"],
            "arp": ["muted_guitar", "clean_guitar", "rhodes"],
            "counter": ["brass_section", "trombone", "strings"],
        },
        "rootless": False, "spread": False, "reverb": 0.3, "delay": 0.08, "chorus": False, "drive": True,
    },
    "orchestral_adventure": {
        "title": "Orchestral adventure",
        "describe": "cinematic orchestra: horns and strings, harp and pizzicato, timpani",
        "bpm": (96, 128), "swing": 0.5, "ext": ["triad"], "tension": 0.3,
        "borrowed": ["bVI", "bVII", "iv", "Vsus"], "harmonic_rhythm": [1, 1, 2],
        "favourites": [["I", "bVI", "bVII", "I"], ["vi", "IV", "I", "V"], ["I", "V", "vi", "IV"]],
        "kit": ["orchestra"],
        "drums": [{"concert_bd": "x.......x.......", "snare": "....g.......g...", "crash": "................"},
                  {"concert_bd": "x.....x.x.......", "tom_lo": "............x.x."}],
        "bass": [[(0, 8, "R"), (8, 8, "5")], [(0, 12, "R"), (12, 4, "A")]],
        "comp_rhythm": [[(0, 16)], [(0, 8), (8, 8)]],
        "roles": {
            "lead": ["french_horn", "violin", "flute", "trumpet", "clarinet"],
            "comp": ["strings", "slow_strings"],
            "pad": ["choir", "slow_strings", "choir_pad"],
            "bass": ["contrabass", "cello"],
            "arp": ["harp", "pizzicato", "celesta"],
            "counter": ["cello", "french_horn", "clarinet"],
        },
        "rootless": False, "spread": True, "reverb": 0.75, "delay": 0.0, "chorus": False, "timpani": True,
    },
    "arcade": {
        "title": "Arcade",
        "describe": "chiptune / arcade: square-wave lead, fast arpeggios, electronic drums",
        "bpm": (128, 150), "swing": 0.5, "ext": ["triad"], "tension": 0.3,
        "borrowed": ["bVII", "bVI", "V/V"], "harmonic_rhythm": [1, 2],
        "favourites": [["I", "V", "vi", "IV"], ["vi", "IV", "I", "V"], ["I", "bVII", "IV", "I"]],
        "kit": ["electronic", "tr808"],
        "drums": [{"kick": "x...x...x...x...", "snare": "....x.......x...", "hat": "x.x.x.x.x.x.x.x."},
                  {"kick": "x.....x.x.......", "snare": "....x.......x.x.", "hat": "xxxxxxxxxxxxxxxx"}],
        "bass": [[(i * 2, 1, "R" if i % 2 == 0 else "8") for i in range(8)], [(0, 3, "R"), (4, 3, "5"), (8, 3, "8"), (12, 3, "5")]],
        "comp_rhythm": [[(0, 2), (4, 2), (8, 2), (12, 2)]],
        "roles": {
            "lead": ["square_lead", "chiff_lead", "saw_lead"],
            "comp": ["square_lead", "polysynth"],
            "pad": ["polysynth", "synth_strings"],
            "bass": ["bass_lead", "synth_bass"],
            "arp": ["square_lead", "chiff_lead"],
            "counter": ["chiff_lead", "saw_lead"],
        },
        "rootless": False, "spread": False, "reverb": 0.2, "delay": 0.15, "chorus": False, "fast_arp": True,
    },
    "dream_ambient": {
        "title": "Dream",
        "describe": "calm exploration: harp and celesta, soft pads, a lot of space",
        "bpm": (70, 90), "swing": 0.5, "ext": ["ninth", "seventh"], "tension": 0.8,
        "borrowed": ["iv", "bVII", "Vsus"], "harmonic_rhythm": [1],
        "favourites": [["I", "IV", "vi", "V"], ["vi", "IV", "I", "V"], ["I", "iii", "IV", "iv"]],
        "kit": ["brush", "jazz"],
        "drums": [{"kick": "x..........x....", "rim": "........x.......", "shaker": "x.x.x.x.x.x.x.x."},
                  {"shaker": "xgxgxgxgxgxgxgxg", "kick": "x.......x......."}],
        "bass": [[(0, 16, "R")], [(0, 12, "R"), (12, 4, "5")]],
        "comp_rhythm": [[(0, 16)]],
        "roles": {
            "lead": ["celesta", "music_box", "pan_flute", "ocarina", "shakuhachi", "kalimba", "harp"],
            "comp": ["piano", "harp"],
            "pad": ["halo_pad", "bowed_pad", "choir_pad", "slow_strings"],
            "bass": ["fretless_bass", "acoustic_bass"],
            "arp": ["harp", "celesta", "kalimba", "music_box"],
            "counter": ["slow_strings", "voice_oohs", "clarinet"],
        },
        "rootless": False, "spread": True, "reverb": 0.85, "delay": 0.22, "chorus": True,
    },
}

# Persona-informed packs (docs/PERSONA_STYLE.md): genre traits, never fingerprints.
PACKS["heist_funk"] = {
    "title": "Heist funk",
    "describe": "acid-jazz / funk, Persona 5-style energy: minor key, organ and slap bass, Rhodes riff, brass hooks",
    "bpm": (120, 134), "swing": 0.5, "ext": ["seventh", "ninth"], "tension": 0.75,
    "borrowed": ["bVI", "bVII", "subV", "V7"], "harmonic_rhythm": [1, 2],
    "favourites": [["i", "bVI", "bVII", "i"], ["i", "iv", "bVII", "bIII"], ["bVI", "bVII", "i", "i"]],
    "kit": ["power", "room", "standard"],
    "drums": [{"kick": "x..x..x...x..x..", "snare": "....X.......X...", "ghost": "..g..g.g..g..g.g",
               "hat": "x.x.x.x.x.x.x.x.", "open_hat": "......o.......o."},
              {"kick": "x.x.......x..x..", "snare": "....X..g....X...", "hat": "xxxxxxxxxxxxxxxx"}],
    "bass": [[(0, 1, "R"), (2, 1, "8"), (3, 1, "R"), (6, 1, "8"), (8, 1, "R"), (10, 1, "8"), (11, 1, "5"), (14, 2, "A")],
             [(0, 3, "R"), (3, 1, "8"), (6, 2, "R"), (8, 2, "5"), (10, 1, "8"), (12, 2, "R"), (14, 2, "A")]],
    "comp_rhythm": [[(0, 1), (3, 1), (6, 1), (10, 2), (13, 1)], [(2, 1), (6, 1), (10, 1), (14, 1)]],
    "roles": {
        "lead": ["trumpet", "muted_trumpet", "chorus_guitar", "flute", "vibraphone"],
        "comp": ["drawbar_organ", "clavinet", "funk_guitar", "rhodes"],
        "pad": ["brass_section", "strings", "orchestra_pad"],
        "bass": ["slap_bass", "finger_bass", "pick_bass"],
        "arp": ["funk_guitar", "clean_guitar", "vibraphone"],
        "counter": ["brass_section", "trombone", "flute"],
        "riff": ["rhodes", "chorus_rhodes", "brass_section", "clavinet"],
    },
    "rootless": True, "spread": False, "reverb": 0.3, "delay": 0.1, "chorus": False, "drive": True,
    "vocal_preset": "soul",
}
PACKS["bright_pop_rock"] = {
    "title": "Bright pop-rock",
    "describe": "upbeat J-pop / funk-rock, Persona 4-style: major key, funky piano, surf-ish guitar, brass stabs",
    "bpm": (124, 150), "swing": 0.5, "ext": ["triad", "seventh"], "tension": 0.5,
    "borrowed": ["V/V", "V/vi", "bVII", "iv"], "harmonic_rhythm": [1, 2],
    "favourites": [["IV", "V", "iii", "vi"], ["I", "V", "vi", "IV"], ["vi", "IV", "V", "I"]],
    "kit": ["standard", "power", "room"],
    "drums": [{"kick": "x...x...x...x...", "snare": "....X.......X...", "hat": "x.x.x.x.x.x.x.x.", "open_hat": "..o...o...o...o."},
              {"kick": "x.x...x.x.x.....", "snare": "....X.......X..g", "hat": "xxxxxxxxxxxxxxxx"}],
    "bass": [[(i * 2, 1, "R" if i % 2 == 0 else "8") for i in range(8)],
             [(0, 2, "R"), (3, 1, "R"), (6, 2, "5"), (8, 2, "R"), (11, 1, "8"), (14, 2, "A")]],
    "comp_rhythm": [[(0, 2), (3, 1), (6, 2), (10, 2), (13, 1)], [(0, 6), (6, 4), (10, 6)]],
    "roles": {
        "lead": ["bright_piano", "chorus_guitar", "trumpet", "flute", "violin"],
        "comp": ["piano", "bright_piano", "electric_grand", "steel_guitar"],
        "pad": ["strings", "synth_strings", "polysynth"],
        "bass": ["pick_bass", "finger_bass", "slap_bass"],
        "arp": ["clean_guitar", "glockenspiel", "synth_mallet"],
        "counter": ["brass_section", "strings", "flute"],
        "riff": ["brass_section", "overdrive_guitar", "bright_piano"],
    },
    "rootless": False, "spread": True, "reverb": 0.35, "delay": 0.12, "chorus": True,
    "vocal_preset": "bright_pop",
}
PACKS["moonlit_hiphop"] = {
    "title": "Moonlit hip-hop",
    "describe": "hip-hop with piano and strings, Persona 3-style night mood: minor key, boom-bap, synth touches",
    "bpm": (84, 98), "swing": 0.57, "ext": ["seventh", "ninth"], "tension": 0.7,
    "borrowed": ["bVI", "bVII", "iv"], "harmonic_rhythm": [1],
    "favourites": [["i", "bVI", "bIII", "bVII"], ["i", "iv", "bVI", "V"], ["i", "bVII", "bVI", "bVII"]],
    "kit": ["standard", "tr808", "room"],
    "drums": [{"kick": "x......x..x.....", "snare": "....x.......x...", "hat": "x.x.x.x.x.x.x.x.", "ghost": "..g........g...."},
              {"kick": "x.........x..x..", "clap": "....x.......x...", "hat": "x.xxx.x.xxxxx.xx"}],
    "bass": [[(0, 6, "R"), (7, 1, "R"), (10, 4, "5"), (14, 2, "A")], [(0, 12, "R"), (12, 4, "5")]],
    "comp_rhythm": [[(0, 8), (8, 8)], [(0, 14)]],
    "roles": {
        "lead": ["piano", "bell_piano", "violin", "synth_mallet", "whistling"],
        "comp": ["piano", "electric_grand", "bell_rhodes"],
        "pad": ["strings", "slow_strings", "night_vision", "choir_pad"],
        "bass": ["synth_bass", "fm_bass", "finger_bass"],
        "arp": ["synth_chime", "music_box", "celesta"],
        "counter": ["cello", "violin", "strings"],
        "riff": ["bell_piano", "synth_chime", "piano"],
    },
    "rootless": False, "spread": True, "reverb": 0.5, "delay": 0.2, "chorus": False, "vinyl": True,
    "vocal_preset": "lofi",
}
for _k, _preset in {"city_pop_day": "soul", "neon_night": "soul", "acid_jazz_battle": "rock",
                    "orchestral_adventure": "cinematic", "arcade": "arcade", "dream_ambient": "dreamy"}.items():
    PACKS[_k]["vocal_preset"] = _preset

DEFAULT_PACKS = ["city_pop_day", "neon_night", "acid_jazz_battle", "heist_funk"]  # the decided three + the Persona-informed one

# Two more Persona-informed moods for the starter beats (docs/PERSONA_STYLE.md §2, §8).
INSTRUMENTS["distortion_guitar"] = (0, 30, 40, 86, "guitar", 0.55)
PACKS["tense_dungeon"] = {
    "title": "Tense dungeon",
    "describe": "dungeon / tension: minor key with a dark flat-2 colour, pulsing synth bass, sparse drums, bells",
    "bpm": (100, 112), "swing": 0.5, "ext": ["triad", "seventh"], "tension": 0.8,
    "borrowed": ["bII", "bVI", "iv"], "harmonic_rhythm": [1],
    "favourites": [["i", "bVI", "i", "bVII"], ["i", "iv", "i", "bVI"], ["i", "bII", "i", "bVII"]],
    "kit": ["electronic", "room", "standard"],
    "drums": [{"kick": "x.......x.......", "snare": "........x.......", "hat": "..x...x...x...x.", "rim": "......x.......x."},
              {"kick": "x..x....x..x....", "clap": "....x.......x...", "hat": "x.x.x.x.x.x.x.x."}],
    "bass": [[(i * 2, 1, "R") for i in range(8)], [(0, 1, "R"), (2, 1, "R"), (3, 1, "8"), (6, 2, "R"), (8, 1, "R"),
                                                    (10, 1, "R"), (11, 1, "8"), (14, 2, "5")]],
    "comp_rhythm": [[(0, 16)], [(0, 8), (8, 8)]],
    "roles": {
        "lead": ["music_box", "celesta", "synth_chime", "oboe", "mystery_pad"],
        "comp": ["mystery_pad", "night_vision", "piano"],
        "pad": ["mystery_pad", "atmosphere", "bowed_pad", "tremolo_strings"],
        "bass": ["synth_bass", "pulse_bass", "fm_bass"],
        "arp": ["music_box", "celesta", "synth_chime"],
        "counter": ["cello", "tremolo_strings", "oboe"],
        "riff": ["synth_chime", "music_box", "pizzicato"],
    },
    "rootless": False, "spread": True, "reverb": 0.6, "delay": 0.2, "chorus": False,
    "vocal_preset": "dreamy",
}
PACKS["boss_rock"] = {
    "title": "Boss rock",
    "describe": "boss / rock battle, Persona 4-style energy: minor key, driving 8th-note bass, distorted guitar, brass",
    "bpm": (146, 160), "swing": 0.5, "ext": ["triad"], "tension": 0.6,
    "borrowed": ["bVI", "bVII", "V7"], "harmonic_rhythm": [1, 2],
    "favourites": [["i", "bVI", "bVII", "i"], ["i", "bVII", "bVI", "V"], ["bVI", "bVII", "i", "i"]],
    "kit": ["power", "standard", "room"],
    "drums": [{"kick": "x.x...x.x.x...x.", "snare": "....X.......X...", "hat": "x.x.x.x.x.x.x.x.", "open_hat": "......o.......o."},
              {"kick": "x...x...x...x...", "snare": "....X.......X..X", "hat": "xxxxxxxxxxxxxxxx"}],
    "bass": [[(i * 2, 2, "R") for i in range(8)], [(0, 2, "R"), (2, 2, "R"), (4, 2, "8"), (6, 2, "R"), (8, 2, "R"),
                                                    (10, 2, "5"), (12, 2, "R"), (14, 2, "A")]],
    "comp_rhythm": [[(0, 2), (2, 2), (4, 2), (6, 2), (8, 2), (10, 2), (12, 2), (14, 2)], [(0, 3), (3, 3), (6, 2), (8, 8)]],
    "roles": {
        "lead": ["distortion_guitar", "overdrive_guitar", "trumpet", "saw_lead", "brass_section"],
        "comp": ["distortion_guitar", "overdrive_guitar", "rock_organ"],
        "pad": ["strings", "synth_strings", "brass_section"],
        "bass": ["pick_bass", "finger_bass", "synth_bass"],
        "arp": ["clean_guitar", "rock_organ", "synth_mallet"],
        "counter": ["brass_section", "strings", "synth_brass"],
        "riff": ["brass_section", "distortion_guitar", "synth_brass"],
    },
    "rootless": False, "spread": False, "reverb": 0.3, "delay": 0.08, "chorus": False, "drive": True,
    "vocal_preset": "rock",
}

# Saxophones (GM 64-67), for night jazz (not as a battle lead: PERSONA_STYLE §8).
INSTRUMENTS["soprano_sax"] = (0, 64, 56, 87, "reed", 0.7)
INSTRUMENTS["alto_sax"] = (0, 65, 49, 81, "reed", 0.7)
INSTRUMENTS["tenor_sax"] = (0, 66, 44, 76, "reed", 0.7)
INSTRUMENTS["baritone_sax"] = (0, 67, 36, 69, "reed", 0.7)

# More styles for LINE ZERO's song list (docs/SONGBOOK.md).
PACKS["rain_bossa"] = {
    "title": "Rainy bossa",
    "describe": "soft bossa nova: nylon guitar, brushes and rim-click clave, upright bass, major 7ths",
    "bpm": (128, 140), "swing": 0.5, "ext": ["seventh", "ninth"], "tension": 0.75,
    "borrowed": ["V/ii", "iv", "subV"], "harmonic_rhythm": [1, 2],
    "favourites": [["IV", "iii", "ii", "V"], ["I", "vi", "ii", "V"], ["ii", "V", "I", "I"]],
    "kit": ["brush", "jazz", "standard"],
    "drums": [{"kick": "x..x....x..x....", "rim": "x..x..x...x..x..", "hat": "x.x.x.x.x.x.x.x."},
              {"kick": "x.......x.......", "rim": "..x..x....x..x..", "shaker": "xxxxxxxxxxxxxxxx"}],
    "bass": [[(0, 6, "R"), (6, 2, "5"), (8, 6, "5"), (14, 2, "R")], [(0, 4, "R"), (6, 2, "5"), (8, 4, "5"), (14, 2, "A")]],
    "comp_rhythm": [[(0, 2), (3, 2), (6, 2), (8, 2), (10, 2), (13, 2)], [(0, 3), (3, 3), (6, 4), (10, 3), (13, 3)]],
    "roles": {
        "lead": ["flute", "nylon_guitar", "vibraphone", "clarinet", "alto_sax"],
        "comp": ["nylon_guitar", "rhodes", "jazz_guitar"],
        "pad": ["slow_strings", "warm_pad", "strings"],
        "bass": ["acoustic_bass", "fretless_bass", "finger_bass"],
        "arp": ["vibraphone", "celesta", "harp"],
        "counter": ["flute", "clarinet", "strings"],
        "riff": ["rhodes", "vibraphone", "nylon_guitar"],
    },
    "rootless": True, "spread": True, "reverb": 0.5, "delay": 0.14, "chorus": True,
    "vocal_preset": "soul",
}
PACKS["piano_ballad"] = {
    "title": "Piano ballad",
    "describe": "slow ballad: piano, strings that build, soft drums coming in later, big final chorus",
    "bpm": (66, 78), "swing": 0.5, "ext": ["triad", "seventh"], "tension": 0.5,
    "borrowed": ["iv", "bVII", "V/vi"], "harmonic_rhythm": [1, 2],
    "favourites": [["I", "V", "vi", "IV"], ["vi", "IV", "I", "V"], ["IV", "V", "iii", "vi"]],
    "kit": ["standard", "room", "brush"],
    "drums": [{"kick": "x.......x.x.....", "snare": "....x.......x...", "hat": "x.x.x.x.x.x.x.x."},
              {"kick": "x...............", "rim": "....x.......x...", "hat": "x...x...x...x..."}],
    "bass": [[(0, 8, "R"), (8, 8, "5")], [(0, 12, "R"), (12, 4, "A")]],
    "comp_rhythm": [[(0, 4), (4, 4), (8, 4), (12, 4)], [(0, 8), (8, 8)]],
    "roles": {
        "lead": ["piano", "violin", "flute", "cello", "bright_piano"],
        "comp": ["piano", "electric_grand", "bright_piano"],
        "pad": ["slow_strings", "strings", "choir_pad"],
        "bass": ["fretless_bass", "finger_bass", "cello"],
        "arp": ["piano", "harp", "celesta"],
        "counter": ["cello", "violin", "french_horn"],
        "riff": ["piano", "celesta", "harp"],
    },
    "rootless": False, "spread": True, "reverb": 0.7, "delay": 0.15, "chorus": False,
    "vocal_preset": "cinematic",
}
PACKS["boss_choir"] = {
    "title": "Choir boss",
    "describe": "big story-boss theme: choir, staccato strings, brass, timpani and heavy drums, minor key",
    "bpm": (138, 150), "swing": 0.5, "ext": ["triad"], "tension": 0.6,
    "borrowed": ["bVI", "bVII", "V7", "bII"], "harmonic_rhythm": [1, 2],
    "favourites": [["i", "bVI", "bVII", "V"], ["i", "bII", "i", "V"], ["bVI", "bVII", "i", "i"]],
    "kit": ["power", "orchestra", "room"],
    "drums": [{"kick": "x.x...x.x.x...x.", "snare": "....X.......X...", "hat": "x.x.x.x.x.x.x.x.", "tom_lo": "..............x."},
              {"kick": "x...x...x...x...", "snare": "....X.......X..X", "ride": "x.x.x.x.x.x.x.x."}],
    "bass": [[(i * 2, 2, "R") for i in range(8)], [(0, 3, "R"), (3, 3, "R"), (6, 2, "8"), (8, 3, "R"), (11, 3, "R"), (14, 2, "5")]],
    "comp_rhythm": [[(i * 2, 1) for i in range(8)], [(0, 3), (3, 3), (6, 2), (8, 3), (11, 3), (14, 2)]],
    "roles": {
        "lead": ["brass_section", "french_horn", "strings", "trumpet", "choir"],
        "comp": ["strings", "brass_section", "tremolo_strings"],
        "pad": ["choir", "choir_pad", "slow_strings"],
        "bass": ["contrabass", "synth_bass", "pick_bass"],
        "arp": ["pizzicato", "harp", "tubular_bells"],
        "counter": ["french_horn", "cello", "brass_section"],
        "riff": ["brass_section", "strings", "orchestra_hit"],
    },
    "rootless": False, "spread": False, "reverb": 0.6, "delay": 0.08, "chorus": False, "drive": False,
    "vocal_preset": "cinematic",
}

# Sampled and synthesised instruments (arrange/instruments.py, docs/PERSONA_PRODUCTION.md §1). Bank -1 marks
# them; the program is their General MIDI cousin, used for MIDI export and when a library isn't installed.
def _register_sampled() -> None:
    from .instruments import KITS as SAMPLED_KITS, SAMPLED, SFX, SYNTH_KEYS

    for key, spec in SAMPLED.items():
        gm = INSTRUMENTS[spec["gm"]]
        lo, hi = spec["range"]
        INSTRUMENTS[key] = (-1, gm[1], lo, hi, spec["family"], 1.0)
    organ = INSTRUMENTS["drawbar_organ"]
    for key, (kind, _) in SYNTH_KEYS.items():
        INSTRUMENTS[key] = (-1, organ[1] if kind == "organ" else 81, 24, 96, "keys" if kind == "organ" else "synth", 1.0)
    for key, spec in SAMPLED_KITS.items():
        KITS[key[4:]] = KITS[spec["gm"][4:]]
    for key in SFX:
        INSTRUMENTS[key] = (-1, 119, 0, 127, "fx", 1.0)


_register_sampled()

# The hand-produced Persona 5 / Persona 3 Reload band (studio/last_train.py, docs/PERSONA_PRODUCTION.md).
PACKS["persona_acid_jazz"] = dict(PACKS["heist_funk"]) | {
    "title": "Persona acid jazz",
    "describe": "Persona 5 acid-jazz band with a P3R rap pocket: finger bass, Rhodes, live kit with congas and "
                "triangle, B3 organ, strings and brass in the choruses, clean guitars left and right",
    "reverb": 0.4, "delay": 0.08, "drive": False, "vocal_preset": "soul", "match_tone": True,
}
