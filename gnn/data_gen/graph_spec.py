"""
将案例 JSON 转换为图规格 JSON（纯 Python，无 ML 依赖）。

图规格格式：
{
  "case_id": "...",
  "fraud_type": "...",
  "nodes": {
    "application": [[feat, ...], ...],
    "person":       [[feat, ...], ...],
    ...
  },
  "edges": {
    "person__controls__enterprise":   [[src,...], [dst,...]],
    "person__claims__claim":          [[src,...], [dst,...]],
    ...
  },
  "labels": {
    "score": 0-100,
    "score_norm": 0.0-1.0,
    "sub_scores_norm": [identity, business, loan_logic, cooperation],  # each /25
    "recommendation": "approve/review/reject"
  }
}

训练时用 spec_to_heterodata(spec) 转成 PyG HeteroData。
"""

from __future__ import annotations

import math
from typing import Any

INDUSTRY_LIST = ["餐饮", "零售", "制造", "服务业", "贸易", "建筑", "电商", "农业"]
RISK_LEVEL_MAP = {"low": 0, "medium": 1, "high": 2, "critical": 3}
DOC_QUALITY_MAP = {"clear": 1.0, "blurry": 0.4, "refused": 0.0}


def _bool(v: Any) -> float:
    if isinstance(v, bool): return 1.0 if v else 0.0
    if isinstance(v, (int, float)): return float(bool(v))
    if isinstance(v, str): return 1.0 if v.lower() in ("true","yes","1") else 0.0
    return 0.0


def _log(x: float) -> float:
    return math.log(max(float(x), 1.0))


def _onehot(value: str, vocab: list[str]) -> list[float]:
    return [1.0 if value == v else 0.0 for v in vocab]


# ── 节点特征 ──────────────────────────────────────────────────────────────────

def _feat_application(case: dict) -> list[float]:
    la = case.get("loan_application", {})
    hist = la.get("amount_history", [la.get("final_amount", 0)])
    changes = case.get("claim_changes", [])
    ov = case.get("open_verifications", [])
    high = sum(1 for x in ov if x.get("level") == "high")
    return [
        _log(la.get("final_amount", 0)),
        float(la.get("term_months", 0)),
        float(len(hist)),
        float(len(changes)),
        float(len(ov)),
        float(high),
    ]


def _feat_person(p: dict) -> list[float]:
    names = p.get("claimed_names", [])
    id_name = p.get("id_card_name", "")
    conflict = 1.0 if id_name and id_name not in names else 0.0
    return [
        float(len(names)),
        conflict,
        _bool(p.get("is_student")),
        _bool(p.get("is_legal_representative")),
        float(p.get("birth_year", 1990)) / 2030.0,
    ]


def _feat_enterprise(e: dict) -> list[float]:
    claimed = float(e.get("claimed_monthly_revenue", 0))
    actual  = float(e.get("actual_monthly_revenue", claimed))
    ratio   = min(claimed / max(actual, 1.0), 10.0)
    return [
        float(e.get("established_years", 0)),
        _log(claimed),
        _log(actual),
        ratio,
        float(e.get("employee_count", 0)),
        _bool(e.get("has_license")),
        _bool(e.get("license_authentic")),
        _bool(e.get("has_tax_record")),
        *_onehot(e.get("tax_grade") or "", ["A","B","C","D",""]),
        *_onehot(e.get("industry",""), INDUSTRY_LIST),
    ]


def _feat_claim(change: dict, field_idx: int) -> list[float]:
    return [
        float(field_idx),
        float(change.get("turn", 0)),
        _bool(change.get("is_reasonable")),
        1.0 if change.get("explanation") else 0.0,
    ]


def _feat_document(doc: dict) -> list[float]:
    q = DOC_QUALITY_MAP.get(doc.get("quality","clear"), 0.5)
    return [_bool(doc.get("submitted")), q, _bool(doc.get("authentic"))]


def _feat_video_call(vc: dict) -> list[float]:
    sigs = vc.get("risk_signals", [])
    high = sum(1 for s in sigs if s.get("level") == "high")
    med  = sum(1 for s in sigs if s.get("level") == "medium")
    return [float(len(sigs)), float(high), float(med), _bool(vc.get("environment_matches_business"))]


def _feat_risk_signal(sig: dict) -> list[float]:
    lv = RISK_LEVEL_MAP.get(sig.get("level","low"), 0)
    return [float(lv) / 3.0]


def _feat_transaction(tx: dict) -> list[float]:
    return [_log(tx.get("amount", 0)), float(tx.get("transaction_count", 0))]


# ── 主函数 ────────────────────────────────────────────────────────────────────

def case_to_graph_spec(case: dict[str, Any]) -> dict[str, Any]:
    person     = case.get("person", {})
    enterprise = case.get("enterprise", {})
    changes    = case.get("claim_changes", [])
    docs       = case.get("documents_submitted", [])
    vcalls     = case.get("video_calls", [])
    open_verif = case.get("open_verifications", [])
    txs        = case.get("wallet_transactions", [])

    # ── 节点特征矩阵 ──────────────────────────────────────────────────────────
    nodes: dict[str, list[list[float]]] = {}

    nodes["application"] = [_feat_application(case)]
    nodes["person"]      = [_feat_person(person)]
    nodes["enterprise"]  = [_feat_enterprise(enterprise)]

    unique_fields = sorted({c.get("field","") for c in changes})
    field_idx = {f: i for i, f in enumerate(unique_fields)}
    nodes["claim"] = [_feat_claim(c, field_idx.get(c.get("field",""), 0)) for c in changes] or [[0.0]*4]

    nodes["document"]   = [_feat_document(d) for d in docs]      or [[0.0]*3]
    nodes["video_call"] = [_feat_video_call(vc) for vc in vcalls] or [[0.0]*4]

    # 全部风险信号：视频通话里的 + open_verifications
    all_signals: list[dict] = []
    vc_sig_ranges: list[tuple[int,int]] = []
    for vc in vcalls:
        s = vc.get("risk_signals", [])
        vc_sig_ranges.append((len(all_signals), len(all_signals) + len(s)))
        all_signals.extend(s)
    all_signals += [{"level": ov.get("level","low")} for ov in open_verif]
    nodes["risk_signal"] = [_feat_risk_signal(s) for s in all_signals] or [[0.0]]

    nodes["transaction"] = [_feat_transaction(t) for t in txs] or [[0.0]*2]

    n = {k: len(v) for k, v in nodes.items()}

    # ── 边 ───────────────────────────────────────────────────────────────────
    edges: dict[str, list[list[int]]] = {}

    # person → controls → enterprise
    edges["person__controls__enterprise"] = [[0], [0]]

    # person → claims → claim
    edges["person__claims__claim"] = [[0]*n["claim"], list(range(n["claim"]))]

    # claim → changed_to → claim (同字段连续变更)
    ct_src, ct_dst = [], []
    last: dict[str, int] = {}
    for i, c in enumerate(changes):
        f = c.get("field","")
        if f in last:
            ct_src.append(last[f]); ct_dst.append(i)
        last[f] = i
    edges["claim__changed_to__claim"] = [ct_src, ct_dst]

    # video_call → reveals → risk_signal
    vc_src, vc_dst = [], []
    for vi, (s0, s1) in enumerate(vc_sig_ranges):
        for si in range(s0, s1):
            vc_src.append(vi); vc_dst.append(si)
    edges["video_call__reveals__risk_signal"] = [vc_src, vc_dst]

    # document → supports → claim (全连接)
    d_src, d_dst = [], []
    for di in range(n["document"]):
        for ci in range(n["claim"]):
            d_src.append(di); d_dst.append(ci)
    edges["document__supports__claim"] = [d_src, d_dst]

    # risk_signal → blocks → application
    edges["risk_signal__blocks__application"] = [list(range(n["risk_signal"])), [0]*n["risk_signal"]]

    # transaction → belongs_to → enterprise
    edges["transaction__belongs_to__enterprise"] = [list(range(n["transaction"])), [0]*n["transaction"]]

    # enterprise → applies_to → application
    edges["enterprise__applies_to__application"] = [[0], [0]]

    # ── 标签 ─────────────────────────────────────────────────────────────────
    lbl   = case.get("labels", {})
    score = float(lbl.get("score", 50.0))
    sub   = lbl.get("sub_scores", {})

    labels = {
        "score":           score,
        "score_norm":      score / 100.0,
        "sub_scores_norm": [
            float(sub.get("identity",    0.0)) / 25.0,
            float(sub.get("business",    0.0)) / 25.0,
            float(sub.get("loan_logic",  0.0)) / 25.0,
            float(sub.get("cooperation", 0.0)) / 25.0,
        ],
        "recommendation": lbl.get("recommendation", "review"),
    }

    return {
        "case_id":    case.get("case_id", ""),
        "fraud_type": case.get("fraud_type", ""),
        "nodes":      nodes,
        "edges":      edges,
        "labels":     labels,
    }


# ── PyG 转换（需要 torch_geometric，训练时调用）─────────────────────────────

def spec_to_heterodata(spec: dict[str, Any]):  # type: ignore[return]
    """将图规格 JSON 转换为 PyG HeteroData。需要 torch 和 torch_geometric。"""
    import torch
    from torch_geometric.data import HeteroData

    data = HeteroData()
    for node_type, feats in spec["nodes"].items():
        data[node_type].x = torch.tensor(feats, dtype=torch.float)

    for edge_key, (src, dst) in spec["edges"].items():
        src_type, rel, dst_type = edge_key.split("__")
        if src and dst:
            data[src_type, rel, dst_type].edge_index = torch.tensor([src, dst], dtype=torch.long)
        else:
            data[src_type, rel, dst_type].edge_index = torch.zeros((2, 0), dtype=torch.long)

    lbl = spec["labels"]
    data.y         = torch.tensor([lbl["score_norm"]], dtype=torch.float)
    data.y_raw     = torch.tensor([lbl["score"]], dtype=torch.float)
    data.y_sub     = torch.tensor(lbl["sub_scores_norm"], dtype=torch.float)
    data.case_id   = spec["case_id"]
    data.fraud_type = spec["fraud_type"]
    return data
