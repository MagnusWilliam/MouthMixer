"""The production engine (studio/engine.py): melody writer and a whole songbook song on a generated version."""

import numpy as np

from mouthmixer.arrange import lyrics as LY
from mouthmixer.studio import engine as E
from mouthmixer.studio import songbook_productions as SB
from mouthmixer.studio.production import chord, tones


def test_line_rhythm_puts_stress_on_beats_and_holds_the_end():
    syl = LY.line_syllables("Rain delay, rain delay")
    r = E.line_rhythm(syl, 8.0, pickup=False, dense_ok=False)
    assert len(r) == len(syl)
    assert all(b[0] >= a[0] + a[1] for a, b in zip(r, r[1:]))  # no overlaps
    assert r[-1][1] >= 1.0 and r[-1][0] + r[-1][1] <= 7.6  # held last note, a breath before the next line
    long = LY.line_syllables("we tear the dark from the end of the track and the whole of the night")
    r2 = E.line_rhythm(long, 8.0, pickup=False, dense_ok=True)
    assert len(r2) == len(long) and r2[-1][0] + r2[-1][1] <= 7.6


def _version(sections, lines_by_section):
    secs, sheet, start = [], [], 0
    for name, bars, feel in sections:
        secs.append({"name": name, "start": start, "bars": bars})
        if lines_by_section.get(name):
            sheet.append({"section": name, "start": start * 4, "beats": bars * 4, "lines": lines_by_section[name],
                          "mode": "sung"})
        start += bars
    return {"sections": secs, "section_feels": [f for _, _, f in sections], "lyric_sheet": sheet}


def test_engine_produces_a_whole_song_with_a_singable_guide():
    v = _version([("Intro", 4, "intro"), ("Verse 1", 8, "verse"), ("Chorus", 8, "lift"), ("Outro", 4, "outro")],
                 {"Verse 1": ["Morning light on a quiet street", "coffee cold and the city hums",
                              "every window a different song", "and the day has just begun"],
                  "Chorus": ["Off the clock, off the clock", "nothing waits for me today",
                             "Off the clock, off the clock", "let the hours drift away"]})
    song, gains = E.produce(SB.SPECS["02-off-the-clock"], v, seed=3)
    assert song.bars == 24 and abs(song.bpm - 112) < 1e-9
    mel = next(t for t in song.tracks if t.role == "lead").notes
    assert mel and 57 <= min(p for _, _, p, _ in mel) and max(p for _, _, p, _ in mel) <= 67
    # repeated lines are sung the same way (the hook)
    span = 8.0
    c0 = song.sections[2][1] * 4
    first = [(s - c0, p) for s, _, p, _ in mel if c0 <= s < c0 + span]
    third = [(s - c0 - 2 * span, p) for s, _, p, _ in mel if c0 + 2 * span <= s < c0 + 3 * span]
    assert first == third
    # strong-beat melody notes are mostly chord tones
    strong = [(s, p) for s, l, p, _ in mel if abs(s - round(s)) < 1e-6]
    ct = sum(p % 12 in tones(next(c for st, ln, c in [(a, b, c.name) for a, b, c in song.chords] if st <= s < st + ln))
             for s, p in strong)
    assert ct / len(strong) >= 0.7
    roles = {t.role for t in song.tracks}
    assert {"drums", "bass", "comp", "lead"} <= roles


def test_every_songbook_spec_has_chords_for_its_style():
    for sid, spec in SB.SPECS.items():
        assert spec["style"] in E.STYLES and "verse" in spec["chords"] or "chorus" in spec["chords"], sid
        for prog in spec["chords"].values():
            for c in prog:
                for part in c.split("|"):
                    chord(part)  # parses


def test_extension_keeps_the_words_and_reaches_two_minutes():
    from mouthmixer.studio import songbook

    sb = songbook.get("02-off-the-clock")
    long = SB.extended_lyrics(sb["lyrics"], 112)
    words = lambda t: sorted(l for l in t.splitlines() if l and not l.startswith("["))  # noqa: E731
    assert set(words(long)) == set(words(sb["lyrics"]))  # no new words, only repeats
    heads = [l for l in long.splitlines() if l.startswith("[")]
    assert any(h.startswith("[Solo") for h in heads) and heads[0].startswith("[Intro, 8 bars")
    already = songbook.get("08-return-to-sender")
    assert SB.extended_lyrics(already["lyrics"], 76) == already["lyrics"]  # long enough already


def test_walking_bass_and_soft_night_styles():
    v = _version([("Verse 1", 4, "verse")], {})
    spec = dict(SB.SPECS["03-wrong-side-of-midnight"], style="night_trio")
    song, gains = E.produce(spec, v, seed=2)
    bass = next(t for t in song.tracks if t.role == "bass").notes
    assert len(bass) == 16 and all(abs(l - 0.9) < 1e-6 for _, l, _, _ in bass)  # quarter notes
    assert not [t for t in song.tracks if t.role == "drums"]
    _, g2 = E.produce(dict(spec, style="night_brushes"), v, seed=2)
    assert g2["Drums"] <= -7
