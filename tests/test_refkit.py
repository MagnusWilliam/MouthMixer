"""The toolkit for the reference-modelled songs (studio/refkit.py) and the stem profiler (reference/profile.py)."""

import json

import numpy as np

from mouthmixer.studio import refkit as K
from mouthmixer.studio.production import tones


def _plan(**kw):
    form = [("Intro", "intro", 2, 1), ("Verse", "verse", 4, 2), ("Chorus", "chorus", 4, 3)]
    progs = {"intro": ["Cmaj7"], "verse": ["Am7|D7", "Gmaj7"], "chorus": ["Fmaj7", "G7"]}
    return K.Plan(100, 0, "major", form, progs, **kw)


def test_plan_lays_out_form_and_split_bars():
    p = _plan()
    assert p.total == 10 and [s.start for s in p.secs] == [0, 2, 6]
    assert p.chord_at(8.0) == "Am7" and p.chord_at(10.5) == "D7" and p.chord_at(25.0) == "Fmaj7"
    assert p.sec_at(7).name == "Chorus"


def test_patterns_holds_variation_and_swing():
    assert K.events("x--x....", 0) == [(0.0, 1.5, "x"), (1.5, 0.5, "x")]
    p = _plan()
    kit = {2: {"kick": ["x.......x.......", "x...x...x...x..."], "snare": "....x.......x...", "hat": "x.x.x.x.x.x.x.x."},
           3: {"kick": "x...x...x...x...", "snare": "....X.......X...", "ride": "x.x.x.x.x.x.x.x."}}
    d = K.drums(p, kit, np.random.default_rng(0))
    kicks = sorted(s for s, _, k, _ in d if k == 36)
    assert [k for k in kicks if 8 <= k < 16] == [8.0, 10.0, 12.0, 13.0, 14.0, 15.0]  # bar 1, then bar 2's variation
    assert not [s for s, _, k, _ in d if s < 8]  # the intro (energy 1) has no kit style: silence
    assert any(k == 49 and abs(s - 24.0) < 0.05 for s, _, k, _ in d)  # a crash on the chorus
    fill = [s for s, _, k, _ in d if k == 38 and 22 <= s < 24]
    assert len(fill) == 8  # a 16th-note fill into the bigger section
    sw = K.swing([(0.5, 0.5, 60, 90), (1.25, 0.25, 60, 90)], K.Plan(100, 0, "major", [("A", "verse", 1, 1)],
                                                                    {"verse": ["C"]}, swing8=0.66, swing16=0.6))
    assert abs(sw[0][0] - 0.66) < 1e-6 and abs(sw[1][0] - 1.3) < 1e-6
    assert abs(K.shuffle([(2.5, 0.5, 60, 90)], 0.66)[0][0] - 2.66) < 1e-6


def test_bass_tokens_follow_the_chords():
    p = _plan()
    main, ghosts = K.bass(p, {2: "R...O...5...A.D.", 3: "R---------------"}, lo=28, rng=np.random.default_rng(0))
    bar2 = sorted(n for n in main if 8 <= n[0] < 12)  # Am7 | D7
    assert bar2[0][2] % 12 == 9 and bar2[1][2] == bar2[0][2] + 12  # root, octave
    assert bar2[2][2] % 12 == 9  # the fifth of D (A) on beat 3, where D7 sounds
    assert bar2[3][2] % 12 == 6  # A: a half step under the next bar's root (G)
    assert any(abs(g[0] - 11.5) < 0.05 for g in ghosts)
    assert max(l_ for s, l_, _, _ in main if s >= 24) > 3  # a held root in the chorus


def test_melody_degrees_and_fitting():
    p = _plan()
    m = K.melody(p, 6, "1' - 3' . #4' b7' . .", base=60)
    assert [(s, l_, n) for s, l_, n, _ in m] == [(24.0, 1.0, 72), (25.0, 0.5, 76), (26.0, 0.5, 78), (26.5, 0.5, 82)]
    fitted = K.fit([(24.0, 1.0, 71, 90), (28.0, 1.0, 68, 90), (24.5, 0.5, 71, 90)], p)  # B over Fmaj7, G# over G7
    assert fitted[0][2] % 12 in tones("Fmaj7") and fitted[1][2] % 12 in tones("G7")
    assert fitted[2][2] == 71  # an off-beat passing note stays
    assert K.lengthen([(0, 0.5, 60, 90), (1.0, 0.5, 62, 90), (3.0, 0.5, 64, 90)], 0.6)[0][1] > 0.9


def test_horns_voice_trumpet_over_sax_over_trombone():
    trp, sax, tbn = K.horns(_plan(), {3: "x---x---x---x---"}, np.random.default_rng(0))
    assert len(trp) == len(sax) == len(tbn) == 16
    for a, b, c in zip(sorted(trp), sorted(sax), sorted(tbn)):
        assert a[2] > b[2] > c[2] and a[2] >= 68


def test_balance_puts_groups_at_the_target_spacing():
    from mouthmixer.arrange import styles  # noqa: F401  (registers the packs)
    from mouthmixer.arrange.arranger import Track
    from mouthmixer.studio.production import build_song

    p = _plan()
    d = K.drums(p, {1: {"kick": "x...x...x...x...", "snare": "....x.......x...", "hat": "x.x.x.x.x.x.x.x."}},
                np.random.default_rng(0))
    b, _ = K.bass(p, {1: "R.R.R.R.R.R.R.R."}, rng=np.random.default_rng(0))
    pads = K.pad(p, (1, 2, 3), lo=55, hi=76)
    song = build_song("persona_city", p.bpm, p.tonic, p.mode, [(s.name, s.start, s.bars) for s in p.secs], p.bars,
                      [Track("Drums", "drums", "kit:room", d), Track("Bass", "bass", "finger_bass", b),
                       Track("Pad", "pad", "strings", pads)], seed=1)
    target = {"drums": -6.0, "bass": -4.0, "other": -14.0}
    gains, rep = K.balance(song, {}, {"Drums": "drums", "Bass": "bass", "Pad": "other"}, target)
    # the report is the level before the last correction: render again at the new gains to check
    _, rep2 = K.balance(song, gains, {"Drums": "drums", "Bass": "bass", "Pad": "other"}, target, rounds=1)
    assert abs((rep2["bass"] - rep2["drums"]) - 2.0) < 1.0 and abs((rep2["other"] - rep2["drums"]) + 8.0) < 1.0
    assert gains["Drums"] == 0.0


def test_target_levels_read_profiles(tmp_path, monkeypatch):
    from mouthmixer import config

    monkeypatch.setattr(config, "home", lambda: tmp_path)
    (tmp_path / "analysis" / "a").mkdir(parents=True)
    (tmp_path / "analysis" / "a" / "profile.json").write_text(json.dumps(
        {"stems": {"drums": {"lu_vs_mix": -5.0}, "vocals": {"lu_vs_mix": -3.0}, "piano": {"lu_vs_mix": None}}}))
    t = K.target_levels(["a", "missing"])
    assert t["drums"] == -5.0 and t["lead"] == -3.0 and t["piano"] == K.DEFAULT_TARGET["piano"]


def test_stem_profile_measures_level_rhythm_register_and_length():
    from mouthmixer.reference import profile as PR

    sr = PR.SR
    bars = 8
    n = int(bars * 2.0 * sr)
    beats = np.arange(0, bars * 4) * 0.5
    bar_t = np.r_[beats[::4], n / sr]
    # a "bass": an A2 (110 Hz) pluck on every beat, dying away within 0.2 s; the "mix" adds a noise bed
    bass = np.zeros(n)
    for b in beats:
        a = int(b * sr)
        seg = np.arange(int(0.3 * sr)) / sr
        bass[a:a + len(seg)] += np.sin(2 * np.pi * 110 * seg) * np.exp(-seg * 25)
    stem = np.stack([bass, bass]) * 0.3
    mix = stem + np.random.default_rng(0).normal(0, 0.05, (2, n))
    prof = PR.stem_profile("bass", stem.astype(np.float32), mix.astype(np.float32), beats, bar_t)
    assert prof["rhythm"]["onsets_per_active_bar"] in (3.0, 4.0, 5.0)
    assert sum(prof["rhythm"]["step_share"][0::4]) > 0.8  # on the beats
    assert abs(prof["pitch"]["midi_p10_p50_p90"][1] - 45) <= 1
    assert prof["note_length_beats"] < 0.5 and prof["lu_vs_mix"] < 0 and prof["width_side_vs_mid_db"] < -40



def test_every_reference_song_builds_both_takes_with_a_lead_to_mute():
    from mouthmixer.arrange import styles  # noqa: F401
    from mouthmixer.arrange.styles import INSTRUMENTS
    from mouthmixer.studio import refsongs as R

    for key, spec in R.SONGS.items():
        assert spec["refs"] and set(spec["takes"]) == {"A", "B"}, key
        for take in "AB":
            plan, tracks, gains, cats = spec["build"](take)
            secs = sum(s.bars for s in plan.secs) * 240 / plan.bpm
            assert 140 <= secs <= 240, (key, take, secs)  # instrumentals of 2:20-4:00
            leads = [t for t in tracks if t.role == "lead"]
            assert len(leads) == 1 and leads[0].name.startswith("Lead: ") and leads[0].notes, (key, take)
            assert cats[leads[0].name] == "lead"
            names = [t.name for t in tracks]
            assert len(names) == len(set(names)), (key, take)
            for t in tracks:
                if t.notes and t.role not in ("drums", "perc", "fx") and t.instrument in INSTRUMENTS:
                    lo, hi = INSTRUMENTS[t.instrument][2:4]
                    out = sum(1 for _, _, p, _ in t.notes if not lo <= p <= hi)
                    assert out <= 0.05 * len(t.notes), (key, take, t.name)
        assert key in R.TRIMS
