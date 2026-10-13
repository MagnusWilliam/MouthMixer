"""The background listener process: mic capture, the segmenter, the music gate, the tray icon, the
"save that!" hotkey and auto-pause (PLAN.md §2-3, §12 #4-5).

Only clips the gate calls music (or that you saved with the hotkey) are written to the library's
incoming folder; everything else is dropped from memory without touching the disk.
Hardware parts (sounddevice, pystray, pynput, winreg) are imported lazily so the rest stays testable.
"""

from __future__ import annotations

import hashlib
import json
import logging
import queue
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

import librosa
import numpy as np
import soundfile as sf

from .. import config
from ..analysis import detect
from .segmenter import Segmenter, SegmenterSettings

log = logging.getLogger("mouthmixer.listener")


class ClipWriter:
    """Judges finished clips off the audio thread and writes the musical ones to incoming/."""

    def __init__(self, incoming: Path, sr: int):
        self.incoming = incoming
        self.sr = sr
        self.q: queue.Queue = queue.Queue()
        self.kept_today = 0
        self.dropped_today = 0
        self.last_kept: str | None = None
        self.notice = ""
        self._last_digest = ""
        self._day = datetime.now().date()
        threading.Thread(target=self._run, daemon=True, name="clip-writer").start()

    def submit(self, audio: np.ndarray, source: str) -> None:
        self.q.put((audio, source, time.time()))

    def handle(self, audio: np.ndarray, source: str, created: float) -> bool:
        # Two hotkey saves with the same audio mean the mic stopped delivering (the 30 s memory froze):
        # never save the copy.
        if source == "hotkey":
            digest = hashlib.sha1(np.ascontiguousarray(audio, dtype=np.float32).tobytes()).hexdigest()
            if digest == self._last_digest:
                log.warning("dropped a hotkey clip identical to the previous one (no new audio from the mic)")
                self.notice = "That save had no new sound in it: the mic had stopped sending audio."
                return False
            self._last_digest = digest
        if datetime.now().date() != self._day:
            self._day, self.kept_today, self.dropped_today = datetime.now().date(), 0, 0
        y16 = librosa.resample(audio.astype(np.float32), orig_sr=self.sr, target_sr=16000)
        verdict = detect.judge(y16, 16000)
        if not verdict.is_music and source != "hotkey":
            verdict = self.second_opinion(y16, verdict)
        if not verdict.is_music and source != "hotkey":
            self.dropped_today += 1
            return False
        stamp = datetime.fromtimestamp(created).strftime("%Y%m%d-%H%M%S-%f")[:-3]
        wav = self.incoming / f"{stamp}.wav"
        tmp = self.incoming / f"{stamp}.part"
        sf.write(str(tmp), audio, self.sr, subtype="PCM_16", format="WAV")
        (self.incoming / f"{stamp}.json").write_text(json.dumps(
            {"source": source, "created": created, "verdict": verdict.to_dict(), "sr": self.sr}))
        tmp.replace(wav)  # the app only picks up complete .wav files
        self.kept_today += 1
        self.last_kept = stamp
        return True

    @staticmethod
    def second_opinion(y16: np.ndarray, verdict: detect.Verdict) -> detect.Verdict:
        """Unsure? (some held notes or some beat, below the bar.) Transcribe it and check whether it follows
        musical rules and is consistent (critic.clip_quality). Kept only if it does."""
        sc = verdict.scores
        if sc.get("melody", 0) < 0.2 and sc.get("beat", 0) < 0.15:
            return verdict
        from ..analysis import pipeline
        from ..arrange.critic import clip_quality

        try:
            result = pipeline.analyse(y16, 16000, verdict=detect.Verdict(True, "both" if sc.get("beat", 0) >= 0.15
                                                                          and sc.get("melody", 0) >= 0.2 else
                                                                          "beat" if sc.get("beat", 0) >= 0.15 else "melody",
                                                                          sc))
            q = clip_quality(result)
        except Exception:
            log.exception("second opinion failed")
            return verdict
        if q["ok"]:
            return detect.Verdict(True, result["kind"], {**sc, "rescued_by_rules": q["score"]})
        return verdict

    def _run(self):
        while True:
            audio, source, created = self.q.get()
            try:
                self.handle(audio, source, created)
            except Exception:  # never let one bad clip stop the listener
                log.exception("failed to judge or write a clip")


def in_quiet_hours(start: str, end: str, now: datetime | None = None) -> bool:
    if not start or not end:
        return False
    now = now or datetime.now()
    cur = now.hour * 60 + now.minute
    s = int(start[:2]) * 60 + int(start[3:5])
    e = int(end[:2]) * 60 + int(end[3:5])
    return s <= cur < e if s <= e else (cur >= s or cur < e)


def apps_using_mic(watch: list[str]) -> list[str]:
    """Windows: apps currently using the microphone, from the privacy settings registry. Our own Python
    process is excluded. Returns the names from `watch` that matched."""
    if sys.platform != "win32":
        return []
    import winreg

    base = r"Software\Microsoft\Windows\CurrentVersion\CapabilityAccessManager\ConsentStore\microphone"
    own = sys.executable.lower().replace("\\", "#")
    found = []

    def scan(path: str):
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, path)
        except OSError:
            return
        i = 0
        while True:
            try:
                sub = winreg.EnumKey(key, i)
            except OSError:
                break
            i += 1
            if sub == "NonPackaged":
                scan(path + "\\" + sub)
                continue
            try:
                k = winreg.OpenKey(winreg.HKEY_CURRENT_USER, path + "\\" + sub)
                stop, _ = winreg.QueryValueEx(k, "LastUsedTimeStop")
                start, _ = winreg.QueryValueEx(k, "LastUsedTimeStart")
            except OSError:
                continue
            name = sub.lower()
            if stop == 0 and start > 0 and own not in name:
                for w in watch:
                    if w in name:
                        found.append(w)

    scan(base)
    return sorted(set(found))


def find_input_device(name: str):
    """The input device the user picked: an exact name match first (from the app's mic list), then a
    partial match (the default setting "QuadCast"). None = the system default."""
    import sounddevice as sd

    if not name:
        return None
    devs = list(enumerate(sd.query_devices()))
    for i, d in devs:
        if d["max_input_channels"] > 0 and d["name"] == name:
            return i
    for i, d in devs:
        if d["max_input_channels"] > 0 and name.lower() in d["name"].lower():
            return i
    return None


class Listener:
    def __init__(self, settings: config.Settings | None = None):
        self.settings = settings or config.Settings.load()
        self.paths = config.ensure_dirs()
        self.sr = self.settings.sample_rate
        self.writer = ClipWriter(self.paths["incoming"], self.sr)
        seg_s = SegmenterSettings(pre_roll_sec=self.settings.pre_roll_seconds, ring_sec=self.settings.ring_seconds)
        self.seg = Segmenter(self.sr, self.writer.submit, seg_s)
        self.audio_q: queue.Queue = queue.Queue(maxsize=400)
        self.user_paused = False
        self.auto_reason = ""
        self.stream = None
        self.running = True
        self.icon = None
        self.device_name = ""
        self.mic_error = ""
        self._last_try = 0.0
        self.last_block = 0.0  # time.monotonic() of the last block from the mic callback
        self.opened_at = 0.0
        self.restarts = 0
        self._stream_lock = threading.RLock()

    # --- state --------------------------------------------------------------------------------
    @property
    def paused(self) -> bool:
        return self.user_paused or bool(self.auto_reason)

    def state(self) -> str:
        if self.paused:
            return "paused"
        if self.mic_error:
            return "no mic"
        if self.seg.muted:
            return "muted"
        return "capturing" if self.seg.capturing else "listening"

    def write_status(self) -> None:
        status = {
            "state": self.state(),
            "paused_by_user": self.user_paused,
            "auto_pause_reason": self.auto_reason,
            "kept_today": self.writer.kept_today,
            "dropped_today": self.writer.dropped_today,
            "device": self.device_name,
            "level_db": round(float(getattr(self, "level_db", -120.0)), 1) if self.stream is not None else None,
            "mic_error": self.mic_error,
            "notice": self.writer.notice,
            "audio_age_s": round(time.monotonic() - self.last_block, 1) if self.stream is not None and self.last_block else None,
            "mic_restarts": self.restarts,
            "hotkey": self.settings.hotkey,
            "updated": time.time(),
        }
        tmp = self.paths["status"].with_suffix(".tmp")
        tmp.write_text(json.dumps(status))
        tmp.replace(self.paths["status"])

    # --- audio --------------------------------------------------------------------------------
    def _callback(self, indata, frames, t, status):
        self.last_block = time.monotonic()
        if status:
            self._cb_status = str(status)
        block = indata[:, 0]
        # Input level for the app's meter (smoothed dBFS).
        db = 10 * np.log10(float(np.mean(block.astype(np.float64) ** 2)) + 1e-12)
        self.level_db = max(db, self.level_db - 1.5) if hasattr(self, "level_db") else db
        try:
            self.audio_q.put_nowait(block.copy())
        except queue.Full:
            pass

    def start_stream(self):
        """Open the mic. If it isn't there (unplugged, in use exclusively), keep running and retry."""
        self._last_try = time.time()
        try:
            self._open_stream()
            self.mic_error = ""
        except Exception as e:
            self.stream = None
            self.mic_error = str(e) or "microphone not available"
            log.warning("mic unavailable: %s", self.mic_error)

    def _open_stream(self):
        import sounddevice as sd

        dev = find_input_device(self.settings.mic_name)
        self.device_name = sd.query_devices(dev, "input")["name"] if dev is not None else sd.query_devices(kind="input")["name"]
        self.stream = sd.InputStream(device=dev, channels=1, samplerate=self.sr, dtype="float32",
                                     blocksize=int(self.sr * 0.03), callback=self._callback)
        self.stream.start()
        self.opened_at = time.monotonic()
        self.last_block = 0.0
        log.info("listening on %s", self.device_name)

    def stop_stream(self):
        # Stopping the stream turns off Windows' "mic in use" indicator while paused.
        if self.stream is not None:
            self.stream.stop()
            self.stream.close()
            self.stream = None
        self.seg.reset()
        while not self.audio_q.empty():
            self.audio_q.get_nowait()

    def _process_audio(self):
        while self.running:
            try:
                block = self.audio_q.get(timeout=0.5)
            except queue.Empty:
                continue
            if not self.paused:
                try:
                    self.seg.feed(block)
                except Exception:  # one bad block must not freeze the 30 s memory for good
                    log.exception("could not process an audio block")

    # --- control ------------------------------------------------------------------------------
    def set_paused(self, paused: bool):
        self.user_paused = paused
        self._apply_pause()

    def _apply_pause(self):
        if self.paused and self.stream is not None:
            self.stop_stream()
        elif not self.paused and self.stream is None:
            self.start_stream()

    def save_last(self):
        if self.paused:
            return
        # Only save sound that is actually fresh. If the mic stopped delivering, the memory holds old audio:
        # saving it would give you the same clip again (not what you just did).
        if not self.seg.last_feed or time.monotonic() - self.seg.last_feed > 2.0:
            self.writer.notice = "Nothing saved: the mic isn't sending sound right now (reconnecting it)."
            log.warning("hotkey save skipped: no fresh audio (last fed %.1f s ago)",
                        time.monotonic() - self.seg.last_feed if self.seg.last_feed else -1)
            self._restart_stream("hotkey found no fresh audio")
            return
        self.writer.notice = ""
        self.seg.save_last()

    def check_stream(self) -> None:
        """Watchdog: USB mics drop out (sleep, a loose cable, Windows resetting the device) and PortAudio
        then just stops calling back, with no error. No audio for 3 s = reopen the mic."""
        if self.paused or self.stream is None:
            return
        now = time.monotonic()
        since = now - (self.last_block or self.opened_at)
        active = getattr(self.stream, "active", True)
        if since > 3.0 or not active:
            self._restart_stream(f"no audio from the mic for {since:.0f} s" if active else "the stream stopped")

    def _restart_stream(self, why: str) -> None:
        with self._stream_lock:
            log.warning("reopening the mic: %s", why)
            self.restarts += 1
            try:
                self.stop_stream()
            except Exception:
                log.exception("closing the stalled stream failed")
                self.stream = None
            self.start_stream()
            if not self.mic_error and not self.writer.notice:
                self.writer.notice = "The mic stopped sending sound for a moment and was reconnected."

    def _control_loop(self):
        ctl = self.paths["control"]
        last_auto = 0.0
        while self.running:
            for f in sorted(ctl.glob("*.cmd")):
                cmd = f.stem.split("-")[0]
                f.unlink(missing_ok=True)
                if cmd == "pause":
                    self.set_paused(True)
                elif cmd == "resume":
                    self.set_paused(False)
                elif cmd == "save_last":
                    self.save_last()
                elif cmd == "quit":
                    self.quit()
                elif cmd == "reload_mic":
                    self.settings = config.Settings.load()
                    self.stop_stream()
                    if not self.paused:
                        self.start_stream()
            if time.time() - last_auto > 5:
                last_auto = time.time()
                reason = ""
                if in_quiet_hours(self.settings.quiet_start, self.settings.quiet_end):
                    reason = "quiet hours"
                else:
                    apps = apps_using_mic(self.settings.pause_for_apps)
                    if apps:
                        reason = "mic in use by " + ", ".join(apps)
                if reason != self.auto_reason:
                    self.auto_reason = reason
                    self._apply_pause()
            if not self.paused and self.stream is None and time.time() - self._last_try > 5:
                self.start_stream()
            self.check_stream()
            self.write_status()
            self._update_icon()
            time.sleep(0.5)

    def quit(self):
        self.running = False
        self.stop_stream()
        self.paths["status"].unlink(missing_ok=True)
        if self.icon is not None:
            self.icon.stop()

    # --- tray and hotkey ----------------------------------------------------------------------
    def _icon_image(self, state: str):
        from ..icon import image

        return image(state)

    def _update_icon(self):
        if self.icon is None:
            return
        st = self.state()
        if getattr(self, "_icon_state", None) != st:
            self._icon_state = st
            self.icon.icon = self._icon_image(st)
            self.icon.title = f"MouthMixer: {st}" + (f" ({self.auto_reason})" if self.auto_reason else "")

    def _start_hotkey(self):
        try:
            from pynput import keyboard

            hk = keyboard.GlobalHotKeys({self.settings.hotkey: self.save_last})
            hk.daemon = True
            hk.start()
        except Exception:
            log.exception("hotkey unavailable")

    def run(self, tray: bool = True):
        threading.Thread(target=self._process_audio, daemon=True, name="audio").start()
        if not self.paused:
            self.start_stream()
        self._start_hotkey()
        threading.Thread(target=self._control_loop, daemon=True, name="control").start()
        if tray:
            import pystray

            from ..launcher import open_app

            def toggle(icon, item):
                self.set_paused(not self.user_paused)

            menu = pystray.Menu(
                pystray.MenuItem("Open MouthMixer", lambda i, it: open_app(self.settings.port), default=True),
                pystray.MenuItem("Pause listening", toggle, checked=lambda item: self.user_paused),
                pystray.MenuItem("Save the last 30 seconds", lambda i, it: self.save_last()),
                pystray.MenuItem("Quit MouthMixer", lambda i, it: self.quit()),
            )
            self.icon = pystray.Icon("MouthMixer", self._icon_image("listening"), "MouthMixer", menu)
            self.icon.run()
        else:
            while self.running:
                time.sleep(0.5)


def main(tray: bool = True):
    from ..runtime import setup

    log = setup("listener")
    try:
        Listener().run(tray=tray)
    except Exception:
        log.exception("the listener stopped")
        raise
