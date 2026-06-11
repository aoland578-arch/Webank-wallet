"""网关进程池上限：满了驱逐最久未用且空闲的；全忙快速失败（GatewayPoolBusy）。

这是 100 并发场景的核心护栏——没有上限，每个企业一个 Hermes 子进程会把内存打爆。

Run from the project root:
    python3 -m unittest tests.test_gateway_pool -v
"""
from __future__ import annotations

import os
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("WEWALLET_AUTH_SECRET", "test-secret")
os.environ.setdefault(
    "WEWALLET_DB",
    str(Path(tempfile.mkdtemp(prefix="wewallet-test-pool-")) / "test.sqlite"),
)

sys.path.insert(0, str(REPO_ROOT / "ui"))

import gateway  # noqa: E402

ENT_A = "ent_" + "a" * 12
ENT_B = "ent_" + "b" * 12
ENT_C = "ent_" + "c" * 12


class GatewayPoolTestCase(unittest.TestCase):
    def setUp(self) -> None:
        gateway.GATEWAYS.clear()
        self._max = gateway.MAX_ACTIVE_GATEWAYS
        gateway.MAX_ACTIVE_GATEWAYS = 2
        # 不碰真实 app_data：home 目录只是个占位路径，测试里不会拉起子进程。
        self._home_patch = mock.patch.object(
            gateway,
            "ensure_enterprise_hermes_home",
            side_effect=lambda eid: Path(tempfile.mkdtemp(prefix="hermes-home-")),
        )
        self._home_patch.start()

    def tearDown(self) -> None:
        self._home_patch.stop()
        gateway.MAX_ACTIVE_GATEWAYS = self._max
        gateway.GATEWAYS.clear()

    def test_lru_idle_gateway_evicted_when_full(self) -> None:
        g_a = gateway.gateway_for_enterprise(ENT_A)
        gateway.gateway_for_enterprise(ENT_B)
        g_a._last_used_at = time.monotonic() - 999  # A 最久未用

        gateway.gateway_for_enterprise(ENT_C)
        self.assertEqual(len(gateway.GATEWAYS), 2)
        self.assertNotIn(ENT_A, gateway.GATEWAYS, "最久未用的空闲网关应被驱逐")
        self.assertIn(ENT_B, gateway.GATEWAYS)
        self.assertIn(ENT_C, gateway.GATEWAYS)

    def test_busy_gateway_not_evicted(self) -> None:
        g_a = gateway.gateway_for_enterprise(ENT_A)
        gateway.gateway_for_enterprise(ENT_B)
        g_a._last_used_at = time.monotonic() - 999
        # A 虽然最旧但在跑一轮（持有轮次锁）→ 驱逐 B。
        self.assertTrue(g_a._turn_lock(f"chat:{ENT_A}").acquire(blocking=False))
        try:
            gateway.gateway_for_enterprise(ENT_C)
            self.assertIn(ENT_A, gateway.GATEWAYS, "忙的网关绝不能被驱逐")
            self.assertNotIn(ENT_B, gateway.GATEWAYS)
        finally:
            g_a._turn_lock(f"chat:{ENT_A}").release()

    def test_pool_full_all_busy_raises(self) -> None:
        g_a = gateway.gateway_for_enterprise(ENT_A)
        g_b = gateway.gateway_for_enterprise(ENT_B)
        self.assertTrue(g_a._turn_lock("chat:a").acquire(blocking=False))
        self.assertTrue(g_b._turn_lock("chat:b").acquire(blocking=False))
        try:
            with self.assertRaises(gateway.GatewayPoolBusy):
                gateway.gateway_for_enterprise(ENT_C)
        finally:
            g_a._turn_lock("chat:a").release()
            g_b._turn_lock("chat:b").release()

    def test_existing_gateway_returned_even_when_pool_full(self) -> None:
        g_a = gateway.gateway_for_enterprise(ENT_A)
        g_b = gateway.gateway_for_enterprise(ENT_B)
        self.assertTrue(g_a._turn_lock("chat:a").acquire(blocking=False))
        self.assertTrue(g_b._turn_lock("chat:b").acquire(blocking=False))
        try:
            # 已在池里的企业不受池满影响。
            self.assertIs(gateway.gateway_for_enterprise(ENT_A), g_a)
        finally:
            g_a._turn_lock("chat:a").release()
            g_b._turn_lock("chat:b").release()

    def test_busy_gateway_not_swept_as_idle(self) -> None:
        g_a = gateway.gateway_for_enterprise(ENT_A)
        g_a._last_used_at = time.monotonic() - 999
        self.assertTrue(g_a._turn_lock("chat:a").acquire(blocking=False))
        try:
            self.assertFalse(g_a.is_idle(60.0), "在途轮次的网关不该被 idle sweep 杀掉")
        finally:
            g_a._turn_lock("chat:a").release()
        self.assertTrue(g_a.is_idle(60.0))


if __name__ == "__main__":
    unittest.main()
