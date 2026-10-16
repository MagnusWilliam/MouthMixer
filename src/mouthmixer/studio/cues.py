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
    # L0: the Line 0 call: a falling minor third and the ticket punch (ka-CHK) as a 16th pickup (C minor)
    "L0": [(0, .75, "Eb5"), (.75, .25, "C5"), (1, .5, "C5"), (1.5, .5, "D5"), (2, .75, "Eb5"), (2.75, .25, "C5"),
           (3, 1, "G5"), (4, .75, "F5"), (4.75, .25, "Eb5"), (5, .5, "D5"), (5.5, .5, "C5"), (6, 1.5, "D5")],
}


def _shift(phrase, semis=0, stretch=1.0, drop=()):
    """A motif moved by semitones, slowed by `stretch`, with some notes left out (the forgetting)."""
    from .production import n

    return [(s * stretch, l * stretch, n(p) + semis) for i, (s, l, p) in enumerate(phrase) if i not in drop]


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
