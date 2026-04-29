# Week 1 Methodology

## Scope Lock

- District: Anantapur, Andhra Pradesh only.
- Six layers only: boundary, NDVI, WorldCover, SRTM slope/elevation, OSM roads+substations, Global Solar Atlas irradiance.
- Explainable weighted-additive scoring only.

## Coordinate Reference Systems

- Storage CRS: `EPSG:4326` for all geometries in PostGIS.
- Metric CRS: `EPSG:32644` for distance and area calculations.

## Candidate Site Generation

- Build a 1 km x 1 km grid in metric CRS.
- Clip to district polygon.
- Keep cells above 25 ha to remove tiny slivers.

## Explainable Scoring

Weighted additive score:

`0.25*solar + 0.20*substation + 0.15*road + 0.15*slope + 0.15*land + 0.10*crop`

- Min-max normalization for positive factors.
- Inverse min-max for distance-based factors.
- Slope penalty: `1 - min(slope_mean_deg/10, 1)`.
- Crop proxy uses inverse NDVI percentile (`ndvi_p75`) as instructed.
- Missing values filled with district medians.
- Confidence decreases with missing factors.
