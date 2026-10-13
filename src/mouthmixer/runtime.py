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
