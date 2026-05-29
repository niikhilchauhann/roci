# API Reference

## `GET /api/health`

Returns backend status.

Response:

```json
{
  "status": "OK",
  "service": "roci-ayodhya-engine"
}
```

## `POST /api/score`

Runs parcel analysis.

Request:

```json
{
  "coordinates": {
    "lat": 26.7999,
    "lng": 82.2042
  },
  "gatta_number": "30",
  "village": "Demo Village",
  "tehsil": "Sadar",
  "captcha_token": "optional"
}
```

Response:

```json
{
  "status": "OK",
  "roci_final": 66.9,
  "zone_label": "Zone 4",
  "parcel": {},
  "bhulekh": {},
  "components": {},
  "scrape_metadata": {}
}
```

Error responses:

- `400` for invalid coordinates, missing identifiers, or out-of-bounds requests

## `GET /api/history`

Returns latest persisted analysis records.

Query params:

- `limit`: optional, defaults to `50`

Response:

```json
{
  "status": "OK",
  "records": [
    {
      "timestamp": "2026-05-22T12:30:00+05:30",
      "gatta_number": "30",
      "village": "Demo Village",
      "tehsil": "Sadar",
      "district": "Ayodhya",
      "latitude": "26.7999",
      "longitude": "82.2042",
      "roci_final": "66.9",
      "infra_score": "74.0",
      "risk_score": "62.0",
      "confidence_score": "58.5",
      "zone_label": "Zone 4",
      "mutation_status": "स्वीकृत",
      "owner_name": "घनश्याम",
      "source_confidence": "0.58"
    }
  ]
}
```

## `GET /api/history/export`

Downloads the persisted CSV file.

Response:

- `200` with `text/csv`

## `GET /api/history/{gatta_number}`

Returns the newest matching persisted history row for a gatta number.

Response:

```json
{
  "timestamp": "2026-05-22T12:30:00+05:30",
  "gatta_number": "30",
  "village": "Demo Village",
  "tehsil": "Sadar",
  "district": "Ayodhya",
  "latitude": "26.7999",
  "longitude": "82.2042",
  "roci_final": "66.9",
  "infra_score": "74.0",
  "risk_score": "62.0",
  "confidence_score": "58.5",
  "zone_label": "Zone 4",
  "mutation_status": "स्वीकृत",
  "owner_name": "घनश्याम",
  "source_confidence": "0.58"
}
```

Error responses:

- `400` if no saved record exists for the requested gatta number
