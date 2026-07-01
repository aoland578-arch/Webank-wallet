from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from threading import Lock
from typing import Any, Iterator

from config import DATA_DIR


MONITOR_DB_PATH = Path(
    os.environ.get("WEWALLET_MONITOR_DB", DATA_DIR / "monitor.sqlite")
).expanduser()

SCHEMA = """
CREATE TABLE IF NOT EXISTS monitor_users (
    user_id         TEXT PRIMARY KEY,
    phone           TEXT NOT NULL,
    enterprise_id   TEXT NOT NULL,
    enterprise_name TEXT NOT NULL DEFAULT '',
    updated_at      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS monitor_sessions (
    enterprise_id   TEXT PRIMARY KEY,
    session_id      TEXT NOT NULL,
    session_index   INTEGER NOT NULL DEFAULT 1,
    updated_at      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS monitor_turns (
    id              TEXT PRIMARY KEY,
    enterprise_id   TEXT NOT NULL,
    user_id         TEXT NOT NULL,
    channel         TEXT NOT NULL,
    session_id      TEXT NOT NULL,
    user_preview    TEXT NOT NULL DEFAULT '',
    turn_index      INTEGER NOT NULL DEFAULT 0,
    created_at      TEXT NOT NULL,
    created_ts      REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_monitor_turns_enterprise
    ON monitor_turns(enterprise_id, created_ts DESC);
CREATE INDEX IF NOT EXISTS idx_monitor_turns_user
    ON monitor_turns(user_id, created_ts DESC);

CREATE TABLE IF NOT EXISTS monitor_llm_records (
    id              TEXT PRIMARY KEY,
    turn_id         TEXT NOT NULL,
    enterprise_id   TEXT NOT NULL,
    user_id         TEXT NOT NULL,
    record_type     TEXT NOT NULL,
    direction       TEXT NOT NULL,
    role            TEXT NOT NULL,
    content         TEXT NOT NULL,
    preview         TEXT NOT NULL DEFAULT '',
    metadata_json   TEXT NOT NULL DEFAULT '{}',
    created_at      TEXT NOT NULL,
    created_ts      REAL NOT NULL,
    FOREIGN KEY (turn_id) REFERENCES monitor_turns(id)
);
CREATE INDEX IF NOT EXISTS idx_monitor_records_turn
    ON monitor_llm_records(turn_id, created_ts DESC);
CREATE INDEX IF NOT EXISTS idx_monitor_records_user
    ON monitor_llm_records(user_id, created_ts DESC);
CREATE INDEX IF NOT EXISTS idx_monitor_records_enterprise
    ON monitor_llm_records(enterprise_id, created_ts DESC);

CREATE TABLE IF NOT EXISTS monitor_prompt_blocks (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    record_id       TEXT NOT NULL,
    block_type      TEXT NOT NULL,
    content         TEXT NOT NULL,
    sort_order      INTEGER NOT NULL,
    FOREIGN KEY (record_id) REFERENCES monitor_llm_records(id)
);
CREATE INDEX IF NOT EXISTS idx_monitor_blocks_record
    ON monitor_prompt_blocks(record_id, sort_order);

CREATE TABLE IF NOT EXISTS monitor_auth_sessions (
    id              TEXT PRIMARY KEY,
    token_hash      TEXT NOT NULL UNIQUE,
    created_at      TEXT NOT NULL,
    expires_at      INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_monitor_auth_expires ON monitor_auth_sessions(expires_at);
"""

_init_lock = Lock()
_initialized = False


def _ensure_initialized() -> None:
    global _initialized
    if _initialized:
        return
    with _init_lock:
        if _initialized:
            return
        MONITOR_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(MONITOR_DB_PATH), isolation_level=None, timeout=10.0)
        try:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.executescript(SCHEMA)
        finally:
            conn.close()
        _initialized = True


def _open() -> sqlite3.Connection:
    _ensure_initialized()
    conn = sqlite3.connect(str(MONITOR_DB_PATH), isolation_level=None, timeout=10.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout=5000")
    return conn


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    conn = _open()
    try:
        yield conn
    finally:
        conn.close()


@contextmanager
def transaction() -> Iterator[sqlite3.Connection]:
    conn = _open()
    conn.execute("BEGIN IMMEDIATE")
    try:
        yield conn
    except BaseException:
        conn.execute("ROLLBACK")
        conn.close()
        raise
    else:
        conn.execute("COMMIT")
        conn.close()


def row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return {key: row[key] for key in row.keys()}
