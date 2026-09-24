import os
import json
import math
import random
from typing import List, Dict, Any

# Target Urban Center: Mumbai Central / Dadar / Bandra corridor (West India)
# Bounding box for sample network: [min_lat, min_lon, max_lat, max_lon]
MUMBAI_BBOX = {
    "min_lat": 19.0100,
    "max_lat": 19.0900,
    "min_lon": 72.8200,
    "max_lon": 72.8800
}

# Major landmark coordinates in Mumbai for synthetic graph nodes
LANDMARKS = [
    {"name": "Mumbai Central Station", "lat": 18.9696, "lon": 72.8193},
    {"name": "Dadar West Railway Station", "lat": 19.0178, "lon": 72.8478},
    {"name": "Senapati Bapat Marg", "lat": 19.0020, "lon": 72.8280},
    {"name": "Lower Parel Commercial Hub", "lat": 18.9950, "lon": 72.8295},
    {"name": "Worli Naka", "lat": 19.0060, "lon": 72.8180},
    {"name": "Prabhadevi Chowk", "lat": 19.0160, "lon": 72.8290},
    {"name": "Bandra Kurla Complex (BKC)", "lat": 19.0650, "lon": 72.8680},
    {"name": "Bandra West Station", "lat": 19.0544, "lon": 72.8402},
    {"name": "Mahim Junction", "lat": 19.0410, "lon": 72.8430},
    {"name": "Matunga Road", "lat": 19.0270, "lon": 72.8450},
    {"name": "Sion Circle", "lat": 19.0360, "lon": 72.8600},
    {"name": "Dharavi Junction", "lat": 19.0400, "lon": 72.8530},
]

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance in meters between two lat/lon coordinates."""
    R = 6371000  # Radius of Earth in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def calculate_composite_safety_score(
    crime_score: float,
    lighting_score: float,
    cctv_density: float,
    crowd_density: float
) -> float:
    """
    Calculate composite safety score (0 to 100 scale).
    Higher score = SAFER street segment.
    """
    normalized_score = (
        0.35 * (1.0 - crime_score) +
        0.25 * lighting_score +
        0.20 * cctv_density +
        0.20 * crowd_density
    )
    return round(max(0.0, min(100.0, normalized_score * 100.0)), 2)

def generate_mumbai_safety_dataset(num_additional_nodes: int = 40) -> Dict[str, Any]:
    """Generate a realistic street segment safety dataset for Mumbai / West India."""
    random.seed(42)  # Reproducible dataset generation

    nodes = list(LANDMARKS)
    # Synthesize additional interconnected street intersections
    for i in range(num_additional_nodes):
        lat = random.uniform(MUMBAI_BBOX["min_lat"], MUMBAI_BBOX["max_lat"])
        lon = random.uniform(MUMBAI_BBOX["min_lon"], MUMBAI_BBOX["max_lon"])
        nodes.append({
            "name": f"Intersection MH-{i+1:02d}",
            "lat": round(lat, 6),
            "lon": round(lon, 6)
        })

    segments = []
    segment_id_counter = 1000

    # Connect nearby street intersections within 2.5 km distance threshold
    for i, u in enumerate(nodes):
        for j, v in enumerate(nodes):
            if i >= j:
                continue

            dist = haversine_distance(u["lat"], u["lon"], v["lat"], v["lon"])
            if dist <= 2500:  # 2.5 km max segment connection
                segment_id_counter += 1
                osm_id = 4000000000 + segment_id_counter

                # Simulate realistic localized risk factors
                # Higher crime near isolated flyovers, lower crime near commercial hubs
                is_commercial = "Station" in u["name"] or "Hub" in u["name"] or "BKC" in u["name"]
                
                crime_score = round(random.uniform(0.05, 0.45) if is_commercial else random.uniform(0.20, 0.75), 2)
                lighting_score = round(random.uniform(0.60, 0.95) if is_commercial else random.uniform(0.25, 0.80), 2)
                cctv_density = round(random.uniform(0.50, 0.95) if is_commercial else random.uniform(0.15, 0.65), 2)
                crowd_density = round(random.uniform(0.55, 0.90) if is_commercial else random.uniform(0.10, 0.60), 2)

                safety_score = calculate_composite_safety_score(
                    crime_score, lighting_score, cctv_density, crowd_density
                )

                street_name = f"{u['name'].split()[0]} to {v['name'].split()[0]} Connector"

                segments.append({
                    "id": f"seg-mh-{segment_id_counter}",
                    "osm_id": osm_id,
                    "name": street_name,
                    "start_lat": u["lat"],
                    "start_lon": u["lon"],
                    "end_lat": v["lat"],
                    "end_lon": v["lon"],
                    "length_meters": round(dist, 1),
                    "crime_score": crime_score,
                    "lighting_score": lighting_score,
                    "cctv_density": cctv_density,
                    "crowd_density": crowd_density,
                    "safety_score": safety_score,
                    "u_node": u["name"],
                    "v_node": v["name"]
                })

    dataset = {
        "region": "West India (Mumbai / Pune, Maharashtra)",
        "bounding_box": MUMBAI_BBOX,
        "total_nodes": len(nodes),
        "total_segments": len(segments),
        "nodes": nodes,
        "segments": segments
    }

    return dataset

if __name__ == "__main__":
    print("Generating simulated urban safety dataset for West India (Mumbai corridor)...")
    dataset = generate_mumbai_safety_dataset()

    output_dir = os.path.dirname(os.path.abspath(__file__))
    output_file = os.path.join(output_dir, "mumbai_safety_network.json")

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(dataset, f, indent=2)

    print(f"[Dataset Generator] Successfully generated {dataset['total_segments']} street segments across {dataset['total_nodes']} nodes.")
    print(f"[Dataset Generator] Output written to file: mumbai_safety_network.json")

