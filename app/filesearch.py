"""Portable file search — the second tool in the workbench.

Windows Search is notoriously weak on external drives and network
shares (no index, no content search). This module builds its own index
into the on-stick SQLite database:

- filenames, sizes, dates for every file under the chosen roots
- optionally, extracted TEXT CONTENT (.txt/.md/.csv/.log/.docx/.pdf/…)
  stored in an FTS5 full-text table for instant "files containing X"

Everything is read-only against the scanned drives; nothing is
modified on them. The index travels with the USB stick.
"""

from __future__ import annotations

import os
import re
import sqlite3
import threading
import time
import zipfile

TEXT_EXTS = {
    ".txt", ".md", ".csv", ".log", ".json", ".py", ".js", ".ts",
    ".html", ".htm", ".xml", ".yaml", ".yml", ".ini", ".cfg", ".conf",
    ".sql", ".sh", ".bat", ".ps1", ".rtf", ".tex", ".java", ".c",
    ".cpp", ".h", ".css",
}
MAX_CONTENT_BYTES = 2_000_000   # per file; big files indexed by name only
MAX_PDF_PAGES = 15

_state = {"running": False, "done": 0, "errors": 0,
          "current": "", "started": 0.0, "with_content": False}
_state_lock = threading.Lock()


def status() -> dict:
    with _state_lock:
        return dict(_state)


def _connect(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


# ---------------- text extraction ----------------

def _extract_docx(path: str) -> str:
    try:
        with zipfile.ZipFile(path) as z:
            xml = z.read("word/document.xml").decode("utf-8", "ignore")
        return re.sub(r"<[^>]+>", " ", xml)
    except Exception:
        return ""


def _extract_pdf(path: str) -> str:
    try:
        from pypdf import PdfReader
        reader = PdfReader(path)
        parts = []
        for page in reader.pages[:MAX_PDF_PAGES]:
            parts.append(page.extract_text() or "")
        return "\n".join(parts)
    except Exception:
        return ""


def extract_text(path: str, ext: str) -> str | None:
    try:
        if os.path.getsize(path) > MAX_CONTENT_BYTES:
            return None
    except OSError:
        return None
    if ext in TEXT_EXTS:
        try:
            with open(path, "rb") as fh:
                return fh.read().decode("utf-8", "ignore")
        except OSError:
            return None
    if ext == ".docx":
        return _extract_docx(path)
    if ext == ".pdf":
        return _extract_pdf(path)
    return None


# ---------------- indexing ----------------

def clear_index(db_path: str):
    conn = _connect(db_path)
    conn.execute("DELETE FROM files")
    conn.execute("DELETE FROM files_fts")
    conn.commit()
    conn.close()


def indexed_count(db_path: str) -> int:
    try:
        conn = _connect(db_path)
        n = conn.execute("SELECT COUNT(*) FROM files").fetchone()[0]
        conn.close()
        return n
    except sqlite3.Error:
        return 0


def index_roots(db_path: str, roots: list[str], with_content: bool):
    """Blocking worker — run in a thread."""
    global _state
    with _state_lock:
        _state = {"running": True, "done": 0, "errors": 0,
                  "current": "", "started": time.time(),
                  "with_content": with_content}
    conn = _connect(db_path)
    try:
        conn.execute("DELETE FROM files")
        conn.execute("DELETE FROM files_fts")
        conn.commit()

        batch_files, batch_fts = [], []
        for root in roots:
            root = root.strip().strip('"')
            if not root or not os.path.exists(root):
                with _state_lock:
                    _state["errors"] += 1
                continue
            for dirpath, dirnames, filenames in os.walk(root):
                with _state_lock:
                    _state["current"] = dirpath
                for name in filenames:
                    full = os.path.join(dirpath, name)
                    try:
                        st = os.stat(full)
                    except OSError:
                        with _state_lock:
                            _state["errors"] += 1
                        continue
                    ext = os.path.splitext(name)[1].lower()
                    batch_files.append((full, name, ext, st.st_size, st.st_mtime))
                    if with_content:
                        text = extract_text(full, ext)
                        if text:
                            batch_fts.append((full, text[:500_000]))
                    with _state_lock:
                        _state["done"] += 1
                    # flush in batches for speed + progress visibility
                    if len(batch_files) >= 500:
                        _flush(conn, batch_files, batch_fts)
                        batch_files, batch_fts = [], []
        _flush(conn, batch_files, batch_fts)
    finally:
        conn.close()
        with _state_lock:
            _state["running"] = False
            _state["current"] = ""


def _flush(conn, batch_files, batch_fts):
    if batch_files:
        conn.executemany(
            "INSERT INTO files (path, name, ext, size, mtime) VALUES (?,?,?,?,?)",
            batch_files)
    if batch_fts:
        conn.executemany(
            "INSERT INTO files_fts (path, content) VALUES (?,?)", batch_fts)
    conn.commit()


# ---------------- searching ----------------

def search(db_path: str, query: str, limit: int = 200) -> dict:
    """Filename matches (substring) + content matches (FTS5)."""
    query = query.strip()
    if not query:
        return {"name_hits": [], "content_hits": []}
    conn = _connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        like = f"%{query}%"
        name_hits = [dict(r) for r in conn.execute(
            "SELECT path, name, ext, size, mtime FROM files "
            "WHERE name LIKE ? ORDER BY mtime DESC LIMIT ?",
            (like, limit))]

        content_hits = []
        # FTS5: quote each term so arbitrary user input can't break MATCH
        fts_query = " OR ".join(f'"{t}"' for t in query.split() if t)
        try:
            content_hits = [dict(r) for r in conn.execute(
                "SELECT f.path, f.name, f.ext, f.size, f.mtime, "
                "snippet(files_fts, 1, '<mark>', '</mark>', ' … ', 28) AS excerpt "
                "FROM files_fts JOIN files f ON f.path = files_fts.path "
                "WHERE files_fts MATCH ? ORDER BY rank LIMIT ?",
                (fts_query, limit))]
        except sqlite3.Error:
            pass
        return {"name_hits": name_hits, "content_hits": content_hits}
    finally:
        conn.close()
