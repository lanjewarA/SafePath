"use client";

import { useEffect, useState } from "react";
import dynamic from "next/dynamic";
import { Search, ShieldCheck, Activity, MapPin, Loader2, Navigation, AlertCircle, Clock, Eye, Lightbulb, Sun, Moon, Info, ShieldAlert } from "lucide-react";
import type { RouteOption, RouteResponse, HeatPoint } from "@/components/Map";

// Dynamically import Leaflet Map with ssr: false
const DynamicMap = dynamic(() => import("@/components/Map"), {
  ssr: false,
  loading: () => (
    <div className="w-full h-full min-h-[500px] bg-slate-800 animate-pulse flex items-center justify-center text-slate-400 rounded-lg border border-slate-700">
      <div className="flex items-center gap-2">
        <Loader2 className="w-5 h-5 animate-spin text-emerald-400" />
        <span>Loading OpenStreetMap (West India)...</span>
      </div>
    </div>
  ),
});

export default function HomePage() {
  const [healthStatus, setHealthStatus] = useState<string>("connecting...");
  const [startLoc, setStartLoc] = useState<string>("Dadar West");
  const [destLoc, setDestLoc] = useState<string>("Bandra West");
  const [timeOfDay, setTimeOfDay] = useState<string>("night");
  const [loading, setLoading] = useState<boolean>(false);
  const [routeData, setRouteData] = useState<RouteResponse | null>(null);
  const [selectedRouteId, setSelectedRouteId] = useState<string>("route-safest");
  const [heatPoints, setHeatPoints] = useState<HeatPoint[]>([]);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  useEffect(() => {
    fetch("http://localhost:8000/api/health")
      .then((res) => res.json())
      .then((data) => {
        setHealthStatus(`${data.service || "SafePath Backend"} is ${data.status}`);
      })
      .catch((err) => {
        console.error("Backend health fetch error:", err);
        setHealthStatus("Backend offline (ensure FastAPI is running on port 8000)");
      });

    // Fetch Heat Points from Supabase & Community Reports
    fetch("http://localhost:8000/api/reports/heatpoints")
      .then((res) => res.json())
      .then((data) => {
        if (data.heat_points) {
          setHeatPoints(data.heat_points);
        }
      })
      .catch((err) => {
        console.error("Error fetching heat points:", err);
      });
  }, []);

  const handleCalculateRoutes = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    setLoading(true);
    setErrorMsg(null);

    try {
      const response = await fetch("http://localhost:8000/api/routes/calculate", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          origin_name: startLoc,
          destination_name: destLoc,
          time_of_day: timeOfDay,
          detour_factor: 1.30
        }),
      });

      if (!response.ok) {
        throw new Error(`Server returned status ${response.status}`);
      }

      const data: RouteResponse = await response.json();
      setRouteData(data);
      if (data.routes && data.routes.length > 0) {
        setSelectedRouteId(data.recommended_route_id || data.routes[0].route_id);
      }
    } catch (err: any) {
      console.error("Route calculation error:", err);
      setErrorMsg("Could not calculate routes. Please check that the backend server is running on port 8000.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    handleCalculateRoutes();
  }, [timeOfDay]);

  const selectedRoute = routeData?.routes.find((r) => r.route_id === selectedRouteId) || routeData?.routes[0];

  return (
    <div className="flex-1 flex flex-col lg:flex-row p-4 gap-4 max-w-7xl mx-auto w-full">
      {/* Sidebar Controls & Route Search */}
      <div className="w-full lg:w-5/12 bg-slate-800 p-5 rounded-lg border border-slate-700 shadow-xl flex flex-col gap-4 overflow-y-auto max-h-[calc(100vh-100px)]">
        <div>
          <h1 className="text-xl font-bold text-slate-100 flex items-center gap-2">
            <ShieldCheck className="w-6 h-6 text-emerald-400" />
            Safest Route Search
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            GNN spatial risk modeling & length-weighted exposure calculation across real road segments.
          </p>
        </div>

        {/* Backend Connection Badge */}
        <div className="flex items-center gap-2 text-xs bg-slate-900/80 p-2.5 rounded border border-slate-700">
          <Activity className={`w-4 h-4 ${healthStatus.includes("healthy") || healthStatus.includes("online") ? "text-emerald-400 animate-pulse" : "text-amber-400"}`} />
          <span className="text-slate-300 font-mono">Backend Status:</span>
          <span className="font-semibold text-slate-100 truncate">{healthStatus}</span>
        </div>

        {/* Search Inputs & Time of Day */}
        <form onSubmit={handleCalculateRoutes} className="flex flex-col gap-3">
          <div>
            <label className="text-xs text-slate-300 font-medium mb-1 block">Origin (West India / Mumbai)</label>
            <div className="relative">
              <MapPin className="w-4 h-4 text-emerald-400 absolute left-3 top-3" />
              <input
                type="text"
                value={startLoc}
                onChange={(e) => setStartLoc(e.target.value)}
                placeholder="e.g. Dadar West"
                className="w-full bg-slate-900 border border-slate-700 rounded py-2 pl-9 pr-3 text-sm text-slate-100 focus:outline-none focus:border-emerald-500"
              />
            </div>
          </div>

          <div>
            <label className="text-xs text-slate-300 font-medium mb-1 block">Destination</label>
            <div className="relative">
              <MapPin className="w-4 h-4 text-rose-400 absolute left-3 top-3" />
              <input
                type="text"
                value={destLoc}
                onChange={(e) => setDestLoc(e.target.value)}
                placeholder="e.g. Bandra West"
                className="w-full bg-slate-900 border border-slate-700 rounded py-2 pl-9 pr-3 text-sm text-slate-100 focus:outline-none focus:border-emerald-500"
              />
            </div>
          </div>

          {/* Time of Day Toggle */}
          <div>
            <label className="text-xs text-slate-300 font-medium mb-1 block">Time of Day (Modifies Crowd & Lighting Risk)</label>
            <div className="grid grid-cols-3 gap-1.5 bg-slate-900 p-1 rounded border border-slate-700 text-xs font-medium">
              <button
                type="button"
                onClick={() => setTimeOfDay("day")}
                className={`py-1.5 px-2 rounded flex items-center justify-center gap-1 transition-colors ${
                  timeOfDay === "day" ? "bg-amber-500 text-slate-950 font-bold" : "text-slate-400 hover:text-slate-200"
                }`}
              >
                <Sun className="w-3.5 h-3.5" /> Day
              </button>
              <button
                type="button"
                onClick={() => setTimeOfDay("evening")}
                className={`py-1.5 px-2 rounded flex items-center justify-center gap-1 transition-colors ${
                  timeOfDay === "evening" ? "bg-purple-600 text-white font-bold" : "text-slate-400 hover:text-slate-200"
                }`}
              >
                <Clock className="w-3.5 h-3.5" /> Evening
              </button>
              <button
                type="button"
                onClick={() => setTimeOfDay("night")}
                className={`py-1.5 px-2 rounded flex items-center justify-center gap-1 transition-colors ${
                  timeOfDay === "night" ? "bg-emerald-600 text-white font-bold" : "text-slate-400 hover:text-slate-200"
                }`}
              >
                <Moon className="w-3.5 h-3.5" /> Night (High Risk)
              </button>
            </div>
          </div>

          {/* Quick Presets */}
          <div className="flex flex-wrap gap-1.5 pt-1">
            <span className="text-[10px] text-slate-400 font-semibold w-full">Quick Preset Locations:</span>
            <button
              type="button"
              onClick={() => { setStartLoc("Dadar West"); setDestLoc("Bandra West"); }}
              className="text-[11px] bg-slate-900 hover:bg-slate-700 text-slate-300 px-2 py-1 rounded border border-slate-700"
            >
              Dadar &rarr; Bandra
            </button>
            <button
              type="button"
              onClick={() => { setStartLoc("Mumbai Central"); setDestLoc("BKC"); }}
              className="text-[11px] bg-slate-900 hover:bg-slate-700 text-slate-300 px-2 py-1 rounded border border-slate-700"
            >
              Mumbai Central &rarr; BKC
            </button>
            <button
              type="button"
              onClick={() => { setStartLoc("Lower Parel"); setDestLoc("Worli Naka"); }}
              className="text-[11px] bg-slate-900 hover:bg-slate-700 text-slate-300 px-2 py-1 rounded border border-slate-700"
            >
              Lower Parel &rarr; Worli
            </button>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-emerald-600 hover:bg-emerald-500 disabled:bg-emerald-800 text-white font-semibold py-2.5 px-4 rounded flex items-center justify-center gap-2 transition-colors text-sm mt-1 shadow-lg shadow-emerald-950/50"
          >
            {loading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" /> Calculating Routes...
              </>
            ) : (
              <>
                <Search className="w-4 h-4" /> Calculate Safe Routes
              </>
            )}
          </button>
        </form>

        {errorMsg && (
          <div className="bg-rose-950/80 border border-rose-800 text-rose-300 text-xs p-3 rounded flex items-start gap-2">
            <AlertCircle className="w-4 h-4 shrink-0 text-rose-400 mt-0.5" />
            <span>{errorMsg}</span>
          </div>
        )}

        {/* Calculated Routes Cards */}
        {routeData && routeData.routes && routeData.routes.length > 0 && (
          <div className="flex flex-col gap-3 mt-1 border-t border-slate-700 pt-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-slate-300 uppercase tracking-wider">
                Ranked Candidates ({routeData.routes.length})
              </span>
              <span className="text-[10px] text-emerald-400 bg-emerald-950 border border-emerald-800 px-2 py-0.5 rounded font-mono">
                Green = Recommended
              </span>
            </div>

            {routeData.recommendation_summary && (
              <div className="bg-emerald-950/80 border border-emerald-800/80 p-2.5 rounded text-xs text-emerald-300 leading-relaxed flex items-start gap-2">
                <Info className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                <span>{routeData.recommendation_summary}</span>
              </div>
            )}

            {routeData.routes.map((route) => {
              const isSelected = route.route_id === selectedRouteId;
              const isRecommended = route.is_recommended;
              return (
                <div
                  key={route.route_id}
                  onClick={() => setSelectedRouteId(route.route_id)}
                  className={`p-3.5 rounded-lg border transition-all cursor-pointer ${
                    isSelected
                      ? isRecommended
                        ? "bg-emerald-950/80 border-emerald-500 shadow-md shadow-emerald-950"
                        : "bg-slate-700/80 border-amber-500 shadow-md"
                      : "bg-slate-900/60 border-slate-700 hover:border-slate-600 hover:bg-slate-900"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <div
                        className="w-3 h-3 rounded-full"
                        style={{ backgroundColor: route.color }}
                      />
                      <span className="font-bold text-sm text-slate-100">{route.name}</span>
                      {isRecommended && (
                        <span className="bg-emerald-500 text-slate-950 font-extrabold text-[10px] px-1.5 py-0.5 rounded uppercase tracking-wider">
                          RECOMMENDED
                        </span>
                      )}
                    </div>
                    <div className="text-right">
                      <span className={`text-base font-extrabold ${isRecommended ? "text-emerald-400" : "text-amber-400"}`}>
                        {route.composite_safety_score}
                      </span>
                      <span className="text-[10px] text-slate-400 font-normal">/100</span>
                    </div>
                  </div>

                  <p className="text-xs text-slate-300 mt-1">{route.description}</p>
                  
                  {route.rationale && (
                    <div className="text-[11px] text-slate-400 mt-1.5 italic bg-slate-950/50 p-1.5 rounded border border-slate-800">
                      "{route.rationale}"
                    </div>
                  )}

                  <div className="grid grid-cols-3 gap-2 text-xs font-mono text-slate-400 mt-2.5 border-t border-slate-800/80 pt-2 text-center">
                    <div className="bg-slate-950/60 p-1 rounded">
                      <span className="text-[10px] text-slate-500 block">DISTANCE</span>
                      <span className="font-bold text-slate-200">{route.total_distance_km} km</span>
                    </div>
                    <div className="bg-slate-950/60 p-1 rounded">
                      <span className="text-[10px] text-slate-500 block">WALK TIME</span>
                      <span className="font-bold text-slate-200">~{route.estimated_walk_minutes} mins</span>
                    </div>
                    <div className="bg-slate-950/60 p-1 rounded">
                      <span className="text-[10px] text-slate-500 block">DETOUR</span>
                      <span className={`font-bold ${route.detour_percentage > 25 ? "text-amber-400" : "text-emerald-400"}`}>
                        +{route.detour_percentage}%
                      </span>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {/* Selected Route Segment Safety Breakdown */}
        {selectedRoute && selectedRoute.segments && selectedRoute.segments.length > 0 && (
          <div className="bg-slate-900/80 p-3 rounded border border-slate-700 text-xs mt-1">
            <span className="font-bold text-slate-200 block mb-2 flex items-center justify-between">
              <span>Segment Risk Breakdown ({selectedRoute.name})</span>
              <span className="text-[10px] font-mono text-slate-400">{selectedRoute.segments.length} segments</span>
            </span>
            <div className="flex flex-col gap-1.5 max-h-40 overflow-y-auto pr-1">
              {selectedRoute.segments.map((seg, idx) => (
                <div key={seg.id || idx} className="flex items-center justify-between text-[11px] bg-slate-800/80 p-2 rounded border border-slate-700/60">
                  <div className="truncate max-w-[140px]">
                    <span className="text-slate-200 font-medium block truncate">{seg.name}</span>
                    <span className="text-[10px] text-slate-400 font-mono">{seg.length_meters.toFixed(0)}m</span>
                  </div>
                  <div className="flex items-center gap-2 text-slate-400 font-mono text-[10px]">
                    <span title="Lighting Score" className="flex items-center gap-0.5"><Lightbulb className="w-3 h-3 text-amber-400" /> {(seg.lighting_score * 100).toFixed(0)}%</span>
                    <span title="GNN Risk Prediction" className="bg-slate-950 px-1 py-0.5 rounded text-purple-300">GNN: {seg.gnn_risk}</span>
                    <span className={`font-mono font-bold text-xs px-1.5 py-0.5 rounded ${seg.safety_score >= 75 ? "bg-emerald-950 text-emerald-400 border border-emerald-800" : "bg-amber-950 text-amber-400 border border-amber-800"}`}>
                      {seg.safety_score.toFixed(0)}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Legend */}
        <div className="mt-auto border-t border-slate-700 pt-3">
          <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider block mb-2">Safety Score Scale</span>
          <div className="grid grid-cols-4 gap-1 text-center text-[10px] font-semibold">
            <div className="bg-emerald-950 text-emerald-300 border border-emerald-800 p-1.5 rounded">80-100 (Safe)</div>
            <div className="bg-amber-950 text-amber-300 border border-amber-800 p-1.5 rounded">60-79 (Moderate)</div>
            <div className="bg-orange-950 text-orange-300 border border-orange-800 p-1.5 rounded">40-59 (Caution)</div>
            <div className="bg-rose-950 text-rose-300 border border-rose-800 p-1.5 rounded">0-39 (High Risk)</div>
          </div>
        </div>
      </div>

      {/* Map Section */}
      <div className="w-full lg:w-7/12 flex flex-col">
        <DynamicMap
          routes={routeData?.routes || []}
          selectedRouteId={selectedRouteId}
          onSelectRoute={(id) => setSelectedRouteId(id)}
          originName={routeData?.origin || startLoc}
          destName={routeData?.destination || destLoc}
          snappedOrigin={routeData?.snapped_origin_coords as [number, number]}
          snappedDest={routeData?.snapped_dest_coords as [number, number]}
          heatPoints={heatPoints}
        />
      </div>
    </div>
  );
}



