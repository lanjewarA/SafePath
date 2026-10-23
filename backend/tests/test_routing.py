import pytest
import networkx as nx
from fastapi.testclient import TestClient
from app.main import app
from app.ml.baseline_rf import predict_safety_score, predict_safety_scores
from app.routing.osm_graphhopper import (
    build_networkx_graph,
    calculate_safepath_routes,
    compute_route_metrics,
    find_closest_node,
)

client = TestClient(app)

def test_random_forest_prediction():
    # High safety features: low crime, high lighting, and active foot traffic
    safe_pred = predict_safety_score(crime_score=0.1, lighting_score=0.9, crowd_density=0.8)
    assert isinstance(safe_pred, float)
    assert 70.0 <= safe_pred <= 100.0

    # Low safety features: high crime, low lighting, and little foot traffic
    risky_pred = predict_safety_score(crime_score=0.9, lighting_score=0.1, crowd_density=0.1)
    assert isinstance(risky_pred, float)
    assert 0.0 <= risky_pred <= 45.0
    assert predict_safety_scores([(0.1, 0.9, 0.8)]) == [safe_pred]

def test_multi_route_calculation():
    response = calculate_safepath_routes(
        origin_name="Mumbai Central Station",
        destination_name="Bandra West Railway Station"
    )

    assert response.routes_found == len(response.routes)
    assert response.recommended_route_id in {route.route_id for route in response.routes}
    assert response.routes
    assert len(response.routes[0].coordinates) >= 2
    assert response.routes[0].coordinates[0] == response.snapped_origin_coords
    assert response.routes[0].coordinates[-1] == response.snapped_dest_coords


def test_route_geometry_follows_edge_direction_without_synthetic_connections():
    segments = [
        {
            "id": "seg-1",
            "osm_id": 1,
            "name": "First Street",
            "u_node": "A",
            "v_node": "B",
            "start_lat": 19.0,
            "start_lon": 72.0,
            "end_lat": 19.0,
            "end_lon": 72.01,
            "length_meters": 100.0,
            "geometry": [[19.0, 72.01], [19.005, 72.005], [19.0, 72.0]],
        },
        {
            "id": "seg-2",
            "osm_id": 2,
            "name": "Separate Street",
            "u_node": "C",
            "v_node": "D",
            "start_lat": 19.0,
            "start_lon": 72.02,
            "end_lat": 19.0,
            "end_lon": 72.03,
            "length_meters": 100.0,
        },
    ]
    graph = build_networkx_graph(segments)

    route = compute_route_metrics(
        graph,
        ["B", "A"],
        "route-test",
        "Test Route",
        "Route geometry direction test",
        "#10b981",
    )

    assert route.coordinates == [[19.0, 72.01], [19.005, 72.005], [19.0, 72.0]]
    assert not graph.has_edge("B", "C")


def test_named_landmark_snaps_to_nearby_largest_connected_road_component():
    graph = nx.Graph()
    graph.add_edge("network-a", "network-b")
    graph.add_edge("isolated-a", "isolated-b")
    nodes = [
        {"name": "network-a", "lat": 21.1458, "lon": 79.0886},
        {"name": "network-b", "lat": 21.1458, "lon": 79.0890},
        {"name": "isolated-a", "lat": 21.1458, "lon": 79.0882},
        {"name": "isolated-b", "lat": 21.1460, "lon": 79.0882},
    ]
    segments = [
        {
            "name": "Sitabuldi Main Road, Nagpur",
            "u_node": "isolated-a",
            "v_node": "isolated-b",
            "start_lat": 21.1458,
            "start_lon": 79.0882,
            "end_lat": 21.1460,
            "end_lon": 79.0882,
        }
    ]

    node, coords = find_closest_node(
        graph,
        nodes,
        "Sitabuldi, Nagpur",
        segments=segments,
    )

    assert node == "network-a"
    assert coords == [21.1458, 79.0886]


def test_calculate_routes_api_endpoint():
    payload = {
        "origin_name": "Dadar West Railway Station",
        "destination_name": "Lower Parel Commercial Hub"
    }

    response = client.post("/api/routes/calculate", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert "routes" in data
    assert data["routes_found"] == len(data["routes"])
    assert len(data["routes"][0]["coordinates"]) >= 2

def test_calculate_routes_api_with_coordinates():
    payload = {
        "origin_name": "",
        "origin_lat": 19.0178,
        "origin_lon": 72.8478,
        "destination_name": "",
        "dest_lat": 19.0020,
        "dest_lon": 72.8280,
    }

    response = client.post("/api/routes/calculate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["routes_found"] == len(data["routes"])
    assert len(data["routes"][0]["coordinates"]) >= 2
