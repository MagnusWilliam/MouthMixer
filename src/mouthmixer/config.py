"""Where things live and the user's settings.

Everything is local: the library folder defaults to %USERPROFILE%\\MouthMixer (or $MOUTHMIXER_HOME).
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path


def home() -> Path:
    return Path(os.environ.get("MOUTHMIXER_HOME", Path.home() / "MouthMixer"))


@dataclass
class Settings:
    port: int = 8765
    hotkey: str = "<ctrl>+<alt>+m"  # "save the last 30 seconds"
    mic_name: str = "QuadCast"  # first input device whose name contains this; "" = system default
    sample_rate: int = 48000
    ring_seconds: float = 30.0
    pre_roll_seconds: float = 5.0
    # Pause listening during these hours (local time, "HH:MM"); empty = never.
    quiet_start: str = ""
    quiet_end: str = ""
    # Auto-pause while any of these apps is using the microphone (Windows only).
    pause_for_apps: list = field(default_factory=lambda: ["discord", "zoom", "teams", "slack", "skype", "webex"])
    keep_tossed_days: int = 7
    # Vocals and lyrics (docs/VOCALS.md). The key stays on this computer; ANTHROPIC_API_KEY also works.
    claude_api_key: str = ""
    # Background listening (catching hums while you work) is off: you record on purpose in the Make tab.
    background_listening: bool = False
    vocal_latency_ms: float = 0.0  # measured by the sync test (Make or Sing), or set by hand
    latency_measured: bool = False  # until it is, recordings use the browser's own estimate of the delay
    latency_pipeline: str = ""  # how the page captured the mic when it was measured ("worklet" or "script")

    def latency_ms(self, estimate_ms: float | None = None, pipeline: str = "worklet") -> float:
        """How late recordings arrive: the value measured with the same mic capture, else the browser's
        estimate (sound out to your ears plus the mic back in), else 0. A value measured with the old
        capture (before the audio-thread recorder) doesn't apply to the new one."""
        if self.measured_for(pipeline) or estimate_ms is None:
            return self.vocal_latency_ms
        return float(max(0.0, min(400.0, estimate_ms)))

    def measured_for(self, pipeline: str = "worklet") -> bool:
        return self.latency_measured and (self.latency_pipeline or "script") == (pipeline or "worklet")

    @classmethod
    def load(cls) -> "Settings":
        p = paths()["settings"]
        if p.exists():
            data = json.loads(p.read_text())
            known = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}
            return cls(**known)
        return cls()

    def save(self) -> None:
        p = paths()["settings"]
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(asdict(self), indent=1))


def paths() -> dict[str, Path]:
    h = home()
    p = {
        "home": h,
        "incoming": h / "incoming",
        "clips": h / "clips",
        "calibration": h / "calibration" / "beatbox.json",
        "control": h / "control",
        "status": h / "listener_status.json",
        "db": h / "library.sqlite",
        "settings": h / "settings.json",
        "logs": h / "logs",
    }
    return p


def ensure_dirs() -> dict[str, Path]:
    p = paths()
    for k in ("incoming", "clips", "control", "logs"):
        p[k].mkdir(parents=True, exist_ok=True)
    p["calibration"].parent.mkdir(parents=True, exist_ok=True)
    return p


def replace_file(tmp: Path, target: Path, tries: int = 40) -> None:
    """Move a freshly written temp file over `target` (atomic for readers). On Windows this fails with
    "Access is denied" while another program has `target` open (the app reads the listener's status every
    second), so wait a moment and retry; as a last resort copy the contents over instead of crashing."""
    import time

    for i in range(tries):
        try:
            tmp.replace(target)
            return
        except PermissionError:
            time.sleep(0.025 * (1 + i % 4))
    target.write_bytes(tmp.read_bytes())
    tmp.unlink(missing_ok=True)

