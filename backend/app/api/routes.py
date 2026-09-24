from fastapi import APIRouter, HTTPException
from app.schemas.route_schema import RouteRequest, RouteResponse
from app.routing.osm_graphhopper import calculate_safepath_routes

router = APIRouter(prefix="/api/routes", tags=["Routing Engine"])

@router.post("/calculate", response_model=RouteResponse)
def calculate_routes(payload: RouteRequest):
    """
    Calculate ranked route options (Safest, Balanced, Shortest) between origin and destination.
    Uses NetworkX graph pathfinding, Random Forest safety predictions, and Supabase data.
    """
    try:
        response = calculate_safepath_routes(
            origin_name=payload.origin_name,
            destination_name=payload.destination_name,
            origin_lat=payload.origin_lat,
            origin_lon=payload.origin_lon,
            dest_lat=payload.dest_lat,
            dest_lon=payload.dest_lon
        )
        return response
    except Exception as e:
        print(f"[API Routes Error] Failed to calculate route: {e}")
        raise HTTPException(status_code=500, detail=f"Route calculation failed: {str(e)}")

