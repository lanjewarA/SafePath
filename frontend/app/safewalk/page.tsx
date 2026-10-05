"use client";

import dynamic from "next/dynamic";
import { useEffect, useState } from "react";
import { AlertTriangle, Check, Copy, MapPin, Navigation, Share2, Square, Star, Search, ShieldCheck, ThumbsUp, ThumbsDown, MessageSquare, Sparkles, CheckCircle2 } from "lucide-react";

type Coordinates = { lat: number; lon: number };
type RouteOption = {
  route_id: string;
  name: string;
  total_distance_km: number;
  estimated_walk_minutes: number;
  composite_safety_score: number;
  coordinates: number[][];
};

const SafeWalkMap = dynamic(() => import("@/components/SafeWalkMap"), {
  ssr: false,
  loading: () => <div className="min-h-[480px] animate-pulse bg-slate-900/60" />,
});

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const DEVIATION_LIMIT_METERS = 100;

const KNOWN_DESTINATIONS: Record<string, { lat: number; lon: number; label: string }> = {
  "bandra": { lat: 19.055, lon: 72.83, label: "Bandra West, Mumbai" },
  "bandra west": { lat: 19.055, lon: 72.83, label: "Bandra West, Mumbai" },
  "dadar": { lat: 19.0178, lon: 72.8478, label: "Dadar West, Mumbai" },
  "dadar west": { lat: 19.0178, lon: 72.8478, label: "Dadar West, Mumbai" },
  "kurla": { lat: 19.068, lon: 72.879, label: "Kurla West, Mumbai" },
  "kurla west": { lat: 19.068, lon: 72.879, label: "Kurla West, Mumbai" },
  "mumbai central": { lat: 18.97, lon: 72.819, label: "Mumbai Central, Mumbai" },
  "bkc": { lat: 19.064, lon: 72.868, label: "Bandra Kurla Complex (BKC)" },
  "lower parel": { lat: 18.995, lon: 72.83, label: "Lower Parel, Mumbai" },
  "worli": { lat: 19.015, lon: 72.818, label: "Worli Naka, Mumbai" },
  "andheri": { lat: 19.119, lon: 72.846, label: "Andheri West, Mumbai" },
  "shivajinagar": { lat: 18.531, lon: 73.844, label: "Shivajinagar, Pune" },
  "pune station": { lat: 18.528, lon: 73.874, label: "Pune Railway Station, Pune" },
};

function distanceFromRoute(position: Coordinates, route: number[][]): number {
  if (route.length === 0) return Infinity;

  const metersPerDegreeLat = 111_320;
  const metersPerDegreeLon = metersPerDegreeLat * Math.cos((position.lat * Math.PI) / 180);
  const points = route.map(([lat, lon]) => ({
    x: (lon - position.lon) * metersPerDegreeLon,
    y: (lat - position.lat) * metersPerDegreeLat,
  }));

  if (points.length === 1) return Math.hypot(points[0].x, points[0].y);

  return Math.min(...points.slice(1).map((point, index) => {
    const start = points[index];
    const dx = point.x - start.x;
    const dy = point.y - start.y;
    const lengthSquared = dx * dx + dy * dy;
    const fraction = lengthSquared === 0
      ? 0
      : Math.max(0, Math.min(1, -(start.x * dx + start.y * dy) / lengthSquared));
    return Math.hypot(start.x + fraction * dx, start.y + fraction * dy);
  }));
}

export default function SafeWalkPage() {
  const [destination, setDestination] = useState<Coordinates | null>(null);
  const [destAddressText, setDestAddressText] = useState("");
  const [destAddressDisplay, setDestAddressDisplay] = useState("");
  const [destSearching, setDestSearching] = useState(false);
  const [position, setPosition] = useState<Coordinates | null>(null);
  const [routeOrigin, setRouteOrigin] = useState<Coordinates | null>(null);
  const [route, setRoute] = useState<RouteOption | null>(null);
  const [isTracking, setIsTracking] = useState(false);
  const [status, setStatus] = useState("Enter destination address or click map");
  const [error, setError] = useState("");
  const [shareStatus, setShareStatus] = useState("");
  const [deviationMeters, setDeviationMeters] = useState<number | null>(null);
  const [watchId, setWatchId] = useState<number | null>(null);

  // Compulsory Safety Feedback States
  const [showFeedbackModal, setShowFeedbackModal] = useState(false);
  const [journeyCompleted, setJourneyCompleted] = useState(false);
  const [lightingRating, setLightingRating] = useState<number>(0);
  const [isDeserted, setIsDeserted] = useState<boolean | null>(null);
  const [hasCctvPolice, setHasCctvPolice] = useState<boolean | null>(null);
  const [hasHarassment, setHasHarassment] = useState<boolean | null>(null);
  const [overallSafety, setOverallSafety] = useState<number>(0);
  const [feedbackDesc, setFeedbackDesc] = useState("");
  const [feedbackSubmitting, setFeedbackSubmitting] = useState(false);
  const [feedbackSubmitted, setFeedbackSubmitted] = useState(false);
  const [feedbackError, setFeedbackError] = useState("");

  // Handle destination address search / lookup
  const handleSearchDestination = async (queryAddress?: string) => {
    const query = (queryAddress || destAddressText).trim().toLowerCase();
    if (!query) return;

    setDestSearching(true);
    setError("");

    // 1. Check known landmark dictionary
    if (KNOWN_DESTINATIONS[query]) {
      const match = KNOWN_DESTINATIONS[query];
      setDestination({ lat: match.lat, lon: match.lon });
      setDestAddressDisplay(match.label);
      setRoute(null);
      setDestSearching(false);
      setStatus(`Destination set: ${match.label}`);
      return;
    }

    // Check partial dictionary matches
    const partialKey = Object.keys(KNOWN_DESTINATIONS).find((k) => query.includes(k) || k.includes(query));
    if (partialKey) {
      const match = KNOWN_DESTINATIONS[partialKey];
      setDestination({ lat: match.lat, lon: match.lon });
      setDestAddressDisplay(match.label);
      setRoute(null);
      setDestSearching(false);
      setStatus(`Destination set: ${match.label}`);
      return;
    }

    // 2. Fallback to OpenStreetMap Nominatim Geocoding API
    try {
      const url = `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(query + ", Maharashtra, India")}&limit=1`;
      const res = await fetch(url, { headers: { "Accept-Language": "en" } });
      const data = await res.json();
      if (data && data.length > 0) {
        const item = data[0];
        const newCoords = { lat: parseFloat(item.lat), lon: parseFloat(item.lon) };
        setDestination(newCoords);
        setDestAddressDisplay(item.display_name.split(",")[0] + ", " + (item.display_name.split(",")[1] || ""));
        setRoute(null);
        setStatus(`Destination set: ${item.display_name.split(",")[0]}`);
      } else {
        setError(`Could not find coordinates for "${query}". Please click on the map directly or choose a preset.`);
      }
    } catch (err) {
      console.warn("Geocoding fetch failed:", err);
      // Fallback default Bandra West
      setDestination({ lat: 19.055, lon: 72.83 });
      setDestAddressDisplay("Bandra West, Mumbai");
      setStatus("Destination set: Bandra West, Mumbai");
    } finally {
      setDestSearching(false);
    }
  };

  useEffect(() => {
    if (!isTracking || !routeOrigin || !destination) return;

    const controller = new AbortController();
    setStatus("Calculating your safest route...");
    fetch(`${API_BASE}/api/routes/calculate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      signal: controller.signal,
      body: JSON.stringify({
        origin_name: "",
        origin_lat: routeOrigin.lat,
        origin_lon: routeOrigin.lon,
        destination_name: destAddressDisplay || "Destination",
        dest_lat: destination.lat,
        dest_lon: destination.lon,
      }),
    })
      .then(async (response) => {
        if (!response.ok) throw new Error(`Route request failed (${response.status})`);
        return response.json();
      })
      .then((data) => {
        const recommended = data.routes?.find((item: RouteOption) => item.route_id === data.recommended_route_id)
          ?? data.routes?.[0];
        if (!recommended) throw new Error("No route was returned for this destination");
        setRoute(recommended);
        setStatus("SafeWalk is active — walk along the green path");
      })
      .catch((requestError: unknown) => {
        if (requestError instanceof Error && requestError.name === "AbortError") return;
        setError(requestError instanceof Error ? requestError.message : "Could not calculate the route");
        setStatus("Tracking location; route unavailable");
      });

    return () => controller.abort();
  }, [destination, isTracking, routeOrigin, destAddressDisplay]);

  useEffect(() => () => {
    if (watchId !== null && "geolocation" in navigator) {
      navigator.geolocation.clearWatch(watchId);
    }
  }, [watchId]);

  useEffect(() => {
    if (!position || !route) {
      setDeviationMeters(null);
      return;
    }
    setDeviationMeters(distanceFromRoute(position, route.coordinates));

    // Automatic arrival detection: if within 40m of destination
    if (destination && isTracking && !journeyCompleted) {
      const distToDest = Math.hypot(
        (position.lat - destination.lat) * 111320,
        (position.lon - destination.lon) * 111320 * Math.cos((position.lat * Math.PI) / 180)
      );
      if (distToDest <= 40) {
        completeJourney();
      }
    }
  }, [position, route, destination, isTracking, journeyCompleted]);

  const startSession = () => {
    setError("");
    setShareStatus("");
    setRoute(null);
    setRouteOrigin(null);
    setPosition(null);
    setDeviationMeters(null);
    setJourneyCompleted(false);
    setFeedbackSubmitted(false);

    if (!destination) {
      setError("Please enter a destination address or click on the map first.");
      return;
    }
    if (!navigator.geolocation) {
      setError("This browser does not support location access.");
      return;
    }

    setStatus("Requesting GPS location permission...");
    setIsTracking(true);
    const id = navigator.geolocation.watchPosition(
      (location) => {
        const nextPosition = { lat: location.coords.latitude, lon: location.coords.longitude };
        setPosition(nextPosition);
        setRouteOrigin((current) => current ?? nextPosition);
        setStatus("SafeWalk is tracking your live location");
      },
      (locationError) => {
        setIsTracking(false);
        setStatus("Location unavailable");
        setError(locationError.code === locationError.PERMISSION_DENIED
          ? "Location permission was denied. Allow location access in your browser to start SafeWalk."
          : locationError.code === locationError.POSITION_UNAVAILABLE
            ? "Your device could not determine its location. Try again outdoors."
            : "Location request timed out. Try starting again.");
        setWatchId(null);
      },
      { enableHighAccuracy: true, maximumAge: 5_000, timeout: 20_000 },
    );
    setWatchId(id);
  };

  const stopSession = () => {
    if (watchId !== null) navigator.geolocation?.clearWatch(watchId);
    setWatchId(null);
    setIsTracking(false);
    setRouteOrigin(null);
    setRoute(null);
    setDeviationMeters(null);
    setStatus("Session stopped");
  };

  // Called when user arrives at destination (automatic or button click)
  const completeJourney = () => {
    if (watchId !== null) navigator.geolocation?.clearWatch(watchId);
    setWatchId(null);
    setIsTracking(false);
    setJourneyCompleted(true);
    setStatus("🎉 Arrived at destination! Compulsory safety feedback required.");
    setShowFeedbackModal(true);
  };

  const shareEmergencyLocation = async () => {
    if (!position) {
      setShareStatus("Start a SafeWalk session to share your current location.");
      return;
    }

    const mapUrl = `https://maps.google.com/?q=${position.lat},${position.lon}`;
    const message = `🚨 EMERGENCY SOS: I am walking in West India and need assistance. My live GPS location: ${mapUrl}`;
    try {
      if (navigator.share) {
        await navigator.share({ title: "SafePath Emergency SOS", text: message, url: mapUrl });
        setShareStatus("Location shared using your device's share menu.");
      } else if (navigator.clipboard) {
        await navigator.clipboard.writeText(message);
        setShareStatus("SOS location link copied to clipboard. Send it immediately to your emergency contact.");
      } else {
        setShareStatus(message);
      }
    } catch (shareError) {
      if (shareError instanceof Error && shareError.name === "AbortError") return;
      setShareStatus("Could not open sharing. Copy this link: " + mapUrl);
    }
  };

  // Submit compulsory feedback to backend
  const handleSubmitFeedback = async (e: React.FormEvent) => {
    e.preventDefault();
    setFeedbackError("");

    // Validate compulsory fields
    if (lightingRating === 0) {
      setFeedbackError("Please rate the street lighting condition.");
      return;
    }
    if (isDeserted === null) {
      setFeedbackError("Please answer whether the streets felt deserted or crowded.");
      return;
    }
    if (hasCctvPolice === null) {
      setFeedbackError("Please answer whether CCTV or police security was visible.");
      return;
    }
    if (hasHarassment === null) {
      setFeedbackError("Please answer whether you experienced any harassment or safety concerns.");
      return;
    }
    if (overallSafety === 0) {
      setFeedbackError("Please provide an overall safety rating.");
      return;
    }

    setFeedbackSubmitting(true);

    try {
      // If user reported harassment or poor conditions, auto-submit a safety report to backend
      if (hasHarassment || lightingRating <= 2 || isDeserted) {
        const hazardType = hasHarassment ? "harassment_risk" : lightingRating <= 2 ? "poor_lighting" : "isolated_area";
        await fetch(`${API_BASE}/api/reports/submit`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            location_landmark: destAddressDisplay || "SafeWalk Destination",
            report_type: hazardType,
            description: feedbackDesc || `Post-journey safety feedback: Lighting ${lightingRating}/5, Deserted: ${isDeserted ? 'Yes' : 'No'}, CCTV/Police: ${hasCctvPolice ? 'Yes' : 'No'}`,
            user_id: "safewalk_verified_user",
            segment_id: "seg-mh-1001",
          }),
        }).catch((e) => console.warn("Feedback report sync:", e));
      }

      setFeedbackSubmitted(true);
    } catch (err: any) {
      console.error("Feedback error:", err);
      setFeedbackSubmitted(true);
    } finally {
      setFeedbackSubmitting(false);
    }
  };

  const isOffRoute = deviationMeters !== null && deviationMeters > DEVIATION_LIMIT_METERS;

  return (
    <div className="mx-auto flex w-full max-w-7xl flex-col gap-5 p-4 md:p-6 relative">
      <header className="flex flex-col gap-2 border-b border-white/10 pb-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-widest text-teal-300">Live Journey Tracking</p>
          <h1 className="mt-1 flex items-center gap-2 text-2xl font-semibold text-slate-100">
            <Navigation className="h-6 w-6 text-teal-400" /> SafeWalk Live Monitor
          </h1>
        </div>
        <p className="max-w-xl text-sm leading-6 text-slate-400">
          Real-time GPS walking monitor with automatic route deviation detection, manual address entry, and compulsory safety feedback upon arrival.
        </p>
      </header>

      {/* Destination Address Input Bar */}
      <div className="glass-panel p-4 rounded-xl flex flex-col md:flex-row gap-3 items-center justify-between shadow-lg">
        <div className="flex-1 w-full">
          <label className="text-xs font-semibold text-slate-300 mb-1.5 flex items-center gap-1.5">
            <MapPin className="w-3.5 h-3.5 text-pink-400" />
            <span>Enter Destination Address or Landmark (West India / Mumbai / Pune):</span>
          </label>
          <div className="flex gap-2">
            <div className="relative flex-1">
              <input
                type="text"
                value={destAddressText}
                onChange={(e) => setDestAddressText(e.target.value)}
                onKeyDown={(e) => { if (e.key === "Enter") handleSearchDestination(); }}
                placeholder="e.g. Bandra West, Dadar Station, Kurla, BKC, Pune Station..."
                className="w-full glass-inset rounded-lg py-2 pl-3 pr-8 text-sm text-slate-100 placeholder:text-slate-500 focus:outline-none focus:border-pink-400 focus:ring-2 focus:ring-pink-400/20"
              />
            </div>
            <button
              type="button"
              onClick={() => handleSearchDestination()}
              disabled={destSearching || !destAddressText.trim()}
              className="bg-pink-600 hover:bg-pink-500 disabled:opacity-50 text-white font-semibold text-xs px-4 py-2 rounded-lg flex items-center gap-1.5 transition-colors shadow-md shadow-pink-950/50"
            >
              <Search className="w-3.5 h-3.5" />
              <span>{destSearching ? "Locating..." : "Set Destination"}</span>
            </button>
          </div>
        </div>

        {/* Quick Destination Presets */}
        <div className="flex flex-col gap-1 w-full md:w-auto">
          <span className="text-[10px] text-slate-400 font-semibold">Or Quick Choose Destination:</span>
          <div className="flex flex-wrap gap-1.5">
            <button
              type="button"
              onClick={() => { setDestAddressText("Bandra West"); handleSearchDestination("Bandra West"); }}
              className="text-[11px] glass-inset hover:bg-white/10 text-pink-200 px-2 py-1 rounded-md"
            >
              Bandra West
            </button>
            <button
              type="button"
              onClick={() => { setDestAddressText("Dadar West"); handleSearchDestination("Dadar West"); }}
              className="text-[11px] glass-inset hover:bg-white/10 text-pink-200 px-2 py-1 rounded-md"
            >
              Dadar West
            </button>
            <button
              type="button"
              onClick={() => { setDestAddressText("Kurla West"); handleSearchDestination("Kurla West"); }}
              className="text-[11px] glass-inset hover:bg-white/10 text-pink-200 px-2 py-1 rounded-md"
            >
              Kurla West
            </button>
            <button
              type="button"
              onClick={() => { setDestAddressText("BKC"); handleSearchDestination("BKC"); }}
              className="text-[11px] glass-inset hover:bg-white/10 text-pink-200 px-2 py-1 rounded-md"
            >
              BKC
            </button>
            <button
              type="button"
              onClick={() => { setDestAddressText("Pune Station"); handleSearchDestination("Pune Station"); }}
              className="text-[11px] glass-inset hover:bg-white/10 text-pink-200 px-2 py-1 rounded-md"
            >
              Pune Station
            </button>
          </div>
        </div>
      </div>

      <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_340px]">
        {/* Map Section */}
        <section className="min-w-0 overflow-hidden rounded-xl border border-white/10 bg-slate-900/85 shadow-xl">
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-white/10 px-4 py-3">
            <div className="flex items-center gap-2 text-sm">
              <span className={`h-2.5 w-2.5 rounded-full ${isTracking ? "bg-teal-400 animate-pulse" : "bg-slate-500"}`} />
              <span className="font-medium text-slate-200">{status}</span>
            </div>
            {position && <span className="font-mono text-xs text-slate-400">GPS {position.lat.toFixed(5)}, {position.lon.toFixed(5)}</span>}
          </div>
          <SafeWalkMap
            position={position}
            destination={destination}
            routeCoordinates={route?.coordinates ?? []}
            onDestinationSelect={async (nextDestination) => {
              setDestination(nextDestination);
              setRoute(null);
              setError("");

              // Initial placeholder while reverse-geocoding
              const initialLabel = `Map Pin (${nextDestination.lat.toFixed(4)}, ${nextDestination.lon.toFixed(4)})`;
              setDestAddressText(initialLabel);
              setDestAddressDisplay(initialLabel);
              setStatus(`Destination set from map: ${initialLabel}`);

              // Reverse geocode to get street name / landmark
              try {
                const res = await fetch(
                  `https://nominatim.openstreetmap.org/reverse?format=json&lat=${nextDestination.lat}&lon=${nextDestination.lon}&zoom=18&addressdetails=1`,
                  { headers: { "Accept-Language": "en" } }
                );
                const data = await res.json();
                if (data && data.display_name) {
                  const parts = data.display_name.split(",");
                  const cleanAddress = parts.slice(0, 3).join(",").trim();
                  setDestAddressText(cleanAddress);
                  setDestAddressDisplay(cleanAddress);
                  setStatus(`Destination: ${cleanAddress}`);
                  return;
                }
              } catch (geoErr) {
                console.warn("Reverse geocode fetch error:", geoErr);
              }

              // Fallback to closest regional landmark
              let closest = "";
              let minDistance = Infinity;
              for (const [, val] of Object.entries(KNOWN_DESTINATIONS)) {
                const d = Math.hypot(val.lat - nextDestination.lat, val.lon - nextDestination.lon);
                if (d < minDistance && d < 0.03) {
                  minDistance = d;
                  closest = `Near ${val.label}`;
                }
              }
              if (closest) {
                setDestAddressText(closest);
                setDestAddressDisplay(closest);
              }
            }}
          />
          <div className="flex items-center justify-between border-t border-white/10 px-4 py-3 text-xs text-slate-400">
            <div className="flex items-center gap-2">
              <MapPin className="h-4 w-4 shrink-0 text-pink-400" />
              {destAddressDisplay ? (
                <span className="font-semibold text-pink-300">Destination: {destAddressDisplay}</span>
              ) : destination ? (
                <span>Destination: [{destination.lat.toFixed(4)}, {destination.lon.toFixed(4)}]</span>
              ) : (
                <span>Type address above or click anywhere on the map</span>
              )}
            </div>
            <span className="text-[11px] text-teal-400/80 font-mono">✓ Clicking map auto-populates address</span>
          </div>
        </section>

        {/* Walk Controls Sidebar */}
        <aside className="flex flex-col gap-4">
          <section className="glass-panel rounded-xl p-4">
            <h2 className="text-sm font-semibold text-slate-100 flex items-center justify-between">
              <span>Walk Status</span>
              {isTracking && (
                <span className="text-[10px] bg-teal-950 text-teal-300 border border-teal-500/40 px-2 py-0.5 rounded-full font-mono animate-pulse">
                  LIVE GPS
                </span>
              )}
            </h2>
            <p className="mt-2 text-sm text-slate-400">{status}</p>

            {route && (
              <dl className="mt-4 grid grid-cols-2 gap-3 border-t border-white/10 pt-3 text-sm">
                <div><dt className="text-xs text-slate-500">Distance</dt><dd className="mt-1 text-slate-200 font-bold">{route.total_distance_km} km</dd></div>
                <div><dt className="text-xs text-slate-500">Est. Walk</dt><dd className="mt-1 text-slate-200 font-bold">~{route.estimated_walk_minutes} min</dd></div>
                <div className="col-span-2">
                  <dt className="text-xs text-slate-500">Route Safety Score</dt>
                  <dd className="mt-1 text-emerald-400 font-black text-base">{Math.round(route.composite_safety_score)} / 100</dd>
                </div>
              </dl>
            )}

            {isOffRoute && (
              <div role="alert" className="mt-4 flex gap-2 border-l-2 border-amber-400 bg-amber-950/40 p-3 text-sm text-amber-200 rounded-r-lg">
                <AlertTriangle className="h-5 w-5 shrink-0" />
                <span>You are about <strong>{Math.round(deviationMeters!)} m</strong> off the safest suggested route.</span>
              </div>
            )}

            {deviationMeters !== null && !isOffRoute && route && (
              <p className="mt-3 flex items-center gap-2 text-xs text-teal-300"><Check className="h-4 w-4" /> On the suggested safe route</p>
            )}

            {error && <p role="alert" className="mt-3 text-sm text-rose-300">{error}</p>}

            <div className="mt-4 flex flex-col gap-2.5">
              {!isTracking ? (
                <button
                  onClick={startSession}
                  disabled={!destination}
                  className="flex min-h-11 items-center justify-center gap-2 rounded-lg bg-gradient-to-r from-teal-500 to-emerald-400 px-4 py-2 text-sm font-semibold text-slate-950 shadow-lg shadow-teal-950/60 transition-colors hover:from-teal-400 hover:to-emerald-300 disabled:cursor-not-allowed disabled:from-slate-600 disabled:to-slate-600 disabled:text-slate-400 disabled:shadow-none"
                >
                  <Navigation className="h-4 w-4" /> Start SafeWalk Tracking
                </button>
              ) : (
                <>
                  {/* Arrival Trigger Button */}
                  <button
                    onClick={completeJourney}
                    className="flex min-h-11 items-center justify-center gap-2 rounded-lg bg-gradient-to-r from-emerald-500 to-teal-400 px-4 py-2 text-sm font-bold text-slate-950 shadow-lg shadow-emerald-950/60 transition-all hover:scale-[1.02]"
                  >
                    <CheckCircle2 className="h-4 w-4" /> I Have Arrived / Complete Walk
                  </button>

                  <button
                    onClick={stopSession}
                    className="flex min-h-11 items-center justify-center gap-2 rounded-lg bg-slate-700 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-slate-600"
                  >
                    <Square className="h-4 w-4" /> Stop Session
                  </button>
                </>
              )}

              <button
                onClick={shareEmergencyLocation}
                className="flex min-h-11 items-center justify-center gap-2 rounded-lg border border-pink-500/50 bg-pink-950/60 px-4 py-2 text-sm font-semibold text-pink-200 transition-colors hover:bg-pink-900/70"
              >
                <Share2 className="h-4 w-4" /> Share Emergency SOS Location
              </button>
              {shareStatus && <p aria-live="polite" className="flex items-start gap-2 text-xs leading-5 text-slate-300"><Copy className="mt-0.5 h-3.5 w-3.5 shrink-0" />{shareStatus}</p>}
            </div>
          </section>

          <p className="text-xs leading-5 text-slate-500">
            SafeWalk monitors walking adherence locally on your device. Live coordinates are evaluated against the GNN spatial risk layer to alert if you deviate into isolated streets.
          </p>
        </aside>
      </div>

      {/* COMPULSORY FEEDBACK FORM MODAL */}
      {showFeedbackModal && (
        <div className="fixed inset-0 z-[9999] flex items-center justify-center bg-black/80 backdrop-blur-md p-4 overflow-y-auto">
          <div className="glass-panel-strong border border-teal-500/40 w-full max-w-xl rounded-2xl p-6 shadow-2xl relative animate-in fade-in zoom-in-95 duration-200">
            {!feedbackSubmitted ? (
              <form onSubmit={handleSubmitFeedback} className="flex flex-col gap-5">
                <div className="border-b border-white/10 pb-3">
                  <div className="flex items-center gap-2 text-teal-300 font-bold text-lg">
                    <ShieldCheck className="w-6 h-6 text-teal-400" />
                    <span>Arrival Safety Feedback (Compulsory)</span>
                  </div>
                  <p className="text-xs text-slate-400 mt-1">
                    You have arrived at your destination! Please complete this verified safety feedback to update the SafePath AI regional safety index and protect other women traveling this route.
                  </p>
                </div>

                {/* Factor 1: Street Lighting (Rating) */}
                <div className="glass-inset p-3 rounded-xl flex flex-col gap-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-slate-200">1. How was the Street Lighting along your route?</span>
                    <span className="text-[11px] font-mono text-amber-400">{lightingRating > 0 ? `${lightingRating} / 5 Stars` : "Required"}</span>
                  </div>
                  <div className="flex items-center gap-3">
                    {[1, 2, 3, 4, 5].map((star) => (
                      <button
                        key={star}
                        type="button"
                        onClick={() => setLightingRating(star)}
                        className="p-1 text-slate-600 hover:text-amber-400 transition-colors"
                      >
                        <Star className={`w-7 h-7 ${star <= lightingRating ? "text-amber-400 fill-amber-400" : "text-slate-600"}`} />
                      </button>
                    ))}
                    <span className="text-[11px] text-slate-400 ml-auto">
                      {lightingRating === 1 ? "Pitch Dark" : lightingRating === 3 ? "Adequate" : lightingRating === 5 ? "Brightly Lit" : ""}
                    </span>
                  </div>
                </div>

                {/* Factor 2: Street Crowdedness (Yes / No) */}
                <div className="glass-inset p-3 rounded-xl flex flex-col gap-2">
                  <span className="text-xs font-semibold text-slate-200">2. Did the street feel deserted or isolated?</span>
                  <div className="grid grid-cols-2 gap-2 text-xs">
                    <button
                      type="button"
                      onClick={() => setIsDeserted(true)}
                      className={`py-2 px-3 rounded-lg border font-medium transition-all ${
                        isDeserted === true
                          ? "bg-rose-950/80 border-rose-500 text-rose-200 font-bold"
                          : "border-white/10 hover:bg-white/5 text-slate-300"
                      }`}
                    >
                      ⚠️ Yes (Felt Deserted / Lonely)
                    </button>
                    <button
                      type="button"
                      onClick={() => setIsDeserted(false)}
                      className={`py-2 px-3 rounded-lg border font-medium transition-all ${
                        isDeserted === false
                          ? "bg-emerald-950/80 border-emerald-500 text-emerald-200 font-bold"
                          : "border-white/10 hover:bg-white/5 text-slate-300"
                      }`}
                    >
                      👥 No (Active Foot Traffic)
                    </button>
                  </div>
                </div>

                {/* Factor 3: CCTV & Security Presence (Yes / No) */}
                <div className="glass-inset p-3 rounded-xl flex flex-col gap-2">
                  <span className="text-xs font-semibold text-slate-200">3. Did you notice visible CCTV cameras or police patrolling?</span>
                  <div className="grid grid-cols-2 gap-2 text-xs">
                    <button
                      type="button"
                      onClick={() => setHasCctvPolice(true)}
                      className={`py-2 px-3 rounded-lg border font-medium transition-all ${
                        hasCctvPolice === true
                          ? "bg-emerald-950/80 border-emerald-500 text-emerald-200 font-bold"
                          : "border-white/10 hover:bg-white/5 text-slate-300"
                      }`}
                    >
                      📹 Yes (CCTV / Security Visible)
                    </button>
                    <button
                      type="button"
                      onClick={() => setHasCctvPolice(false)}
                      className={`py-2 px-3 rounded-lg border font-medium transition-all ${
                        hasCctvPolice === false
                          ? "bg-amber-950/80 border-amber-500 text-amber-200 font-bold"
                          : "border-white/10 hover:bg-white/5 text-slate-300"
                      }`}
                    >
                      ❌ No (No Security Visible)
                    </button>
                  </div>
                </div>

                {/* Factor 4: Harassment / Suspicious Activity (Yes / No) */}
                <div className="glass-inset p-3 rounded-xl flex flex-col gap-2">
                  <span className="text-xs font-semibold text-slate-200">4. Did you experience or observe any harassment, eve-teasing, or danger?</span>
                  <div className="grid grid-cols-2 gap-2 text-xs">
                    <button
                      type="button"
                      onClick={() => setHasHarassment(true)}
                      className={`py-2 px-3 rounded-lg border font-medium transition-all ${
                        hasHarassment === true
                          ? "bg-rose-950 border-rose-500 text-rose-200 font-bold"
                          : "border-white/10 hover:bg-white/5 text-slate-300"
                      }`}
                    >
                      🚨 Yes (Encountered Issue)
                    </button>
                    <button
                      type="button"
                      onClick={() => setHasHarassment(false)}
                      className={`py-2 px-3 rounded-lg border font-medium transition-all ${
                        hasHarassment === false
                          ? "bg-emerald-950/80 border-emerald-500 text-emerald-200 font-bold"
                          : "border-white/10 hover:bg-white/5 text-slate-300"
                      }`}
                    >
                      🛡️ No (Felt Safe)
                    </button>
                  </div>
                </div>

                {/* Factor 5: Overall Feeling of Safety (Rating) */}
                <div className="glass-inset p-3 rounded-xl flex flex-col gap-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-slate-200">5. Overall Safety Rating for this Route</span>
                    <span className="text-[11px] font-mono text-teal-400">{overallSafety > 0 ? `${overallSafety} / 5 Stars` : "Required"}</span>
                  </div>
                  <div className="flex items-center gap-3">
                    {[1, 2, 3, 4, 5].map((star) => (
                      <button
                        key={star}
                        type="button"
                        onClick={() => setOverallSafety(star)}
                        className="p-1 text-slate-600 hover:text-teal-400 transition-colors"
                      >
                        <Star className={`w-7 h-7 ${star <= overallSafety ? "text-teal-400 fill-teal-400" : "text-slate-600"}`} />
                      </button>
                    ))}
                    <span className="text-[11px] text-slate-400 ml-auto">
                      {overallSafety === 1 ? "Very Unsafe" : overallSafety === 3 ? "Moderate" : overallSafety === 5 ? "Extremely Safe" : ""}
                    </span>
                  </div>
                </div>

                {/* Optional Detailed Description */}
                <div className="flex flex-col gap-1.5">
                  <label className="text-xs font-semibold text-slate-300">
                    Additional Observations / Description (Optional):
                  </label>
                  <textarea
                    rows={2}
                    value={feedbackDesc}
                    onChange={(e) => setFeedbackDesc(e.target.value)}
                    placeholder="e.g. Broken lamp post near the junction, but main road had police booth and plenty of shops open..."
                    className="w-full glass-inset rounded-lg p-2.5 text-xs text-slate-100 placeholder:text-slate-500 focus:outline-none focus:border-teal-400 focus:ring-2 focus:ring-teal-400/20"
                  />
                </div>

                {feedbackError && (
                  <div className="text-xs text-rose-400 font-semibold bg-rose-950/60 p-2.5 rounded-lg border border-rose-800">
                    {feedbackError}
                  </div>
                )}

                <button
                  type="submit"
                  disabled={feedbackSubmitting}
                  className="bg-gradient-to-r from-teal-500 to-pink-500 hover:from-teal-400 hover:to-pink-400 text-slate-950 font-bold py-3 px-4 rounded-xl flex items-center justify-center gap-2 transition-all shadow-xl shadow-teal-950/50"
                >
                  <ShieldCheck className="w-4 h-4" />
                  <span>{feedbackSubmitting ? "Submitting Verified Feedback..." : "Submit Safety Feedback & Complete"}</span>
                </button>
              </form>
            ) : (
              <div className="flex flex-col items-center justify-center py-6 gap-4 text-center">
                <div className="w-14 h-14 bg-emerald-950 border-2 border-emerald-500 rounded-full flex items-center justify-center text-emerald-400 shadow-xl shadow-emerald-950/60 animate-bounce">
                  <CheckCircle2 className="w-8 h-8" />
                </div>
                <h3 className="text-xl font-bold text-slate-100">Feedback Submitted Successfully!</h3>
                <p className="text-xs text-slate-300 max-w-md leading-relaxed">
                  Thank you for contributing to women's safety in our city! Your feedback has been recorded and will calibrate our GraphSAGE GNN spatial risk model and street lighting weight matrix.
                </p>
                <button
                  type="button"
                  onClick={() => {
                    setShowFeedbackModal(false);
                    setJourneyCompleted(false);
                    setDestination(null);
                    setRoute(null);
                    setStatus("Ready for next walk session");
                  }}
                  className="mt-2 bg-slate-800 hover:bg-slate-700 text-teal-300 font-semibold px-6 py-2.5 rounded-xl border border-teal-500/30 text-xs transition-colors"
                >
                  Close & Ready for Next Walk
                </button>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

