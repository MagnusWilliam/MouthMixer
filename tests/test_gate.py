"""Stage B: the music gate keeps hums and beatbox and drops talking and typing (PLAN §3)."""

import pytest

from mouthmixer import synth as S
from mouthmixer.analysis import detect


@pytest.mark.parametrize("seed", range(3))
def test_hums_are_melody(seed):
    for name in ("ode", "minor", "repeat"):
        y, _ = S.hum(S.melody(name), seed=seed, drift=0.04, global_offset_cents=-25)
        assert detect.judge(y, S.SR).kind == "melody", name


@pytest.mark.parametrize("seed", range(3))
def test_beatbox_is_beat(seed):
    y, _ = S.beatbox(seed=seed)
    assert detect.judge(y, S.SR).kind == "beat"


@pytest.mark.parametrize("seed", range(4))
def test_talking_and_typing_are_dropped(seed):
    assert not detect.judge(S.talking(seed=seed), S.SR).is_music
    assert not detect.judge(S.typing(seed=seed), S.SR).is_music


def test_scan_finds_the_hum_in_a_long_recording():
    import numpy as np

    hum, _ = S.hum(S.melody("ode"), seed=1)
    y = np.concatenate([S.silence(6), S.talking(5), S.silence(6), hum, S.silence(6), S.typing(5), S.silence(4)])
    found = [f for f in detect.scan(y, S.SR) if f["is_music"]]
    assert len(found) == 1
    hum_start = 17.0
    assert found[0]["start"] <= hum_start + 0.5 and found[0]["end"] >= hum_start + len(hum) / S.SR - 1.0
