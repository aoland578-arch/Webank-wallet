from __future__ import annotations

import json
import secrets
import sys
import time
import traceback
from dataclasses import dataclass
from typing import Any

from config import enterprise_hermes_home, iso_now
from auth import mask_phone
from monitor_model_info import dashscope_embed_info, resolve_llm_for_record
import monitor_db
import db as main_db


@dataclass
class PromptBlock:
    block_type: str
    content: str


def _new_id(prefix: str) -> str:
    return f"{prefix}_{secrets.token_hex(8)}"


def _preview(text: str, limit: int = 120) -> str:
    value = " ".join(str(text or "").split())
    if len(value) <= limit:
        return value
    return value[: limit - 1] + "…"


def _safe(fn: Any, *args: Any, **kwargs: Any) -> Any:
    try:
        return fn(*args, **kwargs)
    except Exception:
        print("[monitor] record failed:", file=sys.stderr)
        traceback.print_exc()
        return None


def resolve_user_id(enterprise_id: str) -> str:
    with monitor_db.connect() as conn:
        row = conn.execute(
            "SELECT user_id FROM monitor_users WHERE enterprise_id = ?",
            (enterprise_id,),
        ).fetchone()
    if row:
        return str(row["user_id"])
    with main_db.connect() as conn:
        row = conn.execute(
            "SELECT id FROM users WHERE enterprise_id = ?",
            (enterprise_id,),
        ).fetchone()
    return str(row["id"]) if row else "unknown"


def sync_user(user: dict[str, Any], enterprise: dict[str, Any] | None) -> None:
    if not user or not enterprise:
        return
    _safe(
        _sync_user_impl,
        str(user.get("id") or ""),
        str(user.get("phone") or ""),
        str(enterprise.get("id") or ""),
        str(enterprise.get("name") or ""),
    )


def _sync_user_impl(user_id: str, phone: str, enterprise_id: str, enterprise_name: str) -> None:
    with monitor_db.transaction() as conn:
        conn.execute(
            """
            INSERT INTO monitor_users (user_id, phone, enterprise_id, enterprise_name, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                phone = excluded.phone,
                enterprise_id = excluded.enterprise_id,
                enterprise_name = excluded.enterprise_name,
                updated_at = excluded.updated_at
            """,
            (user_id, phone, enterprise_id, enterprise_name, iso_now()),
        )


def get_session_id(enterprise_id: str) -> str:
    with monitor_db.connect() as conn:
        row = conn.execute(
            "SELECT session_id FROM monitor_sessions WHERE enterprise_id = ?",
            (enterprise_id,),
        ).fetchone()
    if row:
        return str(row["session_id"])
    session_id = _new_id("sess")
    with monitor_db.transaction() as conn:
        conn.execute(
            """
            INSERT INTO monitor_sessions (enterprise_id, session_id, session_index, updated_at)
            VALUES (?, ?, 1, ?)
            ON CONFLICT(enterprise_id) DO NOTHING
            """,
            (enterprise_id, session_id, iso_now()),
        )
        row = conn.execute(
            "SELECT session_id FROM monitor_sessions WHERE enterprise_id = ?",
            (enterprise_id,),
        ).fetchone()
    return str(row["session_id"]) if row else session_id


def bump_session(enterprise_id: str) -> str:
    session_id = _new_id("sess")
    with monitor_db.transaction() as conn:
        row = conn.execute(
            "SELECT session_index FROM monitor_sessions WHERE enterprise_id = ?",
            (enterprise_id,),
        ).fetchone()
        next_index = int(row["session_index"]) + 1 if row else 1
        conn.execute(
            """
            INSERT INTO monitor_sessions (enterprise_id, session_id, session_index, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(enterprise_id) DO UPDATE SET
                session_id = excluded.session_id,
                session_index = excluded.session_index,
                updated_at = excluded.updated_at
            """,
            (enterprise_id, session_id, next_index, iso_now()),
        )
    return session_id


def start_turn(
    *,
    enterprise_id: str,
    user_id: str,
    channel: str,
    user_preview: str,
) -> str:
    turn_id = _new_id("turn")
    session_id = get_session_id(enterprise_id)
    created_ts = time.time()
    with monitor_db.transaction() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS cnt FROM monitor_turns WHERE enterprise_id = ?",
            (enterprise_id,),
        ).fetchone()
        turn_index = int(row["cnt"]) + 1 if row else 1
        conn.execute(
            """
            INSERT INTO monitor_turns
            (id, enterprise_id, user_id, channel, session_id, user_preview, turn_index, created_at, created_ts)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                turn_id,
                enterprise_id,
                user_id,
                channel,
                session_id,
                _preview(user_preview, 200),
                turn_index,
                iso_now(),
                created_ts,
            ),
        )
    return turn_id


def record_input(
    turn_id: str,
    *,
    enterprise_id: str,
    user_id: str,
    record_type: str,
    role: str,
    content: str,
    blocks: list[PromptBlock] | None = None,
    metadata: dict[str, Any] | None = None,
) -> str | None:
    return _safe(
        _record_impl,
        turn_id,
        enterprise_id,
        user_id,
        record_type,
        "input",
        role,
        content,
        blocks,
        metadata,
    )


def record_output(
    turn_id: str,
    *,
    enterprise_id: str,
    user_id: str,
    record_type: str,
    role: str,
    content: str,
    metadata: dict[str, Any] | None = None,
) -> str | None:
    return _safe(
        _record_impl,
        turn_id,
        enterprise_id,
        user_id,
        record_type,
        "output",
        role,
        content,
        None,
        metadata,
    )


def record_event(
    turn_id: str,
    *,
    enterprise_id: str,
    user_id: str,
    record_type: str,
    role: str,
    content: str,
    direction: str = "output",
    metadata: dict[str, Any] | None = None,
) -> str | None:
    return _safe(
        _record_impl,
        turn_id,
        enterprise_id,
        user_id,
        record_type,
        direction,
        role,
        content,
        None,
        metadata,
    )


def _record_impl(
    turn_id: str,
    enterprise_id: str,
    user_id: str,
    record_type: str,
    direction: str,
    role: str,
    content: str,
    blocks: list[PromptBlock] | None,
    metadata: dict[str, Any] | None,
) -> str:
    record_id = _new_id("rec")
    created_ts = time.time()
    meta = _enrich_record_metadata(
        {
            "record_type": record_type,
            "enterprise_id": enterprise_id,
            "direction": direction,
            "metadata": metadata,
        }
    )
    meta_json = json.dumps(meta, ensure_ascii=False)
    with monitor_db.transaction() as conn:
        conn.execute(
            """
            INSERT INTO monitor_llm_records
            (id, turn_id, enterprise_id, user_id, record_type, direction, role, content, preview,
             metadata_json, created_at, created_ts)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record_id,
                turn_id,
                enterprise_id,
                user_id,
                record_type,
                direction,
                role,
                content,
                _preview(content),
                meta_json,
                iso_now(),
                created_ts,
            ),
        )
        if blocks:
            for index, block in enumerate(blocks):
                conn.execute(
                    """
                    INSERT INTO monitor_prompt_blocks (record_id, block_type, content, sort_order)
                    VALUES (?, ?, ?, ?)
                    """,
                    (record_id, block.block_type, block.content, index),
                )
    return record_id


def build_hermes_system_blocks(enterprise_id: str) -> list[PromptBlock]:
    home = enterprise_hermes_home(enterprise_id)
    blocks: list[PromptBlock] = []
    for label, relative in (
        ("hermes_soul", "SOUL.md"),
        ("hermes_config", "config.yaml"),
        ("hermes_memory", "memories/MEMORY.md"),
        ("hermes_user", "USER.md"),
    ):
        path = home / relative
        if path.exists():
            try:
                blocks.append(PromptBlock(label, path.read_text(encoding="utf-8")))
            except OSError:
                pass
    skills_dir = home / "skills"
    if skills_dir.is_dir():
        for skill_md in sorted(skills_dir.glob("**/SKILL.md")):
            try:
                rel = skill_md.relative_to(home)
                blocks.append(
                    PromptBlock(f"hermes_skill_{rel.parent.name}", skill_md.read_text(encoding="utf-8"))
                )
            except (OSError, ValueError):
                pass
    if not blocks:
        blocks.append(
            PromptBlock(
                "hermes_system",
                f"(Hermes home 未找到 system 文件: {home})",
            )
        )
    return blocks


def list_users() -> list[dict[str, Any]]:
    with monitor_db.connect() as conn:
        rows = conn.execute(
            """
            SELECT
                u.user_id,
                u.phone,
                u.enterprise_id,
                u.enterprise_name,
                u.updated_at,
                (
                    SELECT MAX(r.created_ts)
                    FROM monitor_llm_records r
                    WHERE r.user_id = u.user_id
                ) AS last_record_ts,
                (
                    SELECT COUNT(*)
                    FROM monitor_llm_records r
                    WHERE r.user_id = u.user_id
                ) AS record_count
            FROM monitor_users u
            ORDER BY COALESCE(last_record_ts, 0) DESC, u.updated_at DESC
            """
        ).fetchall()
    seen = {str(row["user_id"]) for row in rows}
    result: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        item["phone_masked"] = mask_phone(str(item.get("phone") or ""))
        result.append(item)

    with main_db.connect() as conn:
        extra_rows = conn.execute(
            """
            SELECT u.id AS user_id, u.phone, u.enterprise_id, COALESCE(e.name, '') AS enterprise_name
            FROM users u
            LEFT JOIN enterprises e ON e.id = u.enterprise_id
            WHERE u.enterprise_id IS NOT NULL AND u.enterprise_id != ''
            ORDER BY u.last_login_at DESC
            """
        ).fetchall()
    for row in extra_rows:
        user_id = str(row["user_id"])
        if user_id in seen:
            continue
        result.append({
            "user_id": user_id,
            "phone": row["phone"],
            "enterprise_id": row["enterprise_id"],
            "enterprise_name": row["enterprise_name"],
            "updated_at": "",
            "last_record_ts": None,
            "record_count": 0,
            "phone_masked": mask_phone(str(row["phone"] or "")),
        })
    return result


def list_records(
    *,
    user_id: str | None = None,
    enterprise_id: str | None = None,
    limit: int = 200,
    offset: int = 0,
) -> list[dict[str, Any]]:
    clauses: list[str] = []
    params: list[Any] = []
    if user_id:
        clauses.append("r.user_id = ?")
        params.append(user_id)
    if enterprise_id:
        clauses.append("r.enterprise_id = ?")
        params.append(enterprise_id)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    params.extend([limit, offset])
    with monitor_db.connect() as conn:
        rows = conn.execute(
            f"""
            SELECT
                r.id,
                r.turn_id,
                r.enterprise_id,
                r.user_id,
                r.record_type,
                r.direction,
                r.role,
                r.preview,
                r.metadata_json,
                r.created_at,
                r.created_ts,
                t.user_preview AS turn_preview,
                t.turn_index,
                t.channel AS turn_channel
            FROM monitor_llm_records r
            JOIN monitor_turns t ON t.id = r.turn_id
            {where}
            ORDER BY r.created_ts DESC
            LIMIT ? OFFSET ?
            """,
            params,
        ).fetchall()
    result: list[dict[str, Any]] = []
    for row in rows:
        item = {k: v for k, v in dict(row).items() if k != "metadata_json"}
        item["metadata"] = _enrich_record_metadata(
            {
                **item,
                "metadata": _parse_metadata_json(row["metadata_json"]),
            }
        )
        result.append(item)
    return result


def _parse_metadata_json(raw: Any) -> dict[str, Any]:
    try:
        data = json.loads(raw or "{}")
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _enrich_record_metadata(record: dict[str, Any]) -> dict[str, Any]:
    """Ensure metadata carries llm info for both legacy and new records."""
    meta = dict(record.get("metadata") or {})
    direction = str(record.get("direction") or meta.get("llm_direction") or "").strip()
    if not meta.get("llm"):
        llm = resolve_llm_for_record(
            str(record.get("record_type") or ""),
            str(record.get("enterprise_id") or ""),
        )
        if llm:
            meta["llm"] = llm
    if meta.get("llm") and direction:
        meta["llm_direction"] = direction
    if (
        record.get("record_type") == "chat_main"
        and record.get("direction") == "input"
        and not meta.get("auxiliary_llms")
    ):
        embed = dashscope_embed_info()
        meta.setdefault("embed_model", embed.get("model"))
        meta["auxiliary_llms"] = [{"role": "向量检索 / RAG", **embed}]
    return meta


def get_record(record_id: str) -> dict[str, Any] | None:
    with monitor_db.connect() as conn:
        row = conn.execute(
            """
            SELECT
                r.*,
                t.user_preview AS turn_preview,
                t.turn_index,
                t.channel AS turn_channel
            FROM monitor_llm_records r
            JOIN monitor_turns t ON t.id = r.turn_id
            WHERE r.id = ?
            """,
            (record_id,),
        ).fetchone()
        if not row:
            return None
        record = dict(row)
        block_rows = conn.execute(
            """
            SELECT block_type, content, sort_order
            FROM monitor_prompt_blocks
            WHERE record_id = ?
            ORDER BY sort_order ASC
            """,
            (record_id,),
        ).fetchall()
        record["blocks"] = [dict(block) for block in block_rows]
        record["metadata"] = _enrich_record_metadata(
            {
                **record,
                "metadata": _parse_metadata_json(record.pop("metadata_json", "{}")),
            }
        )
        return record


def list_turn_records(turn_id: str) -> list[dict[str, Any]]:
    with monitor_db.connect() as conn:
        rows = conn.execute(
            """
            SELECT id, record_type, direction, role, preview, created_at, created_ts
            FROM monitor_llm_records
            WHERE turn_id = ?
            ORDER BY created_ts DESC
            """,
            (turn_id,),
        ).fetchall()
    return [dict(row) for row in rows]
