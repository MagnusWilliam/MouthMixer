"""Starter beats: the backing you hum over. Each one sets the tempo, key and two chord loops (A for most of
the song, B for the bridge) and comes with a few ready-made parts (beat, bass, chords, pad) you can keep,
swap, or replace with your own recordings.

They take Persona's genre traits (docs/PERSONA_STYLE.md: acid-jazz and funk grooves, organ and slap bass,
minor-key battle loops around 120-135 BPM, laid-back night hip-hop) and none of its fingerprints: the
loops are common progressions and the parts are generated from the style's rules, not from any song.
"""

from __future__ import annotations

from ..arrange import arranger, theory
from ..arrange.styles import PACKS

# mood -> what it's for, in game terms
MOODS = {
    "battle": {"label": "Battle", "hint": "fights and chases: driving, funky, minor key"},
    "daily": {"label": "Daily life", "hint": "school, town, hanging out: bright, easy groove"},
    "night": {"label": "Night / exploring", "hint": "walking the city at night: laid-back, a little lonely"},
    "dungeon": {"label": "Dungeon / tense", "hint": "danger nearby: dark, pulsing, sparse"},
    "boss": {"label": "Boss", "hint": "the big fight: loud rock, fast, heavy"},
}

# Two starters per mood. favourite loops are roman numerals (arranger.resolve_degree).
STARTERS = {
    "battle_funk": {"mood": "battle", "pack": "heist_funk", "bpm": 126, "tonic": 2, "mode": "minor", "ext": "ninth",
                    "a": ["i", "bVI", "bVII", "i"], "b": ["iv", "bVII", "bIII", "V"], "cell": 0, "drums": 0,
                    "describe": "acid-jazz funk at 126 BPM in D minor: organ chords, slap bass, breakbeat"},
    "battle_jazz": {"mood": "battle", "pack": "heist_funk", "bpm": 132, "tonic": 7, "mode": "minor", "ext": "seventh",
                    "a": ["i", "iv", "bVII", "bIII"], "b": ["bVI", "bVII", "i", "i"], "cell": 1, "drums": 1,
                    "describe": "faster jazz-funk at 132 BPM in G minor, busy 16th hats"},
    "daily_citypop": {"mood": "daily", "pack": "city_pop_day", "bpm": 98, "tonic": 5, "mode": "major", "ext": "seventh",
                      "a": ["IV", "V", "iii", "vi"], "b": ["ii", "V", "I", "vi"], "cell": 0, "drums": 0,
                      "describe": "city pop at 98 BPM in F major: Rhodes, finger bass, light swing"},
    "daily_poprock": {"mood": "daily", "pack": "bright_pop_rock", "bpm": 136, "tonic": 0, "mode": "major",
                      "ext": "triad", "a": ["I", "V", "vi", "IV"], "b": ["vi", "IV", "V", "V"], "cell": 0, "drums": 0,
                      "describe": "upbeat pop-rock at 136 BPM in C major: piano, pick bass, open hats"},
    "night_hiphop": {"mood": "night", "pack": "moonlit_hiphop", "bpm": 88, "tonic": 7, "mode": "minor", "ext": "seventh",
                     "a": ["i", "bVI", "bIII", "bVII"], "b": ["iv", "bVI", "V", "V"], "cell": 0, "drums": 0,
                     "describe": "night hip-hop at 88 BPM in G minor: piano, strings, boom-bap"},
    "night_neosoul": {"mood": "night", "pack": "neon_night", "bpm": 84, "tonic": 9, "mode": "minor", "ext": "ninth",
                      "a": ["i", "iv", "bVII", "bIII"], "b": ["bVI", "bVII", "i", "i"], "cell": 0, "drums": 0,
                      "describe": "neo-soul at 84 BPM in A minor: minor 9ths, Wurlitzer-ish keys, swing"},
    "dungeon_pulse": {"mood": "dungeon", "pack": "tense_dungeon", "bpm": 104, "tonic": 4, "mode": "minor", "ext": "triad",
                      "a": ["i", "bII", "i", "bVII"], "b": ["iv", "bVI", "bII", "V"], "cell": 0, "drums": 0,
                      "describe": "tense pulse at 104 BPM in E minor with a dark flat-2 chord"},
    "dungeon_creep": {"mood": "dungeon", "pack": "tense_dungeon", "bpm": 108, "tonic": 0, "mode": "minor",
                      "ext": "seventh", "a": ["i", "iv", "i", "bVI"], "b": ["bII", "bVII", "i", "V"], "cell": 1,
                      "drums": 1, "describe": "creeping groove at 108 BPM in C minor, claps and bells"},
    "boss_rock": {"mood": "boss", "pack": "boss_rock", "bpm": 152, "tonic": 11, "mode": "minor", "ext": "triad",
                  "a": ["i", "bVI", "bVII", "i"], "b": ["bVI", "bVII", "i", "V"], "cell": 0, "drums": 0,
                  "describe": "rock boss at 152 BPM in B minor: distorted guitar, driving 8th bass"},
    "boss_brass": {"mood": "boss", "pack": "boss_rock", "bpm": 148, "tonic": 4, "mode": "minor", "ext": "triad",
                   "a": ["i", "bVII", "bVI", "V"], "b": ["bVI", "bVII", "i", "i"], "cell": 1, "drums": 1,
                   "describe": "brassy rock boss at 148 BPM in E minor, four-on-the-floor kick"},
}


def public() -> list[dict]:
    out = []
    for sid, s in STARTERS.items():
        out.append({"id": sid, "mood": s["mood"], "mood_label": MOODS[s["mood"]]["label"],
                    "mood_hint": MOODS[s["mood"]]["hint"], "style": PACKS[s["pack"]]["title"], "bpm": s["bpm"],
                    "key": f"{theory.NAMES[s['tonic']]} {s['mode']}", "describe": s["describe"]})
    return out


def progression(degrees: list[str], tonic: int, ext: str, bars: int, start_bar: int = 0) -> list:
    """[(start_beat, length, Chord)] for `bars` bars, one chord per bar, looping the degrees."""
    chords = [arranger.resolve_degree(d, tonic, ext) for d in degrees]
    return [((start_bar + i) * 4, 4, chords[i % len(chords)]) for i in range(bars)]


def instrument_for(pack_name: str, role: str, index: int = 0) -> str:
    roles = PACKS[pack_name]["roles"]
    opts = roles.get(role) or roles.get("comp")
    return opts[index % len(opts)]


def starter_parts(starter: dict) -> list[dict]:
    """The ready-made pieces a starter comes with. They are generated per section (`gen`), so they follow
    whatever chords that section uses."""
    pack = PACKS[starter["pack"]]
    kit = "kit:" + pack["kit"][0]
    return [
        {"slot": "beat", "name": "Starter beat", "gen": "drums", "instrument": kit},
        {"slot": "bass", "name": "Starter bass", "gen": "bass", "instrument": instrument_for(starter["pack"], "bass")},
        {"slot": "chords", "name": "Starter chords", "gen": "comp", "instrument": instrument_for(starter["pack"], "comp")},
        {"slot": "pad", "name": "Starter pad", "gen": "pad", "instrument": instrument_for(starter["pack"], "pad")},
    ]


def generate(gen: str, starter: dict, chords: list, bars_range: tuple, *, fills: bool = False,
             light: bool = False, melody: list | None = None, rng=None) -> list[tuple]:
    """Notes for a generated starter part over `chords` in `bars_range` (absolute bars)."""
    import numpy as np

    rng = rng if rng is not None else np.random.default_rng(0)
    pack = PACKS[starter["pack"]]
    swing = pack["swing"]
    if gen == "drums":
        pat = pack["drums"][starter.get("drums", 0) % len(pack["drums"])]
        return arranger.drum_part(pat, bars_range, swing, fill_last=fills, crash_first=fills,
                                  variant="light" if light else "full", rng=rng)
    if gen == "bass":
        cell = pack["bass"][starter.get("cell", 0) % len(pack["bass"])]
        return arranger.bass_part(chords, bars_range, cell, swing, rng)
    if gen == "comp":
        rhythm = pack["comp_rhythm"][starter.get("cell", 0) % len(pack["comp_rhythm"])]
        return arranger.comp_part(chords, bars_range, rhythm, swing, 52, 77, pack["rootless"], pack["spread"],
                                  vel=64 if light else 76, melody=melody)
    if gen == "pad":
        return arranger.pad_part(chords, bars_range, 55, 79, pack["spread"], melody=melody)
    raise ValueError(gen)
