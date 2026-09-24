import os
import sys
import json
import torch
import numpy as np

# Add backend directory to sys.path for standalone script execution
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from typing import Tuple, Dict, Any, List
from torch_geometric.data import Data
from app.routing.osm_graphhopper import load_graph_data


DATASET_FILE = os.path.join(os.path.dirname(__file__), "..", "..", "data", "mumbai_safety_network.json")

def build_pyg_graph_data() -> Tuple[Data, Dict[str, Any]]:
    """
    Convert Mumbai street network into a PyTorch Geometric Data graph object.
    
    Node Features (x): [crime_score, lighting_score, cctv_density, crowd_density, normalized_length]
    Edge Index (edge_index): Undirected graph connections between adjacent street segments.
    Target (y): Safety score (0 to 100).
    """
    nodes, segments = load_graph_data()

    # Map node names to integer indices
    node_to_idx = {n["name"]: idx for idx, n in enumerate(nodes)}
    
    # Calculate feature tensors for segments/nodes
    num_nodes = len(nodes)

    # Initialize node feature aggregations
    node_features = np.zeros((num_nodes, 5), dtype=np.float32)
    node_targets = np.zeros((num_nodes, 1), dtype=np.float32)
    node_counts = np.zeros((num_nodes, 1), dtype=np.float32)

    edge_list = []

    for seg in segments:
        u_name = seg.get("u_node", f"{seg['start_lat']},{seg['start_lon']}")
        v_name = seg.get("v_node", f"{seg['end_lat']},{seg['end_lon']}")

        if u_name in node_to_idx and v_name in node_to_idx:
            u_idx = node_to_idx[u_name]
            v_idx = node_to_idx[v_name]

            # Undirected edge pair
            edge_list.append([u_idx, v_idx])
            edge_list.append([v_idx, u_idx])

            feat = [
                float(seg.get("crime_score", 0.3)),
                float(seg.get("lighting_score", 0.7)),
                float(seg.get("cctv_density", 0.5)),
                float(seg.get("crowd_density", 0.5)),
                float(seg.get("length_meters", 100.0)) / 1000.0  # Normalize length to km
            ]
            safety = float(seg.get("safety_score", 75.0))

            node_features[u_idx] += feat
            node_counts[u_idx] += 1
            node_targets[u_idx] += safety

            node_features[v_idx] += feat
            node_counts[v_idx] += 1
            node_targets[v_idx] += safety

    # Average features across connected edges
    node_counts = np.maximum(node_counts, 1.0)
    node_features = node_features / node_counts
    node_targets = node_targets / node_counts

    # Convert to PyTorch Tensors
    x_tensor = torch.tensor(node_features, dtype=torch.float)
    y_tensor = torch.tensor(node_targets, dtype=torch.float)

    if edge_list:
        edge_index_tensor = torch.tensor(edge_list, dtype=torch.long).t().contiguous()
    else:
        edge_index_tensor = torch.empty((2, 0), dtype=torch.long)

    pyg_data = Data(x=x_tensor, edge_index=edge_index_tensor, y=y_tensor)
    
    meta = {
        "num_nodes": num_nodes,
        "num_edges": edge_index_tensor.size(1) // 2,
        "num_features": x_tensor.size(1)
    }

    return pyg_data, meta

if __name__ == "__main__":
    data, meta = build_pyg_graph_data()
    print(f"[Graph Builder] Built PyTorch Geometric Data object: {meta}")
    print(f"[Graph Builder] Node Feature Matrix shape: {data.x.shape}")
    print(f"[Graph Builder] Edge Index shape: {data.edge_index.shape}")
