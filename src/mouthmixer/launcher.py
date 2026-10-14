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
    # Everything the process prints, including errors before its own logging starts, goes to a file.
    out = open(config.paths()["logs"] / f"{args[0]}-console.log", "w", encoding="utf-8")
    kw = {"stdin": subprocess.DEVNULL, "stdout": out, "stderr": subprocess.STDOUT}
    if sys.platform == "win32":
        kw["creationflags"] = 0x00000008 | 0x00000200  # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
    else:
        kw["start_new_session"] = True
    subprocess.Popen([_pythonw(), "-m", "mouthmixer", *args], **kw)


_NO_PROXY = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def app_running(port: int) -> bool:
    try:
        with _NO_PROXY.open(f"http://127.0.0.1:{port}/api/ping", timeout=1) as r:
            return r.status == 200
    except OSError:
        return False


def app_version(port: int) -> str | None:
    try:
        with _NO_PROXY.open(f"http://127.0.0.1:{port}/api/ping", timeout=1) as r:
            return json.loads(r.read()).get("version")
    except (OSError, ValueError):
        return None


def stop_old(port: int, force: bool = False) -> None:
    """After an update, a MouthMixer started from the old code may still be running (the app keeps
    serving the new page files but not the new features). Ask it, and the listener, to quit."""
    from .runtime import code_version

    cur = code_version()
    if app_running(port) and (force or app_version(port) != cur):
        try:
            _NO_PROXY.open(urllib.request.Request(f"http://127.0.0.1:{port}/api/shutdown", data=b"", method="POST"),
                           timeout=2).read()
        except OSError:
            pass
        for _ in range(40):
            if not app_running(port):
                break
            time.sleep(0.25)
        if app_running(port):  # an app too old to know /api/shutdown: stop whatever holds the port
            _kill_port(port)
    p = config.paths()
    try:
        st = json.loads(p["status"].read_text())
        if time.time() - st.get("updated", 0) < 5 and (force or st.get("version") != cur):
            p["control"].mkdir(parents=True, exist_ok=True)
            (p["control"] / f"quit-{time.time_ns()}.cmd").write_text("")
            for _ in range(40):
                if not listener_running():
                    break
                time.sleep(0.25)
    except (OSError, ValueError):
        pass


def _kill_port(port: int) -> None:
    if sys.platform != "win32":
        return
    cmd = (f"Get-NetTCPConnection -LocalPort {int(port)} -State Listen -ErrorAction SilentlyContinue | "
           "ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }")
    try:
        subprocess.run(["powershell", "-NoProfile", "-Command", cmd], timeout=15, capture_output=True,
                       creationflags=0x08000000)  # CREATE_NO_WINDOW
    except (OSError, subprocess.SubprocessError):
        pass
    for _ in range(20):
        if not app_running(port):
            return
        time.sleep(0.25)


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


def _tail(path: Path, lines: int = 40) -> str:
    try:
        return "\n".join(path.read_text(encoding="utf-8", errors="replace").splitlines()[-lines:]) or "(empty)"
    except OSError:
        return "(no file)"


def _error_page(port: int) -> str:
    """A page that shows the end of the logs, so a failed start can be screenshotted as-is."""
    import html

    logs = config.paths()["logs"]
    parts = []
    for name in ("app-console.log", "app.log", "listener-console.log", "listener.log", "launcher.log"):
        parts.append(f"<h3>{html.escape(str(logs / name))}</h3><pre>{html.escape(_tail(logs / name))}</pre>")
    page = config.paths()["home"] / "didnt-start.html"
    page.write_text(f"""<!doctype html><meta charset="utf-8"><title>MouthMixer didn't start</title>
<style>body{{font:14px system-ui,"Segoe UI",sans-serif;background:#15161a;color:#ecebf0;margin:24px}}
pre{{background:#1e2026;padding:10px;border-radius:6px;white-space:pre-wrap;font-size:12px}}h3{{font-size:13px;color:#9ab}}</style>
<h2>MouthMixer didn't start</h2><p>Take a screenshot of this page (scroll if needed) and send it to Claude.
Nothing was waiting on port {port}.</p>{"".join(parts)}""", encoding="utf-8")
    return page.as_uri()


def _wait_with_splash(port: int, seconds: float = 120) -> bool:
    """Wait for the app to answer, showing a small "Starting..." window meanwhile."""
    deadline = time.time() + seconds
    try:
        import tkinter as tk

        root = tk.Tk()
        root.title("MouthMixer")
        root.configure(bg="#15161a")
        root.resizable(False, False)
        root.attributes("-topmost", True)
        w, h = 340, 110
        root.geometry(f"{w}x{h}+{(root.winfo_screenwidth() - w) // 2}+{(root.winfo_screenheight() - h) // 2}")
        tk.Label(root, text="Starting MouthMixer…", fg="#ecebf0", bg="#15161a", font=("Segoe UI", 13)).pack(pady=(22, 4))
        tk.Label(root, text="The first start can take up to a minute.", fg="#9a9aa6", bg="#15161a",
                 font=("Segoe UI", 9)).pack()
        result = {"ok": False}

        def poll():
            if app_running(port):
                result["ok"] = True
                root.destroy()
            elif time.time() > deadline:
                root.destroy()
            else:
                root.after(500, poll)

        root.after(300, poll)
        root.mainloop()
        return result["ok"]
    except Exception:
        while time.time() < deadline:
            if app_running(port):
                return True
            time.sleep(0.5)
        return False


def open_app(port: int) -> None:
    # A new address per code version: the window can't show a page it cached before an update.
    v = app_version(port) or str(int(time.time()))
    _open_window(f"http://127.0.0.1:{port}/?v={v}")


def _open_window(url: str) -> None:
    b = _browser()
    if b:
        subprocess.Popen([b, f"--app={url}", "--window-size=1280,900"])
    else:
        webbrowser.open(url)


def launch() -> None:
    from .runtime import setup

    log = setup("launcher")
    settings = config.Settings.load()
    stop_old(settings.port)
    if settings.background_listening and not listener_running():
        _spawn(["listen"])
    if not app_running(settings.port):
        _spawn(["app"])
        if not _wait_with_splash(settings.port):
            log.error("the app didn't answer on port %s", settings.port)
            _open_window(_error_page(settings.port))
            return
    open_app(settings.port)
