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


def test_frozen_mic_is_reopened_and_never_saves_stale_audio(home, monkeypatch):
    """The reported bug: three hotkey saves gave the exact same clip, not what was just sung. That happens
    when the mic stops calling back (USB drop-out, sleep) while the listener keeps running: the 30 s
    memory freezes. Now the watchdog reopens the mic, a save with no fresh audio is refused, and an
    identical clip is never written twice."""
    import time

    from mouthmixer import config
    from mouthmixer.listener import service

    lst = service.Listener(config.Settings(sample_rate=SR))
    opened = []

    class FakeStream:
        active = True

        def stop(self):
            pass

        def close(self):
            pass

    def fake_open():
        lst.stream = FakeStream()
        lst.opened_at = time.monotonic()
        lst.last_block = 0.0
        opened.append(1)

    monkeypatch.setattr(lst, "_open_stream", fake_open)
    lst.start_stream()
    hum, _ = S.hum(S.melody("ode"), seed=5)
    lst.seg.feed(up(hum))  # sound arrives...
    lst.last_block = time.monotonic()
    lst.save_last()
    clip = lst.writer.q.get(timeout=2)
    assert lst.writer.handle(*clip)

    # ...then the mic goes quiet (no callbacks). A save now must not repeat the old audio.
    lst.seg.last_feed -= 10
    lst.last_block -= 10
    lst.save_last()
    assert lst.writer.q.empty() and "Nothing saved" in lst.writer.notice
    assert len(opened) == 2  # the save reopened the mic

    lst.last_block = time.monotonic() - 5  # still nothing arriving: the watchdog reopens it again
    lst.check_stream()
    assert len(opened) == 3 and lst.restarts == 2

    # Belt and braces: the writer refuses a byte-identical copy of the previous clip.
    assert not lst.writer.handle(clip[0], "hotkey", time.time())
    assert len(list(lst.paths["incoming"].glob("*.wav"))) == 1
    status = (lst.write_status(), json.loads(lst.paths["status"].read_text()))[1]
    assert status["mic_restarts"] == 2 and status["notice"]


def test_a_bad_block_does_not_stop_the_audio_thread(home, monkeypatch):
    import threading
    import time

    from mouthmixer import config
    from mouthmixer.listener import service

    lst = service.Listener(config.Settings(sample_rate=SR))
    real = lst.seg.feed
    calls = []

    def flaky(block):
        calls.append(1)
        if len(calls) == 1:
            raise ValueError("boom")
        real(block)

    monkeypatch.setattr(lst.seg, "feed", flaky)
    threading.Thread(target=lst._process_audio, daemon=True).start()
    for _ in range(3):
        lst.audio_q.put(np.zeros(1440, dtype=np.float32))
    deadline = time.time() + 5
    while time.time() < deadline and len(calls) < 3:
        time.sleep(0.05)
    assert len(calls) == 3 and lst.seg.last_feed > 0
    lst.running = False


def test_status_file_survives_a_reader_holding_it_open(tmp_path, monkeypatch):
    """Windows refuses to replace a file another program has open (the app reads the status every
    second). That crashed the listener's control loop on the user's PC; now it waits and retries."""
    from pathlib import Path

    from mouthmixer import config

    target = tmp_path / "status.json"
    target.write_text("old")
    tmp = tmp_path / "status.tmp"
    tmp.write_text("new")
    real = Path.replace
    fails = {"n": 3}

    def flaky(self, dst):
        if fails["n"] > 0:
            fails["n"] -= 1
            raise PermissionError(5, "Access is denied")
        return real(self, dst)

    monkeypatch.setattr(Path, "replace", flaky)
    config.replace_file(tmp, target)
    assert target.read_text() == "new" and not tmp.exists()

    tmp.write_text("newer")  # never succeeds: the contents are copied instead of crashing
    fails["n"] = 10 ** 6
    config.replace_file(tmp, target, tries=3)
    assert target.read_text() == "newer"


def test_control_loop_keeps_going_after_an_error(home, monkeypatch):
    import threading
    import time

    from mouthmixer import config
    from mouthmixer.listener import service

    lst = service.Listener(config.Settings(sample_rate=SR))
    monkeypatch.setattr(lst, "_open_stream", lambda: (_ for _ in ()).throw(RuntimeError("no device")))
    calls = {"n": 0}
    real = lst.write_status

    def flaky():
        calls["n"] += 1
        if calls["n"] == 1:
            raise PermissionError(5, "Access is denied")
        real()

    monkeypatch.setattr(lst, "write_status", flaky)
    threading.Thread(target=lst._control_loop, daemon=True).start()
    time.sleep(1.6)
    assert calls["n"] >= 3  # it carried on after the failure
    assert json.loads(lst.paths["status"].read_text())["version"]
    (lst.paths["control"] / "quit-1.cmd").write_text("")
    time.sleep(1.2)
    assert not lst.running
