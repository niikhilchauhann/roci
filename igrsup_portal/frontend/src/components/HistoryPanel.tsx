"use client";

import { useEffect, useMemo, useState } from "react";
import { Download, History, Search } from "lucide-react";
import { useRouter } from "next/navigation";

import { downloadAnalysisHistoryCsv, getAnalysisHistory } from "@/lib/api";
import type { AnalysisHistoryRecord } from "@/lib/types";
import { useLandStore } from "@/store/useLandStore";


export function HistoryPanel({ compact = false }: { compact?: boolean }) {
  const [records, setRecords] = useState<AnalysisHistoryRecord[]>([]);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();
  const loadHistoryResult = useLandStore((state) => state.loadHistoryResult);

  useEffect(() => {
    let active = true;

    async function load() {
      setLoading(true);
      setError(null);
      try {
        const response = await getAnalysisHistory(compact ? 8 : 50);
        if (active) {
          setRecords(Array.isArray(response) ? response : (response as { records: AnalysisHistoryRecord[] }).records ?? []);
        }
      } catch (err) {
        if (active) {
          setError(err instanceof Error ? err.message : "Failed to load history");
        }
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    }

    void load();
    return () => {
      active = false;
    };
  }, [compact]);

  const filtered = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    if (!normalized) {
      return records;
    }

    return records.filter((record) => {
      return (
        record.gatta_number.toLowerCase().includes(normalized) ||
        record.village.toLowerCase().includes(normalized) ||
        record.tehsil.toLowerCase().includes(normalized)
      );
    });
  }, [records, query]);

  async function handleReload(record: AnalysisHistoryRecord) {
    await loadHistoryResult(record);
    router.push("/results");
  }

  async function handleExport() {
    try {
      await downloadAnalysisHistoryCsv();
    } catch (err) {
      setError(err instanceof Error ? err.message : "CSV unavailable");
    }
  }

  return (
    <section className="rounded-[28px] border border-line bg-panel/80 p-5 shadow-panel">
      <div className="mb-5 flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs uppercase tracking-[0.3em] text-accent">History</p>
          <h2 className="text-lg font-semibold">Previous analyses</h2>
        </div>
        <button
          onClick={() => void handleExport()}
          className="flex items-center gap-2 rounded-full border border-line bg-ink/50 px-4 py-2 text-sm text-muted transition hover:text-white"
        >
          <Download size={16} />
          Export Analysis CSV
        </button>
      </div>

      <div className="mb-4 flex items-center gap-3 rounded-2xl border border-line bg-ink/50 px-4 py-3">
        <Search size={16} className="text-accent" />
        <input
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Search by gatta or village"
          className="w-full bg-transparent text-sm outline-none placeholder:text-muted"
        />
      </div>

      {loading ? <div className="rounded-2xl border border-line bg-ink/45 p-4 text-sm text-muted">Loading history...</div> : null}
      {!loading && error ? <div className="rounded-2xl border border-alert/30 bg-alert/10 p-4 text-sm text-alert">{error}</div> : null}
      {!loading && !error && filtered.length === 0 ? (
        <div className="rounded-2xl border border-line bg-ink/45 p-4 text-sm text-muted">
          {records.length === 0 ? "No history yet. Run an analysis to persist the first parcel." : "No history rows matched your search."}
        </div>
      ) : null}

      {!loading && !error && filtered.length > 0 ? (
        <div className="overflow-hidden rounded-2xl border border-line bg-ink/35">
          <div className="grid grid-cols-[1fr_1fr_1fr_110px_170px] gap-3 border-b border-line px-4 py-3 text-xs uppercase tracking-[0.2em] text-muted">
            <span>Gatta</span>
            <span>Village</span>
            <span>Tehsil</span>
            <span>ROCI</span>
            <span>Timestamp</span>
          </div>
          <div className="max-h-[420px] overflow-auto">
            {filtered.map((record) => (
              <button
                key={`${record.gatta_number}-${record.timestamp}`}
                onClick={() => void handleReload(record)}
                className="grid w-full grid-cols-[1fr_1fr_1fr_110px_170px] gap-3 border-b border-line/70 px-4 py-3 text-left text-sm transition hover:bg-ink/55"
              >
                <span className="font-medium text-white">{record.gatta_number}</span>
                <span className="truncate text-muted">{record.village || "Unknown"}</span>
                <span className="truncate text-muted">{record.tehsil || "Unknown"}</span>
                <span className="text-accent">{record.roci_final}</span>
                <span className="truncate text-muted">{record.timestamp}</span>
              </button>
            ))}
          </div>
        </div>
      ) : null}

      {compact ? (
        <div className="mt-4 flex items-center gap-2 text-sm text-muted">
          <History size={16} />
          Click a saved row to reload that parcel into the results view.
        </div>
      ) : null}
    </section>
  );
}
