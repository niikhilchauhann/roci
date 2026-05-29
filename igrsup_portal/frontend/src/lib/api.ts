import type { AnalysisHistoryRecord, ScoreRequest, ScoreResponse } from "./types";

const BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api";

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    const detail = await res.text().catch(() => res.statusText);
    throw new Error(`API error ${res.status}: ${detail}`);
  }
  return res.json() as Promise<T>;
}

export async function scoreParcel(payload: ScoreRequest): Promise<ScoreResponse> {
  return apiFetch<ScoreResponse>("/score", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getAnalysisHistory(limit = 50): Promise<AnalysisHistoryRecord[]> {
  const data = await apiFetch<{ status: string; records: AnalysisHistoryRecord[] }>(
    `/history?limit=${limit}`
  );
  return data.records;
}

export async function getAnalysisHistoryRecord(gattaNumber: string): Promise<AnalysisHistoryRecord> {
  return apiFetch<AnalysisHistoryRecord>(`/history/${encodeURIComponent(gattaNumber)}`);
}

export async function downloadAnalysisHistoryCsv(): Promise<void> {
  const res = await fetch(`${BASE_URL}/history/export`);
  if (!res.ok) throw new Error(`Export failed: ${res.statusText}`);
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "analysis_history.csv";
  a.click();
  URL.revokeObjectURL(url);
}
