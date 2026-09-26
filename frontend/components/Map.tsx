"use client";

import React, { useEffect, useState } from "react";
import { MapContainer, TileLayer, Marker, Popup, Polyline, Circle, CircleMarker, useMap } from "react-leaflet";
import L from "leaflet";

export interface SegmentDetail {
  id: string;
  name: string;
  length_meters: number;
  safety_score: number;
  final_risk: number;
  gnn_risk: number;
  rf_risk: number;
  crime_score: number;
  lighting_score: number;
  cctv_density: number;
  crowd_density: number;
  isolation_score: number;
  incident_count: number;
  cctv_alert: boolean;
  start_lat: number;
  start_lon: number;
  end_lat: number;
  end_lon: number;
  geometry?: [number, number][];
}

export interface RouteOption {
  route_id: string;
  name: string;
  description: string;
  total_distance_meters: number;
  total_distance_km: number;
  estimated_walk_minutes: number;
  composite_safety_score: number;
  safety_exposure: number;
  max_segment_risk: number;
  high_risk_exposure_pct: number;
  detour_percentage: number;
  route_cost: number;
  is_recommended: boolean;
  rationale: string;
  safety_category: string;
  color: string;
  segments: SegmentDetail[];
  coordinates: [number, number][];
}

export interface RouteResponse {
  origin: string;
  destination: string;
  snapped_origin_coords: [number, number];
  snapped_dest_coords: [number, number];
  routes_found: number;
  recommended_route_id: string;
  recommendation_summary: string;
  routes: RouteOption[];
}

export interface HeatPoint {
  id: string;
  latitude: number;
  longitude: number;
  intensity: number;
  report_type: string;
  description: string;
  location_landmark: string;
  source: string;
}

interface MapProps {
  routes?: RouteOption[];
  selectedRouteId?: string | null;
  onSelectRoute?: (routeId: string) => void;
  originName?: string;
  destName?: string;
  snappedOrigin?: [number, number];
  snappedDest?: [number, number];
  heatPoints?: HeatPoint[];
  showHeatmap?: boolean;
}

// Fix Leaflet's default marker icon paths
const defaultIcon = L.icon({
  iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
  iconRetinaUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
  shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41],
});
L.Marker.prototype.options.icon = defaultIcon;

const startMarkerIcon = L.divIcon({
  className: "custom-start-marker",
  html: `<div style="background-color: #10b981; width: 26px; height: 26px; border-radius: 50%; border: 3px solid white; box-shadow: 0 0 14px rgba(16,185,129,0.95); display:flex; align-items:center; justify-content:center; color:white; font-size:12px; font-weight:bold;">A</div>`,
  iconSize: [26, 26],
  iconAnchor: [13, 13],
});

const endMarkerIcon = L.divIcon({
  className: "custom-end-marker",
  html: `<div style="background-color: #ef4444; width: 26px; height: 26px; border-radius: 50%; border: 3px solid white; box-shadow: 0 0 14px rgba(239,68,68,0.95); display:flex; align-items:center; justify-content:center; color:white; font-size:12px; font-weight:bold;">B</div>`,
  iconSize: [26, 26],
  iconAnchor: [13, 13],
});

const MUMBAI_CENTER: [number, number] = [19.04, 72.845];

function MapController({ bounds }: { bounds: L.LatLngBoundsExpression | null }) {
  const map = useMap();
  useEffect(() => {
    if (bounds) {
      map.fitBounds(bounds, { padding: [50, 50], maxZoom: 15 });
    }
  }, [bounds, map]);
  return null;
}

export default function MapComponent({
  routes = [],
  selectedRouteId = "route-safest",
  onSelectRoute,
  originName,
  destName,
  snappedOrigin,
  snappedDest,
  heatPoints = [],
  showHeatmap = true,
}: MapProps) {
  const [heatmapActive, setHeatmapActive] = useState<boolean>(showHeatmap);
  const selectedRoute = routes.find((r) => r.route_id === selectedRouteId) || routes[0];
  const activeCoordinates = selectedRoute?.coordinates || [];

  let bounds: L.LatLngBoundsExpression | null = null;
  if (activeCoordinates.length > 0) {
    bounds = activeCoordinates as [number, number][];
  } else if (routes.length > 0 && routes[0].coordinates.length > 0) {
    bounds = routes[0].coordinates as [number, number][];
  }

  const startCoord = snappedOrigin || (activeCoordinates.length > 0 ? activeCoordinates[0] : null);
  const endCoord = snappedDest || (activeCoordinates.length > 0 ? activeCoordinates[activeCoordinates.length - 1] : null);

  const getReportColor = (type: string) => {
    switch (type) {
      case "harassment_risk":
        return "#ef4444"; // Red
      case "isolated_area":
        return "#a855f7"; // Purple
      case "poor_lighting":
        return "#f59e0b"; // Amber
      case "cctv_broken":
        return "#f43f5e"; // Rose
      default:
        return "#dc2626"; // Crimson
    }
  };


  return (
    <div className="w-full h-full min-h-[500px] rounded-lg overflow-hidden border border-slate-700 shadow-2xl relative z-10 flex flex-col">
      <MapContainer
        center={startCoord || MUMBAI_CENTER}
        zoom={12}
        scrollWheelZoom={true}
        className="w-full h-full min-h-[500px]"
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        {bounds && <MapController bounds={bounds} />}

        {routes.length === 0 && (
          <Marker position={MUMBAI_CENTER}>
            <Popup>
              <div className="text-slate-900 font-sans p-1">
                <strong className="text-emerald-700 font-bold block text-sm">SafePath AI — West India</strong>
                <span className="text-xs text-slate-600">Enter Origin & Destination and click "Calculate Safe Routes" to view green safest path overlay.</span>
              </div>
            </Popup>
          </Marker>
        )}

        {/* Draw Non-Selected Candidate Routes */}
        {routes
          .filter((r) => r.route_id !== selectedRouteId)
          .map((route) => {
            const isSafest = route.is_recommended || route.name.includes("Safe");
            const polyColor = isSafest ? "#10b981" : route.color || "#f59e0b";
            return (
              <Polyline
                key={route.route_id}
                positions={route.coordinates}
                pathOptions={{
                  color: polyColor,
                  weight: isSafest ? 5 : 4,
                  opacity: 0.5,
                  dashArray: isSafest ? undefined : "6, 8",
                }}
                eventHandlers={{
                  click: () => onSelectRoute && onSelectRoute(route.route_id),
                }}
              >
                <Popup>
                  <div className="text-slate-900 font-sans text-xs p-1">
                    <strong style={{ color: polyColor }}>{route.name}</strong> ({route.composite_safety_score}/100)
                    <br />
                    Distance: {route.total_distance_km} km | Walk: {route.estimated_walk_minutes} mins | Cost: {route.route_cost}
                  </div>
                </Popup>
              </Polyline>
            );
          })}

        {/* Draw Selected Primary Route */}
        {selectedRoute && selectedRoute.coordinates.length > 0 && (
          <>
            <Polyline
              positions={selectedRoute.coordinates}
              pathOptions={{
                color: selectedRoute.color === "#10b981" || selectedRoute.is_recommended ? "#047857" : selectedRoute.color,
                weight: 11,
                opacity: 0.35,
              }}
            />
            <Polyline
              positions={selectedRoute.coordinates}
              pathOptions={{
                color: selectedRoute.color === "#10b981" || selectedRoute.is_recommended ? "#10b981" : selectedRoute.color,
                weight: 6,
                opacity: 0.95,
                lineCap: "round",
                lineJoin: "round",
              }}
            >
              <Popup>
                <div className="text-slate-900 font-sans p-1 max-w-xs">
                  <div className="font-bold text-sm flex items-center justify-between gap-1.5" style={{ color: selectedRoute.color }}>
                    <span>{selectedRoute.name}</span>
                    <span className="bg-emerald-100 text-emerald-800 text-[10px] px-1.5 py-0.5 rounded-full font-bold">
                      {selectedRoute.composite_safety_score}/100
                    </span>
                  </div>
                  <div className="text-xs text-slate-700 mt-1">
                    {selectedRoute.description}
                  </div>
                  <div className="text-xs text-slate-600 mt-1 italic">
                    "{selectedRoute.rationale}"
                  </div>
                  <div className="text-xs font-semibold text-slate-900 mt-1.5 pt-1 border-t border-slate-200 flex justify-between">
                    <span>📍 {selectedRoute.total_distance_km} km</span>
                    <span>⏱️ ~{selectedRoute.estimated_walk_minutes} mins</span>
                    <span>Risk Exp: {(selectedRoute.safety_exposure * 100).toFixed(1)}%</span>
                  </div>
                </div>
              </Popup>
            </Polyline>

            {/* Render Individual Segment Details with Inspection Markers/Popups */}
            {selectedRoute.segments.map((seg, idx) => {
              const segStart: [number, number] = [seg.start_lat, seg.start_lon];
              const segEnd: [number, number] = [seg.end_lat, seg.end_lon];
              const midLat = (seg.start_lat + seg.end_lat) / 2;
              const midLon = (seg.start_lon + seg.end_lon) / 2;
              const isHighRisk = seg.final_risk >= 0.60;
              const isMediumRisk = seg.final_risk >= 0.40;
              const strokeColor = isHighRisk ? "#ef4444" : isMediumRisk ? "#f59e0b" : "#10b981";

              const segPositions = (seg.geometry && seg.geometry.length > 0) ? (seg.geometry as [number, number][]) : [segStart, segEnd];

              return (
                <Polyline
                  key={`seg-${seg.id}-${idx}`}
                  positions={segPositions}
                  pathOptions={{
                    color: strokeColor,
                    weight: 7,
                    opacity: 0.9,
                  }}
                >
                  <Popup>
                    <div className="text-slate-900 font-sans p-1 text-xs max-w-xs">
                      <strong className="text-sm block font-bold" style={{ color: strokeColor }}>
                        🛣️ {seg.name}
                      </strong>
                      <div className="text-slate-600 mb-1">
                        Length: {seg.length_meters.toFixed(0)}m &bull; Segment Score: <strong>{seg.safety_score}/100</strong>
                      </div>
                      <div className="grid grid-cols-2 gap-1 bg-slate-100 p-1.5 rounded font-mono text-[10px] my-1 border border-slate-200">
                        <div>🧠 GNN Risk: <strong>{seg.gnn_risk}</strong></div>
                        <div>🌲 RF Baseline: <strong>{seg.rf_risk}</strong></div>
                        <div>💡 Lighting: <strong>{(seg.lighting_score * 100).toFixed(0)}%</strong></div>
                        <div>📹 CCTV Density: <strong>{(seg.cctv_density * 100).toFixed(0)}%</strong></div>
                        <div>👥 Crowd Proxy: <strong>{(seg.crowd_density * 100).toFixed(0)}%</strong></div>
                        <div>🏝️ Isolation: <strong>{(seg.isolation_score * 100).toFixed(0)}%</strong></div>
                      </div>
                      {seg.incident_count > 0 && (
                        <div className="text-[10px] text-amber-700 font-semibold mt-1">
                          ⚠️ {seg.incident_count} verified community hazard report(s)
                        </div>
                      )}
                      {seg.cctv_alert && (
                        <div className="text-[10px] text-rose-700 font-semibold mt-0.5">
                          🚨 Active CCTV proximity alert
                        </div>
                      )}
                    </div>
                  </Popup>
                </Polyline>
              );
            })}
          </>
        )}

        {/* Supabase & Community Safety Heat Points Layer */}
        {heatmapActive &&
          heatPoints.map((hp) => {
            const color = getReportColor(hp.report_type);
            const intensityPct = (hp.intensity * 100).toFixed(0);

            return (
              <React.Fragment key={`hp-${hp.id}`}>
                {/* Outer Glowing Heat Halo */}
                <Circle
                  center={[hp.latitude, hp.longitude]}
                  radius={180 * hp.intensity}
                  pathOptions={{
                    color: color,
                    fillColor: color,
                    fillOpacity: 0.22,
                    stroke: false,
                  }}
                />
                {/* Core Heat Spot Marker */}
                <CircleMarker
                  center={[hp.latitude, hp.longitude]}
                  radius={8 + hp.intensity * 5}
                  pathOptions={{
                    color: "#ffffff",
                    weight: 2,
                    fillColor: color,
                    fillOpacity: 0.9,
                  }}
                >
                  <Popup>
                    <div className="text-slate-900 font-sans p-1 max-w-xs">
                      <div className="flex items-center justify-between gap-2 border-b border-slate-200 pb-1 mb-1">
                        <span className="font-bold text-xs flex items-center gap-1 uppercase tracking-wider" style={{ color: color }}>
                          🔥 {hp.report_type.replace(/_/g, " ")}
                        </span>
                        <span className="bg-slate-900 text-slate-100 text-[10px] px-1.5 py-0.5 rounded font-mono">
                          Intensity {intensityPct}%
                        </span>
                      </div>
                      <strong className="text-sm text-slate-900 block font-semibold mb-0.5">
                        📍 {hp.location_landmark}
                      </strong>
                      <p className="text-xs text-slate-700 leading-snug">
                        {hp.description}
                      </p>
                      <div className="mt-2 pt-1 border-t border-slate-100 flex items-center justify-between text-[10px] text-slate-500">
                        <span>[{hp.latitude.toFixed(4)}, {hp.longitude.toFixed(4)}]</span>
                        <span className="bg-slate-100 px-1.5 py-0.5 rounded font-mono text-slate-700 font-semibold uppercase">
                          {hp.source === "supabase" ? "⚡ Supabase DB" : hp.source === "community_memory" ? "👥 Community Report" : "⚠️ Verified Hazard"}
                        </span>
                      </div>
                    </div>
                  </Popup>
                </CircleMarker>
              </React.Fragment>
            );
          })}

        {/* Start Marker */}
        {startCoord && (
          <Marker position={startCoord} icon={startMarkerIcon}>
            <Popup>
              <div className="text-slate-900 font-sans text-xs">
                <strong className="text-emerald-700 font-bold block">🟢 Snapped Origin (Start)</strong>
                <span>{originName || "Origin Location"}</span>
                <br />
                <span className="font-mono text-[10px] text-slate-500">[{startCoord[0].toFixed(4)}, {startCoord[1].toFixed(4)}]</span>
              </div>
            </Popup>
          </Marker>
        )}

        {/* End Marker */}
        {endCoord && (
          <Marker position={endCoord} icon={endMarkerIcon}>
            <Popup>
              <div className="text-slate-900 font-sans text-xs">
                <strong className="text-rose-700 font-bold block">🏁 Snapped Destination (End)</strong>
                <span>{destName || "Destination Location"}</span>
                <br />
                <span className="font-mono text-[10px] text-slate-500">[{endCoord[0].toFixed(4)}, {endCoord[1].toFixed(4)}]</span>
              </div>
            </Popup>
          </Marker>
        )}
      </MapContainer>

      {/* Heatmap Toggle Badge Control Overlay */}
      <div className="absolute top-3 right-3 z-[1000] bg-slate-900/90 backdrop-blur-md border border-slate-700 p-2 rounded-lg shadow-xl flex items-center gap-2">
        <button
          onClick={() => setHeatmapActive(!heatmapActive)}
          className={`text-xs px-2.5 py-1.5 rounded-md font-semibold flex items-center gap-1.5 transition-all ${
            heatmapActive
              ? "bg-rose-600 text-white shadow-md shadow-rose-950"
              : "bg-slate-800 text-slate-400 hover:text-slate-200"
          }`}
        >
          <span>🔥 Heat Points Overlay</span>
          <span className="bg-slate-950 text-rose-300 text-[10px] px-1.5 py-0.5 rounded-full font-mono font-bold">
            {heatPoints.length} Points
          </span>
        </button>
      </div>
    </div>
  );
}



