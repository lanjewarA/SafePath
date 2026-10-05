"use client";

import { useEffect } from "react";
import { CircleMarker, MapContainer, Polyline, Popup, TileLayer, useMap, useMapEvents } from "react-leaflet";
import type { LatLngExpression } from "leaflet";

type Coordinates = { lat: number; lon: number };
type SafeWalkMapProps = {
  position: Coordinates | null;
  destination: Coordinates | null;
  routeCoordinates: number[][];
  onDestinationSelect: (destination: Coordinates) => void;
};

const MUMBAI_CENTER: LatLngExpression = [19.076, 72.8777];

function MapInteraction({ position, routeCoordinates, onDestinationSelect }: Pick<SafeWalkMapProps, "position" | "routeCoordinates" | "onDestinationSelect">) {
  const map = useMap();
  useMapEvents({
    click(event) {
      onDestinationSelect({ lat: event.latlng.lat, lon: event.latlng.lng });
    },
  });

  useEffect(() => {
    if (routeCoordinates.length > 1) {
      map.fitBounds(routeCoordinates.map(([lat, lon]) => [lat, lon] as [number, number]), { padding: [32, 32] });
    }
  }, [map, routeCoordinates]);

  useEffect(() => {
    if (position && routeCoordinates.length <= 1) {
      map.flyTo([position.lat, position.lon], Math.max(map.getZoom(), 15), { duration: 0.6 });
    }
  }, [map, position, routeCoordinates.length]);

  return null;
}

export default function SafeWalkMap({ position, destination, routeCoordinates, onDestinationSelect }: SafeWalkMapProps) {
  return (
    <div className="h-[480px] w-full bg-slate-900">
      <MapContainer center={MUMBAI_CENTER} zoom={13} scrollWheelZoom className="h-full w-full">
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <MapInteraction position={position} routeCoordinates={routeCoordinates} onDestinationSelect={onDestinationSelect} />
        {routeCoordinates.length > 1 && <Polyline positions={routeCoordinates as LatLngExpression[]} pathOptions={{ color: "#2dd4bf", weight: 6, opacity: 0.9 }} />}
        {position && (
          <CircleMarker center={[position.lat, position.lon]} radius={9} pathOptions={{ color: "#99f6e4", fillColor: "#0d9488", fillOpacity: 1, weight: 3 }}>
            <Popup>Your live location</Popup>
          </CircleMarker>
        )}
        {destination && (
          <CircleMarker center={[destination.lat, destination.lon]} radius={8} pathOptions={{ color: "#f9a8d4", fillColor: "#db2777", fillOpacity: 1, weight: 3 }}>
            <Popup>Selected destination</Popup>
          </CircleMarker>
        )}
      </MapContainer>
    </div>
  );
}