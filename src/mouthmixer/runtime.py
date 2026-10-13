"""Process setup shared by the listener and the app.

The shortcut runs pythonw.exe, which gives a program no console: sys.stdout and sys.stderr are None,
and anything that prints (uvicorn's logging, a stray warning) crashes it silently. Here both streams go
to a log file instead, and any crash is written to that log with its traceback.
"""

from __future__ import annotations

import logging
import sys
import traceback

from . import config


def setup(name: str) -> logging.Logger:
    p = config.ensure_dirs()
    log_path = p["logs"] / f"{name}.log"
    if sys.stdout is None or sys.stderr is None:
        stream = open(log_path, "a", buffering=1, encoding="utf-8")
        if sys.stdout is None:
            sys.stdout = stream
        if sys.stderr is None:
            sys.stderr = stream
    logging.basicConfig(filename=str(log_path), level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s", force=True)
    log = logging.getLogger(f"mouthmixer.{name}")

    def hook(kind, value, tb):
        log.error("crashed:\n%s", "".join(traceback.format_exception(kind, value, tb)))

    sys.excepthook = hook
    import threading

    # A crash in a background thread (audio, control) is logged too, instead of vanishing.
    threading.excepthook = lambda a: log.error("thread %s crashed:\n%s", a.thread.name if a.thread else "?",
                                               "".join(traceback.format_exception(a.exc_type, a.exc_value, a.exc_traceback)))
    log.info("starting (%s)", sys.executable)
    return log


_CODE_VERSION = None


def code_version() -> str:
    """A fingerprint of the installed code (every .py/.js/.html/.css file). A running app or listener
    started from older code reports a different one, so the launcher knows to restart it."""
    global _CODE_VERSION
    if _CODE_VERSION is None:
        import hashlib
        from pathlib import Path

        root = Path(__file__).resolve().parent
        h = hashlib.sha1()
        for f in sorted(root.rglob("*")):
            if f.suffix in (".py", ".js", ".html", ".css") and "__pycache__" not in f.parts:
                h.update(f.relative_to(root).as_posix().encode())
                h.update(f.read_bytes())
        _CODE_VERSION = h.hexdigest()[:12]
    return _CODE_VERSION

