"""SQLite storage layer. The database file lives in the data directory
(next to the executable when packaged), so everything stays on the USB
stick and nothing is written to the host machine."""

from __future__ import annotations

import json
import os
import sqlite3
import time

from .models import Finding, Link

SCHEMA = """
CREATE TABLE IF NOT EXISTS investigations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at REAL NOT NULL,
    input_type TEXT NOT NULL,      -- "email" | "username" | "name"
    input_value TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'running',  -- running | done | error
    summary TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS findings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    investigation_id INTEGER NOT NULL REFERENCES investigations(id) ON DELETE CASCADE,
    source TEXT NOT NULL,
    category TEXT NOT NULL,
    fact_type TEXT NOT NULL,
    value TEXT NOT NULL,
    url TEXT DEFAULT '',
    snippet TEXT DEFAULT '',
    confidence INTEGER DEFAULT 50,
    retrieved_at REAL NOT NULL,
    metadata TEXT DEFAULT '{}'
);
CREATE TABLE IF NOT EXISTS links (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    investigation_id INTEGER NOT NULL REFERENCES investigations(id) ON DELETE CASCADE,
    from_id INTEGER NOT NULL,
    to_id INTEGER NOT NULL,
    reason TEXT NOT NULL,
    confidence INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_findings_inv ON findings(investigation_id);
CREATE INDEX IF NOT EXISTS idx_links_inv ON links(investigation_id);
CREATE TABLE IF NOT EXISTS files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    path TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    ext TEXT DEFAULT '',
    size INTEGER DEFAULT 0,
    mtime REAL DEFAULT 0
);
CREATE VIRTUAL TABLE IF NOT EXISTS files_fts USING fts5(
    path UNINDEXED, content, tokenize='unicode61'
);
"""


class Store:
    def __init__(self, data_dir: str):
        os.makedirs(data_dir, exist_ok=True)
        self.path = os.path.join(data_dir, "workbench.db")
        self.conn = sqlite3.connect(self.path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    # ---- investigations ----
    def create_investigation(self, input_type: str, input_value: str) -> int:
        cur = self.conn.execute(
            "INSERT INTO investigations (created_at, input_type, input_value) VALUES (?,?,?)",
            (time.time(), input_type, input_value),
        )
        self.conn.commit()
        return cur.lastrowid

    def set_status(self, inv_id: int, status: str, summary: str = ""):
        self.conn.execute(
            "UPDATE investigations SET status=?, summary=? WHERE id=?",
            (status, summary, inv_id),
        )
        self.conn.commit()

    def get_investigation(self, inv_id: int) -> dict | None:
        row = self.conn.execute(
            "SELECT * FROM investigations WHERE id=?", (inv_id,)
        ).fetchone()
        return dict(row) if row else None

    def list_investigations(self) -> list[dict]:
        rows = self.conn.execute(
            "SELECT i.*, (SELECT COUNT(*) FROM findings f WHERE f.investigation_id=i.id) AS finding_count "
            "FROM investigations i ORDER BY i.created_at DESC"
        ).fetchall()
        return [dict(r) for r in rows]

    def delete_investigation(self, inv_id: int):
        self.conn.execute("DELETE FROM findings WHERE investigation_id=?", (inv_id,))
        self.conn.execute("DELETE FROM links WHERE investigation_id=?", (inv_id,))
        self.conn.execute("DELETE FROM investigations WHERE id=?", (inv_id,))
        self.conn.commit()

    # ---- findings ----
    def add_findings(self, inv_id: int, findings: list[Finding]) -> list[int]:
        ids = []
        for f in findings:
            cur = self.conn.execute(
                """INSERT INTO findings
                   (investigation_id, source, category, fact_type, value, url,
                    snippet, confidence, retrieved_at, metadata)
                   VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (inv_id, f.source, f.category, f.fact_type, f.value, f.url,
                 f.snippet, f.confidence, f.retrieved_at, json.dumps(f.metadata)),
            )
            f.id = cur.lastrowid
            ids.append(cur.lastrowid)
        self.conn.commit()
        return ids

    def get_findings(self, inv_id: int) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM findings WHERE investigation_id=? ORDER BY confidence DESC, source",
            (inv_id,),
        ).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d["metadata"] = json.loads(d.get("metadata") or "{}")
            out.append(d)
        return out

    def update_confidence(self, finding_id: int, confidence: int):
        self.conn.execute(
            "UPDATE findings SET confidence=? WHERE id=?", (confidence, finding_id)
        )
        self.conn.commit()

    # ---- links ----
    def add_links(self, inv_id: int, links: list[Link]):
        for l in links:
            self.conn.execute(
                "INSERT INTO links (investigation_id, from_id, to_id, reason, confidence) VALUES (?,?,?,?,?)",
                (inv_id, l.from_id, l.to_id, l.reason, l.confidence),
            )
        self.conn.commit()

    def get_links(self, inv_id: int) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM links WHERE investigation_id=?", (inv_id,)
        ).fetchall()
        return [dict(r) for r in rows]
