"""Fetch and seed a connected pedestrian road network for central Nagpur."""

from __future__ import annotations

import argparse
import math
from typing import Any, Dict, Iterable, List, Tuple

import networkx as nx
import osmnx as ox
from shapely.geometry import LineString

from app.db.supabase_client import fetch_all_segments, get_supabase_client

NAGPUR_CENTER = (21.1458, 79.0882)
DEFAULT_RADIUS_METERS = 3_000
DEFAULT_RISK = {
    "crime_score": 0.30,
    "lighting_score": 0.70,
    "crowd_density": 0.50,
}
PAGE_SIZE = 250


def _projected_line(
    coordinates: Iterable[Tuple[float, float]],
    latitude_origin: float,
) -> LineString:
    lon_scale = 111_320.0 * math.cos(math.radians(latitude_origin))
    return LineString(
        [(float(lon) * lon_scale, float(lat) * 110_540.0) for lon, lat in coordinates]
    )


def _reference_risk_segments(
    segments: List[Dict[str, Any]],
    latitude_origin: float,
) -> List[Tuple[LineString, Dict[str, float]]]:
    references = []
    for segment in segments:
        coordinates = [
            (float(segment["start_lon"]), float(segment["start_lat"])),
            (float(segment["end_lon"]), float(segment["end_lat"])),
        ]
        references.append(
            (
                _projected_line(coordinates, latitude_origin),
                {
                    key: float(segment.get(key, default))
                    for key, default in DEFAULT_RISK.items()
                },
            )
        )
    return references


def _edge_name(attributes: Dict[str, Any]) -> str:
    name = attributes.get("name")
    if isinstance(name, list):
        return " / ".join(str(value) for value in name)
    return str(name or attributes.get("highway", "Unnamed pedestrian road"))


def prepare_nagpur_segments(
    graph: nx.MultiGraph,
    existing_segments: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Convert OSM's connected pedestrian graph to PostGIS segment rows."""
    latitude_origin = NAGPUR_CENTER[0]
    references = _reference_risk_segments(existing_segments, latitude_origin)
    rows: List[Dict[str, Any]] = []

    for u, v, key, attributes in graph.edges(keys=True, data=True):
        start = graph.nodes[u]
        end = graph.nodes[v]
        geometry = attributes.get("geometry")
        coordinates = (
            list(geometry.coords)
            if geometry is not None
            else [(float(start["x"]), float(start["y"])), (float(end["x"]), float(end["y"]))]
        )
        projected = _projected_line(coordinates, latitude_origin)

        risk = DEFAULT_RISK
        nearest_distance = float("inf")
        for reference_line, reference_metrics in references:
            distance = projected.distance(reference_line)
            if distance < nearest_distance:
                nearest_distance = distance
                risk = reference_metrics
        if nearest_distance > 150.0:
            risk = DEFAULT_RISK

        safety_score = round(
            (
                0.4375 * (1.0 - risk["crime_score"])
                + 0.3125 * risk["lighting_score"]
                + 0.25 * risk["crowd_density"]
            )
            * 100.0,
            2,
        )
        osm_ids = attributes.get("osmid", 0)
        if isinstance(osm_ids, list):
            osm_ids = osm_ids[0]

        wkt_points = ", ".join(f"{lon:.7f} {lat:.7f}" for lon, lat in coordinates)
        rows.append(
            {
                "id": f"osm-ng-{min(u, v)}-{max(u, v)}-{key}",
                "osm_id": int(osm_ids),
                "name": _edge_name(attributes),
                "start_lat": float(start["y"]),
                "start_lon": float(start["x"]),
                "end_lat": float(end["y"]),
                "end_lon": float(end["x"]),
                "length_meters": float(attributes.get("length", projected.length)),
                **risk,
                "safety_score": safety_score,
                "geom": f"SRID=4326;LINESTRING({wkt_points})",
            }
        )
    return rows


def seed_nagpur_roads(
    radius_meters: int = DEFAULT_RADIUS_METERS,
    dry_run: bool = False,
) -> int:
    """Fetch connected OSM pedestrian roads and upsert them into Supabase."""
    ox.settings.use_cache = True
    ox.settings.timeout = 60
    ox.settings.log_console = False
    directed_graph = ox.graph_from_point(
        NAGPUR_CENTER,
        dist=radius_meters,
        network_type="walk",
        simplify=True,
        retain_all=False,
    )
    road_graph = ox.convert.to_undirected(directed_graph)
    if not nx.is_connected(road_graph):
        raise RuntimeError("Fetched Nagpur pedestrian road network is not connected.")

    rows = prepare_nagpur_segments(road_graph, fetch_all_segments())
    print(
        f"[Nagpur Seed] Prepared {len(rows)} connected OSM road segments "
        f"within {radius_meters} m."
    )
    if dry_run:
        return len(rows)

    client = get_supabase_client()
    if client is None:
        raise RuntimeError("Supabase is not configured; road segments were not written.")

    upserted = 0
    for offset in range(0, len(rows), PAGE_SIZE):
        batch = rows[offset : offset + PAGE_SIZE]
        client.table("segments").upsert(batch, on_conflict="id").execute()
        upserted += len(batch)
        print(f"[Nagpur Seed] Upserted {upserted}/{len(rows)} road segments.")
    return upserted


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--radius-meters", type=int, default=DEFAULT_RADIUS_METERS)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    seed_nagpur_roads(radius_meters=args.radius_meters, dry_run=args.dry_run)
