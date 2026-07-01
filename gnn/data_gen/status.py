"""
实时查看生成进度。
用法：python3 status.py
"""

import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
RAW_DIR  = DATA_DIR / "raw"
STATS_PATH = DATA_DIR / "stats.json"

n = len(list(RAW_DIR.glob("*.json")))
print(f"已生成: {n} / 20000  ({n/200:.1f}%)")

if STATS_PATH.exists():
    s = json.loads(STATS_PATH.read_text(encoding="utf-8"))
    print(f"成功: {s['success']}  失败: {s['failed']}")
    print(f"分值分布: {s['score_buckets']}")
    print(f"均分: {s['score_mean']:.1f}  [min={s['score_min']:.1f}, max={s['score_max']:.1f}]")
    print(f"欺诈类型: {s['fraud_type_counts']}")
