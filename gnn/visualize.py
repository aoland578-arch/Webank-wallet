"""
风控 GNN 可视化：
  图一 — 三个典型案例的风险评分雷达图（欺诈 / 灰色地带 / 正常）
  图二 — 模型预测分 vs 实际分散点图（准确性展示）

运行：
  /opt/anaconda3/envs/anti_fraud/bin/python3 visualize.py
"""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

ROOT      = Path(__file__).resolve().parent.parent
RAW_DIR   = ROOT / "gnn" / "data" / "raw"
GRAPH_DIR = ROOT / "gnn" / "data" / "graphs"
OUT_DIR   = ROOT / "gnn" / "output"
OUT_DIR.mkdir(exist_ok=True)

plt.rcParams["font.family"] = ["PingFang SC", "Heiti TC", "SimHei",
                                "Arial Unicode MS", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False


# ── 工具 ──────────────────────────────────────────────────────────────────────

def load_cases(n: int = 5000, seed: int = 42) -> list[dict]:
    paths = sorted(RAW_DIR.glob("*.json"))
    random.Random(seed).shuffle(paths)
    cases = []
    for p in paths[:n]:
        try:
            cases.append(json.loads(p.read_text(encoding="utf-8")))
        except Exception:
            pass
    return cases


def pick_representatives(cases: list[dict]) -> tuple[dict, dict, dict]:
    """挑选欺诈 / 灰色地带 / 正常三个典型案例。"""
    fraud    = [c for c in cases if c["labels"]["score"] <= 25]
    grey     = [c for c in cases if 40 <= c["labels"]["score"] <= 60]
    normal   = [c for c in cases if c["labels"]["score"] >= 78]

    def _best(bucket: list[dict], target: float) -> dict:
        return min(bucket, key=lambda c: abs(c["labels"]["score"] - target))

    return (
        _best(fraud,  15.0) if fraud  else cases[0],
        _best(grey,   50.0) if grey   else cases[len(cases)//2],
        _best(normal, 88.0) if normal else cases[-1],
    )


# ── 图一：雷达图 ──────────────────────────────────────────────────────────────

DIMS   = ["身份\n一致性", "经营\n真实性", "申请\n逻辑", "配合度\n材料"]
COLORS = ["#E74C3C", "#F39C12", "#27AE60"]
FILLS  = ["#FADBD8", "#FDEBD0", "#D5F5E3"]
LABELS = ["⚠ 欺诈案例", "◐ 灰色地带", "✓ 正常申请"]


def _radar(ax: plt.Axes, sub_scores: list[float], color: str, fill: str,
           title: str, score: float, fraud_type: str) -> None:
    n = len(DIMS)
    angles = np.linspace(0, 2 * np.pi, n, endpoint=False).tolist()
    angles += angles[:1]
    vals = [min(v * 25, 25) for v in sub_scores] + [min(sub_scores[0] * 25, 25)]

    ax.set_theta_offset(np.pi / 2)
    ax.set_theta_direction(-1)
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(DIMS, fontsize=10, fontweight="bold")
    ax.set_ylim(0, 25)
    ax.set_yticks([5, 10, 15, 20, 25])
    ax.set_yticklabels(["5", "10", "15", "20", "25"], fontsize=7, color="#888")
    ax.grid(color="#ddd", linestyle="--", linewidth=0.8)

    ax.plot(angles, vals, color=color, linewidth=2.5, zorder=3)
    ax.fill(angles, vals, color=fill, alpha=0.85, zorder=2)

    # 数值标注
    for angle, val in zip(angles[:-1], vals[:-1]):
        x = (val + 3.5) * np.cos(angle - np.pi / 2)
        y = (val + 3.5) * np.sin(angle - np.pi / 2)
        ax.annotate(f"{val:.0f}", xy=(angle, val), xytext=(x/25, y/25),
                    textcoords="axes fraction", ha="center", va="center",
                    fontsize=9, color=color, fontweight="bold",
                    xycoords="data")

    TYPE_MAP = {
        "identity_fraud": "身份欺诈", "business_fraud": "经营造假",
        "purpose_fraud": "用途虚报", "document_fraud": "材料伪造",
        "multi_fraud": "复合欺诈", "no_fraud": "正常申请",
        "minor_issues": "轻微瑕疵",
    }
    ft_label = TYPE_MAP.get(fraud_type, fraud_type)
    ax.set_title(f"{title}\n总分：{score:.0f} / 100\n({ft_label})",
                 fontsize=12, fontweight="bold", color=color, pad=18)


def plot_radar(cases_trio: tuple[dict, dict, dict]) -> Path:
    fig, axes = plt.subplots(1, 3, figsize=(15, 5.5),
                             subplot_kw={"projection": "polar"})
    fig.patch.set_facecolor("#F8F9FA")

    for ax, case, color, fill, label in zip(
        axes, cases_trio, COLORS, FILLS, LABELS
    ):
        lbl  = case["labels"]
        sub  = lbl["sub_scores_norm"] if "sub_scores_norm" in lbl else [
            lbl["sub_scores"].get(k, 0) / 25
            for k in ["identity", "business", "loan_logic", "cooperation"]
        ]
        _radar(ax, sub, color, fill, label, lbl["score"], case["fraud_type"])

    fig.suptitle("风控 GNN · 典型案例风险评分雷达图",
                 fontsize=16, fontweight="bold", y=1.02, color="#2C3E50")

    note = ("评分维度：身份一致性（25分）· 经营真实性（25分）"
            "· 申请逻辑合理性（25分）· 配合度与材料完整性（25分）\n"
            "总分 0-100，越高越可信。红色 = 高风险，绿色 = 低风险。")
    fig.text(0.5, -0.04, note, ha="center", fontsize=9, color="#555",
             style="italic")

    plt.tight_layout()
    out = OUT_DIR / "radar_chart.png"
    fig.savefig(out, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    print(f"✓ 雷达图保存：{out}")
    return out


# ── 图二：预测 vs 实际散点图 ──────────────────────────────────────────────────

def plot_scatter(cases: list[dict], checkpoint: Path) -> Path | None:
    try:
        import torch
        sys.path.insert(0, str(ROOT / "gnn" / "model"))
        sys.path.insert(0, str(ROOT / "gnn" / "data_gen"))
        from model import RiskScoreGNN
        from graph_spec import case_to_graph_spec, spec_to_heterodata
    except ImportError as e:
        print(f"跳过散点图（缺少依赖）: {e}")
        return None

    ckpt = torch.load(checkpoint, map_location="cpu", weights_only=False)
    model = RiskScoreGNN()
    model.load_state_dict(ckpt["model"])
    model.eval()

    sample = random.Random(99).sample(cases, min(500, len(cases)))
    actuals, preds, fraud_types = [], [], []

    with torch.no_grad():
        for case in sample:
            try:
                spec  = case_to_graph_spec(case)
                graph = spec_to_heterodata(spec)
                edge_dict = {k: v for k, v in graph.edge_index_dict.items()
                             if v.size(1) > 0}
                p_score, _ = model(graph.x_dict, edge_dict)
                preds.append(float(p_score[0]) * 100)
                actuals.append(case["labels"]["score"])
                fraud_types.append(case["fraud_type"])
            except Exception:
                pass

    if not preds:
        return None

    actuals = np.array(actuals)
    preds   = np.array(preds)
    mae     = np.mean(np.abs(actuals - preds))

    TYPE_COLORS = {
        "identity_fraud": "#E74C3C", "multi_fraud": "#C0392B",
        "business_fraud": "#E67E22", "document_fraud": "#F39C12",
        "purpose_fraud":  "#F1C40F", "minor_issues":  "#2ECC71",
        "no_fraud":       "#27AE60",
    }
    TYPE_LABELS = {
        "identity_fraud": "身份欺诈", "multi_fraud": "复合欺诈",
        "business_fraud": "经营造假", "document_fraud": "材料伪造",
        "purpose_fraud":  "用途虚报", "minor_issues":  "轻微瑕疵",
        "no_fraud":       "正常申请",
    }

    fig, ax = plt.subplots(figsize=(8, 7))
    fig.patch.set_facecolor("#F8F9FA")
    ax.set_facecolor("#FDFDFD")

    for ft in TYPE_COLORS:
        idx = [i for i, t in enumerate(fraud_types) if t == ft]
        if idx:
            ax.scatter(actuals[idx], preds[idx],
                       c=TYPE_COLORS[ft], label=TYPE_LABELS[ft],
                       alpha=0.65, s=28, edgecolors="white", linewidths=0.4)

    # 对角线（完美预测）
    lim = [0, 100]
    ax.plot(lim, lim, "--", color="#AAA", linewidth=1.5, label="完美预测线")
    ax.fill_between(lim, [x - 10 for x in lim], [x + 10 for x in lim],
                    alpha=0.07, color="#3498DB", label="±10分误差带")

    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.set_xlabel("实际风险分（AI 评分员打分）", fontsize=12)
    ax.set_ylabel("GNN 预测分", fontsize=12)
    ax.set_title(f"风控 GNN · 模型预测准确性\n"
                 f"测试样本 {len(preds)} 个  ·  平均误差 {mae:.1f} 分",
                 fontsize=13, fontweight="bold", color="#2C3E50")
    ax.legend(loc="upper left", fontsize=9, framealpha=0.9)
    ax.grid(True, alpha=0.3, linestyle="--")

    # 角落注释
    ax.text(98, 3, f"MAE = {mae:.1f} 分\n（越小越准）",
            ha="right", va="bottom", fontsize=10, color="#555",
            bbox=dict(boxstyle="round,pad=0.4", facecolor="white",
                      edgecolor="#CCC", alpha=0.9))

    plt.tight_layout()
    out = OUT_DIR / "scatter_accuracy.png"
    fig.savefig(out, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    print(f"✓ 散点图保存：{out}")
    return out


# ── main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    print(f"加载案例数据（{RAW_DIR}）...")
    cases = load_cases(5000)
    print(f"已加载 {len(cases)} 个案例")

    trio = pick_representatives(cases)
    print(f"典型案例分数：{[c['labels']['score'] for c in trio]}")

    plot_radar(trio)

    ckpt = ROOT / "gnn" / "model" / "stage4_checkpoint.pt"
    if not ckpt.exists():
        ckpt = ROOT / "gnn" / "model" / "checkpoint.pt"
    plot_scatter(cases, ckpt)

    print(f"\n图表已保存至：{OUT_DIR}")


if __name__ == "__main__":
    main()
