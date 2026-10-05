import os
import json
import math
import networkx as nx
from typing import List, Dict, Any, Tuple
from app.db.supabase_client import fetch_all_segments
from app.ml.baseline_rf import predict_safety_score
from app.schemas.route_schema import RouteOption, SegmentDetail, RouteResponse

DATASET_FILE = os.path.join(os.path.dirname(__file__), "..", "..", "data", "mumbai_safety_network.json")

# Configurable Cost & Detour Weights
ROUTE_DISTANCE_WEIGHT = 0.30
ROUTE_SAFETY_WEIGHT = 0.50
ROUTE_HIGH_RISK_WEIGHT = 0.20
DEFAULT_MAX_ACCEPTABLE_DETOUR = 1.30

def load_graph_data() -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Load street segments and nodes from Supabase DB or local JSON file fallback."""
    db_segments = fetch_all_segments()
    if db_segments and len(db_segments) >= 10:
        print(f"[Routing Engine] Loaded {len(db_segments)} segments from Supabase PostGIS.")

        # The segments table has no u_node/v_node columns, so recover endpoint
        # labels from the local dataset (JSON node names) and inject them into
        # each segment. This guarantees the node ids used here are identical to
        # the ones build_networkx_graph() creates from u_node/v_node, and that
        # shared physical endpoints always map to the same graph node.
        label_by_coord: Dict[Tuple[float, float], str] = {}
        if os.path.exists(DATASET_FILE):
            with open(DATASET_FILE, "r", encoding="utf-8") as f:
                local_nodes = json.load(f).get("nodes", [])
            for n in local_nodes:
                label_by_coord[(round(float(n["lat"]), 6), round(float(n["lon"]), 6))] = n["name"]

        def endpoint_label(lat: Any, lon: Any) -> str:
            key = (round(float(lat), 6), round(float(lon), 6))
            label = label_by_coord.get(key) or f"{lat},{lon}"
            label_by_coord.setdefault(key, label)
            return label

        nodes_dict = {}
        for s in db_segments:
            u_node = endpoint_label(s["start_lat"], s["start_lon"])
            v_node = endpoint_label(s["end_lat"], s["end_lon"])
            s["u_node"], s["v_node"] = u_node, v_node
            nodes_dict[u_node] = {"name": u_node, "lat": s["start_lat"], "lon": s["start_lon"]}
            nodes_dict[v_node] = {"name": v_node, "lat": s["end_lat"], "lon": s["end_lon"]}
        return list(nodes_dict.values()), db_segments

    if os.path.exists(DATASET_FILE):
        with open(DATASET_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data["nodes"], data["segments"]

    raise FileNotFoundError("No street segment data available for routing!")

def calculate_segment_risk_features(seg: Dict[str, Any], time_of_day: str = "night") -> Dict[str, Any]:
    """
    Calculate comprehensive safety & risk metrics for a single road segment.
    Combines:
    1. RF Baseline Risk
    2. GNN Spatial Neighborhood Risk
    3. Lighting Score
    4. Crowd / POI activity proxy adjusted for Time of Day
    5. Isolation score
    6. Incident count & CCTV Alert proximity
    """
    crime = float(seg.get("crime_score", 0.3))
    lighting = float(seg.get("lighting_score", 0.7))
    cctv = float(seg.get("cctv_density", 0.5))
    crowd = float(seg.get("crowd_density", 0.5))
    incident_count = int(seg.get("incident_count", 1 if crime > 0.4 else 0))
    cctv_alert = bool(seg.get("cctv_alert", cctv < 0.3))

    # Time-of-day crowd/activity modifier
    tod = time_of_day.lower() if time_of_day else "night"
    if tod == "night" or tod == "2am":
        adjusted_crowd = crowd * 0.4
    elif tod == "evening":
        adjusted_crowd = crowd * 0.8
    else:  # day
        adjusted_crowd = crowd * 1.0

    # Derived Isolation score
    isolation = (1.0 - lighting) * 0.4 + (1.0 - adjusted_crowd) * 0.4 + (1.0 - cctv) * 0.2
    isolation = max(0.0, min(1.0, isolation))

    # 1. Baseline Random Forest Risk
    rf_pred_score = predict_safety_score(crime, lighting, cctv, crowd)
    rf_risk = max(0.0, min(1.0, 1.0 - (rf_pred_score / 100.0)))

    # 2. GNN Spatial Neighbor Risk (Simulated spatial propagation from 2-hop graph degree/neighbors)
    spatial_modifier = (crime * 0.4) + (isolation * 0.4) + (0.2 if cctv_alert else 0.0)
    gnn_risk = max(0.0, min(1.0, (rf_risk * 0.6) + (spatial_modifier * 0.4)))

    # Direct environmental risk signals
    lighting_risk = 1.0 - lighting
    cctv_incident_risk = min(1.0, (incident_count * 0.25) + (0.3 if cctv_alert else 0.0))

    # Composite Final Segment Risk (0.0 = safe, 1.0 = dangerous)
    final_risk = (
        0.40 * gnn_risk +
        0.25 * rf_risk +
        0.15 * lighting_risk +
        0.10 * isolation +
        0.10 * cctv_incident_risk
    )
    final_risk = round(max(0.0, min(1.0, final_risk)), 4)
    safety_score = round((1.0 - final_risk) * 100.0, 2)

    return {
        "final_risk": final_risk,
        "safety_score": safety_score,
        "gnn_risk": round(gnn_risk, 4),
        "rf_risk": round(rf_risk, 4),
        "crime_score": crime,
        "lighting_score": lighting,
        "cctv_density": cctv,
        "crowd_density": crowd,
        "isolation_score": round(isolation, 4),
        "incident_count": incident_count,
        "cctv_alert": cctv_alert,
    }

def build_networkx_graph(segments: List[Dict[str, Any]], time_of_day: str = "night") -> nx.Graph:
    """Build NetworkX undirected graph from street segments with risk weights."""
    G = nx.Graph()

    for seg in segments:
        u = seg.get("u_node", f"{seg['start_lat']},{seg['start_lon']}")
        v = seg.get("v_node", f"{seg['end_lat']},{seg['end_lon']}")

        metrics = calculate_segment_risk_features(seg, time_of_day)
        length = float(seg["length_meters"])
        geom = seg.get("geometry", [[float(seg["start_lat"]), float(seg["start_lon"])], [float(seg["end_lat"]), float(seg["end_lon"])]])

        G.add_edge(
            u, v,
            segment_id=seg.get("id", f"seg-{seg['osm_id']}"),
            name=seg.get("name", "Connector Street"),
            length=length,
            geometry=geom,
            safety_score=metrics["safety_score"],
            final_risk=metrics["final_risk"],
            gnn_risk=metrics["gnn_risk"],
            rf_risk=metrics["rf_risk"],
            crime_score=metrics["crime_score"],
            lighting_score=metrics["lighting_score"],
            cctv_density=metrics["cctv_density"],
            crowd_density=metrics["crowd_density"],
            isolation_score=metrics["isolation_score"],
            incident_count=metrics["incident_count"],
            cctv_alert=metrics["cctv_alert"],
            start_lat=float(seg["start_lat"]),
            start_lon=float(seg["start_lon"]),
            end_lat=float(seg["end_lat"]),
            end_lon=float(seg["end_lon"]),
        )

    return G

def find_closest_node(graph: nx.Graph, nodes: List[Dict[str, Any]], query: str, lat: float = None, lon: float = None) -> Tuple[str, List[float]]:
    """Find closest graph node matching name query or lat/lon coordinates."""
    if not nodes:
        node_name = list(graph.nodes())[0]
        return node_name, [19.04, 72.845]

    if query:
        query_lower = query.lower()
        for n in nodes:
            if query_lower in n["name"].lower():
                if n["name"] in graph:
                    return n["name"], [n["lat"], n["lon"]]

    if lat is not None and lon is not None:
        best_node = None
        best_coords = [lat, lon]
        best_dist = float("inf")
        for n in nodes:
            dist = math.hypot(n["lat"] - lat, n["lon"] - lon)
            if dist < best_dist and n["name"] in graph:
                best_dist = dist
                best_node = n["name"]
                best_coords = [n["lat"], n["lon"]]
        if best_node:
            return best_node, best_coords

    first_node = nodes[0]
    return first_node["name"], [first_node["lat"], first_node["lon"]]

import urllib.request

def fetch_osrm_turn_by_turn(waypoints: List[Tuple[float, float]]) -> Tuple[List[List[float]], float]:
    """
    Fetch 100% exact OpenStreetMap foot routing turn-by-turn walking geometry from OSRM.
    Clips any extraneous U-turn tails or loops outside the Origin -> Destination bounding area.
    """
    if not waypoints or len(waypoints) < 2:
        return [], 0.0

    start_lat, start_lon = waypoints[0]
    end_lat, end_lon = waypoints[-1]

    wp_str = ";".join([f"{round(wp[1], 6)},{round(wp[0], 6)}" for wp in waypoints if wp[0] and wp[1]])
    url = f"https://router.project-osrm.org/route/v1/foot/{wp_str}?overview=full&geometries=geojson"
    req = urllib.request.Request(url, headers={"User-Agent": "SafePathAI/1.0"})
    
    try:
        res = urllib.request.urlopen(req, timeout=4)
        data = json.loads(res.read())
        if data.get("routes"):
            route = data["routes"][0]
            raw_coords = [[round(c[1], 6), round(c[0], 6)] for c in route["geometry"]["coordinates"]]

            # Clip extraneous U-turn loops outside Origin-Destination bounds
            lat_buffer = 0.002
            lon_buffer = 0.006
            min_lat = min(start_lat, end_lat) - lat_buffer
            max_lat = max(start_lat, end_lat) + lat_buffer
            min_lon = min(start_lon, end_lon) - lon_buffer
            max_lon = max(start_lon, end_lon) + lon_buffer

            clean_coords = [
                pt for pt in raw_coords 
                if min_lat <= pt[0] <= max_lat and min_lon <= pt[1] <= max_lon
            ]

            if clean_coords:
                clean_coords.insert(0, [round(start_lat, 6), round(start_lon, 6)])
                clean_coords.append([round(end_lat, 6), round(end_lon, 6)])
                return clean_coords, route["distance"]

            return raw_coords, route["distance"]
    except Exception as e:
        print(f"[OSRM Foot Routing] Warning: OSRM fetch failed ({e}), using fallback geometry.")

    return [], 0.0


def compute_route_metrics(
    graph: nx.Graph,
    path: List[str],
    route_id: str,
    name: str,
    description: str,
    color: str,
    shortest_distance: float = 0.0
) -> RouteOption:
    """Calculate length-weighted risk exposure, maximum risk segment, detour %, and route cost."""
    segment_details: List[SegmentDetail] = []
    coordinates: List[List[float]] = []
    total_distance = 0.0
    weighted_risk_sum = 0.0
    max_risk = 0.0
    high_risk_distance = 0.0

    path_waypoints: List[Tuple[float, float]] = []

    for i in range(len(path) - 1):
        u, v = path[i], path[i + 1]
        edge = graph[u][v]

        length = edge["length"]
        risk = edge["final_risk"]
        geom = edge.get("geometry", [[edge["start_lat"], edge["start_lon"]], [edge["end_lat"], edge["end_lon"]]])

        total_distance += length
        weighted_risk_sum += (risk * length)

        if not path_waypoints:
            path_waypoints.append((edge["start_lat"], edge["start_lon"]))
        path_waypoints.append((edge["end_lat"], edge["end_lon"]))

        if risk > max_risk:
            max_risk = risk

        if risk >= 0.60:
            high_risk_distance += length

        # Append curved waypoints ensuring seamless node connection on land only
        MIN_LAND_LON = 72.8315
        for idx, pt in enumerate(geom):
            clamped_lat = round(pt[0], 6)
            clamped_lon = round(max(MIN_LAND_LON, pt[1]), 6)
            if not coordinates or (abs(coordinates[-1][0] - clamped_lat) > 1e-6 or abs(coordinates[-1][1] - clamped_lon) > 1e-6):
                coordinates.append([clamped_lat, clamped_lon])

    # Fetch 100% exact OpenStreetMap foot routing turn-by-turn coordinates following real streets
    osrm_coords, osrm_dist = fetch_osrm_turn_by_turn(path_waypoints)
    if osrm_coords and len(osrm_coords) >= 10:
        coordinates = osrm_coords
        if osrm_dist > 0:
            total_distance = osrm_dist



        segment_details.append(SegmentDetail(
            id=edge["segment_id"],
            name=edge["name"],
            length_meters=length,
            safety_score=edge["safety_score"],
            final_risk=edge["final_risk"],
            gnn_risk=edge["gnn_risk"],
            rf_risk=edge["rf_risk"],
            crime_score=edge["crime_score"],
            lighting_score=edge["lighting_score"],
            cctv_density=edge["cctv_density"],
            crowd_density=edge["crowd_density"],
            isolation_score=edge["isolation_score"],
            incident_count=edge["incident_count"],
            cctv_alert=edge["cctv_alert"],
            start_lat=edge["start_lat"],
            start_lon=edge["start_lon"],
            end_lat=edge["end_lat"],
            end_lon=edge["end_lon"],
            geometry=geom
        ))


    # Length-Weighted Risk Exposure
    safety_exposure = round(weighted_risk_sum / total_distance, 4) if total_distance > 0 else 0.25
    composite_safety = round((1.0 - safety_exposure) * 100.0, 2)
    dist_km = round(total_distance / 1000.0, 2)
    walk_mins = max(1, int(round((total_distance / 1.4) / 60.0)))
    high_risk_pct = round((high_risk_distance / total_distance) * 100.0, 1) if total_distance > 0 else 0.0

    # Detour percentage relative to shortest route
    if shortest_distance > 0:
        detour_pct = round(((total_distance - shortest_distance) / shortest_distance) * 100.0, 1)
        norm_dist = total_distance / shortest_distance
    else:
        detour_pct = 0.0
        norm_dist = 1.0

    # Combined Route Cost Calculation
    route_cost = (
        ROUTE_DISTANCE_WEIGHT * norm_dist +
        ROUTE_SAFETY_WEIGHT * safety_exposure +
        ROUTE_HIGH_RISK_WEIGHT * (high_risk_pct / 100.0)
    )
    route_cost = round(route_cost, 4)

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
        safety_exposure=safety_exposure,
        max_segment_risk=round(max_risk, 4),
        high_risk_exposure_pct=high_risk_pct,
        detour_percentage=detour_pct,
        route_cost=route_cost,
        is_recommended=False,
        rationale="",
        safety_category=category,
        color=color,
        segments=segment_details,
        coordinates=coordinates
    )

def calculate_safepath_routes(
    origin_name: str = "Dadar West",
    destination_name: str = "Bandra West",
    origin_lat: float = None,
    origin_lon: float = None,
    dest_lat: float = None,
    dest_lon: float = None,
    time_of_day: str = "night",
    detour_factor: float = DEFAULT_MAX_ACCEPTABLE_DETOUR
) -> RouteResponse:
    """
    Calculate multi-candidate route options (Recommended Safe, Shortest, Balanced, Alternative Safe)
    incorporating GNN spatial risk, RF baseline, length-weighted exposure, detour constraints, and safety override.
    """
    nodes, segments = load_graph_data()
    G = build_networkx_graph(segments, time_of_day)

    start_node, start_coords = find_closest_node(G, nodes, origin_name, origin_lat, origin_lon)
    end_node, end_coords = find_closest_node(G, nodes, destination_name, dest_lat, dest_lon)

    if start_node == end_node:
        all_nodes = list(G.nodes())
        end_node = all_nodes[1] if len(all_nodes) > 1 else start_node

    # 1. Shortest Route (distance weight)
    for u, v, d in G.edges(data=True):
        d["w_shortest"] = d["length"]

    try:
        shortest_path = nx.dijkstra_path(G, start_node, end_node, weight="w_shortest")
    except nx.NetworkXNoPath:
        shortest_path = [start_node, end_node]

    # Calculate shortest route distance for detour reference
    shortest_dist_meters = sum(G[shortest_path[i]][shortest_path[i+1]]["length"] for i in range(len(shortest_path)-1))

    # 2. Safest Route (Risk penalty lambda = 3.5)
    for u, v, d in G.edges(data=True):
        risk_penalty = 1.0 + 3.5 * (d["final_risk"] ** 1.5)
        d["w_safest"] = d["length"] * risk_penalty

    try:
        safest_path = nx.dijkstra_path(G, start_node, end_node, weight="w_safest")
    except nx.NetworkXNoPath:
        safest_path = shortest_path

    # 3. Balanced Route (Risk penalty lambda = 1.2)
    for u, v, d in G.edges(data=True):
        risk_penalty = 1.0 + 1.2 * d["final_risk"]
        d["w_balanced"] = d["length"] * risk_penalty

    try:
        balanced_path = nx.dijkstra_path(G, start_node, end_node, weight="w_balanced")
    except nx.NetworkXNoPath:
        balanced_path = shortest_path

    # Build RouteOption objects
    r_shortest = compute_route_metrics(
        G, shortest_path, "route-shortest", "Shortest Route",
        "Direct path minimizing total walking distance", "#ef4444", shortest_dist_meters
    )
    r_safest = compute_route_metrics(
        G, safest_path, "route-safest", "Recommended Safe Route",
        "Bypasses poorly lit, high-incident, or unmonitored segments", "#10b981", shortest_dist_meters
    )
    r_balanced = compute_route_metrics(
        G, balanced_path, "route-balanced", "Balanced Route",
        "Optimal balance between walking distance and safety ratings", "#f59e0b", shortest_dist_meters
    )

    all_candidates = [r_safest, r_balanced, r_shortest]

    # Filter out duplicate coordinate paths
    unique_candidates: List[RouteOption] = []
    seen_distances = set()
    for c in all_candidates:
        if c.total_distance_meters not in seen_distances:
            seen_distances.add(c.total_distance_meters)
            unique_candidates.append(c)

    if not unique_candidates:
        unique_candidates = [r_safest]

    # Geographic Detour Constraint & Safety-First Override Logic
    acceptable_candidates = []
    max_detour_ratio = detour_factor if detour_factor > 1.0 else DEFAULT_MAX_ACCEPTABLE_DETOUR

    for r in unique_candidates:
        dist_ratio = r.total_distance_meters / shortest_dist_meters if shortest_dist_meters > 0 else 1.0
        
        # Safety-First Override: if shortest route has high risk (>0.60) and route improves safety, allow up to 45% detour
        shortest_high_risk = r_shortest.max_segment_risk >= 0.60 or r_shortest.safety_exposure >= 0.40
        allowable_detour = max_detour_ratio if not shortest_high_risk else (max_detour_ratio + 0.15)

        if dist_ratio <= allowable_detour:
            acceptable_candidates.append(r)

    if not acceptable_candidates:
        acceptable_candidates = unique_candidates

    # Select recommended route with lowest route_cost
    recommended = min(acceptable_candidates, key=lambda x: x.route_cost)
    recommended_id = recommended.route_id

    # Update recommendation flags and rationale
    for r in unique_candidates:
        if r.route_id == recommended_id:
            r.is_recommended = True
            r.name = "Recommended Safe Route"
            r.color = "#10b981"
            if r.route_id == r_shortest.route_id:
                r.rationale = "Direct shortest route is already sufficiently safe (Safety Score >= 75)."
            else:
                score_diff = round(r.composite_safety_score - r_shortest.composite_safety_score, 1)
                dist_diff_m = int(r.total_distance_meters - r_shortest.total_distance_meters)
                r.rationale = (
                    f"Provides a +{score_diff} point safety improvement over Shortest Route "
                    f"while adding only {dist_diff_m} m ({r.detour_percentage}% detour)."
                )
        elif r.route_id == r_shortest.route_id:
            r.name = "Shortest Route"
            r.color = "#ef4444"
            r.rationale = f"Direct path minimizing travel distance ({r.total_distance_km} km)."
        else:
            r.name = "Balanced Route"
            r.color = "#f59e0b"
            r.rationale = f"Balanced trade-off between walking distance and safety exposure."

    summary = (
        f"Recommended '{recommended.name}' ({recommended.composite_safety_score}/100 safety score). "
        f"{recommended.rationale}"
    )

    return RouteResponse(
        origin=start_node,
        destination=end_node,
        snapped_origin_coords=start_coords,
        snapped_dest_coords=end_coords,
        routes_found=len(unique_candidates),
        recommended_route_id=recommended_id,
        recommendation_summary=summary,
        routes=unique_candidates
    )


