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
CREATE TABLE IF NOT EXISTS songs (
  id TEXT PRIMARY KEY,
  created REAL NOT NULL,
  status TEXT NOT NULL,           -- new | kept | tossed
  title TEXT,
  style TEXT,
  clip_ids TEXT,                  -- JSON list of the clips it was built from
  score REAL,
  version INTEGER DEFAULT 0,      -- which version is shown
  versions INTEGER DEFAULT 1
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
        # Columns added after the first release (old databases get them here).
        cols = {r[1] for r in self.conn.execute("PRAGMA table_info(clips)")}
        for name, kind in (("quality", "REAL"), ("quality_reasons", "TEXT"), ("song_id", "TEXT")):
            if name not in cols:
                self.conn.execute(f"ALTER TABLE clips ADD COLUMN {name} {kind}")
        self.conn.commit()
        self.songs_dir = clips_dir.parent / "songs"
        self.songs_dir.mkdir(parents=True, exist_ok=True)

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

    # --- clips: quality -----------------------------------------------------------------------------
    def set_quality(self, clip_id: str, q: dict) -> None:
        with self._lock:
            self.conn.execute("UPDATE clips SET quality=?, quality_reasons=? WHERE id=?",
                              (q["score"], json.dumps(q["reasons"]), clip_id))
            self.conn.commit()

    def usable_clips(self, limit: int = 40) -> list[dict]:
        """Clips that passed the quality check and weren't thrown away: material for combinations."""
        rows = self.conn.execute(
            "SELECT * FROM clips WHERE quality >= 0.6 AND status NOT IN ('tossed', 'not_music', 'failed') "
            "ORDER BY created DESC LIMIT ?", (limit,)).fetchall()
        return [self._row(r) for r in rows]

    # --- songs --------------------------------------------------------------------------------------
    def song_dir(self, song_id: str) -> Path:
        return self.songs_dir / song_id

    def add_song(self, song_id: str, record: dict) -> None:
        v = record["versions"][0]
        with self._lock:
            self.conn.execute(
                "INSERT OR REPLACE INTO songs (id, created, status, title, style, clip_ids, score, version, versions) "
                "VALUES (?, ?, 'new', ?, ?, ?, ?, 0, ?)",
                (song_id, record["created"], v["title"], v["style"], json.dumps(sorted({c for x in record["versions"]
                 for c in x["spec"]["clips"]})), v["score"], len(record["versions"])))
            for c in {c for x in record["versions"] for c in x["spec"]["clips"]}:
                self.conn.execute("UPDATE clips SET song_id=COALESCE(song_id, ?) WHERE id=?", (song_id, c))
            self.conn.commit()

    def update_song(self, song_id: str, record: dict, version: int) -> None:
        v = record["versions"][version]
        with self._lock:
            self.conn.execute("UPDATE songs SET title=?, style=?, score=?, version=?, versions=? WHERE id=?",
                              (v["title"], v["style"], v["score"], version, len(record["versions"]), song_id))
            self.conn.commit()

    def set_song_status(self, song_id: str, status: str) -> None:
        with self._lock:
            self.conn.execute("UPDATE songs SET status=? WHERE id=?", (status, song_id))
            self.conn.execute("INSERT INTO feedback (clip_id, at, action, value) VALUES (?, ?, 'song', ?)",
                              (song_id, time.time(), json.dumps(status)))
            self.conn.commit()

    def get_song(self, song_id: str) -> dict | None:
        r = self.conn.execute("SELECT * FROM songs WHERE id=?", (song_id,)).fetchone()
        if not r:
            return None
        d = dict(r)
        d["clip_ids"] = json.loads(d["clip_ids"] or "[]")
        return d

    def list_songs(self, statuses: list[str]) -> list[dict]:
        q = f"SELECT * FROM songs WHERE status IN ({','.join('?' * len(statuses))}) ORDER BY created DESC"
        out = []
        for r in self.conn.execute(q, statuses).fetchall():
            d = dict(r)
            d["clip_ids"] = json.loads(d["clip_ids"] or "[]")
            out.append(d)
        return out
