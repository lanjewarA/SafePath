import os
import json
import pytest
from app.db.supabase_client import get_supabase_client, fetch_all_segments

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
                     "length_meters", "crime_score", "lighting_score", "cctv_density", 
                     "crowd_density", "safety_score"]
    for key in required_keys:
        assert key in sample_seg, f"Missing key '{key}' in sample segment!"

    # Verify score ranges
    assert 0.0 <= sample_seg["crime_score"] <= 1.0
    assert 0.0 <= sample_seg["lighting_score"] <= 1.0
    assert 0.0 <= sample_seg["cctv_density"] <= 1.0
    assert 0.0 <= sample_seg["crowd_density"] <= 1.0
    assert 0.0 <= sample_seg["safety_score"] <= 100.0

def test_supabase_client_initialization():
    # Should initialize safely even if environment variables are unset (returns None fallback)
    client = get_supabase_client()
    segments = fetch_all_segments()
    assert isinstance(segments, list)

