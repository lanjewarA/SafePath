import os
import json
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db.supabase_client import get_supabase_client, fetch_all_segments

client = TestClient(app)

def test_dataset_json_integrity():
    dataset_path = os.path.join(os.path.dirname(__file__), "..", "data", "mumbai_safety_network.json")
    assert os.path.exists(dataset_path), "mumbai_safety_network.json does not exist!"

    with open(dataset_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert "segments" in data
    assert "nodes" in data
    assert len(data["nodes"]) >= 50
    assert len(data["segments"]) >= 100

    # Verify first segment schema
    sample_seg = data["segments"][0]
    required_keys = ["id", "osm_id", "name", "start_lat", "start_lon", "end_lat", "end_lon",
                     "length_meters", "crime_score", "lighting_score", "crowd_density", "safety_score"]
    for key in required_keys:
        assert key in sample_seg, f"Missing key '{key}' in sample segment!"
    assert all("cctv_density" not in segment for segment in data["segments"])

    # Verify score ranges
    assert 0.0 <= sample_seg["crime_score"] <= 1.0
    assert 0.0 <= sample_seg["lighting_score"] <= 1.0
    assert 0.0 <= sample_seg["crowd_density"] <= 1.0
    assert 0.0 <= sample_seg["safety_score"] <= 100.0
    for segment in data["segments"]:
        expected_score = (
            0.4375 * (1.0 - segment["crime_score"])
            + 0.3125 * segment["lighting_score"]
            + 0.25 * segment["crowd_density"]
        ) * 100.0
        assert segment["safety_score"] == pytest.approx(expected_score, abs=0.01)

def test_supabase_client_initialization():
    # Should initialize safely even if environment variables are unset (returns None fallback)
    client = get_supabase_client()
    segments = fetch_all_segments()
    assert isinstance(segments, list)

def test_segments_api_endpoint():
    """GET /api/segments must serve the map overlay payload from Supabase
    (or the local dataset fallback) with Leaflet-ready [lat, lon] geometry."""
    response = client.get("/api/segments")
    assert response.status_code == 200

    data = response.json()
    assert isinstance(data["supabase_active"], bool)
    assert data["source"] in {"supabase", "local_dataset", "none"}
    assert data["total_segments"] == len(data["segments"])
    assert data["total_segments"] > 0, "No segment data: DB empty and local dataset missing!"

    required_keys = {"id", "name", "start_lat", "start_lon", "end_lat", "end_lon",
                     "length_meters", "safety_score", "crime_score", "lighting_score",
                     "crowd_density", "geometry", "source"}
    for seg in data["segments"]:
        assert required_keys.issubset(seg.keys()), f"Segment {seg.get('id')} missing keys"
        assert 0.0 <= seg["safety_score"] <= 100.0
        for metric in ("crime_score", "lighting_score", "crowd_density"):
            assert 0.0 <= seg[metric] <= 1.0, f"{metric} out of range in {seg['id']}"
        # Geometry must be Leaflet [lat, lon] pairs inside the West India region
        assert len(seg["geometry"]) >= 2
        for lat, lon in seg["geometry"]:
            assert 17.0 <= lat <= 25.0, f"lat {lat} not Leaflet-ordered in {seg['id']}"
            assert 68.0 <= lon <= 85.0, f"lon {lon} not Leaflet-ordered in {seg['id']}"
    # Supabase rows carry the provenance badge the map popup renders
    if data["supabase_active"]:
        assert all(s["source"] == "supabase" for s in data["segments"])
