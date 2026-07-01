"""
将真实企业数据转换为 GNN 推理所需的 case JSON 格式。

数据来源：
  profile_state.json  → open_verifications（风险待核实项）
  profile.md          → 人员/企业/贷款/文件信息（正则提取，best-effort）
  video_calls DB      → 视频通话记录 + 风控结论
  wallet JSON         → 流水按月聚合

输出格式与 gnn/data_gen/generate_case.py 生成的训练数据结构完全一致，
可直接传入 gnn/data_gen/graph_spec.py:case_to_graph_spec() 进行图构建。
"""
from __future__ import annotations

import re
import uuid
from collections import defaultdict
from typing import Any

# ── 内部导入（与 server.py 同目录运行）────────────────────────────────────────
from profile_service import load_profile_markdown, load_profile_state
from wallet import load_wallet_transactions
import video_calls as vc_module


# ── Markdown 解析工具 ─────────────────────────────────────────────────────────

def _extract_table_value(md: str, field_key: str, col: int = 1) -> str:
    """从 Markdown 表格中提取字段值。col=1 当前口径，col=2 历史口径/备注。"""
    pattern = re.compile(
        r"\|\s*" + re.escape(field_key) + r"\s*\|([^|]*)\|" + r"([^|]*)\|" * col,
        re.IGNORECASE,
    )
    m = pattern.search(md)
    if not m:
        return ""
    # col=1 → group(1)，col=2 → group(2)
    val = m.group(col).strip()
    # 去掉 Markdown 加粗/斜体标记
    val = re.sub(r"\*+", "", val)
    return val.strip()


def _extract_section(md: str, heading: str) -> str:
    """提取某个 ## 二级标题下的内容直到下一个 ## 为止。"""
    pattern = re.compile(
        r"##\s*" + re.escape(heading) + r".*?\n(.*?)(?=\n##|\Z)",
        re.DOTALL | re.IGNORECASE,
    )
    m = pattern.search(md)
    return m.group(1).strip() if m else ""


def _extract_current_risk_level(md: str) -> str:
    m = re.search(r"当前风险等级[：:]\s*(\S+)", md)
    return (m.group(1).strip().lower() if m else "medium")


def _parse_amount(text: str) -> float:
    """从文本中提取第一个数值（万/元单位识别）。"""
    text = re.sub(r"[,，]", "", text)
    # 带"万"
    m = re.search(r"([\d.]+)\s*万", text)
    if m:
        return float(m.group(1)) * 10000
    # 纯数字
    m = re.search(r"[\d.]+", text)
    return float(m.group(0)) if m else 0.0


def _parse_birth_year(text: str) -> int:
    m = re.search(r"(\d{4})\s*年", text)
    if m:
        return int(m.group(1))
    m = re.search(r"\d{4}", text)
    return int(m.group(0)) if m else 1990


def _parse_established_years(text: str) -> float:
    m = re.search(r"([\d.]+)\s*年", text)
    if m:
        return float(m.group(1))
    m = re.search(r"约?\s*([\d.]+)", text)
    return float(m.group(1)) if m else 2.0


def _parse_loan_history(md: str) -> tuple[list[float], list[str]]:
    """从画像中提取申请金额历史和用途历史（优先读历史口径列）。"""
    # 历史口径列（col=2）有完整变更链；当前口径列（col=1）只有最新值
    amount_history = _extract_table_value(md, "申请金额", col=2)
    amount_current = _extract_table_value(md, "申请金额", col=1)
    purpose_history = _extract_table_value(md, "贷款用途", col=2)
    purpose_current = _extract_table_value(md, "贷款用途", col=1)

    # 金额历史
    amounts: list[float] = []
    src = amount_history if ("→" in amount_history or ">" in amount_history) else amount_current
    if src:
        for part in re.split(r"[→>]", src):
            v = _parse_amount(part)
            if v > 0:
                amounts.append(v)
    if not amounts:
        amounts = [100000.0]

    # 用途历史
    purposes: list[str] = []
    src_p = purpose_history if ("→" in purpose_history or ">" in purpose_history) else purpose_current
    if src_p:
        for part in re.split(r"[→>]", src_p):
            p = re.sub(r"\*+|\(.*?\)|（.*?）", "", part).strip()
            if p:
                purposes.append(p[:40])
    if not purposes:
        purposes = ["流动资金"]

    return amounts, purposes


def _parse_claim_changes(md: str) -> list[dict[str, Any]]:
    """从画像中提取字段变更记录（申请金额 + 贷款用途的历史口径列）。"""
    changes = []

    amount_raw = _extract_table_value(md, "申请金额", col=2)
    if "→" in amount_raw or ">" in amount_raw:
        parts = [p.strip() for p in re.split(r"[→>]", amount_raw) if _parse_amount(p) > 0]
        for i in range(1, len(parts)):
            changes.append({
                "field": "loan_amount",
                "from_value": parts[i - 1],
                "to_value": parts[i],
                "turn": i * 5,
                "explanation": "",
                "is_reasonable": False,
            })

    purpose_raw = _extract_table_value(md, "贷款用途", col=2)
    if "→" in purpose_raw or ">" in purpose_raw:
        parts = [p.strip() for p in re.split(r"[→>]", purpose_raw) if p.strip()]
        for i in range(1, len(parts)):
            changes.append({
                "field": "loan_purpose",
                "from_value": parts[i - 1][:40],
                "to_value": parts[i][:40],
                "turn": i * 5 + 2,
                "explanation": "",
                "is_reasonable": False,
            })

    return changes


def _parse_documents(md: str) -> list[dict[str, Any]]:
    """从画像中提取文件核验状态。"""
    KNOWN_DOCS = [
        ("营业执照", "营业执照"),
        ("税务", "税务登记证"),
        ("银行流水", "银行流水"),
        ("身份证", "身份证"),
        ("租赁合同", "租赁合同"),
        ("装修合同", "装修合同"),
        ("征信", "征信报告"),
    ]
    docs = []
    for keyword, label in KNOWN_DOCS:
        if keyword in md:
            # 看是否有"待核验"或"已核验"标记
            ctx_m = re.search(
                r"(" + re.escape(keyword) + r".{0,60})",
                md,
            )
            ctx = ctx_m.group(1) if ctx_m else ""
            submitted = "待核验" not in ctx or keyword in ctx
            authentic = "真实" in ctx or ("待核验" not in ctx and "伪" not in ctx and "假" not in ctx)
            quality = "clear"
            if "模糊" in ctx or "不清" in ctx:
                quality = "blurry"
            elif "拒绝" in ctx or "拒" in ctx or "未提供" in ctx:
                quality = "refused"
                submitted = False
            docs.append({
                "type": label,
                "submitted": submitted,
                "quality": quality,
                "authentic": authentic,
            })
    if not docs:
        docs = [{"type": "营业执照", "submitted": False, "quality": "refused", "authentic": False}]
    return docs


def _parse_person(md: str) -> dict[str, Any]:
    name_raw = _extract_table_value(md, "法定姓名")
    birth_raw = _extract_table_value(md, "出生日期")
    student_raw = _extract_table_value(md, "学生身份")

    # 提取所有名字变体
    claimed_names: list[str] = []
    id_card_name = ""
    if name_raw:
        # 格式如：麦立俊（身份证）；客户自称李杰
        id_m = re.search(r"(\S+)\s*[（(]身份证[)）]", name_raw)
        if id_m:
            id_card_name = id_m.group(1)
        # 自称
        claimed_m = re.findall(r'自称\s*[““「]?(\w+)[“”」]?', name_raw)
        if claimed_m:
            claimed_names.extend(claimed_m)
        # 其他名字（引号包裹）
        extra = re.findall(r'[““「](\w+)[“”」]', name_raw)
        for groups in extra:
            for g in groups:
                if g and g not in claimed_names:
                    claimed_names.append(g)

    if not claimed_names and id_card_name:
        claimed_names = [id_card_name]
    elif not claimed_names:
        claimed_names = ["未知"]

    birth_year = _parse_birth_year(birth_raw) if birth_raw else 1990
    is_student = bool(student_raw and "学生" in student_raw and "否" not in student_raw)

    return {
        "claimed_names": claimed_names,
        "id_card_name": id_card_name or claimed_names[0],
        "birth_year": birth_year,
        "province": "未知",
        "is_student": is_student,
        "is_legal_representative": True,
    }


INDUSTRY_MAP = {
    "餐饮": "餐饮", "火锅": "餐饮", "饭店": "餐饮", "食品": "餐饮",
    "零售": "零售", "超市": "零售", "批发": "零售",
    "制造": "制造", "工厂": "制造", "加工": "制造",
    "服务": "服务业", "中介": "服务业", "咨询": "服务业",
    "贸易": "贸易", "进出口": "贸易",
    "建筑": "建筑", "装修": "建筑", "工程": "建筑",
    "电商": "电商", "网店": "电商", "直播": "电商",
    "农业": "农业", "养殖": "农业", "种植": "农业",
}

def _detect_industry(md: str) -> str:
    for kw, industry in INDUSTRY_MAP.items():
        if kw in md:
            return industry
    return "服务业"


def _parse_enterprise(md: str, wallet_txs: list[dict]) -> dict[str, Any]:
    ent_name = _extract_table_value(md, "企业全称")
    established_raw = _extract_table_value(md, "成立时间") or _extract_table_value(md, "经营年限")
    revenue_raw = _extract_table_value(md, "月营业额")
    tax_raw = _extract_table_value(md, "纳税等级")
    employees_raw = _extract_table_value(md, "员工数量")

    established = _parse_established_years(established_raw) if established_raw else 2.0

    # 月营业额：从 wallet 计算更可靠
    monthly_amounts = []
    by_month: dict[str, float] = defaultdict(float)
    for tx in wallet_txs:
        date = str(tx.get("date", ""))[:7]
        amount = float(tx.get("amount", 0))
        if tx.get("type") == "income":
            by_month[date] += amount
    if by_month:
        monthly_amounts = list(by_month.values())

    actual_monthly = sum(monthly_amounts) / len(monthly_amounts) if monthly_amounts else 50000.0

    # 声称的月营业额（从画像文本提取）
    claimed_monthly = actual_monthly
    if revenue_raw:
        v = _parse_amount(revenue_raw)
        if v > 0:
            claimed_monthly = v

    # 纳税等级
    tax_grade = ""
    if tax_raw:
        m = re.search(r"[ABCD]", tax_raw.upper())
        if m:
            tax_grade = m.group(0)

    # 员工数
    employees = 5
    if employees_raw:
        m = re.search(r"\d+", employees_raw)
        if m:
            employees = int(m.group(0))

    industry = _detect_industry(md)

    has_license = "营业执照" in md
    license_authentic = has_license and "执照" in md and "伪" not in md and "假" not in md
    has_tax = "纳税" in md or "税务" in md

    return {
        "name": ent_name or "未知企业",
        "industry": industry,
        "established_years": established,
        "claimed_monthly_revenue": claimed_monthly,
        "actual_monthly_revenue": actual_monthly,
        "employee_count": employees,
        "has_license": has_license,
        "license_authentic": license_authentic,
        "has_tax_record": has_tax,
        "tax_grade": tax_grade,
        "city": "未知",
    }


# ── 视频通话转换 ───────────────────────────────────────────────────────────────

def _convert_video_calls(calls: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """将 DB 中的视频通话记录转为 GNN 格式。"""
    result = []
    for call in calls:
        risk = call.get("risk") or {}
        observations = call.get("observations") or []

        # 从 LLM 风控结论提取信号
        risk_signals: list[dict[str, Any]] = []
        if isinstance(risk, dict):
            level = risk.get("level", "low")
            for reason in (risk.get("reasons") or []):
                risk_signals.append({"level": level, "text": str(reason)[:100]})

        # 从帧观察聚合额外信号
        anomaly_count = 0
        off_screen = 0
        absent = 0
        for obs in (observations if isinstance(observations, list) else []):
            if not isinstance(obs, dict):
                continue
            anomalies = obs.get("anomalies")
            if isinstance(anomalies, list):
                anomaly_count += len([a for a in anomalies if a])
            if obs.get("looking_off_screen") is True:
                off_screen += 1
            if obs.get("person_present") is False:
                absent += 1

        if anomaly_count > 3:
            risk_signals.append({"level": "medium", "text": f"画面异常帧：{anomaly_count}次"})
        if off_screen > 5:
            risk_signals.append({"level": "medium", "text": f"回避视线：{off_screen}次"})
        if absent > 3:
            risk_signals.append({"level": "high", "text": f"人员离开画面：{absent}次"})

        result.append({
            "call_id": call.get("id", ""),
            "environment_description": "",
            "environment_matches_business": len([s for s in risk_signals if s.get("level") in ("high", "medium")]) == 0,
            "risk_signals": risk_signals,
        })
    return result


# ── 流水月度聚合 ───────────────────────────────────────────────────────────────

def _aggregate_monthly_txs(txs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """按月聚合流水，只取收入，最近 6 个月。"""
    by_month: dict[str, dict[str, Any]] = defaultdict(lambda: {"amount": 0.0, "count": 0})
    for tx in txs:
        date = str(tx.get("date", ""))[:7]  # YYYY-MM
        if not re.match(r"\d{4}-\d{2}", date):
            continue
        if tx.get("type") == "income":
            by_month[date]["amount"] += float(tx.get("amount", 0))
            by_month[date]["count"] += 1

    sorted_months = sorted(by_month.keys())[-6:]
    return [
        {"month": m, "amount": round(by_month[m]["amount"], 2), "transaction_count": by_month[m]["count"]}
        for m in sorted_months
    ]


# ── 主函数 ────────────────────────────────────────────────────────────────────

def enterprise_to_case(enterprise_id: str) -> dict[str, Any]:
    """
    将真实企业数据组装成 GNN case JSON。
    labels.score 设为 -1 表示"待推理"（不参与训练，仅用于推理路径）。
    """
    # 1. profile_state
    state = load_profile_state(enterprise_id)
    open_verif = [
        item for item in (state.get("open_verifications") or [])
        if isinstance(item, dict)
    ]

    # 2. profile.md
    _, profile_md = load_profile_markdown(enterprise_id)

    # 3. 视频通话
    calls = vc_module.list_calls(enterprise_id, limit=20)

    # 4. 流水
    wallet_txs = load_wallet_transactions(enterprise_id)

    # 解析结构化字段
    person = _parse_person(profile_md)
    enterprise = _parse_enterprise(profile_md, wallet_txs)
    amounts, purposes = _parse_loan_history(profile_md)
    claim_changes = _parse_claim_changes(profile_md)
    documents = _parse_documents(profile_md)
    video_call_list = _convert_video_calls(calls)
    monthly_txs = _aggregate_monthly_txs(wallet_txs)

    loan_application = {
        "amount_history": amounts,
        "purpose_history": purposes,
        "final_amount": amounts[-1] if amounts else 100000.0,
        "final_purpose": purposes[-1] if purposes else "流动资金",
        "term_months": 12,
    }

    return {
        "case_id": enterprise_id,
        "fraud_type": "unknown",
        "industry": enterprise.get("industry", "服务业"),
        "person": person,
        "enterprise": enterprise,
        "loan_application": loan_application,
        "video_calls": video_call_list,
        "claim_changes": claim_changes,
        "documents_submitted": documents,
        "open_verifications": open_verif,
        "wallet_transactions": monthly_txs,
        "labels": {
            "score": -1.0,
            "sub_scores": {"identity": 0, "business": 0, "loan_logic": 0, "cooperation": 0},
            "recommendation": "review",
        },
    }
