# ROCI Ayodhya — Deployment Guide

## Requirements
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (free, Mac/Windows/Linux)
- 4 GB free disk space (Playwright Chromium is ~300 MB)

## First-time setup

```bash
# 1. Clone / unzip the project
cd roci

# 2. Build and start everything (takes ~5 min on first run)
docker-compose up --build
```

## Daily use

```bash
# Start
docker-compose up

# Stop
docker-compose down
```

Open **http://localhost:3000** in your browser.

## What runs where

| Service  | URL                          | Purpose                        |
|----------|------------------------------|--------------------------------|
| Frontend | http://localhost:3000        | Web UI (Run Pipeline, Portals) |
| Backend  | http://localhost:8000/api    | FastAPI + ROCI engine          |
| API docs | http://localhost:8000/docs   | Auto-generated Swagger UI      |

## Running the pipeline

1. Go to **Run Pipeline** in the nav bar
2. Enter lat/lng coordinates (default is Ayodhya city centre)
3. Enter area in sq ft and an optional gatta number
4. Select zone type
5. Click **Run Pipeline**

Tick **Fixture-only mode** to skip live scraping and get an instant result using cached data.

## Updating the IGRSUP cache

The IGRSUP circle rates and transaction counts are pre-cached. To refresh:

```bash
docker-compose exec backend python -m scripts.cache_igrsup_sros
```

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Port 3000 already in use | Change `"3000:3000"` to `"3001:3000"` in docker-compose.yml |
| Port 8000 already in use | Change `"8000:8000"` to `"8001:8000"` and update `NEXT_PUBLIC_API_BASE_URL` |
| Playwright browser missing | `docker-compose build --no-cache backend` |
