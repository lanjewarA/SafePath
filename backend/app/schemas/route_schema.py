from pydantic import BaseModel, Field
from typing import List, Optional


class HeatPointInput(BaseModel):
    id: Optional[str] = None
    latitude: float = Field(ge=-90.0, le=90.0)
    longitude: float = Field(ge=-180.0, le=180.0)
    intensity: float = Field(default=0.75, ge=0.0, le=1.0)
    report_type: Optional[str] = None
    description: Optional[str] = None
    location_landmark: Optional[str] = None
    source: Optional[str] = None
    status: Optional[str] = None


class RouteRequest(BaseModel):
    origin_name: Optional[str] = Field(default="Dadar West", description="Landmark or origin address name")
    destination_name: Optional[str] = Field(default="Bandra West", description="Landmark or destination address name")
    origin_lat: Optional[float] = Field(default=None, description="Origin latitude coordinate")
    origin_lon: Optional[float] = Field(default=None, description="Origin longitude coordinate")
    dest_lat: Optional[float] = Field(default=None, description="Destination latitude coordinate")
    dest_lon: Optional[float] = Field(default=None, description="Destination longitude coordinate")
    time_of_day: Optional[str] = Field(default="night", description="Time of day: 'day', 'evening', or 'night'")
    detour_factor: Optional[float] = Field(default=1.30, description="Max acceptable detour multiplier (e.g., 1.30 = 30% detour)")
    heat_points: Optional[List[HeatPointInput]] = Field(
        default=None,
        description="Optional active Nagpur heat points used to weight nearby road edges",
    )

class SegmentDetail(BaseModel):
    id: str
    name: str
    length_meters: float
    safety_score: float                       # 0 to 100 score
    final_risk: float                         # 0.0 (safe) to 1.0 (high risk), includes heat IDW
    heat_penalty: float = 0.0                 # Normalized IDW heat-point penalty (0 to 1)
    gnn_risk: float                           # GraphSAGE spatial risk prediction
    rf_risk: float                            # Random Forest baseline risk prediction
    crime_score: float
    lighting_score: float
    crowd_density: float
    isolation_score: float
    incident_count: int
    start_lat: float
    start_lon: float
    end_lat: float
    end_lon: float
    geometry: Optional[List[List[float]]] = None


class RouteOption(BaseModel):
    route_id: str
    name: str                                  # 'Recommended Safe Route', 'Shortest Route', 'Balanced Route'
    description: str                           # e.g., 'Bypasses dark, unmonitored segments'
    total_distance_meters: float
    total_distance_km: float
    estimated_walk_minutes: int
    composite_safety_score: float              # 0 to 100 overall score
    safety_exposure: float                     # Length-weighted risk (0.0 to 1.0)
    max_segment_risk: float                    # Highest risk segment along the route
    high_risk_exposure_pct: float              # % of distance on high-risk segments (>0.60)
    detour_percentage: float                   # % detour compared to shortest route (e.g. +12%)
    route_cost: float                          # Combined cost (distance + safety + high risk exposure)
    is_recommended: bool                       # True if recommended by multi-criteria cost ranking
    rationale: str                             # Explicit rationale for recommendation/ranking
    safety_category: str                       # 'High Safety', 'Moderate Safety', 'Caution Required'
    color: str                                 # Hex color for map polyline overlay ('#10b981', '#f59e0b', '#ef4444')
    segments: List[SegmentDetail]
    coordinates: List[List[float]]             # Array of [lat, lon] tuples for Leaflet polyline rendering

class RouteResponse(BaseModel):
    origin: str
    destination: str
    snapped_origin_coords: List[float]         # [lat, lon]
    snapped_dest_coords: List[float]           # [lat, lon]
    routes_found: int
    recommended_route_id: str
    recommendation_summary: str
    routes: List[RouteOption]
