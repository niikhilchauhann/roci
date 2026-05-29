"use client";

import { useState } from "react";

const API = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api";

export function BhulakhPanel() {
  const [gatta, setGatta] = useState("374");
  const [village, setVillage] = useState("Akbar Bazar");
  const [tehsil, setTehsil] = useState("Sadar");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState<string | null>(null);

  const run = async () => {
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const r = await fetch(`${API}/bhulekh`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ gatta_number: gatta, village, tehsil }),
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
        Look up Bhulekh land records by gatta number. Returns mutation status, bhoomi prakar, and owner name.
      </p>
      <div className="flex flex-wrap gap-3">
        <input value={gatta} onChange={(e) => setGatta(e.target.value)} placeholder="Gatta #" className="w-28 rounded-xl border border-line bg-ink px-3 py-2 text-sm text-white focus:border-accent focus:outline-none" />
        <input value={village} onChange={(e) => setVillage(e.target.value)} placeholder="Village" className="w-40 rounded-xl border border-line bg-ink px-3 py-2 text-sm text-white focus:border-accent focus:outline-none" />
        <input value={tehsil} onChange={(e) => setTehsil(e.target.value)} placeholder="Tehsil" className="w-32 rounded-xl border border-line bg-ink px-3 py-2 text-sm text-white focus:border-accent focus:outline-none" />
        <button onClick={run} disabled={loading} className="rounded-full bg-signal px-5 py-2 text-sm font-medium text-ink disabled:opacity-40">
          {loading ? "Fetching…" : "Fetch Record"}
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
