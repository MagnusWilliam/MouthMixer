"""Ready-made parts (grooves, phrases, combos), recording timing, and the voice tweaks."""

import io

import numpy as np
import soundfile as sf

from mouthmixer import config
from mouthmixer import synth as S
from mouthmixer.arrange import theory
from mouthmixer.arrange import vocals as V
from mouthmixer.studio import presets, starters
from mouthmixer.studio.project import Project


def _gen(gen, feel="verse", style="", busy=0, sid="battle_funk", bars=4):
    st = dict(starters.STARTERS[sid], id=sid)
    chords = starters.progression(st["a"], st["tonic"], st["ext"], bars)
    return starters.generate(gen, st, chords, (0, bars), feel=feel, style=style, busy=busy)


def test_every_groove_plays_and_changes_the_part():
    for gen, table in presets.GROOVES.items():
        own = _gen(gen)
        for k in table:
            notes = _gen(gen, style=k)
            assert notes, (gen, k)
        assert any(_gen(gen, style=k) != own for k in table)
    # four-on-the-floor: a kick on every beat
    kicks = sorted({round(n[0], 2) for n in _gen("drums", style="four_floor") if n[2] == 36})
    assert kicks[:4] == [0.0, 1.0, 2.0, 3.0]


def test_grooves_keep_the_section_feel():
    assert _gen("drums", "breakdown", style="disco") == []  # drums still drop out
    rap = _gen("drums", "rap", style="disco")
    assert sorted({round(n[0] % 4, 2) for n in rap if n[2] == 38 and n[3] > 80}) == [2.0]  # still the rap pocket
    intro = _gen("drums", "intro", style="train")
    assert any(n[2] == 38 and n[0] >= 14 for n in intro)  # the snare roll into the verse
    end = _gen("bass", "hits_end", style="walking")
    assert len([n for n in end if n[0] >= 12]) == 3  # three hits at the end


def test_simpler_and_busier_thin_and_fill_grooves():
    for gen in ("drums", "bass", "comp"):
        counts = [len(_gen(gen, busy=b)) for b in (-2, -1, 0, 1, 2)]
        assert counts[0] <= counts[1] <= counts[2] <= counts[3] <= counts[4], (gen, counts)
        assert counts[0] < counts[2] < counts[4], (gen, counts)


def test_phrases_fit_the_chords_and_key():
    for sid in ("battle_funk", "daily_citypop", "night_hiphop"):
        st = starters.STARTERS[sid]
        prog = starters.progression(st["a"], st["tonic"], st["ext"], 4)
        scale = {(st["tonic"] + i) % 12 for i in theory.MODES[st["mode"]]}
        for k, pr in presets.PHRASES.items():
            notes = presets.render_phrase(k, prog, st["tonic"], st["mode"])
            assert notes and max(n[0] for n in notes) < pr["bars"] * 4, k
            if "rows" in pr:
                continue
            for s, l, p, v in notes:
                c = next(c for cs, cl, c in prog if cs <= s < cs + cl)
                chord = {(c.root + i) % 12 for i in theory.QUALITIES[c.quality]}
                assert p % 12 in scale | chord, (sid, k, s, p)
            spread = max(n[2] for n in notes) - min(n[2] for n in notes)
            assert spread <= 26, (k, spread)  # stays in one register, no wild jumps
    # tone 0 is the chord's root
    st = starters.STARTERS["battle_funk"]
    prog = starters.progression(st["a"], st["tonic"], st["ext"], 4)
    assert presets.render_phrase("stab_big_one", prog, st["tonic"], st["mode"])[0][2] % 12 == 2  # D


def test_project_presets_combos_and_pattern_swaps(home):
    p = Project.create("battle_funk")
    beat = p.add_preset("boom_bap")
    assert beat["gen"] == "drums" and beat["pattern"] == "boom_bap" and beat["source"] == "starter"
    assert sum(1 for q in p.pieces if q.get("gen") == "drums") == 1  # swapped in, not added
    riff = p.add_preset("riff_clav")
    assert riff["source"] == "preset" and riff["notes"] and len(riff["over"]) == 2 and riff["instrument"] == "clavinet"
    assert any(riff["id"] in s["parts"] for s in p.data["sections"])
    p.edit_piece(riff["id"], instrument="rhodes")
    p.set_pattern(riff["id"], "riff_heist")
    q = p.piece(riff["id"])
    assert q["preset"] == "riff_heist" and q["instrument"] == "rhodes" and q["name"] == "Sneaky heist line"
    p.apply_combo("club")
    pats = {q["gen"]: q["pattern"] for q in p.pieces if q.get("gen") in presets.GROOVES}
    assert pats == {"drums": "jazz_ride", "bass": "walking", "comp": "charleston"}
    p._gen_variation(p.piece(beat["id"]), "busier")
    assert p.piece(beat["id"])["busy"] == 1
    perc = p.add_preset("perc_congas")
    assert p.piece(perc["id"])["instrument"].startswith("kit:") and not p.piece(perc["id"])["over"]
    name, secs = p.booth_stem(riff["id"])
    assert (p.dir / "stems" / name).exists()
    # a deleted starter beat comes back when you pick a beat
    p.remove_piece(beat["id"])
    again = p.add_preset("disco")
    assert again["gen"] == "drums" and any(again["id"] in s["parts"] for s in p.data["sections"])
    pub = p.public()
    assert any(x.get("patterns") for x in pub["pieces"] if x["id"] == riff["id"])
    song, _ = p.song()
    assert any(t.name == "Sneaky heist line" and t.notes for t in song.tracks)


def test_whole_piece_nudge_earlier_and_later(home):
    p = Project.create("battle_funk")
    q = p.add_preset("stab_push")
    before = [n[0] for n in q["notes"]]
    p.variation(q["id"], "earlier")
    assert [n[0] for n in p.piece(q["id"])["notes"]] == [b - 0.25 for b in before]
    p.variation(q["id"], "later")
    p.variation(q["id"], "later")
    assert [n[0] for n in p.piece(q["id"])["notes"]] == [b + 0.25 for b in before]


def test_latency_uses_the_estimate_until_measured(home):
    s = config.Settings.load()
    assert s.latency_ms(120) == 120 and s.latency_ms(None) == 0
    assert s.latency_ms(5000) == 400  # a silly estimate is capped
    s.vocal_latency_ms, s.latency_measured = 85, True
    assert s.latency_ms(120) == 120  # measured with the old capture: doesn't apply to the audio-thread one
    s.latency_pipeline = "worklet"
    assert s.latency_ms(120) == 85 and s.latency_ms(120, "script") == 120


def test_api_presets_and_estimated_timing(home):
    from fastapi.testclient import TestClient

    from mouthmixer.app.server import create_app

    c = TestClient(create_app(start_worker=False))
    pr = c.get("/api/presets").json()
    assert {x["id"] for x in pr["categories"]} >= {"beat", "bass", "chords", "riff", "stab", "perc"}
    assert all(cat["items"] for cat in pr["categories"]) and len(pr["combos"]) >= 8
    pid = c.post("/api/projects", json={"starter": "battle_funk"}).json()["id"]
    r = c.post(f"/api/projects/{pid}/presets", json={"preset": "ans_reply"}).json()
    added = r["added"]
    r = c.post(f"/api/projects/{pid}/pieces/{added}", json={"pattern": "ans_sigh"}).json()
    assert next(x for x in r["pieces"] if x["id"] == added)["preset"] == "ans_sigh"
    r = c.post(f"/api/projects/{pid}", json={"combo": "chase"}).json()
    assert next(x for x in r["pieces"] if x.get("gen") == "drums")["pattern"] == "disco"
    assert c.post(f"/api/projects/{pid}/presets", json={"preset": "nope"}).status_code == 404
    assert c.post(f"/api/projects/{pid}/pieces/{added}/record", content=b"x").status_code == 400
    # a booth take recorded before the sync test is placed using the browser's estimate (150 ms late here)
    hook = c.post(f"/api/projects/{pid}/pieces", json={"slot": "hook"}).json()["added"]
    mel = [(62, 1), (65, 0.5), (67, 0.5), (69, 2), (-1, 1), (67, 1), (65, 1), (62, 2), (-1, 2), (60, 0.5), (62, 1.5), (-1, 3)]
    spb = 60 / 126
    y, _ = S.hum(mel * 2, bpm=126, lead_in=4 * spb, seed=2, detune_cents=25)
    y = np.concatenate([np.zeros(int(0.15 * S.SR), np.float32), y])
    b = io.BytesIO()
    sf.write(b, y, S.SR, format="WAV", subtype="FLOAT")
    r = c.post(f"/api/projects/{pid}/pieces/{hook}/record?start={-4 * spb}&est_ms=150", content=b.getvalue()).json()
    q = next(x for x in r["pieces"] if x["id"] == hook)
    assert [n[0] for n in q["notes"]][:4] == [0.0, 1.0, 1.5, 2.0]  # on the beat, not a 16th late


def test_tweaks_are_cleaned_and_shape_the_style():
    t = V.clean_tweaks({"pitch": 40, "tone": "x", "fx": "robot", "harmony": "bogus", "echo": 50, "other": 1})
    assert t == {"pitch": 7.0, "fx": "robot", "echo": 50.0}
    p = V.tweak_preset(V.preset("soul"), {"fx": "robot", "double": 100, "space": 0, "tuning": "off"})
    assert p["tune"] == "hard" and p["doubles"] == "all" and p["reverb"] == 0  # robot overrides "off"
    assert V.tweak_preset(V.preset("soul"), {"tuning": "off"})["strength"] == 0
    assert V.tweak_preset(V.preset("soul"), {})["strength"] == V.preset("soul")["strength"]  # untouched stays
    assert V.character_spec("female", {"tone": 10})["formant"] > V.CHARACTERS["female"]["formant"]


def test_harmony_voice_and_pitch_and_effects():
    # D minor: a third above D is F, above F is A; a fifth above D is A
    f = 440 * 2 ** ((np.array([62, 65, 69]) - 69) / 12)
    r = V._harmony_ratio(f, 2, 2, "minor")
    assert np.allclose(12 * np.log2(r), [3, 4, 3])
    assert np.allclose(12 * np.log2(V._harmony_ratio(f, 4, 2, "minor")), [7, 7, 7])
    x, _ = S.sing([(0, 2, 62), (2, 2, 65), (4, 2, 69)], 100, pre_roll=0.2, sibilants=0, breaths=False, seed=5)
    x = x.astype(np.float32)
    f0, _ = V.track_f0(x)
    rep = {}
    main, layer = V.apply_character(x, f0, "natural", rep, tweaks={"harmony": "third_up", "pitch": 1}, scale=(2, "minor"))
    assert layer is not None and rep["harmony_voice"] == "third_up"
    fm, _ = V.track_f0(main)
    both = (fm > 0) & (f0[: len(fm)] > 0)
    moved = 12 * np.log2(fm[both] / f0[: len(fm)][both])
    assert 1.0 <= np.median(moved) <= 2.2  # one note of the key up: D->E, F->G (2 semitones), A->Bb (1)
    scale = {(2 + i) % 12 for i in (0, 2, 3, 5, 7, 8, 10)}

    def in_key(f):
        return np.mean([round(m) % 12 in scale for m in 69 + 12 * np.log2(f[f > 0] / 440)])

    plain = V.voice_variant(x, f0, cents=200)  # a plain 2-semitone shift, for comparison
    assert in_key(fm) >= in_key(f0) - 0.08 and in_key(fm) > in_key(V.track_f0(plain)[0]) + 0.1  # stays in D minor
    fh, _ = V.track_f0(layer.mean(axis=0))
    both = (fh > 0) & (f0[: len(fh)] > 0)
    up = np.median(12 * np.log2(fh[both] / f0[: len(fh)][both]))
    assert 4.5 <= up <= 5.5  # pitch +1 plus a third = 3 notes of the key up: a fourth (5 semitones)
    radio = V._fx(x, "radio")
    hi = lambda y: np.abs(np.fft.rfft(y))[int(len(y) * 6000 / V.SR):].sum() / np.abs(np.fft.rfft(y)).sum()  # noqa: E731
    assert hi(radio) < hi(x) * 0.6 and abs(np.sqrt(np.mean(radio ** 2)) / np.sqrt(np.mean(x ** 2)) - 1) < 0.05
    robot = V._fx(x, "robot")
    assert robot.shape == x.shape and not np.allclose(robot, x)


def test_preview_is_a_short_stereo_clip():
    x, _ = S.sing([(b, 0.9, 62 + (b % 3) * 2) for b in range(12)], 100, pre_roll=1.0, sibilants=0.1,
                  breaths=False, seed=8)
    tk = V.Take(x.astype(np.float32) * 0.6, 0.0, "t")
    y = V.preview(tk, 2, "minor", "soul", "female", {"grit": 40, "echo": 60, "fx": "megaphone"}, seconds=4)
    assert y.shape[0] == 2 and 3.5 * V.SR <= y.shape[1] <= 4.1 * V.SR and 0.8 < np.abs(y).max() <= 0.9
    rap = V.preview(tk, 2, "minor", "soul", "male_deep", {}, seconds=3, untuned=True)
    assert rap.shape[0] == 2


def test_booth_loops_one_off_pieces_and_build_keeps_each_volume(home):
    p = Project.create("battle_funk")
    for pid in ("intro_fanfare", "fill_roll"):
        q = p.add_preset(pid)
        name, _ = p.booth_stem(q["id"])
        y, _ = sf.read(str(p.dir / "stems" / name))
        assert np.sqrt(np.mean(y ** 2)) > 0.005, pid  # it plays in the booth loop
    a, b = p.add_preset("riff_clav"), p.add_preset("riff_clav")  # same name twice
    p.edit_piece(b["id"], gain_db=-24)
    song, _ = p.song()
    names = [t.name for t in song.tracks if t.name.startswith("Funky clav")]
    assert len(names) == 2 and len(set(names)) == 2
    assert sorted(p.track_gains[n] for n in names) == [-24.0, 0.0]


def test_one_off_nudge_does_not_wrap_and_note_ops_report_the_new_index(home):
    p = Project.create("battle_funk")
    q = p.add_preset("intro_fanfare")
    assert q["kind"] == "one" and q["notes"][0][0] == 0
    p.variation(q["id"], "earlier")
    assert p.piece(q["id"])["notes"][0][0] == 0.0  # the first note stays first
    r = p.add_preset("riff_clav")
    second = list(p.piece(r["id"])["notes"][1])
    for _ in range(3):  # move note 1 earlier past note 0
        p.note_op(r["id"], 1 if _ == 0 else p.last_note_index, "earlier")
    moved = p.piece(r["id"])["notes"][p.last_note_index]
    assert moved[2] == second[2] and moved[0] == max(0.0, second[0] - 0.75)


def test_key_change_moves_a_vocal_chop(home):
    p = Project.create("battle_funk")
    q = p._new_piece("chop")
    t = np.arange(int(0.5 * S.SR)) / S.SR
    sf.write(str(p.dir / "takes" / "chop-a.wav"), (0.5 * np.sin(2 * np.pi * 440 * t)).astype(np.float32), S.SR)
    q["audio"] = "chop-a.wav"
    q["takes"] = [{"id": "a", "audio": "chop-a.wav", "notes": [], "pass": 0, "score": 1}]
    q["take"] = "a"
    p.save()
    p.set_key(4)  # D -> E: two semitones up
    q = p.piece(q["id"])
    assert q["audio"] != "chop-a.wav" and q["takes"][0]["audio"] == q["audio"]
    y, sr = sf.read(str(p.dir / "takes" / q["audio"]))
    f = np.fft.rfftfreq(len(y), 1 / sr)[np.argmax(np.abs(np.fft.rfft(y)))]
    assert abs(f - 440 * 2 ** (2 / 12)) < 6


def test_bad_input_gets_a_clear_error_not_a_crash(home):
    from fastapi.testclient import TestClient

    from mouthmixer.app.server import create_app

    c = TestClient(create_app(start_worker=False), raise_server_exceptions=False)
    pid = c.post("/api/projects", json={"starter": "battle_funk"}).json()["id"]
    for body in ({"tonic": "C"}, {"sections": None}, {"sections": ["a"]}, {"sections": [{"bars": "x"}]}):
        assert c.post(f"/api/projects/{pid}", json=body).status_code == 400, body
    r = c.post(f"/api/projects/{pid}", json={"sections": [{"feel": [1], "bars": 4}]})
    assert r.status_code == 200 and r.json()["sections"][0]["feel"] is None  # a bad feel is ignored
    assert c.post(f"/api/projects/{pid}/pieces/q1", json={"instrument": 5}).status_code == 400
    assert c.delete(f"/api/projects/{pid}/pieces/nope/takes/x").status_code == 404
    assert c.post("/api/settings", json={"vocal_latency_ms": "x"}).status_code == 400
    for path in ("/api/songs/nope/lyrics/own", "/api/songs/nope/lyrics/choose", "/api/songs/nope/vocals"):
        assert c.post(path, json={}).status_code == 404, path
    r = c.post(f"/api/projects/{pid}/pieces", json={"slot": "hook"}).json()
    q = c.post(f"/api/projects/{pid}/presets", json={"preset": "riff_clav"}).json()["added"]
    r = c.post(f"/api/projects/{pid}/pieces/{q}", json={"note_op": "earlier", "index": 1}).json()
    assert isinstance(r["note_index"], int)


def test_scripts_are_served_as_javascript(home):
    from fastapi.testclient import TestClient

    from mouthmixer.app.server import create_app

    c = TestClient(create_app(start_worker=False))
    r = c.get("/static/capture-worklet.js")
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/javascript")
    assert "registerProcessor" in r.text
    assert c.get("/static/../server.py").status_code == 404


def _onset_offsets_ms(stem, sr, truth_onsets, window):
    """For each true note onset (song seconds) in `window`, how far (ms) the nearest pitched onset in the
    processed vocal is from it; the median of those."""
    import librosa

    y = librosa.resample(np.asarray(stem, dtype=np.float32), orig_sr=sr, target_sr=V.SR)
    f0, _ = V.track_f0(y)
    t = np.arange(len(f0)) * V.FRAME_MS / 1000
    on = t[1:][(f0[1:] > 0) & (f0[:-1] == 0)]
    offs = []
    for o in truth_onsets:
        if window[0] <= o <= window[1]:
            near = on[np.argmin(np.abs(on - o))] if len(on) else None
            if near is not None and abs(near - o) < 0.3:
                offs.append((near - o) * 1000)
    return float(np.median(offs)), len(offs)


def test_vocals_land_where_they_were_sung_and_choices_and_nudges_work(home):
    """The finished vocal sits where the take says it was sung; a section can use an older take; the
    Timing tweak moves the whole track; a preview can be of any take, with the band."""
    from fastapi.testclient import TestClient

    from mouthmixer.app.server import create_app
    from mouthmixer.library.db import Library
    from mouthmixer.studio import songbook

    c = TestClient(create_app(start_worker=False))
    song = next(s for s in songbook.songs() if s["title"].startswith("Last Train"))
    pid = c.post("/api/projects", json={"songbook": song["id"]}).json()["id"]
    sid = c.post(f"/api/projects/{pid}/build").json()["song_id"]
    v = c.get(f"/api/songs/{sid}").json()["record"]["versions"][-1]
    spb = 60 / v["bpm"]
    sec = next(s for s in v["sections"] if s["name"] == "Verse 1")
    a, b_ = sec["start"] * 4 * spb, (sec["start"] + sec["bars"]) * 4 * spb
    count_in = 8 * spb
    takes = []
    for seed, step in ((3, 2), (4, 3)):  # two takes of the verse with different rhythms
        notes = [(count_in / spb + b, 0.9, 62 + ((b + seed) % 3) * 3) for b in range(0, sec["bars"] * 4 - 2, step)]
        x, truth = S.sing(notes, v["bpm"], pre_roll=0.0, sibilants=0, breaths=False, seed=seed, detune_cents=10)
        b = io.BytesIO()
        sf.write(b, (x * 0.6).astype(np.float32), 44100, format="WAV", subtype="FLOAT")  # sing() is 44.1 kHz
        t = c.post(f"/api/songs/{sid}/takes?start={a - count_in:.4f}&section=Verse%201&track=Verse%20lead&est_ms=0",
                   content=b.getvalue()).json()
        takes.append((t["id"], [a - count_in + n.onset for n in truth]))
    lib = Library(config.paths()["db"], config.paths()["clips"])

    def stem_of(version):
        mix = c.get(f"/api/songs/{sid}/mixer?v={version}").json()
        part = next(q for q in mix["parts"] if q["role"] == "vocal")
        y, sr = sf.read(str(lib.song_dir(sid) / "stems" / part["stem"]))
        return y.mean(axis=1), sr

    win = (a + 0.3, b_ - 0.3)
    # newest take, no nudge: right on the notes as sung
    r = c.post(f"/api/songs/{sid}/vocals", json={"track": "Verse lead", "v": 0}).json()
    off, n = _onset_offsets_ms(*stem_of(r["version"]), takes[1][1], win)
    assert n >= 6 and abs(off) <= 15, (off, n)
    # the older take picked for Verse 1, nudged 120 ms later
    r = c.post(f"/api/songs/{sid}/vocals", json={"track": "Verse lead", "v": 0, "choice": {"Verse 1": takes[0][0]},
                                                 "tweaks": {"timing": 120}}).json()
    y, sr = stem_of(r["version"])
    off, n = _onset_offsets_ms(y, sr, takes[0][1], win)
    assert n >= 6 and abs(off - 120) <= 15, (off, n)
    # previews: a chosen take, with the band under it
    p1 = c.post(f"/api/songs/{sid}/vocals/preview", json={"track": "Verse lead", "take": takes[0][0], "band": True})
    p2 = c.post(f"/api/songs/{sid}/vocals/preview", json={"track": "Verse lead", "take": takes[0][0]})
    assert p1.status_code == p2.status_code == 200 and p1.content != p2.content


def test_lyrics_say_who_sings_each_part(home):
    """Headers name the singers ("[Chorus, Chorus lead + Gang]"), "Gang:" marks who joins on a line, "8 bars"
    sets a section's length, and a chorus straight after the rap gets the freeze-and-drop."""
    from mouthmixer.studio import songbook

    song = next(s for s in songbook.songs() if s["title"].startswith("Last Train"))
    p = Project.create(song["starter"], song["title"])
    secs = p.apply_lyrics(song["lyrics"])
    by = {s["name"]: s for s in secs}
    assert by["Intro"]["bars"] == 8 and by["Chorus instrumental"]["bars"] == 8 and by["Chorus 2"]["bars"] == 8
    sheet = {x["section"]: x for x in p.lyric_sheet()}
    assert sheet["Intro"]["singers"] == ["Announcer"] and sheet["Intro"]["mode"] == "spoken"
    assert sheet["Chorus"]["singers"] == ["Chorus lead", "Gang"]
    assert sheet["Chorus"]["lines"][0].startswith("Ride, ride, ride") and sheet["Chorus"]["line_singers"][0] == ["Gang"]
    assert sheet["Rap Verse"]["mode"] == "rap" and sheet["Rap Verse"]["line_singers"][7] == ["Ad-libs"]
    assert sheet["Bridge build"]["singers"] == ["Chorus lead"] and sheet["Bridge build"]["line_singers"][1] == ["Backing"]
    assert sheet["Outro"]["singers"] == ["Announcer"] and sheet["Outro"]["lines"] == ["Next stop: tomorrow."]
    names = [s["name"] for s in secs]
    drops = p.drops()
    assert drops[names.index("Chorus 2")] == 4 and drops[names.index("Chorus")] == 4  # after the rap / the pre
    # a line with a colon that isn't a singer stays as written
    p.apply_lyrics("[Verse 1, Verse lead]\nNote: this stays\nTwo\n")
    assert p.lyric_sheet()[0]["lines"][0] == "Note: this stays"
