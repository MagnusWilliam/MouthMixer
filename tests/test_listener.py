"""Stage A: the always-on segmenter and the clip writer (PLAN §2)."""

import json
from datetime import datetime

import librosa
import numpy as np

from mouthmixer import synth as S
from mouthmixer.listener.segmenter import Ring, Segmenter
from mouthmixer.listener.service import ClipWriter, in_quiet_hours

SR = 48000


def up(y):
    return librosa.resample(y, orig_sr=S.SR, target_sr=SR).astype(np.float32)


def feed(seg, y, block=1440):
    for i in range(0, len(y), block):
        seg.feed(y[i : i + block])


def test_ring_keeps_only_the_last_seconds():
    r = Ring(10)
    r.write(np.arange(7, dtype=np.float32))
    r.write(np.arange(7, 14, dtype=np.float32))
    assert list(r.last(10)) == list(range(4, 14))
    assert list(r.last(3)) == [11, 12, 13]


def test_segmenter_finds_clips_with_pre_roll():
    clips = []
    seg = Segmenter(SR, lambda a, src: clips.append((a, src)))
    hum, _ = S.hum(S.melody("ode"), seed=1, lead_in=0.0, tail=0.0)
    talk = S.talking(4, seed=2)
    y = np.concatenate([S.silence(8), hum, S.silence(4), talk, S.silence(4)])
    feed(seg, up(y))
    assert len(clips) == 2
    a, src = clips[0]
    assert src == "auto"
    # Contains the whole hum plus pre-roll, minus most of the trailing quiet.
    assert len(hum) / S.SR + 2 < len(a) / SR < len(hum) / S.SR + 7


def test_short_noises_are_ignored():
    clips = []
    seg = Segmenter(SR, lambda a, src: clips.append(a))
    blip = S.typing(0.4, seed=1)
    feed(seg, up(np.concatenate([S.silence(8), blip, S.silence(5)])))
    assert clips == []


def test_hotkey_saves_the_last_30_seconds():
    clips = []
    seg = Segmenter(SR, lambda a, src: clips.append((a, src)))
    feed(seg, up(S.silence(40)))
    seg.save_last()
    assert clips[0][1] == "hotkey" and abs(len(clips[0][0]) / SR - 30) < 0.1


def test_mute_button_is_detected():
    seg = Segmenter(SR, lambda a, s: None)
    feed(seg, np.zeros(SR * 3, dtype=np.float32))
    assert seg.muted
    feed(seg, up(S.silence(1)))
    assert not seg.muted


def test_clip_writer_keeps_music_and_drops_talking(tmp_path):
    w = ClipWriter(tmp_path, SR)
    hum, _ = S.hum(S.melody("minor"), seed=3)
    assert w.handle(up(hum), "auto", 1.0)
    assert not w.handle(up(S.talking(5, seed=3)), "auto", 2.0)
    assert w.handle(up(S.talking(5, seed=3)), "hotkey", 3.0)  # the hotkey always keeps
    wavs = sorted(tmp_path.glob("*.wav"))
    assert len(wavs) == 2 and not list(tmp_path.glob("*.part"))
    meta = json.loads(wavs[0].with_suffix(".json").read_text())
    assert meta["verdict"]["kind"] == "melody"


def test_quiet_hours():
    assert in_quiet_hours("22:00", "08:00", datetime(2026, 1, 1, 23, 30))
    assert in_quiet_hours("22:00", "08:00", datetime(2026, 1, 1, 7, 59))
    assert not in_quiet_hours("22:00", "08:00", datetime(2026, 1, 1, 12, 0))
    assert not in_quiet_hours("", "", datetime(2026, 1, 1, 23, 0))


def test_listener_end_to_end_without_hardware(home, monkeypatch):
    """Fake mic audio through the real listener: the hum lands in incoming/, the talking doesn't,
    pause/quit commands work, and a missing mic doesn't crash it."""
    import threading
    import time

    from mouthmixer import config
    from mouthmixer.listener import service

    lst = service.Listener(config.Settings(sample_rate=SR))
    monkeypatch.setattr(lst, "_open_stream", lambda: (_ for _ in ()).throw(RuntimeError("no device")))
    lst.start_stream()
    assert lst.state() == "no mic"
    lst.mic_error = ""

    threading.Thread(target=lst._process_audio, daemon=True).start()
    hum, _ = S.hum(S.melody("ode"), seed=5)
    y = up(np.concatenate([S.silence(8), hum, S.silence(4), S.talking(5, seed=4), S.silence(4)]))
    for i in range(0, len(y), 1440):
        lst.audio_q.put(y[i : i + 1440])
    deadline = time.time() + 60
    while time.time() < deadline and (lst.writer.kept_today + lst.writer.dropped_today < 2 or not lst.audio_q.empty()):
        time.sleep(0.2)
    assert lst.writer.kept_today == 1 and lst.writer.dropped_today == 1
    assert len(list(lst.paths["incoming"].glob("*.wav"))) == 1

    threading.Thread(target=lst._control_loop, daemon=True).start()
    (lst.paths["control"] / "pause-1.cmd").write_text("")
    time.sleep(1.5)
    assert lst.state() == "paused"
    status = json.loads(lst.paths["status"].read_text())
    assert status["state"] == "paused" and status["kept_today"] == 1
    (lst.paths["control"] / "quit-1.cmd").write_text("")
    time.sleep(1.5)
    assert not lst.running
