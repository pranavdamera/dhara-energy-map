"""
Seed the database with a small demo dataset for local API exploration.

Inserts:
  - 1 district (Anantapur, simplified boundary)
  - 4 candidate sites
  - 2 substations, 2 roads
  - Solar, crop intensity, land cover, slope records for each site
  - Scores for each site
  - 2 parcel observation snapshots on 2 sites

Safe to run multiple times — uses INSERT ... ON CONFLICT DO NOTHING where possible,
and clears+reinserts the demo district each run.

Usage:
    python scripts/seed_demo.py
    DATABASE_URL=postgresql://... python scripts/seed_demo.py
"""

import os
import sys
import uuid
from datetime import datetime

import psycopg2
from psycopg2.extras import execute_values

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://dhara_user:dhara_pass@localhost:5433/dhara"
)


SITES = [
    {
        "id": "a1b2c3d4-0000-0000-0000-000000000001",
        "grid_id": "demo_r042_c017",
        "area_ha": 98.4,
        "lon": 77.5842,
        "lat": 14.8231,
    },
    {
        "id": "a1b2c3d4-0000-0000-0000-000000000002",
        "grid_id": "demo_r038_c021",
        "area_ha": 87.1,
        "lon": 77.6103,
        "lat": 14.7894,
    },
    {
        "id": "a1b2c3d4-0000-0000-0000-000000000003",
        "grid_id": "demo_r051_c009",
        "area_ha": 102.3,
        "lon": 77.4921,
        "lat": 14.9102,
    },
    {
        "id": "a1b2c3d4-0000-0000-0000-000000000004",
        "grid_id": "demo_r031_c033",
        "area_ha": 75.6,
        "lon": 77.7241,
        "lat": 14.7102,
    },
]

SCORES = [
    # site_id, solar_norm, sub_norm, road_norm, slope_norm, land_norm, crop_norm, total, confidence
    ("a1b2c3d4-0000-0000-0000-000000000001", 0.84, 0.72, 0.91, 0.95, 0.61, 0.58, 0.763, 0.8),
    ("a1b2c3d4-0000-0000-0000-000000000002", 0.79, 0.81, 0.74, 0.88, 0.55, 0.44, 0.724, 0.8),
    ("a1b2c3d4-0000-0000-0000-000000000003", 0.91, 0.48, 0.83, 0.97, 0.70, 0.62, 0.741, 0.7),
    ("a1b2c3d4-0000-0000-0000-000000000004", 0.68, 0.60, 0.55, 0.82, 0.44, 0.71, 0.611, 0.8),
]

OBSERVATIONS = [
    {
        "site_id": "a1b2c3d4-0000-0000-0000-000000000001",
        "observed_at": datetime(2024, 11, 15, 10, 30),
        "source": "Sentinel-2",
        "observation_type": "satellite_derived",
        "ndvi_mean": 0.31,
        "cloud_cover": 0.04,
        "notes": "Post-monsoon dry-down period. Low vegetation activity.",
    },
    {
        "site_id": "a1b2c3d4-0000-0000-0000-000000000001",
        "observed_at": datetime(2024, 3, 20, 8, 0),
        "source": "field_survey",
        "observation_type": "field_survey",
        "ndvi_mean": None,
        "cloud_cover": None,
        "notes": "Accessible via state highway. Flat terrain confirmed. No active cultivation observed.",
    },
    {
        "site_id": "a1b2c3d4-0000-0000-0000-000000000003",
        "observed_at": datetime(2024, 8, 5, 6, 45),
        "source": "Sentinel-2",
        "observation_type": "satellite_derived",
        "ndvi_mean": 0.47,
        "cloud_cover": 0.12,
        "notes": "Monsoon peak. Elevated NDVI likely seasonal grass cover.",
    },
]


def cell_polygon(lon: float, lat: float, half_deg: float = 0.004) -> str:
    """Return a simple WKT polygon centered on (lon, lat)."""
    return (
        f"POLYGON(("
        f"{lon - half_deg} {lat - half_deg},"
        f"{lon + half_deg} {lat - half_deg},"
        f"{lon + half_deg} {lat + half_deg},"
        f"{lon - half_deg} {lat + half_deg},"
        f"{lon - half_deg} {lat - half_deg}"
        f"))"
    )


def main():
    print(f"Connecting to {DATABASE_URL.split('@')[-1]} ...")
    try:
        conn = psycopg2.connect(DATABASE_URL)
    except Exception as e:
        print(f"ERROR: Could not connect to database: {e}")
        sys.exit(1)

    cur = conn.cursor()

    # District
    cur.execute("DELETE FROM districts WHERE name = 'Anantapur' AND source = 'seed_demo'")
    cur.execute(
        """
        INSERT INTO districts (name, state, country, source, geom)
        VALUES (
            'Anantapur', 'Andhra Pradesh', 'India', 'seed_demo',
            ST_Multi(ST_GeomFromText(
                'POLYGON((77.2 14.5, 77.9 14.5, 77.9 15.1, 77.2 15.1, 77.2 14.5))',
                4326
            ))
        )
        RETURNING id;
        """
    )
    district_id = cur.fetchone()[0]
    print(f"  district inserted (id={district_id})")

    # Candidate sites
    for site in SITES:
        poly_wkt = cell_polygon(site["lon"], site["lat"])
        cur.execute(
            """
            INSERT INTO candidate_sites (id, grid_id, district_id, area_ha, centroid, geom)
            VALUES (
                %s, %s, %s, %s,
                ST_SetSRID(ST_MakePoint(%s, %s), 4326),
                ST_Multi(ST_GeomFromText(%s, 4326))
            )
            ON CONFLICT (grid_id) DO NOTHING;
            """,
            (
                site["id"], site["grid_id"], district_id, site["area_ha"],
                site["lon"], site["lat"], poly_wkt,
            ),
        )
    print(f"  {len(SITES)} candidate sites inserted")

    # Substations
    cur.execute("DELETE FROM substations WHERE source = 'seed_demo'")
    substations = [
        ("demo_sub_001", "Anantapur North GSS", "132kV", None, 77.6012, 14.8901),
        ("demo_sub_002", "Puttaparthi Sub", "33kV", None, 77.7834, 14.6723),
    ]
    for osm_id, name, voltage, operator, lon, lat in substations:
        cur.execute(
            """
            INSERT INTO substations (osm_id, name, voltage, operator, source, geom)
            VALUES (%s, %s, %s, %s, 'seed_demo', ST_SetSRID(ST_MakePoint(%s, %s), 4326));
            """,
            (osm_id, name, voltage, operator, lon, lat),
        )
    print(f"  {len(substations)} substations inserted")

    # Roads
    cur.execute("DELETE FROM roads WHERE source = 'seed_demo'")
    roads = [
        ("demo_rd_001", "NH 67", "primary", "asphalt", [(77.45, 14.82), (77.75, 14.82)]),
        ("demo_rd_002", "SH 14", "secondary", "concrete", [(77.58, 14.70), (77.58, 14.95)]),
    ]
    for osm_id, name, highway, surface, coords in roads:
        coord_str = ", ".join(f"{lon} {lat}" for lon, lat in coords)
        cur.execute(
            f"""
            INSERT INTO roads (osm_id, name, highway, surface, source, geom)
            VALUES (%s, %s, %s, %s, 'seed_demo',
                ST_GeomFromText('LINESTRING({coord_str})', 4326));
            """,
            (osm_id, name, highway, surface),
        )
    print(f"  {len(roads)} roads inserted")

    # Factor tables
    for site in SITES:
        sid = site["id"]
        cur.execute(
            """
            INSERT INTO solar_resource (site_id, ghi_kwh_m2_day, pvout_kwh_kwp_day, source, confidence)
            VALUES (%s, %s, %s, 'Global Solar Atlas (demo)', 0.8)
            ON CONFLICT (site_id) DO UPDATE
              SET ghi_kwh_m2_day = EXCLUDED.ghi_kwh_m2_day,
                  pvout_kwh_kwp_day = EXCLUDED.pvout_kwh_kwp_day;
            """,
            (sid, 5.4 + SITES.index(site) * 0.1, 1420 + SITES.index(site) * 15),
        )
        cur.execute(
            """
            INSERT INTO crop_intensity (site_id, ndvi_mean, ndvi_p75, ndvi_seasonality, crop_intensity_score, source)
            VALUES (%s, %s, %s, %s, %s, 'Sentinel-2 (demo)')
            ON CONFLICT (site_id) DO UPDATE
              SET ndvi_mean = EXCLUDED.ndvi_mean, ndvi_p75 = EXCLUDED.ndvi_p75;
            """,
            (sid, 0.28, 0.35, 0.15, 0.4),
        )
        cur.execute(
            """
            INSERT INTO land_cover (site_id, dominant_class, dominant_label, bare_sparse_pct, cropland_pct, built_pct, tree_pct, water_pct, source)
            VALUES (%s, 60, 'Bare/sparse vegetation', 0.61, 0.22, 0.05, 0.08, 0.04, 'ESA WorldCover v200 (demo)')
            ON CONFLICT (site_id) DO UPDATE
              SET bare_sparse_pct = EXCLUDED.bare_sparse_pct;
            """,
            (sid,),
        )
        cur.execute(
            """
            INSERT INTO slope (site_id, elevation_mean_m, slope_mean_deg, slope_p90_deg, source)
            VALUES (%s, %s, %s, %s, 'SRTMGL1_003 (demo)')
            ON CONFLICT (site_id) DO UPDATE
              SET slope_mean_deg = EXCLUDED.slope_mean_deg;
            """,
            (sid, 340 + SITES.index(site) * 10, 1.8, 3.2),
        )
    print(f"  factor tables populated for {len(SITES)} sites")

    # Scores
    weights = dict(solar=0.25, substation=0.20, road=0.15, slope=0.15, land=0.15, crop=0.10)
    for sid, solar, sub, road, slope, land, crop, total, conf in SCORES:
        cur.execute(
            """
            INSERT INTO scores (
                site_id,
                solar_norm, solar_contribution,
                substation_norm, substation_contribution,
                road_norm, road_contribution,
                slope_norm, slope_contribution,
                land_norm, land_contribution,
                crop_norm, crop_contribution,
                total_score, confidence_score, score_version
            ) VALUES (
                %s,
                %s, %s,
                %s, %s,
                %s, %s,
                %s, %s,
                %s, %s,
                %s, %s,
                %s, %s, 'v1.0'
            )
            ON CONFLICT (site_id) DO UPDATE
              SET total_score = EXCLUDED.total_score,
                  confidence_score = EXCLUDED.confidence_score,
                  computed_at = now();
            """,
            (
                sid,
                solar, round(solar * weights["solar"], 4),
                sub, round(sub * weights["substation"], 4),
                road, round(road * weights["road"], 4),
                slope, round(slope * weights["slope"], 4),
                land, round(land * weights["land"], 4),
                crop, round(crop * weights["crop"], 4),
                total, conf,
            ),
        )
    print(f"  scores inserted for {len(SCORES)} sites")

    # Observations
    cur.execute(
        "DELETE FROM parcel_observation_snapshots WHERE site_id::text LIKE 'a1b2c3d4-0000%'"
    )
    for obs in OBSERVATIONS:
        cur.execute(
            """
            INSERT INTO parcel_observation_snapshots
              (site_id, observed_at, source, observation_type, ndvi_mean, cloud_cover, notes)
            VALUES (%s, %s, %s, %s, %s, %s, %s);
            """,
            (
                obs["site_id"], obs["observed_at"], obs["source"],
                obs["observation_type"], obs["ndvi_mean"], obs["cloud_cover"], obs["notes"],
            ),
        )
    print(f"  {len(OBSERVATIONS)} observation snapshots inserted")

    conn.commit()
    cur.close()
    conn.close()
    print("\nDemo data loaded successfully.")
    print("\nTop sites by score:")
    print("  Site ID                                    | Grid ID           | Score | Confidence")
    for sid, solar, sub, road, slope, land, crop, total, conf in sorted(SCORES, key=lambda x: x[7], reverse=True):
        grid = next(s["grid_id"] for s in SITES if s["id"] == sid)
        print(f"  {sid} | {grid:<17} | {total:.3f} | {conf:.1f}")


if __name__ == "__main__":
    main()
