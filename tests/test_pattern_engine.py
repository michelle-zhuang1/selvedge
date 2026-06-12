import pytest
from pathlib import Path
from body_profile import BodyProfile
from yield_engine import YieldEstimate
from pattern_engine import (
    PatternPiece, PatternOutput, SkirtLength,
    generate_skirt, generate_trousers, save_svg, save_dxf, save_assembly_notes,
)


@pytest.fixture
def body():
    return BodyProfile(
        bust=90.0, waist=70.0, hip=95.0,
        inseam=75.0, height=165.0, shoulder=38.0,
    )


@pytest.fixture
def ample_yield():
    return YieldEstimate(area_cm2=20000.0, width_cm=100.0, length_cm=200.0)


@pytest.fixture
def tight_yield():
    return YieldEstimate(area_cm2=1000.0, width_cm=50.0, length_cm=20.0)


def test_skirt_generates_three_pieces(body, ample_yield):
    output = generate_skirt(body, ample_yield, SkirtLength.MIDI)
    names = [p.name for p in output.pieces]
    assert "front panel" in names
    assert "back panel" in names
    assert "waistband" in names
    assert len(output.pieces) == 3


def test_panel_width_reflects_body_and_ease(body, ample_yield):
    # hip half with ease = (95 + 4) / 2 = 49.5 cm
    # after buffering by seam_allowance=1.5, bounding box width >= 49.5
    output = generate_skirt(body, ample_yield, SkirtLength.MIDI, seam_allowance=1.5)
    panel = next(p for p in output.pieces if p.name == "front panel")
    minx, miny, maxx, maxy = panel.polygon.bounds
    width = maxx - minx
    # hip_half + ease is the widest part; buffering adds sa on each side
    expected_min = (body.hip + 4.0) / 2
    assert width == pytest.approx(expected_min + 2 * 1.5, abs=0.5)


def test_panel_height_reflects_length_and_allowances(body, ample_yield):
    # height = length + hem allowance (3.0) + 2 * seam_allowance (top + bottom via buffer)
    output = generate_skirt(body, ample_yield, SkirtLength.MIDI, seam_allowance=1.5)
    panel = next(p for p in output.pieces if p.name == "front panel")
    minx, miny, maxx, maxy = panel.polygon.bounds
    height = maxy - miny
    expected = float(SkirtLength.MIDI) + 3.0 + 2 * 1.5
    assert height == pytest.approx(expected, abs=0.5)


def test_fits_yield_true_when_fabric_is_sufficient(body, ample_yield):
    output = generate_skirt(body, ample_yield, SkirtLength.MIDI)
    assert output.fits_yield is True


def test_fits_yield_false_when_fabric_is_insufficient(body, tight_yield):
    output = generate_skirt(body, tight_yield, SkirtLength.MAXI)
    assert output.fits_yield is False


def test_assembly_notes_contain_length_name_and_seam_allowance(body, ample_yield):
    output = generate_skirt(body, ample_yield, SkirtLength.SHORT, seam_allowance=1.5)
    assert "mini" in output.assembly_notes.lower()
    assert "1.5" in output.assembly_notes


def test_assembly_notes_warn_when_yield_insufficient(body, tight_yield):
    output = generate_skirt(body, tight_yield, SkirtLength.MAXI, seam_allowance=1.5)
    assert "warning" in output.assembly_notes.lower() or "⚠" in output.assembly_notes


def test_save_svg_creates_nonempty_file(body, ample_yield, tmp_path):
    output = generate_skirt(body, ample_yield, SkirtLength.MIDI)
    path = tmp_path / "skirt.svg"
    save_svg(output, path)
    assert path.exists()
    assert path.stat().st_size > 0


def test_save_dxf_creates_nonempty_file(body, ample_yield, tmp_path):
    output = generate_skirt(body, ample_yield, SkirtLength.MIDI)
    path = tmp_path / "skirt.dxf"
    save_dxf(output, path)
    assert path.exists()
    assert path.stat().st_size > 0


def test_save_assembly_notes_writes_text(body, ample_yield, tmp_path):
    output = generate_skirt(body, ample_yield, SkirtLength.MIDI)
    path = tmp_path / "notes.txt"
    save_assembly_notes(output, path)
    assert path.exists()
    assert "Assembly order" in path.read_text()


# ── Trouser tests ──────────────────────────────────────────────────────────────

def test_trousers_generates_three_pieces(body, ample_yield):
    output = generate_trousers(body, ample_yield)
    names = [p.name for p in output.pieces]
    assert "front leg" in names
    assert "back leg" in names
    assert "waistband" in names
    assert len(output.pieces) == 3


def test_trouser_leg_height_reflects_inseam_and_rise(body, ample_yield):
    # rise=None → default 28 + ease 1.5 = 29.5; inseam=75; hem=3; 2*sa=3
    output = generate_trousers(body, ample_yield, seam_allowance=1.5)
    leg = next(p for p in output.pieces if p.name == "front leg")
    _, miny, _, maxy = leg.polygon.bounds
    height = maxy - miny
    expected = (28.0 + 1.5) + body.inseam + 3.0 + 2 * 1.5
    assert height == pytest.approx(expected, abs=0.5)


def test_trouser_back_leg_wider_than_front(body, ample_yield):
    output = generate_trousers(body, ample_yield)
    front = next(p for p in output.pieces if p.name == "front leg")
    back  = next(p for p in output.pieces if p.name == "back leg")
    front_w = front.polygon.bounds[2] - front.polygon.bounds[0]
    back_w  = back.polygon.bounds[2]  - back.polygon.bounds[0]
    assert back_w > front_w


def test_trouser_fits_yield_true_for_ample_fabric(body, ample_yield):
    output = generate_trousers(body, ample_yield)
    assert output.fits_yield is True


def test_trouser_fits_yield_false_for_tight_fabric(body, tight_yield):
    output = generate_trousers(body, tight_yield)
    assert output.fits_yield is False


def test_trouser_assembly_notes_are_trouser_specific(body, ample_yield):
    output = generate_trousers(body, ample_yield)
    notes = output.assembly_notes.lower()
    assert "crotch" in notes
    assert "inseam" in notes or str(int(body.inseam)) in output.assembly_notes


def test_trouser_assembly_notes_warn_when_insufficient(body, tight_yield):
    output = generate_trousers(body, tight_yield)
    assert "warning" in output.assembly_notes.lower() or "⚠" in output.assembly_notes


def test_save_trouser_svg_creates_nonempty_file(body, ample_yield, tmp_path):
    output = generate_trousers(body, ample_yield)
    path = tmp_path / "trousers.svg"
    save_svg(output, path)
    assert path.exists() and path.stat().st_size > 0


def test_save_trouser_dxf_creates_nonempty_file(body, ample_yield, tmp_path):
    output = generate_trousers(body, ample_yield)
    path = tmp_path / "trousers.dxf"
    save_dxf(output, path)
    assert path.exists() and path.stat().st_size > 0


def test_save_trouser_notes_writes_assembly_order(body, ample_yield, tmp_path):
    output = generate_trousers(body, ample_yield)
    path = tmp_path / "notes.txt"
    save_assembly_notes(output, path)
    assert "Assembly order" in path.read_text()
