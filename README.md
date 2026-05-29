# ROCI Ayodhya Engine

Full-stack land intelligence pipeline for Uttar Pradesh. Scrapes 5 government portals, computes a ROCI score, and serves results via a Next.js web UI.

---

## Quick Start (Docker — recommended)

**Requirements:** Docker Desktop, 4 GB free disk space.

```bash
docker-compose up --build
```

Open **http://localhost:3000** in your browser.

First build takes ~5–10 minutes (downloads Playwright Chromium and Python deps).

| Service  | URL                        |
|----------|----------------------------|
| Frontend | http://localhost:3000      |
| Backend  | http://localhost:8000/api  |
| API docs | http://localhost:8000/docs |

---

## Local Development (without Docker)

### Requirements

- Python 3.12+
- Node.js 20+

### Backend

```bash
# From repo root
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pip install -e .

# Install Playwright and download Chromium browser (required for CPPP, RERA, Bhulekh scrapers)
playwright install chromium --with-deps

cd igrsup_portal/backend
cp .env.example .env             # edit if needed
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd igrsup_portal/frontend
npm install
npm run dev
```

Open **http://localhost:3000**.

### Environment Variables (backend)

All variables have defaults except the three marked required:

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_ENV` | `development` | Environment name |
| `LOG_LEVEL` | `INFO` | Logging level |
| `ALLOWED_ORIGINS` | `["http://localhost:3000"]` | CORS origins (JSON array) |
| `BHUNAKSHA_WFS_URL` | "https://upbhunaksha.gov.in/bhunakshaserver" | Bhunaksha WFS endpoint |
| `BHUNAKSHA_LAYER_NAME` | "up:land_parcels" | Bhunaksha layer name |
| `BHULEKH_BASE_URL` | "https://upbhulekh.gov.in" | Bhulekh base URL |
| `ROCI_OUT_DIR` | `./data` | Directory for pipeline outputs |

---

## Running the Pipeline (CLI)

```bash
python -m roci_scraper.main \
  --lat 26.7954 \
  --lng 82.1942 \
  --area-sqft 174240 \
  --gatta-number 374/1-A \
  --zone-type urban_expansion \
  --output-dir out
```

Use `--fixture-only` to skip live scraping and use cached portal outputs from `out/portal_outputs/`.

---

## Running Tests

```bash
pytest tests/ -v
```

All 10 tests should pass.

---

## CAPTCHA Notes

Two portals use image CAPTCHAs that the scraper attempts to solve automatically using an OCR-based solver:

| Portal | CAPTCHA type | Behaviour on failure |
|--------|-------------|----------------------|
| CPPP/GeM | Image CAPTCHA on search form | Retries 10 times; returns 0 projects on all failures. Pipeline continues — infra score contribution is 0. |
| UP RERA | Image CAPTCHA on search form | Retries 10 times; returns 0 projects on all failures. Pipeline continues — RERA density contribution is 0. |

**IGRSUP, Bhunaksha, Bhulekh** do not use CAPTCHAs.

If CPPP/RERA consistently fail in production, consider:
- Using the `--fixture-only` flag with pre-cached outputs
- Integrating a paid CAPTCHA service (2Captcha / AntiCaptcha) via the `CAPTCHA_API_KEY` env variable

---

## Portal Outputs

Live scraping writes one JSON file per portal under `out/portal_outputs/`:

```
out/
  portal_outputs/
    igrsup.json
    bhunaksha.json
    bhulekh.json
    cppp_gem.json
    rera_up.json
  igrsup_sro_cache.json   ← pre-cached circle rates, refresh with scripts/cache_igrsup_sros.py
```

---

## Updating the IGRSUP Cache

Circle rates and transaction counts are pre-cached. To refresh:

```bash
# Local
python scripts/cache_igrsup_sros.py

# Docker
docker-compose exec backend python scripts/cache_igrsup_sros.py
```
