"use client";

import { useState } from "react";
import { AppShell } from "@/components/AppShell";
import { IgrsupPanel } from "@/components/portals/IgrsupPanel";
import { BhulakhPanel } from "@/components/portals/BhulekhPanel";
import { BhunakshaPanel } from "@/components/portals/BhunakshaPanel";
import { CpppPanel } from "@/components/portals/CpppPanel";
import { ReraPanel } from "@/components/portals/ReraPanel";

const TABS = [
  { id: "igrsup", label: "IGRSUP", sublabel: "Deed Registry" },
  { id: "bhunaksha", label: "Bhunaksha", sublabel: "Cadastral Map" },
  { id: "bhulekh", label: "Bhulekh", sublabel: "Land Records" },
  { id: "cppp", label: "CPPP / GeM", sublabel: "Tenders" },
  { id: "rera", label: "UP RERA", sublabel: "Projects" },
];

export default function PortalsPage() {
  const [activeTab, setActiveTab] = useState("igrsup");

  return (
    <AppShell>
      <div className="flex flex-col gap-6">
        <div>
          <p className="text-sm uppercase tracking-[0.35em] text-accent">Data Sources</p>
          <h2 className="mt-2 text-2xl font-semibold text-white">Portal Management</h2>
          <p className="mt-1 text-sm text-muted">Browse cached data and trigger individual portal scrapes.</p>
        </div>

        {/* Tab bar */}
        <div className="flex gap-2 overflow-x-auto pb-1">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex shrink-0 flex-col rounded-[18px] border px-5 py-3 text-left transition-colors ${
                activeTab === tab.id
                  ? "border-accent/40 bg-accent/10 text-white"
                  : "border-line bg-panel/40 text-muted hover:text-white"
              }`}
            >
              <span className="text-sm font-medium">{tab.label}</span>
              <span className="text-xs text-muted">{tab.sublabel}</span>
            </button>
          ))}
        </div>

        {/* Panel content */}
        <div>
          {activeTab === "igrsup" && <IgrsupPanel />}
          {activeTab === "bhunaksha" && <BhunakshaPanel />}
          {activeTab === "bhulekh" && <BhulakhPanel />}
          {activeTab === "cppp" && <CpppPanel />}
          {activeTab === "rera" && <ReraPanel />}
        </div>
      </div>
    </AppShell>
  );
}
