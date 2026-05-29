"use client";

import {
  AlertTriangle,
  BarChart3,
  Building2,
  FileJson,
  Landmark,
  MapPinned,
  ShieldAlert,
  Sparkles,
} from "lucide-react";

import type { InfrastructureSummary, ScoreResponse } from "@/lib/types";
import { useLandStore } from "@/store/useLandStore";

function scoreTone(score: number) {
  if (score >= 75) {
    return {
      ring: "from-signal to-emerald-300",
      chip: "border-signal/30 bg-signal/10 text-signal",
      label: "High conviction",
    };
  }

  if (score >= 60) {
    return {
      ring: "from-accent to-cyan-200",
      chip: "border-accent/30 bg-accent/10 text-accent",
      label: "Watchlist positive",
    };
  }

  return {
    ring: "from-alert to-orange-300",
    chip: "border-alert/30 bg-alert/10 text-alert",
    label: "Caution required",
  };
}

function componentBar(score: number) {
  if (score >= 75) return "bg-signal";
  if (score >= 60) return "bg-accent";
  return "bg-alert";
}

function getInfrastructureSummary(result: ScoreResponse): InfrastructureSummary | undefined {
  const value = result.scrape_metadata.infrastructure;

  if (!value || typeof value !== "object" || !("projects" in value)) {
    return undefined;
  }

  return value as InfrastructureSummary;
}

export function ResultsPanel() {
  const result = useLandStore((state) => state.result);

  if (!result) {
    return (
      <section className="rounded-[28px] border border-line bg-panel/70 p-5 shadow-panel">
        <p className="text-xs uppercase tracking-[0.3em] text-accent">Results</p>
        <h2 className="mt-2 text-lg font-semibold">No parcel scored yet</h2>
        <p className="mt-2 text-sm text-muted">
          Run a Bhunaksha and Bhulekh-backed lookup to populate land intelligence output.
        </p>
      </section>
    );
  }

  const tone = scoreTone(result.roci_final);
  const infrastructure = getInfrastructureSummary(result);
  const topProjects = infrastructure?.projects ?? [];
  const riskComponent = result.components.risk_score;
  const confidenceComponent = result.components.confidence_score;
  const detailRows = [
    { label: "Gatta", value: result.parcel.gatta_number },
    { label: "Village", value: result.parcel.village ?? result.bhulekh.village ?? "Unknown" },
    { label: "Tehsil", value: result.parcel.tehsil ?? result.bhulekh.tehsil ?? "Unknown" },
    { label: "Mutation", value: result.bhulekh.mutation_status },
    { label: "Bhoomi Prakar", value: result.bhulekh.bhoomi_prakar },
    { label: "Owner", value: result.bhulekh.owner_name ?? "Unavailable" },
  ];

  return (
    <div className="grid gap-6">
      <div className="grid gap-6 xl:grid-cols-[1.2fr_0.8fr]">
        <section className="overflow-hidden rounded-[30px] border border-line bg-panel/80 shadow-panel">
          <div className="border-b border-line/70 px-6 py-5">
            <p className="text-xs uppercase tracking-[0.32em] text-accent">ROCI Result</p>
            <div className="mt-3 flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
              <div>
                <h2 className="text-2xl font-semibold text-white">{result.parcel.gatta_number}</h2>
                <p className="mt-2 text-sm text-muted">
                  {result.parcel.village ?? "Unknown village"} • {result.parcel.tehsil ?? "Unknown tehsil"} •{" "}
                  {result.parcel.district}
                </p>
              </div>
              <div className={`rounded-full border px-4 py-2 text-xs uppercase tracking-[0.25em] ${tone.chip}`}>
                {tone.label}
              </div>
            </div>
          </div>

          <div className="grid gap-6 px-6 py-6 lg:grid-cols-[240px_1fr]">
            <div className="flex flex-col items-center justify-center rounded-[28px] border border-line bg-ink/50 p-5">
              <div
                className={`flex h-40 w-40 items-center justify-center rounded-full bg-gradient-to-br ${tone.ring} p-[10px]`}
              >
                <div className="flex h-full w-full flex-col items-center justify-center rounded-full bg-ink">
                  <p className="text-xs uppercase tracking-[0.28em] text-muted">Score</p>
                  <p className="mt-2 text-5xl font-semibold text-white">{result.roci_final.toFixed(1)}</p>
                  <p className="mt-2 text-sm text-muted">{result.zone_label}</p>
                </div>
              </div>
              <p className="mt-5 text-center text-sm text-muted">
                Confidence score {confidenceComponent ? confidenceComponent.score.toFixed(1) : "N/A"} based on parcel
                and record quality.
              </p>
            </div>

            <div className="grid gap-4">
              <div className="grid gap-4 md:grid-cols-3">
                <div className="rounded-2xl border border-line bg-ink/45 p-4">
                  <div className="flex items-center gap-2 text-accent">
                    <BarChart3 size={16} />
                    Components
                  </div>
                  <p className="mt-3 text-2xl font-semibold text-white">{Object.keys(result.components).length}</p>
                  <p className="mt-1 text-sm text-muted">Weighted inputs contributing to the final ROCI score.</p>
                </div>

                <div className="rounded-2xl border border-line bg-ink/45 p-4">
                  <div className="flex items-center gap-2 text-signal">
                    <Building2 size={16} />
                    Infra Score
                  </div>
                  <p className="mt-3 text-2xl font-semibold text-white">
                    {infrastructure ? infrastructure.score.toFixed(1) : "N/A"}
                  </p>
                  <p className="mt-1 text-sm text-muted">{infrastructure?.project_count ?? 0} nearby projects assessed.</p>
                </div>

                <div className="rounded-2xl border border-line bg-ink/45 p-4">
                  <div className="flex items-center gap-2 text-alert">
                    <ShieldAlert size={16} />
                    Risk Score
                  </div>
                  <p className="mt-3 text-2xl font-semibold text-white">
                    {riskComponent ? riskComponent.score.toFixed(1) : "N/A"}
                  </p>
                  <p className="mt-1 text-sm text-muted">
                    Legal-operational exposure from parcel confidence and mutation state.
                  </p>
                </div>
              </div>

              <div className="rounded-2xl border border-line bg-ink/45 p-4">
                <div className="flex items-center gap-2 text-white">
                  <Sparkles size={16} className="text-accent" />
                  Component performance
                </div>
                <div className="mt-4 grid gap-4">
                  {Object.entries(result.components).map(([key, component]) => (
                    <div key={key}>
                      <div className="flex items-center justify-between gap-3">
                        <p className="text-sm font-medium text-white">{component.name}</p>
                        <p className="text-sm text-muted">
                          {component.score.toFixed(1)} / 100 • weight {(component.weight * 100).toFixed(0)}%
                        </p>
                      </div>
                      <div className="mt-2 h-2 overflow-hidden rounded-full bg-line/70">
                        <div
                          className={`h-full rounded-full ${componentBar(component.score)}`}
                          style={{ width: `${component.score}%` }}
                        />
                      </div>
                      <p className="mt-2 text-sm text-muted">{component.reason}</p>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </section>

        <div className="grid gap-6">
          <section className="rounded-[30px] border border-line bg-panel/75 p-5 shadow-panel">
            <div className="flex items-center gap-2 text-white">
              <MapPinned size={16} className="text-accent" />
              Parcel details
            </div>
            <div className="mt-4 grid gap-3">
              {detailRows.map((item) => (
                <div
                  key={item.label}
                  className="flex items-start justify-between gap-4 rounded-2xl border border-line bg-ink/45 px-4 py-3"
                >
                  <p className="text-sm text-muted">{item.label}</p>
                  <p className="max-w-[60%] text-right text-sm text-white">{item.value}</p>
                </div>
              ))}
            </div>
          </section>

          <section className="rounded-[30px] border border-line bg-panel/75 p-5 shadow-panel">
            <div className="flex items-center gap-2 text-white">
              <AlertTriangle size={16} className="text-alert" />
              Risk analysis
            </div>
            <div className="mt-4 space-y-3">
              <div className="rounded-2xl border border-line bg-ink/45 p-4">
                <p className="text-sm font-medium text-white">Mutation status</p>
                <p className="mt-2 text-sm text-muted">{result.bhulekh.mutation_status}</p>
              </div>
              <div className="rounded-2xl border border-line bg-ink/45 p-4">
                <p className="text-sm font-medium text-white">Record confidence</p>
                <p className="mt-2 text-sm text-muted">
                  {(result.bhulekh.confidence * 100).toFixed(1)}% extraction confidence from Bhulekh parsing.
                </p>
              </div>
              <div className="rounded-2xl border border-line bg-ink/45 p-4">
                <p className="text-sm font-medium text-white">Parcel source confidence</p>
                <p className="mt-2 text-sm text-muted">
                  {(result.parcel.source_confidence * 100).toFixed(1)}% confidence from Bhunaksha parcel matching.
                </p>
              </div>
            </div>
          </section>
        </div>
      </div>

      <div className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
        <section className="rounded-[30px] border border-line bg-panel/75 p-5 shadow-panel">
          <div className="flex items-center gap-2 text-white">
            <Landmark size={16} className="text-signal" />
            Infrastructure intelligence
          </div>
          <div className="mt-4 rounded-2xl border border-line bg-ink/45 p-4">
            <p className="text-sm text-white">
              Dominant classification:{" "}
              <span className="capitalize text-accent">{infrastructure?.dominant_classification ?? "Unavailable"}</span>
            </p>
            <p className="mt-2 text-sm text-muted">
              {infrastructure?.methodology ?? "Infrastructure summary was not available in the current response."}
            </p>
          </div>

          <div className="mt-4 grid gap-3">
            {topProjects.length > 0 ? (
              topProjects.map((project) => (
                <div key={project.project_id} className="rounded-2xl border border-line bg-ink/45 p-4">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="font-medium text-white">{project.title}</p>
                      <p className="mt-1 text-sm text-muted">
                        {project.authority ?? "Unknown authority"} • {project.category}
                      </p>
                    </div>
                    <div className="rounded-full border border-line px-3 py-1 text-xs uppercase tracking-[0.2em] text-accent">
                      {project.distance_km.toFixed(2)} km
                    </div>
                  </div>
                  <div className="mt-3 flex flex-wrap gap-2 text-xs uppercase tracking-[0.18em] text-muted">
                    <span className="rounded-full border border-line px-3 py-1">{project.source}</span>
                    <span className="rounded-full border border-line px-3 py-1">{project.classification}</span>
                    <span className="rounded-full border border-line px-3 py-1">{project.distance_band}</span>
                    <span className="rounded-full border border-line px-3 py-1">{project.status}</span>
                  </div>
                  <p className="mt-3 text-sm text-muted">
                    Influence score {project.influence_score.toFixed(1)} based on category priority and parcel distance.
                  </p>
                </div>
              ))
            ) : (
              <div className="rounded-2xl border border-line bg-ink/45 p-4 text-sm text-muted">
                No infrastructure projects were attached to the current result.
              </div>
            )}
          </div>
        </section>

        <section className="rounded-[30px] border border-line bg-panel/75 p-5 shadow-panel">
          <div className="flex items-center gap-2 text-white">
            <FileJson size={16} className="text-accent" />
            Structured output
          </div>
          <div className="mt-4 overflow-hidden rounded-2xl border border-line bg-ink/55">
            <pre className="max-h-[720px] overflow-auto p-4 text-xs leading-6 text-muted">
              {JSON.stringify(result, null, 2)}
            </pre>
          </div>
        </section>
      </div>
    </div>
  );
}
