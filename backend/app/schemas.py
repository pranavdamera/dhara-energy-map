from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class ScoreBreakdown(BaseModel):
    solar_norm: Optional[float] = None
    solar_contribution: Optional[float] = None
    substation_norm: Optional[float] = None
    substation_contribution: Optional[float] = None
    road_norm: Optional[float] = None
    road_contribution: Optional[float] = None
    slope_norm: Optional[float] = None
    slope_contribution: Optional[float] = None
    land_norm: Optional[float] = None
    land_contribution: Optional[float] = None
    crop_norm: Optional[float] = None
    crop_contribution: Optional[float] = None
    score_version: Optional[str] = None


class ObservationSnapshot(BaseModel):
    id: str
    site_id: str
    observed_at: datetime
    source: str
    observation_type: str
    raster_asset_url: Optional[str] = None
    ndvi_mean: Optional[float] = None
    cloud_cover: Optional[float] = None
    change_score: Optional[float] = None
    notes: Optional[str] = None
