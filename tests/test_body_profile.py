import pytest
from pathlib import Path
from body_profile import BodyProfile, save, load, validate


@pytest.fixture
def valid_profile():
    return BodyProfile(
        bust=90.0, waist=70.0, hip=95.0,
        inseam=75.0, height=165.0, shoulder=38.0,
    )


def test_save_and_load_round_trips(valid_profile, tmp_path):
    path = tmp_path / "body_profile.json"
    save(valid_profile, path)
    loaded = load(path)
    assert loaded == valid_profile


def test_validate_warns_on_out_of_range_measurement(valid_profile):
    valid_profile.waist = 5.0  # impossibly small
    warnings = validate(valid_profile)
    assert any("waist" in w for w in warnings)


def test_validate_returns_no_warnings_for_valid_profile(valid_profile):
    assert validate(valid_profile) == []


def test_validate_does_not_warn_for_absent_extended_measurements(valid_profile):
    # extended fields default to None — should not trigger warnings
    assert valid_profile.arm is None
    warnings = validate(valid_profile)
    assert all("arm" not in w for w in warnings)


def test_load_returns_none_for_nonexistent_file(tmp_path):
    assert load(tmp_path / "missing.json") is None


def test_load_preserves_all_saved_values(valid_profile, tmp_path):
    valid_profile.arm = 58.0
    valid_profile.neck = 36.0
    path = tmp_path / "body_profile.json"
    save(valid_profile, path)
    loaded = load(path)
    assert loaded.arm == 58.0
    assert loaded.neck == 36.0
