"""Tests for layout_engine — greedy strip-packing cutting layout optimizer."""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
from shapely.geometry import Polygon

from pattern_engine import PatternPiece
from layout_engine import LayoutResult, PlacedPiece, compute_layout, save_layout_svg


def _rect_piece(name: str, width: float, height: float, grain: str = "vertical") -> PatternPiece:
    """Helper: axis-aligned rectangle PatternPiece."""
    poly = Polygon([(0, 0), (width, 0), (width, height), (0, height)])
    return PatternPiece(name=name, polygon=poly, grain_line=grain)


# ── Test 1: compute_layout returns LayoutResult with one PlacedPiece per input ──

def test_compute_layout_returns_one_placed_piece_per_input():
    pieces = [
        _rect_piece("front panel", 40.0, 70.0),
        _rect_piece("back panel", 40.0, 70.0),
        _rect_piece("waistband", 80.0, 9.0, grain="horizontal"),
    ]
    result = compute_layout(pieces, fabric_width_cm=150.0, fabric_length_cm=200.0)

    assert isinstance(result, LayoutResult)
    assert len(result.placements) == 3
    assert all(isinstance(p, PlacedPiece) for p in result.placements)
    names = {p.name for p in result.placements}
    assert names == {"front panel", "back panel", "waistband"}


# ── Test 2: no placement exceeds fabric width ────────────────────────────────

def test_no_placement_exceeds_fabric_width():
    fabric_width_cm = 100.0
    pieces = [
        _rect_piece("piece-a", 60.0, 50.0),
        _rect_piece("piece-b", 60.0, 50.0),
        _rect_piece("piece-c", 60.0, 30.0),
    ]
    result = compute_layout(pieces, fabric_width_cm=fabric_width_cm, fabric_length_cm=300.0)

    for placed in result.placements:
        bounds = placed.polygon.bounds  # (minx, miny, maxx, maxy)
        assert bounds[0] >= 0.0, f"{placed.name} left edge out of fabric"
        assert bounds[2] <= fabric_width_cm, (
            f"{placed.name} right edge {bounds[2]:.2f} exceeds fabric width {fabric_width_cm}"
        )


# ── Test 3: utilization = sum(piece areas) / (width × length), in [0, 1] ────

def test_utilization_is_ratio_of_piece_area_to_fabric_area():
    fabric_width_cm = 100.0
    fabric_length_cm = 100.0
    # Two 30×20 rectangles; piece area = 2 * 600 = 1200; fabric = 10000
    pieces = [
        _rect_piece("piece-a", 30.0, 20.0),
        _rect_piece("piece-b", 30.0, 20.0),
    ]
    result = compute_layout(pieces, fabric_width_cm=fabric_width_cm, fabric_length_cm=fabric_length_cm)

    expected_piece_area = 2 * 30.0 * 20.0
    expected_utilization = expected_piece_area / (fabric_width_cm * fabric_length_cm)

    assert 0.0 <= result.utilization <= 1.0
    assert abs(result.utilization - expected_utilization) < 1e-6


# ── Test 4: fits_fabric True when height fits, False when it doesn't ─────────

def test_fits_fabric_true_when_height_fits():
    # One piece 40 cm tall; fabric 150 cm long — should fit
    pieces = [_rect_piece("panel", 40.0, 40.0)]
    result = compute_layout(pieces, fabric_width_cm=150.0, fabric_length_cm=150.0)
    assert result.fits_fabric is True


def test_fits_fabric_false_when_height_exceeds_length():
    # Three stacked pieces each 50 cm tall + gaps → total > 100 cm
    pieces = [
        _rect_piece("piece-a", 110.0, 50.0),  # too wide to share a row → stacked
        _rect_piece("piece-b", 110.0, 50.0),
        _rect_piece("piece-c", 110.0, 50.0),
    ]
    result = compute_layout(pieces, fabric_width_cm=120.0, fabric_length_cm=100.0)
    assert result.fits_fabric is False


# ── Test 5: vertical-grain pieces are not rotated ────────────────────────────

def test_vertical_grain_pieces_preserve_bounding_box_orientation():
    """A tall narrow piece with grain_line='vertical' must remain tall and narrow."""
    # 20 cm wide × 80 cm tall — clearly portrait orientation
    piece = _rect_piece("panel", 20.0, 80.0, grain="vertical")
    result = compute_layout([piece], fabric_width_cm=150.0, fabric_length_cm=200.0)

    placed = result.placements[0]
    bounds = placed.polygon.bounds  # (minx, miny, maxx, maxy)
    placed_w = bounds[2] - bounds[0]
    placed_h = bounds[3] - bounds[1]

    # Width should still be smaller than height (portrait), not swapped
    assert placed_w < placed_h, (
        f"Vertical-grain piece was rotated: placed width={placed_w:.1f} >= height={placed_h:.1f}"
    )


# ── Test 6: save_layout_svg creates a non-empty file ─────────────────────────

def test_save_layout_svg_creates_nonempty_file():
    pieces = [
        _rect_piece("front panel", 40.0, 70.0),
        _rect_piece("waistband", 80.0, 9.0, grain="horizontal"),
    ]
    result = compute_layout(pieces, fabric_width_cm=150.0, fabric_length_cm=200.0)

    with tempfile.TemporaryDirectory() as tmp:
        svg_path = Path(tmp) / "cutting_layout.svg"
        save_layout_svg(result, fabric_width_cm=150.0, fabric_length_cm=200.0, path=svg_path)

        assert svg_path.exists(), "SVG file was not created"
        assert svg_path.stat().st_size > 0, "SVG file is empty"
        content = svg_path.read_text()
        assert "<svg" in content, "File does not contain SVG markup"
