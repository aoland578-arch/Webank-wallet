from __future__ import annotations

import ipaddress
import os
import threading
import time
from collections import deque
from urllib.parse import urlparse

from config import is_truthy


_rate_lock = threading.Lock()
_rate_buckets: dict[tuple[str, str], deque[float]] = {}

# Window/limit defaults: tuned for an interactive UI where humans drive the
# requests. Overridable per-deployment via env vars (WEWALLET_RL_<BUCKET>,
# 形如 "10/60" = 60 秒窗口内最多 10 次)。
RATE_LIMITS: dict[str, tuple[int, float]] = {
    # bucket: (max_requests, window_seconds)
    "auth_sms_send": (5, 60.0),
    "auth_login": (10, 60.0),
    "auth_register": (5, 60.0),
    "auth_other": (30, 60.0),
    # 每次 chat 是一轮 LLM 调用（最长 300s）：不限流就是成本放大 + 线程耗尽入口。
    # 10/分钟对真人打字绰绰有余。
    "chat": (10, 60.0),
    # 通话版每句话一次多模态调用；真人语速一分钟也就十几句。
    "voicecall": (30, 60.0),
    # 全量 embedding 重建是全局重操作，再叠一层单飞锁（见 server.py）。
    "reindex": (2, 600.0),
    # 贷款试算 / 画像刷新：每次都可能触发网关重活。
    "heavy": (10, 60.0),
}


def _apply_env_overrides() -> None:
    for bucket in list(RATE_LIMITS):
        raw = os.environ.get(f"WEWALLET_RL_{bucket.upper()}", "").strip()
        if not raw or "/" not in raw:
            continue
        max_part, _, window_part = raw.partition("/")
        try:
            RATE_LIMITS[bucket] = (int(max_part), float(window_part))
        except ValueError:
            pass


_apply_env_overrides()

CSRF_ENFORCE = is_truthy(os.environ.get("WEWALLET_CSRF_ENFORCE", "1"))
CSRF_ALLOW_MISSING_ORIGIN = is_truthy(os.environ.get("WEWALLET_CSRF_ALLOW_MISSING_ORIGIN", "1"))


def bucket_for_path(path: str) -> str | None:
    if path == "/api/auth/sms/send":
        return "auth_sms_send"
    if path in {"/api/auth/password/login", "/api/auth/sms/verify"}:
        return "auth_login"
    if path == "/api/auth/register":
        return "auth_register"
    if path.startswith("/api/auth/"):
        return "auth_other"
    if path in {"/api/chat", "/api/chat/stream"}:
        return "chat"
    if path in {"/api/voicecall", "/api/voicecall/end"}:
        return "voicecall"
    if path in {"/api/knowledge/reindex", "/api/image-knowledge/reindex"}:
        return "reindex"
    if path in {"/api/loan/estimate", "/api/profile/refresh"}:
        return "heavy"
    return None


# 直连对端落在这些地址/网段内才信任 X-Forwarded-For（默认：本机 + Docker 私有
# 网段，覆盖同机 nginx 和 compose 里 nginx 容器两种反代形态）。不做这层判断的话：
# 要么生产环境所有用户共享 nginx 的对端 IP 一个限流桶（互相 DoS），要么直连时
# 攻击者伪造 XFF 头就能无限换"IP"绕过限流。
_DEFAULT_TRUSTED_PROXIES = "127.0.0.1,::1,172.16.0.0/12"
TRUSTED_PROXY_NETS: list[ipaddress.IPv4Network | ipaddress.IPv6Network] = []


def set_trusted_proxies(raw: str) -> None:
    """Parse a comma-separated list of IPs/CIDRs into TRUSTED_PROXY_NETS."""
    TRUSTED_PROXY_NETS.clear()
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            TRUSTED_PROXY_NETS.append(ipaddress.ip_network(part, strict=False))
        except ValueError:
            pass


set_trusted_proxies(os.environ.get("WEWALLET_TRUSTED_PROXIES", _DEFAULT_TRUSTED_PROXIES))


def _is_trusted_proxy(ip: str) -> bool:
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return False
    return any(addr in net for net in TRUSTED_PROXY_NETS)


def resolve_client_ip(remote_addr: str, forwarded_for: str) -> str:
    """Resolve the real client IP for rate limiting.

    Only when the direct peer is a trusted proxy do we look at
    X-Forwarded-For — and then walk it right-to-left, skipping trusted hops,
    returning the first untrusted address. Entries further left are
    client-supplied and trivially spoofable.
    """
    remote_addr = (remote_addr or "").strip()
    if not forwarded_for or not _is_trusted_proxy(remote_addr):
        return remote_addr
    hops = [hop.strip() for hop in forwarded_for.split(",") if hop.strip()]
    for hop in reversed(hops):
        if not _is_trusted_proxy(hop):
            return hop
    return remote_addr


# 跟踪键数超过这个值就清一次已过窗的键：限流状态按 (IP, bucket) 累积，
# 没有清理的话海量伪造 IP（或单纯长期运行）会慢性吃内存。
_MAX_TRACKED_KEYS = 10_000


def _prune_expired_locked(now: float) -> None:
    expired = [
        key for key, events in _rate_buckets.items()
        if not events or now - events[-1] > RATE_LIMITS.get(key[1], (0, 60.0))[1]
    ]
    for key in expired:
        del _rate_buckets[key]


def check_rate_limit(client_ip: str, bucket: str) -> bool:
    limit = RATE_LIMITS.get(bucket)
    if not limit:
        return True
    max_requests, window_seconds = limit
    now = time.monotonic()
    key = (client_ip, bucket)
    with _rate_lock:
        if len(_rate_buckets) > _MAX_TRACKED_KEYS:
            _prune_expired_locked(now)
        events = _rate_buckets.setdefault(key, deque())
        cutoff = now - window_seconds
        while events and events[0] <= cutoff:
            events.popleft()
        if len(events) >= max_requests:
            return False
        events.append(now)
        return True


def reset_rate_limits() -> None:
    """Clear all rate-limit state. Intended for tests."""
    with _rate_lock:
        _rate_buckets.clear()


def _origin_host(origin_or_referer: str) -> str:
    if not origin_or_referer:
        return ""
    parsed = urlparse(origin_or_referer)
    return parsed.netloc or ""


def check_csrf(origin_header: str, referer_header: str, host_header: str) -> bool:
    """Return True if the request passes the CSRF check.

    Defense-in-depth on top of SameSite=Lax cookies: if the browser sent an
    Origin or Referer, it must match the server's host. Non-browser clients
    (no Origin and no Referer) are allowed when CSRF_ALLOW_MISSING_ORIGIN is
    on, so backend scripts and integration tests keep working.
    """
    if not CSRF_ENFORCE:
        return True
    if not origin_header and not referer_header:
        return CSRF_ALLOW_MISSING_ORIGIN
    expected = (host_header or "").strip().lower()
    if not expected:
        # Without a Host header we cannot verify; reject for safety.
        return False
    origin_host = _origin_host(origin_header).lower()
    referer_host = _origin_host(referer_header).lower()
    if origin_host and origin_host == expected:
        return True
    if referer_host and referer_host == expected:
        return True
    return False
