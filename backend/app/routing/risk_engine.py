"""
Heat-point risk engine.

Applies Inverse Distance Weighting (IDW) from active hazard heat points onto
road-segment edges, then blends that penalty with lighting / crime / crowd /
GNN baseline risk used by NetworkX pathfinding.
"""

from __future__ import annotations

import math
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np
from sklearn.neighbors import KDTree

from app.db.supabase_client import fetch_safety_reports, fetch_segment_heat_penalties

HEAT_BUFFER_METERS = 150.0
IDW_SMOOTHING = 10.0  # Distance^2 + 10 in the IDW denominator
HEAT_RISK_BLEND = 0.50  # share of overall risk coming from heat IDW
ALPHA_SAFEST = 3.5
ALPHA_BALANCED = 1.2
METERS_PER_DEG_LAT = 110_540.0
NAGPUR_BOUNDS = (20.8, 21.3, 78.7, 79.4)

# Seeded Nagpur hazard hotspots (same points drawn on the Leaflet overlay).
SEEDED_HAZARDS: List[Dict[str, Any]] = [
    {
        "id": "hazard-ng-001",
        "latitude": 21.1150,
        "longitude": 79.0200,
        "intensity": 0.92,
        "report_type": "poor_lighting",
        "description": "Hingna Road Industrial Corridor - Very dark stretch with non-functional street lamps after 10 PM.",
        "location_landmark": "Hingna Road Industrial Zone, Nagpur",
        "source": "seeded_hazard",
    },
    {
        "id": "hazard-ng-002",
        "latitude": 21.0510,
        "longitude": 79.0040,
        "intensity": 0.88,
        "report_type": "isolated_area",
        "description": "Butibori MIDC Road - Deserted industrial zone late night with minimal pedestrian presence.",
        "location_landmark": "Butibori MIDC Road, Nagpur",
        "source": "seeded_hazard",
    },
    {
        "id": "hazard-ng-003",
        "latitude": 21.1080,
        "longitude": 79.0120,
        "intensity": 0.75,
        "report_type": "cctv_broken",
        "description": "MIDC Hingna Road - Damaged surveillance cameras near logistics hub.",
        "location_landmark": "MIDC Hingna Road, Nagpur",
        "source": "seeded_hazard",
    },
    {
        "id": "hazard-ng-004",
        "latitude": 21.1290,
        "longitude": 79.0870,
        "intensity": 0.80,
        "report_type": "harassment_risk",
        "description": "Wardha Road Outer Ring - Elevated caution reported near deserted fuel stations late night.",
        "location_landmark": "Wardha Road Outer Ring, Nagpur",
        "source": "seeded_hazard",
    },
    {
        "id": "hazard-ng-005",
        "latitude": 21.1650,
        "longitude": 79.1000,
        "intensity": 0.78,
        "report_type": "poor_lighting",
        "description": "Kamptee Road Main - Multiple broken streetlights along northern stretch.",
        "location_landmark": "Kamptee Road Main, Nagpur",
        "source": "seeded_hazard",
    },
    {
        "id": "hazard-ng-006",
        "latitude": 21.1487,
        "longitude": 79.0940,
        "intensity": 0.72,
        "report_type": "harassment_risk",
        "description": "Itwari Station Road - Poorly monitored lane near freight yard.",
        "location_landmark": "Itwari Station Road, Nagpur",
        "source": "seeded_hazard",
    },
]


def _meters_per_deg_lon(lat: float) -> float:
    return 111_320.0 * math.cos(math.radians(lat))


def project_to_meters(lat: float, lon: float, lat0: float) -> Tuple[float, float]:
    """Equirectangular projection around lat0 — accurate enough inside a 150 m buffer."""
    x = lon * _meters_per_deg_lon(lat0)
    y = lat * METERS_PER_DEG_LAT
    return x, y


def haversine_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6_371_000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return 2 * radius * math.atan2(math.sqrt(a), math.sqrt(max(0.0, 1.0 - a)))


def point_to_segment_meters(
    plat: float,
    plon: float,
    alat: float,
    alon: float,
    blat: float,
    blon: float,
) -> float:
    """Minimum distance from a lat/lon point to a geodesic-approximated line segment."""
    lat0 = (alat + blat + plat) / 3.0
    px, py = project_to_meters(plat, plon, lat0)
    ax, ay = project_to_meters(alat, alon, lat0)
    bx, by = project_to_meters(blat, blon, lat0)
    dx, dy = bx - ax, by - ay
    length_sq = dx * dx + dy * dy
    if length_sq <= 1e-9:
        return math.hypot(px - ax, py - ay)
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / length_sq))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def min_distance_to_polyline(lat: float, lon: float, geometry: Sequence[Sequence[float]]) -> float:
    if not geometry:
        return float("inf")
    if len(geometry) == 1:
        return haversine_meters(lat, lon, float(geometry[0][0]), float(geometry[0][1]))
    best = float("inf")
    for i in range(len(geometry) - 1):
        a, b = geometry[i], geometry[i + 1]
        best = min(
            best,
            point_to_segment_meters(lat, lon, float(a[0]), float(a[1]), float(b[0]), float(b[1])),
        )
    return best


def normalize_heat_point(raw: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    lat = raw.get("latitude", raw.get("lat"))
    lon = raw.get("longitude", raw.get("lon"))
    if lat is None or lon is None:
        return None
    intensity = raw.get("intensity", raw.get("credibility_score", 0.75))
    try:
        intensity_f = float(intensity)
        lat_f, lon_f = float(lat), float(lon)
    except (TypeError, ValueError):
        return None
    if (
        not math.isfinite(lat_f)
        or not math.isfinite(lon_f)
        or not math.isfinite(intensity_f)
        or not -90.0 <= lat_f <= 90.0
        or not -180.0 <= lon_f <= 180.0
    ):
        return None
    intensity_f = max(0.0, min(1.0, intensity_f))
    return {
        "id": str(raw.get("id", "")),
        "latitude": lat_f,
        "longitude": lon_f,
        "intensity": intensity_f,
        "report_type": str(raw.get("report_type", "community_report")),
        "description": str(raw.get("description", "Community reported safety hazard")),
        "location_landmark": str(raw.get("location_landmark", "Reported Spot")),
        "source": str(raw.get("source", "unknown")),
    }


def filter_nagpur_heat_points(
    heat_points: Iterable[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Normalize heat points and keep reports inside the configured Nagpur coverage."""
    min_lat, max_lat, min_lon, max_lon = NAGPUR_BOUNDS
    points: List[Dict[str, Any]] = []
    for raw in heat_points:
        if raw.get("status") not in (None, "approved"):
            continue
        point = normalize_heat_point(raw)
        if point is None:
            continue
        if min_lat <= point["latitude"] <= max_lat and min_lon <= point["longitude"] <= max_lon:
            points.append(point)
    return points


def collect_active_heat_points(extra_points: Optional[Iterable[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
    """Union of Supabase reports, optional in-memory reports, and seeded Nagpur hazards."""
    points: List[Dict[str, Any]] = []
    seen: set = set()

    def _add(raw: Dict[str, Any]) -> None:
        if raw.get("status") not in (None, "approved"):
            return
        normalized = normalize_heat_point(raw)
        if not normalized:
            return
        min_lat, max_lat, min_lon, max_lon = NAGPUR_BOUNDS
        if not (
            min_lat <= normalized["latitude"] <= max_lat
            and min_lon <= normalized["longitude"] <= max_lon
        ):
            return
        key = (
            round(normalized["latitude"], 5),
            round(normalized["longitude"], 5),
            normalized["source"],
            normalized["id"],
        )
        if key in seen:
            return
        seen.add(key)
        points.append(normalized)

    for idx, rep in enumerate(fetch_safety_reports() or []):
        if not rep.get("id"):
            rep = {**rep, "id": f"sp-rep-{idx}"}
        _add({**rep, "source": rep.get("source", "supabase")})

    if extra_points:
        for idx, rep in enumerate(extra_points):
            _add({**rep, "id": rep.get("id", f"extra-{idx}")})

    try:
        from app.api import reports as reports_mod

        for idx, rep in enumerate(getattr(reports_mod, "_in_memory_reports", []) or []):
            _add({**rep, "id": rep.get("id", f"mem-rep-{idx}"), "source": "community_memory"})
    except Exception:
        pass

    for hazard in SEEDED_HAZARDS:
        _add(hazard)

    return points


def idw_penalty(intensity: float, distance_m: float) -> float:
    """Risk_Penalty term: intensity / (distance^2 + 10)."""
    return float(intensity) / ((float(distance_m) ** 2) + IDW_SMOOTHING)


def normalize_penalties(raw: Dict[str, float]) -> Dict[str, float]:
    if not raw:
        return {}
    max_val = max(raw.values()) if raw else 0.0
    if max_val <= 0.0:
        return {key: 0.0 for key in raw}
    return {key: round(max(0.0, min(1.0, value / max_val)), 4) for key, value in raw.items()}


def _densified_segment_samples(
    geometry: Sequence[Sequence[float]],
    lat0: float,
    max_spacing_meters: float,
) -> List[Tuple[float, float]]:
    """Sample every part of a polyline closely enough for a conservative KDTree search."""
    points = [(float(point[0]), float(point[1])) for point in geometry if len(point) >= 2]
    if len(points) < 2 or max_spacing_meters <= 0.0:
        return points

    samples: List[Tuple[float, float]] = [points[0]]
    for start, end in zip(points, points[1:]):
        start_x, start_y = project_to_meters(*start, lat0)
        end_x, end_y = project_to_meters(*end, lat0)
        distance = math.hypot(end_x - start_x, end_y - start_y)
        steps = max(1, math.ceil(distance / max_spacing_meters))
        for step in range(1, steps + 1):
            fraction = step / steps
            samples.append(
                (
                    start[0] + (end[0] - start[0]) * fraction,
                    start[1] + (end[1] - start[1]) * fraction,
                )
            )
    return samples


def compute_heat_penalties_idw(
    segments: Sequence[Dict[str, Any]],
    heat_points: Sequence[Dict[str, Any]],
    buffer_meters: float = HEAT_BUFFER_METERS,
) -> Dict[str, float]:
    """
    For every segment, sum IDW contributions of heat points within `buffer_meters`.

    Candidate search uses a projected KDTree; exact distance is the minimum to the
    polyline so a hazard beside the middle of a long edge still counts.
    """
    if not segments or not heat_points:
        return {str(seg.get("id") or seg.get("segment_id") or ""): 0.0 for seg in segments}

    lat0 = float(np.mean([float(hp["latitude"]) for hp in heat_points]))
    heat_xy = np.array(
        [project_to_meters(float(hp["latitude"]), float(hp["longitude"]), lat0) for hp in heat_points],
        dtype=np.float64,
    )
    tree = KDTree(heat_xy, metric="euclidean")

    raw: Dict[str, float] = {}
    for seg in segments:
        seg_id = str(seg.get("id") or seg.get("segment_id") or "")
        geometry = seg.get("geometry") or [
            [float(seg.get("start_lat", 0.0)), float(seg.get("start_lon", 0.0))],
            [float(seg.get("end_lat", 0.0)), float(seg.get("end_lon", 0.0))],
        ]
        if isinstance(geometry, dict):
            geometry = [
                [float(pt[1]), float(pt[0])]
                for pt in geometry.get("coordinates", [])
                if len(pt) >= 2
            ]
        samples = _densified_segment_samples(geometry, lat0, buffer_meters)
        if not samples:
            raw[seg_id] = 0.0
            continue

        candidate_idx: set[int] = set()
        sample_xy = np.array(
            [project_to_meters(lat, lon, lat0) for lat, lon in samples],
            dtype=np.float64,
        )
        # Each line interval is at most one buffer radius long, so a point no
        # farther than the buffer from the line is within 1.5 radii of a sample.
        neighbors = tree.query_radius(sample_xy, r=buffer_meters * 1.5)
        for hit_list in neighbors:
            candidate_idx.update(int(i) for i in hit_list)

        penalty = 0.0
        for idx in sorted(candidate_idx):
            hp = heat_points[idx]
            dist = min_distance_to_polyline(hp["latitude"], hp["longitude"], geometry)
            if dist <= buffer_meters:
                penalty += idw_penalty(hp["intensity"], dist)
        raw[seg_id] = penalty

    return normalize_penalties(raw)


def blend_overall_risk(baseline_risk: float, heat_penalty: float, blend: float = HEAT_RISK_BLEND) -> float:
    """Combine lighting/crime/crowd/GNN baseline with the spatial heat penalty."""
    blended = (1.0 - blend) * float(baseline_risk) + blend * float(heat_penalty)
    return round(max(0.0, min(1.0, blended)), 4)


def compute_edge_weight(length_meters: float, overall_risk: float, alpha: float) -> float:
    """Edge_Weight = Length * (1 + Alpha * Overall_Risk_Score)."""
    return float(length_meters) * (1.0 + float(alpha) * float(overall_risk))


def load_heat_penalties(
    segments: Sequence[Dict[str, Any]],
    heat_points: Optional[Sequence[Dict[str, Any]]] = None,
) -> Dict[str, float]:
    """Prefer the PostGIS spatial join; fall back to in-process KDTree IDW."""
    db_penalties = fetch_segment_heat_penalties(HEAT_BUFFER_METERS)
    segment_ids = {
        str(segment.get("id") or segment.get("segment_id") or "")
        for segment in segments
    }
    if db_penalties and segment_ids.issubset(db_penalties):
        return {segment_id: db_penalties[segment_id] for segment_id in segment_ids}
    points = list(heat_points) if heat_points is not None else collect_active_heat_points()
    return compute_heat_penalties_idw(segments, points, HEAT_BUFFER_METERS)
