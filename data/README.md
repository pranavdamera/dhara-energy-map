# Data Layout

Week 1 data flow uses only public sources and manual downloads.

- `raw/boundaries/`: boundary zips/shapefiles (geoBoundaries/GADM source files)
- `raw/osm/`: raw Overpass JSON exports
- `raw/solar/`: Global Solar Atlas downloads
- `raw/gee_exports/`: manually downloaded Earth Engine export GeoTIFFs
- `processed/vectors/`: clipped/derived vector layers
- `processed/rasters/`: clipped rasters such as `anantapur_ghi.tif`
- `processed/tiles/`: optional map tiles for later use

Do not commit large rasters or proprietary data.
