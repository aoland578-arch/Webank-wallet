from __future__ import annotations

import os
from pathlib import Path

# ── API ──────────────────────────────────────────────────────────────────────
API_KEY   = os.environ.get("MIMO_API_KEY", "tp-cm7haicozzdtzsszxzbt2cetyv87rrqgzuawfh4s3odvrgb7")
BASE_URL  = os.environ.get("MIMO_BASE_URL", "https://token-plan-cn.xiaomimimo.com/v1")
MODEL     = os.environ.get("MIMO_MODEL", "mimo-v2.5-pro")

# ── paths ────────────────────────────────────────────────────────────────────
ROOT      = Path(__file__).resolve().parent.parent
RAW_DIR   = ROOT / "data" / "raw"
GRAPH_DIR = ROOT / "data" / "graphs"
RAW_DIR.mkdir(parents=True, exist_ok=True)
GRAPH_DIR.mkdir(parents=True, exist_ok=True)

# ── generation ───────────────────────────────────────────────────────────────
CONCURRENCY     = 5     # parallel API calls (avoid 429 rate limit)
REQUEST_TIMEOUT = 120   # seconds per call
MAX_RETRIES     = 4

# ── score distribution (approximate) ─────────────────────────────────────────
# Each bucket: (score_min, score_max, weight)
SCORE_BUCKETS = [
    (0,  20,  0.12),   # definite fraud / reject
    (20, 35,  0.15),   # high risk
    (35, 50,  0.18),   # elevated risk
    (50, 65,  0.20),   # grey zone
    (65, 80,  0.20),   # minor issues
    (80, 100, 0.15),   # normal / approve
]
