import uuid

import geopandas as gpd
from shapely.geometry import box
from sqlalchemy import create_engine

DB_URL = "postgresql://dhara_user:dhara_pass@localhost:5433/dhara"

engine = create_engine(DB_URL)

district = gpd.read_postgis(
    "SELECT id, name, geom FROM districts WHERE name = 'Anantapur'",
    engine,
    geom_col="geom",
).to_crs("EPSG:32644")

district_id = int(district.iloc[0]["id"])
boundary = district.geometry.iloc[0]

cell_size = 1000  # meters
minx, miny, maxx, maxy = boundary.bounds

cells = []
i = 0
x = minx

while x < maxx:
    y = miny
    while y < maxy:
        cell = box(x, y, x + cell_size, y + cell_size)
        clipped = cell.intersection(boundary)
        if not clipped.is_empty and clipped.area > 250000:  # at least 25 ha
            cells.append(
                {
                    "grid_id": f"ATP-{i:06d}",
                    "district_id": district_id,
                    "area_ha": clipped.area / 10000,
                    "geometry": clipped,
                }
            )
            i += 1
        y += cell_size
    x += cell_size

gdf = gpd.GeoDataFrame(cells, crs="EPSG:32644")
gdf["centroid"] = gdf.geometry.centroid
gdf = gdf.to_crs("EPSG:4326")
gdf["centroid"] = gdf.to_crs("EPSG:32644").geometry.centroid.to_crs("EPSG:4326")

# GeoPandas only writes one geometry column cleanly.
centroids = gdf[["grid_id", "centroid"]].copy()
centroids = centroids.set_geometry("centroid")

sites = gdf[["grid_id", "district_id", "area_ha", "geometry"]].copy()
sites = sites.rename(columns={"geometry": "geom"}).set_geometry("geom")
sites["id"] = [str(uuid.uuid4()) for _ in range(len(sites))]

sites.to_postgis("candidate_sites_tmp", engine, if_exists="replace", index=False)

with engine.begin() as conn:
    conn.exec_driver_sql(
        """
        INSERT INTO candidate_sites (id, grid_id, district_id, area_ha, geom, centroid)
        SELECT id, grid_id, district_id, area_ha, geom, ST_Centroid(geom)
        FROM candidate_sites_tmp;
        DROP TABLE candidate_sites_tmp;
    """
    )

print(f"Generated {len(sites)} candidate cells")
