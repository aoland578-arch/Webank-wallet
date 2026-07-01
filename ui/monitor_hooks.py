from __future__ import annotations

import json
from typing import Any

from monitor_recorder import (
    PromptBlock,
    build_hermes_system_blocks,
    bump_session,
    record_event,
    record_input,
    record_output,
    start_turn,
    sync_user,
)
from monitor_model_info import (
    dashscope_asr_info,
    dashscope_embed_info,
    hermes_llm_info,
    merge_llm_metadata,
    realtime_voice_info,
    voicecall_brain_info,
    voicecall_vision_info,
)


def on_user_context(user: dict[str, Any], enterprise: dict[str, Any]) -> None:
    sync_user(user, enterprise)


def on_session_reset(enterprise_id: str) -> None:
    bump_session(enterprise_id)


def record_chat_turn(
    *,
    user: dict[str, Any],
    enterprise: dict[str, Any],
    user_message: str,
    prompt: str,
    prompt_blocks: list[PromptBlock],
    result: dict[str, Any],
    attachments: list[dict[str, Any]] | None = None,
    knowledge_hits: list[Any] | None = None,
    image_hits: list[Any] | None = None,
    tool_events: list[dict[str, Any]] | None = None,
) -> None:
    user_id = str(user.get("id") or "")
    enterprise_id = str(enterprise.get("id") or "")
    sync_user(user, enterprise)
    turn_id = start_turn(
        enterprise_id=enterprise_id,
        user_id=user_id,
        channel="chat",
        user_preview=user_message,
    )

    hermes_llm = hermes_llm_info(enterprise_id)
    embed_llm = dashscope_embed_info()

    for attachment in attachments or []:
        if attachment.get("kind") != "audio":
            continue
        asr_text = str(attachment.get("transcript") or "")
        if not asr_text and not attachment.get("transcript_error"):
            continue
        record_event(
            turn_id,
            enterprise_id=enterprise_id,
            user_id=user_id,
            record_type="asr",
            role="assistant",
            direction="output",
            content=json.dumps(
                {
                    "path": attachment.get("path") or attachment.get("name") or "",
                    "text": asr_text,
                    "emotion": attachment.get("transcript_emotion") or "",
                    "language": attachment.get("transcript_language") or "",
                    "error": attachment.get("transcript_error") or "",
                },
                ensure_ascii=False,
                indent=2,
            ),
            metadata=merge_llm_metadata({"kind": "asr"}, dashscope_asr_info()),
        )

    hermes_blocks = build_hermes_system_blocks(enterprise_id)
    record_input(
        turn_id,
        enterprise_id=enterprise_id,
        user_id=user_id,
        record_type="chat_hermes_system",
        role="system",
        content="\n\n".join(block.content for block in hermes_blocks),
        blocks=hermes_blocks,
        metadata=merge_llm_metadata(
            {"note": "Hermes 运行时 system 快照（SOUL/config/memory/skills），供下方 chat 模型读取"},
            hermes_llm,
        ),
    )

    record_input(
        turn_id,
        enterprise_id=enterprise_id,
        user_id=user_id,
        record_type="chat_main",
        role="user",
        content=prompt,
        blocks=prompt_blocks,
        metadata=merge_llm_metadata(
            {
                "knowledge_hit_count": len(knowledge_hits or []),
                "image_hit_count": len(image_hits or []),
                "attachment_count": len(attachments or []),
                "embed_model": embed_llm.get("model"),
                "auxiliary_llms": [
                    {
                        "role": "向量检索 / RAG",
                        **embed_llm,
                    }
                ],
            },
            hermes_llm,
        ),
    )

    for event in tool_events or []:
        record_event(
            turn_id,
            enterprise_id=enterprise_id,
            user_id=user_id,
            record_type="tool_call",
            role="tool",
            direction="output",
            content=json.dumps(event, ensure_ascii=False, indent=2),
            metadata=merge_llm_metadata({"event_type": event.get("type") or ""}, hermes_llm),
        )

    thinking = str(result.get("thinking") or "").strip()
    if thinking:
        record_output(
            turn_id,
            enterprise_id=enterprise_id,
            user_id=user_id,
            record_type="thinking",
            role="assistant",
            content=thinking,
            metadata=merge_llm_metadata({"kind": "reasoning"}, hermes_llm),
        )

    record_output(
        turn_id,
        enterprise_id=enterprise_id,
        user_id=user_id,
        record_type="chat_main",
        role="assistant",
        content=str(result.get("content") or ""),
        metadata=merge_llm_metadata(
            {
                "progress_count": len(result.get("progress") or []),
                "inline_diff_count": len(result.get("inline_diffs") or []),
            },
            hermes_llm,
        ),
    )


def record_profile_update(
    *,
    user_id: str,
    enterprise_id: str,
    prompt: str,
    result: dict[str, Any],
    trigger: str,
) -> None:
    turn_id = start_turn(
        enterprise_id=enterprise_id,
        user_id=user_id,
        channel="profile",
        user_preview=f"画像更新 ({trigger})",
    )
    llm = hermes_llm_info(enterprise_id, slot="profile")
    record_input(
        turn_id,
        enterprise_id=enterprise_id,
        user_id=user_id,
        record_type="profile_update",
        role="user",
        content=prompt,
        blocks=[PromptBlock("profile_prompt", prompt)],
        metadata=merge_llm_metadata({"trigger": trigger}, llm),
    )
    thinking = str(result.get("thinking") or "").strip()
    if thinking:
        record_output(
            turn_id,
            enterprise_id=enterprise_id,
            user_id=user_id,
            record_type="thinking",
            role="assistant",
            content=thinking,
            metadata=merge_llm_metadata({"trigger": trigger}, llm),
        )
    record_output(
        turn_id,
        enterprise_id=enterprise_id,
        user_id=user_id,
        record_type="profile_update",
        role="assistant",
        content=str(result.get("content") or ""),
        metadata=merge_llm_metadata({"trigger": trigger}, llm),
    )


def record_loan_estimate(
    *,
    user_id: str,
    enterprise_id: str,
    prompt: str,
    result: dict[str, Any],
) -> None:
    turn_id = start_turn(
        enterprise_id=enterprise_id,
        user_id=user_id,
        channel="loan",
        user_preview="贷款额度估算",
    )
    llm = hermes_llm_info(enterprise_id, slot="loan")
    record_input(
        turn_id,
        enterprise_id=enterprise_id,
        user_id=user_id,
        record_type="loan_estimate",
        role="user",
        content=prompt,
        blocks=[PromptBlock("loan_estimate_prompt", prompt)],
        metadata=merge_llm_metadata(None, llm),
    )
    record_output(
        turn_id,
        enterprise_id=enterprise_id,
        user_id=user_id,
        record_type="loan_estimate",
        role="assistant",
        content=str(result.get("content") or ""),
        metadata=merge_llm_metadata(None, llm),
    )


def record_voicecall_turn(
    *,
    user_id: str,
    enterprise_id: str,
    system_prompt: str,
    user_message: str,
    assistant_reply: str,
    memory_context: str = "",
) -> None:
    turn_id = start_turn(
        enterprise_id=enterprise_id,
        user_id=user_id,
        channel="voice",
        user_preview=user_message,
    )
    brain_llm = voicecall_brain_info()
    blocks = [PromptBlock("voicecall_system", system_prompt)]
    if memory_context.strip():
        blocks.append(PromptBlock("voicecall_memory", memory_context))
    record_input(
        turn_id,
        enterprise_id=enterprise_id,
        user_id=user_id,
        record_type="voicecall_turn",
        role="system",
        content=system_prompt + ("\n\n" + memory_context if memory_context.strip() else ""),
        blocks=blocks,
        metadata=merge_llm_metadata(None, brain_llm),
    )
    record_input(
        turn_id,
        enterprise_id=enterprise_id,
        user_id=user_id,
        record_type="voicecall_turn",
        role="user",
        content=user_message,
        blocks=[PromptBlock("user_input", user_message)],
        metadata=merge_llm_metadata(None, brain_llm),
    )
    record_output(
        turn_id,
        enterprise_id=enterprise_id,
        user_id=user_id,
        record_type="voicecall_turn",
        role="assistant",
        content=assistant_reply,
        metadata=merge_llm_metadata(None, brain_llm),
    )


def record_vision_frame(
    *,
    user_id: str,
    enterprise_id: str,
    prompt: str,
    result: str,
) -> None:
    turn_id = start_turn(
        enterprise_id=enterprise_id,
        user_id=user_id,
        channel="vision",
        user_preview="视觉帧描述",
    )
    vision_llm = voicecall_vision_info()
    record_input(
        turn_id,
        enterprise_id=enterprise_id,
        user_id=user_id,
        record_type="vision_frame",
        role="user",
        content=prompt,
        blocks=[PromptBlock("vision_prompt", prompt)],
        metadata=merge_llm_metadata(None, vision_llm),
    )
    record_output(
        turn_id,
        enterprise_id=enterprise_id,
        user_id=user_id,
        record_type="vision_frame",
        role="assistant",
        content=result,
        metadata=merge_llm_metadata(None, vision_llm),
    )


def record_realtime_session(
    *,
    user_id: str,
    enterprise_id: str,
    instructions: str,
    extra_instructions: str = "",
) -> None:
    turn_id = start_turn(
        enterprise_id=enterprise_id,
        user_id=user_id,
        channel="voice_realtime",
        user_preview="实时语音会话建立",
    )
    realtime_llm = realtime_voice_info()
    blocks = [PromptBlock("realtime_instructions", instructions)]
    if extra_instructions.strip():
        blocks.append(PromptBlock("realtime_memory", extra_instructions))
    record_input(
        turn_id,
        enterprise_id=enterprise_id,
        user_id=user_id,
        record_type="voicecall_realtime",
        role="system",
        content=instructions + ("\n\n" + extra_instructions if extra_instructions.strip() else ""),
        blocks=blocks,
        metadata=merge_llm_metadata(
            {"note": "豆包 StartSession.system_role：REALTIME_INSTRUCTIONS + 开场记忆，整通通话只注入一次"},
            realtime_llm,
        ),
    )


def record_voicecall_transcript(
    *,
    user_id: str,
    enterprise_id: str,
    turns: list[dict[str, Any]],
) -> int:
    """Persist a full realtime call transcript into monitor (one turn per user/ai exchange)."""
    if not turns:
        return 0
    realtime_llm = realtime_voice_info()
    recorded = 0
    index = 0
    while index < len(turns):
        item = turns[index]
        role = str(item.get("role") or "").strip()
        text = str(item.get("text") or item.get("content") or "").strip()
        if not text:
            index += 1
            continue
        if role == "user":
            user_text = text
            assistant_text = ""
            if index + 1 < len(turns) and str(turns[index + 1].get("role") or "").strip() == "ai":
                assistant_text = str(
                    turns[index + 1].get("text") or turns[index + 1].get("content") or ""
                ).strip()
                index += 2
            else:
                index += 1
            turn_id = start_turn(
                enterprise_id=enterprise_id,
                user_id=user_id,
                channel="voice_realtime",
                user_preview=user_text[:200],
            )
            record_input(
                turn_id,
                enterprise_id=enterprise_id,
                user_id=user_id,
                record_type="voicecall_realtime",
                role="user",
                content=user_text,
                blocks=[PromptBlock("user_input", user_text)],
                metadata=merge_llm_metadata(
                    {
                        "kind": "realtime_turn",
                        "source": "end_batch",
                        "input_mode": "audio_pcm_asr",
                        "prompt_note": (
                            "端到端实时语音：用户侧为 PCM 音频→豆包内置 ASR 转写；"
                            "非 Hermes 式每轮整包 prompt。"
                            "会话级 system_role+记忆见同通话首条 system 记录；"
                            "画面上下文见「画面上下文注入」记录。"
                        ),
                    },
                    realtime_llm,
                ),
            )
            if assistant_text:
                record_output(
                    turn_id,
                    enterprise_id=enterprise_id,
                    user_id=user_id,
                    record_type="voicecall_realtime",
                    role="assistant",
                    content=assistant_text,
                    metadata=merge_llm_metadata({"kind": "realtime_turn", "source": "end_batch"}, realtime_llm),
                )
            recorded += 1
        elif role == "ai":
            turn_id = start_turn(
                enterprise_id=enterprise_id,
                user_id=user_id,
                channel="voice_realtime",
                user_preview="实时语音播报",
            )
            record_output(
                turn_id,
                enterprise_id=enterprise_id,
                user_id=user_id,
                record_type="voicecall_realtime",
                role="assistant",
                content=text,
                metadata=merge_llm_metadata({"kind": "realtime_turn", "source": "end_batch"}, realtime_llm),
            )
            recorded += 1
            index += 1
        else:
            index += 1
    return recorded


def record_realtime_vision_injection(
    *,
    user_id: str,
    enterprise_id: str,
    injected_text: str,
) -> None:
    """Record silent [画面] context injected into the Doubao realtime dialog (ChatTextQuery)."""
    content = str(injected_text or "").strip()
    if not content:
        return
    realtime_llm = realtime_voice_info()
    turn_id = start_turn(
        enterprise_id=enterprise_id,
        user_id=user_id,
        channel="voice_realtime",
        user_preview="画面上下文注入",
    )
    record_input(
        turn_id,
        enterprise_id=enterprise_id,
        user_id=user_id,
        record_type="voicecall_realtime",
        role="user",
        content=content,
        blocks=[PromptBlock("realtime_vision_context", content)],
        metadata=merge_llm_metadata(
            {
                "kind": "vision_context_injection",
                "note": "静默注入豆包实时对话（ChatTextQuery），触发回复被中继吞掉，仅更新模型上下文",
            },
            realtime_llm,
        ),
    )
