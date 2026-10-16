"""Hand-produced songs (studio/production.py, studio/last_train.py) and the instrument registry."""

import numpy as np
import soundfile as sf

from mouthmixer.arrange import instruments as IN
from mouthmixer.arrange import render
from mouthmixer.arrange.arranger import Track
from mouthmixer.studio import last_train as LT
from mouthmixer.studio import production as P


def test_chords_and_voicings():
    assert P.chord("C6/9")[0] == 0 and P.chord("C6/9")[3] is None
    assert P.chord("Am7/E")[3] == 4 and P.tones("A7#5#9") == {9, 1, 5, 7, 0}
    prev = None
    for nm in ["Dm9", "Bbmaj7", "Gm9", "A7#5#9", "Dm9"]:
        root = P.chord(nm)[0]
        v = P.upper(nm, prev, 55, 74)
        assert all(55 <= x <= 74 for x in v) and all(x % 12 in P.tones(nm) | {(root + 2) % 12} for x in v)
        assert root not in {x % 12 for x in v} or len(P.tones(nm)) <= 3  # rootless when it can be
        if prev:
            assert sum(abs(a - b) for a, b in zip(v, prev)) <= 12  # voice-led, not jumping around
        prev = v
    assert any(b - a <= 2 for a, b in zip(P.upper("Dm9", None)[:-1], P.upper("Dm9", None)[1:]))  # a second inside


def test_clear_of_moves_rubbing_chord_tones():
    melody = [(0.0, 2.0, P.n("F4"), 90)]
    harmony = [(0.0, 2.0, P.n("E4"), 80), (0.0, 2.0, P.n("C4"), 80)]
    out = P.clear_of(harmony, melody, lambda b: "Dm9")
    assert P.n("E4") not in [x[2] for x in out] and P.n("C4") in [x[2] for x in out]


def test_bass_lands_roots_on_the_changes():
    rng = np.random.default_rng(1)
    main, ghosts = P.bass_line(["Dm9", "Bbmaj7", "Gm9", "A7"], 0, "funk", rng)
    for bar, nm in enumerate(["Dm9", "Bbmaj7", "Gm9", "A7"]):
        first = min((x for x in main if bar * 4 - 0.6 <= x[0] <= bar * 4), key=lambda x: abs(x[0] - bar * 4))
        assert first[2] % 12 == P.chord(nm)[0]
    assert ghosts and all(g[3] < 70 for g in ghosts)


def test_last_train_structure_and_melody():
    song = LT.song()
    assert song.bars == 92 and len(LT.BARS) == 92 and abs(song.bpm - 126) < 1e-9
    names = {t.name for t in song.tracks}
    for want in ("Drums", "Finger bass", "Rhodes", "Organ", "Violins", "Trumpets", "Guide melody (for singing)"):
        assert want in names
    for t in song.tracks:
        assert t.notes and all(0 <= s < 92 * 4 + 4 and l > 0 for s, l, p, v in t.notes), t.name
    mel = next(t for t in song.tracks if t.role == "lead").notes
    assert min(p for _, _, p, _ in mel) >= P.n("A3") and max(p for _, _, p, _ in mel) <= P.n("G4")
    rubs = 0
    for t in song.tracks:
        if t.role in ("comp", "pad", "riff", "arp") or t.name == "Trumpets":
            for hs, hl, hp, hv in t.notes:
                for ms, ml, mp, _ in mel:
                    if hs < ms + ml and hs + hl > ms and (abs(mp - hp) == 1 or (hp < mp and (mp - hp) % 12 == 1 and mp - hp > 12)):
                        rubs += 1
    assert rubs == 0
    # the rap has no guide melody; the bridge drops the drums
    rap = [x for x in mel if LT.SEC["Rap Verse"] * 4 <= x[0] < LT.SEC["Chorus 2"] * 4]
    drums = next(t for t in song.tracks if t.role == "drums").notes
    assert not rap and not [x for x in drums if LT.SEC["Bridge"] * 4 <= x[0] < LT.SEC["Bridge build"] * 4]


def test_missing_libraries_fall_back_to_general_midi(home):
    IN._CACHE.clear()
    assert not IN.available("sfz:rhodes") and IN.fallback("sfz:rhodes") == "rhodes"
    t = Track("Rhodes", "comp", "sfz:rhodes", [(0, 1, 62, 100)])
    y = render.render_track(t, 120, 1.5, np.random.default_rng(0))
    assert np.abs(y).max() > 0.01  # played by the soundfont instead
    assert IN.available("synth:organ_jazz") and IN.available("sfx:boom")
    IN._CACHE.clear()


def test_folder_of_samples_becomes_an_instrument(tmp_path):
    sr = 44100
    for name, f in (("Vln_sus_A3_v1_rr1", 220), ("Vln_sus_A3_v1_rr2", 220), ("Vln_sus_A3_v2_rr1", 220),
                    ("Vln_sus_A4_v1_rr1", 440)):
        t = np.arange(sr) / sr
        sf.write(str(tmp_path / f"{name}.wav"), (0.3 * np.sin(2 * np.pi * f * t)).astype(np.float32), sr)
    text = IN.folder_sfz(tmp_path)
    (tmp_path / "x.sfz").write_text(text)
    from mouthmixer.arrange import sampler

    inst = sampler.Instrument(tmp_path / "x.sfz")
    keys = {(r.lokey, r.hikey, r.center) for r in inst.regions}
    assert (0, 63, 57) in keys and (64, 127, 69) in keys  # split halfway between A3 and A4
    assert any(r.seq_length == 2 for r in inst.regions) and {r.hivel for r in inst.regions if r.center == 57} == {64, 127}


def test_match_tone_moves_the_mix_toward_the_references():
    from mouthmixer.reference.analyse import band_shares

    rng = np.random.default_rng(0)
    spec = np.fft.rfft(rng.normal(0, 1, 44100 * 3))
    f = np.fft.rfftfreq(44100 * 3, 1 / 44100)
    pink = np.fft.irfft(spec / np.sqrt(np.maximum(f, 20)), 44100 * 3)  # music-like 1/f balance
    x = np.stack([pink, pink]).astype(np.float32) / np.abs(pink).max() * 0.3
    from pedalboard import Pedalboard, PeakFilter

    boxy = Pedalboard([PeakFilter(cutoff_frequency_hz=350, gain_db=10, q=0.8)])(x, 44100)
    before = band_shares(boxy.mean(0))["low_mid"]
    y, g = render.match_tone(boxy)
    assert g["low_mid"] < 0 and band_shares(y.mean(0))["low_mid"] < before - 1
    assert all(abs(v) <= 3.0 for v in g.values())


def test_match_tone_follows_one_reference_and_reads_saved_analyses(tmp_path, monkeypatch):
    import json

    from mouthmixer import config

    rng = np.random.default_rng(0)
    x = (rng.normal(0, 0.1, (2, 44100 * 2))).astype(np.float32)
    dark = {k: v for k, (_, v) in render.REF_BANDS.items()} | {"air": -30.0, "presence": -25.0}
    _, g = render.match_tone(x, limit_db=40, target=dark)
    _, g0 = render.match_tone(x, limit_db=40)
    assert g["air"] < g0["air"] and g["presence"] < g0["presence"]  # a darker reference pulls the top down
    monkeypatch.setattr(config, "home", lambda: tmp_path)
    assert render.ref_bands(["nope"]) is None  # no analyses on this machine: the default target
    for slug, air in (("a", -20.0), ("b", -10.0)):
        (tmp_path / "analysis" / slug).mkdir(parents=True)
        (tmp_path / "analysis" / slug / "analysis.json").write_text(json.dumps({"bands_db": dark | {"air": air}}))
    assert render.ref_bands(["a", "b"])["air"] == -15.0
