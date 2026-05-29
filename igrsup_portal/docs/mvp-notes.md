# Ayodhya MVP Notes

## Current Implementation

- Ayodhya-only spatial boundary validation
- WFS-oriented Bhunaksha lookup client with fallback parcel generation
- Bhulekh parser workflow with CAPTCHA placeholder contract
- Modular ROCI scoring response for frontend consumption

## Next Sensible Extensions

- Replace fallback Bhunaksha geometry with live district-specific WFS filters
- Integrate approved CAPTCHA workflow for Bhulekh retrieval
- Add parcel caching with a spatial table and PostGIS geometry column
- Add registry velocity ingestion from local registrar datasets
