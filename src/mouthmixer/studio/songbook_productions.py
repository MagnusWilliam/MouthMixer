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
    vi = add_version(d, song, gains, title, base, {"spec": {**base.get("spec", {}), "production": f"engine:{spec['style']}:long"}})
    lib.update_song(sid, json.loads((d / "song.json").read_text()), vi)
    return sid, vi
