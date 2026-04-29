import os
from pathlib import Path

import geopandas as gpd
import numpy as np
import rasterio
from dotenv import load_dotenv
from rasterio.mask import mask
from sqlalchemy import create_engine, text

load_dotenv()

DB_URL = os.getenv("DATABASE_URL", "postgresql://dhara_user:dhara_pass@localhost:5433/dhara")
STORAGE_CRS = os.getenv("TARGET_STORAGE_CRS", "EPSG:4326")

NDVI_PATH = Path("data/raw/gee_exports/anantapur_ndvi_2024.tif")
SRTM_PATH = Path("data/raw/gee_exports/anantapur_srtm_slope.tif")
GHI_PATH = Path("data/processed/rasters/anantapur_ghi.tif")
WORLDCOVER_PATH = Path("data/raw/gee_exports/anantapur_worldcover_2021.tif")

WORLD_COVER_LABELS = {
    10: "Tree cover",
    20: "Shrubland",
    30: "Grassland",
    40: "Cropland",
    50: "Built-up",
    60: "Bare/sparse vegetation",
    70: "Snow/ice",
    80: "Permanent water bodies",
    90: "Herbaceous wetland",
    95: "Mangroves",
    100: "Moss/lichen",
}


def nanpercentile_safe(arr, q):
    valid = arr[np.isfinite(arr)]
    if valid.size == 0:
        return None
    return float(np.percentile(valid, q))


def nanmean_safe(arr):
    valid = arr[np.isfinite(arr)]
    if valid.size == 0:
        return None
    return float(np.mean(valid))


def zonal_band_values(src, geom, band_idx):
    out, _ = mask(src, [geom], crop=True, filled=True, nodata=np.nan)
    arr = out[band_idx - 1].astype("float64")
    return arr


def ensure_inputs():
    required = [NDVI_PATH, SRTM_PATH, GHI_PATH]
    missing = [p for p in required if not p.exists()]
    if missing:
        print("[ERROR] Missing required raster inputs:")
        for m in missing:
            print(f"  - {m}")
        print("Populate files first, then rerun.")
        raise SystemExit(1)


def main():
    ensure_inputs()

    engine = create_engine(DB_URL)
    sites = gpd.read_postgis(
        "SELECT id, geom FROM candidate_sites",
        engine,
        geom_col="geom",
    ).to_crs(STORAGE_CRS)
    if sites.empty:
        print("[ERROR] candidate_sites is empty. Run grid generation first.")
        raise SystemExit(1)

    with rasterio.open(NDVI_PATH) as ndvi_src, rasterio.open(SRTM_PATH) as srtm_src, rasterio.open(
        GHI_PATH
    ) as ghi_src:
        ndvi_crs = ndvi_src.crs
        srtm_crs = srtm_src.crs
        ghi_crs = ghi_src.crs

        for _, row in sites.iterrows():
            site_id = str(row["id"])

            site_ndvi_geom = gpd.GeoSeries([row["geom"]], crs=STORAGE_CRS).to_crs(ndvi_crs).iloc[0]
            site_srtm_geom = gpd.GeoSeries([row["geom"]], crs=STORAGE_CRS).to_crs(srtm_crs).iloc[0]
            site_ghi_geom = gpd.GeoSeries([row["geom"]], crs=STORAGE_CRS).to_crs(ghi_crs).iloc[0]

            ndvi_mean = nanmean_safe(zonal_band_values(ndvi_src, site_ndvi_geom, 1))
            ndvi_p75 = nanpercentile_safe(zonal_band_values(ndvi_src, site_ndvi_geom, 2), 75)
            ndvi_std = nanmean_safe(zonal_band_values(ndvi_src, site_ndvi_geom, 3))
            crop_score = None if ndvi_mean is None else float(np.clip(1 - ndvi_mean, 0, 1))

            elev_mean = nanmean_safe(zonal_band_values(srtm_src, site_srtm_geom, 1))
            slope_mean = nanmean_safe(zonal_band_values(srtm_src, site_srtm_geom, 2))
            slope_p90 = nanpercentile_safe(zonal_band_values(srtm_src, site_srtm_geom, 2), 90)

            ghi_mean = nanmean_safe(zonal_band_values(ghi_src, site_ghi_geom, 1))

            with engine.begin() as conn:
                conn.execute(
                    text(
                        """
                        INSERT INTO crop_intensity (site_id, ndvi_mean, ndvi_p75, ndvi_seasonality, crop_intensity_score)
                        VALUES (:site_id, :ndvi_mean, :ndvi_p75, :ndvi_std, :crop_score)
                        ON CONFLICT (site_id) DO UPDATE SET
                          ndvi_mean = EXCLUDED.ndvi_mean,
                          ndvi_p75 = EXCLUDED.ndvi_p75,
                          ndvi_seasonality = EXCLUDED.ndvi_seasonality,
                          crop_intensity_score = EXCLUDED.crop_intensity_score;
                        """
                    ),
                    {
                        "site_id": site_id,
                        "ndvi_mean": ndvi_mean,
                        "ndvi_p75": ndvi_p75,
                        "ndvi_std": ndvi_std,
                        "crop_score": crop_score,
                    },
                )
                conn.execute(
                    text(
                        """
                        INSERT INTO slope (site_id, elevation_mean_m, slope_mean_deg, slope_p90_deg)
                        VALUES (:site_id, :elev_mean, :slope_mean, :slope_p90)
                        ON CONFLICT (site_id) DO UPDATE SET
                          elevation_mean_m = EXCLUDED.elevation_mean_m,
                          slope_mean_deg = EXCLUDED.slope_mean_deg,
                          slope_p90_deg = EXCLUDED.slope_p90_deg;
                        """
                    ),
                    {
                        "site_id": site_id,
                        "elev_mean": elev_mean,
                        "slope_mean": slope_mean,
                        "slope_p90": slope_p90,
                    },
                )
                conn.execute(
                    text(
                        """
                        INSERT INTO solar_resource (site_id, ghi_kwh_m2_day)
                        VALUES (:site_id, :ghi)
                        ON CONFLICT (site_id) DO UPDATE SET
                          ghi_kwh_m2_day = EXCLUDED.ghi_kwh_m2_day;
                        """
                    ),
                    {"site_id": site_id, "ghi": ghi_mean},
                )

    if WORLDCOVER_PATH.exists():
        print("[TODO] WorldCover zonal percentages can be implemented here next.")
        print("Target fields: built_pct, cropland_pct, bare_sparse_pct, tree_pct, water_pct.")
        print(f"Class map loaded with {len(WORLD_COVER_LABELS)} classes.")
    else:
        print(f"[INFO] Optional WorldCover raster not found: {WORLDCOVER_PATH}")
        print("Skipping land_cover population for now.")

    print("Zonal stats written for crop_intensity, slope, and solar_resource.")


if __name__ == "__main__":
    main()
