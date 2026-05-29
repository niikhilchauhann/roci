# ROCI Ayodhya Engine

ROCI Ayodhya Engine is an Ayodhya-focused land intelligence MVP. The project already includes a FastAPI backend, a Next.js frontend dashboard, scraper modules, services, scoring, and CSV-based demo artifacts. This repository now keeps that architecture intact and completes the missing Bhunaksha Ayodhya demo scraper flow without adding new infrastructure layers.

## What This Demo Covers

- FastAPI backend with existing API routes
- Next.js frontend dashboard that remains unchanged
- Bhunaksha coordinate lookup flow for the UI
- Bhunaksha CSV demo scraper flow for Ayodhya
- Bhulekh parser placeholder flow
- ROCI scoring and infrastructure enrichment already present in the backend

## Project Structure

```text
roci-ayodhya/
├── backend/
│   ├── app/
│   │   ├── api/                  # FastAPI routes
│   │   ├── models/               # Pydantic models
│   │   ├── scrapers/             # Bhunaksha, Bhulekh, CPPP, GeM scrapers
│   │   ├── services/             # Land orchestration and Bhunaksha demo flow
│   │   ├── utils/                # Config, logging, GIS and text helpers
│   │   └── ref_data/             # Ayodhya village to GIS-code mapping
│   ├── tests/                    # Existing scripts and tests
│   └── requirements.txt
├── frontend/                     # Existing Next.js dashboard
├── land_data.csv                 # Raw Bhunaksha plot responses
├── parsed_land_data.csv          # Parsed plot fields
├── failed_plots.csv              # Failed plot requests
└── README.md
```

## Bhunaksha Demo Scraper Flow

The completed demo flow is now:

`District -> Tehsil -> Village -> GIS Code -> Plot Loop -> Plot Info -> Parse -> CSV Export`

This flow is implemented through:

- [`backend/app/scrapers/bhunaksha.py`](./backend/app/scrapers/bhunaksha.py)
- [`backend/app/services/bhunaksha_demo_service.py`](./backend/app/services/bhunaksha_demo_service.py)
- [`backend/app/main.py`](./backend/app/main.py)

### Implemented Bhunaksha Demo Functions

- `get_villages()`
- `generate_gis_code()`
- `get_plot_info()`
- `get_plot_by_number()`
- `parse_plot_info()`

The parser extracts:

- plot number
- khata number
- owner name
- area

## CSV Outputs

The Bhunaksha demo writes CSV files at the project root:

- `land_data.csv`
  Raw successful plot responses with `plot_number`, `status_code`, and `response_text`
- `parsed_land_data.csv`
  Parsed plot data with `plot_number`, `khata_number`, `owner_name`, and `area`
- `failed_plots.csv`
  Failed or skipped plot rows with `plot_number`, `error`, and `attempts`

## Retry, Timeout, and Logging

The Bhunaksha demo flow now includes:

- up to 3 retries per failed plot request
- explicit timeout handling
- request exception handling
- log lines for successful plots
- log lines for failed plots
- log lines for retry attempts

## How to Run the Backend API

```bash
cd roci-ayodhya/backend
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

API routes already present:

- `GET /api/health`
- `POST /api/bhunaksha`
- `POST /api/bhulekh`
- `POST /api/score`

## How to Run the Bhunaksha Demo Scraper

From the `backend/` directory:

```bash
python -m app.main --demo --district Ayodhya --tehsil Sadar --village "Demo Village" --plot-start 1 --plot-end 10
```

This runs the CSV-based Ayodhya demo scraper and exports:

- `land_data.csv`
- `parsed_land_data.csv`
- `failed_plots.csv`

## How the Frontend Fits

The frontend already exists and was intentionally left in place.

Run it with:

```bash
cd roci-ayodhya/frontend
npm install
cp .env.example .env.local
npm run dev
```

The current frontend continues to use backend API responses. It was not redesigned during this audit.

## Current Limitations

- The Bhunaksha demo village-to-GIS-code mapping is intentionally small and CSV-backed for MVP stability.
- The CSV demo flow is synchronous and intended for demo or operator use, not large-scale crawling.
- The WFS-style Bhunaksha API flow and the CSV plot-info flow serve different use cases and are both preserved.
- Bhulekh remains a placeholder-assisted parser flow because the real portal requires CAPTCHA handling.
- No PostgreSQL, Redis, Celery, Docker, or Kubernetes layers were added.

## Audit Summary

### Already Complete

- FastAPI backend structure
- frontend dashboard
- API routes
- service/scoring/utils/logging structure
- WFS-style Bhunaksha lookup used by the app
- Bhulekh placeholder parser flow
- CSV artifacts from earlier Bhunaksha scripts

### Fixed

- Unified the Bhunaksha CSV demo logic into the existing app-layer scraper and service architecture
- Added retry, timeout, and request exception handling for plot requests
- Added missing parser extraction for plot number, khata number, owner name, and area
- Added failed plot export handling through `failed_plots.csv`
- Refactored the old raw scripts in `backend/tests/` to use the shared app logic
- Turned `backend/app/main.py` into a clean runnable scraper demo entry point while keeping the FastAPI app intact

### Newly Added

- `backend/app/services/bhunaksha_demo_service.py`
- `backend/app/ref_data/ayodhya_villages.csv`
- Bhunaksha demo helper methods in `backend/app/scrapers/bhunaksha.py`
- extra Bhunaksha config values for retries and plot-info endpoint

### Future Work

- Replace the demo village catalog with a fuller Ayodhya reference dataset
- Add stronger owner parsing for multi-owner responses
- Add dedicated tests for the Bhunaksha demo service and parser edge cases
- Optionally expose CSV summaries through an API route if the frontend needs them later
