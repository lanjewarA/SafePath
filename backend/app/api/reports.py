from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from app.llm.report_trust import evaluate_report_credibility
from app.db.supabase_client import insert_safety_report, update_segment_safety_score

router = APIRouter(prefix="/api/reports", tags=["Safety Reports & Trust Filter"])

# In-memory storage fallback for reports if Supabase is un-connected
_in_memory_reports: List[Dict[str, Any]] = []

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
    """List all submitted community safety reports."""
    return {
        "total_reports": len(_in_memory_reports),
        "reports": _in_memory_reports
    }
