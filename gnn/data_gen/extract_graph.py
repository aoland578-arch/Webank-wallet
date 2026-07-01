"""
将 generate_case.py 生成的案例 JSON 转换为 PyTorch Geometric HeteroData 图对象。

节点类型：
  application  — 根节点，每图一个
  person       — 申请人
  enterprise   — 企业
  claim        — 一条声明值（字段+口径+轮次）
  document     — 提交的证件/材料
  video_call   — 一次视频通话
  risk_signal  — 一条风险信号
  transaction  — 一个月的流水记录

边类型（有向）：
  person       → controls    → enterprise
  person       → claims      → claim
  claim        → changed_to  → claim       (字段变更链)
  video_call   → reveals     → risk_signal
  document     → supports    → claim       (材料支撑声明)
  risk_signal  → blocks      → application
  transaction  → belongs_to  → enterprise
  enterprise   → applies_to  → application
"""

from __future__ import annotations

import math
from typing import Any

import torch
from torch_geometric.data import HeteroData


# ── 编码工具 ─────────────────────────────────────────────────────────────────

INDUSTRY_LIST = ["餐饮", "零售", "制造", "服务业", "贸易", "建筑", "电商", "农业"]
FRAUD_TYPE_LIST = [
    "identity_fraud", "business_fraud", "purpose_fraud",
    "document_fraud", "multi_fraud", "no_fraud", "minor_issues",
]
RISK_LEVEL_MAP = {"low": 0, "medium": 1, "high": 2, "critical": 3}
DOC_QUALITY_MAP = {"clear": 1.0, "blurry": 0.4, "refused": 0.0}
RECOMMEND_MAP = {"approve": 1.0, "review": 0.5, "reject": 0.0}


def _onehot(value: str, vocab: list[str]) -> list[float]:
    return [1.0 if value == v else 0.0 for v in vocab]


def _safe_log(x: float) -> float:
    return math.log(max(x, 1.0))


def _bool(v: Any) -> float:
    if isinstance(v, bool):
        return 1.0 if v else 0.0
    if isinstance(v, (int, float)):
        return float(bool(v))
    if isinstance(v, str):
        return 1.0 if v.lower() in ("true", "yes", "1") else 0.0
    return 0.0


# ── 节点特征向量 ──────────────────────────────────────────────────────────────

def _application_feat(case: dict) -> list[float]:
    la = case.get("loan_application", {})
    amount_hist = la.get("amount_history", [la.get("final_amount", 0)])
    claim_changes = case.get("claim_changes", [])
    open_verif = case.get("open_verifications", [])
    high_signals = sum(
        1 for ov in open_verif if ov.get("level") == "high"
    )
    return [
        _safe_log(la.get("final_amount", 0)),       # 申请金额（log）
        float(la.get("term_months", 0)),             # 期限
        float(len(amount_hist)),                     # 金额变更次数
        float(len(claim_changes)),                   # 声明变更次数
        float(len(open_verif)),                      # 待核验数
        float(high_signals),                         # 高级风险信号数
    ]


def _person_feat(person: dict) -> list[float]:
    names = person.get("claimed_names", [])
    id_name = person.get("id_card_name", "")
    name_conflict = 1.0 if id_name and id_name not in names else 0.0
    return [
        float(len(names)),                    # 自称姓名数（>1说明改口）
        name_conflict,                        # 身份证姓名与自称是否冲突
        _bool(person.get("is_student")),
        _bool(person.get("is_legal_representative")),
        float(person.get("birth_year", 1990)) / 2030.0,  # 归一化出生年
    ]


def _enterprise_feat(ent: dict) -> list[float]:
    claimed = ent.get("claimed_monthly_revenue", 0)
    actual  = ent.get("actual_monthly_revenue", claimed)
    revenue_ratio = min(claimed / max(actual, 1), 10.0)  # 虚报倍数，cap 10
    return [
        float(ent.get("established_years", 0)),
        _safe_log(claimed),
        _safe_log(actual),
        revenue_ratio,
        float(ent.get("employee_count", 0)),
        _bool(ent.get("has_license")),
        _bool(ent.get("license_authentic")),
        _bool(ent.get("has_tax_record")),
        *_onehot(ent.get("tax_grade") or "", ["A", "B", "C", "D", ""]),
        *_onehot(ent.get("industry", ""), INDUSTRY_LIST),
    ]


def _claim_feat(change: dict, field_index: int) -> list[float]:
    return [
        float(field_index),                         # 字段编号（词典序）
        float(change.get("turn", 0)),               # 发生轮次
        _bool(change.get("is_reasonable")),         # 变更是否合理
        1.0 if change.get("explanation") else 0.0,  # 有无解释
    ]


def _document_feat(doc: dict) -> list[float]:
    quality = DOC_QUALITY_MAP.get(doc.get("quality", "clear"), 0.5)
    return [
        _bool(doc.get("submitted")),
        quality,
        _bool(doc.get("authentic")),
    ]


def _video_call_feat(vc: dict) -> list[float]:
    signals = vc.get("risk_signals", [])
    high = sum(1 for s in signals if s.get("level") == "high")
    med  = sum(1 for s in signals if s.get("level") == "medium")
    return [
        float(len(signals)),
        float(high),
        float(med),
        _bool(vc.get("environment_matches_business")),
    ]


def _risk_signal_feat(sig: dict) -> list[float]:
    level = RISK_LEVEL_MAP.get(sig.get("level", "low"), 0)
    return [float(level) / 3.0]  # normalized 0-1


def _transaction_feat(tx: dict) -> list[float]:
    return [
        _safe_log(tx.get("amount", 0)),
        float(tx.get("transaction_count", 0)),
    ]


# ── 主转换函数 ────────────────────────────────────────────────────────────────

def case_to_heterodata(case: dict[str, Any]) -> HeteroData:
    data = HeteroData()

    person     = case.get("person", {})
    enterprise = case.get("enterprise", {})
    la         = case.get("loan_application", {})
    changes    = case.get("claim_changes", [])
    docs       = case.get("documents_submitted", [])
    vcalls     = case.get("video_calls", [])
    open_verif = case.get("open_verifications", [])
    txs        = case.get("wallet_transactions", [])

    # ── 节点 ─────────────────────────────────────────────────────────────────
    data["application"].x = torch.tensor([_application_feat(case)], dtype=torch.float)

    data["person"].x = torch.tensor([_person_feat(person)], dtype=torch.float)

    data["enterprise"].x = torch.tensor([_enterprise_feat(enterprise)], dtype=torch.float)

    # claim 节点：每个声明变更一个节点
    unique_fields = sorted({c.get("field", "") for c in changes})
    field_to_idx = {f: i for i, f in enumerate(unique_fields)}
    if changes:
        claim_feats = [_claim_feat(c, field_to_idx.get(c.get("field", ""), 0)) for c in changes]
        data["claim"].x = torch.tensor(claim_feats, dtype=torch.float)
    else:
        data["claim"].x = torch.zeros((1, 4), dtype=torch.float)

    # document 节点
    if docs:
        data["document"].x = torch.tensor([_document_feat(d) for d in docs], dtype=torch.float)
    else:
        data["document"].x = torch.zeros((1, 3), dtype=torch.float)

    # video_call 节点
    all_signals: list[dict] = []
    vc_signal_ranges: list[tuple[int, int]] = []
    for vc in vcalls:
        start = len(all_signals)
        sigs = vc.get("risk_signals", [])
        all_signals.extend(sigs)
        vc_signal_ranges.append((start, start + len(sigs)))

    if vcalls:
        data["video_call"].x = torch.tensor([_video_call_feat(vc) for vc in vcalls], dtype=torch.float)
    else:
        data["video_call"].x = torch.zeros((1, 4), dtype=torch.float)

    # risk_signal 节点（来自视频通话 + open_verifications）
    ov_signals = [{"level": ov.get("level", "low"), "text": ov.get("text", "")} for ov in open_verif]
    combined_signals = all_signals + ov_signals
    if combined_signals:
        data["risk_signal"].x = torch.tensor(
            [_risk_signal_feat(s) for s in combined_signals], dtype=torch.float
        )
    else:
        data["risk_signal"].x = torch.zeros((1, 1), dtype=torch.float)

    # transaction 节点
    if txs:
        data["transaction"].x = torch.tensor([_transaction_feat(t) for t in txs], dtype=torch.float)
    else:
        data["transaction"].x = torch.zeros((1, 2), dtype=torch.float)

    # ── 边 ───────────────────────────────────────────────────────────────────
    # person → controls → enterprise  (0→0)
    data["person", "controls", "enterprise"].edge_index = torch.tensor([[0], [0]], dtype=torch.long)

    # person → claims → claim  (0 → each claim)
    n_claims = data["claim"].x.size(0)
    data["person", "claims", "claim"].edge_index = torch.tensor(
        [[0] * n_claims, list(range(n_claims))], dtype=torch.long
    )

    # claim → changed_to → claim  (consecutive changes of same field)
    ct_src, ct_dst = [], []
    field_last: dict[str, int] = {}
    for i, c in enumerate(changes):
        f = c.get("field", "")
        if f in field_last:
            ct_src.append(field_last[f])
            ct_dst.append(i)
        field_last[f] = i
    if ct_src:
        data["claim", "changed_to", "claim"].edge_index = torch.tensor(
            [ct_src, ct_dst], dtype=torch.long
        )
    else:
        data["claim", "changed_to", "claim"].edge_index = torch.zeros((2, 0), dtype=torch.long)

    # video_call → reveals → risk_signal
    vc_src, vc_dst = [], []
    for vc_i, (sig_start, sig_end) in enumerate(vc_signal_ranges):
        for sig_j in range(sig_start, sig_end):
            vc_src.append(vc_i)
            vc_dst.append(sig_j)
    if vc_src:
        data["video_call", "reveals", "risk_signal"].edge_index = torch.tensor(
            [vc_src, vc_dst], dtype=torch.long
        )
    else:
        data["video_call", "reveals", "risk_signal"].edge_index = torch.zeros((2, 0), dtype=torch.long)

    # document → supports → claim  (每份材料与它对应的声明关联，简化为全连接)
    n_docs = data["document"].x.size(0)
    doc_src, doc_dst = [], []
    for d_i in range(n_docs):
        for c_j in range(n_claims):
            doc_src.append(d_i)
            doc_dst.append(c_j)
    if doc_src:
        data["document", "supports", "claim"].edge_index = torch.tensor(
            [doc_src, doc_dst], dtype=torch.long
        )
    else:
        data["document", "supports", "claim"].edge_index = torch.zeros((2, 0), dtype=torch.long)

    # risk_signal → blocks → application  (所有风险信号指向唯一的 application 节点)
    n_signals = data["risk_signal"].x.size(0)
    data["risk_signal", "blocks", "application"].edge_index = torch.tensor(
        [list(range(n_signals)), [0] * n_signals], dtype=torch.long
    )

    # transaction → belongs_to → enterprise
    n_txs = data["transaction"].x.size(0)
    data["transaction", "belongs_to", "enterprise"].edge_index = torch.tensor(
        [list(range(n_txs)), [0] * n_txs], dtype=torch.long
    )

    # enterprise → applies_to → application
    data["enterprise", "applies_to", "application"].edge_index = torch.tensor(
        [[0], [0]], dtype=torch.long
    )

    # ── 标签 ─────────────────────────────────────────────────────────────────
    labels = case.get("labels", {})
    score = float(labels.get("score", 50.0))
    sub = labels.get("sub_scores", {})
    data.y = torch.tensor([score / 100.0], dtype=torch.float)          # normalized [0,1]
    data.y_raw = torch.tensor([score], dtype=torch.float)              # original 0-100
    data.y_sub = torch.tensor([
        float(sub.get("identity",   0.0)) / 25.0,
        float(sub.get("business",   0.0)) / 25.0,
        float(sub.get("loan_logic", 0.0)) / 25.0,
        float(sub.get("cooperation",0.0)) / 25.0,
    ], dtype=torch.float)

    # 元数据
    data.case_id    = case.get("case_id", "")
    data.fraud_type = case.get("fraud_type", "")

    return data


if __name__ == "__main__":
    import json, sys
    sample_path = sys.argv[1] if len(sys.argv) > 1 else None
    if sample_path:
        with open(sample_path, encoding="utf-8") as f:
            case = json.load(f)
    else:
        # 最小 mock 案例，用于测试结构
        case = {
            "case_id": "test-001",
            "fraud_type": "identity_fraud",
            "industry": "餐饮",
            "person": {"claimed_names": ["李杰", "麦立俊"], "id_card_name": "麦立俊",
                       "birth_year": 2002, "province": "广西", "is_student": True, "is_legal_representative": True},
            "enterprise": {"name": "龙火餐饮", "industry": "餐饮", "established_years": 2,
                           "claimed_monthly_revenue": 500000, "actual_monthly_revenue": 50000,
                           "employee_count": 5, "has_license": True, "license_authentic": False,
                           "has_tax_record": True, "tax_grade": "A", "city": "深圳"},
            "loan_application": {"amount_history": [30000, 1000000, 150000], "purpose_history": ["房租","设备","装修"],
                                 "final_amount": 150000, "final_purpose": "装修门店", "term_months": 3},
            "video_calls": [{"call_id": "abc12345", "environment_description": "上下铺宿舍",
                             "environment_matches_business": False,
                             "risk_signals": [{"level": "high", "text": "环境与火锅店不符"}]}],
            "claim_changes": [{"field": "loan_amount", "from_value": "30000", "to_value": "1000000",
                               "turn": 15, "explanation": None, "is_reasonable": False}],
            "documents_submitted": [{"type": "身份证", "submitted": True, "quality": "blurry", "authentic": False}],
            "wallet_transactions": [{"month": "2026-03", "amount": 38600, "transaction_count": 45},
                                    {"month": "2026-04", "amount": 45200, "transaction_count": 52}],
            "open_verifications": [{"level": "high", "text": "身份矛盾", "source": "视频通话"}],
            "labels": {"score": 12.5, "sub_scores": {"identity": 3.0, "business": 2.0,
                       "loan_logic": 4.0, "cooperation": 3.5}, "recommendation": "reject"},
        }
    graph = case_to_heterodata(case)
    print(graph)
    print(f"\n✓ y={graph.y.item():.3f}  fraud_type={graph.fraud_type}")
