"""
训练脚本。

用法：
  # 用 anti_fraud conda 环境（有 torch）
  /opt/anaconda3/envs/anti_fraud/bin/python3 train.py

  # 先安装 torch_geometric（若未装）：
  /opt/anaconda3/envs/anti_fraud/bin/pip install torch_geometric

  # 自定义参数：
  python3 train.py --epochs 50 --batch-size 32 --hidden-dim 128 --lr 1e-3
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import torch
from torch.utils.data import DataLoader
from torch_geometric.data import HeteroData
from torch_geometric.loader import DataLoader as PyGDataLoader

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))

from dataset import RiskGraphDataset
from model import RiskScoreGNN, RiskScoreLoss


def collate_fn(batch: list[HeteroData]):
    from torch_geometric.data import Batch
    return Batch.from_data_list(batch)


def evaluate(model: RiskScoreGNN, loader, loss_fn: RiskScoreLoss, device: torch.device):
    model.eval()
    total_loss, total_mae, n = 0.0, 0.0, 0
    with torch.no_grad():
        for batch in loader:
            batch = batch.to(device)
            pred_score, pred_sub = model(batch.x_dict, batch.edge_index_dict)
            target_score = batch["application"].y.squeeze(-1)
            target_sub   = batch["application"].y_sub

            loss, _ = loss_fn(pred_score, pred_sub, target_score, target_sub)
            mae = (pred_score - target_score).abs().mean().item()

            total_loss += loss.item() * len(pred_score)
            total_mae  += mae * len(pred_score)
            n += len(pred_score)
    return total_loss / n, total_mae / n


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--graphs-dir",  default=str(ROOT / "data" / "graphs"))
    parser.add_argument("--epochs",      type=int,   default=30)
    parser.add_argument("--batch-size",  type=int,   default=32)
    parser.add_argument("--hidden-dim",  type=int,   default=128)
    parser.add_argument("--num-layers",  type=int,   default=3)
    parser.add_argument("--lr",          type=float, default=1e-3)
    parser.add_argument("--dropout",     type=float, default=0.1)
    parser.add_argument("--max-samples", type=int,   default=None,
                        help="限制最大样本数（调试用）")
    parser.add_argument("--checkpoint",  default=str(ROOT / "model" / "checkpoint.pt"))
    args = parser.parse_args()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"设备: {device}")

    # ── 数据集 ────────────────────────────────────────────────────────────────
    dataset = RiskGraphDataset(args.graphs_dir, max_samples=args.max_samples)
    train_ds, val_ds, test_ds = dataset.split(0.8, 0.1, 0.1)
    print(f"训练: {len(train_ds)}  验证: {len(val_ds)}  测试: {len(test_ds)}")

    train_loader = PyGDataLoader(train_ds, batch_size=args.batch_size, shuffle=True)
    val_loader   = PyGDataLoader(val_ds,   batch_size=args.batch_size)
    test_loader  = PyGDataLoader(test_ds,  batch_size=args.batch_size)

    # ── 模型 ──────────────────────────────────────────────────────────────────
    model = RiskScoreGNN(
        hidden_dim=args.hidden_dim,
        num_layers=args.num_layers,
        dropout=args.dropout,
    ).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=args.epochs)
    loss_fn   = RiskScoreLoss()

    best_val_mae = float("inf")
    history: list[dict] = []

    print(f"\n开始训练（{args.epochs} epochs）...\n")

    for epoch in range(1, args.epochs + 1):
        model.train()
        epoch_loss, epoch_mae, n = 0.0, 0.0, 0
        t0 = time.time()

        for batch in train_loader:
            batch = batch.to(device)
            optimizer.zero_grad()

            pred_score, pred_sub = model(batch.x_dict, batch.edge_index_dict)
            target_score = batch["application"].y.squeeze(-1)
            target_sub   = batch["application"].y_sub

            loss, parts = loss_fn(pred_score, pred_sub, target_score, target_sub)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()

            mae = (pred_score - target_score).abs().mean().item()
            epoch_loss += loss.item() * len(pred_score)
            epoch_mae  += mae * len(pred_score)
            n += len(pred_score)

        scheduler.step()
        train_loss = epoch_loss / n
        train_mae  = epoch_mae / n * 100   # 转回 0-100 尺度

        val_loss, val_mae = evaluate(model, val_loader, loss_fn, device)
        val_mae *= 100

        elapsed = time.time() - t0
        row = {"epoch": epoch, "train_loss": train_loss, "train_mae": train_mae,
               "val_loss": val_loss, "val_mae": val_mae}
        history.append(row)

        marker = " ◀ best" if val_mae < best_val_mae else ""
        print(f"Epoch {epoch:3d}/{args.epochs}  "
              f"train_loss={train_loss:.4f}  train_mae={train_mae:.2f}  "
              f"val_loss={val_loss:.4f}  val_mae={val_mae:.2f}  "
              f"({elapsed:.1f}s){marker}")

        if val_mae < best_val_mae:
            best_val_mae = val_mae
            torch.save({"epoch": epoch, "model": model.state_dict(),
                        "val_mae": val_mae, "args": vars(args)},
                       args.checkpoint)

    # ── 测试集评估 ────────────────────────────────────────────────────────────
    ckpt = torch.load(args.checkpoint, map_location=device)
    model.load_state_dict(ckpt["model"])
    test_loss, test_mae = evaluate(model, test_loader, loss_fn, device)
    print(f"\n最佳 val_mae={best_val_mae:.2f}  test_mae={test_mae*100:.2f}")

    # 保存训练历史
    history_path = Path(args.checkpoint).parent / "train_history.json"
    history_path.write_text(json.dumps(history, indent=2), encoding="utf-8")
    print(f"训练历史已保存: {history_path}")


if __name__ == "__main__":
    main()
