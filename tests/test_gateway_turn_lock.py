"""同一企业并发双发消息时，gateway 必须按会话串行（第二条快速失败）。

没有这把锁，两个线程会同时消费同一个事件队列，回复互相串台。

Run from the project root:
    python3 -m unittest tests.test_gateway_turn_lock -v
"""
from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("WEWALLET_AUTH_SECRET", "test-secret")
os.environ.setdefault(
    "WEWALLET_DB",
    str(Path(tempfile.mkdtemp(prefix="wewallet-test-gateway-")) / "test.sqlite"),
)

sys.path.insert(0, str(REPO_ROOT / "ui"))

from gateway import HermesTuiGateway  # noqa: E402


class TurnLockTestCase(unittest.TestCase):
    def test_second_submit_fails_fast_while_turn_in_flight(self) -> None:
        gateway = HermesTuiGateway(Path(tempfile.mkdtemp(prefix="hermes-home-")))
        # 模拟"上一轮还在跑"：持有该会话的轮次锁。
        lock = gateway._turn_lock("chat:ent_x")
        self.assertTrue(lock.acquire(blocking=False))
        try:
            # submit 在拿锁阶段就该失败（1s 超时），不会走到拉起子进程。
            with self.assertRaises(ValueError):
                gateway.submit("chat:ent_x", "你好")
        finally:
            lock.release()
        self.assertIsNone(gateway._proc, "拿锁失败时不应拉起网关子进程")

    def test_locks_are_per_session(self) -> None:
        gateway = HermesTuiGateway(Path(tempfile.mkdtemp(prefix="hermes-home-")))
        lock_a = gateway._turn_lock("chat:ent_a")
        lock_b = gateway._turn_lock("chat:ent_b")
        self.assertIsNot(lock_a, lock_b)
        self.assertIs(lock_a, gateway._turn_lock("chat:ent_a"))


if __name__ == "__main__":
    unittest.main()
