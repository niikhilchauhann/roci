# Architecture

## Flow

Frontend
↓
FastAPI
↓
Bhunaksha
↓
Bhulekh
↓
Infrastructure APIs
↓
Scoring Engine
↓
CSV Persistence
↓
Frontend Dashboard

## Components

### Frontend

- Next.js App Router
- Zustand store for active parcel state and session persistence
- Leaflet map for coordinate selection, marker rendering, polygon rendering, and history reload UX

### FastAPI

- `/api/score` orchestrates parcel lookup, enrichment, scoring, and CSV persistence
- `/api/history` reads persisted CSV analysis rows
- `/api/history/export` exposes the raw CSV download
- `/api/history/{gatta_number}` returns the newest saved record for a parcel

### Bhunaksha

- WFS-style lookup for geometry-oriented parcel matching
- CSV plot-info demo flow for bulk and raw record extraction

### Bhulekh

- Hindi parser flow with CAPTCHA placeholder architecture
- CSV enrichment path for owner name reuse from parsed Bhunaksha records

### Infrastructure APIs

- CPPP and GeM scrapers classify nearby projects and produce distance-aware influence signals

### Scoring Engine

- ROCI component scoring remains modular
- land, risk, confidence, and infrastructure signals are combined into the final score

### CSV Persistence

- `backend/data/analysis_history.csv` stores analysis history
- `backend/data/land_data.csv` stores raw plot responses
- `backend/data/parsed_land_data.csv` stores parsed owner/area rows
- `backend/data/failed_plots.csv` stores failed plot attempts
