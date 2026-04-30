from fastapi import APIRouter
from sqlalchemy import text

from backend.app.db import engine

router = APIRouter()


@router.get("/site/{site_id}/observations")
def site_observations(site_id: str):
    sql = text(
        """
        SELECT
          id::text,
          site_id::text,
          observed_at,
          source,
          observation_type,
          raster_asset_url,
          ndvi_mean,
          cloud_cover,
          change_score,
          notes
        FROM parcel_observation_snapshots
        WHERE site_id::text = :site_id
        ORDER BY observed_at DESC;
        """
    )
    with engine.connect() as conn:
        rows = conn.execute(sql, {"site_id": site_id}).mappings().all()
    return {"site_id": site_id, "count": len(rows), "items": [dict(r) for r in rows]}
