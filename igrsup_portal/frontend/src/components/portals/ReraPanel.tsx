"use client";

import { useEffect, useState } from "react";

const API = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api";

export function ReraPanel() {
  const [data, setData] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch(`${API}/portals/rera`)
      .then((r) => r.json())
      .then(setData)
      .catch((e) => setError(String(e)));
  }, []);

  const projects = (data?.rera_projects as unknown[]) ?? [];

  return (
    <div className="flex flex-col gap-4">
      <p className="text-sm text-muted">
        Registered RERA projects within the search radius of the last analysed parcel.
      </p>
      {error && <p className="text-sm text-alert">Could not load: {error}</p>}
      {!data && !error && <p className="text-sm text-muted">Loading…</p>}
      {projects.length === 0 && data && <p className="text-sm text-muted">No RERA projects cached yet. Run the pipeline first.</p>}
      {projects.length > 0 && (
        <div className="overflow-x-auto rounded-[20px] border border-line">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-line text-left text-xs text-muted">
                <th className="px-4 py-3">Project</th>
                <th className="px-4 py-3">Stage</th>
                <th className="px-4 py-3">Dist (km)</th>
                <th className="px-4 py-3">Scale Weight</th>
                <th className="px-4 py-3">Stage Mult</th>
              </tr>
            </thead>
            <tbody>
              {projects.map((p: unknown, i) => {
                const proj = p as Record<string, unknown>;
                const detail = proj.detail as Record<string, unknown> | undefined;
                return (
                  <tr key={i} className="border-b border-line/50 hover:bg-line/20">
                    <td className="px-4 py-3 text-white max-w-xs truncate">{String(detail?.project_name ?? proj.project_name ?? "—")}</td>
                    <td className="px-4 py-3 text-muted">{String(proj.stage ?? detail?.stage ?? "—")}</td>
                    <td className="px-4 py-3 tabular-nums">{typeof proj.distance_km === "number" ? proj.distance_km.toFixed(1) : "—"}</td>
                    <td className="px-4 py-3 tabular-nums">{typeof proj.scale_weight === "number" ? proj.scale_weight.toFixed(2) : "—"}</td>
                    <td className="px-4 py-3 tabular-nums">{typeof proj.stage_multiplier === "number" ? proj.stage_multiplier.toFixed(2) : "—"}</td>
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
