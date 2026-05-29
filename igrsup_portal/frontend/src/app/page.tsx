import Link from "next/link";

import { AppShell } from "@/components/AppShell";

export default function HomePage() {
  return (
    <AppShell>
      <section className="grid gap-8 lg:grid-cols-[1.1fr_0.9fr]">
        <div className="rounded-[32px] border border-line bg-panel/60 p-8 shadow-panel">
          <p className="text-sm uppercase tracking-[0.35em] text-accent">Ayodhya MVP</p>
          <h2 className="mt-4 max-w-2xl text-4xl font-semibold leading-tight">
            Coordinate-driven land intelligence for Ayodhya, built around Bhunaksha, Bhulekh, and GIS-native scoring.
          </h2>
          <p className="mt-5 max-w-2xl text-base text-muted">
            Select a parcel on the map or enter a gatta number, fetch structured land context, and compute an investment-oriented ROCI score with GeoJSON parcel output.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Link href="/dashboard" className="rounded-full bg-signal px-5 py-3 font-medium text-ink">Open Dashboard</Link>
            <Link href="/map" className="rounded-full border border-line px-5 py-3 text-white">Go to Map</Link>
          </div>
        </div>

        <div className="grid gap-4">
          <div className="rounded-[28px] border border-line bg-panel/50 p-6">
            <p className="text-sm text-accent">Phase 1 coverage</p>
            <p className="mt-2 text-muted">Interactive map, parcel geometry, API-backed scoring, and scraper-first foundations for Ayodhya government land intelligence workflows.</p>
          </div>
          <div className="rounded-[28px] border border-line bg-panel/50 p-6">
            <p className="text-sm text-accent">Backend contract</p>
            <p className="mt-2 font-mono text-sm text-muted">/api/score • /api/bhunaksha • /api/bhulekh • /api/health</p>
          </div>
          <div className="rounded-[28px] border border-line bg-panel/50 p-6">
            <p className="text-sm text-accent">Spatial focus</p>
            <p className="mt-2 text-muted">Ayodhya-centered viewport, Ayodhya boundary validation, GeoJSON-ready parcel responses, and PostGIS-compatible model shape.</p>
          </div>
        </div>
      </section>
    </AppShell>
  );
}
