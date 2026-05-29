"use client";

import { useState } from "react";

const API = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api";

export function BhunakshaPanel() {
  const [lat, setLat] = useState("26.7954");
  const [lng, setLng] = useState("82.1942");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState<string | null>(null);

  const run = async () => {
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const r = await fetch(`${API}/bhunaksha`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ coordinates: { lat: parseFloat(lat), lng: parseFloat(lng) } }),
      });
      const data = await r.json();
      if (!r.ok) throw new Error(data.detail ?? r.statusText);
      setResult(data);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col gap-4">
      <p className="text-sm text-muted">
        Look up a cadastral parcel by coordinates. Returns gatta number, village, parcel geometry, and source confidence.
      </p>
      <div className="flex flex-wrap gap-3">
        <input value={lat} onChange={(e) => setLat(e.target.value)} placeholder="Lat" className="w-36 rounded-xl border border-line bg-ink px-3 py-2 text-sm text-white focus:border-accent focus:outline-none" />
        <input value={lng} onChange={(e) => setLng(e.target.value)} placeholder="Lng" className="w-36 rounded-xl border border-line bg-ink px-3 py-2 text-sm text-white focus:border-accent focus:outline-none" />
        <button onClick={run} disabled={loading} className="rounded-full bg-signal px-5 py-2 text-sm font-medium text-ink disabled:opacity-40">
          {loading ? "Fetching…" : "Fetch Parcel"}
        </button>
      </div>
      {error && <p className="text-sm text-alert">{error}</p>}
      {result && (
        <pre className="max-h-64 overflow-auto rounded-[18px] border border-line bg-ink p-4 text-xs text-muted">
          {JSON.stringify(result, null, 2)}
        </pre>
      )}
    </div>
  );
}
