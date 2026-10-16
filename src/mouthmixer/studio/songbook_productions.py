"""Produced bases for the songbook songs (docs/PERSONA_PRODUCTION.md §5): one style each, chords per
section, the song's own hook motif and the words the band hits on. `make(songbook_id)` creates the song the
way Make does (so the words, sections and Sing work), produces it with `engine` and adds it as a version.
"""

from __future__ import annotations

SPECS = {
    "02-off-the-clock": {
        "style": "citypop",  # G major, 112: P5 "Tokyo Daylight" / P4 daytime territory
        "chords": {"intro": ["Cmaj7", "Bm7", "Am7", "D7sus4|D"],
                   "verse": ["Cmaj7", "Bm7", "Em7", "A9", "Cmaj7", "Bm7", "Am7", "D7sus4|D"],
                   "chorus": ["Cmaj7", "D", "Bm7", "Em7", "Cmaj7", "D", "G", "G"],
                   "outro": ["Cmaj7", "Bm7", "Am7", "D7sus4|D"]},
        "hook": [(0, .5, "B4"), (.5, .5, "D5"), (1, 1, "E5"), (2.5, .5, "D5"), (3, 1, "B4")],
    },
    "03-wrong-side-of-midnight": {
        "style": "night_jazz",  # A minor, 86, swung: the hideout
        "chords": {"intro": ["Am9", "Fmaj7", "Am9", "E7#5#9"],
                   "verse": ["Am9", "Dm9", "Bm7b5", "E7#5#9"],
                   "chorus": ["Fmaj7", "E7#5#9", "Am9", "Am9", "Dm9", "G7", "Cmaj7", "E7#5#9"],
                   "outro": ["Am9", "Fmaj7", "Am9", "Am9"]},
        "hook": [(0, .5, "E4"), (.5, .5, "G4"), (1, 1.5, "A4"), (3, .5, "C5"), (3.5, 2, "B4")],
    },
    "04-pull-the-brake": {
        "style": "battle_rush",  # E minor, 158: hits from the first beat
        "chords": {"intro": ["Em9", "B7#5#9"],
                   "chorus": ["Cmaj7", "D", "Bm7", "Em9"],
                   "rap": ["Em9", "Cmaj7", "Am9", "B7#5#9"],
                   "pre": ["Am9", "Bm7", "Cmaj7", "B7#5#9"],
                   "outro": ["Em9", "Em9", "Em9", "Em9"]},
        "hook": [(0, .5, "E5"), (.5, .5, "G5"), (1, .5, "A5"), (1.5, 1, "B5"), (3, .5, "A5"), (3.5, .5, "G5")],
        "hits": ["hey", "brake", "shake"],
    },
    "05-rain-delay": {
        "style": "bossa",  # D major, 132: a busy little groove under slow words
        "chords": {"intro": ["Dmaj7", "Bm7", "Em9", "A9"],
                   "verse": ["Dmaj7", "Bm7", "Em9", "A9", "F#m7", "B7", "Em7", "A7sus4|A7"],
                   "chorus": ["Gmaj7", "F#m7", "Em9", "A9", "Gmaj7", "F#m7", "Bm7|E9", "Em7|A7"],
                   "outro": ["Dmaj7", "Bm7", "Em9", "A9"]},
        "hook": [(0, 1, "A4"), (1, 1, "F#4"), (2, .5, "E4"), (2.5, 1.5, "D4")],  # the sigh: "rain de-lay"
    },
    "06-no-ticket-home": {
        "style": "boss_choir",  # C minor, 150: big slow words over a fast orchestra
        "chords": {"intro": ["Cm9", "Dbmaj7", "Cm9", "G7#5#9"],
                   "verse": ["Cm9", "Abmaj7", "Bb", "G7#5#9"],
                   "pre": ["Fm9", "Abmaj7", "Bb", "G7#5#9"],
                   "chorus": ["Abmaj7", "Bb", "Gm7", "Cm9", "Abmaj7", "Bb", "Dbmaj7", "G7#5#9"],
                   "bridge": ["Abmaj7", "Gm7", "Fm9", "G7sus4"],
                   "outro": ["Cm9", "Cm9", "Cm9", "Cm9"]},
        "hook": [(0, 1, "C5"), (1, 1, "Eb5"), (2, 1, "G5"), (3, 1, "F5")],
        "hits": ["not yours"],
    },
    "08-return-to-sender": {
        "style": "ballad",  # F major, 76; quotes the main theme's "Ride, ride, ride" line (same notes as in D minor)
        "chords": {"intro": ["Fmaj7", "Bbmaj7", "Fmaj7", "C7sus4|C"],
                   "verse": ["Fmaj7", "Am7", "Bbmaj7", "C7sus4|C"],
                   "pre": ["Dm7", "Am7", "Bbmaj7", "C"],
                   "chorus": ["Bbmaj7", "C", "Am7", "Dm9", "Bbmaj7", "C", "Fmaj7", "Fmaj7"],
                   "outro": ["Fmaj7", "Bbmaj7", "Fmaj7", "Fmaj7"]},
        "hook": [(0, .75, "D5"), (.75, .75, "F5"), (1.5, 1, "G5"), (2.5, .5, "F5"), (3, .5, "E5"), (3.5, 1, "F5"),
                 (4.5, 2.5, "E5")],
    },
}


def make(songbook_id: str, lib, seed: int = 11) -> tuple[str, int]:
    """Create the songbook song through Make (lyrics, sections, a first build), produce its base with the
    engine and add it as a version. Returns (song id, version index)."""
    import json

    from . import engine, songbook
    from .production import add_version
    from .project import Project

    sb = songbook.get(songbook_id)
    spec = SPECS[songbook_id]
    p = Project.create(sb["starter"], sb["title"])
    p.apply_lyrics(sb["lyrics"])
    p.data["songbook"] = {k: sb.get(k, "") for k in ("id", "slot", "voices", "hits", "notes")}
    p.save()
    built = p.build(lib)
    sid = built["song_id"]
    d = lib.song_dir(sid)
    record = json.loads((d / "song.json").read_text())
    base = record["versions"][-1]
    song, gains = engine.produce(spec, base, seed)
    title = sb["title"] + " · " + engine.STYLES[spec["style"]]["title"] + " (base)"
    vi = add_version(d, song, gains, title, base, {"spec": {**base.get("spec", {}), "production": f"engine:{spec['style']}"}})
    record = json.loads((d / "song.json").read_text())
    lib.update_song(sid, record, vi)
    return sid, vi
