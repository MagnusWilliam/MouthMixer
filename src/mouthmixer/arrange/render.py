"""Rendering and mixing (PLAN.md §11.1, §11.3): instruments from GeneralUser GS through TinySoundFont,
effects through pedalboard, then a mix bus and mastering to a consistent loudness.

Mix rules applied here (MUSIC_KNOWLEDGE §7): every part high-passed except kick and bass; bass ducks on
each kick (sidechain); shared reverb and delay buses instead of one reverb per part; lead balanced first;
lows kept mono; master to about -14 LUFS with the peak under -1 dBFS.
"""

from __future__ import annotations

import os
from pathlib import Path

import numpy as np

from .arranger import Song, Track
from .styles import DRUM, INSTRUMENTS, KITS, PACKS

SR = 44100


def soundfont_path() -> Path:
    env = os.environ.get("MOUTHMIXER_SOUNDFONT")
    if env:
        return Path(env)
    return Path(__file__).resolve().parents[3] / "assets" / "soundfonts" / "GeneralUser-GS.sf2"


_SYNTH = None


def _synth():
    global _SYNTH
    if _SYNTH is None:
        import tinysoundfont

        s = tinysoundfont.Synth(samplerate=SR, gain=-3)
        sfid = s.sfload(str(soundfont_path()))
        _SYNTH = (s, sfid)
    return _SYNTH


# Played brass and saxes (docs/ARRANGING.md "Making brass sound played"): a scoop into phrase starts,
# vibrato that comes in partway through long notes, phrases shaped louder into the top note and softer
# at the end, and single lines doubled by a second player a few cents and ms away. Values are [U].
PLAYED = {"trumpet", "trombone", "muted_trumpet", "french_horn", "brass_section", "brass_section_2", "tuba",
          "soprano_sax", "alto_sax", "tenor_sax", "baritone_sax"}
DOUBLED = {"trumpet", "trombone", "muted_trumpet", "soprano_sax", "alto_sax", "tenor_sax", "baritone_sax"}
BEND_CENTER, BEND_PER_CENT = 8192, 8192 / 200  # default bend range: 2 semitones = 200 cents


def _phrase_velocities(notes: list, spb: float) -> list[int]:
    """Velocities shaped per phrase (a gap of half a beat starts a new one): the first note and the top
    note leaned on, the last one lighter unless it's held."""
    out = [int(n[3]) for n in notes]
    order = sorted(range(len(notes)), key=lambda i: notes[i][0])
    phrase: list[int] = []

    def close(ph):
        if not ph:
            return
        top = max(ph, key=lambda i: notes[i][2])
        out[ph[0]] += 6
        out[top] += 8
        if len(ph) > 2 and notes[ph[-1]][1] < 1.0:
            out[ph[-1]] -= 8

    for k, i in enumerate(order):
        if phrase and notes[i][0] - (notes[phrase[-1]][0] + notes[phrase[-1]][1]) > 0.5:
            close(phrase)
            phrase = []
        phrase.append(i)
    close(phrase)
    return [int(np.clip(v, 1, 127)) for v in out]


def _bends(notes: list, spb: float, rng) -> list[tuple[float, int]]:
    """Pitch-bend moves (time, cents) for a played line: a 40-cent scoop over 60 ms into each phrase
    start, and on notes of half a second or more a 5.4 Hz vibrato that starts after a quarter of the note
    and grows to about 18 cents."""
    out: list[tuple[float, int]] = []
    starts = sorted(notes, key=lambda n: n[0])
    prev_end = -1e9
    for s, l, p, v in starts:
        t0, dur = s * spb, l * spb
        if s - prev_end > 0.4:  # a phrase start: scoop up into it
            for k in range(7):
                out.append((t0 + k * 0.01, int(-40 * (1 - k / 6) ** 2)))
        else:
            out.append((t0, 0))
        if dur >= 0.5:
            a, b = t0 + min(0.3, 0.25 * dur), t0 + dur - 0.03
            rate, ph = 5.4 + rng.normal(0, 0.2), rng.uniform(0, 6.28)
            t = a
            while t < b:
                depth = 18 * min(1.0, (t - a) / 0.25)
                out.append((t, int(depth * np.sin(ph + 2 * np.pi * rate * (t - a)))))
                t += 0.015
            out.append((b, 0))
        prev_end = max(prev_end, s + l)
    return out


def render_track(track: Track, bpm: float, total_sec: float, rng, _double: bool = False) -> np.ndarray:
    """One part -> stereo float32 array (2, n)."""
    synth, sfid = _synth()
    spb = 60.0 / bpm
    is_drums = track.instrument.startswith("kit:")
    played = not is_drums and track.instrument in PLAYED
    if is_drums:
        synth.program_select(9, sfid, 128, KITS[track.instrument[4:]], True)
        chan = 9
    else:
        bank, prog = INSTRUMENTS[track.instrument][:2]
        chan = 1 if _double else 0
        synth.program_select(chan, sfid, bank, prog)
    jitter = 0.003 if is_drums else 0.007
    vels = _phrase_velocities(track.notes, spb) if played else [n[3] for n in track.notes]
    offset = 0.014 if _double else 0.0  # the second player, a little behind
    events = []
    for (s, l, p, v), vv in zip(track.notes, vels):
        t0 = max(0.0, s * spb + offset + rng.normal(0, jitter))
        vel = int(np.clip(vv + rng.normal(0, 4) - (8 if _double else 0), 1, 127))
        events.append((t0, 1, int(p), vel))
        events.append((t0 + max(0.05, l * spb), 0, int(p), 0))
    if played:
        detune = 7 if _double else 0
        for t, cents in _bends(track.notes, spb, rng):
            events.append((t + offset, 2, int(BEND_CENTER + (cents + detune) * BEND_PER_CENT), 0))
    events.sort(key=lambda e: (e[0], e[1]))  # note-offs before note-ons at the same time, bends after
    n_total = int(total_sec * SR)
    out = np.zeros((n_total, 2), dtype=np.float32)
    pos = 0
    for t, on, p, vel in events:
        target = min(n_total, int(t * SR))
        if target > pos:
            out[pos:target] = np.frombuffer(synth.generate(target - pos), dtype=np.float32).reshape(-1, 2)
            pos = target
        if on == 2:
            synth.pitchbend(chan, int(np.clip(p, 0, 16383)))
        elif on:
            synth.noteon(chan, p, vel)
        else:
            synth.noteoff(chan, p)
    if pos < n_total:
        out[pos:] = np.frombuffer(synth.generate(n_total - pos), dtype=np.float32).reshape(-1, 2)
    synth.notes_off()
    if not is_drums:
        synth.pitchbend(chan, BEND_CENTER)
    synth.generate(SR // 2)  # let the synth fall silent before the next part
    gain = 1.0 if is_drums else INSTRUMENTS[track.instrument][5]
    out = (out.T * gain).astype(np.float32)
    if played and not _double and track.instrument in DOUBLED and not _chordal(track.notes):
        # a single line gets a second player: same part, a few cents sharp and 14 ms late, the two
        # spread a little left and right (a section, not one sample)
        dbl = render_track(track, bpm, total_sec, rng, _double=True)
        main_, second = out.mean(axis=0), dbl.mean(axis=0) * 10 ** (-5 / 20)
        out = np.stack([main_ * 0.9 + second * 0.45, main_ * 0.62 + second * 0.82]).astype(np.float32)
    return out


def _chordal(notes: list) -> bool:
    """Mostly chords (several notes starting together), like stabs: those aren't doubled."""
    if not notes:
        return False
    starts = [round(n[0], 3) for n in notes]
    return len(set(starts)) < 0.75 * len(starts)


def _pan(x: np.ndarray, pan: float) -> np.ndarray:
    a = (pan + 1) * np.pi / 4
    mono = x.mean(axis=0)
    width = x - mono
    return np.stack([mono * np.cos(a) * 1.414 + width[0], mono * np.sin(a) * 1.414 + width[1]]).astype(np.float32)


def _sidechain(n: int, kick_times: list[float], depth_db: float = 5.0) -> np.ndarray:
    """Gain curve that dips on every kick (5 ms attack, 140 ms release)."""
    g = np.ones(n, dtype=np.float32)
    dip = 10 ** (-depth_db / 20)
    a, r = int(0.005 * SR), int(0.14 * SR)
    shape = np.concatenate([np.linspace(1, dip, a), dip + (1 - dip) * (1 - np.exp(-np.linspace(0, 5, r)))])
    for t in kick_times:
        i = int(t * SR)
        seg = shape[: max(0, min(len(shape), n - i))]
        g[i : i + len(seg)] = np.minimum(g[i : i + len(seg)], seg)
    return g


def _vinyl(n: int, rng) -> np.ndarray:
    """Soft vinyl crackle for the night style (a texture, very low)."""
    x = rng.normal(0, 0.0015, n).astype(np.float32)
    clicks = rng.random(n) < 2.5 / SR
    x[clicks] += rng.uniform(-0.05, 0.05, clicks.sum())
    return np.stack([x, np.roll(x, 37)])


def _fx(track: Track, pack: dict, bpm: float):
    from pedalboard import Chorus, Compressor, Distortion, Gain, HighpassFilter, LowpassFilter, Pedalboard, PeakFilter

    role = track.role
    fx = []
    if role == "bass":
        fx += [LowpassFilter(5000), Compressor(threshold_db=-20, ratio=4, attack_ms=5, release_ms=120),
               Distortion(drive_db=6 if pack.get("drive") else 3), Gain(-4)]  # harmonics so phones hear it
    elif role == "drums":
        fx += [Compressor(threshold_db=-14, ratio=3, attack_ms=8, release_ms=100)]
    elif role == "timpani":
        fx += [HighpassFilter(40)]
    else:
        hp = {"lead": 160, "comp": 140, "pad": 220, "arp": 300, "counter": 180}.get(role, 150)
        fx += [HighpassFilter(hp), Compressor(threshold_db=-18, ratio=2.5, attack_ms=12, release_ms=150)]
        # Carve room for the melody (docs/ARRANGING.md R2.3): harmony layers dip where the ear listens.
        if role in ("comp", "pad", "arp", "riff", "counter"):
            fx += [PeakFilter(cutoff_frequency_hz=2500, gain_db=-3.0, q=0.7)]
        if pack.get("chorus") and role in ("comp", "pad"):
            fx += [Chorus(rate_hz=0.6, depth=0.2, mix=0.35)]
        if pack.get("drive") and role == "lead" and "guitar" in track.instrument:
            fx += [Distortion(drive_db=8), Gain(-6)]
        if track.instrument in PLAYED:
            # brass and saxes: less boxy midrange, a touch of bite and air
            from pedalboard import HighShelfFilter

            fx += [PeakFilter(cutoff_frequency_hz=380, gain_db=-2.5, q=1.0), Distortion(drive_db=3), Gain(-2),
                   HighShelfFilter(cutoff_frequency_hz=7000, gain_db=2.0, q=0.7)]
    return Pedalboard(fx)


LEVEL = {"lead": -6.0, "vocal": -5.0, "comp": -13.0, "pad": -17.0, "bass": -9.0, "arp": -17.0, "counter": -15.0,
         "riff": -13.5, "drums": -8.0, "perc": -16.0, "timpani": -12.0, "fx": -22.0}
SENDS = {"lead": 0.22, "comp": 0.2, "pad": 0.45, "arp": 0.35, "counter": 0.3, "riff": 0.18, "drums": 0.06,
         "perc": 0.15, "timpani": 0.25, "bass": 0.0, "fx": 0.3}


def song_length(song: Song) -> tuple[float, int]:
    total_sec = song.bars * 4 * 60.0 / song.bpm + 3.0
    return total_sec, int(total_sec * SR)


def kick_times(song: Song) -> list[float]:
    spb = 60.0 / song.bpm
    return [s * spb for t in song.tracks if t.role == "drums" for s, _, p, _ in t.notes
            if p in (DRUM["kick"], DRUM["concert_bd"])]


def render_stem(t: Track, song: Song, rng=None, duck: np.ndarray | None = None, gain_db: float = 0.0) -> np.ndarray:
    """One part as a finished stem (2, n): instrument, effects, level, sidechain, pan, and its own share of
    the style's reverb and delay. Stems add up to the pre-master mix, so the mixer can switch parts on
    and off live and the saved mix sounds the same."""
    from pedalboard import Delay, HighpassFilter, Pedalboard, Reverb

    rng = rng or np.random.default_rng(song.seed)
    pack = PACKS[song.pack]
    total_sec, n = song_length(song)
    if t.instrument.startswith("fx:"):
        x = texture(t.instrument[3:], n, rng)
    else:
        x = render_track(t, song.bpm, total_sec, rng)
        x = _fx(t, pack, song.bpm)(x, SR)[:, :n]
    if x.shape[1] < n:
        x = np.pad(x, ((0, 0), (0, n - x.shape[1])))
    active = np.abs(x).max(axis=0) > 1e-4
    rms = float(np.sqrt(np.mean(x[:, active] ** 2))) if active.any() else 0.0
    if rms > 0:
        x *= 10 ** ((LEVEL.get(t.role, -14) + gain_db) / 20) / rms * 0.25
    if duck is not None and t.role in ("bass", "pad"):
        x *= duck
    x = _pan(x, t.pan)
    send = SENDS.get(t.role, 0.2)
    if send > 0:
        rev = Pedalboard([HighpassFilter(250), Reverb(room_size=pack["reverb"], damping=0.5, wet_level=1.0,
                                                      dry_level=0.0, width=1.0)])
        x = x + 0.55 * rev(x * send, SR)
    if t.role == "lead" and pack.get("delay"):
        dly = Pedalboard([HighpassFilter(300), Delay(delay_seconds=0.75 * 60.0 / song.bpm, feedback=0.3, mix=1.0)])
        x = x + 0.55 * dly(x * pack["delay"], SR)
    return x.astype(np.float32)


def master(x: np.ndarray, target_lufs: float = -14.0) -> np.ndarray:
    """Mono lows, glue compression, loudness to target, peak limit, fade-out tail."""
    from pedalboard import Compressor, Pedalboard
    from scipy.signal import butter, sosfilt

    sos = butter(2, 120, btype="low", fs=SR, output="sos")
    low = sosfilt(sos, x, axis=1)
    out = x - low + low.mean(axis=0, keepdims=True)  # MUSIC_KNOWLEDGE X9
    out = Pedalboard([Compressor(threshold_db=-14, ratio=2, attack_ms=15, release_ms=200)])(out.astype(np.float32), SR)
    out = loudness_normalise(out, target_lufs)
    out = limit(out, ceiling_db=-1.0)
    fade = int(1.5 * SR)
    out[:, -fade:] *= np.linspace(1, 0, fade)
    return out.astype(np.float32)


def mix(song: Song, rng=None) -> tuple[np.ndarray, dict]:
    """Render, process and master the song. Returns (stereo mix (2, n), stems by role)."""
    rng = rng or np.random.default_rng(song.seed)
    pack = PACKS[song.pack]
    _, n = song_length(song)
    duck = _sidechain(n, kick_times(song))
    out = np.zeros((2, n), dtype=np.float32)
    stems: dict[str, np.ndarray] = {}
    for t in song.tracks:
        x = render_stem(t, song, rng, duck)
        out += x
        stems[t.role] = stems.get(t.role, 0) + x
    if pack.get("vinyl"):
        out += _vinyl(n, rng)
    return master(out), stems


def texture(name: str, n: int, rng) -> np.ndarray:
    """Generated ambience textures (no samples needed): vinyl crackle, rain, wind, tape hiss, riser."""
    from scipy.signal import butter, sosfilt

    t = np.arange(n) / SR
    if name == "vinyl":
        return _vinyl(n, rng) * 4
    if name == "rain":
        x = rng.normal(0, 1, (2, n))
        x = sosfilt(butter(2, [800, 9000], btype="band", fs=SR, output="sos"), x, axis=1)
        drops = (rng.random((2, n)) < 40 / SR) * rng.uniform(0.2, 1.0, (2, n))
        return (0.05 * x + sosfilt(butter(2, 3000, btype="high", fs=SR, output="sos"), drops, axis=1)).astype(np.float32)
    if name == "wind":
        x = rng.normal(0, 1, (2, n))
        lfo = 0.6 + 0.4 * np.sin(2 * np.pi * 0.07 * t + rng.uniform(0, 6))
        return (sosfilt(butter(2, [200, 1200], btype="band", fs=SR, output="sos"), x, axis=1) * lfo * 0.3).astype(np.float32)
    if name == "tape":
        return (sosfilt(butter(1, 4000, btype="high", fs=SR, output="sos"), rng.normal(0, 0.01, (2, n)), axis=1)).astype(np.float32)
    return np.zeros((2, n), dtype=np.float32)


def limit(x: np.ndarray, ceiling_db: float = -1.0, lookahead_ms: float = 5.0, release_ms: float = 80.0) -> np.ndarray:
    """A look-ahead peak limiter that only turns peaks down (pedalboard's Limiter also raises the level
    to 0 dBFS and compresses everything above -10 dB, which is not what a game mix wants)."""
    from scipy.ndimage import minimum_filter1d
    from scipy.signal import lfilter

    ceiling = 10 ** (ceiling_db / 20)
    peak = np.abs(x).max(axis=0)
    g = np.minimum(1.0, ceiling / np.maximum(peak, 1e-9))
    look = max(1, int(lookahead_ms / 1000 * SR))
    g = minimum_filter1d(g, size=2 * look + 1)
    # Instant attack (with look-ahead), smooth exponential release: the causal one-pole smoothing of the
    # gain only ever lags behind, so taking the minimum keeps every peak under the ceiling.
    a = np.exp(-1.0 / (release_ms / 1000 * SR))
    smooth, _ = lfilter([1 - a], [1, -a], g, zi=[a])
    g = np.minimum(g, smooth)
    from scipy.ndimage import uniform_filter1d

    g = uniform_filter1d(g, size=look)  # soften the attack edge
    y = x * g
    return np.clip(y, -ceiling, ceiling).astype(np.float32)


def loudness_normalise(x: np.ndarray, target: float) -> np.ndarray:
    import pyloudnorm as pyln

    meter = pyln.Meter(SR)
    lufs = meter.integrated_loudness(x.T)
    if not np.isfinite(lufs):
        return x
    return x * 10 ** ((target - lufs) / 20)


def write_midi(song: Song, path: Path) -> None:
    import pretty_midi

    pm = pretty_midi.PrettyMIDI(initial_tempo=song.bpm)
    spb = 60.0 / song.bpm
    for t in song.tracks:
        drums = t.instrument.startswith("kit:")
        prog = 0 if drums else INSTRUMENTS[t.instrument][1]
        inst = pretty_midi.Instrument(program=prog, is_drum=drums, name=f"{t.name} ({t.instrument})")
        for s, l, p, v in t.notes:
            inst.notes.append(pretty_midi.Note(int(v), int(p), s * spb, (s + l) * spb))
        pm.instruments.append(inst)
    pm.write(str(path))


def write_audio(x: np.ndarray, path: Path) -> None:
    import soundfile as sf

    # Written in chunks: libsndfile's Vorbis encoder can crash on one long write.
    # Vorbis at libsndfile's default is ~130 kbps, which dulls cymbals and the top of a voice; 0.2 is ~280 kbps.
    fmt = ("OGG", "VORBIS") if path.suffix == ".ogg" else ("WAV", "PCM_16")
    kw = {"compression_level": 0.2} if fmt[0] == "OGG" else {}
    with sf.SoundFile(str(path), "w", SR, x.shape[0], format=fmt[0], subtype=fmt[1], **kw) as f:
        for i in range(0, x.shape[1], 32768):
            f.write(np.ascontiguousarray(x[:, i : i + 32768].T))
