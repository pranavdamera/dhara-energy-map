import geopandas as gpd
import osmnx as ox
from sqlalchemy import create_engine

DB_URL = "postgresql://dhara_user:dhara_pass@localhost:5433/dhara"
engine = create_engine(DB_URL)

district = gpd.read_postgis(
    "SELECT geom FROM districts WHERE name = 'Anantapur'",
    engine,
    geom_col="geom",
).to_crs("EPSG:4326")

poly = district.geometry.iloc[0]

roads = ox.features_from_polygon(poly, tags={"highway": True})
roads = roads.reset_index()
roads = roads[roads.geometry.type.isin(["LineString", "MultiLineString"])].to_crs(
    "EPSG:4326"
)
roads = roads.explode(index_parts=False)
roads = roads[roads.geometry.type == "LineString"]

roads_out = roads[["osmid", "name", "highway", "surface", "geometry"]].copy()
roads_out["osm_id"] = roads_out["osmid"].astype(str)
roads_out["source"] = "OpenStreetMap"
roads_out = roads_out[["osm_id", "name", "highway", "surface", "source", "geometry"]]
roads_out = roads_out.rename(columns={"geometry": "geom"}).set_geometry("geom")
roads_out.to_postgis("roads", engine, if_exists="append", index=False)

subs = ox.features_from_polygon(poly, tags={"power": "substation"})
subs = subs.reset_index()
subs = subs.to_crs("EPSG:4326")
subs["geometry"] = subs.geometry.centroid
subs_out = subs[["osmid", "name", "voltage", "operator", "geometry"]].copy()
subs_out["osm_id"] = subs_out["osmid"].astype(str)
subs_out["source"] = "OpenStreetMap"
subs_out = subs_out[["osm_id", "name", "voltage", "operator", "source", "geometry"]]
subs_out = subs_out.rename(columns={"geometry": "geom"}).set_geometry("geom")
subs_out.to_postgis("substations", engine, if_exists="append", index=False)

print("Loaded roads:", len(roads_out))
print("Loaded substations:", len(subs_out))
