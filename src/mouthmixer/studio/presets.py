"""Ready-made parts to mix and match, so a track can be made without recording anything.

Two kinds:

- Grooves (beat, bassline, chords): patterns for the starter's generated parts. They keep following each
  section's feel (the intro builds, a chorus lifts, a rap verse drops into its pocket, the ending hits), so
  swapping the groove never loses the song's shape. Simpler / busier works on them too.
- Phrases (riffs, stabs, answer lines, intro motifs, hooks, percussion, fills): short parts written in
  chord tones, laid onto the track's main chords when added. They then behave like a recorded piece: they
  follow other chords, take one-note fixes, simpler / busier, octave and sound swaps.

Every pattern here is a common, generic figure of its style (8th-note rock, four-on-the-floor, a bossa
clave, a walking bass...), none taken from a song. Combos are named sets of a beat, a bassline and a chord
rhythm that go together.

Phrase notes are (16th step, length in 16ths, tone). A tone is a chord tone counted from the chord's root
nearest the part's register (CENTER): 0 the root, 1 its 3rd, 2 its 5th, 3 its 7th (or the root again),
-1 the chord tone below the root. A string "2+" / "2-" is the note of the key just above / below that
chord tone (a passing note). Percussion and fills are 16-step drum rows per bar (styles.VEL: X accent,
x normal, g ghost, o open).
"""

from __future__ import annotations

from ..arrange import theory

# --- grooves ---------------------------------------------------------------------------------------
BEATS = {
    "funk_break": {"name": "Funk breakbeat", "describe": "syncopated kick, ghost notes, open hat lifts",
                   "pattern": {"kick": "x..x..x...x..x..", "snare": "....X.......X...", "ghost": "..g..g.g..g..g.g",
                               "hat": "x.x.x.x.x.x.x.x.", "open_hat": "......o.......o."}},
    "busy_funk": {"name": "Busy 16th funk", "describe": "16th hats driving the whole bar",
                  "pattern": {"kick": "x.x.......x..x..", "snare": "....X..g....X...", "hat": "xxxxxxxxxxxxxxxx"}},
    "break_two": {"name": "Rolling break", "describe": "a classic two-bar-feel breakbeat with a late snare",
                  "pattern": {"kick": "x.x.......xx....", "snare": "....X..g.g..X..g", "hat": "x.x.x.x.x.x.x.x."}},
    "boom_bap": {"name": "Boom-bap", "describe": "hip-hop: heavy kick, crisp snare, laid back",
                 "pattern": {"kick": "x.........x..x..", "snare": "....X.......X...", "hat": "x.x.x.x.x.x.x.x.",
                             "ghost": "...........g...."}, "swing": 0.56},
    "half_time": {"name": "Half-time", "describe": "the snare only on beat 3: heavy and slow-feeling",
                  "pattern": {"kick": "x.....x...x.....", "snare": "........X.......", "hat": "x.x.x.x.x.x.x.x."}},
    "four_floor": {"name": "Four on the floor", "describe": "a kick on every beat, claps on 2 and 4",
                   "pattern": {"kick": "x...x...x...x...", "clap": "....X.......X...", "hat": "..x...x...x...x.",
                               "open_hat": "..o...o...o...o."}},
    "disco": {"name": "Disco chase", "describe": "four-on-the-floor with 16th hats and an open hat bark",
              "pattern": {"kick": "x...x...x...x...", "snare": "....X.......X...", "hat": "xxx.xxx.xxx.xxx.",
                          "open_hat": "...o...o...o...o"}},
    "rock_8ths": {"name": "Rock 8ths", "describe": "straight 8th hats, kick on 1 and the and of 2",
                  "pattern": {"kick": "x.....x.x.......", "snare": "....X.......X...", "hat": "x.x.x.x.x.x.x.x."}},
    "pop_drive": {"name": "Pop-rock drive", "describe": "pushing kicks and open hats: upbeat and bright",
                  "pattern": {"kick": "x..x..x.x..x....", "snare": "....X.......X...", "open_hat": "..o...o...o...o.",
                              "hat": "x...x...x...x..."}},
    "train": {"name": "Train rhythm", "describe": "chugga-chugga ghost snares: a train on the rails",
              "pattern": {"kick": "x.......x.......", "snare": "gXggxggxgXggxggx", "hat": "x.x.x.x.x.x.x.x."}},
    "shuffle": {"name": "Shuffle", "describe": "swung 8ths: bouncy, a little cheeky",
                "pattern": {"kick": "x.....x.x.......", "snare": "....X.......X...", "hat": "x.x.x.x.x.x.x.x."},
                "swing": 0.66},
    "jazz_ride": {"name": "Jazz ride", "describe": "swung ride cymbal, hi-hat foot on 2 and 4, soft kick",
                  "pattern": {"ride": "x...x.x.x...x.x.", "pedal_hat": "....x.......x...", "kick": "x.......g.......",
                              "ghost": "......g.......g."}, "swing": 0.64},
    "bossa": {"name": "Bossa nova", "describe": "rim clave, soft kick, shaker: gentle and swaying",
              "pattern": {"kick": "x..x....x..x....", "rim": "x..x..x...x..x..", "shaker": "xgxgxgxgxgxgxgxg"}},
    "neo_soul": {"name": "Lazy neo-soul", "describe": "late, swung and soft: a head-nod groove",
                 "pattern": {"kick": "x......x..x.....", "snare": "....X.......X..g", "hat": "x.xgx.xgx.xgx.xg"},
                 "swing": 0.6},
    "trap": {"name": "Trap hats", "describe": "rattling 16th hats, a big snare on 3",
             "pattern": {"kick": "x......x..x.....", "clap": "........X.......", "hat": "xxxxxxxxxxxxxxxx"}},
    "dembow": {"name": "Dembow bounce", "describe": "the bouncing three-hit snare of reggaeton",
               "pattern": {"kick": "x...x...x...x...", "snare": "...x..x....x..x.", "hat": "x.x.x.x.x.x.x.x."}},
    "pulse": {"name": "Tense pulse", "describe": "sparse kick and rim: danger nearby",
              "pattern": {"kick": "x.......x.......", "rim": "......x.......x.", "hat": "..x...x...x...x."}},
    "tom_tribal": {"name": "Tribal toms", "describe": "pounding toms for a dramatic fight",
                   "pattern": {"kick": "x..x....x..x....", "tom_lo": "x...x.x.x...x.x.", "tom_hi": "..x.....x.x.....",
                               "snare": "....X.......X..."}},
    "double_time": {"name": "Double-time rush", "describe": "8th-note kick and a snare on every off-beat: flat out",
                    "pattern": {"kick": "x.x.x.x.x.x.x.x.", "snare": "..X...X...X...X.", "hat": "xxxxxxxxxxxxxxxx"}},
    "march": {"name": "March", "describe": "snare rolls and a steady kick: heroic, orchestral",
              "pattern": {"kick": "x.......x.......", "snare": "X.xxX...X.xxX.x.", "crash": "x..............."}},
}

BASSES = {
    "slap_octaves": {"name": "Slap octaves", "describe": "root and octave pops, funk style",
                     "cell": [(0, 1, "R"), (2, 1, "8"), (3, 1, "R"), (6, 1, "8"), (8, 1, "R"), (10, 1, "8"), (11, 1, "5"), (14, 2, "A")]},
    "funk_pops": {"name": "Funk pops", "describe": "busy, syncopated, lots of octave pops",
                  "cell": [(0, 2, "R"), (3, 1, "8"), (5, 1, "8"), (7, 1, "R"), (8, 2, "R"), (10, 1, "8"), (13, 1, "5"), (14, 1, "8")]},
    "syncopated": {"name": "Syncopated groove", "describe": "a long root, then pushes and a walk-up",
                   "cell": [(0, 3, "R"), (3, 1, "8"), (6, 2, "R"), (8, 2, "5"), (10, 1, "8"), (12, 2, "R"), (14, 2, "A")]},
    "root_8ths": {"name": "Driving 8ths", "describe": "the root on every 8th: rock and build-ups",
                  "cell": [(i * 2, 2, "R") for i in range(8)]},
    "disco_octaves": {"name": "Disco octaves", "describe": "root and octave jumping every 8th",
                      "cell": [(i * 2, 1, "R" if i % 2 == 0 else "8") for i in range(8)]},
    "gallop": {"name": "Gallop", "describe": "8th and two 16ths: a charging rock rhythm",
               "cell": [(b * 4 + s, ln, "R") for b in range(4) for s, ln in ((0, 2), (2, 1), (3, 1))]},
    "walking": {"name": "Walking bass", "describe": "a note on every beat walking up the chord: jazz",
                "cell": [(0, 4, "R"), (4, 4, "3"), (8, 4, "5"), (12, 4, "A")]},
    "bossa": {"name": "Bossa root-fifth", "describe": "root and fifth, gently swaying",
              "cell": [(0, 6, "R"), (6, 2, "5"), (8, 6, "5"), (14, 2, "R")]},
    "long_roots": {"name": "Long roots", "describe": "one long note per chord: lots of space",
                   "cell": [(0, 16, "R")]},
    "half_notes": {"name": "Root and fifth", "describe": "two long notes per bar",
                   "cell": [(0, 8, "R"), (8, 8, "5")]},
    "sub_pocket": {"name": "Sub pocket", "describe": "long low notes that leave room for a rapper",
                   "cell": [(0, 6, "R"), (10, 4, "R"), (14, 2, "A")]},
    "pedal_16ths": {"name": "Pulsing 16ths", "describe": "a nervous pulse of 16th-note roots",
                    "cell": [(i, 1, "R") for i in range(16)]},
    "reggae": {"name": "One-drop", "describe": "laid back, skipping beat 1",
               "cell": [(4, 2, "R"), (7, 1, "5"), (8, 4, "R"), (12, 2, "3")]},
}

CHORD_RHYTHMS = {
    "funk_chops": {"name": "Funky chops", "describe": "short 16th-note chord stabs",
                   "rhythm": [(0, 1), (3, 1), (6, 1), (10, 2), (13, 1)]},
    "offbeat": {"name": "Off-beat skank", "describe": "chords on the and of every beat",
                "rhythm": [(2, 1), (6, 1), (10, 1), (14, 1)]},
    "held": {"name": "Held chords", "describe": "one long chord per bar: calm, spacious",
             "rhythm": [(0, 16)]},
    "halves": {"name": "Two per bar", "describe": "chords on 1 and 3",
               "rhythm": [(0, 8), (8, 8)]},
    "quarters": {"name": "Quarter pumps", "describe": "a chord on every beat",
                 "rhythm": [(i * 4, 3) for i in range(4)]},
    "eighths": {"name": "8th-note pumps", "describe": "driving 8ths: rock and build-ups",
                "rhythm": [(i * 2, 1) for i in range(8)]},
    "charleston": {"name": "Charleston", "describe": "on 1 and the and of 2: jazzy and bouncy",
                   "rhythm": [(0, 3), (6, 2)]},
    "push": {"name": "Pushes", "describe": "long chords that arrive early, before the bar",
             "rhythm": [(0, 6), (6, 4), (14, 2)]},
    "bossa": {"name": "Bossa comp", "describe": "the gentle syncopation of bossa guitar",
              "rhythm": [(0, 3), (3, 3), (6, 2), (10, 3), (13, 3)]},
    "gospel": {"name": "Gospel stabs", "describe": "punchy chords with a late hit",
               "rhythm": [(0, 2), (4, 2), (7, 1), (10, 2), (14, 2)]},
}

GROOVES = {"drums": BEATS, "bass": BASSES, "comp": CHORD_RHYTHMS}

COMBOS = {
    "starter": {"name": "The starter's own", "describe": "back to the starter beat's groove", "beat": "", "bass": "", "chords": ""},
    "heist": {"name": "Heist break", "describe": "funk breakbeat, slap octaves, chopped chords",
              "beat": "funk_break", "bass": "slap_octaves", "chords": "funk_chops"},
    "chase": {"name": "Disco chase", "describe": "four-on-the-floor, octave bass, off-beat chords",
              "beat": "disco", "bass": "disco_octaves", "chords": "offbeat"},
    "train": {"name": "Night train", "describe": "chugging train rhythm, driving bass, pushes",
              "beat": "train", "bass": "root_8ths", "chords": "push"},
    "pocket": {"name": "Boom-bap pocket", "describe": "hip-hop: heavy kick, long bass, held chords",
               "beat": "boom_bap", "bass": "sub_pocket", "chords": "held"},
    "charge": {"name": "Rock charge", "describe": "rock 8ths, galloping bass, pumping chords",
               "beat": "rock_8ths", "bass": "gallop", "chords": "eighths"},
    "club": {"name": "Jazz club", "describe": "swung ride, walking bass, Charleston chords",
             "beat": "jazz_ride", "bass": "walking", "chords": "charleston"},
    "rain": {"name": "Bossa rain", "describe": "bossa drums, root-fifth bass, bossa comp",
             "beat": "bossa", "bass": "bossa", "chords": "bossa"},
    "menace": {"name": "Half-time menace", "describe": "slow, heavy, lots of space",
               "beat": "half_time", "bass": "long_roots", "chords": "held"},
    "dance": {"name": "Dance floor", "describe": "four-on-the-floor, funk pops, quarter pumps",
              "beat": "four_floor", "bass": "funk_pops", "chords": "quarters"},
    "neo": {"name": "Neo-soul lean", "describe": "lazy swung drums, syncopated bass, pushes",
            "beat": "neo_soul", "bass": "syncopated", "chords": "push"},
    "boss": {"name": "Boss rush", "describe": "double-time drums, pulsing bass, pumping chords",
             "beat": "double_time", "bass": "pedal_16ths", "chords": "eighths"},
}


def busy_drums(pat: dict, busy: int) -> dict:
    """Simpler (busy < 0): ghosts and open hats out, hats to 8ths, then quarters. Busier: 16th hats and
    ghost snares, then open-hat lifts and a pickup kick."""
    pat = dict(pat)
    if busy <= -1:
        pat.pop("ghost", None)
        pat.pop("open_hat", None)
        for k in ("hat", "shaker", "ride"):
            if k in pat:
                pat[k] = "".join(c if i % (4 if busy <= -2 else 2) == 0 else "." for i, c in enumerate(pat[k]))
        if busy <= -2 and "kick" in pat:
            pat["kick"] = "".join(c if i in (0, 8) else "." for i, c in enumerate(pat["kick"]))
    if busy >= 1:
        hat = "hat" if "hat" in pat or "ride" not in pat else "ride"
        row = pat.get(hat, "." * 16)
        pat[hat] = "".join(c if c != "." else "x" for c in row)
        g = pat.get("ghost", "." * 16)
        snare = pat.get("snare", "." * 16)
        pat["ghost"] = "".join("g" if g[i] == "." and snare[i] == "." and i % 4 == 2 else g[i] for i in range(16))
    if busy >= 2:
        pat["open_hat"] = pat.get("open_hat", "..o...o...o...o.")
        k = pat.get("kick", "x.......x.......")
        pat["kick"] = k[:7] + "x" + k[8:15] + "x"
    return pat


def busy_bass(cell: list, busy: int) -> list:
    """Simpler: only the notes on the beat, held longer (then one long root). Busier: octave pops in the
    gaps (then 16th ghost roots too)."""
    if busy <= -2:
        return [(0, 16, "R")]
    cell = sorted(cell)
    if busy == -1:
        keep = [c for c in cell if c[0] % 4 == 0] or cell[:1]
        return [(s, (keep[i + 1][0] if i + 1 < len(keep) else 16) - s, slot) for i, (s, _, slot) in enumerate(keep)]
    if busy >= 1:
        covered = set()
        for s, ln, _ in cell:
            covered.update(range(s, s + ln))
        extra = [(s, 1, "8") for s in (2, 6, 10) if s not in covered]
        if busy >= 2:
            extra += [(s, 1, "R") for s in (3, 7, 11, 15) if s not in covered and (s - 1, 1, "8") not in extra]
        cell = sorted(cell + extra)
    return cell


def busy_comp(rhythm: list, busy: int) -> list:
    """Simpler: every other chord, held longer (then one per bar). Busier: off-beat 8th chops in the gaps
    (then 16ths)."""
    if busy <= -2:
        return [(0, 16)]
    rhythm = sorted(rhythm)
    if busy == -1:
        keep = rhythm[::2] or rhythm[:1]
        return [(s, (keep[i + 1][0] if i + 1 < len(keep) else 16) - s) for i, (s, _) in enumerate(keep)]
    if busy >= 1:
        covered = set()
        for s, ln in rhythm:
            covered.update(range(s, s + ln))
        steps = (2, 6, 10, 14) if busy == 1 else (2, 3, 6, 7, 10, 11, 14, 15)
        rhythm = sorted(rhythm + [(s, 1) for s in steps if s not in covered])
    return rhythm


# --- phrases ---------------------------------------------------------------------------------------
def _bar2(*bars):
    """Join per-bar note lists into one list (bar k shifted by k bars)."""
    return [(s + 16 * k, ln, t) for k, notes in enumerate(bars) for s, ln, t in notes]


PHRASES = {
    # riffs: a figure that repeats under everything (2 bars)
    "riff_clav": {"slot": "riff", "name": "Funky clav chops", "describe": "choppy 16ths around the chord", "bars": 2,
                  "instrument": "clavinet",
                  "notes": _bar2([(0, 1, 0), (2, 1, 1), (3, 1, 2), (6, 1, 1), (8, 1, 0), (10, 1, 2), (11, 1, 1), (14, 1, 0)],
                                 [(0, 1, 0), (2, 1, 1), (3, 1, 2), (6, 1, 3), (8, 2, 2), (11, 1, 1), (14, 2, "0-")])},
    "riff_heist": {"slot": "riff", "name": "Sneaky heist line", "describe": "a creeping line that walks down, then up",
                   "bars": 2,
                   "notes": _bar2([(0, 3, 3), (3, 1, "2+"), (4, 2, 2), (6, 2, 1), (8, 4, 0), (12, 2, "0-"), (14, 2, 0)],
                                  [(0, 2, 0), (2, 2, 1), (4, 2, 2), (6, 2, 3), (8, 6, 4), (14, 2, 3)])},
    "riff_arp": {"slot": "riff", "name": "Rising arpeggio", "describe": "8th notes up and down the chord", "bars": 2,
                 "notes": _bar2([(i * 2, 2, t) for i, t in enumerate([0, 1, 2, 3, 4, 3, 2, 1])],
                                [(i * 2, 2, t) for i, t in enumerate([0, 1, 2, 3, 4, 5, 4, 2])])},
    "riff_sparkle": {"slot": "riff", "name": "Sparkly 16th run", "describe": "a quick run, then a held note",
                     "bars": 2, "instrument": "vibraphone",
                     "notes": _bar2([(i, 1, [0, 1, 2, 3][i % 4]) for i in range(8)] + [(8, 8, 4)],
                                    [(i, 1, [4, 3, 2, 1][i % 4]) for i in range(8)] + [(8, 8, 0)])},
    "riff_octaves": {"slot": "riff", "name": "Octave pulse", "describe": "a low note jumping an octave every 8th",
                     "bars": 2, "notes": _bar2([(i * 2, 1, 0 if i % 2 == 0 else 3) for i in range(8)],
                                               [(i * 2, 1, 0 if i % 2 == 0 else 3) for i in range(8)])},
    "riff_call": {"slot": "riff", "name": "Call and wait", "describe": "a short call, then space", "bars": 2,
                  "notes": _bar2([(0, 2, 2), (3, 1, 2), (6, 2, 3), (10, 2, 2), (14, 2, 1)],
                                 [(0, 2, 1), (3, 1, 1), (6, 4, 0)])},
    "riff_neo": {"slot": "riff", "name": "Lazy neo-soul line", "describe": "long notes that lean on the beat",
                 "bars": 2, "instrument": "rhodes",
                 "notes": _bar2([(0, 6, 2), (6, 2, 3), (8, 4, "2-"), (12, 4, 1)], [(0, 8, 0), (8, 4, 1), (12, 4, 2)])},
    # stabs: short full-band chord hits (2 bars); each note becomes a chord
    "stab_push": {"slot": "stab", "name": "Push into each bar", "describe": "one hit on the and of 4", "bars": 2,
                  "notes": [(14, 2, 0), (30, 2, 0)]},
    "stab_charleston": {"slot": "stab", "name": "Charleston hits", "describe": "on 1 and the and of 2", "bars": 2,
                        "notes": [(0, 2, 0), (6, 2, 0), (16, 2, 0), (22, 2, 0)]},
    "stab_offbeat": {"slot": "stab", "name": "Off-beat brass", "describe": "a hit on every off-beat", "bars": 2,
                     "notes": [(s, 1, 0) for s in (2, 6, 10, 14, 18, 22, 26, 30)]},
    "stab_big_one": {"slot": "stab", "name": "Big hit on 1", "describe": "one big hit, and a pickup into the next",
                     "bars": 2, "notes": [(0, 4, 0), (30, 2, 0)]},
    "stab_three": {"slot": "stab", "name": "Three-hit tag", "describe": "three hits at the end of the 2 bars",
                   "bars": 2, "notes": [(24, 1, 0), (27, 1, 0), (30, 2, 0)]},
    "stab_funk": {"slot": "stab", "name": "Funk syncopation", "describe": "hits that dodge the beat", "bars": 2,
                  "notes": [(3, 1, 0), (10, 1, 0), (19, 1, 0), (22, 1, 0), (28, 2, 0)]},
    "stab_battle": {"slot": "stab", "name": "Battle shots", "describe": "a burst of hits, then a pickup", "bars": 2,
                    "notes": [(0, 1, 0), (3, 1, 0), (6, 2, 0), (28, 1, 0), (30, 2, 0)]},
    # answer lines: replies in the gaps after a sung line (4 bars: bars 2 and 4)
    "ans_reply": {"slot": "counter", "name": "Brass reply", "describe": "three notes up in the gaps", "bars": 4,
                  "notes": [(24, 1, 1), (26, 1, 2), (28, 4, 3), (56, 1, 2), (58, 1, 1), (60, 4, 0)]},
    "ans_run": {"slot": "counter", "name": "Rising run", "describe": "a quick run up into the next line", "bars": 4,
                "notes": [(24, 1, 0), (25, 1, "0+"), (26, 1, 1), (27, 1, "1+"), (28, 4, 2),
                          (56, 1, 2), (57, 1, "2+"), (58, 1, 3), (59, 1, "3+"), (60, 4, 5)]},
    "ans_sigh": {"slot": "counter", "name": "Falling sighs", "describe": "two long notes falling", "bars": 4,
                 "notes": [(24, 4, 3), (28, 4, 2), (56, 4, 2), (60, 4, 1)]},
    "ans_echo": {"slot": "counter", "name": "Echo shots", "describe": "short repeated notes, like an echo", "bars": 4,
                 "notes": [(26, 1, 2), (28, 1, 2), (30, 2, 3), (58, 1, 2), (60, 1, 2), (62, 2, 1)]},
    "ans_trill": {"slot": "counter", "name": "Trill fill", "describe": "a fluttering trill", "bars": 4,
                  "instrument": "flute",
                  "notes": [(24 + i, 1, 2 if i % 2 == 0 else "2+") for i in range(4)] + [(28, 4, 2)] +
                           [(56 + i, 1, 1 if i % 2 == 0 else "1+") for i in range(4)] + [(60, 4, 1)]},
    # intro motifs: a few notes that open the track and come back at the end (4 bars)
    "intro_fanfare": {"slot": "intro", "name": "Heroic fanfare", "describe": "rising up the chord to a long top note",
                      "bars": 4, "instrument": "trumpet",
                      "notes": [(0, 2, 0), (2, 2, 1), (4, 4, 2), (8, 8, 3), (32, 2, 1), (34, 2, 2), (36, 4, 3), (40, 16, 4)]},
    "intro_chime": {"slot": "intro", "name": "Station call", "describe": "three falling notes, twice", "bars": 4,
                    "instrument": "vibraphone",
                    "notes": [(0, 4, 2), (4, 4, 1), (8, 8, 0), (32, 4, 2), (36, 4, 1), (40, 16, "0-")]},
    "intro_rise": {"slot": "intro", "name": "Mystery rise", "describe": "slowly climbing, step by step", "bars": 4,
                   "instrument": "strings",
                   "notes": [(0, 8, 0), (8, 8, "0+"), (16, 8, 1), (24, 8, "1+"), (32, 8, 2), (40, 8, "2+"), (48, 16, 3)]},
    "intro_count": {"slot": "intro", "name": "Countdown pings", "describe": "a high note on every beat, then a long one",
                    "bars": 4, "instrument": "glockenspiel",
                    "notes": [(i * 4, 1, 3) for i in range(12)] + [(48, 16, 4)]},
    "intro_spy": {"slot": "intro", "name": "Spy theme", "describe": "a sneaky up-down figure", "bars": 4,
                  "notes": [(0, 3, 0), (3, 3, "0+"), (6, 2, 1), (8, 8, 0), (16, 3, 0), (19, 3, "0-"), (22, 2, "0+"),
                            (24, 8, 0), (32, 3, 1), (35, 3, "1+"), (38, 2, 2), (40, 8, 1), (48, 16, 0)]},
    # hooks: the catchy instrumental line (4 bars)
    "hook_three": {"slot": "hook", "name": "Three-note hook", "describe": "short, repeated, easy to remember",
                   "bars": 4,
                   "notes": [(0, 2, 2), (2, 2, 2), (4, 4, 1), (8, 4, 0), (16, 2, 2), (18, 2, 2), (20, 4, 1), (24, 8, "1+"),
                             (32, 2, 2), (34, 2, 2), (36, 4, 1), (40, 4, 0), (48, 2, 2), (50, 2, 3), (52, 4, 4), (56, 8, 2)]},
    "hook_qa": {"slot": "hook", "name": "Question and answer", "describe": "rises in bar 1, falls back in bar 3",
                "bars": 4, "notes": [(0, 2, 0), (2, 2, 1), (4, 2, 2), (6, 6, 3), (32, 2, 3), (34, 2, 2), (36, 2, 1), (38, 10, 0)]},
    "hook_sync": {"slot": "hook", "name": "Syncopated earworm", "describe": "notes that land just off the beat",
                  "bars": 4,
                  "notes": [(0, 1, 2), (3, 1, 2), (6, 2, 3), (10, 2, 2), (14, 2, 1), (16, 6, 0),
                            (32, 1, 2), (35, 1, 2), (38, 2, 3), (42, 2, 4), (46, 2, 3), (48, 8, 2)]},
    "hook_soar": {"slot": "hook", "name": "Soaring line", "describe": "long notes climbing high", "bars": 4,
                  "notes": [(0, 8, 2), (8, 8, 3), (16, 16, 4), (32, 8, 3), (40, 8, 2), (48, 16, 1)]},
    # percussion: an extra groove layer (2 bars)
    "perc_shaker": {"slot": "perc", "name": "Shaker 16ths", "describe": "a soft shaker on every 16th", "bars": 2,
                    "rows": {"shaker": "xgxgxgxgxgxgxgxg"}},
    "perc_tamb": {"slot": "perc", "name": "Tambourine 2 and 4", "describe": "a bright tambourine on the backbeat",
                  "bars": 2, "rows": {"tambourine": "....x.......x..."}},
    "perc_congas": {"slot": "perc", "name": "Congas", "describe": "a rolling conga groove", "bars": 2,
                    "rows": {"hi_conga": "..x...x...x.x...", "lo_conga": "x.....x.....x...", "mute_conga": "....x.......x..x"}},
    "perc_claps": {"slot": "perc", "name": "Claps", "describe": "claps on 2 and 4, with a flam", "bars": 2,
                   "rows": {"clap": "....X.......X.x."}},
    "perc_cowbell": {"slot": "perc", "name": "Cowbell", "describe": "an 8th-note cowbell", "bars": 2,
                     "rows": {"cowbell": "x.x.x.x.x.x.x.x."}},
    "perc_bongos": {"slot": "perc", "name": "Bongos", "describe": "a busy bongo pattern", "bars": 2,
                    "rows": {"hi_bongo": "x.xx..x.x.xx..x.", "lo_bongo": "...x.....x....x."}},
    "perc_train": {"slot": "perc", "name": "Rail clatter", "describe": "an accented shaker like train wheels",
                   "bars": 2, "rows": {"shaker": "XgxgXgxgXgxgXgxg", "claves": "x.......x......."}},
    # fills: one bar that leads into the next section
    "fill_roll": {"slot": "fill", "name": "Snare roll", "describe": "a roll that grows into the next section",
                  "bars": 1, "rows": {"snare": "....gggxxxxXXXXX"}},
    "fill_toms": {"slot": "fill", "name": "Tom run", "describe": "down the toms", "bars": 1,
                  "rows": {"kick": "x.......x.......", "tom_hi": "........XX......", "tom_mid": "..........XX....",
                           "tom_lo": "............XXXX"}},
    "fill_build": {"slot": "fill", "name": "Kick-snare build", "describe": "kicks and snares speeding up", "bars": 1,
                   "rows": {"kick": "x.x.x.x.xxxxxxxx", "snare": "....x...x.x.xxxx"}},
    "fill_stop": {"slot": "fill", "name": "Stop-time hits", "describe": "three hits, then silence", "bars": 1,
                  "rows": {"kick": "x.....x.....x...", "crash": "x.....x.....x..."}},
}

CATEGORIES = [
    {"id": "beat", "label": "Beat", "gen": "drums"},
    {"id": "bass", "label": "Bassline", "gen": "bass"},
    {"id": "chords", "label": "Chords", "gen": "comp"},
    {"id": "riff", "label": "Riffs"},
    {"id": "stab", "label": "Stabs"},
    {"id": "counter", "label": "Answer lines"},
    {"id": "intro", "label": "Intro motifs"},
    {"id": "hook", "label": "Hooks"},
    {"id": "perc", "label": "Percussion"},
    {"id": "fill", "label": "Fills"},
]
CENTER = {"riff": 60, "stab": 72, "counter": 67, "intro": 72, "hook": 72}


def public() -> dict:
    cats = []
    for c in CATEGORIES:
        if c.get("gen"):
            items = [{"id": k, "name": v["name"], "describe": v["describe"]} for k, v in GROOVES[c["gen"]].items()]
        else:
            items = [{"id": k, "name": v["name"], "describe": v["describe"]} for k, v in PHRASES.items()
                     if v["slot"] == c["id"]]
        cats.append(c | {"items": items})
    return {"categories": cats,
            "combos": [{"id": k} | v for k, v in COMBOS.items()]}


def groove_options(gen: str) -> list[dict]:
    return [{"id": "", "name": "The starter's own"}] + [{"id": k, "name": v["name"]} for k, v in GROOVES[gen].items()]


def phrase_options(slot: str) -> list[dict]:
    return [{"id": k, "name": v["name"]} for k, v in PHRASES.items() if v["slot"] == slot]


def _ladder(chord, lo: int, hi: int) -> list[int]:
    pcs = {(chord.root + i) % 12 for i in theory.QUALITIES[chord.quality] if i < 12}
    return [p for p in range(lo, hi + 1) if p % 12 in pcs]


def _neighbour(pitch: int, d: int, scale: set) -> int:
    q = pitch + d
    while q % 12 not in scale:
        q += d
    return q


def render_phrase(pid: str, chords: list, tonic: int, mode: str) -> list[list]:
    """A phrase's notes ([start beat, length, pitch, velocity]) laid on `chords` ([(start, len, Chord)] from
    beat 0), each tone taken from the chord sounding at that moment."""
    from ..arrange.styles import DRUM, VEL

    pr = PHRASES[pid]
    if "rows" in pr:
        out = []
        for bar in range(pr["bars"]):
            for name, row in pr["rows"].items():
                for step, ch in enumerate(row):
                    if ch != ".":
                        out.append([bar * 4 + step / 4, 0.2, DRUM[name], VEL.get(ch, 80)])
        return sorted(out)
    center = CENTER.get(pr["slot"], 64)
    scale = {(tonic + i) % 12 for i in theory.MODES.get(mode, theory.MODES["major"])}
    out = []
    for step, ln, tone in pr["notes"]:
        beat = step / 4
        c = next((c for s, l, c in chords if s <= beat < s + l), chords[-1][2])
        lad = _ladder(c, center - 24, center + 36)
        base = min((i for i, p in enumerate(lad) if p % 12 == c.root), key=lambda i: (abs(lad[i] - center), -lad[i]))
        if isinstance(tone, str):
            k, d = int(tone[:-1]), 1 if tone.endswith("+") else -1
            pitch = _neighbour(lad[max(0, min(len(lad) - 1, base + k))], d, scale)
        else:
            pitch = lad[max(0, min(len(lad) - 1, base + tone))]
        vel = 100 if step % 4 == 0 else 88
        out.append([beat, ln / 4 * 0.95, int(pitch), vel])
    return sorted(out)
