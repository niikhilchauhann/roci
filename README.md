# ROCI Scraper Release

This package runs the ROCI pipeline with live portal attempts, per-portal JSON outputs, and a pure scoring core.

## Install

```bash
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
playwright install
```

## Run

```bash
python -m roci_scraper.main --lat 26.7954 --lng 82.1942 --area-sqft 174240 --gatta-number 374/1-A --zone-type urban_expansion --output-dir out
```

## Notes

- Use `--fixture` only to merge manual test inputs.
- Live scraping writes one JSON file per portal under `<output-dir>/portal_outputs/`.
- If a portal is blocked by CAPTCHA or session protection, the scraper records a structured failure instead of hanging.
- Airflow and Celery files are included as optional orchestration scaffolding.
