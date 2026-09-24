import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.ml.baseline_rf import predict_safety_score
from app.routing.osm_graphhopper import calculate_safepath_routes

client = TestClient(app)

def test_random_forest_prediction():
    # High safety features: low crime, high lighting, high CCTV, high crowd
    safe_pred = predict_safety_score(crime_score=0.1, lighting_score=0.9, cctv_density=0.8, crowd_density=0.8)
    assert isinstance(safe_pred, float)
    assert 70.0 <= safe_pred <= 100.0

    # Low safety features: high crime, low lighting, low CCTV, low crowd
    risky_pred = predict_safety_score(crime_score=0.9, lighting_score=0.1, cctv_density=0.1, crowd_density=0.1)
    assert isinstance(risky_pred, float)
    assert 0.0 <= risky_pred <= 45.0

def test_multi_route_calculation():
    response = calculate_safepath_routes(
        origin_name="Mumbai Central Station",
        destination_name="Bandra West Railway Station"
    )

    assert response.routes_found == 3
    assert len(response.routes) == 3
    assert response.recommended_route_id == "route-safest"

    route_names = [r.name for r in response.routes]
    assert "Safest Route" in route_names
    assert "Balanced Route" in route_names
    assert "Shortest Route" in route_names

    safest_route = next(r for r in response.routes if r.name == "Safest Route")
    shortest_route = next(r for r in response.routes if r.name == "Shortest Route")

    # Safest route should have safety score >= shortest route safety score
    assert safest_route.composite_safety_score >= shortest_route.composite_safety_score
    # Polyline coordinates must be present
    assert len(safest_route.coordinates) > 0

def test_calculate_routes_api_endpoint():
    payload = {
        "origin_name": "Dadar West Railway Station",
        "destination_name": "Lower Parel Commercial Hub"
    }

    response = client.post("/api/routes/calculate", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["routes_found"] == 3
    assert "routes" in data
    assert len(data["routes"]) == 3

