from fastapi import APIRouter, Query
from sqlalchemy import text

from backend.app.db import engine

router = APIRouter()


@router.get("/sites/ranked")
def ranked_sites(limit: int = Query(50, ge=1, le=500), min_score: float = 0.0):
    sql = text(
        """
        SELECT
          c.id,
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
          c.id,
          c.grid_id,
          c.area_ha,
          ST_AsGeoJSON(c.geom)::json AS geom_geojson,
          ST_AsGeoJSON(c.centroid)::json AS centroid_geojson,
          s.total_score,
          s.confidence_score
        FROM candidate_sites c
        LEFT JOIN scores s ON s.site_id = c.id
        WHERE c.id::text = :site_id
        LIMIT 1;
        """
    )
    with engine.connect() as conn:
        row = conn.execute(sql, {"site_id": site_id}).mappings().first()
    return {"item": dict(row) if row else None}
