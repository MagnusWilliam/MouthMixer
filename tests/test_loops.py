"""The last LINE ZERO cues (menu, game over, the Line 0 ride, the Ward, FULL ASSAULT) and loop export for Roblox:
an unfaded master cut at the form's exact length with the ring-out laid over bar 1 (render.loop_cut)."""

import json

import numpy as np

from mouthmixer.arrange import render as R
from mouthmixer.studio import cues as C
from mouthmixer.studio import engine as E

SR = R.SR


def _cue_base(cid):
    start, secs = 0, []
    for nm, bars in C.CUES[cid]["form"]:
        secs.append({"name": nm, "start": start, "bars": bars})
        start += bars
    return {"sections": secs, "section_feels": [C.CUES[cid]["feels"][nm] for nm, _ in C.CUES[cid]["form"]],
            "lyric_sheet": []}


def test_last_cues_produce_with_their_motifs_textures_and_loop_flags():
    for cid in ("menu", "game_over", "line0_ride", "ward", "assault_sting"):
        cue = C.CUES[cid]
        song, gains = E.produce(C.resolved(cue), _cue_base(cid), seed=4)
        names = {t.name for t in song.tracks}
        assert any(nm.startswith("Theme") for nm in names), cid
        for tex in cue.get("textures", []):
            assert f"Ambience: {tex}" in names and f"Ambience: {tex}" in gains, (cid, tex)
        if cue.get("themes2"):
            assert "Countermelody" in names, cid
    # stings and the through-composed ride get no loop; menu and the Ward loop
    assert [c for c in ("menu", "ward") if C.CUES[c].get("loop", True)] == ["menu", "ward"]
    assert not any(C.CUES[c].get("loop", True) for c in ("game_over", "line0_ride", "assault_sting"))
    # FULL ASSAULT: one bar at battle tempo (1.5-3 s), the punch (ka on 2.75, CHK on 3) on the snare
    st = E.STYLES["assault_sting"]
    assert st["bpm"] == E.STYLES["boss_choir"]["bpm"] and 1.5 <= 4 * 60 / st["bpm"] <= 3.0
    song, _ = E.produce(C.resolved(C.CUES["assault_sting"]), _cue_base("assault_sting"), seed=4)
    snare = sorted(round(s, 2) for s, _, p, _ in next(t for t in song.tracks if t.name == "Drums").notes if p == E.DRUM["snare"])
    assert 2.75 in snare and 3.0 in snare
    # the ride is about a minute and a half
    ride = sum(b for _, b in C.CUES["line0_ride"]["form"]) * 4 * 60 / E.STYLES["line0_ride"]["bpm"]
    assert 75 <= ride <= 105
    # game over: the Hum falling on solo piano (D A Bb A G), with no drums or bass
    go = [p for _, _, p in C.resolved(C.CUES["game_over"])["themes"]["Sting"]]
    assert go == [74, 69, 70, 69, 67]
    song, _ = E.produce(C.resolved(C.CUES["game_over"]), _cue_base("game_over"), seed=4)
    assert not [t for t in song.tracks if t.role in ("drums", "bass")]


def test_new_textures_wheels_doors_bubbles():
    rng = np.random.default_rng(2)
    n = SR * 6
    for name in ("wheels", "doors", "bubbles"):
        x = R.texture(name, n, rng)
        assert x.shape == (2, n) and np.isfinite(x).all() and np.abs(x).max() > 1e-3, name
    doors = R.texture("doors", n, rng)
    assert np.abs(doors[:, : n - 4 * SR]).max() == 0  # the doors close once, at the end
    wheels = np.abs(R.texture("wheels", n, rng)).mean(axis=0)
    # da-dum once a second: louder just after each joint than half a second later
    on = np.mean([wheels[int(k * SR): int(k * SR) + SR // 20].mean() for k in range(5)])
    off = np.mean([wheels[int((k + .5) * SR): int((k + .5) * SR) + SR // 20].mean() for k in range(5)])
    assert on > 3 * off


def test_master_without_fade_keeps_the_tail():
    rng = np.random.default_rng(0)
    x = (rng.normal(0, 0.1, (2, SR * 5))).astype(np.float32)
    faded, unfaded = R.master(x), R.master(x, fade=False)
    assert np.abs(faded[:, -100:]).max() < 1e-3
    assert np.abs(unfaded[:, -SR // 2:]).std() > 0.5 * np.abs(unfaded[:, SR:2 * SR]).std()


def _seam_click(y: np.ndarray, w: int = 2000) -> float:
    """How much the loop's wrap (end -> start) sticks out: the second difference at the seam over the 99.9th
    percentile of the second difference around it. A click is a spike far above the music's own."""
    z = np.concatenate([y[:, -w:], y[:, :w]], axis=1)
    d2 = np.abs(np.diff(z, 2, axis=1)).max(axis=0)
    seam = d2[w - 4: w + 2].max()
    rest = np.concatenate([d2[: w - 50], d2[w + 50:]])
    return float(seam / np.percentile(rest, 99.9))


def _synthetic_cue(bpm=90, bars=4, tail_s=3.0):
    """A held chord ringing through the end of the form (not a whole number of cycles in it) and a decaying
    'reverb' past the cut, as a mastered cue would have."""
    L = C.loop_samples(bars, bpm)
    n = L + int(tail_s * SR)
    t = np.arange(n) / SR
    tone = sum(np.sin(2 * np.pi * f * t + ph) for f, ph in ((110.3, 0.0), (164.9, 0.4), (277.7, 1.1))) * 0.2
    env = np.ones(n)
    env[L:] = np.exp(-(t[L:] - t[L]) / 0.6)  # the ring-out after the last bar
    onset = np.minimum(1, t / 0.002)  # bar 1 starts from silence
    x = np.stack([tone * env * onset, 0.9 * tone * env * onset]).astype(np.float32)
    return x, L


def test_loop_cut_is_exact_and_the_seam_has_no_click():
    x, L = _synthetic_cue()
    y = R.loop_cut(x, L)
    assert y.shape == (2, L)  # exactly the form: 4 bars at 90
    assert L == round(4 * 4 * 60 / 90 * SR)
    assert _seam_click(y) < 2.0
    # the measure finds a click: a plain cut at the same point jumps
    assert _seam_click(np.array(x[:, :L])) > 10
    # the ring-out is laid over bar 1 (not thrown away), and nothing goes over the ceiling
    assert np.abs(y[:, 100:1000] - x[:, 100:1000]).max() > 0.01
    assert np.abs(y).max() <= 10 ** (-1 / 20) + 1e-6
    # from bar 1's own start (silence + a 3 ms ramp), the wrap continues the ring-out sample for sample
    assert abs(float(y[0, 0]) - float(x[0, L])) < 1e-4


def test_loop_file_keeps_its_exact_length(tmp_path):
    x, L = _synthetic_cue(bpm=150, bars=2)
    y = R.loop_cut(x, L)
    import soundfile as sf

    R.write_audio(y, tmp_path / "v1-loop.flac")
    back, sr = sf.read(str(tmp_path / "v1-loop.flac"))
    assert sr == SR and back.shape[0] == L
    assert np.abs(back.T - y).max() < 1e-4 and _seam_click(back.T.astype(np.float32)) < 2.0  # lossless: the seam survives


def test_export_loop_writes_the_file_and_records_it(tmp_path, monkeypatch):
    from mouthmixer.arrange import mixer

    x, L = _synthetic_cue(bpm=100, bars=4)

    class FakeSong:
        bars, bpm = 4, 100

    class FakeMixer:
        def __init__(self, song_dir, vi):
            self.v = json.loads((song_dir / "song.json").read_text())["versions"][vi]

        def render_stems(self):
            return []

        def song(self, include_muted=False):
            return FakeSong()

        def _stems(self, n):
            return x * 0.5, x * 0.5, None, {}

    monkeypatch.setattr(mixer, "Mixer", FakeMixer)
    monkeypatch.setattr(R, "song_length", lambda s: (x.shape[1] / SR, x.shape[1]))
    monkeypatch.setattr(R, "match_tone", lambda a, **k: (a, {}))
    (tmp_path / "song.json").write_text(json.dumps({"versions": [{"file": "v0.ogg"}, {"file": "v3.ogg"}]}))
    name = C.export_loop(tmp_path, 1)
    assert name == "v3-loop.flac" and (tmp_path / name).exists()
    rec = json.loads((tmp_path / "song.json").read_text())["versions"][1]
    assert rec["loop_file"] == name and rec["loop_samples"] == L
    import soundfile as sf

    y, _ = sf.read(str(tmp_path / name))
    assert y.shape[0] == L and _seam_click(y.T.astype(np.float32)) < 2.0
