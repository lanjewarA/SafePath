from pydantic import BaseModel, Field
from typing import List, Optional

class RouteRequest(BaseModel):
    origin_name: Optional[str] = Field(default="Mumbai Central", description="Landmark or origin address name")
    destination_name: Optional[str] = Field(default="Bandra West", description="Landmark or destination address name")
    origin_lat: Optional[float] = Field(default=None, description="Origin latitude coordinate")
    origin_lon: Optional[float] = Field(default=None, description="Origin longitude coordinate")
    dest_lat: Optional[float] = Field(default=None, description="Destination latitude coordinate")
    dest_lon: Optional[float] = Field(default=None, description="Destination longitude coordinate")

class SegmentDetail(BaseModel):
    id: str
    name: str
    length_meters: float
    safety_score: float
    crime_score: float
    lighting_score: float
    cctv_density: float
    crowd_density: float
    start_lat: float
    start_lon: float
    end_lat: float
    end_lon: float

class RouteOption(BaseModel):
    route_id: str
    name: str                                  # 'Safest Route', 'Shortest Route', 'Balanced Route'
    description: str                           # e.g., 'Maximizes well-lit, highly populated streets'
    total_distance_meters: float
    total_distance_km: float
    estimated_walk_minutes: int
    composite_safety_score: float             # 0 to 100 overall score
    safety_category: str                       # 'High Safety', 'Moderate Safety', 'Caution Required'
    color: str                                 # Hex color for map polyline overlay ('#10b981', '#f59e0b', '#ef4444')
    segments: List[SegmentDetail]
    coordinates: List[List[float]]             # Array of [lat, lon] tuples for Leaflet polyline rendering

class RouteResponse(BaseModel):
    origin: str
    destination: str
    routes_found: int
    recommended_route_id: str
    routes: List[RouteOption]

