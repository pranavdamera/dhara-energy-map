# Data Model

All tables are in a PostgreSQL + PostGIS database. Geometries are stored in EPSG:4326 (WGS84). Distance and area calculations use EPSG:32644 (UTM Zone 44N, appropriate for southern India).

---

## Core Tables

### `districts`

Admin boundary polygons. Currently populated with a single record for Anantapur, Andhra Pradesh.

| Column | Type | Notes |
|---|---|---|
| `id` | `SERIAL PRIMARY KEY` | |
| `name` | `TEXT NOT NULL` | District name |
| `state` | `TEXT NOT NULL` | State name |
| `country` | `TEXT` | Default: `'India'` |
| `source` | `TEXT` | Data source attribution |
| `geom` | `geometry(MultiPolygon, 4326)` | District boundary |

Index: `GIST (geom)`

---

### `candidate_sites`

1 km × 1 km grid cells clipped to the district boundary. Only cells with area > 25 ha are retained. These are the units of analysis — everything else references them.

| Column | Type | Notes |
|---|---|---|
| `id` | `UUID PRIMARY KEY` | Generated with `gen_random_uuid()` |
| `grid_id` | `TEXT UNIQUE NOT NULL` | Human-readable row/col identifier |
| `district_id` | `INTEGER` | FK → `districts.id` |
| `area_ha` | `NUMERIC` | Cell area in hectares |
| `centroid` | `geometry(Point, 4326)` | Cell centroid |
| `geom` | `geometry(MultiPolygon, 4326)` | Cell polygon (clipped to boundary) |
| `created_at` | `TIMESTAMP` | |

Indexes: `GIST (geom)`, `GIST (centroid)`

---

### `roads`

OSM road network loaded via `04_load_osm.py`. Used to compute proximity scores.

| Column | Type | Notes |
|---|---|---|
| `id` | `SERIAL PRIMARY KEY` | |
| `osm_id` | `TEXT` | OpenStreetMap feature ID |
| `name` | `TEXT` | Road name (nullable) |
| `highway` | `TEXT` | OSM highway tag (primary, secondary, track, etc.) |
| `surface` | `TEXT` | Road surface type (nullable) |
| `source` | `TEXT` | Default: `'OpenStreetMap'` |
| `geom` | `geometry(LineString, 4326)` | Road centerline |

Indexes: `GIST (geom)`, `btree (highway)`

---

### `substations`

OSM electrical substations. Used for grid infrastructure proximity scoring.

| Column | Type | Notes |
|---|---|---|
| `id` | `SERIAL PRIMARY KEY` | |
| `osm_id` | `TEXT` | OpenStreetMap feature ID |
| `name` | `TEXT` | Substation name (nullable) |
| `voltage` | `TEXT` | Voltage level (nullable, sparse in rural India) |
| `operator` | `TEXT` | Utility operator (nullable) |
| `source` | `TEXT` | Default: `'OpenStreetMap'` |
| `geom` | `geometry(Point, 4326)` | Substation location |

Index: `GIST (geom)`

---

### `solar_resource`

Per-site solar irradiance derived from Global Solar Atlas GeoTIFFs via zonal statistics.

| Column | Type | Notes |
|---|---|---|
| `site_id` | `UUID PRIMARY KEY` | FK → `candidate_sites.id` (cascade delete) |
| `ghi_kwh_m2_day` | `NUMERIC` | Global Horizontal Irradiance, kWh/m²/day |
| `pvout_kwh_kwp_day` | `NUMERIC` | Photovoltaic output estimate |
| `source` | `TEXT` | Default: `'Global Solar Atlas'` |
| `confidence` | `NUMERIC` | Source confidence (0–1) |

---

### `crop_intensity`

Per-site vegetation index statistics from Sentinel-2 SR Harmonized (2024) via Google Earth Engine export.

| Column | Type | Notes |
|---|---|---|
| `site_id` | `UUID PRIMARY KEY` | FK → `candidate_sites.id` (cascade delete) |
| `ndvi_mean` | `NUMERIC` | Mean NDVI across site |
| `ndvi_p75` | `NUMERIC` | 75th percentile NDVI — used in scoring |
| `ndvi_seasonality` | `NUMERIC` | NDVI variability proxy |
| `crop_intensity_score` | `NUMERIC` | Derived crop intensity classification |
| `source` | `TEXT` | Default: `'Sentinel-2 SR Harmonized'` |
| `confidence` | `NUMERIC` | |

Higher `ndvi_p75` indicates active cropland — scored inversely (lower NDVI preferred for site suitability).

---

### `land_cover`

Per-site land cover class distribution from ESA WorldCover v200 (2021).

| Column | Type | Notes |
|---|---|---|
| `site_id` | `UUID PRIMARY KEY` | FK → `candidate_sites.id` (cascade delete) |
| `dominant_class` | `INTEGER` | WorldCover integer class code |
| `dominant_label` | `TEXT` | Class label |
| `built_pct` | `NUMERIC` | Fraction of cell classified as built-up |
| `cropland_pct` | `NUMERIC` | Fraction classified as cropland |
| `bare_sparse_pct` | `NUMERIC` | Fraction classified as bare/sparse — used in scoring |
| `tree_pct` | `NUMERIC` | Fraction classified as tree cover |
| `water_pct` | `NUMERIC` | Fraction classified as water |
| `source` | `TEXT` | Default: `'ESA WorldCover v200'` |
| `confidence` | `NUMERIC` | |

`bare_sparse_pct` is the primary scoring input — higher values indicate land with fewer competing uses.

> **Note:** WorldCover class distribution zonal stats are defined in the schema but not yet fully populated by the pipeline. See `06_raster_to_zone_stats.py` for the TODO.

---

### `slope`

Per-site terrain statistics from SRTMGL1_003 via Google Earth Engine.

| Column | Type | Notes |
|---|---|---|
| `site_id` | `UUID PRIMARY KEY` | FK → `candidate_sites.id` (cascade delete) |
| `elevation_mean_m` | `NUMERIC` | Mean elevation in meters |
| `slope_mean_deg` | `NUMERIC` | Mean slope in degrees — used in scoring |
| `slope_p90_deg` | `NUMERIC` | 90th percentile slope (tail risk indicator) |
| `source` | `TEXT` | Default: `'SRTMGL1_003'` |
| `confidence` | `NUMERIC` | |

Slope penalty: `slope_norm = 1 - min(slope_mean_deg / 10, 1)`. Sites above 10° are scored zero for this factor.

---

### `scores`

Final scoring output. One row per candidate site. Stores both normalized factor values and their weighted contributions.

| Column | Type | Notes |
|---|---|---|
| `site_id` | `UUID PRIMARY KEY` | FK → `candidate_sites.id` (cascade delete) |
| `solar_norm` | `NUMERIC` | Normalized solar score (0–1) |
| `solar_contribution` | `NUMERIC` | `solar_norm × 0.25` |
| `substation_norm` | `NUMERIC` | Normalized substation proximity score |
| `substation_contribution` | `NUMERIC` | `substation_norm × 0.20` |
| `road_norm` | `NUMERIC` | Normalized road proximity score |
| `road_contribution` | `NUMERIC` | `road_norm × 0.15` |
| `slope_norm` | `NUMERIC` | Normalized slope score |
| `slope_contribution` | `NUMERIC` | `slope_norm × 0.15` |
| `land_norm` | `NUMERIC` | Normalized land suitability score |
| `land_contribution` | `NUMERIC` | `land_norm × 0.15` |
| `crop_norm` | `NUMERIC` | Normalized crop intensity score (inverted) |
| `crop_contribution` | `NUMERIC` | `crop_norm × 0.10` |
| `total_score` | `NUMERIC` | Sum of all contributions (0–1) |
| `confidence_score` | `NUMERIC` | Data completeness penalty (0–1) |
| `score_version` | `TEXT` | Default: `'v1.0'` |
| `computed_at` | `TIMESTAMP` | When scoring was last run |

Index: `btree (total_score DESC)`

Scoring formula:
```
total_score = solar_norm*0.25 + substation_norm*0.20 + road_norm*0.15
            + slope_norm*0.15 + land_norm*0.15 + crop_norm*0.10

confidence_score = max(0, 0.8 - 0.1 * count_of_missing_factors)
```

---

### `risk_flags`

Qualitative risk annotations for sites. Reserved for future use.

| Column | Type | Notes |
|---|---|---|
| `id` | `SERIAL PRIMARY KEY` | |
| `site_id` | `UUID` | FK → `candidate_sites.id` (cascade delete) |
| `flag_type` | `TEXT NOT NULL` | Category (e.g. `'land_conflict'`, `'flood_zone'`) |
| `severity` | `TEXT` | `'low'`, `'medium'`, or `'high'` |
| `message` | `TEXT NOT NULL` | Human-readable flag description |
| `source` | `TEXT` | Flag source |
| `created_at` | `TIMESTAMP` | |

---

### `reports`

Report generation metadata. Reserved for future use.

| Column | Type | Notes |
|---|---|---|
| `id` | `UUID PRIMARY KEY` | |
| `site_id` | `UUID` | FK → `candidate_sites.id` (cascade delete) |
| `report_url` | `TEXT` | URL to generated report |
| `report_status` | `TEXT` | `'pending'`, `'ready'`, or `'failed'` |
| `created_at` | `TIMESTAMP` | |

---

## Planned Extension: `parcel_observation_snapshots`

This table is included in the schema to support future parcel-level monitoring via satellite or field-derived observations. It is not currently populated by the pipeline.

| Column | Type | Notes |
|---|---|---|
| `id` | `UUID PRIMARY KEY` | |
| `site_id` | `UUID` | FK → `candidate_sites.id` (cascade delete) |
| `observed_at` | `TIMESTAMP NOT NULL` | Observation date/time |
| `source` | `TEXT NOT NULL` | Data source (e.g. `'Sentinel-2'`, `'field_survey'`) |
| `observation_type` | `TEXT NOT NULL` | `'field_survey'`, `'satellite_derived'`, or `'raster_composite'` |
| `raster_asset_url` | `TEXT` | URL or path to source raster asset (nullable) |
| `ndvi_mean` | `NUMERIC` | Per-site NDVI at observation time (nullable) |
| `cloud_cover` | `NUMERIC` | Cloud cover fraction 0–1 (nullable) |
| `change_score` | `NUMERIC` | Change intensity relative to baseline (nullable) |
| `notes` | `TEXT` | Free text annotation |
| `footprint` | `geometry(Polygon, 4326)` | Observation footprint if different from site boundary (nullable) |
| `created_at` | `TIMESTAMP` | |

Intended ingestion path:
1. Pull satellite imagery for district bounding box
2. Extract per-parcel zonal statistics (NDVI, cloud cover)
3. Compute change score against a baseline observation
4. Insert a row per parcel per acquisition date
5. Expose via `GET /site/:id/observations`

This table enables multi-temporal monitoring and change overlay workflows without requiring image processing to happen inside this service.

---

## Spatial Index Strategy

All geometry columns have GIST indexes for efficient bounding-box and `ST_DWithin` queries. The scoring pipeline uses `ST_Distance` with a projected CRS (EPSG:32644) for accurate metric distance computation.

## CRS Notes

| Context | CRS | Reason |
|---|---|---|
| Storage | EPSG:4326 | Web interoperability, GeoJSON compatibility |
| Distance / area | EPSG:32644 | Metric accuracy for southern India |
