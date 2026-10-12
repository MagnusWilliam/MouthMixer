"""What the desktop shortcut runs: make sure the listener and the app are running, then open the app in
its own window (Edge or Chrome "app mode": no tabs or address bar)."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
import urllib.request
import webbrowser
from pathlib import Path

from . import config


def _pythonw() -> str:
    exe = Path(sys.executable)
    w = exe.with_name("pythonw.exe")
    return str(w) if sys.platform == "win32" and w.exists() else str(exe)


def _spawn(args: list[str]) -> None:
    kw = {"stdin": subprocess.DEVNULL, "stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL}
    if sys.platform == "win32":
        kw["creationflags"] = 0x00000008 | 0x00000200  # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
    else:
        kw["start_new_session"] = True
    subprocess.Popen([_pythonw(), "-m", "mouthmixer", *args], **kw)


def app_running(port: int) -> bool:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/ping", timeout=1) as r:
            return r.status == 200
    except OSError:
        return False


def listener_running() -> bool:
    p = config.paths()["status"]
    try:
        return time.time() - json.loads(p.read_text()).get("updated", 0) < 5
    except (OSError, ValueError):
        return False


def _browser() -> str | None:
    candidates = []
    for env in ("PROGRAMFILES(X86)", "PROGRAMFILES", "LOCALAPPDATA"):
        base = os.environ.get(env)
        if base:
            candidates += [Path(base) / "Microsoft/Edge/Application/msedge.exe",
                           Path(base) / "Google/Chrome/Application/chrome.exe"]
    for c in candidates:
        if c.exists():
            return str(c)
    return shutil.which("msedge") or shutil.which("google-chrome") or shutil.which("chromium")


def open_app(port: int) -> None:
    url = f"http://127.0.0.1:{port}/"
    b = _browser()
    if b:
        subprocess.Popen([b, f"--app={url}", "--window-size=1280,900"])
    else:
        webbrowser.open(url)


def launch() -> None:
    settings = config.Settings.load()
    config.ensure_dirs()
    if not listener_running():
        _spawn(["listen"])
    if not app_running(settings.port):
        _spawn(["app"])
        for _ in range(60):
            if app_running(settings.port):
                break
            time.sleep(0.25)
    open_app(settings.port)
