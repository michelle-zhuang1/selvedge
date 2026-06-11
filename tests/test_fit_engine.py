import pytest
from body_profile import BodyProfile
from fit_engine import GarmentMeasurements, AlterationInstruction, compute_alterations


@pytest.fixture
def profile():
    return BodyProfile(
        bust=90.0, waist=70.0, hip=95.0,
        inseam=75.0, height=165.0, shoulder=38.0,
    )


def test_garment_too_big_at_waist_produces_take_in_instruction(profile):
    # target waist = 70.0 + 2.54 ease = 72.54; garment = 80 → delta = +7.46
    garment = GarmentMeasurements(garment_type="skirt", waist=80.0)
    instructions = compute_alterations(profile, garment)
    assert len(instructions) == 1
    assert instructions[0].zone == "waist"
    assert instructions[0].delta_cm == pytest.approx(7.46, abs=0.01)
    assert "take in" in instructions[0].instruction
    assert "waist" in instructions[0].instruction


def test_garment_too_small_at_bust_produces_let_out_instruction(profile):
    # target bust = 90.0 + 5.08 ease = 95.08; garment = 91 → delta = -4.08
    garment = GarmentMeasurements(garment_type="shirt", bust=91.0)
    instructions = compute_alterations(profile, garment)
    assert len(instructions) == 1
    assert instructions[0].zone == "bust"
    assert instructions[0].delta_cm == pytest.approx(-4.08, abs=0.01)
    assert "let out" in instructions[0].instruction
    assert "bust" in instructions[0].instruction


def test_zone_within_tolerance_produces_no_instruction(profile):
    # target waist = 70.0 + 2.54 = 72.54; garment = 72.8 → delta = +0.26, within ±0.5
    garment = GarmentMeasurements(garment_type="skirt", waist=72.8)
    instructions = compute_alterations(profile, garment)
    assert instructions == []


def test_unmeasured_garment_zones_produce_no_instructions(profile):
    # garment only has waist — bust/hip/shoulder/inseam absent → only waist assessed
    garment = GarmentMeasurements(garment_type="skirt", waist=80.0)
    instructions = compute_alterations(profile, garment)
    zones = [i.zone for i in instructions]
    assert zones == ["waist"]


def test_all_out_of_tolerance_zones_are_reported(profile):
    # bust too small, waist too big, hip too big — all three should appear
    garment = GarmentMeasurements(
        garment_type="dress",
        bust=91.0,   # too small: target 95.08
        waist=80.0,  # too big:   target 72.54
        hip=105.0,   # too big:   target 98.81
    )
    instructions = compute_alterations(profile, garment)
    zones = {i.zone for i in instructions}
    assert zones == {"bust", "waist", "hip"}
