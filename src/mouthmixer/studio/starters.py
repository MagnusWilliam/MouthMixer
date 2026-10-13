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
    "rain": {"label": "Rainy day", "hint": "soft and gentle: bossa nova, brushes, nylon guitar"},
    "ending": {"label": "Ending / ballad", "hint": "slow and emotional: piano and strings that build"},
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
    "battle_rush": {"mood": "battle", "pack": "acid_jazz_battle", "bpm": 156, "tonic": 9, "mode": "minor", "ext": "seventh",
                    "a": ["i", "bVI", "bVII", "V"], "b": ["iv", "bVII", "bIII", "V"], "cell": 1, "drums": 0,
                    "describe": "fast jazz-rock battle at 156 BPM in A minor: breakbeat, brass, driven guitar"},
    "night_jazz": {"mood": "night", "pack": "neon_night", "bpm": 80, "tonic": 5, "mode": "minor", "ext": "ninth",
                   "a": ["i", "iv", "bVII", "bIII"], "b": ["bVI", "bVII", "i", "V"], "cell": 1, "drums": 1,
                   "kit": "brush", "lead": "tenor_sax",
                   "describe": "moody night jazz at 80 BPM in F minor: brushes, Rhodes, tenor sax"},
    "rain_bossa": {"mood": "rain", "pack": "rain_bossa", "bpm": 132, "tonic": 7, "mode": "major", "ext": "seventh",
                   "a": ["IV", "iii", "ii", "V"], "b": ["ii", "V", "I", "vi"], "cell": 0, "drums": 0,
                   "describe": "soft bossa nova at 132 BPM in G major: nylon guitar, brushes, flute"},
    "ending_ballad": {"mood": "ending", "pack": "piano_ballad", "bpm": 72, "tonic": 2, "mode": "major", "ext": "triad",
                      "a": ["I", "V", "vi", "IV"], "b": ["vi", "IV", "I", "V"], "cell": 0, "drums": 1,
                      "describe": "piano ballad at 72 BPM in D major: piano, strings, soft drums"},
    "boss_choir": {"mood": "boss", "pack": "boss_choir", "bpm": 144, "tonic": 2, "mode": "minor", "ext": "triad",
                   "a": ["i", "bVI", "bVII", "V"], "b": ["i", "bII", "i", "V"], "cell": 0, "drums": 0,
                   "describe": "dramatic story boss at 144 BPM in D minor: choir, staccato strings, timpani"},
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


FEELS = {
    "intro": "Building intro (instruments come in one by one, hits at the end)",
    "big_intro": "Big intro (the full band straight away)",
    "verse": "Verse (the groove)",
    "pre": "Build-up (pre-chorus)",
    "lift": "Chorus lift (bigger, brighter)",
    "rap": "Rap pocket (half-time hip-hop)",
    "breakdown": "Breakdown (drums out)",
    "final": "Final chorus (the biggest)",
    "outro": "Outro (fades down)",
    "hits_end": "Big ending (three hits, then silence)",
}


def feel_for(name: str, is_last_hook: bool = False) -> str:
    """A sensible feel from a section's name."""
    n = name.lower().strip()
    if n.startswith("intro"):
        return "intro"
    if n.startswith(("outro", "ending")):
        return "outro"
    if n.startswith(("pre", "build")) or "build" in n:
        return "pre"
    if n.startswith("rap"):
        return "rap"
    if n.startswith(("bridge", "break")):
        return "breakdown"
    if n.startswith("final") or ((n.startswith(("hook", "chorus"))) and is_last_hook):
        return "final"
    if n.startswith(("hook", "chorus")):
        return "lift"
    return "verse"


def starter_parts(starter: dict) -> list[dict]:
    """The ready-made pieces a starter comes with. They are generated per section (`gen`) and follow that
    section's chords and feel (a chorus lifts, a rap verse drops into a half-time pocket...)."""
    pack = PACKS[starter["pack"]]
    kit = "kit:" + starter.get("kit", pack["kit"][0])
    return [
        {"slot": "beat", "name": "Starter beat", "gen": "drums", "instrument": kit},
        {"slot": "bass", "name": "Starter bass", "gen": "bass", "instrument": instrument_for(starter["pack"], "bass")},
        {"slot": "chords", "name": "Starter chords", "gen": "comp", "instrument": instrument_for(starter["pack"], "comp")},
        {"slot": "pad", "name": "Starter pad", "gen": "pad", "instrument": instrument_for(starter["pack"], "pad")},
        {"slot": "fx", "name": "Risers into big moments", "gen": "fx", "instrument": "reverse_cymbal"},
        {"slot": "keys", "name": "Piano for the quiet parts", "gen": "keys", "instrument": "piano"},
        {"slot": "chime", "name": "Station chime", "gen": "chime", "instrument": "tubular_bells"},
    ]


RAP_DRUMS = {"kick": "x.........x..x..", "snare": "........X.......", "hat": "x.x.x.x.x.x.x.x.", "ghost": "...........g...."}
STAB_STEPS = [0, 6, 12]  # 16th steps of the intro's hits: beat 1, the "and" of 2, beat 4


def generate(gen: str, starter: dict, chords: list, bars_range: tuple, *, fills: bool = False,
             light: bool = False, melody: list | None = None, rng=None, feel: str = "verse",
             next_feel: str | None = None) -> list[tuple]:
    """Notes for a generated starter part over `chords` in `bars_range` (absolute bars), shaped by the
    section's feel (FEELS) and, for transitions, the next section's."""
    import numpy as np

    from ..arrange.styles import DRUM

    rng = rng if rng is not None else np.random.default_rng(0)
    pack = PACKS[starter["pack"]]
    swing = pack["swing"]
    b0, b1 = bars_range
    n_bars = b1 - b0
    half = b0 + max(1, n_bars // 2) if n_bars > 2 else b0  # a short intro hits from the first beat
    if light:
        feel = "outro" if feel == "verse" else feel
    ending = feel == "hits_end"
    if feel in ("big_intro", "hits_end"):
        feel = "final"  # the full band; a big ending then stops on three hits (below)
    if ending:
        body = generate(gen, starter, chords, (b0, b1 - 1), fills=False, melody=melody, rng=rng, feel="final") \
            if n_bars > 1 and gen not in ("fx", "chime", "keys") else []
        return body + _three_hits(gen, starter, chords, b1 - 1)
    chord_at = lambda beat: next((c for s, l, c in chords if s <= beat < s + l), None)  # noqa: E731

    if gen == "drums":
        pat = dict(pack["drums"][starter.get("drums", 0) % len(pack["drums"])])
        if feel == "breakdown":
            return []
        if feel == "rap":
            return arranger.drum_part(RAP_DRUMS, bars_range, max(swing, 0.54), fill_last=fills, crash_first=True, rng=rng)
        if feel == "outro":
            return arranger.drum_part(pat, bars_range, swing, fill_last=False, crash_first=True, variant="light", rng=rng)
        if feel == "intro":
            # Instruments come in one at a time (chords, then bass, then drums at half way), then hits and a
            # snare roll in the last bar into the verse. A 2-bar intro hits from the first beat.
            last = (b1 - 1) * 4
            out = []
            if n_bars > 2:
                out += arranger.drum_part(pat, (half, b1 - 1), swing, fill_last=False, crash_first=True,
                                          variant="light", rng=rng)
            for bar in range(b1 - 1 if n_bars > 2 else b0, b1):
                for st in STAB_STEPS:
                    t = bar * 4 + st / 4
                    out += [(t, 0.3, DRUM["kick"], 116), (t, 1.0, DRUM["crash"], 100 if st == 0 else 84)]
            out = [n for n in out if n[0] < last + 2]
            out += [(last + 2 + i / 8, 0.15, DRUM["snare"], 60 + i * 7) for i in range(8)]  # 32nd-note roll, growing
            return out
        if feel == "pre":  # four-on-the-floor kick, 8th hats, the snare held back until a roll in the last bar
            build = {"kick": "x...x...x...x...", "hat": "x.x.x.x.x.x.x.x."}
            out = arranger.drum_part(build, (b0, b1 - 1), swing, fill_last=False, crash_first=False, rng=rng)
            out += arranger.drum_part(build, (b1 - 1, b1), swing, fill_last=False, crash_first=False, rng=rng)
            out += [((b1 - 1) * 4 + i / 4, 0.15, DRUM["snare"], 50 + i * 4) for i in range(16)]
            return out
        if feel in ("lift", "final"):  # open hats on the off-beats, an extra kick into each bar, crashes
            pat["open_hat"] = "..o...o...o...o."
            pat["kick"] = pat.get("kick", "x.......x.......")[:14] + "x."
            out = arranger.drum_part(pat, bars_range, swing, fill_last=fills, crash_first=True, rng=rng)
            every = 2 if feel == "final" else 4
            out += [(bar * 4, 1.0, DRUM["crash"], 96) for bar in range(b0 + every, b1, every)]
            return out
        return arranger.drum_part(pat, bars_range, swing, fill_last=fills, crash_first=fills,
                                  variant="full", rng=rng)

    if gen == "bass":
        cells = pack["bass"]
        if feel == "breakdown":
            return [(s, l - 0.1, 36 + (c.root - 36) % 12, 60) for s, l, c in chords if b0 * 4 <= s < b1 * 4]
        if feel == "intro":  # the bass comes in a quarter of the way through, then hits with the band at the end
            enter = b0 + (max(1, n_bars // 4) if n_bars > 2 else 0)
            hit_bar = b1 - 1 if n_bars > 2 else b0
            cell = cells[starter.get("cell", 0) % len(cells)]
            out = arranger.bass_part(chords, (enter, hit_bar), cell, swing, rng) if hit_bar > enter else []
            for bar in range(hit_bar, b1):
                for st in STAB_STEPS:
                    c = chord_at(bar * 4 + st / 4)
                    if c:
                        out.append((bar * 4 + st / 4, 0.5, 36 + (c.root - 36) % 12, 112))
            return out
        if feel == "rap":
            cell = [(0, 6, "R"), (10, 4, "R"), (14, 2, "A")]  # long, low, leaves room for the words
        elif feel == "pre":
            cell = [(i * 2, 2, "R") for i in range(8)]  # driving 8ths
        elif feel in ("lift", "final"):
            cell = cells[(starter.get("cell", 0) + 1) % len(cells)]
        else:
            cell = cells[starter.get("cell", 0) % len(cells)]
        if feel == "outro":
            cell = [(0, 16, "R")]
        return arranger.bass_part(chords, bars_range, cell, swing, rng)

    if gen == "comp":
        rhythms = pack["comp_rhythm"]
        lo, hi, vel = 52, 77, 76
        if feel == "intro":  # chords from the first beat, soft, then stabs with the band in the last bar
            hit_bar = b1 - 1 if n_bars > 2 else b0
            out = []
            for bar in range(hit_bar, b1):
                for st in STAB_STEPS:
                    beat = bar * 4 + st / 4
                    c = chord_at(beat)
                    if c:
                        out += [(beat, 0.45, p, 108) for p in theory.voice(c, None, 57, 82, n=4)]
            first = [x for x in chords if b0 * 4 <= x[0] < hit_bar * 4]
            return out + [(s, l - 0.05, p, 52 + 6 * ((s / 4 - b0) // 1)) for s, l, c in first
                          for p in theory.voice(c, None, 52, 74, n=3)]
        if feel in ("rap", "breakdown", "outro"):
            rhythm, vel = [(0, 16)], 54 if feel != "outro" else 60
        elif feel == "pre":
            rhythm, vel = [(i * 2, 2) for i in range(8)], 70
        elif feel in ("lift", "final"):
            rhythm, lo, hi, vel = rhythms[(starter.get("cell", 0) + 1) % len(rhythms)], 57, 82, 84
        else:
            rhythm = rhythms[starter.get("cell", 0) % len(rhythms)]
            if feel == "verse" and n_bars >= 8:  # the verse ramps up: held chords first, the rhythm half way in
                first = arranger.comp_part(chords, (b0, half), [(0, 16)], swing, lo, hi, pack["rootless"],
                                           pack["spread"], vel=56, melody=melody)
                return first + arranger.comp_part(chords, (half, b1), rhythm, swing, lo, hi, pack["rootless"],
                                                  pack["spread"], vel=vel, melody=melody)
        return arranger.comp_part(chords, bars_range, rhythm, swing, lo, hi, pack["rootless"], pack["spread"],
                                  vel=vel, melody=melody)

    if gen == "pad":
        notes = arranger.pad_part(chords, bars_range, 55, 79, pack["spread"], melody=melody)
        if feel in ("lift", "final"):  # an octave higher shimmer on top in the big sections
            notes += [(s, l, p + 12, 44) for s, l, p, v in notes if p + 12 <= 91][: len(notes) // 2]
        return notes

    if gen == "fx":  # a reverse-cymbal swell into big moments
        out = []
        if next_feel in ("lift", "final", "rap") or feel in ("pre",):
            out.append((b1 * 4 - 2, 2.0, 60, 100))
        if feel == "intro":
            out.append(((b1 - 1) * 4, 4.0, 60, 110))
        return out

    if gen == "keys":  # soft broken chords (8ths) for breakdowns: the "singer and piano" moment
        if feel not in ("breakdown",):
            return []
        out = []
        for st_, l_, c in chords:
            if not (b0 * 4 <= st_ < b1 * 4):
                continue
            tones = sorted(theory.voice(c, None, 55, 79, n=4))
            k = len(tones)
            pattern = [tones[0] - 12] + [tones[i % k] for i in (1, 2, 3, 2, 1, 2, 3)]
            out += [(st_ + i * 0.5, 0.9, p, 60 if i else 72) for i, p in enumerate(pattern) if st_ + i * 0.5 < st_ + l_]
        return out

    if gen == "chime":  # a three-note station chime: 5th, 3rd, root, ringing out
        if feel not in ("intro", "outro"):
            return []
        root = 72 + (starter["tonic"] - 72) % 12
        third = root + (3 if starter["mode"] in ("minor", "dorian") else 4)
        return [(b0 * 4, 1.0, root + 7, 92), (b0 * 4 + 1, 1.0, third, 88), (b0 * 4 + 2, 3.0, root, 96)]

    raise ValueError(gen)


def _three_hits(gen: str, starter: dict, chords: list, bar: int) -> list[tuple]:
    """A big ending: the whole band hits on beats 1, 2 and 3 of the last bar, then silence."""
    from ..arrange.styles import DRUM

    c = next((c for s, l, c in chords if s <= bar * 4 < s + l), chords[-1][2] if chords else None)
    hits = [bar * 4, bar * 4 + 1, bar * 4 + 2]
    if gen == "drums":
        return [n for t in hits for n in ((t, 0.3, DRUM["kick"], 122), (t, 1.5, DRUM["crash"], 112),
                                          (t, 0.2, DRUM["snare"], 110))]
    if c is None:
        return []
    if gen == "bass":
        root = 36 + (c.root - 36) % 12
        return [(t, 0.5 if t != hits[-1] else 2.0, root, 118) for t in hits]
    if gen in ("comp", "pad"):
        lo, hi = (57, 82) if gen == "comp" else (55, 79)
        return [(t, 0.5 if t != hits[-1] else 2.0, p, 116) for t in hits for p in theory.voice(c, None, lo, hi, n=4)]
    return []
