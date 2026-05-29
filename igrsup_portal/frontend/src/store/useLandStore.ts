import { create } from "zustand";
import { persist } from "zustand/middleware";

import { getAnalysisHistoryRecord, scoreParcel } from "@/lib/api";
import { AnalysisHistoryRecord, Coordinates, ScoreResponse, Viewport } from "@/lib/types";

const ayodhyaViewport: Viewport = {
  center: [26.7999, 82.2042],
  zoom: 12,
};

function coordinatesEqual(left: Coordinates | null, right: Coordinates | null): boolean {
  if (left === right) return true;
  if (!left || !right) return false;
  return left.lat === right.lat && left.lng === right.lng;
}

function viewportEqual(left: Viewport, right: Viewport): boolean {
  return (
    left.zoom === right.zoom &&
    left.center[0] === right.center[0] &&
    left.center[1] === right.center[1]
  );
}

type LandStore = {
  coordinates: Coordinates | null;
  viewport: Viewport;
  gattaNumber: string;
  village: string;
  tehsil: string;
  captchaToken: string;
  result: ScoreResponse | null;
  sessionResults: ScoreResponse[];
  loading: boolean;
  error: string | null;
  setCoordinates: (coordinates: Coordinates) => void;
  resetCoordinates: () => void;
  setViewport: (viewport: Viewport) => void;
  resetViewport: () => void;
  setField: (field: "gattaNumber" | "village" | "tehsil" | "captchaToken", value: string) => void;
  runScore: () => Promise<void>;
  loadHistoryResult: (record: AnalysisHistoryRecord) => Promise<void>;
  clearResult: () => void;
};

function appendSessionResult(sessionResults: ScoreResponse[], result: ScoreResponse): ScoreResponse[] {
  const filtered = sessionResults.filter((item) => item.parcel.gatta_number !== result.parcel.gatta_number);
  return [result, ...filtered].slice(0, 50);
}

function hydrateHistoryRecord(record: AnalysisHistoryRecord): ScoreResponse {
  const rociFinal = Number(record.roci_final || 0);
  const infraScore = Number(record.infra_score || 0);
  const riskScore = Number(record.risk_score || 0);
  const confidenceScore = Number(record.confidence_score || 0);
  const latitude = Number(record.latitude || 0);
  const longitude = Number(record.longitude || 0);

  return {
    status: "OK",
    roci_final: rociFinal,
    zone_label: record.zone_label,
    parcel: {
      gatta_number: record.gatta_number,
      village: record.village,
      tehsil: record.tehsil,
      district: record.district,
      geometry: {
        type: "Polygon",
        coordinates: [[]],
      },
      source: "history_reload",
      source_confidence: Number(record.source_confidence || 0),
    },
    bhulekh: {
      gatta_number: record.gatta_number,
      mutation_status: record.mutation_status,
      bhoomi_prakar: "Historical record",
      owner_name: record.owner_name,
      village: record.village,
      tehsil: record.tehsil,
      source_language: "hi",
      confidence: Number(record.confidence_score || 0) / 100,
    },
    components: {
      infra_score: { name: "Infrastructure Access", score: infraScore, weight: 0.2, reason: "Loaded from persisted history." },
      risk_score: { name: "Risk Score", score: riskScore, weight: 0.2, reason: "Loaded from persisted history." },
      confidence_score: { name: "Confidence Score", score: confidenceScore, weight: 0.1, reason: "Loaded from persisted history." },
    },
    scrape_metadata: {
      bhunaksha: { source: "history_reload" },
      bhulekh: { source: "history_reload" },
      infrastructure: { source: "history_reload" },
    },
  };
}

export const useLandStore = create<LandStore>()(
  persist(
    (set, get) => ({
      coordinates: null,
      viewport: ayodhyaViewport,
      gattaNumber: "",
      village: "",
      tehsil: "",
      captchaToken: "",
      result: null,
      sessionResults: [],
      loading: false,
      error: null,
      setCoordinates: (coordinates) =>
        set((state) => {
          if (coordinatesEqual(state.coordinates, coordinates) && state.error === null) {
            return state;
          }
          return { ...state, coordinates, error: null };
        }),
      resetCoordinates: () =>
        set((state) => {
          if (state.coordinates === null && state.error === null) {
            return state;
          }
          return { ...state, coordinates: null, error: null };
        }),
      setViewport: (viewport) =>
        set((state) => {
          if (viewportEqual(state.viewport, viewport)) {
            return state;
          }
          return { ...state, viewport };
        }),
      resetViewport: () =>
        set((state) => {
          if (viewportEqual(state.viewport, ayodhyaViewport)) {
            return state;
          }
          return { ...state, viewport: ayodhyaViewport };
        }),
      setField: (field, value) => set({ [field]: value } as Pick<LandStore, typeof field>),
      clearResult: () => set({ result: null, error: null }),
      runScore: async () => {
        const { coordinates, gattaNumber, village, tehsil, captchaToken, sessionResults } = get();
        set({ loading: true, error: null });
        try {
          const result = await scoreParcel({
            coordinates: coordinates ?? undefined,
            gatta_number: gattaNumber || undefined,
            village: village || undefined,
            tehsil: tehsil || undefined,
            captcha_token: captchaToken || undefined,
          });
          set({
            result,
            sessionResults: appendSessionResult(sessionResults, result),
            loading: false,
          });
        } catch (error) {
          const message = error instanceof Error ? error.message : "Unexpected API failure";
          set({ error: message, loading: false });
        }
      },
      loadHistoryResult: async (record) => {
        const { sessionResults } = get();
        const cached = sessionResults.find((item) => item.parcel.gatta_number === record.gatta_number);

        if (cached) {
          set({
            result: cached,
            gattaNumber: cached.parcel.gatta_number,
            village: cached.parcel.village ?? "",
            tehsil: cached.parcel.tehsil ?? "",
            coordinates:
              record.latitude && record.longitude
                ? { lat: Number(record.latitude), lng: Number(record.longitude) }
                : null,
          });
          return;
        }

        try {
          const latest = await getAnalysisHistoryRecord(record.gatta_number);
          const hydrated = hydrateHistoryRecord(latest);
          set({
            result: hydrated,
            sessionResults: appendSessionResult(sessionResults, hydrated),
            gattaNumber: hydrated.parcel.gatta_number,
            village: hydrated.parcel.village ?? "",
            tehsil: hydrated.parcel.tehsil ?? "",
            coordinates:
              latest.latitude && latest.longitude
                ? { lat: Number(latest.latitude), lng: Number(latest.longitude) }
                : null,
            error: null,
          });
        } catch (error) {
          const message = error instanceof Error ? error.message : "Failed to load history result";
          set({ error: message });
        }
      },
    }),
    {
      name: "roci-ayodhya-session",
      partialize: (state) => ({
        coordinates: state.coordinates,
        viewport: state.viewport,
        gattaNumber: state.gattaNumber,
        village: state.village,
        tehsil: state.tehsil,
        captchaToken: state.captchaToken,
        result: state.result,
        sessionResults: state.sessionResults,
      }),
    }
  )
);
