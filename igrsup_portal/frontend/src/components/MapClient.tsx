"use client";

import "leaflet/dist/leaflet.css";

import { useCallback, useEffect, useRef } from "react";
import { Crosshair, LocateFixed, MapPin, RotateCcw } from "lucide-react";
import { MapContainer, Marker, Polygon, TileLayer, useMap } from "react-leaflet";
import L from "leaflet";
import type { LeafletMouseEvent, Map as LeafletMap } from "leaflet";

import { useLandStore } from "@/store/useLandStore";
import type { Viewport } from "@/lib/types";

const ayodhyaCenter: [number, number] = [26.7999, 82.2042];
const ayodhyaBounds: [[number, number], [number, number]] = [
  [26.6, 81.95],
  [27.0, 82.45],
];

const markerIcon = L.icon({
  iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
  shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
  iconAnchor: [12, 41],
});

function toLeafletPolygonRings(geometry: { type: "Polygon" | "MultiPolygon"; coordinates: unknown }): [number, number][][] {
  if (geometry.type === "Polygon") {
    const polygon = geometry.coordinates as number[][][];
    return [polygon[0].map(([lng, lat]) => [lat, lng] as [number, number])];
  }

  const multiPolygon = geometry.coordinates as number[][][][];
  return multiPolygon.map((polygon) => polygon[0].map(([lng, lat]) => [lat, lng] as [number, number]));
}

function viewportEqual(left: Viewport, right: Viewport) {
  return (
    left.zoom === right.zoom &&
    left.center[0] === right.center[0] &&
    left.center[1] === right.center[1]
  );
}

function MapEventBridge() {
  const map = useMap();
  const setCoordinates = useLandStore((state) => state.setCoordinates);
  const setViewport = useLandStore((state) => state.setViewport);
  const setViewportRef = useRef(setViewport);
  const setCoordinatesRef = useRef(setCoordinates);

  useEffect(() => {
    setViewportRef.current = setViewport;
    setCoordinatesRef.current = setCoordinates;
  }, [setViewport, setCoordinates]);

  const handleClick = useCallback((event: LeafletMouseEvent) => {
    const nextViewport: Viewport = {
      center: [event.latlng.lat, event.latlng.lng],
      zoom: 15,
    };
    setCoordinatesRef.current({ lat: event.latlng.lat, lng: event.latlng.lng });
    setViewportRef.current(nextViewport);
  }, []);

  const handleMoveEnd = useCallback((activeMap: LeafletMap) => {
    const center = activeMap.getCenter();
    setViewportRef.current({
      center: [center.lat, center.lng],
      zoom: activeMap.getZoom(),
    });
  }, []);

  useEffect(() => {
    const onClick = (event: LeafletMouseEvent) => handleClick(event);
    const onMoveEnd = () => handleMoveEnd(map);

    map.on("click", onClick);
    map.on("moveend", onMoveEnd);

    return () => {
      map.off("click", onClick);
      map.off("moveend", onMoveEnd);
    };
  }, [map, handleClick, handleMoveEnd]);

  return null;
}

function MapViewportController() {
  const map = useMap();
  const viewport = useLandStore((state) => state.viewport);
  const appliedViewportRef = useRef<Viewport | null>(null);

  useEffect(() => {
    const currentCenter = map.getCenter();
    const currentViewport: Viewport = {
      center: [currentCenter.lat, currentCenter.lng],
      zoom: map.getZoom(),
    };

    if (viewportEqual(currentViewport, viewport)) {
      appliedViewportRef.current = viewport;
      return;
    }

    if (appliedViewportRef.current && viewportEqual(appliedViewportRef.current, viewport)) {
      return;
    }

    appliedViewportRef.current = viewport;
    map.setView(viewport.center, viewport.zoom, { animate: true });
  }, [map, viewport]);

  return null;
}

function MapGeometryController({ polygonPositions }: { polygonPositions: [number, number][][] }) {
  const map = useMap();
  const lastGeometryKeyRef = useRef<string>("");

  useEffect(() => {
    if (polygonPositions.length === 0) {
      lastGeometryKeyRef.current = "";
      return;
    }

    const key = JSON.stringify(polygonPositions);
    if (lastGeometryKeyRef.current === key) {
      return;
    }

    lastGeometryKeyRef.current = key;
    const bounds = L.latLngBounds(polygonPositions.flat());
    if (bounds.isValid()) {
      map.fitBounds(bounds, { padding: [24, 24] });
    }
  }, [map, polygonPositions]);

  return null;
}

export function MapClient() {
  const coordinates = useLandStore((state) => state.coordinates);
  const resetCoordinates = useLandStore((state) => state.resetCoordinates);
  const resetViewport = useLandStore((state) => state.resetViewport);
  const result = useLandStore((state) => state.result);
  const geometry = result?.parcel.geometry;
  const polygonPositions: [number, number][][] = geometry ? toLeafletPolygonRings(geometry) : [];

  return (
    <section className="overflow-hidden rounded-[30px] border border-line bg-panel/75 shadow-panel">
      <div className="flex flex-wrap items-start justify-between gap-4 border-b border-line/80 px-5 py-4">
        <div>
          <p className="text-xs uppercase tracking-[0.32em] text-accent">Spatial Console</p>
          <h2 className="mt-2 text-xl font-semibold">Ayodhya parcel map</h2>
          <p className="mt-1 text-sm text-muted">Click inside the Ayodhya viewport to capture coordinates and anchor a parcel lookup.</p>
        </div>
        <div className="flex flex-wrap gap-2 text-sm">
          <button
            onClick={resetViewport}
            className="flex items-center gap-2 rounded-full border border-line bg-ink/60 px-4 py-2 text-muted transition hover:text-white"
          >
            <LocateFixed size={16} />
            Recenter Ayodhya
          </button>
          <button
            onClick={resetCoordinates}
            className="flex items-center gap-2 rounded-full border border-line bg-ink/60 px-4 py-2 text-muted transition hover:text-white"
          >
            <RotateCcw size={16} />
            Clear selection
          </button>
        </div>
      </div>

      <div className="grid gap-0 xl:grid-cols-[1fr_280px]">
        <div className="relative h-[640px]">
          <div className="absolute left-4 top-4 z-[500] rounded-2xl border border-line/80 bg-ink/85 px-4 py-3 text-sm shadow-lg backdrop-blur">
            <div className="flex items-center gap-2 text-white">
              <Crosshair size={16} className="text-signal" />
              {coordinates ? "Selection captured" : "Awaiting map click"}
            </div>
            <p className="mt-2 text-xs uppercase tracking-[0.25em] text-muted">Viewport</p>
            <p className="mt-1 text-sm text-white">Ayodhya, Uttar Pradesh</p>
            <p className="text-sm text-muted">
              {coordinates ? `${coordinates.lat.toFixed(6)}, ${coordinates.lng.toFixed(6)}` : "No coordinates selected"}
            </p>
          </div>

          <MapContainer
            center={ayodhyaCenter}
            zoom={12}
            minZoom={11}
            maxZoom={18}
            maxBounds={ayodhyaBounds}
            maxBoundsViscosity={0.9}
            className="h-full w-full"
            zoomControl={false}
          >
            <MapViewportController />
            <MapEventBridge />
            <MapGeometryController polygonPositions={polygonPositions} />
            <TileLayer
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            />
            {coordinates ? <Marker position={[coordinates.lat, coordinates.lng]} icon={markerIcon} /> : null}
            {polygonPositions.map((positions, index) => (
              <Polygon
                key={`${result?.parcel.gatta_number ?? "parcel"}-${index}`}
                positions={positions}
                pathOptions={{ color: "#30c48d", weight: 2, fillOpacity: 0.18 }}
              />
            ))}
          </MapContainer>
        </div>

        <aside className="border-l border-line/80 bg-ink/30 p-5">
          <div className="rounded-2xl border border-line bg-ink/50 p-4">
            <p className="text-xs uppercase tracking-[0.25em] text-accent">Selection</p>
            <div className="mt-3 flex items-start gap-3">
              <MapPin size={18} className="mt-0.5 text-signal" />
              <div className="text-sm">
                <p className="text-white">Coordinate target</p>
                <p className="mt-1 text-muted">
                  {coordinates ? `${coordinates.lat.toFixed(6)}, ${coordinates.lng.toFixed(6)}` : "Click on the parcel location to begin."}
                </p>
              </div>
            </div>
          </div>

          <div className="mt-4 rounded-2xl border border-line bg-ink/50 p-4 text-sm text-muted">
            <p className="text-xs uppercase tracking-[0.25em] text-accent">Operator Notes</p>
            <p className="mt-3">The map is constrained to the Ayodhya MVP boundary to prevent accidental out-of-scope lookups.</p>
            <p className="mt-3">Selected coordinates are pushed into the search panel and used directly for Bhunaksha parcel matching.</p>
            <p className="mt-3">Returned parcel geometry is drawn on the map after scoring so the analyst can verify spatial fit.</p>
          </div>
        </aside>
      </div>
    </section>
  );
}
