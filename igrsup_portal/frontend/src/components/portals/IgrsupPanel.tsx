"use client";

import { useEffect, useState } from "react";

const API = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api";

type SroEntry = {
  sro_name: string;
  n_current: number;
  n_previous: number;
  p_current_median: number | null;
  circle_rate_inr_cr_per_acre: number | null;
};

type CacheData = {
  __meta?: { mu_district: number; sigma_district: number; scraped_at?: string };
  [sro: string]: unknown;
};

export function IgrsupPanel() {
  const [data, setData] = useState<CacheData | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch(`${API}/igrsup/cache`)
      .then((r) => r.json())
      .then(setData)
      .catch((e) => setError(String(e)));
  }, []);

  const meta = data?.__meta as { mu_district?: number; sigma_district?: number; scraped_at?: string } | undefined;
  const sros = data
    ? Object.entries(data).filter(([k]) => k !== "__meta") as [string, SroEntry][]
    : [];

  return (
    <div className="flex flex-col gap-4">
      {/* Meta */}
      {meta && (
        <div className="grid grid-cols-3 gap-3">
          <Stat label="μ District" value={meta.mu_district?.toFixed(1) ?? "—"} />
          <Stat label="σ District" value={meta.sigma_district?.toFixed(1) ?? "—"} />
          <Stat label="Scraped At" value={meta.scraped_at ? new Date(meta.scraped_at).toLocaleDateString() : "—"} />
        </div>
      )}

      {error && <p className="text-sm text-alert">Could not load IGRSUP cache: {error}</p>}
      {!data && !error && <p className="text-sm text-muted">Loading…</p>}

      {/* SRO table */}
      {sros.length > 0 && (
        <div className="overflow-x-auto rounded-[20px] border border-line">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-line text-left text-xs text-muted">
                <th className="px-4 py-3">SRO</th>
                <th className="px-4 py-3">n_current</th>
                <th className="px-4 py-3">n_previous</th>
                <th className="px-4 py-3">Median ₹/sqft</th>
                <th className="px-4 py-3">Circle Rate (Cr/acre)</th>
              </tr>
            </thead>
            <tbody>
              {sros.map(([id, s]) => (
                <tr key={id} className="border-b border-line/50 hover:bg-line/20">
                  <td className="px-4 py-3 font-medium text-white">{(s as SroEntry).sro_name ?? id}</td>
                  <td className="px-4 py-3 tabular-nums">{(s as SroEntry).n_current ?? "—"}</td>
                  <td className="px-4 py-3 tabular-nums">{(s as SroEntry).n_previous ?? "—"}</td>
                  <td className="px-4 py-3 tabular-nums">
                    {(s as SroEntry).p_current_median != null ? (s as SroEntry).p_current_median!.toFixed(2) : <span className="text-muted">null</span>}
                  </td>
                  <td className="px-4 py-3 tabular-nums">
                    {(s as SroEntry).circle_rate_inr_cr_per_acre != null
                      ? (s as SroEntry).circle_rate_inr_cr_per_acre!.toFixed(4)
                      : <span className="text-muted">—</span>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <p className="text-xs text-muted">
        Source: <code className="text-accent">out/igrsup_sro_cache.json</code>. Refresh by running{" "}
        <code className="text-accent">python scripts/cache_igrsup_sros.py</code>.
      </p>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-[18px] border border-line bg-panel/50 px-4 py-3">
      <p className="text-xs text-muted">{label}</p>
      <p className="mt-1 text-lg font-semibold text-white tabular-nums">{value}</p>
    </div>
  );
}
