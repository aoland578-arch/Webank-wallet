from __future__ import annotations

from typing import Any

from config import (
    ARK_BASE_URL,
    ARK_VISION_MODEL,
    DASHSCOPE_ASR_MODEL,
    DASHSCOPE_EMBED_MODEL,
    DOUBAO_REALTIME_MODEL_VERSION,
    DOUBAO_REALTIME_RESOURCE_ID,
    DOUBAO_REALTIME_TTS_SPEAKER,
    DOUBAO_REALTIME_WS_URL,
    HERMES_HOME,
    STEP_BASE_URL,
    STEP_REALTIME_MODEL,
    STEP_REALTIME_VOICE,
    STEP_REALTIME_WSS,
    STEP_VOICECALL_MODEL,
    VOICECALL_MODEL,
    VOICECALL_PROVIDER,
    VOICECALL_REALTIME_PROVIDER,
    VOICECALL_VISION_PROVIDER,
    enterprise_hermes_home,
)


def _load_hermes_config(enterprise_id: str) -> dict[str, Any]:
    try:
        import yaml
    except ImportError:
        return {}
    for path in (enterprise_hermes_home(enterprise_id) / "config.yaml", HERMES_HOME / "config.yaml"):
        if not path.is_file():
            continue
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
        except OSError:
            continue
        if isinstance(data, dict):
            return data
    return {}


def hermes_llm_info(enterprise_id: str, *, slot: str = "") -> dict[str, str]:
    """Resolve Hermes gateway LLM from enterprise config.yaml."""
    cfg = _load_hermes_config(enterprise_id)
    model_section = cfg.get("model") if isinstance(cfg.get("model"), dict) else {}
    default_model = str((model_section or {}).get("default") or "").strip()
    provider_key = str((model_section or {}).get("provider") or "").strip()
    if provider_key.startswith("custom:"):
        provider_key = provider_key.split(":", 1)[1]
    providers = cfg.get("providers") if isinstance(cfg.get("providers"), dict) else {}
    prov = providers.get(provider_key) if isinstance(providers, dict) else {}
    prov = prov if isinstance(prov, dict) else {}
    provider_name = str(prov.get("name") or provider_key or "Hermes").strip()
    model = str(prov.get("default_model") or default_model or "unknown").strip()
    endpoint = str(prov.get("api") or "").strip()
    route = "Hermes Agent 网关"
    if slot:
        route += f" · slot={slot}"
    return {
        "provider": provider_name,
        "model": model,
        "endpoint": endpoint,
        "route": route,
    }


def dashscope_asr_info() -> dict[str, str]:
    return {
        "provider": "DashScope 阿里云",
        "model": DASHSCOPE_ASR_MODEL,
        "endpoint": "https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation",
        "route": "语音附件 ASR 转写",
    }


def dashscope_embed_info() -> dict[str, str]:
    return {
        "provider": "DashScope 阿里云",
        "model": DASHSCOPE_EMBED_MODEL,
        "endpoint": "https://dashscope.aliyuncs.com/api/v1/services/embeddings/multimodal-embedding/multimodal-embedding",
        "route": "知识库 / 历史图档向量",
    }


def voicecall_brain_info() -> dict[str, str]:
    if VOICECALL_PROVIDER == "stepfun":
        return {
            "provider": "StepFun 阶跃",
            "model": STEP_VOICECALL_MODEL,
            "endpoint": STEP_BASE_URL,
            "route": "视频通话 HTTP 回合 · 大脑",
        }
    return {
        "provider": "火山方舟 Ark / Doubao",
        "model": VOICECALL_MODEL,
        "endpoint": ARK_BASE_URL,
        "route": "视频通话 HTTP 回合 · 大脑",
    }


def voicecall_vision_info() -> dict[str, str]:
    if VOICECALL_VISION_PROVIDER == "stepfun":
        return {
            "provider": "StepFun 阶跃",
            "model": STEP_VOICECALL_MODEL,
            "endpoint": STEP_BASE_URL,
            "route": "视频通话 · 摄像头帧视觉描述",
        }
    return {
        "provider": "火山方舟 Ark / Doubao",
        "model": ARK_VISION_MODEL,
        "endpoint": ARK_BASE_URL,
        "route": "视频通话 · 摄像头帧视觉描述",
    }


def realtime_voice_info() -> dict[str, str]:
    if VOICECALL_REALTIME_PROVIDER == "stepfun":
        return {
            "provider": "StepFun 阶跃",
            "model": STEP_REALTIME_MODEL,
            "endpoint": STEP_REALTIME_WSS,
            "route": "端到端实时语音 WebSocket",
            "extra": f"voice={STEP_REALTIME_VOICE}",
        }
    return {
        "provider": "豆包 openspeech 实时对话",
        "model": DOUBAO_REALTIME_MODEL_VERSION,
        "endpoint": DOUBAO_REALTIME_WS_URL,
        "route": "端到端实时语音 WebSocket",
        "extra": f"resource={DOUBAO_REALTIME_RESOURCE_ID}, tts={DOUBAO_REALTIME_TTS_SPEAKER}",
    }


def merge_llm_metadata(metadata: dict[str, Any] | None, llm: dict[str, str] | None) -> dict[str, Any]:
    meta = dict(metadata or {})
    if llm:
        meta["llm"] = llm
    return meta


def resolve_llm_for_record(record_type: str, enterprise_id: str = "") -> dict[str, str]:
    """Map a monitor record type to the LLM that handled it."""
    kind = str(record_type or "").strip()
    eid = str(enterprise_id or "").strip()
    if kind in {"chat_main", "chat_hermes_system", "thinking", "tool_call"}:
        return hermes_llm_info(eid) if eid else {}
    if kind == "profile_update":
        return hermes_llm_info(eid, slot="profile") if eid else {}
    if kind == "loan_estimate":
        return hermes_llm_info(eid, slot="loan") if eid else {}
    if kind == "asr":
        return dashscope_asr_info()
    if kind == "voicecall_turn":
        return voicecall_brain_info()
    if kind == "voicecall_realtime":
        return realtime_voice_info()
    if kind == "vision_frame":
        return voicecall_vision_info()
    return {}
