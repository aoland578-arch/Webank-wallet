"""语音中继并发通话槽位：满了拒接、释放后可再接，计数不下穿。

Run from the project root (anaconda python, 依赖 websockets):
    python3 -m unittest tests.test_relay_call_slots -v
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
    str(Path(tempfile.mkdtemp(prefix="wewallet-test-relay-")) / "test.sqlite"),
)

sys.path.insert(0, str(REPO_ROOT / "ui"))

try:
    import voicecall_relay as relay
except ImportError:  # 缺 websockets 依赖的环境跳过整组测试
    relay = None


@unittest.skipIf(relay is None, "websockets not installed")
class CallSlotTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._max = relay.MAX_CONCURRENT_CALLS
        relay.MAX_CONCURRENT_CALLS = 2
        relay._active_calls = 0

    def tearDown(self) -> None:
        relay.MAX_CONCURRENT_CALLS = self._max
        relay._active_calls = 0

    def test_slots_exhaust_and_recover(self) -> None:
        self.assertTrue(relay._acquire_call_slot())
        self.assertTrue(relay._acquire_call_slot())
        self.assertFalse(relay._acquire_call_slot(), "超过上限必须拒接")
        relay._release_call_slot()
        self.assertTrue(relay._acquire_call_slot(), "释放后应能再接")

    def test_release_never_goes_negative(self) -> None:
        relay._release_call_slot()
        relay._release_call_slot()
        self.assertEqual(relay._active_calls, 0)
        # 计数没有被多次释放破坏：仍然精确容纳 2 路。
        self.assertTrue(relay._acquire_call_slot())
        self.assertTrue(relay._acquire_call_slot())
        self.assertFalse(relay._acquire_call_slot())


if __name__ == "__main__":
    unittest.main()
