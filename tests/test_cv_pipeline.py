from __future__ import annotations
import numpy as np
import pytest
from unittest.mock import MagicMock, patch, call
from cv_pipeline import CVPipeline, GarmentAnalysis
from fit_engine import GarmentMeasurements


def _blank_image(h: int = 100, w: int = 80) -> np.ndarray:
    return np.zeros((h, w, 3), dtype=np.uint8)


# ── Tracer bullet ──────────────────────────────────────────────────────────────

def test_analyze_returns_garment_analysis():
    pipeline = CVPipeline()
    result = pipeline.analyze(_blank_image(), _blank_image())
    assert isinstance(result, GarmentAnalysis)
    assert isinstance(result.garment_type, str)
    assert 0.0 <= result.confidence <= 1.0
    assert isinstance(result.dimensions, dict)


# ── Perspective correction ─────────────────────────────────────────────────────

def test_perspective_correction_applied_before_extraction():
    corrected = _blank_image()
    mock_correct = MagicMock(return_value=corrected)
    mock_extract = MagicMock(return_value={"bust": 90.0})

    pipeline = CVPipeline()
    pipeline._correct_perspective = mock_correct
    pipeline._extract_dimensions = mock_extract

    front = _blank_image()
    back = _blank_image()
    pipeline.analyze(front, back)

    assert mock_correct.call_count == 2
    # extraction receives corrected images, not originals
    extract_call_args = mock_extract.call_args[0]
    assert extract_call_args[0] is corrected
    assert extract_call_args[1] is corrected


# ── Garment-type-appropriate dimensions ───────────────────────────────────────

def test_trousers_dimensions_include_inseam_not_bust():
    pipeline = CVPipeline()
    pipeline._classify = MagicMock(return_value=("trousers", 0.95))
    pipeline._correct_perspective = MagicMock(side_effect=lambda img: img)
    pipeline._extract_dimensions = MagicMock(return_value={
        "waist": 76.0, "hip": 92.0, "inseam": 78.0, "length": 100.0
    })

    result = pipeline.analyze(_blank_image(), _blank_image())
    assert "inseam" in result.dimensions
    assert "bust" not in result.dimensions


def test_shirt_dimensions_include_bust_not_inseam():
    pipeline = CVPipeline()
    pipeline._classify = MagicMock(return_value=("shirt", 0.91))
    pipeline._correct_perspective = MagicMock(side_effect=lambda img: img)
    pipeline._extract_dimensions = MagicMock(return_value={
        "bust": 90.0, "waist": 76.0, "shoulder": 38.0, "length": 65.0
    })

    result = pipeline.analyze(_blank_image(), _blank_image())
    assert "bust" in result.dimensions
    assert "inseam" not in result.dimensions


# ── to_garment_measurements ────────────────────────────────────────────────────

def test_to_garment_measurements_maps_fields():
    pipeline = CVPipeline()
    analysis = GarmentAnalysis(
        garment_type="dress",
        confidence=0.88,
        dimensions={"bust": 92.0, "waist": 74.0, "hip": 96.0, "length": 110.0},
    )
    gm = pipeline.to_garment_measurements(analysis)
    assert isinstance(gm, GarmentMeasurements)
    assert gm.garment_type == "dress"
    assert gm.bust == 92.0
    assert gm.waist == 74.0
    assert gm.hip == 96.0
    assert gm.length == 110.0
    assert gm.inseam is None
    assert gm.shoulder is None


def test_to_garment_measurements_none_for_missing_dimensions():
    pipeline = CVPipeline()
    analysis = GarmentAnalysis(
        garment_type="shirt",
        confidence=0.9,
        dimensions={"bust": 88.0},
    )
    gm = pipeline.to_garment_measurements(analysis)
    assert gm.bust == 88.0
    assert gm.waist is None
    assert gm.inseam is None


# ── Low-confidence warning ─────────────────────────────────────────────────────

def test_low_confidence_raises_warning():
    pipeline = CVPipeline()
    pipeline._classify = MagicMock(return_value=("shirt", 0.40))
    pipeline._correct_perspective = MagicMock(side_effect=lambda img: img)
    pipeline._extract_dimensions = MagicMock(return_value={"bust": 88.0})

    with pytest.warns(UserWarning, match="confidence"):
        result = pipeline.analyze(_blank_image(), _blank_image())

    assert result.confidence == 0.40
