"""The part catalog for the mixer (Incredibox-style): every part you can add to a song, how it's written,
what it pairs well with, and which sounds ("vibes") it suits. Suggestions are ranked from this data.

The pairing and vibe tables are grounded in docs/ARRANGING.md (layer roles, register slots, rhythmic
interlock, timbre blends). Generators write notes against the song's chords and sections, so an added
part always fits the harmony and the form.
"""

from __future__ import annotations

import numpy as np

from . import arranger, theory
from .styles import DRUM, INSTRUMENTS

# --------------------------------------------------------------------------------------------------
# Vibes: what kind of sound the user is going for
# --------------------------------------------------------------------------------------------------

VIBES = {
    "groovy": "Funky & groovy", "jazzy": "Smooth & jazzy", "chill": "Chill / lo-fi", "epic": "Epic & cinematic",
    "battle": "Energetic battle", "cozy": "Cozy & whimsical", "dreamy": "Dreamy & ambient", "dark": "Dark & mysterious",
    "sad": "Sad & emotional", "retro": "Retro / arcade", "tropical": "Tropical & sunny", "eerie": "Eerie",
}
PACK_VIBES = {
    "city_pop_day": ["groovy", "jazzy", "cozy"], "neon_night": ["chill", "jazzy", "sad"],
    "acid_jazz_battle": ["battle", "groovy", "jazzy"], "orchestral_adventure": ["epic", "sad"],
    "arcade": ["retro", "battle"], "dream_ambient": ["dreamy", "cozy", "sad"],
    "heist_funk": ["groovy", "jazzy", "battle"], "bright_pop_rock": ["groovy", "battle", "cozy"],
    "moonlit_hiphop": ["chill", "dark", "sad"],
}

# --------------------------------------------------------------------------------------------------
# Part types
# --------------------------------------------------------------------------------------------------
# role: mixing role (level, effects); cat: drawer category; gen: generator; plays: where in the form;
# sounds: instrument choices (first = default); vibes: what it suits; pairs: parts/instruments it
# complements (with the reason shown to the user); fills: the musical space it occupies.

CATEGORIES = ["Beats", "Percussion", "Bass", "Chords", "Pads", "Plucks & arps", "Riffs & hooks",
              "Counter-melodies", "Layers on your melody", "Transitions", "Ambience"]

PARTS: dict[str, dict] = {}


def _part(pid, label, cat, role, gen, sounds, vibes, fills, plays="main", **kw):
    PARTS[pid] = {"id": pid, "label": label, "cat": cat, "role": role, "gen": gen, "sounds": sounds,
                  "vibes": vibes, "fills": fills, "plays": plays, **kw}


# Beats (drum kits). Grids: 16 steps per bar; X accent, x normal, g ghost.
BEATS = {
    "boom_bap": {"kick": "x......x..x.....", "snare": "....x.......x...", "hat": "x.x.x.x.x.x.x.x.", "ghost": "..g........g...."},
    "four_floor": {"kick": "x...x...x...x...", "clap": "....x.......x...", "hat": "..x...x...x...x.", "open_hat": "..o...o...o...o."},
    "breakbeat": {"kick": "x.x.......x.....", "snare": "....X..g.g..X...", "hat": "x.x.x.x.x.x.x.x."},
    "funk_16": {"kick": "x..x..x...x..x..", "snare": "....X.......X...", "ghost": "..g..g.g..g..g.g", "hat": "xxxxxxxxxxxxxxxx"},
    "trap": {"kick": "x......x..x.....", "clap": "........X.......", "hat": "x.xxx.x.xxxxx.xx"},
    "half_time": {"kick": "x.........x.....", "snare": "........X.......", "hat": "x.x.x.x.x.x.x.x."},
    "disco": {"kick": "x...x...x...x...", "snare": "....x.......x...", "open_hat": "..o...o...o...o.", "hat": "x.x.x.x.x.x.x.x."},
    "shuffle": {"kick": "x.....x.x.......", "snare": "....x.......x...", "hat": "x..xx..xx..xx..x"},
    "bossa": {"kick": "x..x..x.x..x..x.", "rim": "..x..x....x..x..", "hat": "xxxxxxxxxxxxxxxx"},
    "dembow": {"kick": "x...x...x...x...", "snare": "...x..x....x..x."},
    "march": {"snare": "x.xxx.x.x.xxx.x.", "concert_bd": "x.......x......."},
    "brush_swing": {"ride": "x..x.x..x..x.x..", "kick": "x.......x.......", "pedal_hat": "....x.......x..."},
}
for name, kits, vibes, label in [
    ("boom_bap", ["standard", "room", "jazz"], ["chill", "groovy", "dark"], "Boom-bap beat"),
    ("four_floor", ["dance", "electronic", "standard"], ["groovy", "battle", "retro"], "Four-on-the-floor"),
    ("breakbeat", ["power", "room", "standard"], ["battle", "groovy"], "Breakbeat"),
    ("funk_16", ["power", "standard"], ["groovy", "battle", "jazzy"], "Funk 16ths"),
    ("trap", ["tr808", "electronic"], ["dark", "battle", "chill"], "Trap hats"),
    ("half_time", ["room", "power"], ["epic", "sad", "dark"], "Half-time (heavy)"),
    ("disco", ["standard", "dance"], ["groovy", "cozy"], "Disco"),
    ("shuffle", ["jazz", "standard"], ["cozy", "jazzy"], "Shuffle"),
    ("bossa", ["jazz", "brush"], ["tropical", "jazzy", "cozy"], "Bossa nova"),
    ("dembow", ["electronic", "dance"], ["tropical", "groovy"], "Reggaeton-style"),
    ("march", ["orchestra"], ["epic"], "Orchestral march"),
    ("brush_swing", ["brush", "jazz"], ["jazzy", "chill", "cozy"], "Brushed swing"),
]:
    _part(f"beat_{name}", label, "Beats", "drums", "beat", [f"kit:{k}" for k in kits], vibes, ["rhythm", "low"],
          pattern=name, replaces="drums")

PERC = {
    "shaker": ("maracas", "xgxgxgxgxgxgxgxg", ["cozy", "tropical", "chill", "groovy"], "Shaker 16ths"),
    "tambourine": ("tambourine", "....x.......x...", ["groovy", "cozy"], "Tambourine on 2 & 4"),
    "congas": ("hi_conga", "..x.x..x..x.x..x", ["tropical", "groovy", "jazzy"], "Congas"),
    "bongos": ("hi_bongo", "x.xx..x.x.xx..x.", ["tropical", "cozy"], "Bongos"),
    "claves": ("claves", "x..x..x...x.x...", ["tropical", "jazzy"], "Claves (3-2 clave)"),
    "cowbell": ("cowbell", "x...x...x...x...", ["groovy", "battle"], "Cowbell"),
    "triangle": ("triangle", "x.......x.......", ["cozy", "dreamy"], "Triangle"),
    "woodblock": ("hi_wood", "..x...x...x...x.", ["cozy", "retro"], "Woodblock"),
    "cabasa": ("cabasa", "x.x.x.x.x.x.x.x.", ["chill", "tropical"], "Cabasa"),
}
for name, (note, row, vibes, label) in PERC.items():
    _part(f"perc_{name}", label, "Percussion", "perc", "perc", ["kit:standard"], vibes, ["rhythm", "high"],
          note=note, row=row)
_part("perc_taiko", "Taiko hits", "Percussion", "perc", "taiko", ["taiko"], ["epic", "battle", "dark"], ["rhythm", "low"])
_part("perc_timpani", "Timpani swells", "Percussion", "timpani", "timpani", ["timpani"], ["epic", "dark"], ["low"])

for name, label, sounds, cell, vibes in [
    ("bass_groove", "Groove bass", ["finger_bass", "pick_bass", "fretless_bass"],
     [(0, 3, "R"), (3, 1, "8"), (6, 2, "R"), (8, 3, "5"), (11, 1, "8"), (14, 2, "A")], ["groovy", "jazzy", "cozy"]),
    ("bass_slap", "Slap bass octaves", ["slap_bass", "funk_guitar"],
     [(0, 1, "R"), (2, 1, "8"), (4, 1, "R"), (6, 1, "8"), (8, 1, "R"), (10, 1, "8"), (12, 1, "R"), (14, 2, "A")],
     ["groovy", "battle"]),
    ("bass_walk", "Walking bass", ["acoustic_bass", "fretless_bass"],
     [(0, 4, "R"), (4, 4, "3"), (8, 4, "5"), (12, 4, "A")], ["jazzy", "cozy"]),
    ("bass_sub", "Deep sub bass", ["synth_bass", "sine_lead", "fm_bass"], [(0, 12, "R"), (12, 4, "5")], ["chill", "dark", "sad"]),
    ("bass_synth", "Synth bass (8ths)", ["acid_bass", "techno_bass", "pulse_bass", "synth_bass"],
     [(i * 2, 1, "R" if i % 2 == 0 else "8") for i in range(8)], ["retro", "battle", "groovy"]),
    ("bass_orchestral", "Orchestral low strings", ["contrabass", "cello", "tuba", "bassoon"], [(0, 8, "R"), (8, 8, "5")],
     ["epic", "sad", "dark"]),
]:
    _part(name, label, "Bass", "bass", "bass", sounds, vibes, ["low"], cell=cell, replaces="bass")

for name, label, sounds, rhythm, vibes, kw in [
    ("chords_rhodes", "Rhodes chords", ["rhodes", "chorus_rhodes", "bell_rhodes", "fm_piano"],
     [(0, 6), (6, 4), (10, 6)], ["jazzy", "chill", "groovy"], {"rootless": True}),
    ("chords_piano", "Piano chords", ["piano", "bright_piano", "electric_grand"], [(0, 8), (8, 8)],
     ["sad", "epic", "cozy"], {}),
    ("chords_stabs", "Funky stabs", ["clavinet", "rhodes", "brass_section", "saw_stab"],
     [(0, 1), (3, 1), (6, 1), (10, 2), (13, 1)], ["groovy", "battle"], {}),
    ("chords_guitar", "Guitar strums", ["steel_guitar", "nylon_guitar", "twelve_string", "ukulele"],
     [(0, 2), (2, 2), (4, 2), (6, 2), (8, 2), (10, 2), (12, 2), (14, 2)], ["cozy", "tropical", "sad"], {}),
    ("chords_skank", "Off-beat chops", ["funk_guitar", "clean_guitar", "rock_organ", "muted_guitar"],
     [(2, 1), (6, 1), (10, 1), (14, 1)], ["groovy", "tropical", "retro"], {}),
    ("chords_organ", "Organ", ["drawbar_organ", "rock_organ", "church_organ"], [(0, 16)], ["groovy", "dark", "epic"], {}),
]:
    _part(name, label, "Chords", "comp", "comp", sounds, vibes, ["mid"], rhythm=rhythm, **kw)

for name, label, sounds, vibes in [
    ("pad_warm", "Warm pad", ["warm_pad", "solar_wind", "new_age_pad"], ["chill", "dreamy", "cozy"]),
    ("pad_strings", "String section", ["strings", "slow_strings", "tremolo_strings", "orchestra_pad"], ["epic", "sad", "cozy"]),
    ("pad_choir", "Choir", ["choir", "voice_oohs", "choir_pad"], ["epic", "dark", "dreamy"]),
    ("pad_glass", "Glassy pad", ["halo_pad", "bowed_pad", "crystal", "night_vision"], ["dreamy", "eerie", "sad"]),
    ("pad_mystery", "Mystery pad", ["mystery_pad", "atmosphere", "soundtrack_pad", "ice_rain"], ["dark", "eerie", "dreamy"]),
    ("pad_synth", "Synth strings", ["synth_strings", "polysynth", "bright_saw_stack"], ["retro", "battle", "groovy"]),
]:
    _part(name, label, "Pads", "pad", "pad", sounds, vibes, ["mid", "sustain"])

for name, label, sounds, fast, vibes in [
    ("arp_harp", "Harp arpeggio", ["harp", "koto", "taisho_koto"], False, ["dreamy", "epic", "cozy"]),
    ("arp_bells", "Bell sparkle", ["celesta", "glockenspiel", "music_box", "tinker_bell", "synth_chime"], False,
     ["cozy", "dreamy", "eerie"]),
    ("arp_mallet", "Mallets", ["marimba", "vibraphone", "synth_mallet", "kalimba", "steel_drums"], False,
     ["tropical", "cozy", "jazzy"]),
    ("arp_pluck", "Pluck arpeggio (16ths)", ["pizzicato", "harp", "synth_mallet", "clean_guitar"], True,
     ["battle", "epic", "retro"]),
    ("arp_chip", "Chip arpeggio", ["square_lead", "chiff_lead", "calliope"], True, ["retro"]),
    ("arp_world", "World pluck", ["sitar", "shamisen", "koto", "mandolin", "banjo", "dulcimer"], False,
     ["cozy", "tropical", "eerie"]),
]:
    _part(name, label, "Plucks & arps", "arp", "arp", sounds, vibes, ["high", "rhythm"], fast=fast)

for name, label, sounds, vibes in [
    ("riff_keys", "Keyboard riff (catchy hook)", ["rhodes", "chorus_rhodes", "clavinet", "piano", "bell_piano"],
     ["groovy", "jazzy", "battle"]),
    ("riff_brass", "Brass hook", ["brass_section", "trumpet", "brass_section_2", "synth_brass_3"], ["battle", "groovy", "epic"]),
    ("riff_guitar", "Guitar riff", ["overdrive_guitar", "funk_guitar", "clean_guitar"], ["battle", "groovy"]),
    ("riff_synth", "Synth hook", ["saw_lead", "doctor_solo", "square_lead", "bright_saw_stack"], ["retro", "battle"]),
]:
    _part(name, label, "Riffs & hooks", "riff", "riff", sounds, vibes, ["mid", "rhythm"])

for name, label, sounds, gen, vibes in [
    ("counter_guide", "Smooth counter-line", ["flute", "clarinet", "cello", "french_horn", "oboe"], "counter",
     ["epic", "sad", "jazzy", "cozy"]),
    ("counter_answer", "Answer phrases (call & response)", ["muted_trumpet", "flute", "vibraphone", "trumpet",
                                                           "whistling", "harmonica"], "answer", ["groovy", "jazzy", "cozy"]),
    ("counter_high", "High strings line", ["violin", "fiddle", "strings"], "counter_high", ["epic", "sad"]),
]:
    _part(name, label, "Counter-melodies", "counter", gen, sounds, vibes, ["high"])

for name, label, sounds, shift, vibes in [
    ("double_octave_up", "Octave-up double (sparkle)", ["flute", "glockenspiel", "celesta", "piccolo", "violin"], 12,
     ["cozy", "dreamy", "epic"]),
    ("double_unison", "Unison double (thicker)", ["strings", "voice_oohs", "muted_trumpet", "synth_mallet"], 0,
     ["epic", "jazzy", "groovy"]),
    ("double_octave_down", "Octave-down double (weight)", ["cello", "french_horn", "bassoon", "trombone"], -12,
     ["epic", "dark", "sad"]),
]:
    _part(name, label, "Layers on your melody", "counter", "double", sounds, vibes, ["mid"], shift=shift)

_part("fx_riser", "Reverse-cymbal swells into sections", "Transitions", "fx", "riser", ["reverse_cymbal"],
      ["battle", "epic", "groovy", "retro"], ["fx"])
_part("fx_hits", "Impact hits on section starts", "Transitions", "fx", "hits", ["orchestra_hit", "taiko", "timpani"],
      ["epic", "battle"], ["fx", "low"])
_part("fx_crash_fills", "Crashes & tom fills", "Transitions", "perc", "fills", ["kit:standard"], ["battle", "epic", "groovy"],
      ["fx"])
for name, label, sound, vibes in [
    ("amb_vinyl", "Vinyl crackle", "fx:vinyl", ["chill", "sad", "jazzy"]),
    ("amb_rain", "Rain", "fx:rain", ["chill", "sad", "dreamy"]),
    ("amb_wind", "Wind", "fx:wind", ["eerie", "dark", "epic"]),
    ("amb_tape", "Tape hiss", "fx:tape", ["chill", "retro"]),
]:
    _part(name, label, "Ambience", "fx", "texture", [sound], vibes, ["fx"])
for name, label, sound, vibes in [
    ("amb_birds", "Birds", "birds", ["cozy", "dreamy"]), ("amb_stream", "Stream", "stream", ["cozy", "dreamy"]),
    ("amb_chimes", "Wind chimes", "windchime", ["dreamy", "eerie", "cozy"]),
    ("amb_waves", "Sea waves", "seashore", ["tropical", "chill", "dreamy"]),
    ("amb_train", "Passing train", "train", ["chill", "sad", "dark"]),
]:
    _part(name, label, "Ambience", "fx", "sfx_notes", [sound], vibes, ["fx"])

# Good pairings (timbre blend / contrast / interlock). Each: (a, b, why). a and b match part ids, part-id
# prefixes ("beat_", "arp_") or instrument names. Grounded in docs/ARRANGING.md §4.
PAIRS = [
    ("rhodes", "muted_trumpet", "Rhodes and muted trumpet: the classic soft jazz blend, warm and airy"),
    ("chords_rhodes", "bass_groove", "Rhodes comping sits right on top of a round finger bass"),
    ("chords_stabs", "beat_funk_16", "short stabs leave room between busy 16th-note drums"),
    ("chords_skank", "bass_slap", "off-beat chops answer the slap bass on the beat: they interlock"),
    ("riff_brass", "chords_skank", "brass hooks over funky guitar chops: big-band funk"),
    ("riff_keys", "bass_groove", "a keyboard riff locked to the bass makes the hook stick"),
    ("pad_strings", "arp_harp", "harp arpeggios over strings: the cinematic pair"),
    ("pad_strings", "chords_piano", "piano and strings: the emotional ballad pair"),
    ("pad_warm", "arp_bells", "bells sparkle above a warm pad without fighting it"),
    ("pad_glass", "arp_bells", "glassy pad + bells: dreamy, wide and high"),
    ("pad_choir", "perc_taiko", "choir + taiko: epic weight"),
    ("pad_choir", "perc_timpani", "choir + timpani: epic weight"),
    ("chords_guitar", "perc_shaker", "acoustic strums + shaker: cozy campfire groove"),
    ("arp_mallet", "perc_congas", "marimba and congas: tropical warmth"),
    ("beat_trap", "bass_sub", "trap hats and a long sub bass: modern and dark"),
    ("beat_boom_bap", "amb_vinyl", "boom-bap and vinyl crackle: lo-fi"),
    ("beat_boom_bap", "chords_rhodes", "boom-bap under Rhodes: neo-soul"),
    ("beat_four_floor", "bass_synth", "four-on-the-floor with an 8th-note synth bass: drives forward"),
    ("beat_disco", "chords_skank", "disco drums with off-beat guitar chops"),
    ("beat_bossa", "chords_guitar", "bossa rhythm with nylon guitar strums"),
    ("beat_march", "pad_strings", "march snare under strings: heroic"),
    ("beat_brush_swing", "bass_walk", "brushes + walking bass: the jazz trio sound"),
    ("arp_pluck", "pad_synth", "16th-note plucks over held synth strings: energy without clutter"),
    ("arp_chip", "bass_synth", "chip arpeggios over a synth bass: arcade"),
    ("counter_answer", "lead", "answer phrases fill the gaps in your melody (call and response)"),
    ("counter_guide", "pad_strings", "a slow counter-line moves while the strings hold"),
    ("double_octave_up", "lead", "an octave-up double makes your melody shimmer"),
    ("double_octave_down", "lead", "an octave-down double gives your melody weight"),
    ("fx_riser", "fx_hits", "swells into hits: big section changes"),
    ("fx_riser", "beat_", "swells lead the drums into each new section"),
    ("amb_rain", "pad_warm", "rain under a warm pad: cozy-sad"),
    ("perc_tambourine", "beat_", "tambourine on 2 and 4 tops up any backbeat"),
    ("perc_shaker", "beat_", "a shaker adds 16th-note motion over a sparser beat"),
    ("bass_orchestral", "pad_strings", "low strings anchor a string section"),
    ("arp_world", "perc_bongos", "world plucks with hand percussion: travel / town themes"),
    # From docs/ARRANGING.md §4 (orchestration and production research)
    ("flute", "violin", "flute with violin brightens and lifts a melody (Rimsky-Korsakov)"),
    ("french_horn", "cello", "horn and cello blend into one warm line (Rimsky-Korsakov)"),
    ("trumpet", "violin", "trumpet gives a string line a brilliant edge (Rimsky-Korsakov)"),
    ("arp_bells", "flute", "bells doubling a flute's important notes add sparkle without blurring pitch"),
    ("arp_bells", "harp", "celesta or glockenspiel over harp: the fairy-tale shimmer"),
    ("pad_warm", "arp_pluck", "short plucks over a long pad: busy against sustained"),
    ("chords_piano", "counter_high", "piano with a high string line: the sad duo, separate registers"),
    ("bass_orchestral", "piano", "cello under piano: the classic sad pairing"),
    ("arp_harp", "counter_guide", "harp arpeggios under a breathy flute line: pastoral"),
    ("arp_mallet", "steel_drums", "marimba and steel pan: tropical"),
    ("chords_guitar", "arp_bells", "ukulele strums with glockenspiel: cozy, whimsical"),
    ("pad_strings", "perc_taiko", "string ostinato with taiko: epic"),
    ("beat_four_floor", "arp_pluck", "a steady four-on-the-floor under plucks: synthwave drive"),
    ("pad_glass", "chords_piano", "a shimmering pad under soft piano: dreamy"),
    ("chords_organ", "chords_rhodes", "organ holds while keys comp: gospel and soul"),
    ("arp_mallet", "bass_walk", "vibraphone over walking bass: smooth jazz, noir"),
    ("riff_guitar", "bass_synth", "a driven riff doubled by synth bass: battle energy"),
    ("perc_tambourine", "beat_boom_bap", "tambourine on 2 and 4 brightens a backbeat"),
    ("beat_trap", "amb_vinyl", "trap hats with vinyl: late-night lo-fi"),
    ("riff_keys", "beat_funk_16", "a 2-bar keyboard riff over funk drums: the catchy hook"),
    ("riff_brass", "beat_breakbeat", "brass hooks over a breakbeat: big-band funk energy"),
]

# Combinations to warn about (docs/ARRANGING.md §4 "Avoid", R1.3)
AVOID = [
    ("pad_", "chords_organ", "two held chord layers in the same range: they blur together"),
    ("bass_", "bass_", "two basses at once: only one part should own the low end"),
    ("arp_bells", "lead", "bells alone can't carry a melody; use them to double one"),
]

# --------------------------------------------------------------------------------------------------
# Suggestions
# --------------------------------------------------------------------------------------------------

def _match(key: str, part_id: str, instrument: str, role: str) -> bool:
    return key == part_id or key == instrument or key == role or (key.endswith("_") and part_id.startswith(key))


def suggest(parts: list[dict], pack: str, vibe: str | None = None, limit: int = 60) -> list[dict]:
    """Rank catalog parts for this song: synergy with what's playing, the chosen vibe, and gaps in the
    arrangement (missing layers, empty registers). Each result says why."""
    active = [p for p in parts if not p.get("muted")]
    roles = {p["role"] for p in active}
    have_ids = {p.get("kind") for p in active}
    vibes = [vibe] if vibe else PACK_VIBES.get(pack, [])
    fills_now = set()
    for p in active:
        fills_now |= set(PARTS.get(p.get("kind"), {}).get("fills", []))
        fills_now |= {"low"} if p["role"] in ("bass",) else set()
        fills_now |= {"rhythm"} if p["role"] in ("drums",) else set()
    out = []
    for pid, spec in PARTS.items():
        if pid in have_ids:
            continue
        score, why = 0.0, []
        v = [x for x in spec["vibes"] if x in vibes]
        if v:
            score += 2.0 + (1.0 if vibe and vibe in spec["vibes"] else 0.0)
            why.append(f"fits the {VIBES[v[0]].lower()} sound")
        best_pair = None
        for a, b, reason in PAIRS:
            for x, y in ((a, b), (b, a)):
                if _match(x, pid, spec["sounds"][0], spec["role"]) and any(
                        _match(y, p.get("kind", ""), p["instrument"], p["role"]) for p in active):
                    best_pair = reason
        if best_pair:
            score += 2.5
            why.append(best_pair)
        gaps = [f for f in spec["fills"] if f not in fills_now and f != "fx"]
        if gaps:
            score += 0.8 * len(gaps)
            why.append({"low": "your song has nothing low yet", "high": "fills the empty high range",
                        "rhythm": "adds rhythm", "mid": "fills the middle", "sustain": "adds a held, glue-like layer"}[gaps[0]])
        if spec.get("replaces") and spec["replaces"] in roles:
            score -= 0.5
            why.append(f"swaps your current {spec['replaces']}")
        crowd = sum(1 for p in active if p["role"] == spec["role"])
        score -= 0.9 * crowd  # MUSIC_KNOWLEDGE A2: don't stack the same job
        out.append({"id": pid, "label": spec["label"], "cat": spec["cat"], "sounds": spec["sounds"],
                    "score": round(score, 2), "why": "; ".join(why[:2]) or "a different colour to try"})
    out.sort(key=lambda d: -d["score"])
    return out[:limit]


# --------------------------------------------------------------------------------------------------
# Generators: notes for a part type against the song's harmony and form
# --------------------------------------------------------------------------------------------------

def _main_bars(song) -> tuple[int, int]:
    """Bars where the full band plays (A to A'', without intro and ending)."""
    secs = song.sections
    return secs[1][1], secs[-1][1]


def _bars_for(song, plays: str) -> list[tuple[int, int]]:
    secs = {n: (s, s + b) for n, s, b in song.sections}
    if plays == "all":
        return [(0, song.bars)]
    if plays == "late":
        return [secs.get("A'", (0, 0)), secs.get("B", (0, 0)), secs.get("A''", (0, 0))]
    a, b = _main_bars(song)
    return [(a, b)]


def generate(kind: str, song, instrument: str, rng=None) -> list[tuple]:
    spec = PARTS[kind]
    rng = rng or np.random.default_rng(abs(hash(kind)) % (1 << 31))
    chords = song.chords
    sw = song.swing
    gen = spec["gen"]
    out: list[tuple] = []
    if gen == "beat":
        pat = BEATS[spec["pattern"]]
        a, b = _main_bars(song)
        out += arranger.drum_part(pat, (0, a), sw, fill_last=True, crash_first=False, variant="light", rng=rng)
        for name, s0, bars in song.sections[1:-1]:
            out += arranger.drum_part(pat, (s0, s0 + bars), sw, fill_last=True, crash_first=True, rng=rng)
        end = song.sections[-1][1] * 4
        out += [(end, 2.0, DRUM["crash"], 110), (end, 0.5, DRUM["kick"], 110)]
        return out
    if gen == "perc":
        a, b = _main_bars(song)
        for bar in range(a, b):
            for step, ch in enumerate(spec["row"]):
                if ch != ".":
                    out.append((bar * 4 + arranger.steps_to_beat(step, sw), 0.2, DRUM[spec["note"]],
                                {"X": 110, "x": 84, "g": 46}.get(ch, 80)))
        return out
    if gen == "fills":
        for name, s0, bars in song.sections[1:]:
            out.append((s0 * 4, 1.0, DRUM["crash"], 104))
            fb = s0 * 4 - 1
            if fb > 0:
                for i, n in enumerate([DRUM["tom_hi"], DRUM["tom_mid"], DRUM["tom_lo"], DRUM["snare"]]):
                    out.append((fb + i / 4, 0.2, n, 70 + 12 * i))
        return out
    if gen == "taiko":
        a, b = _main_bars(song)
        for bar in range(a, b):
            out += [(bar * 4, 1.0, 43, 110), (bar * 4 + 2.5, 0.5, 48, 80), (bar * 4 + 3, 1.0, 43, 95)]
        return out
    if gen == "timpani":
        for name, s0, bars in song.sections[1:]:
            c = song.chord_at(s0 * 4 + 1e-6)
            if c:
                root = 38 + (c.root - 38) % 12
                out += [(s0 * 4 - 1 + i / 8, 0.15, root, 50 + i * 7) for i in range(8)] + [(s0 * 4, 2.0, root, 112)]
        return out
    if gen == "bass":
        a, b = _main_bars(song)
        notes = arranger.bass_part(chords, (a, b), spec["cell"], sw, rng)
        tonic_bass = 36 + (song.tonic - 36) % 12
        notes.append((b * 4, 6.0, tonic_bass - 12 if tonic_bass > 43 else tonic_bass, 96))
        return arranger.fit_range(notes, instrument)
    if gen == "comp":
        lo, hi = (52, 77) if INSTRUMENTS[instrument][4] not in ("guitar",) else (52, 76)
        a, b = _main_bars(song)
        lead = [n for t in song.tracks if t.role == "lead" for n in t.notes]
        return arranger.comp_part(chords, (0, b), spec["rhythm"], sw, lo, hi, spec.get("rootless", False), True,
                                  vel=72, melody=lead)
    if gen == "pad":
        lo, hi = 55, 79
        lead = [n for t in song.tracks if t.role == "lead" for n in t.notes]
        return arranger.pad_part(chords, (0, song.bars), lo, hi, True, melody=lead)
    if gen == "arp":
        i_lo, i_hi = INSTRUMENTS[instrument][2:4]
        lo = max(60, i_lo) if i_hi - max(60, i_lo) >= 18 else max(i_lo, i_hi - 24)
        a, b = _main_bars(song)
        return arranger.arp_part(chords, (a, b), lo, min(lo + 24, i_hi), spec.get("fast", False), sw, rng)
    if gen == "riff":
        return arranger.riff_part(song.chords, _main_bars(song), instrument, rng)
    if gen in ("counter", "counter_high"):
        i_lo, i_hi = INSTRUMENTS[instrument][2:4]
        lo, hi = (max(i_lo, 67), min(i_hi, 91)) if gen == "counter_high" else (max(i_lo, 55), min(i_hi, 79))
        a, b = _main_bars(song)
        return arranger.counter_part(chords, (a, b), lo, hi)
    if gen == "answer":
        return answer(song, instrument, rng)
    if gen == "double":
        lead = [n for t in song.tracks if t.role == "lead" for n in t.notes]
        notes = [(s, l, p + spec["shift"], int(v * 0.8)) for s, l, p, v in lead]
        return arranger.fit_range(notes, instrument) if spec["shift"] == 0 else _fit_keep_shift(notes, instrument)
    if gen == "riser":
        return [(s0 * 4 - 2, 2.0, 60, 100) for _, s0, _ in song.sections[1:] if s0 * 4 - 2 > 0]
    if gen == "hits":
        out = []
        for _, s0, _ in song.sections[1:]:
            c = song.chord_at(s0 * 4 + 1e-6)
            if c:
                out.append((s0 * 4, 1.5, 48 + (c.root - 48) % 12, 112))
        return out
    if gen == "sfx_notes":
        return [(bar * 4 + rng.uniform(0, 2), 3.0, 60, 70) for bar in range(0, song.bars, 2)]
    if gen == "texture":
        return [(0, song.bars * 4, 60, 64)]
    raise ValueError(gen)


def _fit_keep_shift(notes, instrument):
    lo, hi = INSTRUMENTS[instrument][2:4]
    return [(s, l, p, v) for s, l, p, v in notes if lo <= p <= hi] or arranger.fit_range(notes, instrument)


def answer(song, instrument, rng) -> list[tuple]:
    """Call and response: short phrases from chord tones placed only where your melody rests for a
    beat or more (MUSIC_KNOWLEDGE A1: one foreground at a time)."""
    lead = sorted(n for t in song.tracks if t.role == "lead" for n in t.notes)
    i_lo, i_hi = INSTRUMENTS[instrument][2:4]
    lo, hi = max(i_lo, 60), min(i_hi, 84)
    out = []
    a, b = _main_bars(song)
    # Windows: rests of a beat or more, and long held notes ("a long held note is your window",
    # docs/ARRANGING.md R3.1/R3.3): the answer starts once the held note has sounded for a beat.
    windows = []
    for (s, l, p, v), nxt in zip(lead, lead[1:]):
        if nxt[0] - (s + l) >= 1.0:
            windows.append((s + l, nxt[0]))
        elif l >= 2.0:
            windows.append((s + 1.0, s + l))
    for gap_start, gap_end in windows:
        if not (a * 4 <= gap_start < b * 4):
            continue
        c = song.chord_at(gap_start + 1e-6)
        if c is None:
            continue
        tones = sorted(theory.voice(c, None, lo, hi, n=4))
        n_notes = min(4, int((gap_end - gap_start) / 0.5))
        for i in range(n_notes):
            t0 = gap_start + 0.25 + i * 0.5
            if t0 + 0.4 > gap_end:
                break
            out.append((t0, 0.45, tones[(i * 2 + 1) % len(tones)] if i % 2 else tones[-1 - i % len(tones)], 80))
    return out

