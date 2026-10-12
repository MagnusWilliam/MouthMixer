"""The clip library (PLAN.md §6): one SQLite file plus a folder per clip. The database can be rebuilt
from the folders, so the files are the source of truth."""

from __future__ import annotations

import json
import sqlite3
import threading
import time
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS clips (
  id TEXT PRIMARY KEY,
  created REAL NOT NULL,
  source TEXT NOT NULL,           -- auto | hotkey | upload
  status TEXT NOT NULL,           -- processing | new | kept | tossed | not_music | failed
  kind TEXT,                      -- melody | beat | both
  duration REAL,
  bpm REAL,
  key TEXT,
  n_notes INTEGER,
  n_hits INTEGER,
  reading INTEGER DEFAULT 0,      -- index into pipeline.READINGS ("not what I hummed")
  rating INTEGER,
  note TEXT,
  gate TEXT                       -- JSON of the gate's scores, kept for training the personal classifier
);
CREATE TABLE IF NOT EXISTS feedback (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  clip_id TEXT NOT NULL,
  at REAL NOT NULL,
  action TEXT NOT NULL,           -- kept | tossed | not_music | reading | rating
  value TEXT
);
"""


class Library:
    def __init__(self, db_path: Path, clips_dir: Path):
        self.clips_dir = clips_dir
        self._lock = threading.Lock()
        self.conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)

    def clip_dir(self, clip_id: str) -> Path:
        return self.clips_dir / clip_id

    def add(self, clip_id: str, source: str, gate: dict | None = None, created: float | None = None) -> None:
        with self._lock:
            self.conn.execute(
                "INSERT OR REPLACE INTO clips (id, created, source, status, gate) VALUES (?, ?, ?, 'processing', ?)",
                (clip_id, created or time.time(), source, json.dumps(gate or {})),
            )
            self.conn.commit()

    def set_result(self, clip_id: str, result: dict, reading: int = 0) -> None:
        key = result.get("key") or {}
        with self._lock:
            self.conn.execute(
                """UPDATE clips SET status = CASE WHEN status IN ('processing', 'failed') THEN 'new' ELSE status END,
                   kind=?, duration=?, bpm=?, key=?, n_notes=?, n_hits=?, reading=? WHERE id=?""",
                (result["kind"], result["duration"], result["tempo"]["bpm"], key.get("name"), len(result["notes"]),
                 len(result["drums"]), reading, clip_id),
            )
            self.conn.commit()

    def set_status(self, clip_id: str, status: str) -> None:
        with self._lock:
            self.conn.execute("UPDATE clips SET status=? WHERE id=?", (status, clip_id))
            self.conn.execute("INSERT INTO feedback (clip_id, at, action) VALUES (?, ?, ?)", (clip_id, time.time(), status))
            self.conn.commit()

    def log(self, clip_id: str, action: str, value) -> None:
        with self._lock:
            self.conn.execute("INSERT INTO feedback (clip_id, at, action, value) VALUES (?, ?, ?, ?)",
                              (clip_id, time.time(), action, json.dumps(value)))
            self.conn.commit()

    def get(self, clip_id: str) -> dict | None:
        r = self.conn.execute("SELECT * FROM clips WHERE id=?", (clip_id,)).fetchone()
        return self._row(r) if r else None

    def list(self, statuses: list[str] | None = None, limit: int = 200) -> list[dict]:
        if statuses:
            q = f"SELECT * FROM clips WHERE status IN ({','.join('?' * len(statuses))}) ORDER BY created DESC LIMIT ?"
            rows = self.conn.execute(q, (*statuses, limit)).fetchall()
        else:
            rows = self.conn.execute("SELECT * FROM clips ORDER BY created DESC LIMIT ?", (limit,)).fetchall()
        return [self._row(r) for r in rows]

    @staticmethod
    def _row(r: sqlite3.Row) -> dict:
        d = dict(r)
        d["gate"] = json.loads(d["gate"] or "{}")
        return d
