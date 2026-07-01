from __future__ import annotations

import hashlib
import secrets
import sqlite3
import time
from typing import Any

from config import iso_now, now_ts
import monitor_db

MONITOR_COOKIE_NAME = "wewallet_monitor_session"
MONITOR_USERNAME = "admin"
MONITOR_PASSWORD = "sudoBPcreateall"
MONITOR_SESSION_TTL_SECONDS = 24 * 60 * 60


def _token_hash(token: str) -> str:
    return hashlib.sha256(f"monitor:{token}".encode("utf-8")).hexdigest()


def verify_monitor_credentials(username: str, password: str) -> bool:
    return (
        secrets.compare_digest(str(username or "").strip(), MONITOR_USERNAME)
        and secrets.compare_digest(str(password or ""), MONITOR_PASSWORD)
    )


def create_monitor_session() -> str:
    token = secrets.token_urlsafe(32)
    session_id = secrets.token_hex(16)
    expires_at = now_ts() + MONITOR_SESSION_TTL_SECONDS
    with monitor_db.transaction() as conn:
        conn.execute(
            """
            INSERT INTO monitor_auth_sessions (id, token_hash, created_at, expires_at)
            VALUES (?, ?, ?, ?)
            """,
            (session_id, _token_hash(token), iso_now(), expires_at),
        )
    return token


def verify_monitor_token(token: str) -> bool:
    if not token:
        return False
    with monitor_db.connect() as conn:
        row = conn.execute(
            """
            SELECT id FROM monitor_auth_sessions
            WHERE token_hash = ? AND expires_at > ?
            """,
            (_token_hash(token), now_ts()),
        ).fetchone()
    return row is not None


def revoke_monitor_token(token: str) -> None:
    if not token:
        return
    with monitor_db.connect() as conn:
        conn.execute(
            "DELETE FROM monitor_auth_sessions WHERE token_hash = ?",
            (_token_hash(token),),
        )


def purge_expired_monitor_sessions() -> None:
    with monitor_db.connect() as conn:
        conn.execute(
            "DELETE FROM monitor_auth_sessions WHERE expires_at <= ?",
            (now_ts(),),
        )
