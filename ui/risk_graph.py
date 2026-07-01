from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
GRAPH_DIR = ROOT / "gnn" / "data" / "graphs"

TYPE_LABELS = {
    "application": "贷款申请",
    "person": "经营者",
    "enterprise": "企业",
    "claim": "口述信息",
    "document": "申请材料",
    "video_call": "视频核身",
    "risk_signal": "风险信号",
    "transaction": "经营流水",
}

RELATION_LABELS = {
    "controls": "控制",
    "claims": "声称",
    "changed_to": "变更为",
    "reveals": "发现",
    "supports": "支撑",
    "blocks": "影响",
    "belongs_to": "归属",
    "applies_to": "申请",
}

RECOMMENDATION_LABELS = {
    "approve": "建议通过",
    "approve_with_caution": "审慎通过",
    "approve_with_conditions": "附条件通过",
    "review": "人工复核",
    "reject": "建议拒绝",
}

FRAUD_TYPE_LABELS = {
    "identity_fraud": "身份欺诈",
    "business_fraud": "经营造假",
    "purpose_fraud": "用途虚报",
    "document_fraud": "材料伪造",
    "multi_fraud": "复合欺诈",
    "minor_issues": "轻微瑕疵",
    "no_fraud": "正常申请",
}


def _read_graph(path: Path) -> dict[str, Any] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict) or not data.get("nodes") or not data.get("edges"):
        return None
    return data


def _score_bucket(score: float) -> str:
    if score < 35:
        return "high"
    if score < 70:
        return "medium"
    return "low"


def _risk_level(node_type: str, features: list[float], labels: dict[str, Any]) -> float:
    if node_type == "application":
        return 1.0 - float(labels.get("score_norm", 0.5))
    if node_type == "risk_signal":
        return min(max(float(features[0] if features else 0.0), 0.0), 1.0)
    if node_type == "document":
        submitted, quality, authentic = (features + [0.0, 0.0, 0.0])[:3]
        return min(max((1.0 - quality) * 0.45 + (1.0 - authentic) * 0.45 + (1.0 - submitted) * 0.1, 0.0), 1.0)
    if node_type == "person":
        return min(max(float(features[1] if len(features) > 1 else 0.0), 0.0), 1.0)
    if node_type == "enterprise":
        ratio = float(features[3] if len(features) > 3 else 1.0)
        license_risk = 1.0 - float(features[6] if len(features) > 6 else 1.0)
        tax_risk = 1.0 - float(features[7] if len(features) > 7 else 1.0)
        return min(max((max(ratio - 1.0, 0.0) / 4.0) * 0.5 + license_risk * 0.25 + tax_risk * 0.25, 0.0), 1.0)
    if node_type == "video_call":
        high = float(features[1] if len(features) > 1 else 0.0)
        medium = float(features[2] if len(features) > 2 else 0.0)
        mismatch = 1.0 - float(features[3] if len(features) > 3 else 1.0)
        return min(max(high * 0.5 + medium * 0.2 + mismatch * 0.3, 0.0), 1.0)
    if node_type == "claim":
        unreasonable = 1.0 - float(features[2] if len(features) > 2 else 1.0)
        return min(max(unreasonable, 0.0), 1.0)
    return 0.18


def _node_label(node_type: str, index: int, features: list[float]) -> str:
    base = TYPE_LABELS.get(node_type, node_type)
    if node_type == "application":
        return base
    if node_type == "enterprise":
        return "企业主体"
    if node_type == "person":
        return "实际经营者"
    if node_type == "risk_signal":
        level = float(features[0] if features else 0.0)
        if level >= 0.66:
            return "高危信号"
        if level >= 0.33:
            return "中危信号"
        return "低危信号"
    return f"{base} {index + 1}"


def _node_detail(node_type: str, features: list[float]) -> str:
    if node_type == "application":
        return f"期限 {features[1]:.0f} 个月，变更 {features[3]:.0f} 次"
    if node_type == "enterprise":
        return f"经营 {features[0]:.0f} 年，收入偏离约 {features[3]:.1f} 倍"
    if node_type == "document":
        quality = features[1] if len(features) > 1 else 0.0
        authentic = "真实" if len(features) > 2 and features[2] >= 0.5 else "存疑"
        return f"清晰度 {quality:.0%}，真实性{authentic}"
    if node_type == "video_call":
        return f"信号 {features[0]:.0f} 个，高危 {features[1]:.0f} 个"
    if node_type == "transaction":
        return f"交易笔数 {features[1]:.0f}"
    if node_type == "claim":
        return f"第 {features[1]:.0f} 轮提及"
    if node_type == "risk_signal":
        return f"风险强度 {float(features[0] if features else 0.0):.0%}"
    return TYPE_LABELS.get(node_type, node_type)


def list_risk_graph_cases(limit: int = 120) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    for path in sorted(GRAPH_DIR.glob("*.json")):
        graph = _read_graph(path)
        if not graph:
            continue
        labels = graph.get("labels") or {}
        score = float(labels.get("score", 50.0))
        cases.append({
            "case_id": graph.get("case_id") or path.stem,
            "score": score,
            "bucket": _score_bucket(score),
            "recommendation": labels.get("recommendation", "review"),
            "recommendation_label": RECOMMENDATION_LABELS.get(labels.get("recommendation", ""), labels.get("recommendation", "review")),
            "fraud_type": graph.get("fraud_type", ""),
            "fraud_type_label": FRAUD_TYPE_LABELS.get(graph.get("fraud_type", ""), graph.get("fraud_type", "未知")),
        })
        if len(cases) >= limit:
            break
    return cases


def _pick_case(case_id: str = "", bucket: str = "") -> dict[str, Any]:
    best: tuple[float, Path] | None = None
    for path in sorted(GRAPH_DIR.glob("*.json")):
        graph = _read_graph(path)
        if not graph:
            continue
        graph_case_id = str(graph.get("case_id") or path.stem)
        if case_id and graph_case_id == case_id:
            return graph
        if case_id:
            continue
        labels = graph.get("labels") or {}
        score = float(labels.get("score", 50.0))
        score_bucket = _score_bucket(score)
        if bucket and bucket != score_bucket:
            continue
        target = {"high": 18.0, "medium": 55.0, "low": 86.0}.get(bucket, 42.0)
        rank = abs(score - target)
        if best is None or rank < best[0]:
            best = (rank, path)
    if best:
        graph = _read_graph(best[1])
        if graph:
            return graph
    raise FileNotFoundError("没有可用的 GNN 图谱样本")


def build_risk_graph_payload(case_id: str = "", bucket: str = "") -> dict[str, Any]:
    graph = _pick_case(case_id=case_id, bucket=bucket)
    labels = graph.get("labels") or {}
    nodes: list[dict[str, Any]] = []
    node_lookup: dict[tuple[str, int], str] = {}

    for node_type, rows in (graph.get("nodes") or {}).items():
        if not isinstance(rows, list):
            continue
        for index, row in enumerate(rows):
            features = row if isinstance(row, list) else []
            node_id = f"{node_type}:{index}"
            node_lookup[(node_type, index)] = node_id
            risk = _risk_level(node_type, features, labels)
            nodes.append({
                "id": node_id,
                "type": node_type,
                "type_label": TYPE_LABELS.get(node_type, node_type),
                "label": _node_label(node_type, index, features),
                "detail": _node_detail(node_type, features),
                "risk": round(risk, 3),
                "size": 18 + min(risk, 1.0) * 12 + (6 if node_type in {"application", "enterprise"} else 0),
            })

    edges: list[dict[str, Any]] = []
    for edge_key, pair in (graph.get("edges") or {}).items():
        if not isinstance(pair, list) or len(pair) != 2:
            continue
        try:
            src_type, relation, dst_type = edge_key.split("__", 2)
        except ValueError:
            continue
        src_indexes, dst_indexes = pair
        for i, (src_index, dst_index) in enumerate(zip(src_indexes, dst_indexes)):
            source = node_lookup.get((src_type, int(src_index)))
            target = node_lookup.get((dst_type, int(dst_index)))
            if not source or not target:
                continue
            edges.append({
                "id": f"{edge_key}:{i}",
                "source": source,
                "target": target,
                "relation": relation,
                "label": RELATION_LABELS.get(relation, relation),
                "risk_flow": relation in {"reveals", "blocks", "applies_to"} or src_type == "risk_signal",
            })

    score = float(labels.get("score", 50.0))
    recommendation = labels.get("recommendation", "review")
    return {
        "case_id": graph.get("case_id", ""),
        "fraud_type": graph.get("fraud_type", ""),
        "fraud_type_label": FRAUD_TYPE_LABELS.get(graph.get("fraud_type", ""), graph.get("fraud_type", "未知")),
        "score": score,
        "risk_score": round(100.0 - score, 1),
        "bucket": _score_bucket(score),
        "recommendation": recommendation,
        "recommendation_label": RECOMMENDATION_LABELS.get(recommendation, recommendation),
        "sub_scores": labels.get("sub_scores_norm", []),
        "nodes": nodes,
        "edges": edges,
        "samples": list_risk_graph_cases(),
    }
