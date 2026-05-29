export type PipelineStage = {
  stage: number;
  name: string;
  status: "pending" | "running" | "done" | "failed";
  elapsed_s?: number;
  fields?: string[];
  error?: string;
};

export type PipelineEvent =
  | { event: "start"; total_portals: number; message: string }
  | { event: "stage"; stage: number; name: string; portal?: string; message: string }
  | { event: "stage_done"; stage: number; name: string; portal?: string; status?: string; elapsed_s?: number; fields?: string[]; conflicts?: number; portals_ok?: string[]; portals_failed?: string[]; roci_final?: number; district?: string; zone_type?: string }
  | { event: "stage_failed"; stage: number; name: string; portal?: string; error?: string; elapsed_s?: number }
  | { event: "done"; stage: number; result: PipelineResult }
  | { event: "error"; stage?: number; detail: string };

export type PipelineResult = {
  status: string;
  roci_final: number;
  zone_label: string;
  c_score?: number;                          // top-level only on SUPPRESSED
  components: Record<string, number>;        // c_score lives here on OK runs
  risk_flags?: string[];
  scrape_metadata?: Record<string, unknown>;
  inputs_echo?: Record<string, unknown>;
  rera_projects?: unknown[];
};

export type RunParams = {
  lat: number;
  lng: number;
  area_sqft: number;
  gatta_number?: string;
  zone_type?: string;
  fixture_only?: boolean;
};

export function buildStreamUrl(params: RunParams): string {
  // NEXT_PUBLIC_API_BASE_URL already includes /api (e.g. http://localhost:8000/api)
  const base = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api";
  const q = new URLSearchParams({
    lat: String(params.lat),
    lng: String(params.lng),
    area_sqft: String(params.area_sqft),
    zone_type: params.zone_type ?? "urban_expansion",
    headless: "true",
    fixture_only: String(params.fixture_only ?? false),
  });
  if (params.gatta_number) q.set("gatta_number", params.gatta_number);
  return `${base}/pipeline/stream?${q}`;
}

export const STAGE_NAMES = [
  "Zone Detection",
  "IGRSUP",
  "Bhunaksha",
  "Bhulekh",
  "CPPP / GeM",
  "UP RERA",
  "Normalise & Validate",
  "ROCI Score",
  "Complete",
];
