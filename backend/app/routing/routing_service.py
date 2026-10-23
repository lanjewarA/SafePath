"""
Routing service: apply heat-point spatial penalties onto a NetworkX road graph
before Dijkstra / safest-path optimization.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

import networkx as nx

from app.routing.risk_engine import (
    ALPHA_BALANCED,
    ALPHA_SAFEST,
    blend_overall_risk,
    collect_active_heat_points,
    compute_edge_weight,
    compute_heat_penalties_idw,
    filter_nagpur_heat_points,
    load_heat_penalties,
)


def _edge_geometry(data: Dict[str, Any]) -> List[List[float]]:
    geom = data.get("geometry")
    if isinstance(geom, list) and len(geom) >= 2:
        return geom
    return [
        [float(data["start_lat"]), float(data["start_lon"])],
        [float(data["end_lat"]), float(data["end_lon"])],
    ]


def graph_segments_for_spatial_join(graph: nx.Graph) -> List[Dict[str, Any]]:
    """Flatten NetworkX edges into the payload expected by the IDW / PostGIS join."""
    rows: List[Dict[str, Any]] = []
    for _, _, data in graph.edges(data=True):
        rows.append(
            {
                "id": data.get("segment_id"),
                "start_lat": data.get("start_lat"),
                "start_lon": data.get("start_lon"),
                "end_lat": data.get("end_lat"),
                "end_lon": data.get("end_lon"),
                "geometry": _edge_geometry(data),
            }
        )
    return rows


def apply_spatial_heat_weights(
    graph: nx.Graph,
    heat_points: Optional[Iterable[Dict[str, Any]]] = None,
) -> nx.Graph:
    """
    Mutate `graph` in place:

    1. Spatially join heat points within 150 m of each edge (PostGIS or KDTree).
    2. Store normalized `heat_penalty` on the edge.
    3. Blend with baseline lighting/crime/crowd/GNN risk.
    4. Set Dijkstra weights:
         w_shortest = length
         w_safest   = length * (1 + 3.5 * overall_risk)
         w_balanced = length * (1 + 1.2 * overall_risk)
    """
    segments = graph_segments_for_spatial_join(graph)
    if heat_points is not None:
        points = filter_nagpur_heat_points(heat_points)
        penalties = compute_heat_penalties_idw(segments, points)
    else:
        points = collect_active_heat_points()
        penalties = load_heat_penalties(segments, points)

    affected = 0
    for _, _, data in graph.edges(data=True):
        seg_id = str(data.get("segment_id", ""))
        baseline = float(data.get("baseline_risk", data.get("final_risk", 0.25)))
        data["baseline_risk"] = baseline
        heat_penalty = float(penalties.get(seg_id, 0.0))
        data["heat_penalty"] = heat_penalty
        overall = blend_overall_risk(baseline, heat_penalty)
        data["final_risk"] = overall
        data["safety_score"] = round((1.0 - overall) * 100.0, 2)
        length = float(data.get("length", 0.0))
        data["w_shortest"] = length
        data["w_safest"] = compute_edge_weight(length, overall, ALPHA_SAFEST)
        data["w_balanced"] = compute_edge_weight(length, overall, ALPHA_BALANCED)
        if heat_penalty > 0.0:
            affected += 1

    print(
        f"[Routing Service] Applied heat penalties to {affected}/{graph.number_of_edges()} "
        f"edges from {len(points)} heat points."
    )
    return graph
