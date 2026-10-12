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
