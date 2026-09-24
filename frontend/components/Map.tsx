"use client";

import { MapContainer, TileLayer, Marker, Popup } from "react-leaflet";
import L from "leaflet";

// Fix Leaflet's default marker icon paths when bundled with Webpack/Next.js
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

// Centered on Mumbai, Maharashtra, West India
const MUMBAI_CENTER: [number, number] = [19.0760, 72.8777];

export default function MapComponent() {
  return (
    <div className="w-full h-full min-h-[450px] rounded-lg overflow-hidden border border-slate-700 shadow-xl relative z-10">
      <MapContainer
        center={MUMBAI_CENTER}
        zoom={13}
        scrollWheelZoom={true}
        className="w-full h-full min-h-[450px]"
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <Marker position={MUMBAI_CENTER}>
          <Popup>
            <div className="text-slate-900 font-sans">
              <strong className="text-emerald-700">Mumbai Central, Maharashtra</strong><br />
              SafePath AI Regional Hub (West India)
            </div>
          </Popup>
        </Marker>
      </MapContainer>
    </div>
  );
}

