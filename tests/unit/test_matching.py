"""Unit tests for the weighted scoring matching algorithm.

Tests use SQLite via aiosqlite (PostGIS-specific location tests are skipped
when GeoAlchemy2 is unavailable).
"""

from __future__ import annotations

import math
import uuid
from datetime import datetime, timezone

import pytest

from app.core.matching import (
    compute_match,
    score_area,
    score_features,
    score_location,
    score_price,
)


# ── score_price tests ───────────────────────────────────────────────────────────


def test_score_price_within_budget_returns_100() -> None:
    """Price within budget should score 100."""
    assert score_price(budget_min=100_000, budget_max=200_000, property_price=150_000) == 100.0


def test_score_price_way_outside_budget_returns_near_0() -> None:
    """Price far outside budget should return a score near 0."""
    score = score_price(budget_min=100_000, budget_max=200_000, property_price=10_000_000)
    assert score < 5.0


def test_score_price_at_lower_bound_returns_100() -> None:
    """Price exactly at budget_min should score 100."""
    assert score_price(budget_min=100_000, budget_max=200_000, property_price=100_000) == 100.0


def test_score_price_at_upper_bound_returns_100() -> None:
    """Price exactly at budget_max should score 100."""
    assert score_price(budget_min=100_000, budget_max=200_000, property_price=200_000) == 100.0


def test_score_price_missing_budget_returns_50() -> None:
    """Missing budget bounds should return neutral 50."""
    assert score_price(budget_min=None, budget_max=200_000, property_price=150_000) == 50.0
    assert score_price(budget_min=100_000, budget_max=None, property_price=150_000) == 50.0
    assert score_price(budget_min=None, budget_max=None, property_price=150_000) == 50.0


# ── score_features tests ────────────────────────────────────────────────────────


def test_score_features_identical_returns_100() -> None:
    """Identical feature lists should score 100 (full Jaccard overlap)."""
    preferred = ["pool", "garage", "garden"]
    property_features = ["pool", "garage", "garden"]
    score = score_features(preferred, property_features)
    assert score == 100.0


def test_score_features_no_overlap_returns_0() -> None:
    """Completely disjoint feature lists should score 0."""
    preferred = ["pool", "garage"]
    property_features = ["beach", "mountain"]
    score = score_features(preferred, property_features)
    assert score == 0.0


def test_score_features_partial_overlap() -> None:
    """Partial overlap should return the correct Jaccard similarity."""
    preferred = ["pool", "garage", "garden"]
    property_features = ["pool", "garden"]
    # intersection = {"pool", "garden"} = 2, union = {"pool", "garage", "garden"} = 3
    # Jaccard = 2/3 ≈ 66.67
    score = score_features(preferred, property_features)
    assert score == pytest.approx(66.67, abs=0.1)


def test_score_features_empty_preferred_returns_50() -> None:
    """Empty preferred list returns neutral 50."""
    assert score_features(None, ["pool"]) == 50.0
    assert score_features([], ["pool"]) == 50.0


def test_score_features_empty_property_returns_50() -> None:
    """Empty property feature list returns neutral 50."""
    assert score_features(["pool"], None) == 50.0
    assert score_features(["pool"], []) == 50.0


# ── score_area tests ───────────────────────────────────────────────────────────


def test_score_area_within_range_returns_100() -> None:
    """Area within range should score 100."""
    assert score_area(area_min=50.0, area_max=100.0, property_area=75.0) == 100.0


def test_score_area_at_min_bound_returns_100() -> None:
    """Area exactly at min should score 100."""
    assert score_area(area_min=50.0, area_max=100.0, property_area=50.0) == 100.0


def test_score_area_at_max_bound_returns_100() -> None:
    """Area exactly at max should score 100."""
    assert score_area(area_min=50.0, area_max=100.0, property_area=100.0) == 100.0


def test_score_area_outside_range_returns_decay() -> None:
    """Area outside range should decay based on distance from midpoint."""
    score = score_area(area_min=50.0, area_max=100.0, property_area=200.0)
    # midpoint = 75, diff = |200-75|/75 = 125/75 ≈ 1.67, 100 - 1.67*100 ≈ 0
    assert 0.0 <= score < 10.0


def test_score_area_missing_bounds_returns_50() -> None:
    """Missing area bounds return neutral 50."""
    assert score_area(None, 100.0, 50.0) == 50.0
    assert score_area(50.0, None, 50.0) == 50.0
    assert score_area(None, None, 50.0) == 50.0


def test_score_area_missing_property_area_returns_50() -> None:
    """Missing property area returns neutral 50."""
    assert score_area(50.0, 100.0, None) == 50.0


# ── compute_match weights test ─────────────────────────────────────────────────


def test_compute_match_weights_sum_correctly() -> None:
    """The weighted total must equal the sum of weighted individual scores.

    Weights: price=0.30, location=0.25, features=0.25, area=0.20
    """
    # Create mock buyer and property with known scores
    class MockBuyer:
        budget_min = 100_000
        budget_max = 200_000
        preferred_locations = [{"lat": 4.6, "lon": -74.1, "radius_km": 10}]
        preferred_features = {"features": ["pool", "garage"]}
        area_min = 50.0
        area_max = 100.0

    class MockProperty:
        price = 150_000
        location = {"type": "Point", "coordinates": [-74.1, 4.6]}
        features = {"features": ["pool", "garage"]}
        area_m2 = 75.0

    result = compute_match(MockBuyer(), MockProperty())

    # Each individual score should be 100 since everything matches
    assert result["breakdown"]["price"] == 100.0
    assert result["breakdown"]["location"] == 100.0
    assert result["breakdown"]["features"] == 100.0
    assert result["breakdown"]["area"] == 100.0

    # Weighted total: 100*0.30 + 100*0.25 + 100*0.25 + 100*0.20 = 30+25+25+20 = 100
    assert result["total"] == 100.0

    # Verify weight sum = 1.0
    weight_sum = 0.30 + 0.25 + 0.25 + 0.20
    assert weight_sum == 1.0


def test_compute_match_weights_produce_correct_total() -> None:
    """Weighted average of individual scores must equal total."""
    class MockBuyer:
        budget_min = 100_000
        budget_max = 200_000
        preferred_locations = None
        preferred_features = None
        area_min = None
        area_max = None

    class MockProperty:
        price = 150_000  # within budget → 100
        location = None
        features = None
        area_m2 = None

    result = compute_match(MockBuyer(), MockProperty())

    expected_total = (
        result["breakdown"]["price"] * 0.30
        + result["breakdown"]["location"] * 0.25
        + result["breakdown"]["features"] * 0.25
        + result["breakdown"]["area"] * 0.20
    )
    assert math.isclose(result["total"], expected_total, rel_tol=1e-2)


# ── score_location tests ───────────────────────────────────────────────────────


def test_score_location_within_radius() -> None:
    """Property within preferred radius should score 100."""
    preferred_locations = [{"lat": 4.6, "lon": -74.1, "radius_km": 10}]
    # Bogota center to a point ~5km away (rough estimate)
    score = score_location(preferred_locations, property_lat=4.62, property_lon=-74.08)
    assert score == 100.0


def test_score_location_outside_radius_decay() -> None:
    """Property outside all radii should decay based on closest distance."""
    preferred_locations = [{"lat": 4.6, "lon": -74.1, "radius_km": 5}]
    # Point ~30km away
    score = score_location(preferred_locations, property_lat=4.9, property_lon=-74.0)
    # Should be between 0 and 50 (decay from 100 at 0km to 0 at 50km)
    assert 0.0 < score < 50.0


def test_score_location_no_preferred_locations_returns_50() -> None:
    """Missing preferred locations returns neutral 50."""
    assert score_location(None, property_lat=4.6, property_lon=-74.1) == 50.0
    assert score_location([], property_lat=4.6, property_lon=-74.1) == 50.0


def test_score_location_missing_coords_returns_50() -> None:
    """Missing property coordinates returns neutral 50."""
    preferred = [{"lat": 4.6, "lon": -74.1, "radius_km": 10}]
    assert score_location(preferred, None, -74.1) == 50.0
    assert score_location(preferred, 4.6, None) == 50.0
    assert score_location(preferred, None, None) == 50.0


@pytest.mark.skip(reason="Requires PostgreSQL+PostGIS")
def test_score_location_postgis_not_available_in_sqlite() -> None:
    """This test requires full PostGIS — skip in SQLite CI."""
    pass
