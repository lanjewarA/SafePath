from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from app.llm.report_trust import evaluate_report_credibility
from app.db.supabase_client import insert_safety_report, update_segment_safety_score, fetch_safety_reports

router = APIRouter(prefix="/api/reports", tags=["Safety Reports & Trust Filter"])

# In-memory storage fallback for reports if Supabase is un-connected
_in_memory_reports: List[Dict[str, Any]] = []

# Seeded hazard hotspots in Mumbai network
SEEDED_HAZARDS: List[Dict[str, Any]] = [
    {
        "id": "hazard-001",
        "latitude": 19.0375,
        "longitude": 72.8402,
        "intensity": 0.92,
        "report_type": "isolated_area",
        "description": "Mahim Creek connector - Extremely dark walkway with sparse traffic after 10 PM.",
        "location_landmark": "Mahim Creek Connector",
        "source": "seeded_hazard"
    },
    {
        "id": "hazard-002",
        "latitude": 19.0178,
        "longitude": 72.8478,
        "intensity": 0.78,
        "report_type": "poor_lighting",
        "description": "Dadar West flyover staircase - Multiple non-functional light posts.",
        "location_landmark": "Dadar Station West Flyover",
        "source": "seeded_hazard"
    },
    {
        "id": "hazard-003",
        "latitude": 19.0021,
        "longitude": 72.8318,
        "intensity": 0.85,
        "report_type": "harassment_risk",
        "description": "Elphinstone Road underpass alley - Narrow unmonitored footway with zero CCTV coverage.",
        "location_landmark": "Elphinstone Road Passageway",
        "source": "seeded_hazard"
    },
    {
        "id": "hazard-004",
        "latitude": 19.0620,
        "longitude": 72.8425,
        "intensity": 0.80,
        "report_type": "cctv_broken",
        "description": "Bandra East skywalk feeder lane - Damaged camera unit and low crowd density.",
        "location_landmark": "Bandra Station East Skywalk",
        "source": "seeded_hazard"
    },
    {
        "id": "hazard-005",
        "latitude": 19.0112,
        "longitude": 72.8185,
        "intensity": 0.70,
        "report_type": "poor_lighting",
        "description": "Worli Naka pedestrian subway - Shadowed blindspots late night.",
        "location_landmark": "Worli Naka Underpass",
        "source": "seeded_hazard"
    },
    {
        "id": "hazard-006",
        "latitude": 18.9950,
        "longitude": 72.8300,
        "intensity": 0.68,
        "report_type": "isolated_area",
        "description": "Lower Parel old mills lane - Deserted area after business hours.",
        "location_landmark": "Lower Parel Mill Alley",
        "source": "seeded_hazard"
    },
    {
        "id": "hazard-007",
        "latitude": 19.0430,
        "longitude": 72.8550,
        "intensity": 0.88,
        "report_type": "harassment_risk",
        "description": "Dharavi Outer Link Road - Elevated historical risk reports.",
        "location_landmark": "Dharavi Outer Link",
        "source": "seeded_hazard"
    },
    {
        "id": "hazard-008",
        "latitude": 19.0680,
        "longitude": 72.8680,
        "intensity": 0.74,
        "report_type": "cctv_broken",
        "description": "BKC Service Connector - Unlit construction detour stretch.",
        "location_landmark": "BKC Service Connector",
        "source": "seeded_hazard"
    }
]

class ReportSubmitRequest(BaseModel):
    user_id: Optional[str] = Field(default="user_anon_101", description="User ID or anonymous reporter token")
    segment_id: Optional[str] = Field(default="seg-mh-1001", description="Street segment ID")
    location_landmark: str = Field(default="Dadar Station West Flyover, Mumbai", description="Location or landmark description")
    report_type: str = Field(default="poor_lighting", description="Hazard category ('poor_lighting', 'harassment_risk', 'cctv_broken', 'isolated_area')")
    description: str = Field(default="Streetlight out near the corner flyover, dark walkway with low crowd density.", description="Detailed text description of safety hazard")
    latitude: Optional[float] = Field(default=19.0178, description="Latitude coordinate")
    longitude: Optional[float] = Field(default=72.8478, description="Longitude coordinate")

class ReportSubmitResponse(BaseModel):
    report_id: str
    status: str                                  # 'approved', 'rejected', 'pending'
    is_trustworthy: bool
    credibility_score: float                     # 0.0 to 1.0 Gemini LLM score
    reasoning: str
    safety_impact_applied: float
    report_details: Dict[str, Any]

@router.post("/submit", response_model=ReportSubmitResponse)
def submit_safety_report(payload: ReportSubmitRequest):
    """
    Submit a community safety report.
    Evaluated by Gemini LLM filter for credibility (coherence, specificity, duplicate/spam).
    Only trustworthy reports update route safety scores.
    """
    try:
        # 1. Evaluate report credibility via Gemini LLM (or fallback heuristic)
        eval_result = evaluate_report_credibility(
            location=payload.location_landmark,
            report_type=payload.report_type,
            description=payload.description
        )

        is_trustworthy = eval_result.get("is_trustworthy", False)
        credibility_score = eval_result.get("credibility_score", 0.0)
        reasoning = eval_result.get("reasoning", "")
        impact = eval_result.get("suggested_safety_impact", 0.0)

        status = "approved" if is_trustworthy else "rejected"

        report_data = {
            "user_id": payload.user_id,
            "segment_id": payload.segment_id,
            "location_landmark": payload.location_landmark,
            "latitude": payload.latitude,
            "longitude": payload.longitude,
            "report_type": payload.report_type,
            "description": payload.description,
            "credibility_score": credibility_score,
            "status": status
        }

        # 2. Persist in Supabase DB (or memory fallback)
        inserted = insert_safety_report(report_data)
        if inserted and "id" in inserted:
            report_id = str(inserted["id"])
        else:
            report_id = f"rep-{len(_in_memory_reports) + 1:04d}"
            report_data["id"] = report_id
            _in_memory_reports.append(report_data)

        # 3. If approved, apply safety score impact to street segment
        if is_trustworthy and payload.segment_id:
            update_segment_safety_score(payload.segment_id, 65.0)  # Adjust score

        return ReportSubmitResponse(
            report_id=report_id,
            status=status,
            is_trustworthy=is_trustworthy,
            credibility_score=credibility_score,
            reasoning=reasoning,
            safety_impact_applied=impact if is_trustworthy else 0.0,
            report_details=report_data
        )

    except Exception as e:
        print(f"[API Reports Error] Failed to process report: {e}")
        raise HTTPException(status_code=500, detail=f"Report submission failed: {str(e)}")

@router.get("/list")
def list_safety_reports():
    """List all submitted community safety reports from Supabase DB and local memory."""
    supabase_reports = fetch_safety_reports()
    all_reports = supabase_reports if supabase_reports else _in_memory_reports
    return {
        "supabase_connected": len(supabase_reports) > 0,
        "total_reports": len(all_reports),
        "reports": all_reports
    }

@router.get("/heatpoints")
def get_safety_heatpoints():
    """
    Fetch all heat points for map rendering.
    Combines Supabase safety_reports DB records, active community reports, and seeded hazard hotspots.
    """
    heat_points: List[Dict[str, Any]] = []

    # 1. Query Supabase Database safety_reports
    supabase_reports = fetch_safety_reports()
    if supabase_reports:
        for idx, rep in enumerate(supabase_reports):
            lat = rep.get("latitude") or rep.get("lat")
            lon = rep.get("longitude") or rep.get("lon")
            if lat and lon:
                heat_points.append({
                    "id": str(rep.get("id", f"sp-rep-{idx}")),
                    "latitude": float(lat),
                    "longitude": float(lon),
                    "intensity": float(rep.get("credibility_score", 0.8)),
                    "report_type": str(rep.get("report_type", "community_report")),
                    "description": str(rep.get("description", "Community reported safety hazard")),
                    "location_landmark": str(rep.get("location_landmark", "Reported Spot")),
                    "source": "supabase"
                })

    # 2. Add in-memory reports if Supabase is offline or empty
    for idx, rep in enumerate(_in_memory_reports):
        lat = rep.get("latitude")
        lon = rep.get("longitude")
        if lat and lon:
            heat_points.append({
                "id": str(rep.get("id", f"mem-rep-{idx}")),
                "latitude": float(lat),
                "longitude": float(lon),
                "intensity": float(rep.get("credibility_score", 0.75)),
                "report_type": str(rep.get("report_type", "community_report")),
                "description": str(rep.get("description", "User submitted safety hazard")),
                "location_landmark": str(rep.get("location_landmark", "User Reported Location")),
                "source": "community_memory"
            })

    # 3. Always include seeded hazard hotspots so heatmap is rich and informative
    heat_points.extend(SEEDED_HAZARDS)

    return {
        "supabase_active": len(supabase_reports) > 0,
        "total_points": len(heat_points),
        "heat_points": heat_points
    }

