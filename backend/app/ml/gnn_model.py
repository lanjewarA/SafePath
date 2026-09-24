import os
import sys
import torch
import numpy as np
import torch.nn as nn
import torch.nn.functional as F

from typing import Dict, Any, Tuple
from torch_geometric.nn import SAGEConv, GCNConv

# Add backend directory to sys.path for standalone execution
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.ml.graph_builder import build_pyg_graph_data
from app.ml.baseline_rf import train_baseline_rf_model

GNN_MODEL_FILE = os.path.join(os.path.dirname(__file__), "gnn_model.pt")

class SafetyGraphSAGE(nn.Module):
    """
    2-Layer GraphSAGE Neural Network for Spatial Risk Propagation.
    Aggregates node & edge features from 2-hop connected street neighbors.
    """
    def __init__(self, in_channels: int = 5, hidden_channels: int = 32, out_channels: int = 1):
        super().__init__()
        self.conv1 = SAGEConv(in_channels, hidden_channels, aggr="mean")
        self.conv2 = SAGEConv(hidden_channels, hidden_channels, aggr="mean")
        self.regressor = nn.Sequential(
            nn.Linear(hidden_channels, 16),
            nn.ReLU(),
            nn.Linear(16, out_channels)
        )

    def forward(self, x: torch.Tensor, edge_index: torch.Tensor) -> torch.Tensor:
        # Layer 1 message passing
        h = self.conv1(x, edge_index)
        h = F.relu(h)
        h = F.dropout(h, p=0.1, training=self.training)

        # Layer 2 neighborhood aggregation
        h = self.conv2(h, edge_index)
        h = F.relu(h)

        # Output linear regression
        out = self.regressor(h)
        return out

def train_gnn_risk_model(epochs: int = 150, lr: float = 0.01) -> Tuple[SafetyGraphSAGE, Dict[str, float]]:
    """Train GraphSAGE GNN model and benchmark against Random Forest baseline."""
    pyg_data, meta = build_pyg_graph_data()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = SafetyGraphSAGE(in_channels=meta["num_features"], hidden_channels=32, out_channels=1).to(device)
    pyg_data = pyg_data.to(device)

    optimizer = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=1e-4)
    criterion = nn.MSELoss()

    model.train()
    for epoch in range(1, epochs + 1):
        optimizer.zero_grad()
        out = model(pyg_data.x, pyg_data.edge_index)
        loss = criterion(out, pyg_data.y)
        loss.backward()
        optimizer.step()

    # Evaluation
    model.eval()
    with torch.no_grad():
        preds = model(pyg_data.x, pyg_data.edge_index)
        mse = F.mse_loss(preds, pyg_data.y).item()
        rmse = float(np.sqrt(mse))
        mae = float(F.l1_loss(preds, pyg_data.y).item())

        # R2 score calculation
        y_true = pyg_data.y.cpu().numpy()
        y_pred = preds.cpu().numpy()
        ss_res = np.sum((y_true - y_pred) ** 2)
        ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)
        r2 = float(1.0 - (ss_res / (ss_tot + 1e-8)))

    metrics = {
        "gnn_rmse": round(rmse, 4),
        "gnn_mae": round(mae, 4),
        "gnn_r2": round(r2, 4),
        "epochs": epochs,
        "nodes": meta["num_nodes"],
        "edges": meta["num_edges"]
    }

    # Save model weights
    torch.save(model.state_dict(), GNN_MODEL_FILE)
    print(f"[GNN Model] GraphSAGE trained successfully ({epochs} epochs).")
    print(f"[GNN Model] Metrics -> RMSE: {metrics['gnn_rmse']}, MAE: {metrics['gnn_mae']}, R2 Score: {metrics['gnn_r2']}")

    return model, metrics

def evaluate_gnn_vs_random_forest() -> Dict[str, Any]:
    """Benchmark GraphSAGE GNN model performance against Random Forest baseline."""
    # 1. Train/load Random Forest metrics
    _, rf_metrics = train_baseline_rf_model()

    # 2. Train GNN metrics
    _, gnn_metrics = train_gnn_risk_model()

    comparison = {
        "random_forest_baseline": {
            "model_type": "RandomForestRegressor (scikit-learn)",
            "rmse": rf_metrics["rmse"],
            "r2_score": rf_metrics["r2_score"],
            "spatial_neighbor_propagation": False
        },
        "gnn_graphsage": {
            "model_type": "SafetyGraphSAGE (PyTorch Geometric)",
            "rmse": gnn_metrics["gnn_rmse"],
            "mae": gnn_metrics["gnn_mae"],
            "r2_score": gnn_metrics["gnn_r2"],
            "spatial_neighbor_propagation": True
        }
    }

    return comparison

if __name__ == "__main__":
    comp = evaluate_gnn_vs_random_forest()
    print("\n" + "="*50)
    print("MODEL BENCHMARK COMPARISON SUMMARY")
    print("="*50)
    print(f"Random Forest Baseline -> RMSE: {comp['random_forest_baseline']['rmse']}, R2: {comp['random_forest_baseline']['r2_score']}")
    print(f"GraphSAGE GNN Model    -> RMSE: {comp['gnn_graphsage']['rmse']}, R2: {comp['gnn_graphsage']['r2_score']}")
    print("="*50)
