"use client";

import dynamic from "next/dynamic";

import { AppShell } from "@/components/AppShell";
import { HistoryPanel } from "@/components/HistoryPanel";
import { ResultsPanel } from "@/components/ResultsPanel";
import { SearchPanel } from "@/components/SearchPanel";

const MapClient = dynamic(() => import("@/components/MapClient").then((mod) => mod.MapClient), {
  ssr: false,
});

export default function DashboardPage() {
  return (
    <AppShell>
      <section className="mb-6 rounded-[30px] border border-line bg-panel/35 px-6 py-5">
        <p className="text-xs uppercase tracking-[0.35em] text-accent">Dashboard</p>
        <div className="mt-3 flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <h2 className="text-3xl font-semibold">Ayodhya parcel intelligence console</h2>
            <p className="mt-2 max-w-3xl text-sm text-muted">
              Use the map to anchor a parcel, enrich it with gatta metadata, and inspect the resulting Bhunaksha geometry and ROCI response without leaving the dashboard.
            </p>
          </div>
          <div className="rounded-2xl border border-line bg-ink/45 px-4 py-3 text-sm text-muted">
            Flow: select coordinates, optionally add gatta context, run analysis, inspect parcel geometry and JSON output
          </div>
        </div>
      </section>

      <section className="grid gap-6 xl:grid-cols-[1.5fr_0.72fr]">
        <MapClient />
        <div className="grid gap-6 self-start">
          <SearchPanel />
          <ResultsPanel />
          <HistoryPanel compact />
        </div>
      </section>
    </AppShell>
  );
}
