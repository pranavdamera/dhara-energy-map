CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_raster;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

DROP TABLE IF EXISTS reports CASCADE;
DROP TABLE IF EXISTS risk_flags CASCADE;
DROP TABLE IF EXISTS scores CASCADE;
DROP TABLE IF EXISTS slope CASCADE;
DROP TABLE IF EXISTS land_cover CASCADE;
DROP TABLE IF EXISTS crop_intensity CASCADE;
DROP TABLE IF EXISTS solar_resource CASCADE;
DROP TABLE IF EXISTS candidate_sites CASCADE;
DROP TABLE IF EXISTS roads CASCADE;
DROP TABLE IF EXISTS substations CASCADE;
DROP TABLE IF EXISTS districts CASCADE;

CREATE TABLE districts (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    state TEXT NOT NULL,
    country TEXT DEFAULT 'India',
    source TEXT,
    geom geometry(MultiPolygon, 4326) NOT NULL
);

CREATE INDEX districts_geom_gix ON districts USING GIST (geom);

CREATE TABLE substations (
    id SERIAL PRIMARY KEY,
    osm_id TEXT,
    name TEXT,
    voltage TEXT,
    operator TEXT,
    source TEXT DEFAULT 'OpenStreetMap',
    geom geometry(Point, 4326) NOT NULL
);

CREATE INDEX substations_geom_gix ON substations USING GIST (geom);

CREATE TABLE roads (
    id SERIAL PRIMARY KEY,
    osm_id TEXT,
    name TEXT,
    highway TEXT,
    surface TEXT,
    source TEXT DEFAULT 'OpenStreetMap',
    geom geometry(LineString, 4326) NOT NULL
);

CREATE INDEX roads_geom_gix ON roads USING GIST (geom);
CREATE INDEX roads_highway_idx ON roads (highway);

CREATE TABLE candidate_sites (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    grid_id TEXT UNIQUE NOT NULL,
    district_id INTEGER REFERENCES districts(id),
    area_ha NUMERIC,
    centroid geometry(Point, 4326) NOT NULL,
    geom geometry(MultiPolygon, 4326) NOT NULL,
    created_at TIMESTAMP DEFAULT now()
);

CREATE INDEX candidate_sites_geom_gix ON candidate_sites USING GIST (geom);
CREATE INDEX candidate_sites_centroid_gix ON candidate_sites USING GIST (centroid);

CREATE TABLE solar_resource (
    site_id UUID PRIMARY KEY REFERENCES candidate_sites(id) ON DELETE CASCADE,
    ghi_kwh_m2_day NUMERIC,
    pvout_kwh_kwp_day NUMERIC,
    source TEXT DEFAULT 'Global Solar Atlas',
    confidence NUMERIC DEFAULT 0.8
);

CREATE TABLE crop_intensity (
    site_id UUID PRIMARY KEY REFERENCES candidate_sites(id) ON DELETE CASCADE,
    ndvi_mean NUMERIC,
    ndvi_p75 NUMERIC,
    ndvi_seasonality NUMERIC,
    crop_intensity_score NUMERIC,
    source TEXT DEFAULT 'Sentinel-2 SR Harmonized',
    confidence NUMERIC DEFAULT 0.7
);

CREATE TABLE land_cover (
    site_id UUID PRIMARY KEY REFERENCES candidate_sites(id) ON DELETE CASCADE,
    dominant_class INTEGER,
    dominant_label TEXT,
    built_pct NUMERIC,
    cropland_pct NUMERIC,
    bare_sparse_pct NUMERIC,
    tree_pct NUMERIC,
    water_pct NUMERIC,
    source TEXT DEFAULT 'ESA WorldCover v200',
    confidence NUMERIC DEFAULT 0.7
);

CREATE TABLE slope (
    site_id UUID PRIMARY KEY REFERENCES candidate_sites(id) ON DELETE CASCADE,
    elevation_mean_m NUMERIC,
    slope_mean_deg NUMERIC,
    slope_p90_deg NUMERIC,
    source TEXT DEFAULT 'SRTMGL1_003',
    confidence NUMERIC DEFAULT 0.75
);

CREATE TABLE scores (
    site_id UUID PRIMARY KEY REFERENCES candidate_sites(id) ON DELETE CASCADE,

    solar_norm NUMERIC,
    substation_norm NUMERIC,
    road_norm NUMERIC,
    slope_norm NUMERIC,
    land_norm NUMERIC,
    crop_norm NUMERIC,

    solar_contribution NUMERIC,
    substation_contribution NUMERIC,
    road_contribution NUMERIC,
    slope_contribution NUMERIC,
    land_contribution NUMERIC,
    crop_contribution NUMERIC,

    total_score NUMERIC,
    confidence_score NUMERIC,
    score_version TEXT DEFAULT 'v1.0',
    computed_at TIMESTAMP DEFAULT now()
);

CREATE INDEX scores_total_score_idx ON scores (total_score DESC);

CREATE TABLE risk_flags (
    id SERIAL PRIMARY KEY,
    site_id UUID REFERENCES candidate_sites(id) ON DELETE CASCADE,
    flag_type TEXT NOT NULL,
    severity TEXT CHECK (severity IN ('low', 'medium', 'high')),
    message TEXT NOT NULL,
    source TEXT,
    created_at TIMESTAMP DEFAULT now()
);

CREATE INDEX risk_flags_site_idx ON risk_flags (site_id);

CREATE TABLE reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    site_id UUID REFERENCES candidate_sites(id) ON DELETE CASCADE,
    report_url TEXT,
    report_status TEXT CHECK (report_status IN ('pending', 'ready', 'failed')) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT now()
);