import os
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip()
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "").strip()
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "").strip()

# Initialize Client safely
_supabase_client = None

def get_supabase_client():
    global _supabase_client
    if _supabase_client is not None:
        return _supabase_client

    if not SUPABASE_URL or not SUPABASE_KEY:
        print("[Supabase] Warning: SUPABASE_URL or SUPABASE_KEY missing in .env. Running in un-connected fallback mode.")
        return None

    try:
        from supabase import create_client, Client
        # Prefer service role key for backend if available, otherwise fallback to anon key
        key_to_use = SUPABASE_SERVICE_KEY if SUPABASE_SERVICE_KEY else SUPABASE_KEY
        _supabase_client = create_client(SUPABASE_URL, key_to_use)
        print(f"[Supabase] Connected successfully to {SUPABASE_URL}")
        return _supabase_client
    except Exception as e:
        print(f"[Supabase] Error initializing client: {e}")
        return None

def fetch_all_segments() -> List[Dict[str, Any]]:
    """Fetch all street network segments from Supabase."""
    client = get_supabase_client()
    if client is None:
        return []
    
    try:
        response = client.table("segments").select("*").execute()
        return response.data if response.data else []
    except Exception as e:
        print(f"[Supabase] Failed to fetch segments: {e}")
        return []

def insert_segment_batch(segments: List[Dict[str, Any]]) -> bool:
    """Insert a list of street network segments into Supabase."""
    client = get_supabase_client()
    if client is None:
        print("[Supabase] Cannot insert batch: DB client un-connected.")
        return False

    try:
        response = client.table("segments").insert(segments).execute()
        print(f"[Supabase] Successfully inserted {len(response.data or [])} segments.")
        return True
    except Exception as e:
        print(f"[Supabase] Failed to insert segment batch: {e}")
        return False

def insert_safety_report(report_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Insert a new user safety report."""
    client = get_supabase_client()
    if client is None:
        return None

    try:
        response = client.table("safety_reports").insert(report_data).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        print(f"[Supabase] Failed to insert safety report: {e}")
        return None

def fetch_safety_reports() -> List[Dict[str, Any]]:
    """Fetch safety reports from Supabase database."""
    client = get_supabase_client()
    if client is None:
        return []
    
    try:
        response = client.table("safety_reports").select("*").execute()
        return response.data if response.data else []
    except Exception as e:
        print(f"[Supabase] Failed to fetch safety reports: {e}")
        return []

def update_segment_safety_score(segment_id: str, new_safety_score: float) -> bool:
    """Update a segment's calculated safety score after Gemini LLM verification."""
    client = get_supabase_client()
    if client is None:
        return False

    try:
        client.table("segments").update({"safety_score": new_safety_score}).eq("id", segment_id).execute()
        return True
    except Exception as e:
        print(f"[Supabase] Failed to update segment safety score: {e}")
        return False


