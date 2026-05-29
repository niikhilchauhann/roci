"use client";

import { useEffect, useState } from "react";

const API = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api";

export function CpppPanel() {
  const [data, setData] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch(`${API}/portals/cppp`)
      .then((r) => r.json())
      .then(setData)
      .catch((e) => setError(String(e)));
  }, []);

  const projects = (data?.infra_projects as unknown[]) ?? [];

  return (
    <div className="flex flex-col gap-4">
      <p className="text-sm text-muted">
        Infrastructure tenders from CPPP and GeM within 10 km of the last analysed parcel.
      </p>
      {error && <p className="text-sm text-alert">Could not load: {error}</p>}
      {!data && !error && <p className="text-sm text-muted">Loading…</p>}
      {projects.length === 0 && data && <p className="text-sm text-muted">No projects cached yet. Run the pipeline first.</p>}
      {projects.length > 0 && (
        <div className="overflow-x-auto rounded-[20px] border border-line">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-line text-left text-xs text-muted">
                <th className="px-4 py-3">Title</th>
                <th className="px-4 py-3">Type</th>
                <th className="px-4 py-3">Stage</th>
                <th className="px-4 py-3">Dist (km)</th>
                <th className="px-4 py-3">Weight</th>
              </tr>
            </thead>
            <tbody>
              {projects.map((p: unknown, i) => {
                const proj = p as Record<string, unknown>;
                return (
                  <tr key={i} className="border-b border-line/50 hover:bg-line/20">
                    <td className="px-4 py-3 text-white max-w-xs truncate">{String(proj.title ?? "—")}</td>
                    <td className="px-4 py-3 text-muted">{String(proj.type ?? "—")}</td>
                    <td className="px-4 py-3 text-muted">{String(proj.stage ?? "—")}</td>
                    <td className="px-4 py-3 tabular-nums">{typeof proj.distance_km === "number" ? proj.distance_km.toFixed(1) : "—"}</td>
                    <td className="px-4 py-3 tabular-nums">{typeof proj.type_weight === "number" ? proj.type_weight.toFixed(2) : "—"}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
