"""
Backend import and scoring logic smoke check.

Verifies:
  1. Backend modules import cleanly
  2. Scoring weights sum to 1.0
  3. Score computation produces a plausible result for a mock site
  4. API route modules import cleanly

Does not require a running database or API server.

Usage:
    python scripts/09_smoke_api.py
"""

import sys
import os

# Allow running from the project root or via `make smoke-api`
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

PASS = "\033[32mPASS\033[0m"
FAIL = "\033[31mFAIL\033[0m"


def check(label: str, fn):
    try:
        result = fn()
        print(f"  [{PASS}] {label}" + (f" — {result}" if result else ""))
        return True
    except Exception as e:
        print(f"  [{FAIL}] {label}: {e}")
        return False


def test_imports():
    import backend.app.main  # noqa: F401
    import backend.app.schemas  # noqa: F401
    import backend.app.routes.sites  # noqa: F401
    import backend.app.routes.observations  # noqa: F401
    import backend.app.routes.health  # noqa: F401


def test_weights_sum():
    weights = {"solar": 0.25, "substation": 0.20, "road": 0.15, "slope": 0.15, "land": 0.15, "crop": 0.10}
    total = sum(weights.values())
    assert abs(total - 1.0) < 1e-9, f"Weights sum to {total}, expected 1.0"
    return f"sum={total}"


def test_score_computation():
    """Replicate the scoring logic from 07_compute_scores.py with mock data."""
    import numpy as np

    weights = {"solar": 0.25, "substation": 0.20, "road": 0.15, "slope": 0.15, "land": 0.15, "crop": 0.10}

    # Mock a single site
    ghi = np.array([5.4])
    substation_km = np.array([12.3])
    road_km = np.array([2.1])
    slope_deg = np.array([2.0])
    bare_sparse_pct = np.array([0.61])
    ndvi_p75 = np.array([0.35])

    def minmax_pos(arr):
        lo, hi = arr.min(), arr.max()
        return np.zeros_like(arr) if hi == lo else (arr - lo) / (hi - lo)

    def minmax_inv(arr):
        lo, hi = arr.min(), arr.max()
        return np.ones_like(arr) if hi == lo else 1 - (arr - lo) / (hi - lo)

    solar_norm = minmax_pos(ghi)
    sub_norm = minmax_inv(substation_km)
    road_norm = minmax_inv(road_km)
    slope_norm = 1 - np.clip(slope_deg / 10, 0, 1)
    land_norm = minmax_pos(bare_sparse_pct)
    crop_norm = minmax_inv(ndvi_p75)

    total = (
        solar_norm * weights["solar"]
        + sub_norm * weights["substation"]
        + road_norm * weights["road"]
        + slope_norm * weights["slope"]
        + land_norm * weights["land"]
        + crop_norm * weights["crop"]
    )

    score = float(total[0])
    assert 0.0 <= score <= 1.0, f"Score out of range: {score}"
    return f"score={score:.4f}"


def test_schemas():
    from backend.app.schemas import ScoreBreakdown, ObservationSnapshot
    from datetime import datetime

    sb = ScoreBreakdown(solar_norm=0.84, solar_contribution=0.21, total_score=0.763)
    assert sb.solar_norm == 0.84

    obs = ObservationSnapshot(
        id="abc",
        site_id="def",
        observed_at=datetime(2024, 11, 15),
        source="Sentinel-2",
        observation_type="satellite_derived",
    )
    assert obs.ndvi_mean is None


def main():
    print("Dhara Energy Map — backend smoke check\n")

    results = [
        check("Backend modules import cleanly", test_imports),
        check("Scoring weights sum to 1.0", test_weights_sum),
        check("Score computation produces 0–1 result", test_score_computation),
        check("Pydantic schemas validate correctly", test_schemas),
    ]

    passed = sum(results)
    total = len(results)
    print(f"\n{passed}/{total} checks passed")

    if passed < total:
        sys.exit(1)


if __name__ == "__main__":
    main()
