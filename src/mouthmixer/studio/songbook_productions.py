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
    # The era songs of LINE ZERO's rotation (AUDIO_PLAN 3.2b), each in a distinct Persona sound.
    "09-second-platform": {
        "style": "p3_urban",  # B minor, 96: boom-bap, piano loop, string stabs, scratches
        "chords": {"intro": ["Bm9", "Gmaj7", "Bm9", "Gmaj7"],
                   "verse": ["Bm9", "Gmaj7", "Em9", "F#7#5#9"],
                   "pre": ["Gmaj7", "A6/9", "F#m7", "Bm9"],
                   "chorus": ["Gmaj7", "A", "F#m7", "Bm9", "Gmaj7", "A", "Em9", "F#7#5#9"],
                   "bridge": ["Em9", "F#m7", "Gmaj7", "F#7sus4|F#7"],
                   "outro": ["Bm9", "Gmaj7", "Bm9", "Bm9"]},
        "hook": [(0, .5, "F#5"), (.5, .5, "D5"), (1, 1, "B4"), (2.5, .5, "C#5"), (3, 1, "D5")],
    },
    "10-hold-the-door": {
        "style": "p4_jpop",  # E major, 120: piano 8ths, crunchy guitars, the royal-road chorus
        "chords": {"intro": ["Emaj7", "B", "C#m7", "Amaj7"],
                   "verse": ["Emaj7", "C#m7", "Amaj7", "B"],
                   "pre": ["C#m7", "G#m7", "Amaj7", "B7sus4|B"],
                   "chorus": ["Amaj7", "B", "G#m7", "C#m7", "Amaj7", "B", "E", "E"],
                   "bridge": ["F#m7", "G#m7", "Amaj7", "B7sus4|B"],
                   "outro": ["Amaj7", "B", "E", "E"]},
        "hook": [(0, .5, "B4"), (.5, .5, "E5"), (1, .5, "F#5"), (1.5, 1.5, "G#5"), (3, .5, "F#5"), (3.5, .5, "E5")],
        "hits": ["hold the door"],
    },
    "11-off-the-rails": {
        "style": "p5_heavy",  # G minor, 166: organ, distorted guitar, brass, driving 16ths
        "chords": {"intro": ["Gm9", "D7#5#9"],
                   "chorus": ["Ebmaj7", "F", "Dm7", "Gm9"],
                   "rap": ["Gm9", "Ebmaj7", "Cm9", "D7#5#9"],
                   "pre": ["Cm9", "Dm7", "Ebmaj7", "D7#5#9"],
                   "bridge": ["Ebmaj7", "Dm7", "Cm9", "D7sus4"],
                   "outro": ["Gm9", "Gm9", "Gm9", "Gm9"]},
        "hook": [(0, .5, "G4"), (.5, .5, "Bb4"), (1, .5, "C5"), (1.5, 1, "D5"), (3, .5, "C5"), (3.5, .5, "Bb4")],
        "hits": ["off the rails", "slow down"],
    },
    "12-punch-the-ticket": {
        "style": "anthem",  # A minor, 140: band, organ, strings, choir on the hook
        "chords": {"intro": ["Am9", "Fmaj7", "G", "E7#5#9"],
                   "verse": ["Am9", "Fmaj7", "C", "G"],
                   "pre": ["Dm9", "Fmaj7", "G", "E7#5#9"],
                   "chorus": ["Fmaj7", "G", "Em7", "Am9", "Fmaj7", "G", "C", "E7#5#9"],
                   "bridge": ["Fmaj7", "Em7", "Dm9", "E7sus4|E"],
                   "outro": ["Am9", "Fmaj7", "Am9", "Am9"]},
        "hook": [(0, 1, "A4"), (1, 1, "C5"), (2, 1, "E5"), (3, .5, "D5"), (3.5, .5, "C5"), (4, 2, "B4")],
        "hits": ["here we go"],
    },
    # Inspired by the user's reference folder (PERSONA_PRODUCTION section 9). Original chords and hooks built from
    # each reference's measured favourite moves (reference/analyse.py); nothing copied.
    "13-hollow-hour": {  # Burn My Dread: the flat II (Gb), iv7 to bvii7
        "style": "ref_dread",
        "chords": {"intro": ["Fm9", "Gbmaj7", "Fm9", "Gbmaj7"],
                   "verse": ["Fm9", "Gbmaj7", "Bbm9|Ebm7", "Dbmaj7|C7#5#9"],
                   "pre": ["Bbm9", "Ebm7", "Abmaj7", "C7sus4|C7#5#9"],
                   "chorus": ["Dbmaj7", "Gbmaj7", "Bbm9|Ebm7", "Fm9", "Dbmaj7", "Gbmaj7", "Bbm9|C7#5#9", "Fm9"],
                   "rap": ["Fm9", "Fm9|Gbmaj7", "Bbm9", "Bbm9|C7#5#9"],
                   "bridge": ["Gbmaj7", "Abmaj7", "Bbm9", "C7sus4|C7"],
                   "outro": ["Fm9", "Gbmaj7", "Fm9", "Fm9"]},
        "hook": [(0, 1, "C5"), (1, .5, "Db5"), (1.5, 1.5, "C5"), (3, .5, "Ab4"), (3.5, .5, "G4")],
    },
    "14-paint-the-city": {  # Color Your Night: vi7 to V, ii7 to iii7, IVmaj7 to II7, two beats a chord
        "style": "ref_colour",
        "chords": {"intro": ["Gbmaj7|Fm7", "Ebm7|Ab", "Gbmaj7|Fm7", "Bbm7|Ab"],
                   "verse": ["Dbmaj7|Ebm7", "Fm7|Bbm7", "Gbmaj7|Fm7", "Ebm7|Ab"],
                   "pre": ["Gbmaj7", "F7", "Bbm7|Ab", "Gbmaj7|Ab7sus4"],
                   "chorus": ["Gbmaj7|Eb7", "Fm7|Bbm7", "Gbmaj7|Ab", "Dbmaj7", "Gbmaj7|Eb7", "Fm7|Bbm7", "Ebm7|Ab7sus4",
                              "Dbmaj7"],
                   "rap": ["Bbm7|Ab", "Ebm7|Fm7", "Bbm7|Ab", "Gbmaj7|F7"],
                   "bridge": ["Bbm7", "Fm7", "Gbmaj7", "Ab7sus4|Ab"],
                   "outro": ["Gbmaj7|Fm7", "Ebm7|Ab", "Dbmaj7", "Dbmaj7"]},
        "hook": [(0, .5, "Ab4"), (.5, .5, "Bb4"), (1, 1, "Db5"), (2.5, .5, "C5"), (3, 1, "Ab4")],
    },
    "15-high-tide": {  # Full Moon Full Life: iii7 to VI7 to ii7, IVmaj7 to Imaj7, bVImaj7 to vi7
        "style": "ref_tide",
        "chords": {"intro": ["Dmaj7", "E", "C#m7", "F#m7"],
                   "verse": ["Amaj7|E", "F#m7|C#m7", "Dmaj7|Amaj7", "Bm7|E"],
                   "pre": ["Dmaj7", "E", "C#m7|F#7", "Bm7|E7sus4"],
                   "chorus": ["Dmaj7|C#m7", "F#7|Bm7", "Dmaj7|E", "Amaj7", "Dmaj7|C#m7", "F#7|Bm7", "Fmaj7|E7sus4", "Amaj7"],
                   "rap": ["F#m7", "Dmaj7", "Bm7", "E7sus4|E"],
                   "bridge": ["Fmaj7", "F#m7", "Dmaj7", "E7sus4|E"],
                   "outro": ["Dmaj7", "E", "Amaj7", "Amaj7"]},
        "hook": [(0, .5, "E5"), (.5, .5, "F#5"), (1, 1, "A5"), (2, .5, "G#5"), (2.5, .5, "F#5"), (3, 1, "E5")],
        "hits": ["high tide"],
    },
    "16-down-to-the-wire": {  # It's Going Down Now: bIIImaj7, bVImaj7 to v7, the half-step slide IImaj7 to bIIImaj7
        "style": "ref_wire",
        "chords": {"intro": ["Dm9", "Fmaj7|Am7", "Bbmaj7|Am7", "Gm9|A7#5#9"],
                   "verse": ["Dm9", "Fmaj7|Am7", "Bbmaj7|Am7", "Gm9|A7sus4"],
                   "pre": ["Bbmaj7|Am7", "Gm9|Fmaj7", "Emaj7|Fmaj7", "Gm9|A7#5#9"],
                   "chorus": ["Bbmaj7", "Am7", "Gm9", "Dm9", "Bbmaj7", "Am7", "Emaj7|Fmaj7", "Gm9|A7#5#9"],
                   "rap": ["Dm9", "Dm9|Fmaj7", "Gm9", "Am7|A7#5#9"],
                   "bridge": ["Bbmaj7", "Am7", "Gm9", "A7sus4|A7#5#9"],
                   "outro": ["Dm9", "Bbmaj7", "A7#5#9", "Dm9"]},
        "hook": [(0, .5, "D5"), (.5, .5, "F5"), (1, .5, "A5"), (1.5, 1, "G5"), (3, .5, "F5"), (3.5, .5, "E5")],
        "hits": ["down to the wire", "take it"],
    },
    "17-safety-off": {  # Pull the Trigger + A Way of Life: bIIImaj7 to IIsus4 to i7; Imaj7 and bVImaj7 in the outro
        "style": "ref_safety",
        "chords": {"intro": ["Em9", "Gmaj7|F#7sus4", "Em9", "Cmaj7|B7#5#9"],
                   "verse": ["Em9", "Gmaj7|F#7sus4", "Em9|Am7", "Cmaj7|Bm7"],
                   "pre": ["Am7", "Bm7", "Cmaj7", "B7sus4|B7#5#9"],
                   "chorus": ["Cmaj7", "Bm7", "Em9", "Gmaj7|F#7sus4", "Cmaj7", "Bm7", "Am7|B7sus4", "Em9"],
                   "rap": ["Em9|Gmaj7", "F#7sus4|Em9", "Cmaj7|Bm7", "Am7|B7sus4"],
                   "bridge": ["Cmaj7", "D", "Bm7", "F#7sus4|B7sus4"],
                   "outro": ["Cmaj7", "Emaj7", "Cmaj7", "Emaj7"]},
        "hook": [(0, 1, "B4"), (1, .5, "D5"), (1.5, 1, "E5"), (3, .5, "D5"), (3.5, .5, "B4")],
    },
    "18-lunchbell": {  # School Days + Signs of Love: major sevenths sliding up a step, Vmaj7 to iii7, ii7 to IVmaj7
        "style": "ref_lunch",
        "chords": {"intro": ["Amaj7|G#m7", "F#m7|Emaj7", "Amaj7|G#m7", "F#maj7|B7sus4"],
                   "verse": ["Emaj7|G#m7", "Amaj7|G#m7", "F#m7|Amaj7", "Bmaj7|G#m7"],
                   "pre": ["F#maj7", "G#maj7", "Amaj7|G#m7", "F#m7|B7sus4"],
                   "chorus": ["Amaj7|G#m7", "F#m7|Emaj7", "Amaj7|G#m7", "F#m7|B7sus4", "Amaj7|G#m7", "C#m7|F#maj7",
                              "F#m7|B7sus4", "Emaj7"],
                   "bridge": ["C#m7", "G#m7", "Amaj7", "B7sus4|B"],
                   "outro": ["Amaj7|G#m7", "F#m7|B7sus4", "Emaj7", "Emaj7"]},
        "hook": [(0, .5, "B4"), (.5, .5, "E5"), (1, .5, "G#5"), (1.5, 1, "F#5"), (3, .5, "E5"), (3.5, .5, "D#5")],
    },
    "19-reach-for-the-stars": {  # When the Moon's Reaching Out Stars: ii7 and iii7 into IVmaj7, IIsus4 to vi7, bVIImaj7
        "style": "ref_moon",
        "chords": {"intro": ["Ebmaj7|Dm7", "Cm7|F7sus4", "Ebmaj7|Dm7", "Gm7|C7sus4"],
                   "verse": ["Bbmaj7|Gm7", "Cm7|Ebmaj7", "Dm7|Ebmaj7", "C7sus4|Gm7"],
                   "pre": ["Ebmaj7", "Dm7|Gm7", "Cm7|Ebmaj7", "F7sus4|F7"],
                   "chorus": ["Ebmaj7|Dm7", "Cm7|Ebmaj7", "Gm7|Bbmaj7", "Abmaj7|F7sus4", "Ebmaj7|Dm7", "Cm7|Ebmaj7",
                              "Gm7|C7sus4", "Ebmaj7|F7sus4"],
                   "bridge": ["Gm7", "Dm7", "Ebmaj7", "F7sus4|F7"],
                   "outro": ["Ebmaj7|Dm7", "Cm7|F7sus4", "Bbmaj7", "Bbmaj7"]},
        "hook": [(0, .5, "F5"), (.5, .5, "G5"), (1, 1, "Bb5"), (2.5, .5, "A5"), (3, 1, "G5")],
    },
}


def make(songbook_id: str, lib, seed: int = 11) -> tuple[str, int]:
    """Create the songbook song through Make (lyrics, sections, a first build), produce its base with the
    engine and add it as a version. Returns (song id, version index)."""
    import json

    from ..arrange import render
    from . import engine, songbook
    from .production import add_version
    from .project import Project

    sb = songbook.get(songbook_id)
    spec = SPECS[songbook_id]
    p = Project.create(sb["starter"], sb["title"])
    bpm = spec.get("bpm", engine.STYLES[spec["style"]]["bpm"])
    p.apply_lyrics(extended_lyrics(sb["lyrics"], bpm))  # vocal songs run at least two minutes (the user's ask)
    if sum(s_["bars"] for s_ in p.data["sections"]) * 240 / bpm < 120:
        p.apply_lyrics(extended_lyrics(sb["lyrics"], bpm, 150, force=True))
    p.data["songbook"] = {k: sb.get(k, "") for k in ("id", "slot", "voices", "hits", "notes")}
    p.save()
    built = p.build(lib)
    sid = built["song_id"]
    d = lib.song_dir(sid)
    record = json.loads((d / "song.json").read_text())
    base = record["versions"][-1]
    song, gains = engine.produce(spec, base, seed)
    title = sb["title"] + " · " + engine.STYLES[spec["style"]]["title"] + " (base)"
    vi = add_version(d, song, gains, title, base, {"spec": {**base.get("spec", {}), "production": f"engine:{spec['style']}"}},
                     tone_target=render.ref_bands(engine.STYLES[spec["style"]].get("refs", [])))
    record = json.loads((d / "song.json").read_text())
    lib.update_song(sid, record, vi)
    return sid, vi


def _blocks(lyrics: str) -> tuple[str, list[tuple[str, list[str]]]]:
    """(title line, [(header, lines)]) from a songbook lyric sheet."""
    title, blocks = "", []
    for raw in lyrics.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("[") and line.endswith("]"):
            blocks.append((line[1:-1], []))
        elif blocks:
            blocks[-1][1].append(line)
        else:
            title = title or line
    return title, blocks


def extended_lyrics(lyrics: str, bpm: float, min_seconds: float = 130.0, force: bool = False) -> str:
    """The same words in a longer form (the user asked for vocal songs of at least two minutes): an 8-bar
    intro (unless it's a battle cold open), an instrumental Solo before the last chorus, the chorus once more
    at the end and an 8-bar outro; more solos until the song is long enough. Never new words."""
    from .project import Project  # noqa: F401  (apply_lyrics' rules decide the bar counts)

    title, blocks = _blocks(lyrics)
    chorus = next((b for b in blocks if b[0].lower().startswith(("chorus", "hook"))), None)
    pre = next((b for b in blocks if b[0].lower().startswith("pre")), None)
    out = []
    for h, lines in blocks:
        low = h.lower()
        if low.startswith("intro") and not any(w in low for w in ("shout", "hit", "fast")) and "bars" not in low:
            h = h.split(",")[0] + ", 8 bars" + ("," + ",".join(h.split(",")[1:]) if "," in h else "")
        if low.startswith(("outro", "ending")) and "bars" not in low:
            h = h.split(",")[0] + ", 8 bars" + ("," + ",".join(h.split(",")[1:]) if "," in h else "")
        out.append((h, lines))
    last = max((i for i, (h, _) in enumerate(out) if h.lower().startswith(("chorus", "hook", "final"))), default=len(out) - 1)
    extra = [("Solo, 8 bars", [])]
    out = out[:last] + extra + out[last:]
    if chorus:
        end = next((i for i, (h, _) in enumerate(out) if h.lower().startswith(("outro", "ending"))), len(out))
        out = out[:end] + [(chorus[0], chorus[1])] + out[end:]
    if not any(h.lower().startswith(("outro", "ending")) for h, _ in out):
        out.append(("Outro, 8 bars", []))

    def text(blocks_):
        return title + "\n\n" + "\n\n".join("[" + h + "]\n" + "\n".join(ls) for h, ls in blocks_)

    def seconds(blocks_):
        bars = 0
        for h, ls in blocks_:
            import re as _re

            m = _re.search(r"(\d+)\s*bars?", h)
            if m:
                bars += int(m.group(1))
            elif not ls:
                bars += 8
            else:
                bars += next(b for b in (4, 8, 12, 16) if b >= min(max(4, len(ls) * (1 if h.lower().startswith("rap") and bpm >= 110 else 2)), 16))
        return bars * 4 * 60 / bpm

    if seconds(blocks) >= min_seconds and not force:  # long enough already: the song as written
        return lyrics
    k = 2
    while seconds(out) < min_seconds and k < 5 and chorus:
        at = max(i for i, (h, _) in enumerate(out) if h.lower().startswith(("chorus", "hook", "final")))
        more = [(f"Solo {k}, 8 bars", [])] + ([pre] if pre else []) + [(chorus[0], chorus[1])]
        out = out[:at] + more + out[at:]
        k += 1
    return text(out)


def extend(songbook_id: str, lib, style: str | None = None, label: str | None = None, seed: int = 11) -> tuple[str, int]:
    """A longer version (at least two minutes) of a produced songbook song, optionally in another style (the
    Wrong Side of Midnight alternatives), added to the same song as a new version."""
    import json

    from ..arrange import render
    from . import engine, songbook
    from .production import add_version
    from .project import Project, _feels

    sb = songbook.get(songbook_id)
    spec = dict(SPECS[songbook_id])
    if style:
        spec["style"] = style
    st = engine.STYLES[spec["style"]]
    sid = next(r["id"] for r in lib.list_songs(["new", "kept", "tossed"]) if r["title"].startswith(sb["title"] + " ·")
               and json.loads((lib.song_dir(r["id"]) / "song.json").read_text())["versions"][-1].get("spec", {})
               .get("production", "").startswith("engine:"))
    d = lib.song_dir(sid)
    record = json.loads((d / "song.json").read_text())
    pid = record["versions"][0].get("spec", {}).get("project") or record.get("project")
    p = Project.load(pid)
    bpm = spec.get("bpm", st["bpm"])
    p.apply_lyrics(extended_lyrics(sb["lyrics"], bpm))
    if sum(s_["bars"] for s_ in p.data["sections"]) * 4 * 60 / bpm < 120:  # the estimate was short: measure, force
        p.apply_lyrics(extended_lyrics(sb["lyrics"], bpm, 150, force=True))
    p.save()
    start, secs = 0, []
    for s in p.data["sections"]:
        secs.append({"name": s["name"], "start": start, "bars": s["bars"]})
        start += s["bars"]
    base = {**record["versions"][0], "sections": secs, "section_feels": _feels(p.data["sections"], p.st.get("mood", "")),
            "lyric_sheet": p.lyric_sheet()}
    song, gains = engine.produce(spec, base, seed)
    title = sb["title"] + " · " + st["title"] + (f" ({label})" if label else " (long)")
    vi = add_version(d, song, gains, title, base, {"spec": {**base.get("spec", {}), "production": f"engine:{spec['style']}:long"}},
                     tone_target=render.ref_bands(st.get("refs", [])))
    lib.update_song(sid, json.loads((d / "song.json").read_text()), vi)
    return sid, vi
