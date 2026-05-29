"use client";

import { useEffect, useRef, useState } from "react";
import { CheckCircle, XCircle, Loader, AlertTriangle } from "lucide-react";
import type { PipelineEvent, PipelineResult, PipelineStage, RunParams } from "@/lib/pipeline";
import { buildStreamUrl, STAGE_NAMES } from "@/lib/pipeline";
import { ScoreCard } from "@/components/ScoreCard";

type Log = { ts: string; text: string; kind: "info" | "ok" | "err" };

function initStages(): PipelineStage[] {
  return STAGE_NAMES.map((name, i) => ({ stage: i, name, status: "pending" }));
}

export function PipelineRunner({ params, onReset }: { params: RunParams; onReset: () => void }) {
  const [stages, setStages] = useState<PipelineStage[]>(initStages);
  const [logs, setLogs] = useState<Log[]>([]);
  const [result, setResult] = useState<PipelineResult | null>(null);
  const [fatalError, setFatalError] = useState<string | null>(null);
  const [done, setDone] = useState(false);
  const logRef = useRef<HTMLDivElement>(null);
  const esRef = useRef<EventSource | null>(null);
  const doneRef = useRef(false);  // ref so onerror closure sees the current value

  const addLog = (text: string, kind: Log["kind"] = "info") => {
    const ts = new Date().toLocaleTimeString();
    setLogs((l) => [...l, { ts, text, kind }]);
  };

  const setStageStatus = (stage: number, status: PipelineStage["status"], patch?: Partial<PipelineStage>) =>
    setStages((prev) =>
      prev.map((s) => (s.stage === stage ? { ...s, status, ...patch } : s))
    );

  useEffect(() => {
    const url = buildStreamUrl(params);
    const es = new EventSource(url);
    esRef.current = es;

    es.onmessage = (e) => {
      let ev: PipelineEvent;
      try { ev = JSON.parse(e.data); } catch { return; }

      switch (ev.event) {
        case "start":
          addLog(`Pipeline started — ${ev.total_portals} portals`, "info");
          break;
        case "stage":
          setStageStatus(ev.stage, "running");
          addLog(`▶ ${ev.name}: ${ev.message}`, "info");
          break;
        case "stage_done": {
          const patch: Partial<PipelineStage> = {};
          if (ev.elapsed_s != null) patch.elapsed_s = ev.elapsed_s;
          if (ev.fields) patch.fields = ev.fields;
          setStageStatus(ev.stage, "done", patch);
          const extra = ev.elapsed_s != null ? ` (${ev.elapsed_s}s)` : "";
          const detail =
            ev.roci_final != null ? ` → score ${ev.roci_final}` :
            ev.conflicts != null ? ` conflicts=${ev.conflicts}` :
            ev.district ? ` district=${ev.district} zone=${ev.zone_type}` : "";
          addLog(`✓ ${ev.name}${extra}${detail}`, "ok");
          break;
        }
        case "stage_failed":
          setStageStatus(ev.stage, "failed", { error: ev.error, elapsed_s: ev.elapsed_s });
          addLog(`✗ ${ev.name}${ev.error ? `: ${ev.error}` : ""}`, "err");
          break;
        case "done":
          doneRef.current = true;
          setResult(ev.result);
          setStageStatus(8, "done");
          setDone(true);
          addLog(`Pipeline complete — ROCI ${ev.result.roci_final} — ${ev.result.zone_label ?? ""}`, "ok");
          es.close();
          break;
        case "error":
          setFatalError(ev.detail);
          addLog(`Fatal: ${ev.detail}`, "err");
          es.close();
          break;
      }
    };

    es.onerror = () => {
      // Use ref (not state) to avoid stale closure — state updates are async
      if (!doneRef.current) {
        setFatalError("Connection to backend lost. Is the server running?");
        addLog("SSE connection error — check that the backend is running on port 8000", "err");
      }
      es.close();
    };

    return () => es.close();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Auto-scroll log
  useEffect(() => {
    logRef.current?.scrollTo({ top: logRef.current.scrollHeight, behavior: "smooth" });
  }, [logs]);

  const completedCount = stages.filter((s) => s.status === "done").length;
  const pct = Math.round((completedCount / STAGE_NAMES.length) * 100);

  return (
    <div className="flex flex-col gap-6">
      {/* Overall progress bar */}
      <div className="rounded-[28px] border border-line bg-panel/60 p-6 shadow-panel">
        <div className="flex items-center justify-between">
          <p className="text-sm font-medium text-white">
            {done ? "Pipeline Complete" : fatalError ? "Pipeline Failed" : "Running Pipeline…"}
          </p>
          <span className="text-sm tabular-nums text-accent">{pct}%</span>
        </div>
        <div className="mt-3 h-2 rounded-full bg-line overflow-hidden">
          <div
            className={`h-full rounded-full transition-all duration-500 ${fatalError ? "bg-alert" : "bg-signal"}`}
            style={{ width: `${pct}%` }}
          />
        </div>

        {/* Stage pills */}
        <div className="mt-5 grid grid-cols-3 gap-2 sm:grid-cols-5">
          {stages.map((s) => (
            <StagePill key={s.stage} stage={s} />
          ))}
        </div>
      </div>

      {/* Fatal error */}
      {fatalError && (
        <div className="flex items-start gap-3 rounded-[20px] border border-alert/40 bg-alert/10 p-4">
          <AlertTriangle size={18} className="mt-0.5 shrink-0 text-alert" />
          <p className="text-sm text-alert">{fatalError}</p>
        </div>
      )}

      {/* Result card */}
      {result && <ScoreCard result={result} />}

      {/* Log */}
      <div className="rounded-[20px] border border-line bg-ink/60 p-4">
        <p className="mb-3 text-xs uppercase tracking-widest text-muted">Live Log</p>
        <div ref={logRef} className="max-h-60 overflow-y-auto font-mono text-xs space-y-1 pr-1">
          {logs.map((l, i) => (
            <div key={i} className={`flex gap-2 ${l.kind === "err" ? "text-alert" : l.kind === "ok" ? "text-signal" : "text-muted"}`}>
              <span className="shrink-0 text-line">{l.ts}</span>
              <span>{l.text}</span>
            </div>
          ))}
          {logs.length === 0 && <p className="text-line">Waiting for events…</p>}
        </div>
      </div>

      {done && (
        <button
          onClick={onReset}
          className="self-start rounded-full border border-line px-5 py-2 text-sm text-muted hover:text-white"
        >
          ← New Analysis
        </button>
      )}
    </div>
  );
}

function StagePill({ stage }: { stage: PipelineStage }) {
  const icon =
    stage.status === "done" ? <CheckCircle size={12} className="text-signal" /> :
    stage.status === "failed" ? <XCircle size={12} className="text-alert" /> :
    stage.status === "running" ? <Loader size={12} className="animate-spin text-accent" /> :
    <span className="h-3 w-3 rounded-full border border-line" />;

  const bg =
    stage.status === "done" ? "border-signal/30 bg-signal/10" :
    stage.status === "failed" ? "border-alert/30 bg-alert/10" :
    stage.status === "running" ? "border-accent/30 bg-accent/10" :
    "border-line bg-ink";

  return (
    <div className={`flex items-center gap-1.5 rounded-xl border px-2 py-1.5 ${bg}`}>
      {icon}
      <span className={`truncate text-[10px] leading-tight ${stage.status === "pending" ? "text-muted" : "text-white"}`}>
        {stage.name}
      </span>
      {stage.elapsed_s != null && (
        <span className="ml-auto shrink-0 text-[9px] text-muted">{stage.elapsed_s}s</span>
      )}
    </div>
  );
}
