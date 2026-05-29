"use client";

import Link from "next/link";
import { MapPinned, Radar, ScanSearch } from "lucide-react";

export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen">
      <header className="border-b border-line/70 bg-ink/70 backdrop-blur">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
          <div>
            <p className="text-xs uppercase tracking-[0.35em] text-accent">Ayodhya Land Intelligence</p>
            <h1 className="text-xl font-semibold text-white">ROCI Ayodhya Engine</h1>
          </div>
          <nav className="flex gap-3 text-sm text-muted">
            <Link href="/" className="rounded-full border border-line px-4 py-2 hover:text-white">Home</Link>
            <Link href="/run" className="rounded-full bg-signal px-4 py-2 font-medium text-ink">Run Pipeline</Link>
            <Link href="/portals" className="rounded-full border border-line px-4 py-2 hover:text-white">Portals</Link>
            <Link href="/history" className="rounded-full border border-line px-4 py-2 hover:text-white">History</Link>
            <Link href="/map" className="rounded-full border border-line px-4 py-2 hover:text-white">Map</Link>
          </nav>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-6 py-8">{children}</main>

      <footer className="mx-auto flex max-w-7xl items-center gap-6 px-6 py-8 text-sm text-muted">
        <div className="flex items-center gap-2"><Radar size={16} /> ROCI scoring</div>
        <div className="flex items-center gap-2"><MapPinned size={16} /> GeoJSON parcel output</div>
        <div className="flex items-center gap-2"><ScanSearch size={16} /> Bhunaksha + Bhulekh flow</div>
      </footer>
    </div>
  );
}
