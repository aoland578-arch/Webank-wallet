"""
HGT (Heterogeneous Graph Transformer) 风险评分模型。

输入：HeteroData 图
输出：0-1 归一化分值（×100 还原为 0-100 分）

架构：
  Linear per-type input projection
  → HGTConv × num_layers
  → application 节点表示
  → MLP → 主分值 + 4个子分（多任务）
"""

from __future__ import annotations

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch_geometric.nn import HGTConv, Linear


NODE_TYPES = ["application", "person", "enterprise", "claim",
              "document", "video_call", "risk_signal", "transaction"]

EDGE_TYPES = [
    ("person",       "controls",    "enterprise"),
    ("person",       "claims",      "claim"),
    ("claim",        "changed_to",  "claim"),
    ("video_call",   "reveals",     "risk_signal"),
    ("document",     "supports",    "claim"),
    ("risk_signal",  "blocks",      "application"),
    ("transaction",  "belongs_to",  "enterprise"),
    ("enterprise",   "applies_to",  "application"),
]

# 各节点类型的原始特征维度（与 graph_spec.py 保持一致）
NODE_IN_DIMS = {
    "application":  6,
    "person":       5,
    "enterprise":   18,   # 8 + 5(tax_grade onehot) + 8(industry onehot) - 1 + 1 = ... 实际算出来
    "claim":        4,
    "document":     3,
    "video_call":   4,
    "risk_signal":  1,
    "transaction":  2,
}

# 动态计算 enterprise 特征维度（tax_grade 5 + industry 8 + 其他 8 = 21）
# established_years, log_claimed, log_actual, ratio, employees,
# has_license, license_authentic, has_tax_record → 8 个数值
# tax_grade onehot: ["A","B","C","D",""] → 5
# industry onehot: 8
NODE_IN_DIMS["enterprise"] = 8 + 5 + 8   # = 21


class RiskScoreGNN(nn.Module):
    def __init__(
        self,
        hidden_dim: int = 128,
        num_layers: int = 3,
        num_heads: int = 4,
        dropout: float = 0.1,
    ) -> None:
        super().__init__()
        self.hidden_dim = hidden_dim

        # 每种节点类型的输入投影层
        self.input_proj = nn.ModuleDict({
            nt: Linear(dim, hidden_dim)
            for nt, dim in NODE_IN_DIMS.items()
        })

        # HGTConv 层
        metadata = (NODE_TYPES, EDGE_TYPES)
        self.convs = nn.ModuleList([
            HGTConv(hidden_dim, hidden_dim, metadata, heads=num_heads)
            for _ in range(num_layers)
        ])

        self.dropout = nn.Dropout(dropout)
        self.layer_norm = nn.ModuleDict({
            nt: nn.LayerNorm(hidden_dim) for nt in NODE_TYPES
        })

        # 输出头：主分值 + 4 个子分（多任务）
        self.score_head = nn.Sequential(
            nn.Linear(hidden_dim, 64),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(64, 1),
            nn.Sigmoid(),    # 输出 0-1
        )
        self.sub_head = nn.Sequential(
            nn.Linear(hidden_dim, 64),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(64, 4),
            nn.Sigmoid(),    # 每个子分 0-1
        )

    def forward(self, x_dict: dict, edge_index_dict: dict) -> tuple[torch.Tensor, torch.Tensor]:
        # 输入投影
        h = {
            nt: F.relu(self.input_proj[nt](x))
            for nt, x in x_dict.items()
            if nt in self.input_proj
        }

        # HGT 消息传递（每层重新过滤，确保 src/dst 类型在当前 h 中）
        for conv in self.convs:
            active_edges = {
                key: ei for key, ei in edge_index_dict.items()
                if ei.size(1) > 0
                and key[0] in h
                and key[2] in h
            }
            h_new = conv(h, active_edges)
            # 残差 + LayerNorm（仅更新有新表示的节点类型）
            h = {
                nt: self.layer_norm[nt](self.dropout(h_new[nt]) + h[nt])
                for nt in h
                if nt in h_new and h_new[nt] is not None
            }

        # 取 application 节点的表示（每图只有一个）
        app_emb = h["application"]   # [batch_size, hidden_dim]

        score     = self.score_head(app_emb).squeeze(-1)    # [batch_size]
        sub_score = self.sub_head(app_emb)                  # [batch_size, 4]
        return score, sub_score


class RiskScoreLoss(nn.Module):
    """主分值 Huber loss + 子分 MSE loss 加权组合。"""

    def __init__(self, sub_weight: float = 0.3, delta: float = 0.1) -> None:
        super().__init__()
        self.sub_weight = sub_weight
        self.huber = nn.HuberLoss(delta=delta)

    def forward(
        self,
        pred_score: torch.Tensor,
        pred_sub: torch.Tensor,
        target_score: torch.Tensor,
        target_sub: torch.Tensor,
    ) -> tuple[torch.Tensor, dict]:
        main_loss = self.huber(pred_score, target_score)
        sub_loss  = F.mse_loss(pred_sub, target_sub)
        total     = main_loss + self.sub_weight * sub_loss
        return total, {"main": main_loss.item(), "sub": sub_loss.item()}
