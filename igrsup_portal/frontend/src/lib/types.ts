export type Coordinates = {
  lat: number;
  lng: number;
};

export type Viewport = {
  center: [number, number];
  zoom: number;
};

export type ScoreRequest = {
  coordinates?: Coordinates;
  gatta_number?: string;
  village?: string;
  tehsil?: string;
  captcha_token?: string;
};

export type ParcelResult = {
  gatta_number: string;
  village?: string;
  tehsil?: string;
  district: string;
  geometry: {
    type: "Polygon" | "MultiPolygon";
    coordinates: number[][][];
  };
  source: string;
  source_confidence: number;
};

export type BhulekhResult = {
  gatta_number: string;
  mutation_status: string;
  bhoomi_prakar: string;
  owner_name?: string;
  village?: string;
  tehsil?: string;
  source_language: string;
  confidence: number;
};

export type ScoreComponent = {
  name: string;
  score: number;
  weight: number;
  reason: string;
};

export type InfraProject = {
  project_id: string;
  title: string;
  authority?: string;
  category: string;
  classification: string;
  source: string;
  distance_km: number;
  distance_band: string;
  status: string;
  influence_score: number;
};

export type InfrastructureSummary = {
  score: number;
  project_count: number;
  dominant_classification: string;
  methodology: string;
  projects: InfraProject[];
};

export type ScoreResponse = {
  status: string;
  roci_final: number;
  zone_label: string;
  parcel: ParcelResult;
  bhulekh: BhulekhResult;
  components: Record<string, ScoreComponent>;
  scrape_metadata: Record<string, unknown>;
};

export type AnalysisHistoryRecord = {
  gatta_number: string;
  village: string;
  tehsil: string;
  district: string;
  latitude?: string | number;
  longitude?: string | number;
  roci_final?: string | number;
  zone_label: string;
  infra_score?: string | number;
  risk_score?: string | number;
  confidence_score?: string | number;
  mutation_status: string;
  owner_name?: string;
  source_confidence?: string | number;
  timestamp?: string;
};
