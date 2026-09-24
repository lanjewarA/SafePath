import os
import json
import networkx as nx
from typing import List, Dict, Any, Tuple
from app.db.supabase_client import fetch_all_segments
from app.ml.baseline_rf import predict_safety_score
from app.schemas.route_schema import RouteOption, SegmentDetail, RouteResponse

DATASET_FILE = os.path.join(os.path.dirname(__file__), "..", "..", "data", "mumbai_safety_network.json")

def load_graph_data() -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Load street segments and nodes from Supabase DB or local JSON file fallback."""
    db_segments = fetch_all_segments()
    if db_segments and len(db_segments) >= 10:
        print(f"[Routing Engine] Loaded {len(db_segments)} segments from Supabase PostGIS.")
        # Deduplicate nodes from DB segments
        nodes_dict = {}
        for s in db_segments:
            nodes_dict[s.get("u_node", s["start_lat"])] = {"name": s.get("u_node", "Start"), "lat": s["start_lat"], "lon": s["start_lon"]}
            nodes_dict[s.get("v_node", s["end_lat"])] = {"name": s.get("v_node", "End"), "lat": s["end_lat"], "lon": s["end_lon"]}
        return list(nodes_dict.values()), db_segments

    # Fallback to local dataset file
    if os.path.exists(DATASET_FILE):
        with open(DATASET_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data["nodes"], data["segments"]

    raise FileNotFoundError("No street segment data available for routing!")

def build_networkx_graph(segments: List[Dict[str, Any]]) -> nx.Graph:
    """Build NetworkX undirected graph from street segments."""
    G = nx.Graph()

    for seg in segments:
        u = seg.get("u_node", f"{seg['start_lat']},{seg['start_lon']}")
        v = seg.get("v_node", f"{seg['end_lat']},{seg['end_lon']}")

        # Ensure dynamic RF safety score prediction if missing
        safety = seg.get("safety_score")
        if safety is None:
            safety = predict_safety_score(
                seg.get("crime_score", 0.3),
                seg.get("lighting_score", 0.7),
                seg.get("cctv_density", 0.5),
                seg.get("crowd_density", 0.5)
            )

        G.add_edge(
            u, v,
            segment_id=seg.get("id", f"seg-{seg['osm_id']}"),
            name=seg.get("name", "Connector"),
            length=float(seg["length_meters"]),
            safety_score=float(safety),
            crime_score=float(seg.get("crime_score", 0.3)),
            lighting_score=float(seg.get("lighting_score", 0.7)),
            cctv_density=float(seg.get("cctv_density", 0.5)),
            crowd_density=float(seg.get("crowd_density", 0.5)),
            start_lat=float(seg["start_lat"]),
            start_lon=float(seg["start_lon"]),
            end_lat=float(seg["end_lat"]),
            end_lon=float(seg["end_lon"]),
        )

    return G

def find_closest_node(graph: nx.Graph, nodes: List[Dict[str, Any]], query: str, lat: float = None, lon: float = None) -> str:
    """Find closest graph node matching name query or lat/lon coordinates."""
    if not nodes:
        return list(graph.nodes())[0]

    if query:
        query_lower = query.lower()
        for n in nodes:
            if query_lower in n["name"].lower():
                if n["name"] in graph:
                    return n["name"]

    # Coordinate distance matching if provided
    if lat is not None and lon is not None:
        best_node = None
        best_dist = float("inf")
        for n in nodes:
            dist = math.hypot(n["lat"] - lat, n["lon"] - lon)
            if dist < best_dist and n["name"] in graph:
                best_dist = dist
                best_node = n["name"]
        if best_node:
            return best_node

    # Default to first available node in graph
    return list(graph.nodes())[0]

def compute_route_metrics(graph: nx.Graph, path: List[str], route_id: str, name: str, description: str, color: str) -> RouteOption:
    """Calculate aggregate distance, composite safety score, and coordinates for a node path."""
    segment_details: List[SegmentDetail] = []
    coordinates: List[List[float]] = []
    total_distance = 0.0
    weighted_safety_sum = 0.0

    for i in range(len(path) - 1):
        u, v = path[i], path[i + 1]
        edge = graph[u][v]

        length = edge["length"]
        safety = edge["safety_score"]

        total_distance += length
        weighted_safety_sum += (safety * length)

        if not coordinates:
            coordinates.append([edge["start_lat"], edge["start_lon"]])
        coordinates.append([edge["end_lat"], edge["end_lon"]])

        segment_details.append(SegmentDetail(
            id=edge["segment_id"],
            name=edge["name"],
            length_meters=length,
            safety_score=safety,
            crime_score=edge["crime_score"],
            lighting_score=edge["lighting_score"],
            cctv_density=edge["cctv_density"],
            crowd_density=edge["crowd_density"],
            start_lat=edge["start_lat"],
            start_lon=edge["start_lon"],
            end_lat=edge["end_lat"],
            end_lon=edge["end_lon"]
        ))

    composite_safety = round(weighted_safety_sum / total_distance, 2) if total_distance > 0 else 75.0
    dist_km = round(total_distance / 1000.0, 2)
    walk_mins = max(1, int(round((total_distance / 1.4) / 60.0)))  # 1.4 m/s average walking speed

    if composite_safety >= 78:
        category = "High Safety"
    elif composite_safety >= 58:
        category = "Moderate Safety"
    else:
        category = "Caution Required"

    return RouteOption(
        route_id=route_id,
        name=name,
        description=description,
        total_distance_meters=round(total_distance, 1),
        total_distance_km=dist_km,
        estimated_walk_minutes=walk_mins,
        composite_safety_score=composite_safety,
        safety_category=category,
        color=color,
        segments=segment_details,
        coordinates=coordinates
    )

def calculate_safepath_routes(
    origin_name: str = "Mumbai Central",
    destination_name: str = "Bandra West",
    origin_lat: float = None,
    origin_lon: float = None,
    dest_lat: float = None,
    dest_lon: float = None
) -> RouteResponse:
    """Calculate multi-route options (Safest, Shortest, Balanced) using NetworkX pathfinding."""
    nodes, segments = load_graph_data()
    G = build_networkx_graph(segments)

    start_node = find_closest_node(G, nodes, origin_name, origin_lat, origin_lon)
    end_node = find_closest_node(G, nodes, destination_name, dest_lat, dest_lon)

    if start_node == end_node:
        # Avoid zero-length route
        all_nodes = list(G.nodes())
        end_node = all_nodes[1] if len(all_nodes) > 1 else start_node

    # 1. Shortest Route (lambda = 0.0)
    for u, v, d in G.edges(data=True):
        d["weight_shortest"] = d["length"]

    try:
        shortest_path = nx.dijkstra_path(G, start_node, end_node, weight="weight_shortest")
    except nx.NetworkXNoPath:
        shortest_path = [start_node, end_node]

    # 2. Safest Route (lambda = 3.0)
    for u, v, d in G.edges(data=True):
        risk_penalty = 1.0 + 3.0 * (1.0 - d["safety_score"] / 100.0)
        d["weight_safest"] = d["length"] * risk_penalty

    try:
        safest_path = nx.dijkstra_path(G, start_node, end_node, weight="weight_safest")
    except nx.NetworkXNoPath:
        safest_path = shortest_path

    # 3. Balanced Route (lambda = 1.0)
    for u, v, d in G.edges(data=True):
        risk_penalty = 1.0 + 1.0 * (1.0 - d["safety_score"] / 100.0)
        d["weight_balanced"] = d["length"] * risk_penalty

    try:
        balanced_path = nx.dijkstra_path(G, start_node, end_node, weight="weight_balanced")
    except nx.NetworkXNoPath:
        balanced_path = shortest_path

    # Construct RouteOption objects
    r_safest = compute_route_metrics(
        G, safest_path, "route-safest", "Safest Route",
        "Maximizes well-lit, CCTV-monitored, and highly populated streets", "#10b981"
    )
    r_balanced = compute_route_metrics(
        G, balanced_path, "route-balanced", "Balanced Route",
        "Optimal balance between walking distance and safety ratings", "#f59e0b"
    )
    r_shortest = compute_route_metrics(
        G, shortest_path, "route-shortest", "Shortest Route",
        "Direct path minimizing total distance regardless of safety score", "#ef4444"
    )

    routes = [r_safest, r_balanced, r_shortest]

    return RouteResponse(
        origin=start_node,
        destination=end_node,
        routes_found=len(routes),
        recommended_route_id="route-safest",
        routes=routes
    )

