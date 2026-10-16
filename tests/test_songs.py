"""Song structure (section feels, lyrics -> form), the songbook, free singing, voice characters, vocal
accent hits and favourites."""

from pathlib import Path

import numpy as np
import pytest

from mouthmixer import synth as S
from mouthmixer.arrange import critic
from mouthmixer.arrange import vocals as V
from mouthmixer.studio import songbook, starters
from mouthmixer.studio.project import Project

LYRICS = (Path(__file__).parent / "data_last_train.txt").read_text(encoding="utf-8")


def _drums(feel, sid="battle_funk", bars=4, next_feel=None):
    st = dict(starters.STARTERS[sid], id=sid)
    chords = starters.progression(st["a"], st["tonic"], st["ext"], bars)
    return starters.generate("drums", st, chords, (0, bars), feel=feel, next_feel=next_feel), st, chords


def test_section_feels_change_the_beat():
    verse, st, chords = _drums("verse")
    lift, _, _ = _drums("lift")
    rap, _, _ = _drums("rap")
    assert _drums("breakdown")[0] == []  # drums out
    assert len(lift) > len(verse) and any(n[2] == 46 for n in lift)  # open hats in the chorus
    snares = sorted({round(n[0] % 4, 2) for n in rap if n[2] == 38 and n[3] > 80})
    assert snares == [2.0]  # rap pocket: half-time, the backbeat only on beat 3
    intro = starters.generate("drums", st, chords, (0, 4), feel="intro")
    assert any(n[2] == 49 and n[0] >= 8 for n in intro) and any(n[2] == 38 and n[0] >= 14 for n in intro)  # hits, then a roll
    fx = starters.generate("fx", st, chords, (0, 8), feel="verse", next_feel="lift")
    assert fx and fx[0][0] == 30  # a riser into the chorus
    chime = starters.generate("chime", st, chords, (0, 4), feel="intro")
    assert len(chime) == 3 and chime[0][2] > chime[-1][2]  # three falling notes


def test_lyrics_lay_out_the_song(home):
    p = Project.create("battle_funk")
    secs = p.apply_lyrics(LYRICS)
    assert p.data["title"] == "LAST TRAIN, FIRST LIGHT"
    names = [s["name"] for s in secs]
    assert names == ["Intro", "Verse 1", "Pre-Chorus", "Chorus", "Rap Verse", "Bridge", "Bridge build",
                     "Final Chorus", "Outro"]
    feels = p.public()["section_feels"]
    assert feels[names.index("Rap Verse")] == "rap" and feels[names.index("Chorus")] == "lift"
    assert feels[names.index("Final Chorus")] == "final" and feels[names.index("Bridge")] == "breakdown"
    assert next(s for s in secs if s["name"] == "Chorus")["bars"] == 16  # 8 lines x 2 bars
    assert next(s for s in secs if s["name"] == "Bridge")["chords"] == "B"
    sheet = p.lyric_sheet()
    assert sheet[0]["mode"] == "spoken" and next(x for x in sheet if x["section"] == "Rap Verse")["mode"] == "rap"
    final = next(x for x in sheet if x["section"] == "Final Chorus")
    assert len(final["lines"]) == 9  # the chorus again, plus "(Next stop: tomorrow.)"
    song, _ = p.song()
    assert not critic.judge(song)["rejects"]


def test_songbook_songs_all_start_and_fit():
    songs = songbook.songs()
    assert len(songs) == 19
    for s in songs:
        assert s["starter"] in starters.STARTERS and s["lyrics"].count("[") >= 3 and s["voices"]


def test_songbook_song_builds_clean(home):
    for s in songbook.songs():
        p = Project.create(s["starter"], s["title"])
        secs = p.apply_lyrics(s["lyrics"])
        assert len({x["name"] for x in secs}) == len(secs)  # repeated headers get numbered
        song, _ = p.song()
        assert not critic.judge(song)["rejects"], s["title"]


def _sung(spans_beats, bpm, seed, detune=40):
    rng = np.random.default_rng(seed)
    scale = [62, 64, 65, 67, 69, 70, 72]  # D minor
    notes = []
    for a, b in spans_beats:
        t = a
        while t < b - 1:
            notes.append((t, 0.9, int(rng.choice(scale))))
            t += 1
    x, _ = S.sing(notes, bpm, pre_roll=0.0, detune_cents=detune, sibilants=0.2, breaths=False, seed=seed)
    return x * 0.7


def test_free_singing_is_tuned_to_the_key_but_rap_is_left_alone():
    bpm = 120
    secs = [{"name": "Verse", "start": 1, "bars": 2}, {"name": "Rap", "start": 3, "bars": 2}]
    x = _sung([(4, 12), (12, 20)], bpm, 3)
    tk = V.Take(x, 0.0, "t1")
    res = V.produce_free([tk], bpm, secs, 2, "minor", "bright_pop", len(x) / V.SR + 0.5, {"Rap": "rap"})
    q = res.report["quality"]
    assert res.report["untuned_sections"] == ["Rap"] and q["in_key_frames"] >= 0.8
    f0b, _ = V.track_f0(tk.audio)
    t = np.arange(len(res.f0_after)) * V.FRAME_MS / 1000
    rap = (t > 6.2) & (t < 9.8) & (res.f0_after > 0)
    ref = np.interp(t[rap], np.arange(len(f0b)) * V.FRAME_MS / 1000, f0b)
    ok = ref > 0
    assert np.median(np.abs(res.f0_after[rap][ok] / ref[ok] - 1)) < 0.01  # the rap keeps its own pitch


def _centroid(y):
    sp = np.abs(np.fft.rfft(y[: 2 ** 16]))
    f = np.fft.rfftfreq(2 ** 16, 1 / V.SR)
    return float((sp * f).sum() / sp.sum())


def test_voice_characters():
    x, _ = S.sing([(0, 2, 60), (2, 2, 64), (4, 2, 62)], 100, pre_roll=0.2, sibilants=0, breaths=False, seed=5)
    f0, _ = V.track_f0(x)
    an = V.world_passages(x, f0)
    up = V.voice_variant(x, f0, formant=1.18, analysis=an)
    down = V.voice_variant(x, f0, formant=0.86, analysis=an)
    assert _centroid(down) < _centroid(x) < _centroid(up)  # formants move the tone, not the notes
    oct_up = V.voice_variant(x, f0, octave=1, analysis=an)
    f_up, _ = V.track_f0(oct_up)
    both = (f_up > 0) & (f0[: len(f_up)] > 0)
    assert abs(np.median(f_up[both] / f0[: len(f_up)][both]) - 2.0) < 0.1
    wh = V.voice_variant(x, f0, whisper=True, analysis=an)
    f_wh, _ = V.track_f0(wh)
    assert (f_wh > 0).mean() < 0.3 * max((f0 > 0).mean(), 1e-6) + 0.05  # a whisper has no pitch
    rep = {}
    main, stack = V.apply_character(x, f0, "gang", rep)
    assert stack is not None and stack.shape[0] == 2 and np.abs(stack).max() > 0.001 and rep["stack_voices"] == 5
    pa, _ = V.apply_character(x, f0, "announcer", {})
    assert _centroid(pa) > 300


def test_band_hits_land_on_vocal_accents():
    from mouthmixer.arrange.mixer import accent_times

    bpm = 120
    quiet = [(b, 0.45, 64) for b in np.arange(0, 16, 0.5)]
    x, _ = S.sing(quiet, bpm, pre_roll=0.0, sibilants=0, breaths=False, seed=6, detune_cents=10)
    x = x * 0.15
    for beat in (2.0, 6.0, 10.5, 14.0):  # four shouted words, much louder, on the grid
        y, _ = S.sing([(beat, 0.4, 67)], bpm, pre_roll=0.0, sibilants=0, breaths=False, seed=int(beat * 10))
        i = int(beat * 0.5 * V.SR)
        seg = y[i:i + int(0.3 * V.SR)]
        x[i:i + len(seg)] += seg * 1.2
    hits = accent_times(np.stack([x, x]), bpm, "some")
    found = {h[0] for h in hits}
    assert sum(any(abs(f - b) <= 0.25 for f in found) for b in (2.0, 6.0, 10.5, 14.0)) >= 3
    assert len(hits) <= 8


def test_favourites_move_to_the_new_key_and_tempo(home):
    a = Project.create("battle_funk")  # D minor, 126
    hook = a.add_piece("hook")
    spb = 60 / 126
    mel = [(62, 1), (65, 0.5), (67, 0.5), (69, 2), (-1, 12)]
    y, _ = S.hum(mel * 2, bpm=126, lead_in=4 * spb, seed=2)
    a.add_recording(hook["id"], y, S.SR, -4 * spb)
    fav = a.favourite(hook["id"], "My hook")
    b = Project.create("night_hiphop")  # G minor, 88
    q = b.use_favourite(fav["id"])
    assert [n[2] for n in q["notes"]] == [n[2] + 5 for n in a.piece(hook["id"])["notes"]]  # D minor -> G minor
    assert [n[0] for n in q["notes"]] == [n[0] for n in a.piece(hook["id"])["notes"]]  # same rhythm in beats
    assert any(q["id"] in s["parts"] for s in b.data["sections"])


def test_api_songbook_and_vocal_options(home):
    from fastapi.testclient import TestClient

    from mouthmixer.app.server import create_app

    c = TestClient(create_app(start_worker=False))
    sb = c.get("/api/songbook").json()
    assert len(sb) == 19
    p = c.post("/api/projects", json={"songbook": sb[0]["id"]}).json()
    assert p["songbook"]["voices"] and p["lyrics"]["sheet"] and p["title"] == sb[0]["title"]
    o = c.get("/api/vocal_options").json()
    assert {"female", "gang", "whisper", "announcer"} <= {x["id"] for x in o["characters"]} and "Rap" in o["tracks"]
    assert c.get("/api/favourites").json() == []


def test_song_shape_rules(home):
    """SONG_SHAPES: layered intro, room for the voice, freeze then drop, rap without pad, piano breakdown,
    three-hit ending."""
    p = Project.create("battle_funk")
    p.apply_lyrics(LYRICS)
    for slot in ("riff", "hook"):
        q = p.add_piece(slot)
        q["notes"] = [[0.0, 1.0, 62, 90]]
        p._default_sections(q)
    secs = {s["name"]: s for s in p.data["sections"]}
    riff = next(q for q in p.pieces if q["slot"] == "riff")
    assert riff["id"] not in secs["Verse 1"]["parts"] and riff["id"] in secs["Chorus"]["parts"]  # room for the voice
    pad = next(q for q in p.pieces if q["slot"] == "pad")
    assert pad["id"] not in secs["Rap Verse"]["parts"]
    song, _ = p.song()
    by = {t.name: t for t in song.tracks}
    start = {n: s * 4 for n, s, b in song.sections}
    first = lambda name, sec: min((x[0] for x in by[name].notes if start[sec] <= x[0] < start[sec] + 16), default=None)  # noqa: E731
    assert first("Starter chords", "Intro") == 0 and first("Starter bass", "Intro") >= 4  # layered intro
    assert first("Starter beat", "Intro") >= 8
    c = start["Chorus"]  # after the build-up: the first bar is frozen, then crash + kick on the drop
    assert not [x for t in song.tracks if t.name != "Risers into big moments" for x in t.notes if c <= x[0] < c + 4]
    assert {(c + 4, 49), (c + 4, 36)} <= {(x[0], x[2]) for x in by["Starter beat"].notes}
    assert any(abs(x[0] + x[1] - (c + 4)) < 0.01 for x in by["Risers into big moments"].notes)  # riser lands on the drop
    assert by["Piano for the quiet parts"].notes and all(start["Bridge"] <= x[0] < start["Bridge"] + 16
                                                         for x in by["Piano for the quiet parts"].notes)
    end = song.sections[-1]
    last = (end[1] + end[2] - 1) * 4
    assert sorted({round(x[0] - last, 2) for t in song.tracks for x in t.notes if x[0] >= last}) == [0, 1, 2]
    assert not critic.judge(song)["rejects"]
