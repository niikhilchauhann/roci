"use client";

import type { PipelineResult } from "@/lib/pipeline";

const ZONE_COLORS: Record<number, string> = {
  1: "text-muted",
  2: "text-accent",
  3: "text-signal",
  4: "text-signal",
  5: "text-yellow-400",
};

const COMPONENT_LABELS: Record<string, string> = {
  clu_t: "CLU Score",
  rv_t: "Registry Velocity",
  is_t: "Infra Score",
  rera_d: "RERA Density",
  base_score: "Base Score",
  velocity_z: "Velocity Z",
  r_total: "Risk Penalty",
  c_score: "Confidence",
  roci_final: "ROCI Final",
};

export function ScoreCard({ result }: { result: PipelineResult }) {
  const score = result.roci_final ?? 0;
  // c_score and zone live inside components, not at the top level
  const components = result.components ?? {};
  const confidence = ((components.c_score ?? result.c_score ?? 0) as number) * 100;
  const zoneLabel = result.zone_label ?? "";
  const zoneNum = parseInt(zoneLabel.match(/Zone\s*(\d)/)?.[1] ?? "0");

  const scoreColor =
    score >= 70 ? "text-signal" :
    score >= 50 ? "text-accent" :
    score >= 35 ? "text-yellow-400" : "text-alert";

  return (
    <div className="rounded-[28px] border border-line bg-panel/60 p-6 shadow-panel">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs uppercase tracking-widest text-muted">ROCI Score</p>
          <p className={`mt-1 text-6xl font-bold tabular-nums ${scoreColor}`}>
            {typeof score === "number" ? score.toFixed(1) : "—"}
          </p>
          <p className={`mt-1 text-sm font-medium ${ZONE_COLORS[zoneNum] ?? "text-muted"}`}>
            {result.zone_label ?? "Unknown"}
          </p>
        </div>

        {/* Confidence gauge */}
        <div className="flex flex-col items-center gap-1">
          <p className="text-xs text-muted">Confidence</p>
          <svg viewBox="0 0 80 80" className="w-16 h-16">
            <circle cx="40" cy="40" r="32" fill="none" stroke="#1e3554" strokeWidth="8" />
            <circle
              cx="40" cy="40" r="32" fill="none"
              stroke={confidence >= 60 ? "#30c48d" : "#ff7a59"}
              strokeWidth="8"
              strokeDasharray={`${(confidence / 100) * 201} 201`}
              strokeLinecap="round"
              transform="rotate(-90 40 40)"
            />
            <text x="40" y="45" textAnchor="middle" fontSize="14" fontWeight="bold" fill="white">
              {confidence.toFixed(0)}%
            </text>
          </svg>
          <p className={`text-xs ${confidence >= 60 ? "text-signal" : "text-alert"}`}>
            {result.status === "SUPPRESSED" ? "SUPPRESSED" : confidence >= 60 ? "OK" : "LOW"}
          </p>
        </div>
      </div>

      {/* Risk flags */}
      {result.risk_flags && result.risk_flags.length > 0 && (
        <div className="mt-4 flex flex-wrap gap-2">
          {result.risk_flags.map((f) => (
            <span key={f} className="rounded-full border border-alert/40 bg-alert/10 px-3 py-0.5 text-xs text-alert">
              {f}
            </span>
          ))}
        </div>
      )}

      {/* Component breakdown */}
      <div className="mt-5">
        <p className="mb-3 text-xs uppercase tracking-widest text-muted">Score Components</p>
        <div className="grid gap-2 sm:grid-cols-2">
          {Object.entries(components)
            .filter(([k]) => k !== "roci_final")
            .map(([key, val]) => {
              const num = typeof val === "number" ? val : parseFloat(String(val));
              const pct = Math.min(Math.abs(isNaN(num) ? 0 : num) * 100, 100);
              const isNeg = num < 0;
              return (
                <div key={key} className="flex flex-col gap-1">
                  <div className="flex justify-between text-xs">
                    <span className="text-muted">{COMPONENT_LABELS[key] ?? key}</span>
                    <span className={`tabular-nums font-medium ${isNeg ? "text-alert" : "text-white"}`}>
                      {isNaN(num) ? "—" : num.toFixed(3)}
                    </span>
                  </div>
                  <div className="h-1 rounded-full bg-line overflow-hidden">
                    <div
                      className={`h-full rounded-full ${isNeg ? "bg-alert" : "bg-signal"}`}
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                </div>
              );
            })}
        </div>
      </div>

      {/* Metadata */}
      {result.scrape_metadata && (
        <details className="mt-5">
          <summary className="cursor-pointer text-xs text-muted hover:text-white">Scrape metadata</summary>
          <pre className="mt-2 max-h-40 overflow-auto rounded-xl bg-ink p-3 text-xs text-muted">
            {JSON.stringify(result.scrape_metadata, null, 2)}
          </pre>
        </details>
      )}
    </div>
  );
}
