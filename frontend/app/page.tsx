"use client";

import { useEffect, useState } from "react";
import dynamic from "next/dynamic";
import { Search, ShieldCheck, Activity, MapPin } from "lucide-react";

// Dynamically import Leaflet Map with ssr: false to prevent Node.js 'window is not defined' error
const DynamicMap = dynamic(() => import("@/components/Map"), {
  ssr: false,
  loading: () => (
    <div className="w-full h-full min-h-[450px] bg-slate-800 animate-pulse flex items-center justify-center text-slate-400 rounded-lg border border-slate-700">
      Loading OpenStreetMap (West India)...
    </div>
  ),
});

export default function HomePage() {
  const [healthStatus, setHealthStatus] = useState<string>("connecting...");
  const [startLoc, setStartLoc] = useState<string>("Mumbai Dadar, MH");
  const [destLoc, setDestLoc] = useState<string>("Bandra West, MH");

  useEffect(() => {
    // Cross-talk test: Call FastAPI backend health check
    fetch("http://localhost:8000/api/health")
      .then((res) => res.json())
      .then((data) => {
        setHealthStatus(`${data.service || "SafePath Backend"} is ${data.status}`);
      })
      .catch((err) => {
        console.error("Backend health fetch error:", err);
        setHealthStatus("Backend offline (ensure FastAPI is running on port 8000)");
      });
  }, []);

  return (
    <div className="flex-1 flex flex-col lg:flex-row p-4 gap-4 max-w-7xl mx-auto w-full">
      {/* Sidebar Controls & Route Form */}
      <div className="w-full lg:w-1/3 bg-slate-800 p-5 rounded-lg border border-slate-700 shadow-xl flex flex-col gap-4">
        <div>
          <h1 className="text-xl font-bold text-slate-100 flex items-center gap-2">
            <ShieldCheck className="w-5 h-5 text-emerald-400" />
            Safest Route Search
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Recommends safest paths using GNN spatial risk modeling & verified reports.
          </p>
        </div>

        {/* Backend Connection Badge */}
        <div className="flex items-center gap-2 text-xs bg-slate-900/80 p-2.5 rounded border border-slate-700">
          <Activity className={`w-4 h-4 ${healthStatus.includes("healthy") ? "text-emerald-400 animate-pulse" : "text-amber-400"}`} />
          <span className="text-slate-300 font-mono">Backend Status:</span>
          <span className="font-semibold text-slate-100">{healthStatus}</span>
        </div>

        {/* Search Inputs */}
        <div className="flex flex-col gap-3">
          <div>
            <label className="text-xs text-slate-300 font-medium mb-1 block">Origin (West India)</label>
            <div className="relative">
              <MapPin className="w-4 h-4 text-emerald-400 absolute left-3 top-3" />
              <input
                type="text"
                value={startLoc}
                onChange={(e) => setStartLoc(e.target.value)}
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
                className="w-full bg-slate-900 border border-slate-700 rounded py-2 pl-9 pr-3 text-sm text-slate-100 focus:outline-none focus:border-emerald-500"
              />
            </div>
          </div>

          <button className="w-full bg-emerald-600 hover:bg-emerald-500 text-white font-medium py-2.5 px-4 rounded flex items-center justify-center gap-2 transition-colors text-sm mt-1 shadow-lg shadow-emerald-950">
            <Search className="w-4 h-4" /> Calculate Safe Routes
          </button>
        </div>

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
      <div className="w-full lg:w-2/3 flex flex-col">
        <DynamicMap />
      </div>
    </div>
  );
}

