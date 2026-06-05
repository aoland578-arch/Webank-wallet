"""端到端实时语音（stepaudio-2.5-realtime）的 WebSocket 中继。

为什么需要中继：浏览器原生 WebSocket **不能自定义请求头**，没法带
``Authorization: Bearer``；而且 API key 绝不能下发到前端。所以这里起一个本地
asyncio WS 服务：

    浏览器  ⇄  本中继（注入 Bearer key）  ⇄  StepFun 实时语音 wss

中继做三件事：
1. 客户端一连上，就替它打开上游 StepFun 连接并发 ``session.update``（小微人设/音色/
   server_vad 断句），之后双向**原样转发**所有 OpenAI-realtime 协议事件。
2. **视觉桥接**：stepaudio 看不了图。前端把客户举到镜头前的一帧用自定义事件
   ``{"type":"vision.frame","frame":"data:image/jpeg;base64,..."}`` 发上来，中继
   **截下不转发**，改调 step-3.7-flash（``voicecall.describe_frame``）把画面关键信息
   描述出来，再以一条 ``[画面]`` 开头的文字消息注入上游会话并 ``response.create``，
   让小微当场"看到并转述"。同时回一条 ``vision.described`` 给前端做字幕。
3. 缺 ``STEP_API_KEY`` 时直接拒连，让前端回落到浏览器占位语音。

随 server.py 同进程、独立线程、独立端口运行（见 ``start_relay_thread``）。
依赖 ``websockets``（仅 python3.13 环境有）。
"""
from __future__ import annotations

import asyncio
import json
import secrets
import threading
from typing import Any
from urllib.parse import parse_qs, urlsplit

import websockets
from websockets.asyncio.client import connect as ws_connect
from websockets.asyncio.server import serve as ws_serve

from config import (
    STEP_API_KEY,
    STEP_REALTIME_WSS,
    VOICECALL_RELAY_HOST,
    VOICECALL_RELAY_PORT,
    VOICECALL_RELAY_TOKEN,
)
from voicecall import describe_frame, realtime_session_config


class _Bridge:
    """一条浏览器⇄StepFun 连接的共享状态。

    关键是跟踪小微当前是否有"活跃回复"（response.created…response.done 之间）：
    实时语音同一时刻只能有一个 response，若在她说话时硬塞 response.create，上游会回
    ``ongoing response already exists`` 把这次"看材料"的开口丢掉。所以看材料时若她正
    在说话，就把开口排队到本轮 response.done 之后再触发。
    """

    def __init__(self, browser: Any, upstream: Any) -> None:
        self.browser = browser
        self.upstream = upstream
        self.active_response = False
        self.pending_vision = False
        self.last_vision_desc = ""  # 上次画面描述，用于去重


async def _inject_vision(bridge: _Bridge, frame: str, auto: bool) -> None:
    """看画面：一帧 → step-3.7-flash 描述 → 注入会话历史。

    auto=True（每轮自动看）：**静默注入**当上下文，不触发 response.create——画面只是
    更新小微的"视觉记忆"，等她回应你这句话时自然用上，不打断、不抢话；描述与上次相同
    则跳过，避免刷屏和重复花钱。
    auto=False（手动"看材料"）：注入后让她当场开口转述，正在说话则排队到说完再触发。
    """
    loop = asyncio.get_running_loop()
    # describe_frame 是阻塞的 requests 调用，丢到线程池，别卡住事件循环。
    description = await loop.run_in_executor(None, describe_frame, frame)
    try:
        await bridge.browser.send(json.dumps({"type": "vision.described", "text": description, "auto": auto}))
    except Exception:
        pass
    # 自动模式下画面没变就不重复注入（省 token、不刷会话历史）。
    if auto and description == bridge.last_vision_desc:
        return
    bridge.last_vision_desc = description
    # 把画面以文字加进会话历史（任何时候都允许，不会和活跃回复冲突）。
    await bridge.upstream.send(json.dumps({
        "type": "conversation.item.create",
        "item": {
            "type": "message",
            "role": "user",
            "content": [{"type": "input_text", "text": "[画面] " + description}],
        },
    }))
    if auto:
        return  # 静默更新视觉记忆，不主动开口
    # 手动看材料：让她开口转述；正在说话就排队，等本轮说完再触发，避免 response 冲突。
    if bridge.active_response:
        bridge.pending_vision = True
    else:
        await bridge.upstream.send(json.dumps({"type": "response.create"}))


async def _pump_upstream_to_browser(bridge: _Bridge) -> None:
    async for msg in bridge.upstream:
        if isinstance(msg, str):
            try:
                ev = json.loads(msg)
            except (ValueError, TypeError):
                ev = None
            if ev is not None:
                t = ev.get("type")
                if t == "response.created":
                    bridge.active_response = True
                elif t == "response.done":
                    bridge.active_response = False
                    await bridge.browser.send(msg)
                    # 本轮回复刚结束，若有排队的"看材料"开口，现在触发。
                    if bridge.pending_vision:
                        bridge.pending_vision = False
                        await bridge.upstream.send(json.dumps({"type": "response.create"}))
                    continue
        await bridge.browser.send(msg)


async def _pump_browser_to_upstream(bridge: _Bridge) -> None:
    async for msg in bridge.browser:
        # 二进制（理论上不会有，协议是 JSON）原样转发。
        if isinstance(msg, (bytes, bytearray)):
            await bridge.upstream.send(msg)
            continue
        # 自定义视觉事件截下来；其余 OpenAI-realtime 事件原样转发。
        try:
            data = json.loads(msg)
        except (ValueError, TypeError):
            await bridge.upstream.send(msg)
            continue
        if data.get("type") == "vision.frame":
            await _inject_vision(bridge, str(data.get("frame") or ""), bool(data.get("auto")))
            continue
        await bridge.upstream.send(msg)


def _token_ok(browser: Any) -> bool:
    """校验连接 query 里的 ?token= 是否匹配（防公网盗用中继）。"""
    try:
        path = browser.request.path  # 形如 /?token=xxx
    except Exception:
        path = ""
    token = (parse_qs(urlsplit(path).query).get("token") or [""])[0]
    return secrets.compare_digest(token, VOICECALL_RELAY_TOKEN)


async def _handle_browser(browser: Any) -> None:
    """一个浏览器连接：校验 token、开上游、配 session、双向转发，任一端断开即收尾。"""
    if not STEP_API_KEY:
        await browser.close(code=1011, reason="STEP_API_KEY not configured")
        return
    if not _token_ok(browser):
        await browser.close(code=4401, reason="unauthorized")
        return
    try:
        async with ws_connect(
            STEP_REALTIME_WSS,
            additional_headers={"Authorization": f"Bearer {STEP_API_KEY}"},
            proxy=None,
            max_size=None,
        ) as upstream:
            # 一连上就把小微人设/音色/断句配下去。
            await upstream.send(json.dumps({
                "type": "session.update",
                "session": realtime_session_config(),
            }))
            bridge = _Bridge(browser, upstream)
            up = asyncio.create_task(_pump_upstream_to_browser(bridge))
            down = asyncio.create_task(_pump_browser_to_upstream(bridge))
            done, pending = await asyncio.wait({up, down}, return_when=asyncio.FIRST_COMPLETED)
            for task in pending:
                task.cancel()
    except websockets.exceptions.WebSocketException:
        try:
            await browser.close(code=1011, reason="upstream error")
        except Exception:
            pass
    except Exception:
        try:
            await browser.close(code=1011, reason="relay error")
        except Exception:
            pass


async def serve_relay(host: str = VOICECALL_RELAY_HOST, port: int = VOICECALL_RELAY_PORT) -> None:
    async with ws_serve(_handle_browser, host, port, max_size=None):
        await asyncio.Future()  # run forever


def start_relay_thread() -> bool:
    """在守护线程里跑中继（供 server.py 启动时调用）。缺 key 则不启动，返回是否启动。"""
    if not STEP_API_KEY:
        return False

    def _run() -> None:
        try:
            asyncio.run(serve_relay())
        except Exception as exc:  # 中继挂了不该拖垮主服务
            print(f"[voicecall_relay] stopped: {exc}", flush=True)

    threading.Thread(target=_run, name="voicecall-relay", daemon=True).start()
    return True


if __name__ == "__main__":
    print(f"voicecall relay: ws://{VOICECALL_RELAY_HOST}:{VOICECALL_RELAY_PORT}", flush=True)
    asyncio.run(serve_relay())
