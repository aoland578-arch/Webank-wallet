"""
GNN 推理入口（子进程模式）。

由 server.py 通过 subprocess 调用，运行在 anti_fraud conda 环境中：
  /opt/anaconda3/envs/anti_fraud/bin/python3 gnn_infer.py <enterprise_id>

从 stdin 读取 case JSON（由 gnn_bridge.enterprise_to_case 生成），
将推理结果以单行 JSON 写入 stdout：
  {"score": 72.3, "sub_scores": [18.5, 20.1, 17.2, 16.5], "ok": true}

失败时输出：
  {"ok": false, "error": "..."}

注意：此脚本需要 torch + torch_geometric，不能用 base Python 运行。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GNN_MODEL_DIR  = ROOT / "gnn" / "model"
GNN_DATA_DIR   = ROOT / "gnn" / "data_gen"
CHECKPOINT     = ROOT / "gnn" / "model" / "stage4_final.pt"

sys.path.insert(0, str(GNN_MODEL_DIR))
sys.path.insert(0, str(GNN_DATA_DIR))


def run(case: dict) -> dict:
    import torch
    from graph_spec import case_to_graph_spec, spec_to_heterodata
    from model import RiskScoreGNN

    # 找 checkpoint
    ckpt_path = CHECKPOINT
    if not ckpt_path.exists():
        ckpt_path = ROOT / "gnn" / "model" / "stage4_checkpoint.pt"
    if not ckpt_path.exists():
        ckpt_path = ROOT / "gnn" / "checkpoint.pt"
    if not ckpt_path.exists():
        return {"ok": False, "error": f"找不到 checkpoint，已查找路径: {CHECKPOINT}"}

    ckpt = torch.load(str(ckpt_path), map_location="cpu", weights_only=False)
    model = RiskScoreGNN()
    model.load_state_dict(ckpt["model"])
    model.eval()

    spec  = case_to_graph_spec(case)
    graph = spec_to_heterodata(spec)

    # 过滤空边
    edge_dict = {k: v for k, v in graph.edge_index_dict.items() if v.size(1) > 0}

    with torch.no_grad():
        score_t, sub_t = model(graph.x_dict, edge_dict)

    score = float(score_t[0]) * 100.0
    sub   = [round(float(v) * 25.0, 1) for v in sub_t[0]]

    return {
        "ok": True,
        "score": round(score, 1),
        "sub_scores": {
            "identity":    sub[0],
            "business":    sub[1],
            "loan_logic":  sub[2],
            "cooperation": sub[3],
        },
        "recommendation": _score_to_recommendation(score),
    }


def _score_to_recommendation(score: float) -> str:
    if score >= 75:
        return "approve"
    if score >= 50:
        return "review"
    if score >= 30:
        return "review"
    return "reject"


if __name__ == "__main__":
    try:
        raw = sys.stdin.read()
        case = json.loads(raw)
        result = run(case)
    except Exception as exc:
        result = {"ok": False, "error": str(exc)}
    print(json.dumps(result, ensure_ascii=False))
