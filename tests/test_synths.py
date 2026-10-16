"""Synthesised organ and analog synth: right pitch, stereo where they should be, no blow-ups."""

import numpy as np

from mouthmixer.arrange import synths as SY

SR = SY.SR


def _peak_hz(x, lo=60, hi=3000):
    spec = np.abs(np.fft.rfft(x * np.hanning(len(x))))
    f = np.fft.rfftfreq(len(x), 1 / SR)
    sel = (f >= lo) & (f <= hi)
    return f[sel][np.argmax(spec[sel])]


def test_organ_plays_the_note_with_a_moving_leslie():
    y = SY.organ([(0.0, 1.0, 57, 100)], 1.2, "jazz")
    assert y.shape == (2, int(1.2 * SR)) and np.isfinite(y).all() and np.abs(y).max() < 2
    assert abs(_peak_hz(y[0, 2000:40000], 150, 300) - 220) < 4  # the 8' drawbar on A3
    assert not np.allclose(y[0], y[1])  # the rotor puts left and right a quarter turn apart


def test_synth_presets_pitch_and_release():
    for name in SY.SYNTHS:
        y = SY.synth([(0.0, 0.5, 60, 110)], 1.5, name)
        assert np.isfinite(y).all() and np.abs(y).max() <= 0.51, name
        assert np.abs(y[:, int(1.3 * SR):]).max() < 0.02, name  # silent after the release
    lead = SY.synth([(0.0, 0.8, 69, 110)], 1.0, "saw_lead")
    assert abs(_peak_hz(lead[0, 2000:30000], 200, 900) - 440) < 6


def test_chip_voices_and_kit():
    sq = SY.chip([(0.0, 0.5, 69, 110)], 1.0, "square")
    assert abs(_peak_hz(sq[0, :20000], 200, 900) - 440) < 6
    assert set(np.unique(np.sign(sq[0, 100:4000]))) <= {-1.0, 0.0, 1.0}  # a raw pulse wave, no filter
    tri = SY.chip([(0.0, 0.5, 45, 110)], 1.0, "triangle")
    d = np.abs(np.diff(tri[0, :4000]))
    assert np.mean(d > 0.05 * np.abs(tri[0, :4000]).max()) < 0.2  # flat stretches between jumps: stepped, NES-like
    kit = SY.chip_drums([(0.0, 0.2, 36, 110), (0.5, 0.2, 38, 110), (1.0, 0.1, 42, 90)], 1.5)
    assert np.isfinite(kit).all() and np.abs(kit[:, :SR // 4]).max() > 0.05


def test_ambience_textures_and_instrument_variants():
    from mouthmixer.arrange import instruments as I
    from mouthmixer.arrange import render as R

    rng = np.random.default_rng(1)
    n = R.SR * 4
    for name in ("sea", "hum", "room", "radio"):
        x = R.texture(name, n, rng)
        assert x.shape == (2, n) and 1e-4 < np.sqrt(np.mean(x ** 2)) < 0.3, name
    radio = R.texture("radio", n, rng)
    spec = np.abs(np.fft.rfft(radio[0]))
    f = np.fft.rfftfreq(n, 1 / R.SR)
    assert spec[(f > 400) & (f < 3500)].mean() > 5 * spec[f > 8000].mean()  # band-limited like AM
    tone = np.tile(np.sin(2 * np.pi * 220 * np.arange(n) / R.SR) * 0.3, (2, 1)).astype(np.float32)
    for character in ("tape", "radio", "old", "prepared"):
        y = I.variant_fx(character, tone, rng)
        assert y.shape == tone.shape and np.isfinite(y).all() and np.abs(y).max() > 0.01, character
    assert I.SAMPLED["sfz:piano_old"]["variant"] == ("sfz:piano", "old", 22)



def test_persona_sheet_synths_play_in_tune():
    import librosa

    for preset, key in (("acid", 43), ("virus_lead", 72), ("virus_bass", 36), ("fm_bass", 36), ("fm_pad", 60)):
        x = SY.synth([(0.05, 0.9, key, 100)], 1.2, preset).mean(axis=0)
        assert np.isfinite(x).all() and np.sqrt(np.mean(x ** 2)) > 0.01, preset
        f0, v, _ = librosa.pyin(x[: int(0.9 * SY.SR)], fmin=30, fmax=1500, sr=SY.SR)
        assert abs(librosa.hz_to_midi(np.nanmedian(f0[v])) - key) < 0.6, preset
    # FM: the modulator's depth falls, so the tone gets purer (fewer upper partials) as the note holds
    x = SY.synth([(0.0, 1.5, 48, 110)], 1.6, "fm_bass").mean(axis=0)
    f = np.fft.rfftfreq(4096, 1 / SY.SR)

    def share(seg):
        s = np.abs(np.fft.rfft(seg * np.hanning(len(seg))))
        return s[f > 400].sum() / s.sum()

    assert share(x[441:441 + 4096]) > share(x[int(1.0 * SY.SR):int(1.0 * SY.SR) + 4096]) * 1.5
