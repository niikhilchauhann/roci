"use client";

import dynamic from "next/dynamic";

import { AppShell } from "@/components/AppShell";
import { SearchPanel } from "@/components/SearchPanel";

const MapClient = dynamic(() => import("@/components/MapClient").then((mod) => mod.MapClient), {
  ssr: false,
});

export default function MapPage() {
  return (
    <AppShell>
      <section className="grid gap-6 lg:grid-cols-[1.3fr_0.7fr]">
        <MapClient />
        <SearchPanel />
      </section>
    </AppShell>
  );
}
