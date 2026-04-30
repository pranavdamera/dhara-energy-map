# API Examples

Base URL: `http://localhost:8000`

All responses are JSON. Geometries are returned as GeoJSON objects embedded in the response body.

---

## Health Check

```http
GET /health
```

**Response (200):**
```json
{
  "status": "ok",
  "db": "ok"
}
```

**Response when DB is unreachable (200):**
```json
{
  "status": "ok",
  "db": "error"
}
```

---

## List Ranked Sites

```http
GET /sites/ranked?limit=5&min_score=0.6
```

Query parameters:
- `limit` — integer, 1–500, default `50`
- `min_score` — float 0.0–1.0, default `0.0`

**Response (200):**
```json
{
  "count": 3,
  "items": [
    {
      "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "grid_id": "r042_c017",
      "total_score": 0.763,
      "confidence_score": 0.8,
      "centroid_geojson": {
        "type": "Point",
        "coordinates": [77.5842, 14.8231]
      }
    },
    {
      "id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
      "grid_id": "r038_c021",
      "total_score": 0.741,
      "confidence_score": 0.7,
      "centroid_geojson": {
        "type": "Point",
        "coordinates": [77.6103, 14.7894]
      }
    },
    {
      "id": "c3d4e5f6-a7b8-9012-cdef-123456789012",
      "grid_id": "r051_c009",
      "total_score": 0.618,
      "confidence_score": 0.8,
      "centroid_geojson": {
        "type": "Point",
        "coordinates": [77.4921, 14.9102]
      }
    }
  ]
}
```

---

## Site Dossier with Score Breakdown

```http
GET /site/a1b2c3d4-e5f6-7890-abcd-ef1234567890
```

**Response (200):**
```json
{
  "item": {
    "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "grid_id": "r042_c017",
    "area_ha": 98.4,
    "geom_geojson": {
      "type": "MultiPolygon",
      "coordinates": [[[
        [77.579, 14.818],
        [77.589, 14.818],
        [77.589, 14.828],
        [77.579, 14.828],
        [77.579, 14.818]
      ]]]
    },
    "centroid_geojson": {
      "type": "Point",
      "coordinates": [77.5842, 14.8231]
    },
    "total_score": 0.763,
    "confidence_score": 0.8,
    "score_breakdown": {
      "solar_norm": 0.84,
      "solar_contribution": 0.21,
      "substation_norm": 0.72,
      "substation_contribution": 0.144,
      "road_norm": 0.91,
      "road_contribution": 0.1365,
      "slope_norm": 0.95,
      "slope_contribution": 0.1425,
      "land_norm": 0.61,
      "land_contribution": 0.0915,
      "crop_norm": 0.58,
      "crop_contribution": 0.058,
      "score_version": "v1.0"
    }
  }
}
```

**When site_id is not found (200):**
```json
{
  "item": null
}
```

---

## Scoring Methodology

```http
GET /methodology
```

**Response (200):**
```json
{
  "scope": "Week 1 single-district demo for Anantapur only",
  "model": "Explainable weighted additive scoring",
  "weights": {
    "solar": 0.25,
    "substation": 0.20,
    "road": 0.15,
    "slope": 0.15,
    "land": 0.15,
    "crop": 0.10
  },
  "crs": {
    "storage": "EPSG:4326",
    "metric": "EPSG:32644"
  }
}
```

---

## Site Observation Snapshots

```http
GET /site/a1b2c3d4-e5f6-7890-abcd-ef1234567890/observations
```

Returns timestamped parcel observation records from field surveys or satellite-derived raster extracts.

**Response (200) — with demo data loaded:**
```json
{
  "site_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "count": 2,
  "items": [
    {
      "id": "d4e5f6a7-b8c9-0123-defa-234567890123",
      "site_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "observed_at": "2024-11-15T10:30:00",
      "source": "Sentinel-2",
      "observation_type": "satellite_derived",
      "raster_asset_url": null,
      "ndvi_mean": 0.31,
      "cloud_cover": 0.04,
      "change_score": null,
      "notes": "Post-monsoon dry-down period"
    },
    {
      "id": "e5f6a7b8-c9d0-1234-efab-345678901234",
      "site_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "observed_at": "2024-03-20T08:00:00",
      "source": "field_survey",
      "observation_type": "field_survey",
      "raster_asset_url": null,
      "ndvi_mean": null,
      "cloud_cover": null,
      "change_score": null,
      "notes": "Accessible via state highway. Flat terrain confirmed. No active cultivation observed."
    }
  ]
}
```

**Response (200) — no observations for site:**
```json
{
  "site_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "count": 0,
  "items": []
}
```

---

## Notes

- All UUIDs are in standard hyphenated format.
- `geom_geojson` and `centroid_geojson` are GeoJSON objects (not strings) for direct use in mapping clients.
- `score_breakdown` fields can be `null` if scoring has not been run for a site (e.g. demo sites inserted manually without all raster inputs).
- The `/site/:id/observations` endpoint returns records from `parcel_observation_snapshots`. This table is pre-populated by `seed_demo.py` for demo purposes. In production use it would be populated by a raster ingestion pipeline.
