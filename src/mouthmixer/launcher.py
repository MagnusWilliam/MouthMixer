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


STARTING_PAGE = """<!doctype html><meta charset="utf-8"><title>MouthMixer</title>
<style>body{font:15px system-ui,"Segoe UI",sans-serif;background:#15161a;color:#ecebf0;display:grid;place-items:center;
height:100vh;margin:0}div{max-width:520px;text-align:center}.d{width:14px;height:14px;border-radius:50%;background:#3b6fe0;
margin:0 auto 16px;animation:p 1s infinite}@keyframes p{50%{opacity:.3}}code{color:#9ab}</style>
<div><div class="d"></div><h2>Starting MouthMixer…</h2><p id="m">The first start after setup can take up to a minute.</p></div>
<script>
const url = "http://127.0.0.1:__PORT__/";
const t0 = Date.now();
async function tick() {
  try { await fetch(url + "api/ping", {mode: "no-cors", cache: "no-store"}); location.href = url; return; } catch (e) {}
  if (Date.now() - t0 > 120000) {
    document.querySelector("h2").textContent = "MouthMixer didn't start";
    document.querySelector(".d").style.background = "#d2493f";
    document.getElementById("m").innerHTML = "Send Claude the end of this file:<br><code>__LOG__</code>";
    return;
  }
  setTimeout(tick, 700);
}
tick();
</script>"""


def open_app(port: int) -> None:
    url = f"http://127.0.0.1:{port}/"
    if not app_running(port):
        # Show a "starting" page that switches to the app as soon as it answers, instead of an error.
        page = config.paths()["home"] / "starting.html"
        log = config.paths()["logs"] / "app.log"
        page.write_text(STARTING_PAGE.replace("__PORT__", str(port)).replace("__LOG__", str(log)), encoding="utf-8")
        url = page.as_uri()
    b = _browser()
    if b:
        subprocess.Popen([b, f"--app={url}", "--window-size=1280,900"])
    else:
        webbrowser.open(url)


def launch() -> None:
    from .runtime import setup

    setup("launcher")
    settings = config.Settings.load()
    if not listener_running():
        _spawn(["listen"])
    if not app_running(settings.port):
        _spawn(["app"])
    open_app(settings.port)
