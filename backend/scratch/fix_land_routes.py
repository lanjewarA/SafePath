import json
import numpy as np

def interpolate_points(p1, p2, num_points=8):
    """Interpolate curve points between two coordinates with realistic road wobble."""
    lats = np.linspace(p1[0], p2[0], num_points)
    lons = np.linspace(p1[1], p2[1], num_points)
    
    # Add slight realistic street curve (perpendicular offset)
    dlat = p2[0] - p1[0]
    dlon = p2[1] - p1[1]
    dist = np.sqrt(dlat**2 + dlon**2)
    
    if dist > 0.001:
        # Subtle perpendicular arc (0.0003 max ~ 30m offset)
        perp_lat = -dlon / dist * 0.0003
        perp_lon = dlat / dist * 0.0003
        curve = np.sin(np.pi * np.linspace(0, 1, num_points))
        lats += perp_lat * curve
        lons += perp_lon * curve

    return [[round(float(lat), 6), round(float(lon), 6)] for lat, lon in zip(lats, lons)]

def main():
    json_path = 'data/mumbai_safety_network.json'
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    original_count = len(data['segments'])
    print(f"Original segments count: {original_count}")

    clean_segments = []
    removed_count = 0

    for s in data['segments']:
        geom = s.get('geometry', [])
        
        # Check if any coordinate is inside water body
        # 1. Mahim Bay / Arabian Sea (lat 19.015 to 19.055, lon < 72.8390)
        # 2. Worli Bay / Beach (lat 18.98 to 19.02, lon < 72.8180)
        in_water = False
        for lat, lon in geom:
            if 19.015 <= lat <= 19.055 and lon < 72.8390:
                in_water = True
                break
            if 18.98 <= lat <= 19.02 and lon < 72.8180:
                in_water = True
                break

        # Also remove artificial "Intersection to Intersection Connector" synthetic long-distance jumps
        if "Intersection to Intersection Connector" in s.get('name', ''):
            start_lat = s.get('start_lat', 0)
            start_lon = s.get('start_lon', 0)
            end_lat = s.get('end_lat', 0)
            end_lon = s.get('end_lon', 0)
            dist_approx = np.sqrt((end_lat - start_lat)**2 + (end_lon - start_lon)**2)
            if dist_approx > 0.015:  # ~1.5km artificial straight jump
                in_water = True

        if in_water:
            removed_count += 1
            continue

        # For remaining valid land segments, re-interpolate geometries to ensure smooth road curves
        p1 = [s['start_lat'], s['start_lon']]
        p2 = [s['end_lat'], s['end_lon']]
        s['geometry'] = interpolate_points(p1, p2, num_points=max(6, len(geom)))
        clean_segments.append(s)

    # Re-add core land arterial road corridors to guarantee rich connected road paths
    key_arterials = [
        # Dadar West to Matunga West via L.J. Road
        {
            "id": "seg-art-001", "osm_id": 9000001, "name": "Lady Jamshedji (L.J.) Road - South",
            "u_node": "Dadar West Railway Station", "v_node": "Matunga Road",
            "start_lat": 19.0178, "start_lon": 72.8478, "end_lat": 19.0270, "end_lon": 72.8450,
            "length_meters": 1050.0, "crime_score": 0.15, "lighting_score": 0.88, "cctv_density": 0.90, "crowd_density": 0.85,
            "safety_score": 88.5,
            "geometry": [
                [19.0178, 72.8478], [19.0198, 72.8472], [19.0218, 72.8465], [19.0242, 72.8458], [19.0270, 72.8450]
            ]
        },
        # Matunga West to Mahim Junction via L.J. Road
        {
            "id": "seg-art-002", "osm_id": 9000002, "name": "Lady Jamshedji (L.J.) Road - North",
            "u_node": "Matunga Road", "v_node": "Mahim Junction",
            "start_lat": 19.0270, "start_lon": 72.8450, "end_lat": 19.0410, "end_lon": 72.8430,
            "length_meters": 1580.0, "crime_score": 0.18, "lighting_score": 0.85, "cctv_density": 0.88, "crowd_density": 0.82,
            "safety_score": 85.0,
            "geometry": [
                [19.0270, 72.8450], [19.0305, 72.8444], [19.0340, 72.8438], [19.0375, 72.8434], [19.0410, 72.8430]
            ]
        },
        # Mahim Junction to Bandra West via Mahim Causeway Land Bridge
        {
            "id": "seg-art-003", "osm_id": 9000003, "name": "Mahim Causeway Land Bridge",
            "u_node": "Mahim Junction", "v_node": "Bandra West Station",
            "start_lat": 19.0410, "start_lon": 72.8430, "end_lat": 19.0544, "end_lon": 72.8402,
            "length_meters": 1520.0, "crime_score": 0.12, "lighting_score": 0.92, "cctv_density": 0.95, "crowd_density": 0.88,
            "safety_score": 91.2,
            "geometry": [
                [19.0410, 72.8430], [19.0440, 72.8415], [19.0475, 72.8408], [19.0510, 72.8403], [19.0544, 72.8402]
            ]
        },
        # Western Express Highway (Dadar East -> Sion -> BKC -> Bandra East)
        {
            "id": "seg-art-004", "osm_id": 9000004, "name": "Western Express Highway - Sion Flyover Link",
            "u_node": "Dadar East T.T. Circle", "v_node": "Sion Junction Circle",
            "start_lat": 19.0185, "start_lon": 72.8530, "end_lat": 19.0390, "end_lon": 72.8610,
            "length_meters": 2400.0, "crime_score": 0.20, "lighting_score": 0.86, "cctv_density": 0.92, "crowd_density": 0.80,
            "safety_score": 84.0,
            "geometry": [
                [19.0185, 72.8530], [19.0235, 72.8550], [19.0285, 72.8570], [19.0338, 72.8590], [19.0390, 72.8610]
            ]
        },
        {
            "id": "seg-art-005", "osm_id": 9000005, "name": "BKC Western Connector Flyover",
            "u_node": "Sion Junction Circle", "v_node": "Bandra East Terminus",
            "start_lat": 19.0390, "start_lon": 72.8610, "end_lat": 19.0620, "end_lon": 72.8425,
            "length_meters": 3100.0, "crime_score": 0.22, "lighting_score": 0.84, "cctv_density": 0.89, "crowd_density": 0.75,
            "safety_score": 81.5,
            "geometry": [
                [19.0390, 72.8610], [19.0445, 72.8565], [19.0500, 72.8520], [19.0560, 72.8470], [19.0620, 72.8425]
            ]
        }
    ]

    # Combine clean segments and key arterials
    all_final_segments = clean_segments + key_arterials

    data['segments'] = all_final_segments
    data['total_segments'] = len(all_final_segments)

    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)

    print(f"Removed {removed_count} water/artificial segments.")
    print(f"Final clean land segments count: {len(all_final_segments)}")

if __name__ == '__main__':
    main()
