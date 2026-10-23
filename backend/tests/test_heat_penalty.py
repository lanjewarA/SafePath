import networkx as nx

from app.api import routes as routes_api
from app.routing.osm_graphhopper import build_networkx_graph
from app.routing import risk_engine
from app.schemas.route_schema import RouteRequest
from app.routing.risk_engine import (
    compute_edge_weight,
    compute_heat_penalties_idw,
    idw_penalty,
    blend_overall_risk,
    filter_nagpur_heat_points,
)
from app.routing.routing_service import apply_spatial_heat_weights


def _straight_segment(seg_id, u, v, start, end, length=100.0):
    return {
        "id": seg_id,
        "osm_id": 1,
        "name": seg_id,
        "u_node": u,
        "v_node": v,
        "start_lat": start[0],
        "start_lon": start[1],
        "end_lat": end[0],
        "end_lon": end[1],
        "length_meters": length,
        "geometry": [list(start), list(end)],
        "crime_score": 0.2,
        "lighting_score": 0.8,
        "cctv_density": 0.7,
        "crowd_density": 0.7,
    }


def test_idw_formula():
    assert abs(idw_penalty(1.0, 0.0) - (1.0 / 10.0)) < 1e-9
    assert idw_penalty(1.0, 10.0) < idw_penalty(1.0, 0.0)


def test_near_heat_point_gets_higher_penalty_than_far_segment():
    origin = (21.1458, 79.0882)
    near_end = (21.1462, 79.0886)
    far_start = (21.1600, 79.1100)
    far_end = (21.1605, 79.1105)
    segments = [
        _straight_segment("near", "A", "B", origin, near_end),
        _straight_segment("far", "C", "D", far_start, far_end),
    ]
    heat_points = [{"latitude": origin[0], "longitude": origin[1], "intensity": 1.0}]

    penalties = compute_heat_penalties_idw(segments, heat_points, buffer_meters=150.0)
    assert penalties["near"] > penalties["far"]
    assert penalties["near"] == 1.0
    assert penalties["far"] == 0.0


def test_heat_penalty_outside_150m_buffer_is_zero():
    segments = [_straight_segment("s1", "A", "B", (21.1458, 79.0882), (21.1460, 79.0884))]
    # ~400 m north
    heat_points = [{"latitude": 21.1495, "longitude": 79.0882, "intensity": 1.0}]
    penalties = compute_heat_penalties_idw(segments, heat_points, buffer_meters=150.0)
    assert penalties["s1"] == 0.0


def test_long_edge_finds_heat_point_near_interior():
    segment = _straight_segment(
        "long",
        "A",
        "B",
        (21.14, 79.00),
        (21.14, 79.04),
        length=4_100.0,
    )
    heat_point = {"latitude": 21.14, "longitude": 79.01, "intensity": 1.0}

    penalties = compute_heat_penalties_idw([segment], [heat_point], buffer_meters=150.0)

    assert penalties["long"] == 1.0


def test_heat_points_are_limited_to_approved_nagpur_coverage():
    points = filter_nagpur_heat_points(
        [
            {"latitude": 21.1458, "longitude": 79.0882, "intensity": 0.8},
            {"latitude": 19.0178, "longitude": 72.8478, "intensity": 0.9},
            {
                "latitude": 21.1458,
                "longitude": 79.0882,
                "intensity": 0.9,
                "status": "pending",
            },
        ]
    )

    assert len(points) == 1
    assert points[0]["latitude"] == 21.1458


def test_postgis_penalties_fall_back_when_segment_ids_do_not_match(monkeypatch):
    segment = _straight_segment(
        "local-segment",
        "A",
        "B",
        (21.1458, 79.0882),
        (21.1460, 79.0884),
    )
    heat_points = [{"latitude": 21.1458, "longitude": 79.0882, "intensity": 1.0}]
    monkeypatch.setattr(
        risk_engine,
        "fetch_segment_heat_penalties",
        lambda _buffer_meters: {"supabase-segment": 1.0},
    )

    penalties = risk_engine.load_heat_penalties([segment], heat_points)

    assert penalties == compute_heat_penalties_idw([segment], heat_points)


def test_routes_api_passes_submitted_heat_points(monkeypatch):
    captured = {}

    def fake_calculate_safepath_routes(**kwargs):
        captured.update(kwargs)
        return {"routes": []}

    monkeypatch.setattr(routes_api, "calculate_safepath_routes", fake_calculate_safepath_routes)
    payload = RouteRequest(
        heat_points=[
            {
                "id": "ng-1",
                "latitude": 21.1458,
                "longitude": 79.0882,
                "intensity": 0.9,
            }
        ]
    )

    routes_api.calculate_routes(payload)

    assert captured["heat_points"][0]["id"] == "ng-1"
    assert captured["heat_points"][0]["intensity"] == 0.9


def test_edge_weight_formula():
    assert compute_edge_weight(100.0, 0.0, 3.5) == 100.0
    assert compute_edge_weight(100.0, 1.0, 3.5) == 450.0


def test_safest_path_detours_around_heat_cluster():
    """
    A --hot--> B --hot--> C   (200 m, hazard on the middle of A-B)
    A --cool--> D --cool--> C (240 m, no hazard)

    After IDW weights, Dijkstra on w_safest must choose A-D-C.
    """
    a = (21.14580, 79.08820)
    b = (21.14580, 79.08910)  # ~90 m east
    c = (21.14580, 79.09000)  # ~180 m east of A
    d = (21.14700, 79.08910)  # north detour

    segments = [
        _straight_segment("ab", "A", "B", a, b, length=95.0),
        _straight_segment("bc", "B", "C", b, c, length=95.0),
        _straight_segment("ad", "A", "D", a, d, length=135.0),
        _straight_segment("dc", "D", "C", d, c, length=135.0),
    ]
    graph = build_networkx_graph(segments)
    heat_points = [
        {
            "id": "hot",
            "latitude": (a[0] + b[0]) / 2.0,
            "longitude": (a[1] + b[1]) / 2.0,
            "intensity": 1.0,
        }
    ]
    apply_spatial_heat_weights(graph, heat_points=heat_points)

    assert graph["A"]["B"]["heat_penalty"] > graph["A"]["D"]["heat_penalty"]
    assert graph["A"]["B"]["w_safest"] > graph["A"]["B"]["length"]
    safest = nx.dijkstra_path(graph, "A", "C", weight="w_safest")
    shortest = nx.dijkstra_path(graph, "A", "C", weight="w_shortest")
    assert shortest == ["A", "B", "C"]
    assert safest == ["A", "D", "C"]


def test_blend_overall_risk_is_convex_combination():
    assert blend_overall_risk(0.0, 0.0) == 0.0
    blended = blend_overall_risk(0.2, 1.0)
    assert 0.2 < blended < 1.0
