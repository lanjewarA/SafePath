import os
import json
from typing import List, Dict, Any

from fastapi import APIRouter

from app.db.supabase_client import fetch_all_segments

router = APIRouter(prefix="/api/segments", tags=["Street Segments"])

DATASET_FILE = os.path.join(os.path.dirname(__file__), "..", "..", "data", "mumbai_safety_network.json")


def normalize_segment(seg: Dict[str, Any], source: str) -> Dict[str, Any]:
    """Normalize a raw DB/JSON segment row into the shape the map overlay expects.

    PostGIS 'geom' is GeoJSON with [lon, lat] pairs; Leaflet polylines need
    [lat, lon], so coordinates are flipped here (same convention as the route
    API's `coordinates` arrays).
    """
    geometry: List[List[float]] = []
    geom = seg.get("geometry") or seg.get("geom")
    if isinstance(geom, dict):
        coords = geom.get("coordinates") or []
        try:
            geometry = [[float(pt[1]), float(pt[0])] for pt in coords]
        except (TypeError, ValueError, IndexError):
            geometry = []
    if not geometry:
        geometry = [
            [float(seg["start_lat"]), float(seg["start_lon"])],
            [float(seg["end_lat"]), float(seg["end_lon"])],
        ]

    return {
        "id": str(seg.get("id", "")),
        "name": str(seg.get("name", "Unnamed Road")),
        "start_lat": float(seg["start_lat"]),
        "start_lon": float(seg["start_lon"]),
        "end_lat": float(seg["end_lat"]),
        "end_lon": float(seg["end_lon"]),
        "length_meters": float(seg.get("length_meters", 0.0)),
        "safety_score": float(seg.get("safety_score", 75.0)),
        "crime_score": float(seg.get("crime_score", 0.2)),
        "lighting_score": float(seg.get("lighting_score", 0.7)),
        "crowd_density": float(seg.get("crowd_density", 0.6)),
        "geometry": geometry,
        "source": source,
    }


@router.get("")
def list_street_segments():
    """
    Return the full street-segment network for the map overlay.

    Primary source: Supabase `segments` table (incl. PostGIS geom LineStrings).
    Fallback: local seed dataset JSON, so the overlay still renders offline.
    """
    db_segments = fetch_all_segments()
    if db_segments:
        segments = [normalize_segment(s, "supabase") for s in db_segments]
        return {
            "supabase_active": True,
            "source": "supabase",
            "total_segments": len(segments),
            "segments": segments,
        }

    if os.path.exists(DATASET_FILE):
        with open(DATASET_FILE, "r", encoding="utf-8") as f:
            local_segments = json.load(f).get("segments", [])
        segments = [normalize_segment(s, "local_dataset") for s in local_segments]
        return {
            "supabase_active": False,
            "source": "local_dataset",
            "total_segments": len(segments),
            "segments": segments,
        }

    return {"supabase_active": False, "source": "none", "total_segments": 0, "segments": []}
