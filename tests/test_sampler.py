"""The SFZ player on a generated instrument: key and velocity mapping, pitch, round robins, envelopes,
choke groups."""

import numpy as np
import soundfile as sf

from mouthmixer.arrange import sampler as SM

SR = SM.SR


def _tone(f, sec=1.0, amp=0.5):
    t = np.arange(int(sec * SR)) / SR
    return (amp * np.sin(2 * np.pi * f * t) * np.exp(-t * 2)).astype(np.float32)


def _f0(x):
    seg = x[: SR // 4]
    spec = np.abs(np.fft.rfft(seg * np.hanning(len(seg))))
    return np.fft.rfftfreq(len(seg), 1 / SR)[np.argmax(spec)]


def test_sfz_maps_keys_velocities_and_pitch(tmp_path):
    d = tmp_path / "samples"
    d.mkdir()
    sf.write(str(d / "a3_soft.wav"), _tone(220, amp=0.2), SR)
    sf.write(str(d / "a3_loud.wav"), _tone(220, amp=0.8), SR)
    sf.write(str(d / "a4.wav"), _tone(440), SR)
    (tmp_path / "inst.sfz").write_text("""
// a test instrument
<control> default_path=samples/
<global> ampeg_release=0.2
<group> lokey=40 hikey=62 pitch_keycenter=a3
<region> sample=a3_soft.wav lovel=1 hivel=80
<region> sample=a3_loud.wav lovel=81 hivel=127
<group> lokey=63 hikey=90
<region> sample=a4.wav pitch_keycenter=69 tune=0
""")
    inst = SM.Instrument(tmp_path / "inst.sfz")
    assert len(inst.regions) == 3
    soft = inst.render([(0.0, 0.5, 57, 60)], 1.0)
    loud = inst.render([(0.0, 0.5, 57, 120)], 1.0)
    assert np.abs(loud).max() > 2.5 * np.abs(soft).max()  # the loud layer, and louder velocity
    up = inst.render([(0.0, 0.5, 60, 100)], 1.0)  # C4 from the A3 sample: 3 semitones up
    assert abs(_f0(up[0]) - 261.6) < 6
    hi = inst.render([(0.0, 0.5, 72, 100)], 1.0)  # C5 from the A4 sample
    assert abs(_f0(hi[0]) - 523.3) < 8
    # release: the note stops sounding after note-off + release
    tail = inst.render([(0.0, 0.2, 57, 100)], 1.0)
    assert np.abs(tail[:, int(0.6 * SR):]).max() < 1e-3


def test_round_robin_and_choke(tmp_path):
    for name, f in (("hat1", 6000), ("hat2", 7000), ("open", 5000)):
        sf.write(str(tmp_path / f"{name}.wav"), _tone(f, sec=1.5), SR)
    (tmp_path / "kit.sfz").write_text("""
<group> key=42 seq_length=2 group=1
<region> sample=hat1.wav seq_position=1
<region> sample=hat2.wav seq_position=2
<group> key=46 group=2 off_by=1 loop_mode=one_shot
<region> sample=open.wav
""")
    inst = SM.Instrument(tmp_path / "kit.sfz")
    a = SM.render_kit(inst, [(0.0, 0.1, 42, 100), (0.5, 0.1, 42, 100)], 1.2)
    assert abs(_f0(a[0, :SR // 4]) - 6000) < 50 and abs(_f0(a[0, int(0.5 * SR):int(0.75 * SR)]) - 7000) < 50
    b = SM.render_kit(inst, [(0.0, 0.1, 46, 100), (0.4, 0.1, 42, 100)], 1.2)  # open hat, then closed
    open_part = b[0, int(0.45 * SR):int(0.55 * SR)]
    assert abs(_f0(np.r_[open_part, np.zeros(SR // 4 - len(open_part))]) - 6000) < 60  # only the closed hat now
    c = SM.render_kit(inst, [(0.0, 0.1, 46, 100)], 1.2)  # no closed hat: the open one rings on
    assert np.abs(c[0, int(0.6 * SR):int(0.7 * SR)]).max() > 0.05


def test_note_names():
    assert SM.note_number("c4") == 60 and SM.note_number("a3") == 57 and SM.note_number("f#2") == 42
    assert SM.note_number("bb1") == 34 and SM.note_number("64") == 64



def test_cc_layers_keyswitches_generators_and_includes(tmp_path):
    d = tmp_path / "samples"
    d.mkdir()
    for name, f in (("closed", 300), ("open", 600), ("legato", 220), ("stac", 440)):
        sf.write(str(d / f"{name}.wav"), _tone(f), SR)
    (tmp_path / "maps").mkdir()
    # an include written relative to the top file (the SFZ spec), from a file in a subfolder
    (tmp_path / "maps" / "hats.sfz").write_text(
        "<region> sample=closed.wav key=46 locc4=0 hicc4=63\n<region> sample=open.wav key=46 locc4=64 hicc4=127\n")
    (tmp_path / "maps" / "all.sfz").write_text('#include "maps/hats.sfz"\n')
    (tmp_path / "kit.sfz").write_text("""
<control> default_path=samples/ set_cc4=10
#include "maps/all.sfz"
<region> sample=*sine key=50
<region> sample=legato.wav key=60 sw_last=24
<region> sample=stac.wav key=60 sw_last=25
""")
    inst = SM.Instrument(tmp_path / "kit.sfz")
    assert sorted(r.sample.name for r in inst.regions) == ["closed.wav", "legato.wav"]  # set_cc default, lowest switch
    inst2 = SM.Instrument(tmp_path / "kit.sfz", cc={4: 127}, keyswitch=25)
    assert sorted(r.sample.name for r in inst2.regions) == ["open.wav", "stac.wav"]
    x = inst2.render([(0.0, 0.5, 46, 100)], 0.6, np.random.default_rng(0))
    assert abs(_f0(x.mean(axis=0)) - 600) < 10
