"use client";

import { useState } from "react";
import dynamic from "next/dynamic";
import { AppShell } from "@/components/AppShell";
import type { RunParams } from "@/lib/pipeline";

const PipelineRunner = dynamic(
  () => import("@/components/PipelineRunner").then((m) => m.PipelineRunner),
  { ssr: false }
);

type FormState = {
  lat: string;
  lng: string;
  area_sqft: string;
  gatta_number: string;
  zone_type: string;
  fixture_only: boolean;
};

const ZONE_OPTIONS = [
  { value: "urban_expansion", label: "Urban Expansion" },
  { value: "peri_urban", label: "Peri-Urban" },
  { value: "agricultural_greenfield", label: "Agricultural Greenfield" },
  { value: "industrial_corridor", label: "Industrial Corridor" },
  { value: "rural_development", label: "Rural Development" },
  { value: "smart_city", label: "Smart City" },
];

export default function RunPage() {
  const [form, setForm] = useState<FormState>({
    lat: "26.7954",
    lng: "82.1942",
    area_sqft: "5000",
    gatta_number: "",
    zone_type: "urban_expansion",
    fixture_only: false,
  });
  const [runParams, setRunParams] = useState<RunParams | null>(null);
  const [running, setRunning] = useState(false);

  const set = (key: keyof FormState) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const value = e.target.type === "checkbox" ? (e.target as HTMLInputElement).checked : e.target.value;
    setForm((f) => ({ ...f, [key]: value }));
  };

  const handleSubmit = () => {
    const lat = parseFloat(form.lat);
    const lng = parseFloat(form.lng);
    const area_sqft = parseFloat(form.area_sqft);
    if (isNaN(lat) || isNaN(lng) || isNaN(area_sqft)) {
      alert("Please enter valid numbers for Latitude, Longitude, and Area.");
      return;
    }
    setRunParams({
      lat,
      lng,
      area_sqft,
      gatta_number: form.gatta_number || undefined,
      zone_type: form.zone_type,
      fixture_only: form.fixture_only,
    });
    setRunning(true);
  };

  const handleReset = () => {
    setRunParams(null);
    setRunning(false);
  };

  return (
    <AppShell>
      <div className="grid gap-8 lg:grid-cols-[420px_1fr]">
        {/* Input form */}
        <div className="rounded-[28px] border border-line bg-panel/60 p-7 shadow-panel">
          <p className="text-sm uppercase tracking-[0.35em] text-accent">New Analysis</p>
          <h2 className="mt-3 text-2xl font-semibold text-white">Run Pipeline</h2>
          <p className="mt-2 text-sm text-muted">Enter parcel coordinates, area, and optional gatta number to run the full 9-stage ROCI pipeline.</p>

          <div className="mt-6 flex flex-col gap-4">
            <div className="grid grid-cols-2 gap-3">
              <label className="flex flex-col gap-1">
                <span className="text-xs text-muted">Latitude</span>
                <input
                  type="number" step="any" required
                  value={form.lat} onChange={set("lat")}
                  disabled={running}
                  className="rounded-xl border border-line bg-ink px-3 py-2 text-sm text-white placeholder-muted focus:border-accent focus:outline-none disabled:opacity-40"
                  placeholder="26.7954"
                />
              </label>
              <label className="flex flex-col gap-1">
                <span className="text-xs text-muted">Longitude</span>
                <input
                  type="number" step="any" required
                  value={form.lng} onChange={set("lng")}
                  disabled={running}
                  className="rounded-xl border border-line bg-ink px-3 py-2 text-sm text-white placeholder-muted focus:border-accent focus:outline-none disabled:opacity-40"
                  placeholder="82.1942"
                />
              </label>
            </div>

            <label className="flex flex-col gap-1">
              <span className="text-xs text-muted">Area (sq ft)</span>
              <input
                type="number" step="any" required min="1"
                value={form.area_sqft} onChange={set("area_sqft")}
                disabled={running}
                className="rounded-xl border border-line bg-ink px-3 py-2 text-sm text-white focus:border-accent focus:outline-none disabled:opacity-40"
              />
            </label>

            <label className="flex flex-col gap-1">
              <span className="text-xs text-muted">Gatta Number (optional)</span>
              <input
                type="text"
                value={form.gatta_number} onChange={set("gatta_number")}
                disabled={running}
                className="rounded-xl border border-line bg-ink px-3 py-2 text-sm text-white focus:border-accent focus:outline-none disabled:opacity-40"
                placeholder="e.g. 374"
              />
            </label>

            <label className="flex flex-col gap-1">
              <span className="text-xs text-muted">Zone Type</span>
              <select
                value={form.zone_type} onChange={set("zone_type")}
                disabled={running}
                className="rounded-xl border border-line bg-ink px-3 py-2 text-sm text-white focus:border-accent focus:outline-none disabled:opacity-40"
              >
                {ZONE_OPTIONS.map((z) => (
                  <option key={z.value} value={z.value}>{z.label}</option>
                ))}
              </select>
            </label>

            <label className="flex items-center gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={form.fixture_only} onChange={set("fixture_only")}
                disabled={running}
                className="h-4 w-4 rounded border-line accent-signal"
              />
              <span className="text-sm text-muted">Fixture-only mode (skip live scraping)</span>
            </label>

            <div className="flex gap-3 pt-2">
              <button
                type="button"
                onClick={handleSubmit}
                disabled={running}
                className="flex-1 rounded-full bg-signal py-3 font-medium text-ink hover:bg-signal/90 disabled:opacity-40 transition-opacity"
              >
                {running ? "Running…" : "Run Pipeline"}
              </button>
              {running && (
                <button
                  type="button" onClick={handleReset}
                  className="rounded-full border border-line px-4 py-3 text-sm text-muted hover:text-white"
                >
                  Reset
                </button>
              )}
            </div>
          </div>
        </div>

        {/* Pipeline runner / progress */}
        <div>
          {runParams ? (
            <PipelineRunner params={runParams} onReset={handleReset} />
          ) : (
            <div className="flex h-full min-h-[400px] items-center justify-center rounded-[28px] border border-dashed border-line text-center text-muted">
              <div>
                <p className="text-lg font-medium text-white">No pipeline running</p>
                <p className="mt-2 text-sm">Fill in the form and click Run Pipeline to start.</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </AppShell>
  );
}
