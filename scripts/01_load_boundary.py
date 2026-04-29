import os
from pathlib import Path

import geopandas as gpd
from dotenv import load_dotenv
from sqlalchemy import create_engine

load_dotenv()

DB_URL = os.getenv("DATABASE_URL", "postgresql://dhara_user:dhara_pass@localhost:5433/dhara")
SRC = Path("data/raw/boundaries/geoboundaries_ind_adm2/geoBoundaries-IND-ADM2.shp")

if not SRC.exists():
    print(f"[ERROR] Missing boundary shapefile: {SRC}")
    print("Download and unzip geoBoundaries IND ADM2 into data/raw/boundaries/geoboundaries_ind_adm2/")
    raise SystemExit(1)

gdf = gpd.read_file(SRC).to_crs("EPSG:4326")  # Store geometries in EPSG:4326.

string_cols = gdf.select_dtypes(include=["object", "string"]).columns.tolist()
mask = gdf[string_cols].astype(str).apply(
    lambda col: col.str.contains("Anantapur", case=False, na=False)
).any(axis=1)
anantapur = gdf[mask].copy()

if anantapur.empty:
    print("[ERROR] Could not find 'Anantapur' in boundary attributes.")
    print("Possible searchable string columns:", string_cols)
    print("Tip: inspect sample rows with `python -c` + geopandas to find district label fields.")
    raise SystemExit(1)

anantapur["name"] = "Anantapur"
anantapur["state"] = "Andhra Pradesh"
anantapur["country"] = "India"
anantapur["source"] = "geoBoundaries IND ADM2"

anantapur = anantapur[["name", "state", "country", "source", "geometry"]]
anantapur = anantapur.rename(columns={"geometry": "geom"}).set_geometry("geom")

engine = create_engine(DB_URL)
anantapur.to_postgis("districts", engine, if_exists="append", index=False)
print(f"Loaded Anantapur boundary rows: {len(anantapur)}")
