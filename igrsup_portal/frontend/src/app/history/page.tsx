"use client";

import { AppShell } from "@/components/AppShell";
import { HistoryPanel } from "@/components/HistoryPanel";

export default function HistoryPage() {
  return (
    <AppShell>
      <section className="mb-6 rounded-[30px] border border-line bg-panel/35 px-6 py-5">
        <p className="text-xs uppercase tracking-[0.35em] text-accent">History</p>
        <div className="mt-3">
          <h2 className="text-3xl font-semibold">Persistent parcel analysis history</h2>
          <p className="mt-2 max-w-3xl text-sm text-muted">
            Review past analyses, search by gatta number or village, reload older results into the results view, and export the full CSV archive.
          </p>
        </div>
      </section>

      <section className="mx-auto max-w-7xl">
        <HistoryPanel />
      </section>
    </AppShell>
  );
}
