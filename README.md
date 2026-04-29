# Dhara Energy Map (Week 1 Scaffold)

Dhara Energy Map is a research/portfolio geospatial intelligence demo that ranks candidate zones for PM-KUSUM feeder solarization in **Anantapur district, Andhra Pradesh, India**.

## What This Is

- A Week 1 backend + data foundation scaffold.
- A single-district geospatial scoring pipeline.
- An explainable weighted-additive model with auditable factor contributions.

## What This Is Not

- Not a farmer-facing app.
- Not deep learning.
- Not multi-district expansion.
- Not financial modeling.
- Not production deployment.

## Scope Lock

Only these six public layers are used:

1. District/admin boundary
2. Sentinel-2 NDVI via Google Earth Engine
3. ESA WorldCover via Google Earth Engine
4. SRTM slope/elevation via Google Earth Engine
5. OpenStreetMap roads + substations
6. Global Solar Atlas irradiance

## Architecture (Week 1)

- Python 3.11 scripts for ingestion and scoring.
- FastAPI for health and ranked-site API.
- PostgreSQL/PostGIS schema for spatial storage (when you are ready to run DB).
- `EPSG:4326` for storage, `EPSG:32644` for metric calculations.

## Docker Status

Docker is **optional until DB execution time**.  
You can scaffold files, install dependencies, and prepare manual datasets without Docker running.

## Manual Steps You Must Do

A. Install Python 3.11  
B. Create and activate virtual environment  
C. Install requirements  
D. Start Docker only when ready  
E. Download Anantapur boundary if script does not download it  
F. Authenticate Google Earth Engine  
G. Start Earth Engine exports  
H. Wait for exports in Google Drive  
I. Manually download exported rasters into `data/raw/gee_exports/`  
J. Manually download Global Solar Atlas India GHI raster into `data/raw/solar/`  
K. Clip/rename it to `data/processed/rasters/anantapur_ghi.tif`  
L. Then run zonal stats and compute scores

## Setup Without Docker (Now)

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r backend/requirements.txt
cp .env.example .env
```

## Setup With Docker (When Ready)

```bash
docker compose up -d
psql "postgresql://dhara_user:dhara_pass@localhost:5433/dhara" -f scripts/00_init_db.sql
```

## Data Download Instructions

### 1) Boundary (geoBoundaries)

```bash
mkdir -p data/raw/boundaries
cd data/raw/boundaries
curl -L -o geoboundaries-ind-adm2.zip "https://github.com/wmgeolab/geoBoundaries/raw/9469f09/releaseData/gbOpen/IND/ADM2/geoBoundaries-IND-ADM2-all.zip"
unzip geoboundaries-ind-adm2.zip -d geoboundaries_ind_adm2
```

### 2) Earth Engine Auth

```bash
earthengine authenticate
earthengine set_project YOUR_GCP_PROJECT_ID
```

Set `GEE_PROJECT_ID` in `.env`.

### 3) Global Solar Atlas Manual Download

- Visit: [Global Solar Atlas India Download](https://globalsolaratlas.info/download/india)
- Download India GHI raster into `data/raw/solar/`.
- Clip to Anantapur and save to `data/processed/rasters/anantapur_ghi.tif`.

## Exact Command Order

```bash
python scripts/01_load_boundary.py
python scripts/02_make_candidate_grid.py
python scripts/03_fetch_osm.py
python scripts/04_load_osm.py
python scripts/05_gee_export_anantapur.py
# manual: download GEE exports to data/raw/gee_exports/
# manual: prepare data/processed/rasters/anantapur_ghi.tif
python scripts/06_raster_to_zone_stats.py
python scripts/07_compute_scores.py
python scripts/08_smoke_test_db.py
```

## Troubleshooting

- **Boundary not found**: check shapefile path and district name columns.
- **DB connection fails**: verify `DATABASE_URL` and whether Docker/DB is running.
- **GEE auth fails**: rerun `earthengine authenticate` and confirm project ID.
- **Missing rasters**: scripts will print exact file paths expected.
- **Slow/fragile Docker**: defer DB steps and continue non-DB prep first.

## Week 1 Done Criteria

- Database schema created and accessible.
- Anantapur district inserted in `districts`.
- Candidate grid inserted in `candidate_sites`.
- OSM roads + substations loaded.
- GEE exports completed and manually downloaded.
- Zonal stats written for `crop_intensity`, `slope`, `solar_resource`.
- Scores computed in `scores`.
- API endpoints respond:
  - `GET /health`
  - `GET /sites/ranked?limit=50&min_score=0`
  - `GET /site/{site_id}`
  - `GET /methodology`
