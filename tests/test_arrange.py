"""The arranger, mixer, critic and songwriter (PLAN §7-8, §11; MUSIC_KNOWLEDGE)."""

import json
import time

import numpy as np
import pytest

from mouthmixer import synth as S
from mouthmixer.analysis import detect, pipeline
from mouthmixer.arrange import arranger, critic, render, songwriter
from mouthmixer.arrange.styles import INSTRUMENTS, PACKS
from mouthmixer.listener.service import ClipWriter


@pytest.fixture(scope="module")
def clips():
    out = {}
    for i, (name, bpm) in enumerate([("ode", 96), ("minor", 104), ("repeat", 88)]):
        y, _ = S.hum(S.melody(name), bpm=bpm, seed=i)
        out[f"m{i}"] = songwriter.ClipInfo(f"m{i}", pipeline.analyse(y, S.SR), time.time())
    y, _ = S.beatbox(bars=4, bpm=96, seed=5)
    out["b0"] = songwriter.ClipInfo("b0", pipeline.analyse(y, S.SR), time.time())
    return out


@pytest.mark.parametrize("pack", list(PACKS))
def test_every_style_arranges_a_full_song(pack, clips):
    c = clips["m0"]
    song = arranger.arrange(pack_name=pack, seed=3, melody=c.result["notes"], clip_bpm=c.bpm, key=c.result["key"])
    roles = {t.role for t in song.tracks}
    assert {"lead", "comp", "bass", "drums", "pad"} <= roles
    assert len({t.instrument for t in song.tracks}) >= 6  # many different instruments
    assert [s[0] for s in song.sections] == ["Intro", "A", "A'", "B", "A''", "Ending"]
    lo, hi = PACKS[pack]["bpm"]
    assert lo <= song.bpm <= hi
    for t in song.tracks:  # MUSIC_KNOWLEDGE A4
        if not t.instrument.startswith("kit:"):
            a, b = INSTRUMENTS[t.instrument][2:4]
            assert all(a <= p <= b for _, _, p, _ in t.notes), t.name
    assert song.tracks[0].mine  # the lead is the user's melody


def test_most_candidates_pass_the_critic(clips):
    rng = np.random.default_rng(1)
    specs = songwriter.candidates(clips["m1"], [clips["b0"], clips["m2"]], 20, rng)
    ok = sum(critic.judge(songwriter.build(s, clips))["ok"] for s in specs)
    assert ok >= 16


def test_mix_is_polished(clips):
    import pyloudnorm as pyln

    c = clips["m0"]
    song = arranger.arrange(pack_name="city_pop_day", seed=4, melody=c.result["notes"], clip_bpm=c.bpm, key=c.result["key"])
    x, stems = render.mix(song)
    assert np.isfinite(x).all()
    lufs = pyln.Meter(render.SR).integrated_loudness(x.T)
    assert abs(lufs - (-14)) < 1.0  # MUSIC_KNOWLEDGE X2
    assert 20 * np.log10(np.abs(x).max()) <= -0.9  # X1
    v = critic.judge(song, x, stems)
    assert v["ok"], v["rejects"]
    assert v["details"]["lead_vs_rest_db"] > -2  # X4: the melody is heard
    assert abs(x.shape[1] / render.SR - (song.bars * 4 * 60 / song.bpm + 3)) < 0.5


def test_songwriter_combines_clips_and_writes_files(clips, tmp_path):
    rec = songwriter.write_songs(clips["b0"], [clips["m0"]], tmp_path, n=6, render_top=2, keep=2, seed=3)
    assert rec and rec["versions"]
    v = rec["versions"][0]
    assert (tmp_path / v["file"]).exists() and (tmp_path / v["midi"]).exists()
    assert json.loads((tmp_path / "song.json").read_text())["versions"][0]["title"] == v["title"]
    # A beat with a tempo-matching melody clip gets combined with it most of the time.
    assert any("m0" in x["spec"]["clips"] for x in rec["versions"]) or rec["made"] >= 6


def test_clip_quality_separates_music_from_talking():
    for i in range(3):
        y, _ = S.hum(S.melody(["ode", "minor", "repeat"][i]), seed=i, drift=0.04)
        assert critic.clip_quality(pipeline.analyse(y, S.SR))["ok"]
        assert not critic.clip_quality(pipeline.analyse(S.talking(6, seed=i), S.SR))["ok"]
        yb, _ = S.beatbox(seed=i)
        assert critic.clip_quality(pipeline.analyse(yb, S.SR))["ok"]


@pytest.mark.parametrize("seed", range(3))
def test_unsure_clips_get_a_second_opinion(seed):
    for y in (S.talking(5, seed=seed), S.typing(5, seed=seed)):
        assert not ClipWriter.second_opinion(y, detect.judge(y, S.SR)).is_music
