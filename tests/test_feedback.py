import json
import pytest
from pathlib import Path
from feedback import ZoneRating, FitFeedback, BODY_ZONES, save_feedback, load_feedback_history


def test_zone_rating_rejects_rating_below_1():
    with pytest.raises(ValueError):
        ZoneRating(zone="bust", rating=0)


def test_zone_rating_rejects_rating_above_5():
    with pytest.raises(ValueError):
        ZoneRating(zone="bust", rating=6)


def test_zone_rating_rejects_unknown_zone():
    with pytest.raises(ValueError):
        ZoneRating(zone="elbow", rating=3)


def test_save_feedback_creates_file_at_correct_path(tmp_path):
    feedback = FitFeedback(
        date="2026-06-10",
        zone_ratings=[ZoneRating(zone="bust", rating=4)],
        notes="Fits well",
    )
    result = save_feedback(tmp_path, feedback)
    assert result == tmp_path / "fit_feedback.json"
    assert result.exists()


def test_save_feedback_appends_to_existing_history(tmp_path):
    feedback1 = FitFeedback(date="2026-06-10", zone_ratings=[ZoneRating("bust", 4)], notes="")
    feedback2 = FitFeedback(date="2026-06-11", zone_ratings=[ZoneRating("waist", 3)], notes="Tight")
    save_feedback(tmp_path, feedback1)
    save_feedback(tmp_path, feedback2)

    data = json.loads((tmp_path / "fit_feedback.json").read_text())
    assert len(data) == 2


def test_load_feedback_history_returns_empty_for_new_dir(tmp_path):
    assert load_feedback_history(tmp_path) == []


def test_load_feedback_history_returns_all_entries_in_order(tmp_path):
    feedback1 = FitFeedback(date="2026-06-10", zone_ratings=[ZoneRating("bust", 4)], notes="")
    feedback2 = FitFeedback(date="2026-06-11", zone_ratings=[ZoneRating("waist", 3)], notes="Tight at waist")
    save_feedback(tmp_path, feedback1)
    save_feedback(tmp_path, feedback2)

    history = load_feedback_history(tmp_path)
    assert len(history) == 2
    assert history[0].date == "2026-06-10"
    assert history[0].zone_ratings[0] == ZoneRating("bust", 4)
    assert history[1].date == "2026-06-11"
    assert history[1].notes == "Tight at waist"
