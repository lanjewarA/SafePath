"use client";

import { Navigation, Share2, ShieldAlert } from "lucide-react";

export default function SafeWalkPage() {
  return (
    <div className="max-w-3xl mx-auto w-full p-6 flex flex-col gap-6">
      <div className="bg-slate-800 p-6 rounded-lg border border-slate-700 shadow-xl flex flex-col gap-4">
        <h1 className="text-2xl font-bold text-slate-100 flex items-center gap-2">
          <Navigation className="w-6 h-6 text-blue-400" />
          SafeWalk Live Journey Monitor
        </h1>
        <p className="text-sm text-slate-400">
          Tracks your live GPS location during your walk. Triggers dynamic route deviation alerts and allows instant emergency SOS sharing via Web Share API.
        </p>

        <div className="bg-slate-900 p-4 rounded border border-slate-700 flex flex-col gap-3">
          <div className="flex items-center justify-between text-sm">
            <span className="text-slate-400">Status:</span>
            <span className="text-blue-400 font-mono font-semibold">Monitoring Standby</span>
          </div>
          <div className="flex items-center justify-between text-sm">
            <span className="text-slate-400">Geolocation API:</span>
            <span className="text-emerald-400 font-mono font-semibold">Ready</span>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4 mt-2">
          <button className="bg-blue-600 hover:bg-blue-500 text-white font-medium py-3 px-4 rounded flex items-center justify-center gap-2 transition-colors text-sm shadow-lg">
            <Navigation className="w-4 h-4" /> Start SafeWalk Session
          </button>
          <button className="bg-rose-600 hover:bg-rose-500 text-white font-medium py-3 px-4 rounded flex items-center justify-center gap-2 transition-colors text-sm shadow-lg shadow-rose-950">
            <Share2 className="w-4 h-4" /> Trigger Emergency SOS (Web Share)
          </button>
        </div>
      </div>
    </div>
  );
}

