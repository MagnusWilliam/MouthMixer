"""The reference-song analyser on a generated song whose tempo, key, chords and sections are known."""

import numpy as np

from mouthmixer.reference import analyse as A

SR = A.SR


def _tone(f, n, amp):
    t = np.arange(n) / SR
    return amp * sum(np.sin(2 * np.pi * f * k * t) / k for k in (1, 2, 3)) * np.exp(-t * 1.5)


def _song(bpm=120.0):
    """8 bars quiet (I-vi in C, soft hats), 8 bars loud (IV-V, kick/snare/hats), 8 bars quiet again."""
    spb = 60 / bpm
    bars = 24
    n = int(bars * 4 * spb * SR) + SR
    x = np.zeros(n)
    rng = np.random.default_rng(0)
    chords = {"I": [60, 64, 67], "vi": [57, 60, 64], "IV": [53, 57, 60], "V": [55, 59, 62]}
    for bar in range(bars):
        loud = 8 <= bar < 16
        prog = ["IV", "V"] if loud else ["I", "vi"]
        for half in range(2):
            a = int((bar * 4 + half * 2) * spb * SR)
            L = int(2 * spb * SR)
            for m in chords[prog[half]]:
                x[a:a + L] += _tone(440 * 2 ** ((m - 69) / 12), L, 0.08 if loud else 0.05)
            x[a:a + L] += _tone(440 * 2 ** ((chords[prog[half]][0] - 12 - 69) / 12), L, 0.12 if loud else 0.06)
        for beat in range(4):
            b = int((bar * 4 + beat) * spb * SR)
            k = int(0.12 * SR)
            if loud and beat in (0, 2) or beat == 0:
                x[b:b + k] += 0.6 * np.sin(2 * np.pi * 55 * np.arange(k) / SR) * np.exp(-np.arange(k) / SR * 30)
            if loud and beat in (1, 3):
                x[b:b + k] += 0.3 * rng.normal(0, 1, k) * np.exp(-np.arange(k) / SR * 25)
            for e in (0, 0.5):
                h = b + int(e * spb * SR)
                x[h:h + 800] += (0.08 if loud else 0.03) * rng.normal(0, 1, 800) * np.exp(-np.arange(800) / 150)
    return np.stack([x, x * 0.9]).astype(np.float32)


def test_analyser_reads_a_known_song(tmp_path, monkeypatch):
    y = _song()
    import soundfile as sf

    f = tmp_path / "known.wav"
    sf.write(str(f), y.T, SR)
    r = A.run(f, tmp_path / "out")[0]
    assert abs(r["bpm"] - 120) < 3 or abs(r["bpm"] - 60) < 2  # half-time readings are reported, not hidden
    assert r["key"].startswith("C ") or r["key"].startswith("A ")  # C major / its relative minor
    assert r["bars"] >= 20
    # the loud middle shows up as its own, louder section
    starts = [s["bar"] for s in r["sections"]]
    assert any(abs(b - 8) <= 1 for b in starts) and any(abs(b - 16) <= 1 for b in starts), starts
    loud = max(r["sections"], key=lambda s: s["lufs"] or -99)
    assert 7 <= loud["bar"] <= 9
    names = [c["roman"] for c in r["chords"]]
    assert {"I", "vi", "IV", "V"} & set(names)
    assert (tmp_path / "out" / "known" / "summary.md").exists()


def test_stems_are_read_when_present(tmp_path):
    import soundfile as sf

    y = _song()
    f = tmp_path / "s.wav"
    sf.write(str(f), y.T, SR)
    stem_dir = tmp_path / "out" / "s" / "stems"
    stem_dir.mkdir(parents=True)
    sf.write(str(stem_dir / "drums.wav"), (y * 0.5).T, SR)
    sf.write(str(stem_dir / "other.wav"), (y * 0.5).T, SR)
    r = A.run(f, tmp_path / "out")[0]
    rows = r["stems"]["levels_by_section"]
    assert rows and all(abs(row["drums"] + 6) < 1.5 for row in rows if row["drums"] is not None)
    assert "kick" in r["stems"]["drums"]


def test_drum_patterns_from_a_known_beat():
    """Kick on 1 and 3, snare on 2 and 4, hats on 8ths, with spill between bands as in real stems."""
    bpm, bars = 100.0, 8
    spb = 60 / bpm
    n = int(bars * 4 * spb * SR) + SR
    x = np.zeros(n)
    rng = np.random.default_rng(1)
    t = np.arange(int(0.2 * SR)) / SR
    for beat in range(bars * 4):
        b = int(beat * spb * SR)
        if beat % 2 == 0:
            k = 0.8 * np.sin(2 * np.pi * (50 + 60 * np.exp(-t * 40)) * t) * np.exp(-t * 18)
            x[b:b + len(k)] += k + 0.02 * rng.normal(0, 1, len(k)) * np.exp(-t * 60)  # a little click
        else:
            s = (0.4 * rng.normal(0, 1, len(t)) + 0.3 * np.sin(2 * np.pi * 200 * t)) * np.exp(-t * 20)
            x[b:b + len(s)] += s
        for e in (0, 0.5):
            h = b + int(e * spb * SR)
            hh = 0.1 * rng.normal(0, 1, 1500) * np.exp(-np.arange(1500) / 300)
            x[h:h + 1500] += A.np.convolve(hh, [1, -1], mode="same")
    y = np.stack([x, x]).astype(np.float32)
    beats = np.arange(bars * 4 + 1) * spb
    d = A.drum_facts(y, beats, 0)
    assert d["kick"]["common_bars"][0]["pattern"] == "x.......x......."
    assert d["snare"]["common_bars"][0]["pattern"] == "....x.......x..."
    assert d["hats"]["common_bars"][0]["pattern"] == "x.x.x.x.x.x.x.x."
