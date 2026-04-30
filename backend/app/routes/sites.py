from fastapi import APIRouter, Query
from sqlalchemy import text

from backend.app.db import engine

router = APIRouter()


@router.get("/sites/ranked")
def ranked_sites(limit: int = Query(50, ge=1, le=500), min_score: float = 0.0):
    sql = text(
        """
        SELECT
          c.id::text,
          c.grid_id,
          s.total_score,
          s.confidence_score,
          ST_AsGeoJSON(c.centroid)::json AS centroid_geojson
        FROM candidate_sites c
        JOIN scores s ON s.site_id = c.id
        WHERE s.total_score >= :min_score
        ORDER BY s.total_score DESC
        LIMIT :limit;
        """
    )
    with engine.connect() as conn:
        rows = conn.execute(sql, {"limit": limit, "min_score": min_score}).mappings().all()
    return {"count": len(rows), "items": [dict(r) for r in rows]}


@router.get("/site/{site_id}")
def site_detail(site_id: str):
    sql = text(
        """
        SELECT
          c.id::text,
          c.grid_id,
          c.area_ha,
          ST_AsGeoJSON(c.geom)::json     AS geom_geojson,
          ST_AsGeoJSON(c.centroid)::json AS centroid_geojson,
          s.total_score,
          s.confidence_score,
          s.solar_norm,
          s.solar_contribution,
          s.substation_norm,
          s.substation_contribution,
          s.road_norm,
          s.road_contribution,
          s.slope_norm,
          s.slope_contribution,
          s.land_norm,
          s.land_contribution,
          s.crop_norm,
          s.crop_contribution,
          s.score_version
        FROM candidate_sites c
        LEFT JOIN scores s ON s.site_id = c.id
        WHERE c.id::text = :site_id
        LIMIT 1;
        """
    )
    with engine.connect() as conn:
        row = conn.execute(sql, {"site_id": site_id}).mappings().first()
    if row is None:
        return {"item": None}

    data = dict(row)
    score_breakdown = {
        "solar_norm": data.pop("solar_norm", None),
        "solar_contribution": data.pop("solar_contribution", None),
        "substation_norm": data.pop("substation_norm", None),
        "substation_contribution": data.pop("substation_contribution", None),
        "road_norm": data.pop("road_norm", None),
        "road_contribution": data.pop("road_contribution", None),
        "slope_norm": data.pop("slope_norm", None),
        "slope_contribution": data.pop("slope_contribution", None),
        "land_norm": data.pop("land_norm", None),
        "land_contribution": data.pop("land_contribution", None),
        "crop_norm": data.pop("crop_norm", None),
        "crop_contribution": data.pop("crop_contribution", None),
        "score_version": data.pop("score_version", None),
    }
    data["score_breakdown"] = score_breakdown
    return {"item": data}
