from pathlib import Path
import os

import geopandas as gpd
import requests
from dotenv import load_dotenv
from sqlalchemy import create_engine

load_dotenv()

DB_URL = os.getenv("DATABASE_URL", "postgresql://dhara_user:dhara_pass@localhost:5433/dhara")
OVERPASS_URL = "https://overpass-api.de/api/interpreter"
OUT_PATH = Path("data/raw/osm/anantapur_overpass.json")

engine = create_engine(DB_URL)

district = gpd.read_postgis(
    "SELECT geom FROM districts WHERE name = 'Anantapur'",
    engine,
    geom_col="geom",
).to_crs("EPSG:4326")

if district.empty:
    print("[ERROR] District 'Anantapur' not found in `districts`.")
    print("Run scripts/01_load_boundary.py first.")
    raise SystemExit(1)

minx, miny, maxx, maxy = district.total_bounds
bbox = f"{miny},{minx},{maxy},{maxx}"

query = f"""
[out:json][timeout:180];
(
  way["highway"]({bbox});
  node["power"="substation"]({bbox});
  way["power"="substation"]({bbox});
  relation["power"="substation"]({bbox});
);
out body;
>;
out skel qt;
"""

resp = requests.post(OVERPASS_URL, data={"data": query}, timeout=240)
resp.raise_for_status()

OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
OUT_PATH.write_text(resp.text)

print(f"Saved OSM Overpass response: {OUT_PATH}")
