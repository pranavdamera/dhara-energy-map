import geopandas as gpd
from sqlalchemy import create_engine

DB_URL = "postgresql://dhara_user:dhara_pass@localhost:5433/dhara"
SRC = "data/raw/boundaries/geoboundaries_ind_adm2/geoBoundaries-IND-ADM2.shp"

gdf = gpd.read_file(SRC).to_crs("EPSG:4326")

# Inspect columns first if this fails:
# print(gdf.columns)
mask = gdf.astype(str).apply(
    lambda col: col.str.contains("Anantapur", case=False, na=False)
).any(axis=1)
anantapur = gdf[mask].copy()

if anantapur.empty:
    raise ValueError(
        "Could not find Anantapur. Print columns and inspect boundary attributes."
    )

anantapur["name"] = "Anantapur"
anantapur["state"] = "Andhra Pradesh"
anantapur["country"] = "India"
anantapur["source"] = "geoBoundaries IND ADM2"

anantapur = anantapur[["name", "state", "country", "source", "geometry"]]
anantapur = anantapur.rename(columns={"geometry": "geom"})
anantapur = anantapur.set_geometry("geom")

engine = create_engine(DB_URL)
anantapur.to_postgis("districts", engine, if_exists="append", index=False)
print("Loaded Anantapur boundary:", len(anantapur))
