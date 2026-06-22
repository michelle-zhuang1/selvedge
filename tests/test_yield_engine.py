import pytest
from pathlib import Path
from cv_pipeline import GarmentAnalysis
from body_profile import BodyProfile
from yield_engine import YieldEstimate, FeasibilityResult, estimate_yield, rank_feasibility, save_cv_output


@pytest.fixture
def shirt_analysis():
    return GarmentAnalysis(
        garment_type="shirt",
        confidence=0.92,
        dimensions={"bust": 100.0, "waist": 88.0, "shoulder": 40.0, "length": 65.0},
    )


@pytest.fixture
def body():
    return BodyProfile(
        bust=90.0, waist=70.0, hip=95.0,
        inseam=75.0, height=165.0, shoulder=38.0,
    )


def test_yield_estimated_from_shirt_dimensions(shirt_analysis):
    # shirt: width ≈ bust * 0.55 = 55.0cm, length = 65.0cm, 2 panels
    # area ≈ 55.0 * 65.0 * 2 = 7150 cm²
    est = estimate_yield(shirt_analysis)
    assert isinstance(est, YieldEstimate)
    assert est.area_cm2 == pytest.approx(7150.0, rel=0.05)
    assert est.width_cm == pytest.approx(55.0, rel=0.05)
    assert est.length_cm == pytest.approx(65.0, rel=0.05)


def test_feasible_candidate_has_yield_pct_at_least_one(body):
    # large shirt with lots of fabric → skirt should be feasible
    large_shirt = GarmentAnalysis(
        garment_type="shirt",
        confidence=0.95,
        dimensions={"bust": 140.0, "length": 90.0},
    )
    est = estimate_yield(large_shirt)
    results = rank_feasibility(est, body)
    skirt = next(r for r in results if r.garment_type == "skirt")
    assert skirt.feasible is True
    assert skirt.yield_pct >= 1.0


def test_infeasible_candidate_has_reason(body):
    # tiny garment → not enough fabric for anything
    tiny = GarmentAnalysis(
        garment_type="shirt",
        confidence=0.88,
        dimensions={"bust": 60.0, "length": 30.0},
    )
    est = estimate_yield(tiny)
    results = rank_feasibility(est, body)
    for r in results:
        assert r.feasible is False
        assert r.reason is not None
        assert len(r.reason) > 0


def test_results_sorted_feasible_first_then_by_yield_pct(body):
    large_shirt = GarmentAnalysis(
        garment_type="shirt",
        confidence=0.95,
        dimensions={"bust": 140.0, "length": 90.0},
    )
    est = estimate_yield(large_shirt)
    results = rank_feasibility(est, body)
    feasible = [r for r in results if r.feasible]
    infeasible = [r for r in results if not r.feasible]
    # all feasible results appear before any infeasible ones
    assert results == feasible + infeasible
    # within each group, sorted by yield_pct descending
    assert feasible == sorted(feasible, key=lambda r: -r.yield_pct)
    assert infeasible == sorted(infeasible, key=lambda r: -r.yield_pct)


def test_save_cv_output_writes_correct_structure(shirt_analysis, tmp_path):
    est = estimate_yield(shirt_analysis)
    path = tmp_path / "cv_output.json"
    save_cv_output(shirt_analysis, est, path)
    import json
    data = json.loads(path.read_text())
    assert data["garment_type"] == "shirt"
    assert data["confidence"] == pytest.approx(0.92)
    assert "dimensions" in data
    assert data["yield"]["area_cm2"] == pytest.approx(est.area_cm2)
    assert "width_cm" in data["yield"]
    assert "length_cm" in data["yield"]
