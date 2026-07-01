"""
生成单个贷款申请案例（结构化 JSON），供图神经网络训练使用。

每次调用一次 LLM，输出一个完整案例：
  - 申请人/企业基本信息
  - 声明值列表（含变更历史）
  - 提交材料
  - 视频通话事件 + 风险信号
  - 评分（0-100，越高越可信）及四维子分
"""

from __future__ import annotations

import json
import random
import time
import uuid
from typing import Any

import urllib.request
import urllib.error

from config import API_KEY, BASE_URL, MODEL, REQUEST_TIMEOUT, MAX_RETRIES

# ── persona templates ─────────────────────────────────────────────────────────

INDUSTRIES = ["餐饮", "零售", "制造", "服务业", "贸易", "建筑", "电商", "农业"]

FRAUD_TYPES = [
    "identity_fraud",      # 身份造假：证件与自称不符、冒用他人身份
    "business_fraud",      # 经营造假：虚构门店、营业额、行业
    "purpose_fraud",       # 用途造假：频繁变更用途、资金实际用途不实
    "document_fraud",      # 材料造假：伪造执照、证件模糊故意回避
    "multi_fraud",         # 复合欺诈：多种欺诈叠加
    "no_fraud",            # 正常申请：真实经营、配合核验
    "minor_issues",        # 轻微瑕疵：信息不完整但非故意欺诈
]

# 欺诈类型 → 推荐分值区间
FRAUD_SCORE_RANGE: dict[str, tuple[int, int]] = {
    "identity_fraud":  (0,  25),
    "multi_fraud":     (0,  30),
    "business_fraud":  (10, 40),
    "document_fraud":  (15, 45),
    "purpose_fraud":   (20, 50),
    "minor_issues":    (45, 75),
    "no_fraud":        (70, 100),
}

SYSTEM_PROMPT = """\
你是一个金融风控数据生成专家。你的任务是生成真实感强、细节丰富的小微企业贷款申请案例，\
用于训练图神经网络风控模型。

输出必须是合法 JSON，不要包含任何解释文字、markdown代码块标记。

评分规则（score字段，0-100，越高越可信）：
- identity子分（0-25）：身份证/营业执照/自称是否一致，无矛盾=25，严重矛盾=0-5
- business子分（0-25）：经营环境/营业额/行业是否真实可信，完全可信=25
- loan_logic子分（0-25）：申请金额/用途是否稳定合理，无变更且合理=25
- cooperation子分（0-25）：材料提交率/配合度，完全配合=25
总分 = 四个子分之和
"""

CASE_PROMPT_TEMPLATE = """\
请生成一个小微企业贷款申请案例，参数如下：
- 欺诈类型：{fraud_type}
- 行业：{industry}
- 目标总分区间：{score_min}-{score_max}分

输出 JSON 结构如下（严格按此结构，不要增删字段）：

{{
  "case_id": "uuid字符串",
  "fraud_type": "{fraud_type}",
  "industry": "{industry}",
  "person": {{
    "claimed_names": ["自称姓名1", "自称姓名2"],
    "id_card_name": "身份证姓名",
    "birth_year": 1990,
    "province": "省份",
    "is_student": false,
    "is_legal_representative": true
  }},
  "enterprise": {{
    "name": "企业全称",
    "industry": "{industry}",
    "established_years": 2,
    "claimed_monthly_revenue": 50000,
    "actual_monthly_revenue": 50000,
    "employee_count": 5,
    "has_license": true,
    "license_authentic": true,
    "has_tax_record": true,
    "tax_grade": "A",
    "city": "深圳"
  }},
  "loan_application": {{
    "amount_history": [50000, 100000],
    "purpose_history": ["采购原料", "扩大经营"],
    "final_amount": 100000,
    "final_purpose": "扩大经营",
    "term_months": 12
  }},
  "video_calls": [
    {{
      "call_id": "a1b2c3d4",
      "environment_description": "门店收银台前",
      "environment_matches_business": true,
      "risk_signals": [
        {{"level": "low", "text": "证件略有反光"}}
      ]
    }}
  ],
  "claim_changes": [
    {{
      "field": "loan_amount",
      "from_value": "50000",
      "to_value": "100000",
      "turn": 8,
      "explanation": "重新核算了资金缺口",
      "is_reasonable": true
    }}
  ],
  "documents_submitted": [
    {{
      "type": "营业执照",
      "submitted": true,
      "quality": "clear",
      "authentic": true
    }}
  ],
  "wallet_transactions": [
    {{
      "month": "2026-03",
      "amount": 45000,
      "transaction_count": 60
    }}
  ],
  "open_verifications": [
    {{
      "level": "low",
      "text": "流水待核验",
      "source": "文字对话"
    }}
  ],
  "labels": {{
    "score": 82.0,
    "sub_scores": {{
      "identity": 22.0,
      "business": 20.0,
      "loan_logic": 20.0,
      "cooperation": 20.0
    }},
    "recommendation": "approve"
  }}
}}

要求：
1. 细节要真实、具体，不要用"xxx"或模板占位符
2. 各字段数据要内部一致（欺诈类型与风险信号要对应）
3. video_calls至少1个，最多3个；claim_changes根据欺诈类型0-6个
4. wallet_transactions生成3-6个月的数据
5. 总分必须落在{score_min}-{score_max}之间，四个子分之和=总分
"""


def _repair_json(text: str) -> str:
    """修复常见 JSON 问题：trailing comma、单引号、注释。"""
    import re
    # 去掉行内注释 (// ...)
    text = re.sub(r'//[^\n]*', '', text)
    # 去掉尾随逗号（在 } 或 ] 前）
    text = re.sub(r',\s*([\}\]])', r'\1', text)
    return text


def _call_api(messages: list[dict[str, str]]) -> str:
    payload = json.dumps({
        "model": MODEL,
        "messages": messages,
        "temperature": 0.9,
        "max_tokens": 4096,
        "response_format": {"type": "json_object"},
    }).encode("utf-8")

    req = urllib.request.Request(
        f"{BASE_URL}/chat/completions",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {API_KEY}",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data["choices"][0]["message"]["content"]


def _pick_params() -> tuple[str, str, int, int]:
    """
    按目标分值分布加权采样，返回 (fraud_type, industry, score_min, score_max)。

    先按 SCORE_BUCKETS 权重抽一个分值桶，再从该桶对应的欺诈类型中随机选一个，
    确保生成数据的分数分布均匀覆盖 0-100。
    """
    from config import SCORE_BUCKETS

    # 按桶权重抽一个桶
    buckets = SCORE_BUCKETS
    weights = [w for _, _, w in buckets]
    total = sum(weights)
    r = random.random() * total
    cumulative = 0.0
    chosen_bucket = buckets[-1]
    for bucket in buckets:
        cumulative += bucket[2]
        if r <= cumulative:
            chosen_bucket = bucket
            break

    b_min, b_max, _ = chosen_bucket

    # 找与该桶分值范围有重叠的欺诈类型
    candidates = [
        ft for ft in FRAUD_TYPES
        if FRAUD_SCORE_RANGE[ft][0] < b_max and FRAUD_SCORE_RANGE[ft][1] > b_min
    ]
    if not candidates:
        candidates = FRAUD_TYPES

    fraud_type = random.choice(candidates)
    industry   = random.choice(INDUSTRIES)

    # 最终分值区间取桶范围与欺诈类型范围的交集，避免越界
    ft_min, ft_max = FRAUD_SCORE_RANGE[fraud_type]
    score_min = max(b_min, ft_min)
    score_max = min(b_max, ft_max)
    if score_min >= score_max:
        score_min, score_max = ft_min, ft_max

    return fraud_type, industry, score_min, score_max


def _extract_json(text: str) -> dict[str, Any]:
    """从可能含有多余文字的响应中提取 JSON 对象。"""
    text = text.strip()
    # 去掉可能的 markdown 代码块
    if text.startswith("```"):
        lines = text.splitlines()
        text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
    # 找第一个 { 到最后一个 }
    start = text.find("{")
    end = text.rfind("}") + 1
    if start == -1 or end == 0:
        raise ValueError("响应中未找到 JSON 对象")
    fragment = text[start:end]
    try:
        return json.loads(fragment)
    except json.JSONDecodeError:
        return json.loads(_repair_json(fragment))


def generate_case(fraud_type: str | None = None, industry: str | None = None) -> dict[str, Any]:
    """生成一个案例，返回结构化 dict。失败时抛出异常。"""
    if fraud_type is None or industry is None:
        ft, ind, smin, smax = _pick_params()
        fraud_type = fraud_type or ft
        industry = industry or ind
    else:
        smin, smax = FRAUD_SCORE_RANGE.get(fraud_type, (0, 100))

    prompt = CASE_PROMPT_TEMPLATE.format(
        fraud_type=fraud_type,
        industry=industry,
        score_min=smin,
        score_max=smax,
    )

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            raw = _call_api([
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ])
            case = _extract_json(raw)
            # 始终用真实 uuid4 覆盖（模型生成的 id 可能重复）
            case["case_id"] = str(uuid.uuid4())
            # 保证 fraud_type 与请求一致
            case["fraud_type"] = fraud_type
            return case
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            if attempt == MAX_RETRIES:
                raise RuntimeError(f"生成失败（{MAX_RETRIES}次重试后）: {e}") from e
            time.sleep(2 ** attempt)
        except urllib.error.HTTPError as e:
            if e.code == 429:
                wait = 10 * attempt   # 429 等更久：10s, 20s, 30s
                time.sleep(wait)
                if attempt == MAX_RETRIES:
                    raise RuntimeError(f"API 请求失败（限流）: {e}") from e
            else:
                if attempt == MAX_RETRIES:
                    raise RuntimeError(f"API 请求失败: {e}") from e
                time.sleep(2 ** attempt)
        except urllib.error.URLError as e:
            if attempt == MAX_RETRIES:
                raise RuntimeError(f"API 请求失败: {e}") from e
            time.sleep(2 ** attempt)

    raise RuntimeError("不应到达这里")


if __name__ == "__main__":
    import sys
    print("生成测试案例...", flush=True)
    case = generate_case()
    print(json.dumps(case, ensure_ascii=False, indent=2))
    print(f"\n✓ fraud_type={case['fraud_type']}  score={case['labels']['score']}", file=sys.stderr)
