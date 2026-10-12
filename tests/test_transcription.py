"""Stages C and D: hums and beatbox become the right notes and hits (PLAN §4-5)."""

import numpy as np
import pytest

from mouthmixer import synth as S
from mouthmixer.analysis import beatbox, key, pipeline, timing


def _check(name, **kw):
    y, _ = S.hum(S.melody(name), **kw)
    r = pipeline.analyse(y, S.SR)
    exp = [m for m, _ in S.melody(name) if m >= 0]
    got = [n["pitch"] for n in r["notes"]]
    starts = [n["grid_start"] for n in r["notes"]]
    true = list(np.cumsum([0] + [b for _, b in S.melody(name)])[:-1])
    rel = [round(s - starts[0], 2) for s in starts]
    return got == exp, rel == [round(t - true[0], 2) for t in true], r


@pytest.mark.parametrize("name,bpm,drift,offset", [
    ("ode", 96, 0.0, 0), ("ode", 120, 0.06, -35), ("minor", 110, -0.05, 20), ("repeat", 84, 0.0, 0),
    ("minor", 96, 0.05, -20), ("ode", 150, -0.06, 30),
])
def test_hums_come_out_note_perfect(name, bpm, drift, offset):
    pitches_ok, timing_ok, r = _check(name, bpm=bpm, drift=drift, global_offset_cents=offset, seed=2)
    assert pitches_ok and timing_ok
    assert abs(r["tempo"]["bpm"] / bpm - 1) < 0.04


def test_legato_hum_without_gaps():
    pitches_ok, timing_ok, _ = _check("ode", bpm=100, gap_beats=0.0, seed=3)
    assert pitches_ok and timing_ok


def test_slow_eighth_notes_offer_half_tempo():
    # 8th notes at 72 BPM look exactly like quarters at 144; the half-tempo reading must be offered.
    y, _ = S.hum(S.melody("minor"), bpm=72, drift=0.06, seed=2)
    r = pipeline.analyse(y, S.SR)
    bpms = [r["tempo"]["bpm"]] + [a["bpm"] for a in r["tempo"]["alternatives"]]
    assert any(abs(b / 72 - 1) < 0.05 for b in bpms)


def test_keys_and_tuning():
    y, _ = S.hum(S.melody("ode"), global_offset_cents=-30, seed=1)
    r = pipeline.analyse(y, S.SR)
    assert r["key"]["name"] == "D major"
    assert -0.45 < r["tuning_offset"] < -0.15
    y, _ = S.hum(S.melody("minor"), seed=1)
    assert pipeline.analyse(y, S.SR)["key"]["name"] in ("A minor", "A dorian")


def test_scale_snap_keeps_deliberate_chromatic_notes():
    assert key.snap(66.4, 2, "major", 1.0) == (66, False)  # sharp F# in D major -> F#
    assert key.snap(65.05, 2, "major", 1.0) == (65, True)  # clean F held a beat: kept on purpose
    assert key.snap(65.4, 2, "major", 0.25)[0] in (64, 66)  # short wobbly F: moved into the scale


@pytest.mark.parametrize("seed", range(6))
def test_beatbox_hits(seed):
    pattern = ["k", "h", "s", "h", "k", "o", "s", "h"] if seed % 2 else None
    y, truth = S.beatbox(seed=seed, bars=4, pattern=pattern)
    hits = beatbox.transcribe(y, S.SR)
    ok = sum(1 for t, n in truth if any(abs(h.onset - t) < 0.03 and h.name == n for h in hits))
    assert ok / len(truth) >= 0.95
    assert len(hits) <= len(truth) + 1


def test_calibration_learns_your_sounds(tmp_path):
    cal = beatbox.Calibration(tmp_path / "cal.json")
    for label, sym in (("kick", "k"), ("snare", "s"), ("hat", "h")):
        y, _ = S.beatbox([sym, "-"] * 4, bars=2, seed=10)
        assert beatbox.calibrate_from_take(y, S.SR, label, cal) >= 6
    cal.save()
    cal2 = beatbox.Calibration(tmp_path / "cal.json")
    assert cal2.ready
    y, truth = S.beatbox(seed=11, bars=2)
    hits = beatbox.transcribe(y, S.SR, cal2)
    ok = sum(1 for t, n in truth if any(abs(h.onset - t) < 0.03 and h.name == n for h in hits))
    assert ok / len(truth) >= 0.9


def test_swing_is_detected_and_kept():
    y, _ = S.beatbox(["k", "h", "s", "h"] * 2, swing=0.64, bpm=90, bars=4, seed=3)
    r = pipeline.analyse(y, S.SR)
    assert r["tempo"]["swing"] > 0.58
    offbeats = [d["start"] % 1 for d in r["drums"] if 0.3 < d["start"] % 1 < 0.9]
    assert offbeats and all(o > 0.56 for o in offbeats)


def test_quantize_strength():
    b = np.array([0.1, 0.9, 2.12])
    full = timing.quantize(b, strength=1.0)
    part = timing.quantize(b, strength=0.7)
    assert np.allclose(full, [0.0, 1.0, 2.0])
    assert np.all(np.abs(part - full) < np.abs(b - full))


def test_process_file_writes_everything(tmp_path):
    import pretty_midi
    import soundfile as sf

    y, _ = S.hum(S.melody("ode"), seed=1)
    sf.write(tmp_path / "hum.wav", y, S.SR)
    r = pipeline.process_file(tmp_path / "hum.wav", tmp_path / "out")
    for f in ("result.json", "clean.mid", "raw.mid", "preview.wav"):
        assert (tmp_path / "out" / f).exists()
    pm = pretty_midi.PrettyMIDI(str(tmp_path / "out" / "clean.mid"))
    assert [n.pitch for n in pm.instruments[0].notes] == [n["pitch"] for n in r["notes"]]


def test_bar_one_lands_on_the_first_kick_and_first_note():
    for seed in range(3):
        y, _ = S.beatbox(bars=4, seed=seed)
        drums = pipeline.analyse(y, S.SR)["drums"]
        assert drums[0]["name"] == "kick" and abs(drums[0]["start"]) < 0.05
    y, _ = S.hum(S.melody("ode"), bpm=92, drift=0.05, global_offset_cents=-30, seed=4)
    assert abs(pipeline.analyse(y, S.SR)["notes"][0]["start"]) < 0.05
