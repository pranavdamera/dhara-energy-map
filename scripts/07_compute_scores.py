import os

import numpy as np
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

DB_URL = os.getenv("DATABASE_URL", "postgresql://dhara_user:dhara_pass@localhost:5433/dhara")
METRIC_CRS = int(os.getenv("TARGET_METRIC_CRS", "EPSG:32644").split(":")[1])


def minmax(series: pd.Series) -> pd.Series:
    s = series.astype(float)
    mn, mx = s.min(), s.max()
    if pd.isna(mn) or pd.isna(mx) or mn == mx:
        return pd.Series(np.ones(len(series)), index=series.index)
    return (s - mn) / (mx - mn)


def inverse_minmax(series: pd.Series) -> pd.Series:
    return 1.0 - minmax(series)


def main():
    engine = create_engine(DB_URL)
    sql = f"""
    WITH nearest AS (
      SELECT
        c.id AS site_id,
        MIN(ST_Distance(ST_Transform(c.centroid, {METRIC_CRS}), ST_Transform(s.geom, {METRIC_CRS}))) / 1000.0 AS substation_km,
        MIN(
          CASE WHEN r.highway IN ('primary', 'secondary', 'tertiary', 'trunk')
               THEN ST_Distance(ST_Transform(c.centroid, {METRIC_CRS}), ST_Transform(r.geom, {METRIC_CRS})) / 1000.0
               ELSE NULL END
        ) AS road_km
      FROM candidate_sites c
      LEFT JOIN substations s ON TRUE
      LEFT JOIN roads r ON TRUE
      GROUP BY c.id
    )
    SELECT
      c.id AS site_id,
      sr.ghi_kwh_m2_day,
      n.substation_km,
      n.road_km,
      sp.slope_mean_deg,
      lc.bare_sparse_pct,
      ci.ndvi_p75
    FROM candidate_sites c
    LEFT JOIN solar_resource sr ON sr.site_id = c.id
    LEFT JOIN nearest n ON n.site_id = c.id
    LEFT JOIN slope sp ON sp.site_id = c.id
    LEFT JOIN land_cover lc ON lc.site_id = c.id
    LEFT JOIN crop_intensity ci ON ci.site_id = c.id;
    """
    df = pd.read_sql(sql, engine)
    if df.empty:
        print("[ERROR] No candidate sites found. Run scripts/02_make_candidate_grid.py first.")
        raise SystemExit(1)

    # Explainable weighted scoring: each factor is normalized and contributes visibly.
    factors = ["ghi_kwh_m2_day", "substation_km", "road_km", "slope_mean_deg", "bare_sparse_pct", "ndvi_p75"]
    for col in factors:
        if col not in df.columns:
            df[col] = np.nan
        med = df[col].median(skipna=True)
        if pd.isna(med):
            med = 0.0
        df[col] = df[col].fillna(med)

    df["solar_norm"] = minmax(df["ghi_kwh_m2_day"])
    df["substation_norm"] = inverse_minmax(df["substation_km"])
    df["road_norm"] = inverse_minmax(df["road_km"])
    df["slope_norm"] = 1 - np.minimum(df["slope_mean_deg"] / 10.0, 1.0)
    df["land_norm"] = minmax(df["bare_sparse_pct"])
    df["crop_norm"] = inverse_minmax(df["ndvi_p75"])

    weights = {
        "solar": 0.25,
        "substation": 0.20,
        "road": 0.15,
        "slope": 0.15,
        "land": 0.15,
        "crop": 0.10,
    }

    df["solar_contribution"] = df["solar_norm"] * weights["solar"]
    df["substation_contribution"] = df["substation_norm"] * weights["substation"]
    df["road_contribution"] = df["road_norm"] * weights["road"]
    df["slope_contribution"] = df["slope_norm"] * weights["slope"]
    df["land_contribution"] = df["land_norm"] * weights["land"]
    df["crop_contribution"] = df["crop_norm"] * weights["crop"]
    df["total_score"] = (
        df["solar_contribution"]
        + df["substation_contribution"]
        + df["road_contribution"]
        + df["slope_contribution"]
        + df["land_contribution"]
        + df["crop_contribution"]
    )

    # Confidence: lower confidence when source columns were missing before median fill.
    missing_counts = pd.DataFrame(
        {
            "solar": pd.read_sql("SELECT site_id, ghi_kwh_m2_day FROM solar_resource", engine).set_index("site_id")[
                "ghi_kwh_m2_day"
            ],
        }
    )
    del missing_counts  # keep implementation simple and deterministic for Week 1 scaffold
    # Approximate missing count from originally null raw features in df load.
    raw = pd.read_sql(sql, engine)
    miss = raw[factors].isna().sum(axis=1)
    df["confidence_score"] = np.clip(0.8 - 0.1 * miss, 0, 1)

    upsert_sql = text(
        """
        INSERT INTO scores (
          site_id, solar_norm, substation_norm, road_norm, slope_norm, land_norm, crop_norm,
          solar_contribution, substation_contribution, road_contribution, slope_contribution, land_contribution, crop_contribution,
          total_score, confidence_score
        )
        VALUES (
          :site_id, :solar_norm, :substation_norm, :road_norm, :slope_norm, :land_norm, :crop_norm,
          :solar_contribution, :substation_contribution, :road_contribution, :slope_contribution, :land_contribution, :crop_contribution,
          :total_score, :confidence_score
        )
        ON CONFLICT (site_id) DO UPDATE SET
          solar_norm = EXCLUDED.solar_norm,
          substation_norm = EXCLUDED.substation_norm,
          road_norm = EXCLUDED.road_norm,
          slope_norm = EXCLUDED.slope_norm,
          land_norm = EXCLUDED.land_norm,
          crop_norm = EXCLUDED.crop_norm,
          solar_contribution = EXCLUDED.solar_contribution,
          substation_contribution = EXCLUDED.substation_contribution,
          road_contribution = EXCLUDED.road_contribution,
          slope_contribution = EXCLUDED.slope_contribution,
          land_contribution = EXCLUDED.land_contribution,
          crop_contribution = EXCLUDED.crop_contribution,
          total_score = EXCLUDED.total_score,
          confidence_score = EXCLUDED.confidence_score,
          computed_at = now();
        """
    )

    with engine.begin() as conn:
        for _, row in df.iterrows():
            conn.execute(upsert_sql, row.to_dict())

    print(f"Scores computed for {len(df)} candidate sites.")


if __name__ == "__main__":
    main()
