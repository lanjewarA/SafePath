"""
Seed Supabase with the Mumbai street-safety dataset.

Reads backend/data/mumbai_safety_network.json and inserts every street
segment into the public.segments table in batches.

Prerequisites
-------------
1. Run docs/supabase_setup.sql in the Supabase SQL Editor (creates tables).
2. Put SUPABASE_URL + SUPABASE_KEY (or SUPABASE_SERVICE_KEY) in backend/.env
3. pip install supabase python-dotenv   (already in requirements.txt)

Usage
-----
    cd backend
    python -m app.db.seed_supabase
"""

import json
import math
import os
from typing import Any, Dict, List

from dotenv import load_dotenv

load_dotenv()

DATASET_FILE = os.path.join(os.path.dirname(__file__), "..", "..", "data", "mumbai_safety_network.json")
BATCH_SIZE = 100  # Supabase/PostgREST rejects huge payloads; insert in batches


def load_dataset() -> List[Dict[str, Any]]:
    """Load the generated Mumbai safety network dataset from disk."""
    if not os.path.exists(DATASET_FILE):
        raise FileNotFoundError(
            f"Dataset file not found: {DATASET_FILE}\n"
            "Run `python data/generate_dataset.py` first to generate it."
        )

    with open(DATASET_FILE, "r", encoding="utf-8") as f:
        dataset = json.load(f)

    segments = dataset.get("segments", [])
    print(f"[Seed] Loaded {len(segments)} segments from {os.path.basename(DATASET_FILE)}")
    return segments


def build_wkt_linestring(seg: Dict[str, Any]) -> str:
    """Build a WKT LINESTRING for the segment geometry (SRID 4326)."""
    return (
        f"SRID=4326;LINESTRING({seg['start_lon']} {seg['start_lat']}, "
        f"{seg['end_lon']} {seg['end_lat']})"
    )


def prepare_rows(segments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Map dataset segments to the columns of public.segments."""
    rows: List[Dict[str, Any]] = []
    for seg in segments:
        rows.append(
            {
                "id": seg["id"],
                "osm_id": seg["osm_id"],
                "name": seg["name"],
                "start_lat": seg["start_lat"],
                "start_lon": seg["start_lon"],
                "end_lat": seg["end_lat"],
                "end_lon": seg["end_lon"],
                "length_meters": seg["length_meters"],
                "crime_score": seg["crime_score"],
                "lighting_score": seg["lighting_score"],
                "cctv_density": seg["cctv_density"],
                "crowd_density": seg["crowd_density"],
                "safety_score": seg["safety_score"],
                "geom": build_wkt_linestring(seg),
            }
        )
    return rows


def seed_segments() -> int:
    """Insert all segments into Supabase in batches. Returns rows inserted."""
    from app.db.supabase_client import get_supabase_client

    client = get_supabase_client()
    if client is None:
        print("[Seed] No Supabase connection. Set SUPABASE_URL / SUPABASE_KEY in backend/.env")
        return 0

    segments = load_dataset()
    rows = prepare_rows(segments)

    inserted = 0
    for i in range(0, len(rows), BATCH_SIZE):
        batch = rows[i : i + BATCH_SIZE]
        try:
            client.table("segments").upsert(batch).execute()
            inserted += len(batch)
            print(f"[Seed] Upserted {inserted}/{len(rows)} segments")
        except Exception as exc:
            print(f"[Seed] Failed to upsert batch {i // BATCH_SIZE + 1}: {exc}")

    print(f"[Seed] Done. {inserted} segments now in Supabase.")
    return inserted


if __name__ == "__main__":
    seed_segments()
