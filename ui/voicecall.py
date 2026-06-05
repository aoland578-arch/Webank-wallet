"""通话版小微：视频通话模块的大脑（路线1 MVP）。

和主线文字版小微（profile_service.build_gateway_chat_turn + Hermes 网关）
**完全独立**：这里直接打火山方舟(Ark) 的 Doubao 多模态模型，一次调用既
理解客户说的话、又能看一帧摄像头画面（客户举着的营业执照/流水等）。

为什么不复用主线 Hermes 大脑：Hermes 是回合制、带一大套工具，延迟和形态
不适合"打电话"。这里要的是短、口语、快。等拿到 openspeech 的 App ID+Token，
浏览器端的 STT/TTS 占位会换成真正的端到端 RealtimeVoice，本模块的提示词
和画面注入逻辑可以平移过去。

失败模式：抛出 RuntimeError，由 server 层转成 JSON 错误；前端用语音念出
一句"网络好像有点慢"。
"""
from __future__ import annotations

from typing import Any

import requests

from config import (
    ARK_API_KEY,
    ARK_BASE_URL,
    STEP_API_KEY,
    STEP_BASE_URL,
    STEP_REALTIME_VOICE,
    STEP_VOICECALL_MODEL,
    VOICECALL_MODEL,
    VOICECALL_PROVIDER,
)


REQUEST_TIMEOUT_S = 30
MAX_HISTORY_TURNS = 8  # 通话讲究即时，只带最近几轮，省 token、降延迟。

# 通话版小微人设：从主线小微的风控提示词里裁出"口语版核心"——保留身份、
# 静默交叉验算、温和追问、待核验闭环；去掉表格/工具/JSON/upload_request 等
# 只在文字 UI 才有意义的东西。语气为"打电话"，回复要短。
SYSTEM_PROMPT = """你叫"小微"，是微众钱包的小微贷款客户经理，现在正在和客户**视频通话**。被问到身份就说你是小微。

这是语音通话，不是打字，所以：
- 回复要**短、口语化**，像真人打电话，一般 1～3 句话，别长篇大论、别念清单。
- **绝对不要**输出 Markdown、表格、emoji、JSON、分点编号、括号注释或任何书面格式——你说的每个字都会被读出来。
- 一次只问 1 个最关键的问题，等客户回答再往下。

业务要点（内部把握，别照本宣科）：
1. 先自然接住客户当前的话，再推进贷款相关信息（经营情况、流水、用途、额度、回款、负债、材料）。
2. **静默交叉验算（每轮心里都做，不说破）**：把客户报的数字默默对一下——收入减成本对得上自报利润吗？人手/产能和营收配吗？要的额度和流水/纳税规模匹配吗？发现对不上，**绝不**说"欺诈/不合理/对不上账"，而是温和确认："您前面说的 X 和 Y，我这边对一下口径哈，方便说下……吗？"
3. **疑点要咬住**：客户用"回头补/差不多/没定/挺多的"这种含糊话搪塞，不算说清楚；先礼貌记下，后面换个说法再问，别不了了之。
4. 如果客户把材料举到镜头前（营业执照、流水、合同等），结合你看到的画面回应；看不清就让他举近一点、稳一下。看不到画面时不要假装看到了。
5. 语气亲切、有耐心；客户情绪激动或难过时先共情一句再继续，但该核实的还是要温和地问。
"""


def _build_messages(transcript: str, history: list[dict[str, Any]] | None, frame_data_uri: str) -> list[dict[str, Any]]:
    messages: list[dict[str, Any]] = [{"role": "system", "content": SYSTEM_PROMPT}]
    for turn in (history or [])[-MAX_HISTORY_TURNS:]:
        role = "assistant" if str(turn.get("role")) == "assistant" else "user"
        text = str(turn.get("content") or "").strip()
        if text:
            messages.append({"role": role, "content": text})

    # 当前这轮：有画面就走多模态 content 数组，否则纯文本。
    spoken = transcript.strip() or "（客户没说话，可能在给你看材料）"
    if frame_data_uri:
        messages.append({
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": frame_data_uri}},
                {"type": "text", "text": spoken},
            ],
        })
    else:
        messages.append({"role": "user", "content": spoken})
    return messages


def _resolve_provider() -> tuple[str, str, str, str, dict[str, Any]]:
    """按 VOICECALL_PROVIDER 选大脑，返回 (label, api_key, base_url, model, extra)。

    Ark 和 StepFun 都是 OpenAI 兼容的 /chat/completions，区别只在凭证/地址/模型，
    所以下游 call_xiaowei 一套代码通吃。step-3.7-flash 原生支持图片，多模态注入
    画面的 message 结构两家一致。

    ``extra`` 是要并进 payload 的 provider 专属参数：
    - StepFun 的 step-3.7-flash 是**推理模型**，每轮都会先思考再出 content。打电话
      要快，所以用 ``reasoning_effort: low`` 把思考压到最短；同时调高 max_tokens——
      思考 token 也算在预算里，给少了会把 content 饿成空字符串（finish=length）。
      注意 step-3.5-flash 虽不推理但**不支持图片**，本模块要看摄像头帧故不能用。
    """
    if VOICECALL_PROVIDER == "stepfun":
        if not STEP_API_KEY:
            raise RuntimeError("STEP_API_KEY 未配置，视频通话不可用")
        return "StepFun", STEP_API_KEY, STEP_BASE_URL, STEP_VOICECALL_MODEL, {
            "reasoning_effort": "low",
            "max_tokens": 800,
        }
    if not ARK_API_KEY:
        raise RuntimeError("ARK_API_KEY 未配置，视频通话不可用")
    return "Ark", ARK_API_KEY, ARK_BASE_URL, VOICECALL_MODEL, {"max_tokens": 400}


def call_xiaowei(
    transcript: str,
    history: list[dict[str, Any]] | None = None,
    frame_data_uri: str = "",
) -> str:
    """跑通话版小微一轮。返回小微要说的话（纯文本，供前端 TTS 念出）。"""
    label, api_key, base_url, model, extra = _resolve_provider()

    payload = {
        "model": model,
        "messages": _build_messages(transcript, history, frame_data_uri),
        "temperature": 0.7,
        **extra,
    }
    try:
        resp = requests.post(
            f"{base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=REQUEST_TIMEOUT_S,
        )
        resp.raise_for_status()
        body = resp.json()
    except requests.exceptions.RequestException as exc:
        raise RuntimeError(f"{label} 请求失败：{exc}") from exc
    except ValueError as exc:
        raise RuntimeError(f"{label} 响应非 JSON：{exc}") from exc

    try:
        text = str(body["choices"][0]["message"]["content"] or "").strip()
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError(f"{label} 响应缺少内容：{body}") from exc
    if not text:
        raise RuntimeError("小微没给出回复")
    return text


# ──────────────────────────────────────────────────────────────────────────
# 实时语音（stepaudio-2.5-realtime）相关：会话人设 + 视觉桥接
#
# 端到端实时语音模型自己听+说，但**看不了图**。混合桥接的做法：客户把材料举到
# 镜头前时，前端截一帧发给中继，中继调 step-3.7-flash（多模态）把画面里的关键证件
# 信息客观描述出来，再以一条文字消息注入实时会话，让小微"像看到了一样"开口转述并
# 交叉验算。describe_frame() 就是这一步的"眼睛"。
# ──────────────────────────────────────────────────────────────────────────

# 实时会话用的人设：在文字版口语人设基础上，补一句"看材料"的行为约定——因为画面
# 是以文字旁白注入的，要让小微把它当成"自己看到的"，而不是别人转述的。
REALTIME_INSTRUCTIONS = SYSTEM_PROMPT + (
    "\n\n（系统补充）通话中会不时收到以 [画面] 开头的旁白，那是你此刻通过摄像头看到的"
    "实时画面，请当成自己亲眼所见，不要说「系统告诉我」「旁白说」之类的话。"
    "这是你的视觉背景，平时不用刻意复述它；只有当画面和当前对话相关时（比如对方把证件、"
    "单据、商品举到镜头前，或你需要核对材料）才自然地结合画面回应。"
    "需要看材料但画面看不清时，温和地请对方把东西举近一点、举稳一点、光线亮一点。"
)

# step-3.7-flash 当"眼睛"：客观描述整个画面，而不是只找证件——否则客户本人出现、
# 没举材料时会被判成"没有材料"而回"看不清"。
_VISION_PROMPT = (
    "你是视觉助手，正在一通小微企业贷款视频通话里看客户的摄像头画面。"
    "用一两句话客观描述你看到的：画面里有没有人、对方大概在做什么、环境是什么样；"
    "如果对方把证件/单据/商品/经营场所等举到或对准镜头，尽量读出关键信息"
    "（名称、成立日期、经营范围、金额、日期、公司抬头等）。"
    "只有画面确实漆黑、严重模糊或完全空白时才说「看不清」。"
    "不要扮演客服、不要寒暄、不要追问、不要给建议，只描述你看到的。"
)


def describe_frame(frame_data_uri: str) -> str:
    """用 step-3.7-flash 客观描述客户举到镜头前的材料，供注入实时会话。

    失败/看不清都返回一句可直接注入的中文（绝不抛错中断通话）。
    """
    if not frame_data_uri:
        return "看不清，画面里好像没有材料。"
    if not STEP_API_KEY:
        return "看不清。"
    payload = {
        "model": STEP_VOICECALL_MODEL,
        "messages": [{
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": frame_data_uri}},
                {"type": "text", "text": _VISION_PROMPT},
            ],
        }],
        "reasoning_effort": "low",
        "max_tokens": 500,
        "temperature": 0.2,
    }
    try:
        resp = requests.post(
            f"{STEP_BASE_URL}/chat/completions",
            headers={"Authorization": f"Bearer {STEP_API_KEY}", "Content-Type": "application/json"},
            json=payload,
            timeout=REQUEST_TIMEOUT_S,
        )
        resp.raise_for_status()
        text = str(resp.json()["choices"][0]["message"]["content"] or "").strip()
        return text or "看不清。"
    except (requests.exceptions.RequestException, ValueError, KeyError, IndexError, TypeError):
        return "看不清，画面有点糊。"


def realtime_session_config() -> dict[str, Any]:
    """实时会话的 session.update.session 配置（人设/音色/音频格式/断句）。"""
    return {
        "modalities": ["text", "audio"],
        "instructions": REALTIME_INSTRUCTIONS,
        "voice": STEP_REALTIME_VOICE,
        "input_audio_format": "pcm16",
        "output_audio_format": "pcm16",
        "turn_detection": {"type": "server_vad", "silence_duration_ms": 600},
    }


if __name__ == "__main__":
    import sys
    q = sys.argv[1] if len(sys.argv) > 1 else "喂，你好，我想问下贷款的事"
    print(call_xiaowei(q))
