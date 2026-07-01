"""
批量生成 GNN 训练数据。

用法：
  # 生成 100 个案例（pipeline 验证）
  python3 batch_generate.py --total 100

  # 生成 20000 个案例（完整数据集），8并发
  python3 batch_generate.py --total 20000 --concurrency 8

  # 续跑（跳过 raw/ 中已有的案例）
  python3 batch_generate.py --total 20000 --resume

输出：
  gnn/data/raw/<case_id>.json   — 原始案例
  gnn/data/graphs/<case_id>.pt  — PyG HeteroData 图
  gnn/data/stats.json           — 实时统计（分数分布、欺诈类型分布）
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import RAW_DIR, GRAPH_DIR, CONCURRENCY
from generate_case import generate_case, FRAUD_TYPES
from graph_spec import case_to_graph_spec


# ── 统计 ──────────────────────────────────────────────────────────────────────

class Stats:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.success = 0
        self.failed = 0
        self.scores: list[float] = []
        self.fraud_counts: dict[str, int] = {ft: 0 for ft in FRAUD_TYPES}

    def record(self, case: dict) -> None:
        with self._lock:
            self.success += 1
            score = case.get("labels", {}).get("score", 0.0)
            self.scores.append(float(score))
            ft = case.get("fraud_type", "unknown")
            self.fraud_counts[ft] = self.fraud_counts.get(ft, 0) + 1

    def record_fail(self) -> None:
        with self._lock:
            self.failed += 1

    def to_dict(self) -> dict:
        scores = self.scores
        return {
            "success": self.success,
            "failed": self.failed,
            "score_mean": sum(scores) / len(scores) if scores else 0.0,
            "score_min": min(scores) if scores else 0.0,
            "score_max": max(scores) if scores else 0.0,
            "score_buckets": {
                "0-20":   sum(1 for s in scores if s < 20),
                "20-40":  sum(1 for s in scores if 20 <= s < 40),
                "40-60":  sum(1 for s in scores if 40 <= s < 60),
                "60-80":  sum(1 for s in scores if 60 <= s < 80),
                "80-100": sum(1 for s in scores if s >= 80),
            },
            "fraud_type_counts": self.fraud_counts,
        }

    def save(self, path: Path) -> None:
        with self._lock:
            path.write_text(json.dumps(self.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")


# ── worker ────────────────────────────────────────────────────────────────────

def _process_one(task_id: int, stats: Stats) -> tuple[bool, str]:
    """生成一个案例并保存，返回 (success, case_id)。"""
    try:
        case = generate_case()
        case_id = case["case_id"]

        # 保存原始 JSON
        raw_path = RAW_DIR / f"{case_id}.json"
        raw_path.write_text(json.dumps(case, ensure_ascii=False, indent=2), encoding="utf-8")

        # 转换为图规格 JSON（无 PyG 依赖，训练时再转 HeteroData）
        spec = case_to_graph_spec(case)
        graph_path = GRAPH_DIR / f"{case_id}.json"
        graph_path.write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")

        stats.record(case)
        return True, case_id
    except Exception as e:  # noqa: BLE001
        stats.record_fail()
        return False, str(e)


# ── 进度打印 ──────────────────────────────────────────────────────────────────

def _progress_bar(done: int, total: int, success: int, failed: int, elapsed: float) -> str:
    pct = done / total * 100 if total > 0 else 0
    rate = done / elapsed if elapsed > 0 else 0
    eta  = (total - done) / rate if rate > 0 else 0
    bar_len = 30
    filled = int(bar_len * done / total) if total > 0 else 0
    bar = "█" * filled + "░" * (bar_len - filled)
    return (
        f"\r[{bar}] {done}/{total} ({pct:.1f}%)  "
        f"✓{success} ✗{failed}  "
        f"{rate:.1f}案例/s  ETA {eta/60:.1f}min"
    )


# ── main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="批量生成 GNN 训练数据")
    parser.add_argument("--total",       type=int, default=100,        help="目标案例总数")
    parser.add_argument("--concurrency", type=int, default=CONCURRENCY, help="并发线程数")
    parser.add_argument("--resume",      action="store_true",           help="续跑，跳过已生成的案例")
    args = parser.parse_args()

    # 统计已有案例数
    existing = {p.stem for p in RAW_DIR.glob("*.json")}
    if args.resume:
        already = len(existing)
        need = max(0, args.total - already)
        print(f"续跑模式：已有 {already} 个案例，还需生成 {need} 个")
    else:
        need = args.total

    if need == 0:
        print("已达到目标数量，无需生成。")
        return

    stats = Stats()
    stats_path = ROOT / "data" / "stats.json"
    start_time = time.time()
    done = 0

    print(f"开始生成 {need} 个案例（并发={args.concurrency}）...\n")

    with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        futures = [pool.submit(_process_one, i, stats) for i in range(need)]
        for future in as_completed(futures):
            done += 1
            success, info = future.result()
            elapsed = time.time() - start_time

            if not success:
                print(f"\n  ✗ 生成失败: {info}", flush=True)

            # 进度条
            print(
                _progress_bar(done, need, stats.success, stats.failed, elapsed),
                end="", flush=True
            )

            # 每 50 个案例保存一次统计
            if done % 50 == 0:
                stats.save(stats_path)

    # 最终统计
    stats.save(stats_path)
    print()  # 换行
    total_time = time.time() - start_time
    s = stats.to_dict()
    print(f"\n{'='*50}")
    print(f"完成！用时 {total_time/60:.1f} 分钟")
    print(f"成功: {s['success']}  失败: {s['failed']}")
    print(f"分数分布: {s['score_buckets']}")
    print(f"欺诈类型: {s['fraud_type_counts']}")
    print(f"均分: {s['score_mean']:.1f}  [min={s['score_min']:.1f}, max={s['score_max']:.1f}]")
    print(f"数据保存在: {RAW_DIR.parent}")


if __name__ == "__main__":
    main()
