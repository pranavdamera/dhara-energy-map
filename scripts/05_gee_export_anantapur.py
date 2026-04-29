import os

import ee
import geemap
import geopandas as gpd
from dotenv import load_dotenv
from sqlalchemy import create_engine

load_dotenv()

DB_URL = os.getenv("DATABASE_URL", "postgresql://dhara_user:dhara_pass@localhost:5433/dhara")
GCP_PROJECT_ID = os.getenv("GEE_PROJECT_ID", "YOUR_GCP_PROJECT_ID")

if GCP_PROJECT_ID == "YOUR_GCP_PROJECT_ID":
    print("[ERROR] Set GEE_PROJECT_ID in your .env before running this script.")
    raise SystemExit(1)

engine = create_engine(DB_URL)
ee.Initialize(project=GCP_PROJECT_ID)

district = gpd.read_postgis(
    "SELECT geom FROM districts WHERE name = 'Anantapur'",
    engine,
    geom_col="geom",
).to_crs("EPSG:4326")

if district.empty:
    print("[ERROR] District 'Anantapur' not found in `districts`.")
    print("Run scripts/01_load_boundary.py first.")
    raise SystemExit(1)

region = geemap.geopandas_to_ee(district).geometry()


def mask_s2_clouds(img):
    scl = img.select("SCL")
    mask = (
        scl.neq(3)
        .And(scl.neq(8))
        .And(scl.neq(9))
        .And(scl.neq(10))
        .And(scl.neq(11))
    )
    return img.updateMask(mask)


s2 = (
    ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
    .filterBounds(region)
    .filterDate("2024-01-01", "2024-12-31")
    .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 30))
    .map(mask_s2_clouds)
    .map(lambda img: img.addBands(img.normalizedDifference(["B8", "B4"]).rename("NDVI")))
)

ndvi_mean = s2.select("NDVI").mean().clip(region).rename("ndvi_mean")
ndvi_p75 = (
    s2.select("NDVI")
    .reduce(ee.Reducer.percentile([75]))
    .clip(region)
    .rename("ndvi_p75")
)
ndvi_std = s2.select("NDVI").reduce(ee.Reducer.stdDev()).clip(region).rename("ndvi_std")

ndvi_out = ndvi_mean.addBands(ndvi_p75).addBands(ndvi_std)

ndvi_task = ee.batch.Export.image.toDrive(
    image=ndvi_out,
    description="dhara_anantapur_ndvi_2024",
    folder="dhara_energy_map",
    fileNamePrefix="anantapur_ndvi_2024",
    region=region,
    scale=30,
    crs="EPSG:4326",
    maxPixels=1e13,
)
ndvi_task.start()
print("Started NDVI export:", ndvi_task.id)

worldcover = ee.Image("ESA/WorldCover/v200/2021").select("Map").clip(region)

worldcover_task = ee.batch.Export.image.toDrive(
    image=worldcover,
    description="dhara_anantapur_worldcover_2021",
    folder="dhara_energy_map",
    fileNamePrefix="anantapur_worldcover_2021",
    region=region,
    scale=10,
    crs="EPSG:4326",
    maxPixels=1e13,
)
worldcover_task.start()
print("Started WorldCover export:", worldcover_task.id)

dem = ee.Image("USGS/SRTMGL1_003").select("elevation").clip(region)
slope = ee.Terrain.slope(dem).rename("slope_deg")
srtm_out = dem.rename("elevation_m").addBands(slope)

srtm_task = ee.batch.Export.image.toDrive(
    image=srtm_out,
    description="dhara_anantapur_srtm_slope",
    folder="dhara_energy_map",
    fileNamePrefix="anantapur_srtm_slope",
    region=region,
    scale=30,
    crs="EPSG:4326",
    maxPixels=1e13,
)
srtm_task.start()
print("Started SRTM export:", srtm_task.id)

print(
    "After tasks finish, manually download files from Google Drive/dhara_energy_map "
    "into data/raw/gee_exports/"
)
