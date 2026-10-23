
import os
from pathlib import Path
from typing import Optional, List, Dict, Any

from dotenv import load_dotenv

# Resolve backend/.env regardless of the terminal's working directory.
BACKEND_DIR = Path(__file__).resolve().parents[2]
ENV_FILE = BACKEND_DIR / ".env"

load_dotenv(dotenv_path=ENV_FILE, override=False)

SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip()
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "").strip()
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "").strip()

# Prefer the service key for trusted server-side operations,
# falling back to the regular key.
KEY_TO_USE = SUPABASE_SERVICE_KEY or SUPABASE_KEY

_supabase_client = None


def get_supabase_client():
    global _supabase_client

    if _supabase_client is not None:
        return _supabase_client

    if not SUPABASE_URL or not KEY_TO_USE:
        print(
            "[Supabase] Missing configuration. "
            f"ENV file exists: {ENV_FILE.is_file()}, "
            f"URL loaded: {bool(SUPABASE_URL)}, "
            f"key loaded: {bool(KEY_TO_USE)}"
        )
        return None

    try:
        from supabase import create_client

        _supabase_client = create_client(
            SUPABASE_URL,
            KEY_TO_USE,
        )

        print("[Supabase] Client initialized.")
        return _supabase_client

    except Exception as exc:
        print(
            f"[Supabase] Client initialization failed: "
            f"{type(exc).__name__}: {exc}"
        )
        return None

# import os
# from typing import Optional, List, Dict, Any
# from dotenv import load_dotenv

# load_dotenv()

# SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip()
# SUPABASE_KEY = os.getenv("SUPABASE_KEY", "").strip()
# SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "").strip()

# # Initialize Client safely
# _supabase_client = None

# def get_supabase_client():
#     global _supabase_client
#     if _supabase_client is not None:
#         return _supabase_client

#     # Require BOTH the project URL and an API key before trying to create a client.
#     # Otherwise PostgREST cannot authenticate and every table query throws
#     # PGRST205 / PGRST100, which the app would silently treat as 'no data'.
#     if not SUPABASE_URL or not SUPABASE_KEY:
#         reason = "missing SUPABASE_URL or SUPABASE_KEY (not set in backend/.env)"
#         print(f"[Supabase] Not connected: {reason}")
#         return None

#     try:
#         from supabase import create_client, Client
#         # Prefer service role key for backend if available, otherwise fallback to anon key
#         key_to_use = SUPABASE_SERVICE_KEY if SUPABASE_SERVICE_KEY else SUPABASE_KEY
#         _supabase_client = create_client(SUPABASE_URL, key_to_use)
#         print(f"[Supabase] Connected successfully to {SUPABASE_URL}")
#         return _supabase_client
#     except Exception as e:
#         # Surface the underlying reason instead of a bare 'unconnected'.
#         print(f"[Supabase] Error initializing client: {e}")
#         return None

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
    """Insert a new user safety report.

    Supabase table 'safety_reports' expects columns 'user_id', 'segment_id',
    'latitude', 'longitude', 'report_type', 'description', 'credibility_score',
    'status'. Do NOT send 'location_landmark' here (it is not a column in the
    table). Map the human-friendly field to 'latitude'/'longitude' at the call site.
    """
    client = get_supabase_client()
    if client is None:
        return None

    try:
        # Strip any field the table does not have, so a bad/extra key can never
        # trigger the PostgREST PGRST204 'column does not exist' error.
        clean = {k: v for k, v in report_data.items()
                 if k in {"user_id", "segment_id", "latitude", "longitude",
                          "report_type", "description", "credibility_score", "status"}}
        response = client.table("safety_reports").insert(clean).execute()
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

def fetch_segment_heat_penalties(buffer_meters: float = 150.0) -> Dict[str, float]:
    """Call PostGIS function public.segment_heat_penalties(buffer_meters).

    Returns {segment_id: heat_penalty in 0..1}. Empty dict if the RPC is missing
    or Supabase is offline — the Python KDTree IDW path then takes over.
    """
    client = get_supabase_client()
    if client is None:
        return {}

    try:
        response = client.rpc(
            "segment_heat_penalties",
            {"buffer_meters": float(buffer_meters)},
        ).execute()
        rows = response.data or []
        penalties: Dict[str, float] = {}
        for row in rows:
            seg_id = row.get("segment_id") or row.get("id")
            if not seg_id:
                continue
            penalties[str(seg_id)] = float(row.get("heat_penalty") or 0.0)
        if penalties:
            print(f"[Supabase] Loaded heat penalties for {len(penalties)} segments via PostGIS.")
        return penalties
    except Exception as e:
        print(f"[Supabase] segment_heat_penalties RPC unavailable, using local IDW: {e}")
        return {}


def update_segment_safety_score(segment_id: str, new_safety_score: float) -> bool:
    """Update a segment's calculated safety score after Gemini LLM verification."""
    client = get_supabase_client()
    if client is None:
        return False

    try:
        # Supabase table 'segments' has a TEXT primary key 'id' (e.g. 'seg-mh-1001')
        # plus a 'safety_score' column. Update that row only.
        response = client.table("segments").update({"safety_score": new_safety_score}).eq("id", segment_id).execute()
        return True
    except Exception as e:
        print(f"[Supabase] Failed to update segment safety score: {e}")
        return False


