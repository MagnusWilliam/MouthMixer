"""Instrumental cues for LINE ZERO's scenes (LINE ZERO docs/design/AUDIO_PLAN.md section 3.2; docs/PERSONA_PRODUCTION.md §6).

Each cue is a song form (no words), a style from `engine.STYLES`, chords per section and themes built on the
game's motifs. **H (the Hum) and B (the Bond theme) here are drafts** written so the cues have something to
quote: the audio plan leaves them to the user, and they're swapped everywhere by changing MOTIFS. S (Soren's
song) is the Fmaj7-E7-Am7-Gm7 C7 turnaround already in the game's code. Loops end on a chord that leads back
to their first bar; stings are two bars.
"""

from __future__ import annotations

# (beat, length in beats, note) phrases. DRAFTS unless the user writes their own.
MOTIFS = {
    # H: a 7-note lullaby (D minor). The Conductor hums it with notes 5 and 6 missing.
    "H": [(0, 1, "D5"), (1, 1, "A4"), (2, 1.5, "C5"), (3.5, .5, "Bb4"), (4, 1, "A4"), (5, 1, "G4"), (6, 2, "A4")],
    # B: the crew's warm 4-bar phrase (F major)
    "B": [(0, 1.5, "A4"), (1.5, .5, "C5"), (2, 1, "D5"), (3, 1, "C5"), (4, 1.5, "A4"), (5.5, .5, "G4"), (6, 2, "F4"),
          (8, 1, "G4"), (9, 1, "A4"), (10, 1, "C5"), (11, 1, "F5"), (12, 1.5, "E5"), (13.5, .5, "D5"), (14, 2, "C5")],
    # S: Soren's song, the busker's arpeggios over Fmaj7-E7-Am7-Gm7 C7 (from LINE ZERO's CityAmbient code), F major
    "S": [(k * 0.5 + bar * 4, 0.45, 65 + semis) for bar, row in enumerate(
        [[0, 4, 7, 11, 12, 11, 7, 4], [-1, 3, 6, 9, 11, 9, 6, 3], [4, 7, 11, 14, 16, 14, 11, 7], [2, 5, 9, 12, 7, 11, 14, 11]])
        for k, semis in enumerate(row)],
    # T: the Timetable, the Hum inverted around its first note and quantised to a rigid click (D minor)
    "T": [(0, .5, "D5"), (.5, .5, "G5"), (1, .5, "E5"), (1.5, .5, "F5"), (2, .5, "G5"), (2.5, .5, "A5"), (3, 1, "G5")],
    # The school bell (the Westminster quarters, traditional), slow, for Stop 1's music box
    "BELL": [(0, 1, "A5"), (1, 1, "F5"), (2, 1, "G5"), (3, 2, "C5"), (6, 1, "C5"), (7, 1, "G5"), (8, 1, "A5"), (9, 2, "F5")],
    # Haru's figure (Stop 2): a sigh down and a lift
    "HARU": [(0, 1, "C5"), (1, 1, "B4"), (2, 2, "E5")],
    # L0: the Line 0 call: a falling minor third and the ticket punch (ka-CHK) as a 16th pickup (C minor)
    "L0": [(0, .75, "Eb5"), (.75, .25, "C5"), (1, .5, "C5"), (1.5, .5, "D5"), (2, .75, "Eb5"), (2.75, .25, "C5"),
           (3, 1, "G5"), (4, .75, "F5"), (4.75, .25, "Eb5"), (5, .5, "D5"), (5.5, .5, "C5"), (6, 1.5, "D5")],
}


def _shift(phrase, semis=0, stretch=1.0, drop=()):
    """A motif moved by semitones, slowed by `stretch`, with some notes left out (the forgetting)."""
    from .production import n

    return [(s * stretch, l * stretch, (n(p) if isinstance(p, str) else p) + semis) for i, (s, l, p) in enumerate(phrase)
            if i not in drop]


CUES = {
    "battle_boss": {
        "title": "Boss battle", "style": "boss_choir", "theme_inst": "sfz:trumpet",
        "form": [("Intro", 4), ("Verse", 8), ("Pre-Chorus", 8), ("Chorus", 16), ("Bridge", 8), ("Final Chorus", 16)],
        "feels": {"Intro": "intro", "Verse": "verse", "Pre-Chorus": "pre", "Chorus": "lift", "Bridge": "breakdown",
                  "Final Chorus": "final"},
        "chords": {"intro": ["Cm9", "Dbmaj7", "Cm9", "G7#5#9"], "verse": ["Cm9", "Cm9", "Abmaj7", "G7#5#9"],
                   "pre": ["Fm9", "Abmaj7", "Bb", "G7#5#9"],
                   "chorus": ["Abmaj7", "Bb", "Gm7", "Cm9", "Fm9", "Abmaj7", "Bb", "G7#5#9"],
                   "bridge": ["Abmaj7", "Gm7", "Fm9", "G7sus4"]},
        "themes": {"chorus": "L0", "final": "L0", "intro": [(0, 2, "Eb5"), (2, 6, "C5")]},
    },
    "lost_car": {
        "title": "The Lost Car", "style": "lost_car", "theme_inst": "sfz:trumpet_harmon",
        "form": [("Intro", 2), ("Verse", 8), ("Chorus", 8), ("Verse 2", 8)],
        "feels": {"Intro": "intro", "Verse": "verse", "Chorus": "lift", "Verse 2": "verse"},
        "chords": {"intro": ["Dm9", "A7#5#9"], "verse": ["Dm9", "Bbmaj7", "Gm9", "A7#5#9"],
                   "chorus": ["Gm9", "C9", "Fmaj7", "A7#5#9"]},
        "themes": {"verse": ("H", 0, 1.0, ()), "chorus": ("H", 3, 1.0, ())},
    },
    "victory": {
        "title": "Victory (sting)", "style": "results", "theme_inst": "sfz:trumpet_harmon",
        "form": [("Sting", 2)], "feels": {"Sting": "sting"},
        "chords": {"verse": ["Fmaj9", "Fmaj9"]},
        "themes": {"Sting": [(0, .5, "A4"), (.5, .5, "C5"), (1, 1, "D5"), (2, .5, "C5"), (2.5, 3, "F5")]},  # B's tail
    },
    "results": {
        "title": "Results", "style": "results",
        "form": [("Verse", 8), ("Chorus", 8)], "feels": {"Verse": "verse", "Chorus": "lift"},
        "chords": {"verse": ["Fmaj7", "Am7", "Bbmaj7", "C7sus4|C"], "chorus": ["Dm9", "Gm9", "C9", "Fmaj7|C7"]},
        "themes": {"chorus": "B"},
    },
    "stop_generic": {
        "title": "Mind the Gap (Stop exploration)", "style": "dungeon", "theme_inst": "celesta",
        "form": [("Intro", 4), ("Verse", 8), ("Bridge", 8), ("Verse 2", 8)],
        "feels": {"Intro": "intro", "Verse": "verse", "Bridge": "breakdown", "Verse 2": "verse"},
        "chords": {"intro": ["F#m9", "Gmaj7"], "verse": ["F#m9", "Gmaj7", "F#m9", "C#7#5#9"],
                   "bridge": ["Dmaj7", "Gmaj7", "F#m9", "F#m9"]},
        # T (the Timetable: H inverted, on a rigid click) as the pizzicato hook; H with notes missing on celesta
        "hook": [(0, .5, "F#4"), (.5, .5, "B4"), (1, .5, "G#4"), (1.5, .5, "A4"), (2, .5, "B4"), (2.5, .5, "C#5"), (3, 1, "B4")],
        "themes": {"bridge": ("H", 4, 1.0, (4, 5))},
    },
    "sad_soft": {
        "title": "Sad (soft)", "style": "sad",
        "form": [("Verse", 8), ("Chorus", 8)], "feels": {"Verse": "verse", "Chorus": "lift"},
        "chords": {"verse": ["Dm9", "Bbmaj7", "Gm9", "A7sus4|A7"], "chorus": ["Bbmaj7", "C", "Am7", "Dm9"]},
        "themes": {"verse": ("H", -12, 2.0, ()), "chorus": ("H", -9, 2.0, ())},
    },
    "hideout": {
        "title": "The Hideout", "style": "hideout",
        "form": [("Intro", 2), ("Verse", 8), ("Chorus", 8)], "feels": {"Intro": "intro", "Verse": "verse", "Chorus": "lift"},
        "chords": {"intro": ["Fmaj7", "C7sus4|C"], "verse": ["Fmaj7", "Dm9", "Bbmaj7", "C7sus4|C"],
                   "chorus": ["Bbmaj7", "Am7", "Gm9", "C9"]},
        "themes": {"chorus": "B"},
    },
    # Distinct Persona sounds and Undertale-inspired cues (PERSONA_PRODUCTION sections 7-8)
    "velvet": {
        "title": "The Waiting Platform (Velvet Room style)", "style": "velvet", "theme_inst": "voice_oohs",
        "form": [("Intro", 4), ("Verse", 8), ("Chorus", 8), ("Verse 2", 8)],
        "feels": {"Intro": "intro", "Verse": "verse", "Chorus": "lift", "Verse 2": "verse"},
        "chords": {"intro": ["C#m9", "Amaj7", "C#m9", "G#7#5#9"], "verse": ["C#m9", "Amaj7", "F#m9", "G#7#5#9"],
                   "chorus": ["Amaj7", "B", "G#m7", "C#m9"]},
        "themes": {"verse": ("H", 11, 1.5, ()), "chorus": ("H", 11, 1.5, ())},  # a wordless soprano, high, sings the Hum
    },
    "stop3_after_hours": {
        "title": "Stop 3: After Hours (chip city pop)", "style": "chip_city", "theme_inst": "synth:chip_square",
        "theme2_inst": "sfz:rhodes",
        "form": [("Intro", 4), ("Verse", 8), ("Chorus", 8), ("Verse 2", 8)],
        "feels": {"Intro": "intro", "Verse": "verse", "Chorus": "lift", "Verse 2": "verse"},
        "chords": {"intro": ["Fmaj7", "E7", "Am7", "Gm7|C7"], "verse": ["Fmaj7", "E7", "Am7", "Gm7|C7"],
                   "chorus": ["Bbmaj7", "C", "Am7", "Dm9"]},
        "themes": {"verse": ("S", 12, 1.0, ()), "chorus": "B"},  # Soren's song on the square wave, an octave up
        "themes2": {"chorus": ("B", -12, 1.0, ())},  # chip + real: the Rhodes doubles it an octave down
    },
    "shop": {
        "title": "Shop (swing)", "style": "chip_swing", "theme_inst": "synth:chip_square", "theme2_inst": "vibraphone",
        "form": [("Verse", 8), ("Chorus", 8)], "feels": {"Verse": "verse", "Chorus": "lift"},
        "chords": {"verse": ["Bbmaj7", "Gm7", "Cm7", "F7"], "chorus": ["Ebmaj7", "Dm7", "Cm7", "F7sus4|F7"]},
        "themes": {"verse": ("B", 5, 1.0, ()), "chorus": ("B", 5, 0.5, ())},  # the Bond theme, then at double speed
        "themes2": {"verse": ("B", -7, 1.0, ())},
    },
    "finale_hope": {
        "title": "Finale: First Light (hope)", "style": "hope", "theme_inst": "synth:chip_square",
        "theme2_inst": "sfz:violins",
        "form": [("Intro", 4), ("Verse", 8), ("Chorus", 16), ("Verse 2", 8), ("Final Chorus", 16)],
        "feels": {"Intro": "intro", "Verse": "verse", "Chorus": "lift", "Verse 2": "verse", "Final Chorus": "lift"},
        "chords": {"intro": ["Fmaj7", "G", "Fmaj7", "G"], "verse": ["Cmaj7", "Am7", "Fmaj7", "G"],
                   "chorus": ["Fmaj7", "G", "Em7", "Am9", "Fmaj7", "G", "Cmaj7", "Cmaj7"]},
        # every motif comes home: the Bond theme leads, the Hum answers as a countermelody, Soren's song in the verse
        "themes": {"verse": ("S", 7, 1.0, ()), "chorus": ("B", 7, 1.0, ()), "final": ("B", 7, 1.0, ())},
        "themes2": {"chorus": ("H", -5, 2.0, ()), "final": ("H", -5, 2.0, ())},
    },
    # AUDIO_PLAN 3.2, the next cues
    "bond": {
        "title": "Bond (hang-outs)", "style": "bond",
        "form": [("Intro", 2), ("Verse", 8), ("Chorus", 8), ("Verse 2", 8)],
        "feels": {"Intro": "intro", "Verse": "verse", "Chorus": "lift", "Verse 2": "verse"},
        "chords": {"intro": ["Fmaj7", "C7sus4|C"], "verse": ["Fmaj7", "Am7", "Dm9", "C7sus4|C"],
                   "chorus": ["Bbmaj7", "C", "Am7", "Dm9"]},
        "themes": {"verse": "B", "chorus": ("B", 12, 1.0, ())},
    },
    "title": {
        "title": "Title", "style": "title",
        "form": [("Intro", 4), ("Verse", 8), ("Chorus", 8), ("Verse 2", 8)],
        "feels": {"Intro": "intro", "Verse": "verse", "Chorus": "lift", "Verse 2": "verse"},
        "chords": {"intro": ["Dm9"], "verse": ["Dm9", "Bbmaj7", "Gm9", "A7sus4|A7"], "chorus": ["Bbmaj7", "C", "Am7", "Dm9"]},
        "themes": {"intro": "H", "verse": "H", "chorus": ("H", 3, 1.0, ())},
        "themes2": {"chorus": ("H", 15, 2.0, ())}, "theme2_inst": "voice_oohs",  # a wordless voice, high and slow
    },
    "tension": {
        "title": "Tension", "style": "tension", "theme_inst": "sfz:violins",
        "form": [("Verse", 8), ("Chorus", 8)], "feels": {"Verse": "verse", "Chorus": "lift"},
        "chords": {"verse": ["F#m9", "F#m9", "Gmaj7", "Gmaj7"], "chorus": ["Dmaj7", "Dmaj7", "C#7#5#9", "C#7#5#9"]},
        "themes": {"chorus": ("T", 4, 2.0, ())},
    },
    "station": {
        "title": "Station (before we go down)", "style": "station", "theme_inst": "sfz:horn", "textures": ["room"],
        "form": [("Verse", 8), ("Chorus", 8)], "feels": {"Verse": "verse", "Chorus": "lift"},
        "chords": {"verse": ["Cm9", "Abmaj7", "Fm9", "G7sus4"], "chorus": ["Abmaj7", "Bb", "Gm7", "Cm9"]},
        "themes": {"verse": [(0, 4, "Eb4"), (4, 4, "C4")], "chorus": ("L0", -12, 1.0, ())},  # the horn far away, then the call
    },
    "stop1_empty_classroom": {
        "title": "Stop 1: Empty Classroom", "style": "classroom", "textures": ["room"],
        "form": [("Verse", 8), ("Chorus", 8)], "feels": {"Verse": "verse", "Chorus": "lift"},
        "chords": {"verse": ["Fmaj7", "Dm9", "Bbmaj7", "C7sus4|C"], "chorus": ["Dm9", "Am7", "Bbmaj7", "C"]},
        "themes": {"verse": ("BELL", 0, 1.5, ()), "chorus": ("B", 0, 1.0, (2, 5, 8, 11))},  # the bell, then B emptied
    },
    "stop2_lost_and_found": {
        "title": "Stop 2: Lost and Found", "style": "lostfound", "textures": ["tape"],
        "form": [("Verse", 8), ("Chorus", 8)], "feels": {"Verse": "verse", "Chorus": "lift"},
        "chords": {"verse": ["Am9", "Fmaj7", "Dm9", "E7sus4|E7"], "chorus": ["Fmaj7", "G", "Em7", "Am9"]},
        "themes": {"verse": "HARU", "chorus": ("HARU", -12, 2.0, ())},
    },
    "stop4_waiting_room": {
        "title": "Stop 4: Waiting Room", "style": "waiting", "textures": ["hum"],
        "form": [("Verse", 8), ("Chorus", 8)], "feels": {"Verse": "verse", "Chorus": "lift"},
        "chords": {"verse": ["Dm9", "Dm9", "Ebmaj7", "Dm9"], "chorus": ["Bbmaj7", "Bbmaj7", "A7#5#9", "A7#5#9"]},
        # the Hum bent out of shape on the prepared piano, then once, clearly, on celesta (the reveal)
        "themes": {"verse": [(0, 1, "D5"), (1, 1, "Ab4"), (2, 1.5, "C5"), (3.5, .5, "B4"), (4, 1, "Ab4"), (6, 2, "A4")],
                   "chorus": ("H", 0, 2.0, ())},
        "theme_by_section": {"Verse": "sfz:piano_prepared", "Chorus": "celesta"},
    },
    "stop5_undertow": {
        "title": "Stop 5: Undertow", "style": "undertow", "textures": ["sea"],
        "form": [("Verse", 8), ("Chorus", 8)], "feels": {"Verse": "verse", "Chorus": "lift"},
        "chords": {"verse": ["Em9", "Cmaj7", "Am9", "B7sus4|B7"], "chorus": ["Cmaj7", "D", "Bm7", "Em9"]},
        "themes": {"verse": ("H", 2, 1.5, ()), "chorus": ("H", 2, 1.5, ())},  # the Hum, for Vance, on guitar
        "themes2": {"verse": [(0, 4, "G3"), (4, 4, "E3")]}, "theme2_inst": "sfz:trombone",  # the foghorn = L0, far off
    },
    "stop6_return_to_sender": {
        "title": "Stop 6: Return to Sender", "style": "radio_flat", "textures": ["radio"],
        "form": [("Verse", 8), ("Chorus", 8)], "feels": {"Verse": "verse", "Chorus": "lift"},
        "chords": {"verse": ["Fmaj7", "Am7", "Bbmaj7", "C7"], "chorus": ["Dm9", "Gm9", "C9", "Fmaj7"]},
        "themes": {"verse": "B", "chorus": "B"}, "theme_by_section": {"Chorus": "sfz:violins"},
    },
    "stop7_end_of_the_line": {
        "title": "Stop 7: End of the Line", "style": "convergence",
        "form": [("Carriage 1", 8), ("Carriage 2", 8), ("Carriage 3", 8), ("Carriage 4", 8), ("Carriage 5", 16)],
        "feels": {"Carriage 1": "s1", "Carriage 2": "s2", "Carriage 3": "s3", "Carriage 4": "s4", "Carriage 5": "s5"},
        "chords": {"Carriage 1": ["Fmaj7", "Dm9", "Bbmaj7", "C7sus4|C"], "Carriage 2": ["Fmaj7", "Dm9", "Bbmaj7", "C7sus4|C"],
                   "Carriage 3": ["Fmaj7", "E7", "Am7", "Gm7|C7"], "Carriage 4": ["Fmaj7", "E7", "Am7", "Gm7|C7"],
                   "Carriage 5": ["Bbmaj7", "C", "Am7", "Dm9", "Bbmaj7", "C", "Fmaj7", "Fmaj7"]},
        # drained Hum with notes missing; then B on flute (Mira); S on guitar (Soren) over H on cello (Kestrel);
        # B on vibraphone (Vesper) with scratches (Rook); everything: B on the band's lead, H and S together
        "themes": {"Carriage 1": ("H", 0, 1.0, (4, 5)), "Carriage 2": "B", "Carriage 3": "S", "Carriage 4": "B",
                   "Carriage 5": "B"},
        "theme_by_section": {"Carriage 1": "celesta", "Carriage 2": "flute", "Carriage 3": "sfz:guitar_clean",
                             "Carriage 4": "vibraphone", "Carriage 5": "sfz:trumpet"},
        "themes2": {"Carriage 3": ("H", -12, 2.0, ()), "Carriage 5": ("H", 0, 2.0, ())}, "theme2_inst": "sfz:cellos",
    },
}


def resolved(cue: dict) -> dict:
    """The cue's spec for engine.produce: motif names and (motif, semitones, stretch, dropped notes) tuples
    turned into note phrases."""
    spec = dict(cue)
    out = {}
    for k, v in (cue.get("themes") or {}).items():
        if isinstance(v, str):
            out[k] = _shift(MOTIFS[v])
        elif isinstance(v, tuple):
            out[k] = _shift(MOTIFS[v[0]], v[1], v[2], v[3])
        else:
            out[k] = v
    spec["themes"] = out
    out2 = {}
    for k, v in (cue.get("themes2") or {}).items():
        out2[k] = (_shift(MOTIFS[v]) if isinstance(v, str) else
                   _shift(MOTIFS[v[0]], v[1], v[2], v[3]) if isinstance(v, tuple) else v)
    spec["themes2"] = out2
    return spec


def make(cue_id: str, lib, seed: int = 21) -> tuple[str, int]:
    """Create the cue as an app song (an empty-headed lyric sheet sets its form), produce it and add it as a
    version. Returns (song id, version index)."""
    import json

    from . import engine
    from .production import add_version
    from .project import Project

    cue = CUES[cue_id]
    style = engine.STYLES[cue["style"]]
    starter = {"boss_choir": "boss_choir", "dungeon": "dungeon_pulse"}.get(cue["style"], "night_jazz")
    title = f"LINE ZERO cue: {cue['title']}"
    p = Project.create(starter, title)
    p.apply_lyrics(title + "\n" + "\n".join(f"[{name}, {bars} bars]" for name, bars in cue["form"]))
    p.save()
    built = p.build(lib)
    sid = built["song_id"]
    d = lib.song_dir(sid)
    record = json.loads((d / "song.json").read_text())
    base = record["versions"][-1]
    start, secs = 0, []
    for name, bars in cue["form"]:  # exactly the cue's form: no automatic outro, so loops loop
        secs.append({"name": name, "start": start, "bars": bars})
        start += bars
    base = {**base, "sections": secs, "section_feels": [cue["feels"][nm] for nm, _ in cue["form"]], "lyric_sheet": []}
    song, gains = engine.produce(resolved(cue), base, seed)
    vi = add_version(d, song, gains, f"{title} · {style['title']} (draft motifs)", base,
                     {"spec": {**base.get("spec", {}), "production": f"cue:{cue_id}"}, "cue": cue_id})
    record = json.loads((d / "song.json").read_text())
    lib.update_song(sid, record, vi)
    return sid, vi
