"""Vocals (docs/VOCALS.md), lyrics (§8) and the part catalog, on synthetic singing (synth.sing)."""

import numpy as np
import pytest

from mouthmixer import synth as S
from mouthmixer.arrange import catalog, lyrics
from mouthmixer.arrange import vocals as V

BPM = 100
MEL = [(0, 1, 62), (1, 1, 64), (2, 1, 66), (3, 1, 67), (4, 2, 69), (6, 2, 66),
       (9, 1, 64), (10, 1, 66), (11, 1, 67), (12, 1, 69), (13, 1, 71), (14, 2, 69)]
LEAD = [(4 + s, l, m) for s, l, m in MEL]  # from bar 2
SECTIONS = [{"name": "A", "start": 0, "bars": 2}, {"name": "A''", "start": 2, "bars": 4}]


def _take(seed, **kw):
    x, truth = S.sing(LEAD, BPM, pre_roll=0.0, seed=seed, **kw)
    return V.Take(x, 0.0, f"t{seed}"), truth


@pytest.fixture(scope="module")
def produced():
    tk, truth = _take(1, detune_cents=35, timing_ms=35, lateness_ms=15, sibilants=0.5)
    res = V.produce([tk], LEAD, BPM, SECTIONS, 2, "major", "soul", length=len(tk.audio) / V.SR + 0.5)
    return res, truth


def test_natural_tuning_fixes_pitch_and_keeps_feel(produced):
    res, truth = produced
    q = res.report["quality"]
    assert q["pitch_before_cents"] > 8
    assert q["pitch_after_cents"] <= 0.75 * q["pitch_before_cents"]  # strength 0.6 for soul, ±10 left alone
    assert q["in_tune_frames"] >= 0.85
    # The singer's average lateness is found and kept as feel (VOCALS §3).
    true_late = 1000 * np.median([n.onset - n.grid for n in truth])
    assert abs(res.report["lateness_ms"] - true_late) < 12
    assert q["timing_median_ms"] < 30 and q["timing_p95_ms"] < 60
    assert np.isfinite(res.stereo).all() and np.abs(res.stereo).max() < 2


def test_quality_report_reads_like_checks(produced):
    res, _ = produced
    q = res.report["quality"]
    assert q["checks"] and all(c["level"] in ("ok", "warn", "bad") for c in q["checks"])
    assert not q["clipped"] and q["noise_raw_db"] < -55
    assert "space" in res.layers and "lead" in res.layers


def test_timing_rules():
    notes = [V.Note(i, i + 0.5, 60) for i in range(5)]
    onsets = [0.0, 1.02, 2.06, 3.12, 4.0]  # +0, +20, +60, +120, +0 ms
    corr, late, flagged = V.timing_targets(notes, onsets)
    assert late == pytest.approx(0.02)
    assert corr[0] == 0.0 and corr[1] == 0.0  # within ±25 ms of the average: left alone
    assert corr[2] == pytest.approx(0.02)  # 40 ms: pulled halfway
    assert corr[3] == pytest.approx(0.04) and flagged == [3]  # 100 ms: at most 40 ms, flagged


def test_hard_tuning_flattens_vibrato():
    tk, _ = _take(3, detune_cents=40, vibrato_cents=40, sibilants=0)
    notes = V.notes_in_seconds(LEAD, BPM, SECTIONS)
    rep = {}
    y, f0b, f0a = V.correct(tk.audio, notes, V.preset("arcade"), rep)
    t = np.arange(len(f0a)) * V.FRAME_MS / 1000
    n = notes[4]  # a 2-beat note, vibrato in full swing
    a, b = np.searchsorted(t, [n.start + 0.3, n.end - 0.1])
    before = V.cents(f0b[a:b][f0b[a:b] > 0], n.midi)
    after = V.cents(f0a[a:b][f0a[a:b] > 0], n.midi)
    assert np.std(after) < 0.25 * np.std(before)
    assert abs(np.median(after)) < 5


def test_comp_takes_the_better_take_per_line():
    good, _ = _take(4, detune_cents=10, timing_ms=10)
    bad, _ = _take(5, detune_cents=90, timing_ms=90)
    notes = V.notes_in_seconds(LEAD, BPM, SECTIONS)
    x, picks, _ = V.comp([bad, good], notes, length=len(good.audio) / V.SR)
    assert set(picks.values()) == {"t4"}
    x2, picks2, _ = V.comp([bad, good], notes, length=len(good.audio) / V.SR, choice={0: "t5"})
    assert picks2[0] == "t5"


def test_take_from_recording_subtracts_latency():
    x = np.zeros(48000, dtype=np.float32)
    tk = V.Take.from_recording(x, 48000, 10.0, 120.0)
    assert tk.t0 == pytest.approx(9.88) and len(tk.audio) == V.SR


def test_breaths_turned_down_not_deleted():
    lead = [(0, 1, 62), (1, 1, 64), (4, 1, 66), (5, 1, 64)]  # a 2-beat rest: a breath before the second phrase
    x, truth = S.sing(lead, BPM, pre_roll=0.0, breaths=True, sibilants=0, seed=6)
    f0, _ = V.track_f0(x)
    rep = {}
    y = V.tame_breaths(x, f0, -62, rep)
    assert rep["breaths_lowered"] >= 1
    i = int((truth[2].onset - 0.25) * V.SR)  # inside the breath before the second phrase
    ratio = np.abs(y[i - 500:i + 500]).mean() / np.abs(x[i - 500:i + 500]).mean()
    assert 0.3 < ratio < 0.8  # -4 to -6 dB, still there


def test_deesser_tames_s_sounds():
    x, _ = S.sing(LEAD, BPM, pre_roll=0.0, sibilants=1.0, seed=7)
    y, gr = V.deess(x, 6.0)
    band = lambda z: np.quantile(V._env(V._filt(z, V._sos("band", [5000, 10000], 2)), 5), 0.995)
    assert gr > 2 and band(y) < band(x) * 0.8


def test_sit_in_song_sets_level_and_makes_room():
    rng = np.random.default_rng(0)
    n = 6 * V.SR
    music = (rng.normal(0, 0.05, (2, n))).astype(np.float32)
    voc, _ = S.sing([(0, 2, 64), (2, 2, 67), (4, 2, 69)], BPM, pre_roll=0.0, seed=8)
    voc = np.stack([voc[:n], voc[:n]]) if len(voc) >= n else np.pad(np.stack([voc, voc]), ((0, 0), (0, n - len(voc))))
    f0, _ = V.track_f0(voc[0])
    env = V.voice_envelope(f0, n)
    p = V.preset("bright_pop")
    rep = {}
    mix, v2, _ = V.sit_in_song(music, voc, env, p, None, "duck", rep)
    sung = env > 0.5
    assert abs(V._lufs(v2[:, sung]) - (V._lufs(music[:, sung]) + p["level_lu"])) < 1.0
    band = lambda z: np.mean(V._filt(z[0], V._sos("band", [1000, 4000], 2))[sung] ** 2)
    assert band(mix - v2) < band(music) * 0.75  # the music dips at 1-4 kHz under the voice


def test_presets_cover_every_pack():
    from mouthmixer.arrange.styles import PACKS

    for k, pk in PACKS.items():
        assert pk.get("vocal_preset") in V.PRESETS, k
    for name in V.PRESETS:
        assert V.preset(name)["label"]


# --- lyrics ---------------------------------------------------------------------------------------

def _version():
    return {"tracks": [{"role": "lead", "notes": [[float(s), float(l), p, 90] for s, l, p in LEAD]}],
            "sections": SECTIONS, "bpm": BPM, "style": "test", "describe": "", "key": "D major"}


def test_lyrics_map_check_and_align():
    v = _version()
    smap = lyrics.syllable_map(v)
    assert [s["section"] for s in smap] == ["A", "A''"]
    assert smap[0]["lines"][0]["count"] == 4  # beats 4-7 in A; the long note at beat 8 starts A''
    opt = lyrics.from_text("Neon Rain", {"A": "walking under neon light", "A''": "neon rain, neon rain\nfalling down again"}, v)
    assert opt["check"]["score"] > 0
    ev = lyrics.align(opt, smap)
    assert len(ev) >= sum(ln["count"] for s in smap for ln in s["lines"])
    assert ev[0]["text"] and ev[0]["section"] == "A"


def test_lyrics_write_parses_and_orders(monkeypatch):
    """lyrics.write with a stand-in client: sections come back in melody order and get checked."""
    import anthropic

    v = _version()

    class Resp:
        stop_reason = "end_turn"

        def __init__(self, parsed):
            self.parsed_output = parsed

    class Fake:
        def __init__(self, **kw):
            self.beta = self
            self.messages = self

        def parse(self, **kw):
            assert kw["model"] == "claude-opus-5-5" and kw["thinking"] == {"type": "adaptive"}
            Opts = kw["output_format"]
            return Resp(Opts.model_validate({"options": [{"title": "Neon Rain", "idea": "x", "sections": [
                {"name": "A''", "lines": [{"text": "neon rain, neon rain"}, {"text": "falling down again"}]},
                {"name": "A", "lines": [{"text": "walking under neon light"}]}]}]}))

    monkeypatch.setattr(anthropic, "Anthropic", Fake)
    out = lyrics.write("rainy city", v, api_key="test")
    assert [s["name"] for s in out[0]["sections"]] == ["A", "A''"]
    assert "check" in out[0]


# --- catalog --------------------------------------------------------------------------------------

def test_suggestions_follow_the_vibe():
    parts = [{"kind": "orig:lead", "role": "lead", "instrument": "flute"},
             {"kind": "orig:drums", "role": "drums", "instrument": "kit:standard"}]
    dark = catalog.suggest(parts, "city_pop_day", "dark", limit=10)
    cozy = catalog.suggest(parts, "city_pop_day", "cozy", limit=10)
    assert dark and all(s["why"] for s in dark)
    assert [s["id"] for s in dark] != [s["id"] for s in cozy]
    top_dark = catalog.PARTS[dark[0]["id"]]
    assert "dark" in top_dark["vibes"] or "nothing low" in dark[0]["why"]


def test_lines_are_singable_phrases():
    """No one-note lines, nothing over 14 notes, splits where a singer would breathe."""
    ode = [(float(i), 1.0, 60) for i in range(12)] + [(12, 1.5, 62), (13.5, 0.5, 60), (14, 2, 60)]
    runs = [(i * 0.5, 0.5, 60) for i in range(30)]
    gaps = [(0, 1, 60), (1, 1, 62), (2, 1, 64), (4, 1, 65), (8, 1, 67), (9, 1, 65), (10, 2, 64)]
    for mel in (ode, runs, gaps):
        lines = lyrics.phrases(mel)
        assert sum(len(x) for x in lines) == len(mel)
        assert all(3 <= len(x) <= 14 for x in lines), [len(x) for x in lines]
    # Vocals number their lines the same way.
    notes = V.notes_in_seconds(LEAD, BPM, SECTIONS)
    smap = lyrics.syllable_map(_version())
    assert len({n.line for n in notes}) == sum(len(s["lines"]) for s in smap)


def test_swapping_a_sound_keeps_chords_clear_of_the_melody():
    from mouthmixer.arrange.mixer import clear_of_melody

    melody = [(0.0, 2.0, 71, 90)]  # B4 held
    chords = [(0.0, 2.0, 60, 70), (0.0, 2.0, 72, 70), (0.0, 2.0, 70, 70), (0.0, 2.0, 64, 70)]
    # C4: melody a major 7th above (fine). C5 and Bb4: a half step from the melody (must move or go).
    out = clear_of_melody(chords, melody, "piano")
    assert (0.0, 2.0, 64, 70) in out and (0.0, 2.0, 60, 70) in out
    assert all(not (abs(71 - p) == 1 or (71 > p and (71 - p) % 12 == 1)) for _, _, p, _ in out)
    assert len(out) >= 3  # moved an octave where possible, not just dropped


# --- PSOLA tuning, the raw voice and the processing switches (VOCALS §13, measured on the user's takes) ---

def _level_jumps(x, f0):
    """Abrupt level jumps (> 6 dB between 5 ms frames) inside sung, loud frames."""
    hop = int(V.FRAME_MS / 1000 * V.SR)
    n = min(len(x) // hop, len(f0))
    db = 20 * np.log10(np.sqrt(np.mean(x[:n * hop].reshape(n, hop).astype(np.float64) ** 2, 1)) + 1e-9)
    sel = (f0[:n] > 0) & (db > db.max() - 30)
    return int(((np.abs(np.diff(db)) > 6) & sel[1:] & sel[:-1]).sum())


def test_psola_leaves_a_voice_alone_when_nothing_moves():
    tk, _ = _take(5, sibilants=0.4)
    f0, _ = V.track_f0(tk.audio, fast=False)
    same = V.psola(tk.audio, f0, np.ones(len(f0)))
    assert np.array_equal(same, tk.audio.astype(np.float32))
    forced = V.psola(tk.audio, f0, np.ones(len(f0)), min_cents=-1)  # rebuilt grain by grain, still the same
    assert np.abs(forced - tk.audio).max() < 0.01


def test_psola_moves_pitch_by_the_ratio():
    tk, _ = _take(6, vibrato_cents=10, sibilants=0)
    f0, _ = V.track_f0(tk.audio, fast=False)
    y = V.psola(tk.audio, f0, np.full(len(f0), 2 ** (50 / 1200)))
    f1, _ = V.track_f0(y, fast=False)
    both = (f0 > 0) & (f1 > 0)
    moved = 1200 * np.log2(f1[both] / f0[both])
    assert abs(np.median(moved) - 50) < 6


def test_tuning_off_returns_the_recording_untouched():
    tk, _ = _take(7)
    rep = {}
    y, f0b, f0a = V.tune_to_key(tk.audio, 2, "major", dict(V.preset("soul"), strength=0.0), [], rep)
    assert np.array_equal(y, tk.audio.astype(np.float32)) and rep["tuned_frames_moved_cents"] == 0
    assert np.array_equal(f0b, f0a)


def test_key_tuning_is_not_choppy():
    """The user's tuned takes doubled their level jumps with WORLD; PSOLA keeps them at the take's own."""
    tk, _ = _take(8, detune_cents=40, vibrato_cents=35)
    rep = {}
    y, f0b, f0a = V.tune_to_key(tk.audio, 2, "major", V.preset("soul"), [], rep)
    assert rep["tuned_frames_moved_cents"] > 5
    assert _level_jumps(y, f0b) <= _level_jumps(tk.audio, f0b) * 1.2 + 5
    v = (f0a > 0)
    off = np.abs(V._run_median(np.where(v, 69 + 12 * np.log2(np.maximum(f0a, 1) / 440), np.nan), v, 40)[v] -
                 V._scale_target(V._run_median(np.where(v, 69 + 12 * np.log2(np.maximum(f0a, 1) / 440), np.nan), v, 40)[v], 2, "major"))
    assert np.mean(off * 100 <= 25) > 0.8


def test_processing_switches_map_to_the_chain():
    p = V.tweak_preset(V.preset("rock"), {"cleanup": "off", "denoise": "off", "breaths": "off", "deess": "off",
                                          "compress": "light", "eq": "off"})
    assert not p["highpass"] and p["denoise"] == 0 and not p["breaths"] and p["deess_db"] == 0
    assert p["compress"] == 0.5 and p["presence_db"] == 0 and p["air_db"] == 0 and p["drive_bite"] == 0
    assert V.tweak_preset(V.preset("soul"), {"process": "raw"})["raw"]
    assert V.clean_tweaks({"denoise": "loud", "process": "raw"}) == {"process": "raw"}  # unknown option dropped


def test_raw_voice_is_exactly_the_takes():
    x, _ = S.sing(LEAD, BPM, pre_roll=1.0, start=4 * 60 / BPM, seed=9)
    tk = V.Take(x, 4 * 60 / BPM - 1.0, "raw")
    length = tk.end + 0.5
    res = V.produce_free([tk], BPM, SECTIONS, 2, "major", "rock", length, tweaks={"process": "raw"},
                         character="female")
    raw, _ = V.comp_sections([tk], [(s["name"], s["start"] * 4 * 0.6, (s["start"] + s["bars"]) * 4 * 0.6)
                                    for s in SECTIONS], length)
    assert set(res.layers) == {"lead"}
    assert np.allclose(res.layers["lead"][0] * np.sqrt(2), raw, atol=1e-6)
    assert res.report["raw"] and res.report["character"] == "natural"
    assert [s["step"] for s in res.report["steps"]] == ["Raw voice"]


def test_every_step_that_ran_is_listed():
    x, _ = S.sing(LEAD, BPM, pre_roll=1.0, start=4 * 60 / BPM, seed=10, noise_db=-50)
    tk = V.Take(x, 4 * 60 / BPM - 1.0, "full")
    res = V.produce_free([tk], BPM, SECTIONS, 2, "major", "soul", tk.end + 0.5)
    names = [s["step"] for s in res.report["steps"]]
    for want in ("Low cut", "Noise reduction", "Tuning to the key", "Compression", "Reverb"):
        assert want in names, names
    off = V.produce_free([tk], BPM, SECTIONS, 2, "major", "soul", tk.end + 0.5,
                         tweaks={"denoise": "off", "compress": "off", "tuning": "off"})
    names = [s["step"] for s in off.report["steps"]]
    assert "Noise reduction" not in names and "Compression" not in names and "Tuning to the key" not in names


def test_pitch_and_breath_tweaks_skip_world():
    tk, _ = _take(11, vibrato_cents=10, sibilants=0)
    f0, _ = V.track_f0(tk.audio, fast=False)
    rep = {}
    y, layer = V.apply_character(tk.audio, f0, "natural", rep, tweaks={"pitch": 7, "breath": 30}, scale=(2, "major"))
    voice = next(s["detail"] for s in rep["steps"] if s["step"] == "Voice")
    assert "PSOLA" in voice and "breath added" in voice and "WORLD" not in voice
    f1, _ = V.track_f0(y, fast=False)
    both = (f0 > 0) & (f1 > 0)
    assert abs(np.median(1200 * np.log2(f1[both] / f0[both])) - 1200) < 30  # 7 notes of the key = an octave
    rep2 = {}
    V.apply_character(tk.audio, f0, "natural", rep2, tweaks={"tone": 10}, scale=(2, "major"))
    assert "WORLD" in next(s["detail"] for s in rep2["steps"] if s["step"] == "Voice")


def test_tone_match_lifts_a_dark_take_toward_the_references():
    from mouthmixer.arrange.vocals import REF_TONE

    tk, _ = _take(12, sibilants=0.1)
    dark = V._filt(tk.audio, V._sos("low", 5000, 4))
    notes = V.notes_in_seconds(LEAD, BPM, SECTIONS)
    f0, _ = V.track_f0(dark, fast=True)
    before = V.vocal_tone(dark)
    rep = {}
    layers = V.chain(dark, notes, f0, V.preset("soul"), BPM, 2, "major", set(), rep)
    assert rep["tone_match"]["air_db"] == 8.0  # capped
    after = V.vocal_tone(layers["lead"][0])
    assert after["10-16k"] > before["10-16k"] + 6 and after["10-16k"] <= REF_TONE["10-16k"] + 3
    rep2 = {}
    V.chain(dark, notes, f0, V.tweak_preset(V.preset("soul"), {"tonematch": "off"}), BPM, 2, "major", set(), rep2)
    assert "tone_match" not in rep2
