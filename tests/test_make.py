"""The Make tab: starter beats, recording pieces on purpose over a loop, pieces, the song board, build."""

import io

import numpy as np
import pytest
import soundfile as sf

from mouthmixer import synth as S
from mouthmixer.arrange import arranger, critic
from mouthmixer.studio import starters
from mouthmixer.studio.project import Project

HOOK = [(62, 1), (65, 0.5), (67, 0.5), (69, 2), (-1, 1), (67, 1), (65, 1), (62, 2), (-1, 2), (60, 0.5), (62, 1.5), (-1, 3)]


def _expected(mel):
    out, b = [], 0.0
    for m, l in mel:
        if m > 0:
            out.append([b, l, m])
        b += l
    return out


def _hum_loop(mel, bpm, passes=2, seed=2, count_in_bars=1):
    """Hum `mel` (one pass) `passes` times after a count-in: returns (audio, start) with start = loop time
    of sample 0."""
    spb = 60 / bpm
    y, _ = S.hum(mel * passes, bpm=bpm, lead_in=4 * spb * count_in_bars, seed=seed, detune_cents=25)
    return y, -4 * spb * count_in_bars


def test_favourite_loops_resolve_to_real_chords():
    names = [arranger.resolve_degree(d, 2, "seventh").name for d in ["i", "bVI", "bVII", "iv", "V", "bII"]]
    assert names == ["Dm7", "Bbmaj7", "C7", "Gm7", "A7", "Ebmaj7"]
    for sid, st in starters.STARTERS.items():  # every starter has moving harmony, not one chord
        chords = {c.name for _, _, c in starters.progression(st["a"], st["tonic"], st["ext"], 4)}
        assert len(chords) >= 2, sid


@pytest.mark.parametrize("sid", list(starters.STARTERS))
def test_every_starter_makes_a_clean_song_on_its_own(home, sid):
    p = Project.create(sid)
    song, chops = p.song()
    assert song.bars == sum(b for _, b, _ in __import__("mouthmixer.studio.project", fromlist=["x"]).DEFAULT_FORM)
    v = critic.judge(song)
    assert not [r for r in v["rejects"] if "clash" in r or "range" in r], v["rejects"]


def test_hummed_hook_lands_on_the_grid_and_becomes_a_piece(home):
    p = Project.create("battle_funk")
    hook = p.add_piece("hook")
    y, start = _hum_loop(HOOK, 126, passes=3)
    takes = p.add_recording(hook["id"], y, S.SR, start)
    assert len(takes) == 3  # every pass round the loop is a take
    got = [n[:3] for n in p.piece(hook["id"])["notes"]]
    assert got == _expected(HOOK)
    assert p.piece(hook["id"])["over"] == [c.root for _, _, c in p.progression("A", 4)]
    # it plays in the hook sections by default, repeated to fill 8 bars
    hooks = [s for s in p.data["sections"] if s["name"].startswith("Hook")]
    assert all(hook["id"] in s["parts"] for s in hooks)
    song, _ = p.song()
    lead = next(t for t in song.tracks if t.name == hook["name"])
    assert lead.mine and len(lead.notes) == 3 * 2 * len(_expected(HOOK))


def test_latency_is_taken_off_the_recording(home):
    p = Project.create("night_hiphop")
    hook = p.add_piece("hook")
    y, start = _hum_loop(HOOK, 88)
    late = np.concatenate([np.zeros(int(0.09 * S.SR), np.float32), y])  # arrives 90 ms late
    p.add_recording(hook["id"], late, S.SR, start - 0.09)  # what the server does with a 90 ms sync result
    assert [n[0] for n in p.piece(hook["id"])["notes"]] == [n[0] for n in _expected(HOOK)]


def test_beatbox_replaces_the_starter_beat(home):
    p = Project.create("daily_citypop")
    beat = p.add_piece("beat")
    y, _ = S.beatbox(bars=6, bpm=98, seed=5)
    p.add_recording(beat["id"], y, S.SR, 0.0)
    notes = p.piece(beat["id"])["notes"]
    assert {36, 38} <= {n[2] for n in notes} and len(notes) >= 8
    starter_beat = next(q for q in p.pieces if q["slot"] == "beat" and q["source"] == "starter")
    for s in p.data["sections"]:
        assert not (beat["id"] in s["parts"] and starter_beat["id"] in s["parts"])


def test_a_bassline_follows_the_bridge_chords(home):
    p = Project.create("battle_funk")
    bass = p.add_piece("bass")
    # each bar's chord root (Dm, Bb, C, Dm), with an octave pop: a D over Bb would be its 3rd and stay a 3rd
    line = [x for r in (38, 46, 48, 38) for x in [(r, 1), (-1, 1), (r, 0.5), (r + 12, 0.5), (-1, 1)]]
    y, start = _hum_loop(line, 126)
    p.add_recording(bass["id"], y, S.SR, start)
    q = p.piece(bass["id"])
    a = p.place(q, 0, 4, p.progression("A", 4))
    b = p.place(q, 0, 4, p.progression("B", 4))
    roots_b = [c.root for _, _, c in p.progression("B", 4)]
    for bar in range(4):  # in the bridge each bar's first note sits on that bar's chord root
        first = min((n for n in b if bar * 4 <= n[0] < bar * 4 + 1), key=lambda n: n[0])
        assert first[2] % 12 == roots_b[bar], (bar, first)
    assert [n[2] % 12 for n in a if n[0] % 4 == 0] == [c.root for _, _, c in p.progression("A", 4)]
    assert a != b


def test_one_note_fixes_variations_octave_and_key(home):
    p = Project.create("battle_funk")
    hook = p.add_piece("hook")
    y, start = _hum_loop(HOOK, 126)
    p.add_recording(hook["id"], y, S.SR, start)
    pid = hook["id"]
    first = p.piece(pid)["notes"][0][2]
    p.note_op(pid, 0, "up")
    assert p.piece(pid)["notes"][0][2] == p._step(first, 1)  # the next note of D minor
    p.note_op(pid, 0, "later")
    assert p.piece(pid)["notes"][0][0] == 0.25
    n = len(p.piece(pid)["notes"])
    p.note_op(pid, 1, "delete")
    assert len(p.piece(pid)["notes"]) == n - 1
    p.variation(pid, "busier")
    assert len(p.piece(pid)["notes"]) > n - 1
    p.edit_piece(pid, octave=1, instrument="flute")
    song, _ = p.song()
    t = next(t for t in song.tracks if t.name == hook["name"])
    assert t.instrument == "flute"
    before = p.piece(pid)["notes"][0][2]
    p.set_key(4)  # D minor -> E minor
    assert p.piece(pid)["notes"][0][2] == before + 2 and p.st["tonic"] == 4


def test_stabs_become_chord_hits(home):
    p = Project.create("battle_funk")
    st = p.add_piece("stab")
    hits = [(-1, 1.5), (69, 0.5), (-1, 1.5), (69, 0.5)] * 2  # "bah!" on the and of 2 and 4
    y, start = _hum_loop(hits, 126)
    p.add_recording(st["id"], y, S.SR, start)
    notes = p.place(p.piece(st["id"]), 0, 2, p.progression("A", 2))
    chords = p.progression("A", 2)
    by_time: dict = {}
    for s, l, pitch, v in notes:
        by_time.setdefault(s, []).append(pitch)
    assert by_time and all(len(v) == 3 for v in by_time.values())
    for s, ps in by_time.items():
        c = next(c for cs, cl, c in chords if cs <= s < cs + cl)
        tones = {(c.root + i) % 12 for i in __import__("mouthmixer.arrange.theory", fromlist=["x"]).QUALITIES[c.quality]}
        assert all(x % 12 in tones for x in ps)


def test_api_flow_record_board_build(home):
    from fastapi.testclient import TestClient

    from mouthmixer.app.server import create_app

    app = create_app(start_worker=False)
    c = TestClient(app)
    st = c.get("/api/starters").json()
    assert len(st["moods"]) == len(starters.MOODS) and len(st["starters"]) == len(starters.STARTERS) >= 10
    p = c.post("/api/projects", json={"starter": "battle_funk", "title": "Test"}).json()
    pid = p["id"]
    booth = c.get(f"/api/projects/{pid}/booth").json()
    assert len(booth["loops"]) == 4 and c.get(f"/api/projects/{pid}/stems/{booth['loops'][0]['stem']}").status_code == 200
    r = c.post(f"/api/projects/{pid}/pieces", json={"slot": "hook"}).json()
    hid = r["added"]
    c.post("/api/settings", json={"vocal_latency_ms": 40})
    y, start = _hum_loop(HOOK, 126)
    y = np.concatenate([np.zeros(int(0.04 * S.SR), np.float32), y])
    b = io.BytesIO()
    sf.write(b, y, S.SR, format="WAV", subtype="FLOAT")
    r = c.post(f"/api/projects/{pid}/pieces/{hid}/record?start={start}", content=b.getvalue()).json()
    q = next(x for x in r["pieces"] if x["id"] == hid)
    assert [n[:3] for n in q["notes"]] == _expected(HOOK) and r["new_takes"]
    assert c.post(f"/api/projects/{pid}/pieces/{hid}", json={"note_op": "up", "index": 0}).status_code == 200
    assert c.post(f"/api/projects/{pid}/pieces", json={"slot": "chords"}).status_code == 400  # starter-only
    secs = r["sections"]
    secs[0]["parts"].append(hid)
    r = c.post(f"/api/projects/{pid}", json={"sections": secs}).json()
    assert hid in r["sections"][0]["parts"]
    built = c.post(f"/api/projects/{pid}/build").json()
    assert built["critic"]["ok"], built["critic"]["rejects"]
    song = c.get(f"/api/songs/{built['song_id']}").json()
    assert song["record"]["versions"][0]["spec"]["project"] == pid
    mix = c.get(f"/api/songs/{built['song_id']}/mixer").json()
    assert any(x["mine"] and x["role"] == "lead" for x in mix["parts"])
    lyr = c.get(f"/api/songs/{built['song_id']}/lyrics").json()
    assert lyr["map"] and lyr["map"][0]["section"] != "Intro"  # sections named Verse/Hook get words
    again = c.post(f"/api/projects/{pid}/build").json()
    assert again["song_id"] == built["song_id"] and again["version"] == 1


def test_background_listening_is_off_by_default(home):
    from mouthmixer import config

    assert config.Settings().background_listening is False


def test_vocal_chop_stays_your_voice_and_reaches_the_mixer(home):
    from mouthmixer.arrange.mixer import Mixer
    from mouthmixer.library.db import Library
    from mouthmixer import config

    p = Project.create("battle_funk")
    ch = p.add_piece("chop")
    spb = 60 / 126
    # "hey!" on beat 1 and "oh-oh" on beat 3 of each 2-bar pass, sung (not hummed)
    notes = [(b + o, l, m) for b in (0, 8, 16) for o, l, m in ((4, 0.5, 69), (6, 0.5, 67), (6.5, 0.5, 65))]
    y, _ = S.sing(notes, 126, start=4 * spb, pre_roll=4 * spb, sr=44100, breaths=False, seed=4)
    p.add_recording(ch["id"], y, 44100, -4 * spb)
    q = p.piece(ch["id"])
    assert q["audio"] and q["notes"]
    name, secs = p.booth_stem(ch["id"])
    x, _ = sf.read(str(p.dir / "stems" / name))
    assert np.abs(x).max() > 0.01 and abs(len(x) / 44100 - secs) < 0.01
    paths = config.ensure_dirs()
    lib = Library(paths["db"], paths["clips"])
    built = p.build(lib)
    m = Mixer(lib.song_dir(built["song_id"]), 0)
    part = next(x for x in m.parts if x.get("file"))
    assert part["role"] == "chop" and (m.stem_dir / part["file"]).exists()
