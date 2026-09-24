import pytest
import torch
from app.ml.graph_builder import build_pyg_graph_data
from app.ml.gnn_model import SafetyGraphSAGE, train_gnn_risk_model, evaluate_gnn_vs_random_forest

def test_pyg_graph_builder():
    pyg_data, meta = build_pyg_graph_data()

    assert meta["num_nodes"] >= 50
    assert meta["num_edges"] >= 100
    assert meta["num_features"] == 5

    assert pyg_data.x.dim() == 2
    assert pyg_data.x.size(1) == 5
    assert pyg_data.edge_index.dim() == 2
    assert pyg_data.edge_index.size(0) == 2

def test_gnn_model_forward_pass():
    pyg_data, meta = build_pyg_graph_data()
    model = SafetyGraphSAGE(in_channels=5, hidden_channels=16, out_channels=1)

    model.eval()
    with torch.no_grad():
        out = model(pyg_data.x, pyg_data.edge_index)

    assert out.shape == (meta["num_nodes"], 1)
    assert not torch.isnan(out).any()

def test_gnn_vs_random_forest_benchmark():
    comp = evaluate_gnn_vs_random_forest()

    assert "random_forest_baseline" in comp
    assert "gnn_graphsage" in comp

    rf_r2 = comp["random_forest_baseline"]["r2_score"]
    gnn_r2 = comp["gnn_graphsage"]["r2_score"]

    assert 0.0 <= rf_r2 <= 1.0
    assert 0.0 <= gnn_r2 <= 1.0
