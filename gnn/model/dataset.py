"""
GNN 数据集加载器。

从 gnn/data/graphs/*.json（图规格）加载数据，转为 PyG HeteroData，
支持 train/val/test 切分。

用法：
  from dataset import RiskGraphDataset
  dataset = RiskGraphDataset("../data/graphs")
  train_ds, val_ds, test_ds = dataset.split(0.8, 0.1, 0.1)
"""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Optional

import torch
from torch.utils.data import Dataset
from torch_geometric.data import HeteroData


def _spec_to_heterodata(spec: dict) -> HeteroData:
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
    # 存在 application 节点上，批处理时可正确 stack
    data["application"].y     = torch.tensor([[lbl["score_norm"]]], dtype=torch.float)
    data["application"].y_raw = torch.tensor([[lbl["score"]]], dtype=torch.float)
    data["application"].y_sub = torch.tensor([lbl["sub_scores_norm"]], dtype=torch.float)
    data.case_id    = spec["case_id"]
    data.fraud_type = spec["fraud_type"]
    return data


class RiskGraphDataset(Dataset):
    def __init__(
        self,
        graphs_dir: str | Path,
        max_samples: Optional[int] = None,
        seed: int = 42,
    ) -> None:
        self.graphs_dir = Path(graphs_dir)
        self._paths = sorted(self.graphs_dir.glob("*.json"))
        if max_samples:
            rng = random.Random(seed)
            self._paths = rng.sample(self._paths, min(max_samples, len(self._paths)))
        print(f"RiskGraphDataset: {len(self._paths)} graphs from {self.graphs_dir}")

    def __len__(self) -> int:
        return len(self._paths)

    def __getitem__(self, idx: int) -> HeteroData:
        spec = json.loads(self._paths[idx].read_text(encoding="utf-8"))
        return _spec_to_heterodata(spec)

    def split(
        self,
        train_ratio: float = 0.8,
        val_ratio: float = 0.1,
        test_ratio: float = 0.1,
        seed: int = 42,
    ) -> tuple["RiskGraphDataset", "RiskGraphDataset", "RiskGraphDataset"]:
        assert abs(train_ratio + val_ratio + test_ratio - 1.0) < 1e-6
        paths = self._paths.copy()
        random.Random(seed).shuffle(paths)
        n = len(paths)
        n_train = int(n * train_ratio)
        n_val   = int(n * val_ratio)

        train_ds = self._clone_with_paths(paths[:n_train])
        val_ds   = self._clone_with_paths(paths[n_train:n_train + n_val])
        test_ds  = self._clone_with_paths(paths[n_train + n_val:])
        return train_ds, val_ds, test_ds

    def _clone_with_paths(self, paths: list[Path]) -> "RiskGraphDataset":
        ds = object.__new__(RiskGraphDataset)
        ds.graphs_dir = self.graphs_dir
        ds._paths = paths
        return ds
