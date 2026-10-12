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


def render_track(track: Track, bpm: float, total_sec: float, rng) -> np.ndarray:
    """One part -> stereo float32 array (2, n)."""
    synth, sfid = _synth()
    spb = 60.0 / bpm
    is_drums = track.instrument.startswith("kit:")
    if is_drums:
        synth.program_select(9, sfid, 128, KITS[track.instrument[4:]], True)
        chan = 9
    else:
        bank, prog = INSTRUMENTS[track.instrument][:2]
        synth.program_select(0, sfid, bank, prog)
        chan = 0
    jitter = 0.003 if is_drums else 0.007
    events = []
    for s, l, p, v in track.notes:
        t0 = max(0.0, s * spb + rng.normal(0, jitter))
        vel = int(np.clip(v + rng.normal(0, 4), 1, 127))
        events.append((t0, 1, int(p), vel))
        events.append((t0 + max(0.05, l * spb), 0, int(p), 0))
    events.sort(key=lambda e: (e[0], e[1]))  # note-offs before note-ons at the same time
    n_total = int(total_sec * SR)
    out = np.zeros((n_total, 2), dtype=np.float32)
    pos = 0
    for t, on, p, vel in events:
        target = min(n_total, int(t * SR))
        if target > pos:
            out[pos:target] = np.frombuffer(synth.generate(target - pos), dtype=np.float32).reshape(-1, 2)
            pos = target
        if on:
            synth.noteon(chan, p, vel)
        else:
            synth.noteoff(chan, p)
    if pos < n_total:
        out[pos:] = np.frombuffer(synth.generate(n_total - pos), dtype=np.float32).reshape(-1, 2)
    synth.notes_off()
    synth.generate(SR // 2)  # let the synth fall silent before the next part
    gain = 1.0 if is_drums else INSTRUMENTS[track.instrument][5]
    return (out.T * gain).astype(np.float32)


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
    from pedalboard import Chorus, Compressor, Distortion, Gain, HighpassFilter, LowpassFilter, Pedalboard

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
        if pack.get("chorus") and role in ("comp", "pad"):
            fx += [Chorus(rate_hz=0.6, depth=0.2, mix=0.35)]
        if pack.get("drive") and role == "lead" and "guitar" in track.instrument:
            fx += [Distortion(drive_db=8), Gain(-6)]
    return Pedalboard(fx)


def mix(song: Song, rng=None) -> tuple[np.ndarray, dict]:
    """Render, process and master the song. Returns (stereo mix (2, n), stems by role)."""
    from pedalboard import Compressor, Delay, HighpassFilter, Pedalboard, Reverb

    rng = rng or np.random.default_rng(song.seed)
    pack = PACKS[song.pack]
    spb = 60.0 / song.bpm
    total_sec = song.bars * 4 * spb + 3.0
    n = int(total_sec * SR)
    # Balance (dB) by role: lead first, then the rhythm section, textures underneath.
    level = {"lead": -6.0, "comp": -13.0, "pad": -17.0, "bass": -9.0, "arp": -17.0, "counter": -15.0,
             "drums": -8.0, "timpani": -12.0}
    sends = {"lead": 0.22, "comp": 0.2, "pad": 0.45, "arp": 0.35, "counter": 0.3, "drums": 0.06, "timpani": 0.25,
             "bass": 0.0}
    kicks = [s * spb for t in song.tracks if t.role == "drums" for s, _, p, _ in t.notes
             if p in (DRUM["kick"], DRUM["concert_bd"])]
    duck = _sidechain(n, kicks)
    dry = np.zeros((2, n), dtype=np.float32)
    rev_send = np.zeros((2, n), dtype=np.float32)
    dly_send = np.zeros((2, n), dtype=np.float32)
    stems: dict[str, np.ndarray] = {}
    for t in song.tracks:
        x = render_track(t, song.bpm, total_sec, rng)
        x = _fx(t, pack, song.bpm)(x, SR)[:, :n]
        if x.shape[1] < n:
            x = np.pad(x, ((0, 0), (0, n - x.shape[1])))
        # Normalise each part to its target level (RMS over the part's active span), then pan.
        active = np.abs(x).max(axis=0) > 1e-4
        rms = float(np.sqrt(np.mean(x[:, active] ** 2))) if active.any() else 0.0
        if rms > 0:
            x *= 10 ** (level.get(t.role, -14) / 20) / rms * 0.25
        if t.role in ("bass", "pad"):
            x *= duck
        x = _pan(x, t.pan)
        dry += x
        rev_send += x * sends.get(t.role, 0.2)
        if t.role == "lead" and pack.get("delay"):
            dly_send += x * pack["delay"]
        stems[t.role] = stems.get(t.role, 0) + x
    reverb = Pedalboard([HighpassFilter(250), Reverb(room_size=pack["reverb"], damping=0.5, wet_level=1.0,
                                                     dry_level=0.0, width=1.0)])
    wet = reverb(rev_send, SR)
    if pack.get("delay"):
        dotted_eighth = 0.75 * spb
        wet += Pedalboard([HighpassFilter(300), Delay(delay_seconds=dotted_eighth, feedback=0.3, mix=1.0)])(dly_send, SR)
    out = dry + 0.55 * wet
    if pack.get("vinyl"):
        out += _vinyl(n, rng)
    # Lows mono (MUSIC_KNOWLEDGE X9): below ~120 Hz both sides get the same signal.
    from scipy.signal import butter, sosfilt

    sos = butter(2, 120, btype="low", fs=SR, output="sos")
    low = sosfilt(sos, out, axis=1)
    out = out - low + low.mean(axis=0, keepdims=True)
    master = Pedalboard([Compressor(threshold_db=-14, ratio=2, attack_ms=15, release_ms=200)])
    out = master(out.astype(np.float32), SR)
    out = loudness_normalise(out, -14.0)
    out = limit(out, ceiling_db=-1.0)
    # Fade the tail out so the ending never clicks.
    fade = int(1.5 * SR)
    out[:, -fade:] *= np.linspace(1, 0, fade)
    return out.astype(np.float32), stems


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
    fmt = ("OGG", "VORBIS") if path.suffix == ".ogg" else ("WAV", "PCM_16")
    with sf.SoundFile(str(path), "w", SR, x.shape[0], format=fmt[0], subtype=fmt[1]) as f:
        for i in range(0, x.shape[1], 32768):
            f.write(np.ascontiguousarray(x[:, i : i + 32768].T))
