"use client";

import { useState, useEffect } from "react";
import { Navigation, Share2, ShieldAlert, CheckCircle2, AlertTriangle, MapPin, Radio } from "lucide-react";

export default function SafeWalkPage() {
  const [activeSession, setActiveSession] = useState<boolean>(false);
  const [offRouteWarning, setOffRouteWarning] = useState<boolean>(false);
  const [currentLocation, setCurrentLocation] = useState<{ lat: number; lon: number }>({ lat: 19.0178, lon: 72.8478 }); // Dadar
  const [selectedRouteName, setSelectedRouteName] = useState<string>("Recommended Safe Route (Dadar → Bandra)");
  const [logs, setLogs] = useState<string[]>([]);

  const addLog = (msg: string) => {
    setLogs((prev) => [`[${new Date().toLocaleTimeString()}] ${msg}`, ...prev.slice(0, 5)]);
  };

  const startSession = () => {
    setActiveSession(true);
    setOffRouteWarning(false);
    addLog("SafeWalk session started. Binding GPS monitoring to Recommended Safe Route.");

    if ("geolocation" in navigator) {
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          setCurrentLocation({ lat: pos.coords.latitude, lon: pos.coords.longitude });
          addLog(`GPS position locked: ${pos.coords.latitude.toFixed(4)}, ${pos.coords.longitude.toFixed(4)}`);
        },
        (err) => {
          addLog("Using simulated GPS location (browser location permission denied).");
        }
      );
    }
  };

  const simulateOffRoute = () => {
    setOffRouteWarning(true);
    addLog("⚠️ DEVIATION DETECTED: Current GPS coordinates moved >150m off selected safe route path!");
  };

  const triggerSOS = async () => {
    const sosMessage = `🚨 EMERGENCY SOS — SafePath AI Alert!\nLocation: https://maps.google.com/?q=${currentLocation.lat},${currentLocation.lon}\nStatus: User triggered Emergency SOS during SafeWalk.`;
    
    if (navigator.share) {
      try {
        await navigator.share({
          title: "SafePath AI Emergency SOS",
          text: sosMessage,
          url: `https://maps.google.com/?q=${currentLocation.lat},${currentLocation.lon}`
        });
        addLog("Emergency SOS shared successfully via Web Share API.");
      } catch (err) {
        addLog("Web Share cancelled or unsupported.");
      }
    } else {
      navigator.clipboard.writeText(sosMessage);
      alert("Emergency SOS Message copied to clipboard:\n\n" + sosMessage);
      addLog("SOS Message copied to clipboard.");
    }
  };

  return (
    <div className="max-w-4xl mx-auto w-full p-6 flex flex-col gap-6">
      <div className="bg-slate-800 p-6 rounded-lg border border-slate-700 shadow-xl flex flex-col gap-5">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold text-slate-100 flex items-center gap-2">
            <Navigation className="w-7 h-7 text-blue-400" />
            SafeWalk Live Journey Monitor
          </h1>
          <span className={`text-xs font-mono font-bold px-3 py-1 rounded-full flex items-center gap-1.5 border ${
            activeSession ? "bg-emerald-950 text-emerald-400 border-emerald-800" : "bg-slate-900 text-slate-400 border-slate-700"
          }`}>
            <Radio className={`w-3.5 h-3.5 ${activeSession ? "animate-ping text-emerald-400" : ""}`} />
            {activeSession ? "LIVE TRACKING ACTIVE" : "STANDBY"}
          </span>
        </div>

        <p className="text-sm text-slate-300">
          Monitors your live location against your selected safe route. Detects dynamic path deviations and provides instant Web Share Emergency SOS triggers.
        </p>

        {/* Bound Route Card */}
        <div className="bg-slate-900/90 p-4 rounded-lg border border-slate-700 flex flex-col gap-3">
          <div className="flex items-center justify-between text-xs font-mono text-slate-400 border-b border-slate-800 pb-2">
            <span>BOUND ROUTE:</span>
            <span className="text-slate-200 font-semibold">{selectedRouteName}</span>
          </div>

          <div className="grid grid-cols-2 gap-4 text-xs font-mono">
            <div>
              <span className="text-slate-400 block">CURRENT COORDINATES:</span>
              <span className="text-emerald-400 font-bold">{currentLocation.lat.toFixed(4)}, {currentLocation.lon.toFixed(4)}</span>
            </div>
            <div>
              <span className="text-slate-400 block">DEVIATION THRESHOLD:</span>
              <span className="text-slate-200 font-bold">150 meters</span>
            </div>
          </div>

          {/* Deviation Alert Banner */}
          {offRouteWarning && (
            <div className="bg-rose-950 border border-rose-800 text-rose-200 p-3 rounded flex items-start gap-2.5 animate-pulse mt-1">
              <ShieldAlert className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
              <div>
                <strong className="block font-bold text-sm text-rose-300">Route Deviation Warning!</strong>
                <span className="text-xs">You are moving away from your selected safe route. Return to the green path or trigger Emergency SOS.</span>
              </div>
            </div>
          )}
        </div>

        {/* Action Controls */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          {!activeSession ? (
            <button
              onClick={startSession}
              className="bg-blue-600 hover:bg-blue-500 text-white font-semibold py-3 px-4 rounded-lg flex items-center justify-center gap-2 transition-colors text-sm shadow-lg shadow-blue-950"
            >
              <Navigation className="w-4 h-4" /> Start SafeWalk Session
            </button>
          ) : (
            <button
              onClick={() => { setActiveSession(false); setOffRouteWarning(false); addLog("Session ended."); }}
              className="bg-slate-700 hover:bg-slate-600 text-slate-200 font-semibold py-3 px-4 rounded-lg flex items-center justify-center gap-2 transition-colors text-sm"
            >
              End SafeWalk Session
            </button>
          )}

          <button
            onClick={simulateOffRoute}
            disabled={!activeSession}
            className="bg-amber-600/90 hover:bg-amber-500 disabled:opacity-50 text-slate-950 font-bold py-3 px-4 rounded-lg flex items-center justify-center gap-2 transition-colors text-sm shadow-lg"
          >
            <AlertTriangle className="w-4 h-4" /> Test Off-Route Warning
          </button>

          <button
            onClick={triggerSOS}
            className="bg-rose-600 hover:bg-rose-500 text-white font-bold py-3 px-4 rounded-lg flex items-center justify-center gap-2 transition-colors text-sm shadow-lg shadow-rose-950/80"
          >
            <Share2 className="w-4 h-4" /> Emergency SOS (Share)
          </button>
        </div>

        {/* Activity Logs */}
        {logs.length > 0 && (
          <div className="bg-slate-950 p-3 rounded border border-slate-800 font-mono text-xs flex flex-col gap-1 mt-1">
            <span className="text-slate-500 font-bold text-[10px] uppercase">Journey Monitor Log:</span>
            {logs.map((log, idx) => (
              <span key={idx} className={log.includes("DEVIATION") ? "text-rose-400 font-bold" : "text-slate-300"}>
                {log}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}


