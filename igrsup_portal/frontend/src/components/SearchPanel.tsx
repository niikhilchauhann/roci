"use client";

import { LoaderCircle, MapPinned, Search } from "lucide-react";

import { useLandStore } from "@/store/useLandStore";

export function SearchPanel() {
  const coordinates = useLandStore((state) => state.coordinates);
  const gattaNumber = useLandStore((state) => state.gattaNumber);
  const village = useLandStore((state) => state.village);
  const tehsil = useLandStore((state) => state.tehsil);
  const captchaToken = useLandStore((state) => state.captchaToken);
  const loading = useLandStore((state) => state.loading);
  const error = useLandStore((state) => state.error);
  const setField = useLandStore((state) => state.setField);
  const runScore = useLandStore((state) => state.runScore);

  return (
    <section className="rounded-[28px] border border-line bg-panel/80 p-5 shadow-panel">
      <div className="mb-5 flex items-start justify-between gap-3">
        <div>
          <p className="text-xs uppercase tracking-[0.3em] text-accent">Land Search</p>
          <h2 className="text-lg font-semibold">Coordinate or gatta lookup</h2>
        </div>
        <div className="rounded-full border border-line bg-ink/50 px-3 py-1 text-xs uppercase tracking-[0.2em] text-muted">Ayodhya only</div>
      </div>

      <div className="grid gap-4">
        <div className="rounded-2xl border border-line bg-ink/50 p-4">
          <div className="flex items-start gap-3">
            <MapPinned size={18} className="mt-0.5 text-accent" />
            <div className="text-sm">
              <p className="text-white">Spatial input</p>
              <p className="mt-1 text-muted">
                {coordinates
                  ? `Selected coordinates: ${coordinates.lat.toFixed(6)}, ${coordinates.lng.toFixed(6)}`
                  : "Click on the map to capture parcel coordinates inside Ayodhya."}
              </p>
            </div>
          </div>
        </div>

        <input
          value={gattaNumber}
          onChange={(event) => setField("gattaNumber", event.target.value)}
          placeholder="Gatta number"
          className="rounded-2xl border border-line bg-ink/60 px-4 py-3 outline-none transition focus:border-accent"
        />
        <input
          value={village}
          onChange={(event) => setField("village", event.target.value)}
          placeholder="Village"
          className="rounded-2xl border border-line bg-ink/60 px-4 py-3 outline-none transition focus:border-accent"
        />
        <input
          value={tehsil}
          onChange={(event) => setField("tehsil", event.target.value)}
          placeholder="Tehsil"
          className="rounded-2xl border border-line bg-ink/60 px-4 py-3 outline-none transition focus:border-accent"
        />
        <input
          value={captchaToken}
          onChange={(event) => setField("captchaToken", event.target.value)}
          placeholder="Bhulekh CAPTCHA token placeholder"
          className="rounded-2xl border border-line bg-ink/60 px-4 py-3 outline-none transition focus:border-accent"
        />

        <button
          onClick={() => void runScore()}
          disabled={loading}
          className="flex items-center justify-center gap-2 rounded-2xl bg-signal px-4 py-3 font-medium text-ink transition hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-70"
        >
          {loading ? <LoaderCircle className="animate-spin" size={18} /> : <Search size={18} />}
          {loading ? "Scoring parcel..." : "Run ROCI analysis"}
        </button>

        {error ? <div className="rounded-2xl border border-alert/30 bg-alert/10 p-4 text-sm text-alert">{error}</div> : null}
      </div>
    </section>
  );
}
